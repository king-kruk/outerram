from __future__ import annotations

import argparse
import hmac
import json
import math
import os
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Iterable

_MAX_BODY_BYTES = 4 * 1024 * 1024
_MAX_TOKENS_HARD_CAP = 32768
_MAX_MESSAGES = 4096
_MAX_TOOLS = 256
_MAX_CONNECTIONS = 8
_SOCKET_TIMEOUT_SECONDS = 30.0


def _chat_prompt(tokenizer: Any, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> str:
    apply = getattr(tokenizer, "apply_chat_template", None)
    if callable(apply):
        kwargs: dict[str, Any] = {"tokenize": False, "add_generation_prompt": True}
        if tools:
            kwargs["tools"] = tools
        try:
            return apply(messages, **kwargs)
        except TypeError:
            kwargs.pop("tools", None)
            try:
                return apply(messages, **kwargs)
            except TypeError:
                return apply(messages, tokenize=False)
    chunks = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(str(part.get("text", "")))
            content = "\n".join(text_parts)
        if role == "assistant" and message.get("tool_calls"):
            chunks.append("assistant tool_calls: " + json.dumps(message.get("tool_calls"), ensure_ascii=False))
        elif role == "tool":
            tool_id = message.get("tool_call_id") or "unknown"
            chunks.append(f"tool[{tool_id}]: {content}")
        else:
            chunks.append(f"{role}: {content}")
    if tools:
        chunks.append("Available tools: " + json.dumps(tools, ensure_ascii=False))
    chunks.append("assistant:")
    return "\n".join(chunks)


def _normalize_tool_calls(tokenizer: Any, text: str, tools: list[dict[str, Any]] | None) -> tuple[str, list[dict[str, Any]]]:
    parser = getattr(tokenizer, "tool_parser", None)
    start = getattr(tokenizer, "tool_call_start", None)
    end = getattr(tokenizer, "tool_call_end", None)
    if not callable(parser) or not start or start not in text:
        return text, []
    payloads: list[str] = []
    visible_parts: list[str] = []
    cursor = 0
    while True:
        idx = text.find(start, cursor)
        if idx < 0:
            visible_parts.append(text[cursor:])
            break
        visible_parts.append(text[cursor:idx])
        payload_start = idx + len(start)
        if end:
            end_idx = text.find(end, payload_start)
            if end_idx < 0:
                visible_parts.append(text[idx:])
                break
            payloads.append(text[payload_start:end_idx].strip())
            cursor = end_idx + len(end)
        else:
            payloads.append(text[payload_start:].strip())
            cursor = len(text)
            break
    calls: list[dict[str, Any]] = []
    for payload in payloads:
        try:
            parsed = parser(payload, tools)
        except TypeError:
            parsed = parser(payload)
        except (ValueError, json.JSONDecodeError):
            continue
        items = parsed if isinstance(parsed, list) else [parsed]
        for item in items:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            arguments = item.get("arguments", {})
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments, ensure_ascii=False)
            calls.append({"id": item.get("id") or f"call_{uuid.uuid4().hex}", "type": "function", "function": {"name": str(item["name"]), "arguments": arguments}})
    return "".join(visible_parts).strip(), calls


def _token_count(tokenizer: Any, text: str) -> int | None:
    try:
        return len(tokenizer.encode(text))
    except Exception:
        return None


class DenseFlashRuntime:
    def __init__(self, model_name: str, ram_gib: float):
        try:
            from mlx_flash import FlashConfig, FlashManager
        except ImportError as exc:
            raise RuntimeError("mlx-flash is not installed. Run: outerram bootstrap <model>") from exc
        self.model_name = model_name
        self.manager = FlashManager(FlashConfig(ram_budget_gb=ram_gib))
        self.model, self.tokenizer = self.manager.load(model_name)
        self.lock = threading.Lock()

    def stream(self, messages: list[dict[str, Any]], *, max_tokens: int, temperature: float, tools: list[dict[str, Any]] | None = None) -> Iterable[str]:
        prompt = _chat_prompt(self.tokenizer, messages, tools)
        with self.lock:
            yield from self.model.stream_generate(prompt, max_tokens=max_tokens, temperature=temperature)

    def usage(self, messages: list[dict[str, Any]], text: str, tools: list[dict[str, Any]] | None = None) -> dict[str, int] | None:
        prompt = _chat_prompt(self.tokenizer, messages, tools)
        p = _token_count(self.tokenizer, prompt)
        c = _token_count(self.tokenizer, text)
        if p is None or c is None:
            return None
        return {"prompt_tokens": p, "completion_tokens": c, "total_tokens": p + c}


class DenseHandler(BaseHTTPRequestHandler):
    runtime: DenseFlashRuntime
    api_key: str | None = None

    def log_message(self, fmt: str, *args):
        return

    def _json(self, status: int, data: dict[str, Any], request_id: str | None = None) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("X-Content-Type-Options", "nosniff")
        if request_id:
            self.send_header("X-Request-ID", request_id)
        self.end_headers()
        self.wfile.write(raw)

    def _authorized(self) -> bool:
        if not self.api_key:
            return True
        auth = self.headers.get("Authorization", "")
        prefix = "Bearer "
        supplied = auth[len(prefix):] if auth.startswith(prefix) else ""
        return bool(supplied) and hmac.compare_digest(supplied, self.api_key)

    def _require_auth(self) -> bool:
        if self._authorized():
            return True
        self._json(401, {"error": {"message": "unauthorized", "type": "authentication_error"}})
        return False

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok", "runtime": "mlx-flash", "api": "openai-chat-v1"})
            return
        if self.path == "/v1/models":
            if not self._require_auth():
                return
            self._json(200, {"object": "list", "data": [{"id": self.runtime.model_name, "object": "model", "owned_by": "local"}]})
            return
        self._json(404, {"error": {"message": "not found"}})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self._json(404, {"error": {"message": "not found"}})
            return
        if not self._require_auth():
            return
        request_id = f"chatcmpl-{uuid.uuid4().hex}"
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > _MAX_BODY_BYTES:
                raise ValueError(f"request body must be between 1 and {_MAX_BODY_BYTES} bytes")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("request body must be a JSON object")
            requested_model = body.get("model")
            if requested_model is not None and (not isinstance(requested_model, str) or not requested_model.strip()):
                raise ValueError("model must be a non-empty string when provided")
            messages = body.get("messages") or []
            if not isinstance(messages, list) or not messages:
                raise ValueError("messages must be a non-empty list")
            if len(messages) > _MAX_MESSAGES:
                raise ValueError(f"messages must contain at most {_MAX_MESSAGES} items")
            if not all(isinstance(message, dict) for message in messages):
                raise ValueError("each message must be an object")
            for message in messages:
                role = message.get("role")
                if not isinstance(role, str) or not role:
                    raise ValueError("each message requires a non-empty string role")
                content = message.get("content")
                if content is not None and not isinstance(content, (str, list)):
                    raise ValueError("message content must be a string, list, or null")
            token_value = body.get("max_completion_tokens", body.get("max_tokens", 512))
            max_tokens = int(token_value)
            if not 1 <= max_tokens <= _MAX_TOKENS_HARD_CAP:
                raise ValueError(f"max_tokens must be in [1, {_MAX_TOKENS_HARD_CAP}]")
            temperature = float(body.get("temperature", 0.0))
            if not math.isfinite(temperature) or temperature < 0:
                raise ValueError("temperature must be a finite non-negative number")
            stream = bool(body.get("stream", False))
            tools = body.get("tools") or None
            if tools is not None:
                if not isinstance(tools, list):
                    raise ValueError("tools must be a list")
                if len(tools) > _MAX_TOOLS:
                    raise ValueError(f"tools must contain at most {_MAX_TOOLS} items")
                if not all(isinstance(tool, dict) for tool in tools):
                    raise ValueError("each tool must be an object")
            tool_choice = body.get("tool_choice", "auto")
            if tool_choice in (None, "auto"):
                pass
            elif tool_choice == "none":
                tools = None
            else:
                raise ValueError("dense-stream currently supports tool_choice='auto' or 'none' only")
            stream_options = body.get("stream_options") or {}
            if not isinstance(stream_options, dict):
                raise ValueError("stream_options must be an object")
            include_usage = bool(stream_options.get("include_usage", False))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._json(400, {"error": {"message": str(exc), "type": "invalid_request_error"}}, request_id)
            return
        created = int(time.time())
        model_name = requested_model or self.runtime.model_name
        try:
            if tools:
                raw_text = "".join(self.runtime.stream(messages, max_tokens=max_tokens, temperature=temperature, tools=tools))
                content, tool_calls = _normalize_tool_calls(self.runtime.tokenizer, raw_text, tools)
                finish_reason = "tool_calls" if tool_calls else "stop"
                usage = self.runtime.usage(messages, raw_text, tools)
                if stream:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "close")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.send_header("X-Request-ID", request_id)
                    self.end_headers()
                    delta: dict[str, Any] = {"role": "assistant"}
                    if content:
                        delta["content"] = content
                    if tool_calls:
                        delta["tool_calls"] = [dict(call, index=i) for i, call in enumerate(tool_calls)]
                    chunk = {"id": request_id, "object": "chat.completion.chunk", "created": created, "model": model_name, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
                    self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
                    final = {"id": request_id, "object": "chat.completion.chunk", "created": created, "model": model_name, "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}]}
                    self.wfile.write(f"data: {json.dumps(final)}\n\n".encode())
                    if include_usage and usage:
                        usage_chunk = {"id": request_id, "object": "chat.completion.chunk", "created": created, "model": model_name, "choices": [], "usage": usage}
                        self.wfile.write(f"data: {json.dumps(usage_chunk)}\n\n".encode())
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
                    self.close_connection = True
                    return
                message: dict[str, Any] = {"role": "assistant", "content": content or None}
                if tool_calls:
                    message["tool_calls"] = tool_calls
                payload = {"id": request_id, "object": "chat.completion", "created": created, "model": model_name, "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}]}
                if usage:
                    payload["usage"] = usage
                self._json(200, payload, request_id)
                return
            if stream:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Request-ID", request_id)
                self.end_headers()
                first = True
                collected: list[str] = []
                for segment in self.runtime.stream(messages, max_tokens=max_tokens, temperature=temperature, tools=None):
                    if not segment:
                        continue
                    collected.append(segment)
                    chunk = {"id": request_id, "object": "chat.completion.chunk", "created": created, "model": model_name, "choices": [{"index": 0, "delta": ({"role": "assistant", "content": segment} if first else {"content": segment}), "finish_reason": None}]}
                    first = False
                    self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8"))
                    self.wfile.flush()
                final = {"id": request_id, "object": "chat.completion.chunk", "created": created, "model": model_name, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
                self.wfile.write(f"data: {json.dumps(final)}\n\n".encode("utf-8"))
                if include_usage:
                    usage = self.runtime.usage(messages, "".join(collected), None)
                    if usage:
                        usage_chunk = {"id": request_id, "object": "chat.completion.chunk", "created": created, "model": model_name, "choices": [], "usage": usage}
                        self.wfile.write(f"data: {json.dumps(usage_chunk)}\n\n".encode())
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
                self.close_connection = True
                return
            text = "".join(self.runtime.stream(messages, max_tokens=max_tokens, temperature=temperature, tools=None))
            payload = {"id": request_id, "object": "chat.completion", "created": created, "model": model_name, "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]}
            usage = self.runtime.usage(messages, text, None)
            if usage:
                payload["usage"] = usage
            self._json(200, payload, request_id)
        except Exception as exc:
            print(f"request {request_id} failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            public_error = {"error": {"message": "internal server error", "type": "server_error", "request_id": request_id}}
            if stream:
                try:
                    self.wfile.write(f"data: {json.dumps(public_error)}\n\ndata: [DONE]\n\n".encode())
                    self.wfile.flush()
                    self.close_connection = True
                except Exception:
                    pass
            else:
                self._json(500, public_error, request_id)


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    """Small local server with bounded concurrent sockets and read timeouts."""

    daemon_threads = True
    request_queue_size = 16

    def __init__(self, server_address, handler_class, *, max_connections: int = _MAX_CONNECTIONS):
        super().__init__(server_address, handler_class)
        self._connection_slots = threading.BoundedSemaphore(max_connections)

    def get_request(self):
        request, client_address = super().get_request()
        request.settimeout(_SOCKET_TIMEOUT_SECONDS)
        return request, client_address

    def process_request(self, request, client_address):
        if not self._connection_slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._connection_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._connection_slots.release()


def _is_loopback(host: str) -> bool:
    return host in {"127.0.0.1", "localhost", "::1"}


def serve(model: str, host: str, port: int, ram_gib: float, *, api_key: str | None = None, allow_unauthenticated_remote: bool = False) -> None:
    if not 1 <= int(port) <= 65535:
        raise ValueError("port must be between 1 and 65535")
    if not host or any(ch.isspace() for ch in host):
        raise ValueError("host must be a non-empty hostname/address without whitespace")
    if not _is_loopback(host) and not allow_unauthenticated_remote:
        raise RuntimeError(
            "Refusing non-loopback plaintext HTTP. Keep OuterRAM on loopback and use an SSH tunnel/TLS reverse proxy. "
            "Pass --allow-unauthenticated-remote only as an explicit insecure-network override; an API key does not encrypt HTTP traffic."
        )
    runtime = DenseFlashRuntime(model, ram_gib)
    handler = type("ConfiguredDenseHandler", (DenseHandler,), {"runtime": runtime, "api_key": api_key})
    server = BoundedThreadingHTTPServer((host, port), handler)
    print(f"OuterRAM dense-stream server: http://{host}:{port}/v1")
    print(f"model: {model}")
    print(f"weight residence budget: {ram_gib:.1f} GiB")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        shutdown = getattr(runtime.model, "shutdown", None)
        if callable(shutdown):
            shutdown()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenAI-compatible server for mlx-flash dense streaming")
    parser.add_argument("--model", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--ram", type=float, default=4.0)
    parser.add_argument("--api-key", default=None, help="Bearer token; prefer OUTERRAM_API_KEY to keep secrets out of argv")
    parser.add_argument(
        "--allow-unauthenticated-remote",
        action="store_true",
        help="Unsafe override permitting non-loopback plaintext HTTP; prefer loopback plus SSH/TLS",
    )
    args = parser.parse_args(argv)
    api_key = args.api_key or os.environ.get("OUTERRAM_API_KEY") or os.environ.get("STRETCHMLX_API_KEY")
    serve(args.model, args.host, args.port, args.ram, api_key=api_key, allow_unauthenticated_remote=args.allow_unauthenticated_remote)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
