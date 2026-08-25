import json
import threading
import urllib.error
import urllib.request

import pytest
from http.server import ThreadingHTTPServer

from outerram.dense_server import DenseHandler


class FakeTokenizer:
    def encode(self, text): return text.split()


class FakeRuntime:
    model_name = "fake-model"
    tokenizer = FakeTokenizer()
    def stream(self, messages, *, max_tokens, temperature, tools=None):
        assert messages[0]["content"] == "hello"
        yield "hello "; yield "world"
    def usage(self, messages, text, tools=None): return {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}


def start_server(api_key=None):
    handler = type("FakeDenseHandler", (DenseHandler,), {"runtime": FakeRuntime(), "api_key": api_key})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    return server, thread


def request_json(url, payload=None, api_key=None):
    headers = {"Content-Type": "application/json"}
    if api_key: headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, headers=headers) if payload is None else urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=3) as resp: return resp.status, json.loads(resp.read())


def test_health_and_models():
    server, thread = start_server()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        status, body = request_json(base + "/health"); assert status == 200 and body["runtime"] == "mlx-flash"
        status, body = request_json(base + "/v1/models"); assert body["data"][0]["id"] == "fake-model"
    finally: server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_chat_completion_non_streaming_has_usage():
    server, thread = start_server()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        status, body = request_json(base + "/v1/chat/completions", {"model": "fake-model", "messages": [{"role": "user", "content": "hello"}], "stream": False, "max_tokens": 16})
        assert status == 200 and body["choices"][0]["message"]["content"] == "hello world"
        assert body["choices"][0]["finish_reason"] == "stop" and body["usage"]["completion_tokens"] == 2
    finally: server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_chat_completion_streaming_sse_and_usage():
    server, thread = start_server()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps({"messages": [{"role": "user", "content": "hello"}], "stream": True, "max_tokens": 16, "stream_options": {"include_usage": True}}).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=3) as resp: raw = resp.read().decode()
        assert "hello " in raw and "world" in raw and '"usage"' in raw and "data: [DONE]" in raw
    finally: server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_api_key_protects_v1_routes_but_health_remains_available():
    server, thread = start_server(api_key="secret")
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        assert request_json(base + "/health")[0] == 200
        with pytest.raises(urllib.error.HTTPError) as exc_info: request_json(base + "/v1/models")
        assert exc_info.value.code == 401
        assert request_json(base + "/v1/models", api_key="secret")[0] == 200
    finally: server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_rejects_invalid_max_tokens():
    server, thread = start_server()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with pytest.raises(urllib.error.HTTPError) as exc_info: request_json(base + "/v1/chat/completions", {"messages": [{"role": "user", "content": "hello"}], "max_tokens": 0})
        assert exc_info.value.code == 400
    finally: server.shutdown(); server.server_close(); thread.join(timeout=2)


class ToolTokenizer:
    tool_call_start = "<tool_call>"; tool_call_end = "</tool_call>"
    def encode(self, text): return text.split()
    def tool_parser(self, text, tools=None): return json.loads(text)


class ToolRuntime(FakeRuntime):
    tokenizer = ToolTokenizer()
    def stream(self, messages, *, max_tokens, temperature, tools=None):
        assert tools and tools[0]["function"]["name"] == "read_file"
        yield '<tool_call>{"name":"read_file","arguments":{"path":"main.py"}}</tool_call>'


def _tool_server(runtime):
    handler = type("ToolDenseHandler", (DenseHandler,), {"runtime": runtime, "api_key": None})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    return server, thread


def test_tool_call_http_returns_openai_tool_calls():
    server, thread = _tool_server(ToolRuntime())
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        _, body = request_json(base + "/v1/chat/completions", {"messages": [{"role": "user", "content": "hello"}], "tools": [{"type": "function", "function": {"name": "read_file", "parameters": {"type": "object"}}}], "max_tokens": 16})
        choice = body["choices"][0]; assert choice["finish_reason"] == "tool_calls"
        call = choice["message"]["tool_calls"][0]; assert call["function"]["name"] == "read_file"
        assert json.loads(call["function"]["arguments"])["path"] == "main.py"
    finally: server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_invalid_stream_options_returns_400():
    server, thread = start_server()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps({"messages": [{"role": "user", "content": "hello"}], "stream_options": ["not", "an", "object"]}).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with pytest.raises(urllib.error.HTTPError) as exc_info: urllib.request.urlopen(req, timeout=2)
        assert exc_info.value.code == 400 and json.loads(exc_info.value.read())["error"]["type"] == "invalid_request_error"
    finally: server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_invalid_message_shape_returns_400():
    server, thread = start_server()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps({"messages": ["bad"]}).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with pytest.raises(urllib.error.HTTPError) as exc_info: urllib.request.urlopen(req, timeout=2)
        assert exc_info.value.code == 400
    finally: server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_tool_call_streaming_returns_structured_sse_and_done():
    server, thread = _tool_server(ToolRuntime())
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps({"messages": [{"role": "user", "content": "hello"}], "tools": [{"type": "function", "function": {"name": "read_file", "parameters": {"type": "object"}}}], "stream": True, "stream_options": {"include_usage": True}, "max_tokens": 16}).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=3) as resp: raw = resp.read().decode()
        assert '"tool_calls"' in raw and '"read_file"' in raw and '"finish_reason": "tool_calls"' in raw and "data: [DONE]" in raw
    finally: server.shutdown(); server.server_close(); thread.join(timeout=2)


class RoundtripToolRuntime(FakeRuntime):
    tokenizer = ToolTokenizer()
    def stream(self, messages, *, max_tokens, temperature, tools=None):
        if any(message.get("role") == "tool" for message in messages):
            assert any(message.get("role") == "assistant" and message.get("tool_calls") for message in messages)
            assert any(message.get("role") == "tool" and message.get("content") == "5" for message in messages)
            yield "OUTERRAM_TOOL_OK"; return
        assert tools and tools[0]["function"]["name"] == "add_numbers"
        yield '<tool_call>{"name":"add_numbers","arguments":{"a":2,"b":3}}</tool_call>'


def test_dense_http_tool_call_roundtrip_continues_after_tool_result():
    server, thread = _tool_server(RoundtripToolRuntime())
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        tools = [{"type": "function", "function": {"name": "add_numbers", "parameters": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}}}}]
        _, first = request_json(base + "/v1/chat/completions", {"messages": [{"role": "user", "content": "add 2 and 3"}], "tools": tools, "max_tokens": 16})
        call = first["choices"][0]["message"]["tool_calls"][0]
        _, second = request_json(base + "/v1/chat/completions", {"messages": [{"role": "user", "content": "add 2 and 3"}, {"role": "assistant", "content": None, "tool_calls": [call]}, {"role": "tool", "tool_call_id": call["id"], "content": "5"}], "tools": tools, "max_tokens": 16})
        assert second["choices"][0]["message"]["content"] == "OUTERRAM_TOOL_OK"
        assert second["choices"][0]["finish_reason"] == "stop"
    finally: server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_tool_choice_none_does_not_expose_tools_to_runtime():
    class NoToolRuntime(FakeRuntime):
        def stream(self, messages, *, max_tokens, temperature, tools=None): assert tools is None; yield "plain"
    server, thread = _tool_server(NoToolRuntime())
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        _, body = request_json(base + "/v1/chat/completions", {"messages": [{"role": "user", "content": "hello"}], "tools": [{"type": "function", "function": {"name": "read_file", "parameters": {"type": "object"}}}], "tool_choice": "none", "max_tokens": 16})
        assert body["choices"][0]["message"]["content"] == "plain" and "tool_calls" not in body["choices"][0]["message"]
    finally: server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_unsupported_required_tool_choice_fails_closed():
    server, thread = start_server()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps({"messages": [{"role": "user", "content": "hello"}], "tools": [{"type": "function", "function": {"name": "x", "parameters": {"type": "object"}}}], "tool_choice": "required"}).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with pytest.raises(urllib.error.HTTPError) as exc_info: urllib.request.urlopen(req, timeout=2)
        assert exc_info.value.code == 400
    finally: server.shutdown(); server.server_close(); thread.join(timeout=2)
