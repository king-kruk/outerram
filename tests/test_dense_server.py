import json

from outerram.dense_server import _chat_prompt, _normalize_tool_calls


class TemplateTokenizer:
    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True, tools=None):
        assert tokenize is False
        assert add_generation_prompt is True
        if tools:
            return "TOOLS:" + tools[0]["function"]["name"]
        return "TEMPLATE:" + messages[0]["content"]


class PlainTokenizer:
    pass


class ToolTokenizer:
    tool_call_start = "<tool_call>"
    tool_call_end = "</tool_call>"
    def tool_parser(self, text, tools=None):
        return json.loads(text)


def test_chat_prompt_uses_template():
    assert _chat_prompt(TemplateTokenizer(), [{"role": "user", "content": "hello"}]) == "TEMPLATE:hello"


def test_chat_prompt_passes_tools_to_template():
    tools = [{"type": "function", "function": {"name": "read_file", "parameters": {}}}]
    assert _chat_prompt(TemplateTokenizer(), [{"role": "user", "content": "hello"}], tools) == "TOOLS:read_file"


def test_chat_prompt_fallback():
    out = _chat_prompt(PlainTokenizer(), [{"role": "user", "content": "hello"}])
    assert "user: hello" in out and out.endswith("assistant:")


def test_tool_call_parser_returns_openai_shape_and_hides_control_tags():
    raw = 'before<tool_call>{"name":"read_file","arguments":{"path":"a.py"}}</tool_call>after'
    content, calls = _normalize_tool_calls(ToolTokenizer(), raw, [])
    assert content == "beforeafter"
    assert calls[0]["type"] == "function" and calls[0]["function"]["name"] == "read_file"
    assert json.loads(calls[0]["function"]["arguments"])["path"] == "a.py"


def test_chat_prompt_fallback_preserves_tool_roundtrip_metadata():
    messages = [
        {"role": "user", "content": "calculate"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "add_numbers", "arguments": "{\"a\":2,\"b\":3}"}}]},
        {"role": "tool", "tool_call_id": "call_1", "content": "5"},
    ]
    prompt = _chat_prompt(PlainTokenizer(), messages, tools=[{"type": "function", "function": {"name": "add_numbers", "parameters": {"type": "object"}}}])
    assert "assistant tool_calls:" in prompt and '"name": "add_numbers"' in prompt and "tool[call_1]: 5" in prompt
