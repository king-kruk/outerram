import pytest

import outerram.launch as launch
from outerram.launch import build_launch_spec, executable_available, execute
from outerram.adapters.base import LaunchSpec
from outerram.types import RuntimePlan, Strategy


def plan(strategy):
    return RuntimePlan(strategy=strategy, runtime="x", total_memory_gib=16, reserved_memory_gib=4, resident_budget_gib=12, weight_size_gib=20, expert_budget_gib=6 if strategy is Strategy.MOE_STREAM else None, reason="test")


def test_resident_server_command():
    spec = build_launch_spec(plan(Strategy.RESIDENT), model="m", port=9000)
    assert spec.argv[:3] == ("mlx_lm.server", "--model", "m") and "9000" in spec.argv


def test_dense_stream_command():
    spec = build_launch_spec(plan(Strategy.DENSE_STREAM), model="m")
    assert "outerram.dense_server" in spec.argv and "--ram" in spec.argv


def test_moe_stream_command():
    spec = build_launch_spec(plan(Strategy.MOE_STREAM), model="/m", streamlx_home="/opt/streamlx")
    assert spec.argv[1] == "/opt/streamlx/examples/serve.py" and "6.0" in spec.argv
    assert spec.required_paths == ("/opt/streamlx/examples/serve.py",)


def test_dense_api_key_is_environment_only_and_redacted():
    spec = build_launch_spec(plan(Strategy.DENSE_STREAM), model="m", api_key="super-secret")
    assert "super-secret" not in spec.argv
    assert dict(spec.env)["OUTERRAM_API_KEY"] == "super-secret"
    rendered = spec.shell()
    assert "super-secret" not in rendered and "OUTERRAM_API_KEY=<redacted>" in rendered


def test_executable_available_rejects_missing_required_script(tmp_path):
    spec = LaunchSpec(argv=("python", "missing.py"), install_hint="x", description="x", required_paths=(str(tmp_path / "missing.py"),))
    assert executable_available(spec) is False


def test_launch_rejects_invalid_port_and_host():
    current_plan = RuntimePlan(Strategy.RESIDENT, "mlx-lm", 16, 4, 12, 8, None, "test")
    with pytest.raises(ValueError, match="port"): build_launch_spec(current_plan, model="/m", port=0)
    with pytest.raises(ValueError, match="port"): build_launch_spec(current_plan, model="/m", port=70000)
    with pytest.raises(ValueError, match="host"): build_launch_spec(current_plan, model="/m", host="bad host")


def test_launch_shell_never_leaks_environment_secret():
    secret = "super secret;$(touch /tmp/nope)"
    spec = LaunchSpec(argv=("python", "server.py"), install_hint="x", description="x", env=(("API_KEY", secret),))
    rendered = spec.shell()
    assert secret not in rendered and "API_KEY=<redacted>" in rendered


def test_execute_replaces_outerram_process_on_posix(monkeypatch):
    spec = LaunchSpec(
        argv=("runtime-bin", "--serve"),
        install_hint="x",
        description="x",
        env=(("OUTERRAM_TEST_TOKEN", "secret"),),
    )
    captured = {}

    monkeypatch.setattr(launch, "_supports_exec_replace", lambda: True)

    def fake_execvpe(executable, argv, env):
        captured.update(executable=executable, argv=argv, token=env.get("OUTERRAM_TEST_TOKEN"))
        raise OSError("exec intercepted")

    monkeypatch.setattr(launch.os, "execvpe", fake_execvpe)
    with pytest.raises(OSError, match="exec intercepted"):
        execute(spec)

    assert captured == {
        "executable": "runtime-bin",
        "argv": ["runtime-bin", "--serve"],
        "token": "secret",
    }


def test_execute_uses_subprocess_only_without_exec_support(monkeypatch):
    spec = LaunchSpec(argv=("runtime-bin",), install_hint="x", description="x")
    monkeypatch.setattr(launch, "_supports_exec_replace", lambda: False)

    class Result:
        returncode = 17

    captured = {}

    def fake_run(argv, *, check, env):
        captured.update(argv=argv, check=check, env=env)
        return Result()

    monkeypatch.setattr(launch.subprocess, "run", fake_run)
    assert execute(spec) == 17
    assert captured["argv"] == ("runtime-bin",)
    assert captured["check"] is False
