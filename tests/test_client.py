import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from outerram.client import benchmark_server, get_json, probe_server, qualify_server


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            body = {"status": "ok"}
        elif self.path == "/v1/models":
            body = {"object": "list", "data": [{"id": "fake"}]}
        else:
            self.send_response(404); self.end_headers(); return
        raw = json.dumps(body).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0")); req = json.loads(self.rfile.read(n))
        if self.path != "/v1/chat/completions":
            self.send_response(404); self.end_headers(); return
        if req.get("stream"):
            self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Connection", "close"); self.end_headers()
            for obj in [
                {"choices": [{"delta": {"content": "hello "}}]},
                {"choices": [{"delta": {"content": "world"}}]},
                {"choices": [], "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}},
            ]:
                self.wfile.write(f"data: {json.dumps(obj)}\n\n".encode()); self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n"); self.wfile.flush(); self.close_connection = True
        else:
            if req.get("tools"):
                has_tool_result = any(isinstance(message, dict) and message.get("role") == "tool" for message in req.get("messages", []))
                if has_tool_result:
                    body = {"choices": [{"message": {"content": "OUTERRAM_TOOL_OK"}, "finish_reason": "stop"}]}
                else:
                    body = {"choices": [{"message": {"content": None, "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "add_numbers", "arguments": "{\"a\":2,\"b\":3}"}}]}, "finish_reason": "tool_calls"}]}
            else:
                body = {"choices": [{"message": {"content": "OUTERRAM_OK"}}]}
            raw = json.dumps(body).encode(); self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)


def start():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    return server, thread


def test_probe_server_end_to_end():
    server, thread = start()
    try:
        result = probe_server(f"http://127.0.0.1:{server.server_port}/v1")
        assert result["healthy"] and result["chat_completed"] and result["response_ok"]
        assert result["models"] == ["fake"]
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_probe_server_tool_call_end_to_end():
    server, thread = start()
    try:
        result = probe_server(f"http://127.0.0.1:{server.server_port}/v1", test_tools=True)
        assert result["response_ok"] and result["tool_call_completed"] is True
        assert result["tool_call"]["function"]["name"] == "add_numbers"
        assert result["tool_roundtrip_completed"] is True
        assert result["tool_roundtrip_response"] == "OUTERRAM_TOOL_OK"
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_benchmark_collects_usage_and_text():
    server, thread = start()
    try:
        result = benchmark_server(f"http://127.0.0.1:{server.server_port}/v1", prompt="x", max_tokens=8)
        assert result.text == "hello world"
        assert result.completion_tokens == 2 and result.prompt_tokens == 3
        assert result.ttft_seconds is not None and result.tokens_per_second is not None
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_qualify_server_end_to_end():
    server, thread = start()
    try:
        result = qualify_server(f"http://127.0.0.1:{server.server_port}/v1", prompt="write code", max_tokens=8, require_tool_call=True)
        assert result["qualified"] is True
        assert result["gates"] == {"health_and_marker": True, "structured_tool_call_roundtrip": True, "streaming_benchmark": True}
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_api_key_is_allowed_on_loopback_plaintext():
    server, thread = start()
    try:
        status = get_json(f"http://127.0.0.1:{server.server_port}/health", api_key="local-secret")
        assert status["status"] == "ok"
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_api_key_is_refused_on_remote_plaintext_before_network_io():
    with pytest.raises(ValueError, match="Refusing to send an API key"):
        get_json("http://example.com/v1/models", api_key="do-not-leak")


def test_api_key_is_allowed_for_https_transport(monkeypatch):
    def stop(*args, **kwargs):
        raise RuntimeError("transport reached")
    monkeypatch.setattr("urllib.request.urlopen", stop)
    with pytest.raises(RuntimeError, match="transport reached"):
        get_json("https://example.com/v1/models", api_key="encrypted-secret")
