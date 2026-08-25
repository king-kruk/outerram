from __future__ import annotations

import json
import subprocess
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import outerram.model as model_mod
from outerram.bootstrap import verify_streamlx_checkout
from outerram.dense_server import DenseHandler


def test_model_fetch_does_not_download_repository_python_code(tmp_path, monkeypatch):
    captured = {}
    def fake_snapshot_download(**kwargs): captured.update(kwargs); return str(tmp_path)
    monkeypatch.setattr(model_mod, "snapshot_download", fake_snapshot_download)
    model_mod.fetch_model("owner/model", tmp_path, revision="abc123", weight_files=("model.safetensors",), declared_license="mit")
    assert "model.safetensors" in captured["allow_patterns"]
    assert "tokenizer.json" in captured["allow_patterns"]
    assert "*.py" not in captured["allow_patterns"]


def _git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=True)


def test_streamlx_checkout_rejects_redirected_origin(tmp_path):
    home = tmp_path / "streamlx"; _git("init", str(home)); _git("remote", "add", "origin", "https://example.invalid/streamlx.git", cwd=home)
    with pytest.raises(RuntimeError, match="unexpected origin"): verify_streamlx_checkout(home)


def test_streamlx_checkout_rejects_local_modifications(tmp_path):
    home = tmp_path / "streamlx"; _git("init", str(home)); _git("remote", "add", "origin", "https://github.com/srcterm/streamlx.git", cwd=home)
    (home / "unexpected.py").write_text("print('modified')\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="modified streamlx checkout"): verify_streamlx_checkout(home)


class ExplodingRuntime:
    model_name = "fake"; tokenizer = object()
    def stream(self, *args, **kwargs): raise RuntimeError("/Users/example/private/model secret-internal-detail")
    def usage(self, *args, **kwargs): return None


def test_dense_http_redacts_internal_exception_details():
    handler = type("ExplodingDenseHandler", (DenseHandler,), {"runtime": ExplodingRuntime(), "api_key": None})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler); thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        request = urllib.request.Request(f"http://127.0.0.1:{server.server_port}/v1/chat/completions", data=json.dumps({"messages": [{"role": "user", "content": "hello"}]}).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with pytest.raises(urllib.error.HTTPError) as exc_info: urllib.request.urlopen(request, timeout=3)
        body = json.loads(exc_info.value.read()); rendered = json.dumps(body)
        assert exc_info.value.code == 500 and body["error"]["message"] == "internal server error"
        assert "private/model" not in rendered and "secret-internal-detail" not in rendered
        assert body["error"]["request_id"].startswith("chatcmpl-")
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_dense_http_rejects_excessive_completion_token_request():
    class QuietRuntime:
        model_name = "fake"; tokenizer = object()
        def stream(self, *args, **kwargs): yield "ok"
        def usage(self, *args, **kwargs): return None
    handler = type("QuietDenseHandler", (DenseHandler,), {"runtime": QuietRuntime(), "api_key": None})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler); thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        request = urllib.request.Request(f"http://127.0.0.1:{server.server_port}/v1/chat/completions", data=json.dumps({"messages": [{"role": "user", "content": "hello"}], "max_tokens": 32769}).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with pytest.raises(urllib.error.HTTPError) as exc_info: urllib.request.urlopen(request, timeout=3)
        assert exc_info.value.code == 400
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
