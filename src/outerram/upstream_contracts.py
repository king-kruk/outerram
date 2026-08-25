from __future__ import annotations

import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Callable

from .runtime_pins import MLX_FLASH_REF, MLX_LM_REF, STREAMLX_REF


@dataclass(frozen=True)
class UpstreamContract:
    name: str
    url: str
    required_markers: tuple[str, ...]
    purpose: str


@dataclass(frozen=True)
class UpstreamContractResult:
    name: str
    url: str
    ok: bool
    missing_markers: tuple[str, ...]
    error: str | None
    purpose: str

    def to_dict(self):
        return asdict(self)


def contracts() -> tuple[UpstreamContract, ...]:
    raw = "https://raw.githubusercontent.com"
    return (
        UpstreamContract("mlx-lm-server", f"{raw}/ml-explore/mlx-lm/{MLX_LM_REF}/mlx_lm/server.py", ('class ToolCallFormatter', '"/v1/models"', '"/health"', '"--host"', '"--port"'), "resident/MoE OpenAI server and tool-call protocol surface"),
        UpstreamContract("mlx-flash-manager", f"{raw}/matt-k-wong/mlx-flash/{MLX_FLASH_REF}/mlx_flash/manager.py", ("class FlashManager", "def load(", "lazy=True", "FlashEngine("), "dense-stream model loading contract"),
        UpstreamContract("mlx-flash-config", f"{raw}/matt-k-wong/mlx-flash/{MLX_FLASH_REF}/mlx_flash/config.py", ("class FlashConfig", "ram_budget_gb", "def validate("), "dense-stream RAM budget contract"),
        UpstreamContract("mlx-flash-engine", f"{raw}/matt-k-wong/mlx-flash/{MLX_FLASH_REF}/mlx_flash/engine/engine.py", ("class FlashEngine", "def stream_generate("), "dense-stream generation contract"),
        UpstreamContract("streamlx-server", f"{raw}/srcterm/streamlx/{STREAMLX_REF}/examples/serve.py", ('--budget-gib', '--prompt-cache-gib', 'StreamingModelProvider', 'srv.main()'), "MoE expert-stream server contract"),
        UpstreamContract("mlx-lm-license", f"{raw}/ml-explore/mlx-lm/{MLX_LM_REF}/LICENSE", ("MIT License",), "third-party license presence"),
        UpstreamContract("mlx-flash-license", f"{raw}/matt-k-wong/mlx-flash/{MLX_FLASH_REF}/LICENSE", ("MIT License",), "third-party license presence"),
        UpstreamContract("streamlx-license", f"{raw}/srcterm/streamlx/{STREAMLX_REF}/LICENSE", ("MIT License",), "third-party license presence"),
    )


def fetch_text(url: str, *, timeout: float = 20.0, retries: int = 2) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "OuterRAM-upstream-contract-check"})
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if getattr(response, "status", 200) != 200:
                    raise RuntimeError(f"HTTP {response.status}")
                return response.read().decode("utf-8")
        except (OSError, UnicodeDecodeError, urllib.error.URLError, RuntimeError) as exc:
            last = exc
            if attempt < retries:
                time.sleep(0.25 * (attempt + 1))
    raise RuntimeError(str(last) if last else "upstream fetch failed")


def verify_upstream_contracts(*, fetcher: Callable[[str], str] | None = None) -> dict[str, object]:
    getter = fetcher or (lambda url: fetch_text(url))
    results: list[UpstreamContractResult] = []
    for contract in contracts():
        try:
            text = getter(contract.url)
            missing = tuple(marker for marker in contract.required_markers if marker not in text)
            results.append(UpstreamContractResult(contract.name, contract.url, not missing, missing, None, contract.purpose))
        except Exception as exc:
            results.append(UpstreamContractResult(contract.name, contract.url, False, (), str(exc), contract.purpose))
    return {
        "ok": all(result.ok for result in results),
        "pins": {"mlx-lm": MLX_LM_REF, "mlx-flash": MLX_FLASH_REF, "streamlx": STREAMLX_REF},
        "contracts": [result.to_dict() for result in results],
    }
