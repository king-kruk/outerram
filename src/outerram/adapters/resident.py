from __future__ import annotations

from .base import Adapter, LaunchSpec


class ResidentAdapter(Adapter):
    name = "mlx-lm"

    def build(self, *, model: str, host: str, port: int, **kwargs) -> LaunchSpec:
        return LaunchSpec(
            argv=("mlx_lm.server", "--model", model, "--host", host, "--port", str(port)),
            install_hint="python -m pip install -U mlx-lm",
            description="Resident MLX-LM OpenAI-compatible server",
        )
