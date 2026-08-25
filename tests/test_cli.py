from types import SimpleNamespace

import outerram.cli as cli
from outerram.cli_parser import build_parser
from outerram.types import (
    CheckpointKind,
    CompatibilityCheck,
    CompatibilityReport,
    MachineInfo,
    ModelInfo,
    ModelSource,
    RuntimePlan,
    Strategy,
)


def _machine():
    return MachineInfo("Darwin", "arm64", 16.0, True, free_disk_gib=100, python_version="3.12.5", os_version="14.0")


def _model():
    return ModelInfo(
        model="m", local_path="/m", architecture="A", model_type="qwen3_8",
        weight_size_gib=10.0, is_moe=False, num_experts=None, top_k=None, quant_bits=3,
        source=ModelSource.LOCAL, checkpoint_kind=CheckpointKind.SAFETENSORS,
        weight_file_count=1, quantized=True,
    )


def _plan():
    return RuntimePlan(Strategy.RESIDENT, "mlx-lm", 16, 4, 12, 10, None, "test")


def _compat():
    return CompatibilityReport(True, (CompatibilityCheck("ok", True, "error", "ok"),))


def test_bootstrap_parser_defaults_to_protecting_base_python():
    args = build_parser().parse_args(["bootstrap", "model"])
    assert args.allow_system_python is False
    override = build_parser().parse_args(["bootstrap", "model", "--allow-system-python"])
    assert override.allow_system_python is True


def test_bootstrap_refuses_base_python_by_default(monkeypatch, capsys):
    called = {"run": False}
    monkeypatch.setattr(cli, "_make_plan", lambda args: (_machine(), _model(), _plan()))
    monkeypatch.setattr(cli, "_isolated_python_environment", lambda: False)
    monkeypatch.setattr(cli, "run_bootstrap", lambda commands: called.__setitem__("run", True) or 0)
    args = SimpleNamespace(streamlx_home=None, latest=False, dry_run=False, allow_system_python=False)
    assert cli.cmd_bootstrap(args) == 3
    assert called["run"] is False
    assert "Refusing runtime bootstrap outside an isolated Python environment" in capsys.readouterr().err


def test_bootstrap_system_python_override_is_explicit(monkeypatch):
    captured = {}
    monkeypatch.setattr(cli, "_make_plan", lambda args: (_machine(), _model(), _plan()))
    monkeypatch.setattr(cli, "_isolated_python_environment", lambda: False)
    monkeypatch.setattr(cli.shutil, "which", lambda executable: "/usr/bin/git" if executable == "git" else None)
    monkeypatch.setattr(cli, "run_bootstrap", lambda commands: (captured.update(commands=commands), 0)[1])
    args = SimpleNamespace(streamlx_home=None, latest=False, dry_run=False, allow_system_python=True)
    result = cli.cmd_bootstrap(args)
    assert result == 0
    assert captured["commands"]


def test_ready_is_fail_closed_on_unpinned_runtime(monkeypatch):
    monkeypatch.setattr(cli, "_make_plan", lambda args: (_machine(), _model(), _plan()))
    monkeypatch.setattr(cli, "assess_compatibility", lambda *args, **kwargs: _compat())
    monkeypatch.setattr(cli, "runtime_status", lambda *args, **kwargs: {"installed": True, "reproducible": False})
    args = SimpleNamespace(streamlx_home=None, json=True, allow_unpinned=False)
    assert cli.cmd_ready(args) == 4


def test_ready_can_explicitly_allow_unpinned_runtime(monkeypatch):
    monkeypatch.setattr(cli, "_make_plan", lambda args: (_machine(), _model(), _plan()))
    monkeypatch.setattr(cli, "assess_compatibility", lambda *args, **kwargs: _compat())
    monkeypatch.setattr(cli, "runtime_status", lambda *args, **kwargs: {"installed": True, "reproducible": False})
    args = SimpleNamespace(streamlx_home=None, json=True, allow_unpinned=True)
    assert cli.cmd_ready(args) == 0


def test_probe_prefers_outerram_api_key(monkeypatch):
    captured = {}
    monkeypatch.setenv("OUTERRAM_API_KEY", "new-key")
    monkeypatch.setenv("STRETCHMLX_API_KEY", "legacy-key")
    def fake_probe(base_url, *, api_key, timeout, test_tools):
        captured.update(base_url=base_url, api_key=api_key, timeout=timeout, test_tools=test_tools)
        return {"healthy": True, "chat_completed": True, "response_ok": True, "tool_call_completed": None}
    monkeypatch.setattr(cli, "probe_server", fake_probe)
    args = SimpleNamespace(base_url="http://127.0.0.1:8080/v1", api_key=None, timeout=2.0, tool_call=False, json=True)
    assert cli.cmd_probe(args) == 0
    assert captured["api_key"] == "new-key"


def test_probe_keeps_legacy_api_key_fallback(monkeypatch):
    captured = {}
    monkeypatch.delenv("OUTERRAM_API_KEY", raising=False)
    monkeypatch.setenv("STRETCHMLX_API_KEY", "legacy-key")
    def fake_probe(base_url, *, api_key, timeout, test_tools):
        captured["api_key"] = api_key
        return {"healthy": True, "chat_completed": True, "response_ok": True, "tool_call_completed": None}
    monkeypatch.setattr(cli, "probe_server", fake_probe)
    args = SimpleNamespace(base_url="http://127.0.0.1:8080/v1", api_key=None, timeout=2.0, tool_call=False, json=True)
    assert cli.cmd_probe(args) == 0
    assert captured["api_key"] == "legacy-key"


def test_benchmark_uses_outerram_api_key_from_environment(monkeypatch):
    captured = {}
    monkeypatch.setenv("OUTERRAM_API_KEY", "from-env")
    class Result:
        ttft_seconds = 0.1; output_chars = 5; chunks = 1; prompt_tokens = 3; completion_tokens = 4; tokens_per_second = 10.0
        def to_dict(self): return {"ok": True}
    def fake_benchmark(base_url, **kwargs):
        captured.update(base_url=base_url, **kwargs); return Result()
    monkeypatch.setattr(cli, "benchmark_server", fake_benchmark)
    args = SimpleNamespace(base_url="http://127.0.0.1:8080/v1", prompt="x", model=None, max_tokens=8, api_key=None, timeout=2.0, json=True)
    assert cli.cmd_benchmark(args) == 0
    assert captured["api_key"] == "from-env"


def test_fetch_path_only_for_existing_local_model(monkeypatch, capsys):
    monkeypatch.setattr(cli, "inspect_model", lambda model: _model())
    args = SimpleNamespace(model="/m", path_only=True, json=False, dir=None, force=False)
    assert cli.cmd_fetch(args) == 0
    assert capsys.readouterr().out.strip() == "/m"


def test_benchmark_fails_when_no_content_was_generated(monkeypatch):
    class Result:
        ttft_seconds = None; output_chars = 0; chunks = 0; prompt_tokens = None; completion_tokens = None; tokens_per_second = None
        def to_dict(self): return {"ttft_seconds": None, "output_chars": 0, "chunks": 0}
    monkeypatch.setattr(cli, "benchmark_server", lambda *args, **kwargs: Result())
    args = SimpleNamespace(base_url="http://127.0.0.1:8080/v1", prompt="x", model=None, max_tokens=8, api_key=None, timeout=2.0, json=True)
    assert cli.cmd_benchmark(args) == 7


def test_qualify_fails_closed_when_a_gate_fails(monkeypatch):
    monkeypatch.setattr(cli, "qualify_server", lambda *args, **kwargs: {"qualified": False, "gates": {"health_and_marker": True, "structured_tool_call_roundtrip": False, "streaming_benchmark": True}})
    args = SimpleNamespace(base_url="http://127.0.0.1:8080/v1", prompt="x", model=None, max_tokens=8, api_key=None, timeout=2.0, skip_tool_call=False, checkpoint=None, disk_path=None, output=None, json=True)
    assert cli.cmd_qualify(args) == 8


def test_qualify_with_checkpoint_binds_api_to_environment(monkeypatch, capsys):
    monkeypatch.setattr(cli, "qualify_server", lambda *args, **kwargs: {"qualified": True, "gates": {"health_and_marker": True, "structured_tool_call_roundtrip": True, "streaming_benchmark": True}})
    monkeypatch.setattr(cli, "detect_machine", lambda: _machine())
    monkeypatch.setattr(cli, "inspect_model", lambda model: _model())
    monkeypatch.setattr(cli, "plan_runtime", lambda *args, **kwargs: _plan())
    monkeypatch.setattr(cli, "assess_compatibility", lambda *args, **kwargs: _compat())
    monkeypatch.setattr(cli, "runtime_status", lambda *args, **kwargs: {"installed": True, "reproducible": True})
    args = SimpleNamespace(base_url="http://127.0.0.1:8080/v1", prompt="x", model=None, max_tokens=8, api_key=None, timeout=2.0, skip_tool_call=False, checkpoint="/m", reserve_gib=None, strategy=None, streamlx_home=None, allow_unpinned=False, disk_path=None, output=None, json=True)
    assert cli.cmd_qualify(args) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["qualification_scope"] == "api+environment"
    assert payload["api_qualified"] is True and payload["environment_ready"] is True and payload["qualified"] is True


def test_qualify_checkpoint_fails_when_runtime_is_unpinned(monkeypatch, capsys):
    monkeypatch.setattr(cli, "qualify_server", lambda *args, **kwargs: {"qualified": True, "gates": {}})
    monkeypatch.setattr(cli, "detect_machine", lambda: _machine())
    monkeypatch.setattr(cli, "inspect_model", lambda model: _model())
    monkeypatch.setattr(cli, "plan_runtime", lambda *args, **kwargs: _plan())
    monkeypatch.setattr(cli, "assess_compatibility", lambda *args, **kwargs: _compat())
    monkeypatch.setattr(cli, "runtime_status", lambda *args, **kwargs: {"installed": True, "reproducible": False})
    args = SimpleNamespace(base_url="http://127.0.0.1:8080/v1", prompt="x", model=None, max_tokens=8, api_key=None, timeout=2.0, skip_tool_call=False, checkpoint="/m", reserve_gib=None, strategy=None, streamlx_home=None, allow_unpinned=False, disk_path=None, output=None, json=True)
    assert cli.cmd_qualify(args) == 8


def test_benchmark_fails_when_usage_is_missing_even_if_text_streamed(monkeypatch):
    class Result:
        ttft_seconds = 0.1; output_chars = 20; chunks = 3; prompt_tokens = None; completion_tokens = None; tokens_per_second = None
        def to_dict(self): return {"ttft_seconds": 0.1, "output_chars": 20, "chunks": 3}
    monkeypatch.setattr(cli, "benchmark_server", lambda *args, **kwargs: Result())
    args = SimpleNamespace(base_url="http://127.0.0.1:8080/v1", prompt="x", model=None, max_tokens=8, api_key=None, timeout=2.0, json=True)
    assert cli.cmd_benchmark(args) == 7


def test_qualify_can_embed_disk_evidence(monkeypatch, capsys):
    monkeypatch.setattr(cli, "qualify_server", lambda *args, **kwargs: {"qualified": True, "gates": {"health_and_marker": True, "structured_tool_call_roundtrip": True, "streaming_benchmark": True}})
    class DiskResult:
        def to_dict(self): return {"path": "/models", "read_mib_s": 2500.0, "random_read_mib_s": 1800.0, "random_read_iops": 1800.0, "random_read_p95_ms": 0.7}
    captured = {}
    def fake_disk(path, **kwargs): captured.update(path=path, **kwargs); return DiskResult()
    monkeypatch.setattr(cli, "benchmark_disk", fake_disk)
    args = SimpleNamespace(base_url="http://127.0.0.1:8080/v1", prompt="x", model=None, max_tokens=8, api_key=None, timeout=2.0, skip_tool_call=False, checkpoint=None, reserve_gib=None, strategy=None, streamlx_home=None, allow_unpinned=False, disk_path="/models", disk_size_mib=64, disk_chunk_mib=2, disk_random_read_kib=512, disk_random_reads=32, output=None, json=True)
    assert cli.cmd_qualify(args) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["qualified"] is True and payload["disk"]["random_read_p95_ms"] == 0.7
