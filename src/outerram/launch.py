from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from .adapters import DenseStreamAdapter, MoeStreamAdapter, ResidentAdapter
from .adapters.base import LaunchSpec
from .types import RuntimePlan, Strategy


def build_launch_spec(
    plan: RuntimePlan,
    *,
    model: str,
    host: str = "127.0.0.1",
    port: int = 8080,
    streamlx_home: str | None = None,
    api_key: str | None = None,
    allow_unauthenticated_remote: bool = False,
) -> LaunchSpec:
    if not 1 <= int(port) <= 65535:
        raise ValueError("port must be between 1 and 65535")
    if not host or any(ch.isspace() for ch in host):
        raise ValueError("host must be a non-empty hostname/address without whitespace")
    if plan.strategy == Strategy.RESIDENT:
        return ResidentAdapter().build(model=model, host=host, port=port)
    if plan.strategy == Strategy.DENSE_STREAM:
        return DenseStreamAdapter().build(
            model=model,
            host=host,
            port=port,
            resident_budget_gib=max(1.0, plan.resident_budget_gib - 1.0),
            api_key=api_key,
            allow_unauthenticated_remote=allow_unauthenticated_remote,
        )
    return MoeStreamAdapter().build(
        model=model,
        host=host,
        port=port,
        expert_budget_gib=plan.expert_budget_gib,
        streamlx_home=streamlx_home,
    )


def executable_available(spec: LaunchSpec) -> bool:
    exe = spec.argv[0]
    if exe.startswith("/"):
        executable_ok = Path(exe).is_file()
    else:
        executable_ok = shutil.which(exe) is not None
    if not executable_ok:
        return False
    return all(Path(path).is_file() for path in spec.required_paths)


def _supports_exec_replace() -> bool:
    """Whether this host can replace the orchestrator with the runtime process."""
    return os.name == "posix"


def execute(spec: LaunchSpec) -> int:
    """Launch a runtime without keeping an avoidable OuterRAM parent resident.

    On macOS/Linux, replace the current process with the selected runtime. This
    preserves the PID/signal model and removes the CLI/planner interpreter from
    the steady-state inference memory footprint. Windows is planning-only today,
    but keeps the subprocess fallback for portability and tests.
    """
    env = os.environ.copy()
    env.update(dict(spec.env))

    if _supports_exec_replace():
        # cmd_serve prints the selected strategy/command immediately before this
        # handoff. Flush explicitly because exec does not run Python shutdown
        # handlers or flush buffered streams.
        sys.stdout.flush()
        sys.stderr.flush()
        os.execvpe(spec.argv[0], list(spec.argv), env)
        raise AssertionError("os.execvpe returned unexpectedly")

    proc = subprocess.run(spec.argv, check=False, env=env)
    return int(proc.returncode)
