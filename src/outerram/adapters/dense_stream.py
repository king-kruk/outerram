from __future__ import annotations

import sys

from .base import Adapter, LaunchSpec


class DenseStreamAdapter(Adapter):
    name = "mlx-flash"

    def build(
        self,
        *,
        model: str,
        host: str,
        port: int,
        resident_budget_gib: float | None = None,
        api_key: str | None = None,
        allow_unauthenticated_remote: bool = False,
        **kwargs,
    ) -> LaunchSpec:
        ram = resident_budget_gib if resident_budget_gib is not None else 4.0
        argv = [
            sys.executable, "-m", "outerram.dense_server",
            "--model", model, "--host", host, "--port", str(port), "--ram", f"{ram:.1f}",
        ]
        env: list[tuple[str, str]] = []
        if api_key:
            # OUTERRAM_API_KEY is canonical. Populate the legacy variable for
            # the one-release private-test migration window only.
            env.append(("OUTERRAM_API_KEY", api_key))
            env.append(("STRETCHMLX_API_KEY", api_key))
        if allow_unauthenticated_remote:
            argv.append("--allow-unauthenticated-remote")
        return LaunchSpec(
            argv=tuple(argv),
            install_hint="outerram bootstrap <model>",
            description="OpenAI-compatible dense out-of-core MLX weight streaming server",
            env=tuple(env),
        )
