from __future__ import annotations

import ipaddress
import json
import time
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Iterator
from urllib.parse import urlparse


@dataclass(frozen=True)
class BenchmarkResult:
    base_url: str
    model: str | None
    ttft_seconds: float | None
    total_seconds: float
    completion_tokens: int | None
    prompt_tokens: int | None
    tokens_per_second: float | None
    output_chars: int
    chunks: int
    text: str

    def to_dict(self) -> dict[str, Any]: return asdict(self)


def _headers(api_key: str | None = None) -> dict[str, str]:
    out = {"Content-Type": "application/json"}
    if api_key: out["Authorization"] = f"Bearer {api_key}"
    return out


def _loopback_host(host: str | None) -> bool:
    if not host: return False
    if host.lower() == "localhost": return True
    try: return ipaddress.ip_address(host).is_loopback
    except ValueError: return False


def _validate_secret_transport(url: str, api_key: str | None) -> None:
    if not api_key: return
    parsed = urlparse(url)
    if parsed.scheme == "https": return
    if parsed.scheme == "http" and _loopback_host(parsed.hostname): return
    raise ValueError("Refusing to send an API key over a non-loopback plaintext or unsupported URL. Use HTTPS, or keep OuterRAM on loopback and connect through an SSH/TLS tunnel.")


def get_json(url: str, *, api_key: str | None = None, timeout: float = 10.0) -> dict[str, Any]:
    _validate_secret_transport(url, api_key)
    req = urllib.request.Request(url, headers=_headers(api_key))
    with urllib.request.urlopen(req, timeout=timeout) as resp: return json.loads(resp.read())


def post_json(url: str, payload: dict[str, Any], *, api_key: str | None = None, timeout: float = 120.0) -> dict[str, Any]:
    _validate_secret_transport(url, api_key)
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=_headers(api_key), method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp: return json.loads(resp.read())


def iter_sse(url: str, payload: dict[str, Any], *, api_key: str | None = None, timeout: float = 120.0) -> Iterator[tuple[float, str]]:
    _validate_secret_transport(url, api_key)
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=_headers(api_key), method="POST")
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        while True:
            line = resp.readline()
            if not line: break
            text = line.decode("utf-8", errors="replace").strip()
            if text.startswith("data:"): yield time.perf_counter() - start, text[5:].strip()


def probe_server(base_url: str, *, api_key: str | None = None, timeout: float = 10.0, test_tools: bool = False) -> dict[str, Any]:
    base = base_url.rstrip("/"); root = base[:-3] if base.endswith("/v1") else base
    health = get_json(root + "/health", timeout=timeout); models = get_json(base + "/models", api_key=api_key, timeout=timeout)
    model_ids = [m.get("id") for m in models.get("data", []) if isinstance(m, dict)]
    payload = {"model": model_ids[0] if model_ids else "local", "messages": [{"role": "user", "content": "Reply with exactly: OUTERRAM_OK"}], "max_tokens": 32, "temperature": 0, "stream": False}
    chat = post_json(base + "/chat/completions", payload, api_key=api_key, timeout=max(timeout, 30.0)); choices = chat.get("choices") or []
    content = str((choices[0].get("message") or {}).get("content") or "") if choices else ""
    result: dict[str, Any] = {"healthy": health.get("status") == "ok", "health": health, "models": model_ids, "chat_completed": bool(choices), "response_ok": "OUTERRAM_OK" in content, "response": content, "tool_call_completed": None, "tool_call": None}
    if test_tools:
        tool_messages = [{"role": "user", "content": "Use the add_numbers tool to add 2 and 3. Do not answer directly. After you receive the tool result, reply exactly: OUTERRAM_TOOL_OK"}]
        tool_payload = {"model": model_ids[0] if model_ids else "local", "messages": tool_messages, "tools": [{"type": "function", "function": {"name": "add_numbers", "description": "Add two integers.", "parameters": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}}}], "tool_choice": "auto", "max_tokens": 64, "temperature": 0, "stream": False}
        tool_response = post_json(base + "/chat/completions", tool_payload, api_key=api_key, timeout=max(timeout, 30.0)); tool_choices = tool_response.get("choices") or []
        calls = (tool_choices[0].get("message") or {}).get("tool_calls") or [] if tool_choices else []
        valid_call = next((call for call in calls if isinstance(call, dict) and isinstance(call.get("function"), dict) and call["function"].get("name") == "add_numbers"), None)
        result["tool_call_completed"] = valid_call is not None; result["tool_call"] = valid_call; result["tool_roundtrip_completed"] = False; result["tool_roundtrip_response"] = None
        if valid_call is not None:
            continuation = {**tool_payload, "messages": tool_messages + [{"role": "assistant", "content": None, "tool_calls": [valid_call]}, {"role": "tool", "tool_call_id": valid_call.get("id"), "content": "5"}], "max_tokens": 32}
            final_response = post_json(base + "/chat/completions", continuation, api_key=api_key, timeout=max(timeout, 30.0)); final_choices = final_response.get("choices") or []
            final_text = str((final_choices[0].get("message") or {}).get("content") or "") if final_choices else ""
            result["tool_roundtrip_response"] = final_text; result["tool_roundtrip_completed"] = "OUTERRAM_TOOL_OK" in final_text
    return result


def benchmark_server(base_url: str, *, prompt: str, model: str | None = None, max_tokens: int = 128, api_key: str | None = None, timeout: float = 300.0) -> BenchmarkResult:
    base = base_url.rstrip("/")
    if model is None:
        models = get_json(base + "/models", api_key=api_key, timeout=min(timeout, 30.0)); data = models.get("data") or []; model = data[0].get("id") if data else None
    payload = {"model": model or "local", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens, "temperature": 0, "stream": True, "stream_options": {"include_usage": True}}
    started = time.perf_counter(); first_content_at = None; text_parts: list[str] = []; chunks = 0; usage: dict[str, Any] = {}
    for elapsed, data in iter_sse(base + "/chat/completions", payload, api_key=api_key, timeout=timeout):
        if data == "[DONE]": break
        try: obj = json.loads(data)
        except json.JSONDecodeError: continue
        if obj.get("error"): raise RuntimeError(obj["error"].get("message", "server error"))
        if obj.get("usage"): usage = obj["usage"]
        for choice in obj.get("choices") or []:
            content = (choice.get("delta") or {}).get("content")
            if content:
                if first_content_at is None: first_content_at = elapsed
                text_parts.append(str(content)); chunks += 1
    total = time.perf_counter() - started; completion = usage.get("completion_tokens") if isinstance(usage, dict) else None; prompt_tokens = usage.get("prompt_tokens") if isinstance(usage, dict) else None
    tps = (completion - 1) / (total - first_content_at) if isinstance(completion, int) and completion > 1 and first_content_at is not None and total > first_content_at else None
    text = "".join(text_parts)
    return BenchmarkResult(base, model, round(first_content_at, 4) if first_content_at is not None else None, round(total, 4), completion if isinstance(completion, int) else None, prompt_tokens if isinstance(prompt_tokens, int) else None, round(tps, 3) if tps is not None else None, len(text), chunks, text)


def qualify_server(base_url: str, *, prompt: str, model: str | None = None, max_tokens: int = 128, api_key: str | None = None, timeout: float = 300.0, require_tool_call: bool = True) -> dict[str, Any]:
    probe = probe_server(base_url, api_key=api_key, timeout=min(timeout, 30.0), test_tools=require_tool_call)
    benchmark = benchmark_server(base_url, prompt=prompt, model=model, max_tokens=max_tokens, api_key=api_key, timeout=timeout)
    benchmark_ok = bool(benchmark.ttft_seconds is not None and benchmark.output_chars > 0 and benchmark.chunks > 0 and isinstance(benchmark.prompt_tokens, int) and isinstance(benchmark.completion_tokens, int) and benchmark.completion_tokens > 1 and benchmark.tokens_per_second is not None and benchmark.tokens_per_second > 0)
    probe_ok = bool(probe.get("healthy") and probe.get("chat_completed") and probe.get("response_ok")); tool_ok = True if not require_tool_call else bool(probe.get("tool_call_completed") is True and probe.get("tool_roundtrip_completed") is True)
    return {"qualified": bool(probe_ok and tool_ok and benchmark_ok), "require_tool_call": require_tool_call, "probe": probe, "benchmark": benchmark.to_dict(), "gates": {"health_and_marker": probe_ok, "structured_tool_call_roundtrip": tool_ok, "streaming_benchmark": benchmark_ok}}
