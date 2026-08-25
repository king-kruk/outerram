from __future__ import annotations

from .runtime_pins import MLX_FLASH_REF, MLX_LM_REF, STREAMLX_REF
from .software import software_report
from .types import RuntimePlan, Strategy


def _pin_state(entry: dict[str, object], expected: str) -> dict[str, object]:
    commit = entry.get("commit")
    entry["expected_commit"] = expected
    entry["pin_match"] = commit == expected if isinstance(commit, str) else None
    return entry


def _matches(entry: dict[str, object]) -> bool:
    return bool(entry.get("installed") and entry.get("pin_match") is True)


def runtime_status(plan: RuntimePlan, *, streamlx_home: str | None = None) -> dict[str, object]:
    report = software_report(streamlx_home=streamlx_home)
    mlx_lm = dict(report["mlx_lm"])

    if plan.strategy == Strategy.RESIDENT:
        entry = _pin_state(mlx_lm, MLX_LM_REF)
        entry.update({"runtime": "mlx-lm", "detail": "Python module mlx_lm", "reproducible": _matches(entry)})
        return entry

    if plan.strategy == Strategy.DENSE_STREAM:
        flash = _pin_state(dict(report["mlx_flash"]), MLX_FLASH_REF)
        mlx_lm = _pin_state(mlx_lm, MLX_LM_REF)
        installed = bool(flash.get("installed") and mlx_lm.get("installed"))
        return {"runtime": "mlx-flash", "installed": installed, "reproducible": bool(installed and _matches(flash) and _matches(mlx_lm)), "mlx_flash": flash, "mlx_lm": mlx_lm, "detail": "mlx_flash + mlx_lm"}

    streamlx = _pin_state(dict(report["streamlx"]), STREAMLX_REF)
    mlx_lm = _pin_state(mlx_lm, MLX_LM_REF)
    installed = bool(streamlx.get("installed") and mlx_lm.get("installed"))
    return {"runtime": "streamlx", "installed": installed, "reproducible": bool(installed and _matches(streamlx) and _matches(mlx_lm)), "streamlx": streamlx, "mlx_lm": mlx_lm, "detail": streamlx.get("home")}
