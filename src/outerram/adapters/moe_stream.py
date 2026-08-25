from __future__ import annotations

import os
import sys
from pathlib import Path

from .base import Adapter, LaunchSpec


class MoeStreamAdapter(Adapter):
    name = "streamlx"

    def build(self, *, model: str, host: str, port: int, expert_budget_gib: float | None = None, streamlx_home: str | None = None, **kwargs) -> LaunchSpec:
        home = streamlx_home or os.environ.get("STREAMLX_HOME")
        if not home:
            home = str(Path.home() / ".cache" / "outerram" / "streamlx")
        serve = str(Path(home).expanduser() / "examples" / "serve.py")
        budget = expert_budget_gib if expert_budget_gib is not None else 6.0
        return LaunchSpec(
            argv=(sys.executable, serve, "--model", model, "--budget-gib", f"{budget:.1f}", "--host", host, "--port", str(port)),
            install_hint="outerram bootstrap <model>",
            description="Exact MoE expert SSD streaming with MLX",
            required_paths=(serve,),
        )
