from __future__ import annotations

import re
from pathlib import Path

from .runtime_pins import MLX_MIN_MACOS_VERSION
from .types import (
    CheckpointKind,
    CompatibilityCheck,
    CompatibilityReport,
    MachineInfo,
    ModelInfo,
    ModelSource,
    RuntimePlan,
    Strategy,
)


def _version_tuple(value: str | None) -> tuple[int, ...] | None:
    if not value:
        return None
    parts = re.findall(r"\d+", value)
    if not parts:
        return None
    try:
        return tuple(int(part) for part in parts[:3])
    except ValueError:
        return None


def _version_at_least(actual: str | None, minimum: str) -> bool | None:
    actual_tuple = _version_tuple(actual)
    minimum_tuple = _version_tuple(minimum)
    if actual_tuple is None or minimum_tuple is None:
        return None
    width = max(len(actual_tuple), len(minimum_tuple))
    actual_tuple = actual_tuple + (0,) * (width - len(actual_tuple))
    minimum_tuple = minimum_tuple + (0,) * (width - len(minimum_tuple))
    return actual_tuple >= minimum_tuple


def macos_runtime_check(machine: MachineInfo) -> CompatibilityCheck:
    if machine.system != "Darwin":
        return CompatibilityCheck(
            name="macos_version", ok=False, severity="error",
            detail="Current execution runtimes require macOS on Apple Silicon.",
            remediation=f"Use an Apple Silicon Mac running macOS {MLX_MIN_MACOS_VERSION} or newer.",
        )
    supported = _version_at_least(machine.os_version, MLX_MIN_MACOS_VERSION)
    if supported is None:
        return CompatibilityCheck(
            name="macos_version", ok=False, severity="error",
            detail="macOS version could not be parsed, so the MLX runtime requirement cannot be proven.",
            remediation=f"Confirm the host runs macOS {MLX_MIN_MACOS_VERSION}+ and retry `outerram doctor`.",
        )
    if not supported:
        return CompatibilityCheck(
            name="macos_version", ok=False, severity="error",
            detail=f"macOS {machine.os_version} detected; pinned MLX requires macOS {MLX_MIN_MACOS_VERSION}+.",
            remediation=f"Upgrade macOS to {MLX_MIN_MACOS_VERSION} or newer before bootstrap/serve.",
        )
    return CompatibilityCheck(
        name="macos_version", ok=True, severity="info",
        detail=f"macOS {machine.os_version} satisfies the pinned MLX minimum of {MLX_MIN_MACOS_VERSION}.",
    )


def assess_compatibility(machine: MachineInfo, model: ModelInfo, plan: RuntimePlan) -> CompatibilityReport:
    checks: list[CompatibilityCheck] = []
    checks.append(CompatibilityCheck(
        name="apple_silicon", ok=machine.apple_silicon, severity="error",
        detail="Apple Silicon macOS host detected." if machine.apple_silicon else "Execution runtimes target Apple Silicon macOS.",
        remediation=None if machine.apple_silicon else "Run OuterRAM on an M-series Mac; non-Mac hosts are supported only for planning/tests.",
    ))
    checks.append(macos_runtime_check(machine))

    py_ok = True
    if machine.python_version:
        try:
            major, minor, *_ = [int(x) for x in machine.python_version.split(".")]
            py_ok = (major, minor) >= (3, 10)
        except ValueError:
            py_ok = True
    checks.append(CompatibilityCheck(
        name="python", ok=py_ok, severity="error", detail=f"Python {machine.python_version or 'unknown'}",
        remediation=None if py_ok else "Install Python 3.10+ for OuterRAM itself.",
    ))

    if machine.swap_used_gib is not None and machine.swap_used_gib >= 1.0:
        checks.append(CompatibilityCheck(
            name="existing_swap_pressure", ok=False, severity="warning",
            detail=f"macOS is already using {machine.swap_used_gib:.2f} GiB of swap before inference starts.",
            remediation="For reproducible performance measurements, close memory-heavy apps and re-run after swap/memory pressure settles.",
        ))
    if machine.memory_free_percent is not None and machine.memory_free_percent < 10.0:
        checks.append(CompatibilityCheck(
            name="memory_pressure", ok=False, severity="warning",
            detail=f"macOS reports only {machine.memory_free_percent:.1f}% system-wide memory free.",
            remediation="Close memory-heavy apps before benchmarking or reduce the runtime memory budget.",
        ))
    if plan.strategy != Strategy.RESIDENT and machine.power_source and "battery" in machine.power_source.lower():
        checks.append(CompatibilityCheck(
            name="power_source", ok=False, severity="warning",
            detail=f"Streaming benchmark is running on {machine.power_source}.",
            remediation="Connect AC power before measuring SSD/Metal throughput to reduce thermal/power variability.",
        ))

    local_execution = model.source == ModelSource.LOCAL and bool(model.local_path)
    checks.append(CompatibilityCheck(
        name="local_execution_checkpoint", ok=local_execution, severity="error",
        detail=(f"Execution checkpoint is materialized locally at {model.local_path}." if local_execution else
                "Execution from a floating Hub repo id is refused so inspection and launch cannot resolve different revisions."),
        remediation=None if local_execution else f"Run `outerram fetch {model.model}` and use the returned local path for check/ready/serve.",
    ))

    if local_execution:
        complete = bool(model.checkpoint_complete)
        if model.missing_weight_files:
            missing_preview = ", ".join(model.missing_weight_files[:5])
            if len(model.missing_weight_files) > 5:
                missing_preview += f", ... (+{len(model.missing_weight_files) - 5} more)"
            detail = f"Local checkpoint is incomplete; missing weight files: {missing_preview}."
            remediation = "Re-run `outerram fetch <repo>` into this directory or restore the missing shards before launch."
        elif not complete:
            detail = "Local checkpoint completeness could not be proven (for example multiple unindexed weight files)."
            remediation = "Use a canonical MLX checkpoint with model.safetensors, a safetensors index, or an OuterRAM fetch sidecar."
        else:
            detail = f"Checkpoint selection is complete ({model.weight_file_count} weight file(s))."
            remediation = None
        checks.append(CompatibilityCheck(
            name="checkpoint_complete", ok=complete, severity="error", detail=detail, remediation=remediation,
        ))

    if plan.strategy == Strategy.MOE_STREAM:
        checks.append(CompatibilityCheck(
            name="strategy_architecture", ok=model.is_moe, severity="error",
            detail="MoE expert streaming selected for a model detected as MoE." if model.is_moe else "MoE expert streaming was selected for a model not detected as MoE.",
            remediation=None if model.is_moe else "Use resident/dense-stream for a dense model, or verify the checkpoint config exposes its MoE expert metadata.",
        ))
    elif plan.strategy == Strategy.DENSE_STREAM:
        checks.append(CompatibilityCheck(
            name="strategy_architecture", ok=not model.is_moe, severity="error",
            detail="Dense out-of-core streaming selected for a dense model." if not model.is_moe else "Dense-stream was selected for a MoE model; the pinned mlx-flash backend is not our validated exact-expert path.",
            remediation=None if not model.is_moe else "Use moe-stream (streamlx) or resident mode if the complete MoE checkpoint safely fits memory.",
        ))

    if plan.strategy == Strategy.DENSE_STREAM:
        dense_py_ok = True
        if machine.python_version:
            try:
                major, minor, *_ = [int(x) for x in machine.python_version.split(".")]
                dense_py_ok = (major, minor) >= (3, 11)
            except ValueError:
                dense_py_ok = True
        checks.append(CompatibilityCheck(
            name="dense_runtime_python", ok=dense_py_ok, severity="error",
            detail="mlx-flash v0.4.x requires Python 3.11+." if not dense_py_ok else "Python satisfies the pinned mlx-flash runtime requirement.",
            remediation=None if dense_py_ok else "Create the OuterRAM environment with Python 3.11, 3.12, or 3.13 before bootstrapping dense-stream.",
        ))

    if model.weight_size_gib is not None and machine.free_disk_gib is not None and model.source == ModelSource.HUGGINGFACE:
        needed = max(2.0, model.weight_size_gib * 1.15)
        disk_ok = machine.free_disk_gib >= needed
        checks.append(CompatibilityCheck(
            name="disk_space", ok=disk_ok, severity="error",
            detail=f"{machine.free_disk_gib:.1f} GiB free; approximately {needed:.1f} GiB recommended for this download.",
            remediation=None if disk_ok else "Free disk space or move the Hugging Face/OuterRAM cache to a larger volume.",
        ))

    if model.checkpoint_kind == CheckpointKind.GGUF:
        format_ok = False
        detail = "GGUF-only checkpoint detected; current OuterRAM execution adapters are MLX/safetensors-first."
        remediation = "Use an MLX quantized checkpoint of the same model, or add a future llama.cpp adapter."
    elif model.checkpoint_kind in {CheckpointKind.SAFETENSORS, CheckpointKind.MIXED}:
        format_ok = True
        detail = f"Checkpoint contains {model.checkpoint_kind.value} weights."
        remediation = None
    else:
        format_ok = plan.strategy == Strategy.RESIDENT
        detail = "Checkpoint weight format could not be proven from repository metadata."
        remediation = None if format_ok else "Use a local MLX/safetensors checkpoint so the streaming adapter can index weight ranges safely."
    checks.append(CompatibilityCheck("checkpoint_format", format_ok, "error", detail, remediation))

    if plan.strategy == Strategy.MOE_STREAM:
        local_ok = local_execution
        checks.append(CompatibilityCheck(
            name="moe_local_checkpoint", ok=local_ok, severity="error",
            detail="streamlx currently needs a local MLX model directory." if not local_ok else f"Local model directory: {model.local_path}",
            remediation=None if local_ok else f"Run `outerram fetch {model.model}` first, then serve the returned local directory.",
        ))
        known = (model.model_type or "").lower()
        validated_family = any(key in known for key in ("qwen3_5_moe", "qwen3_6", "kimi_linear", "laguna"))
        checks.append(CompatibilityCheck(
            name="moe_family", ok=True, severity="warning" if not validated_family else "info",
            detail=("Model family is in the set publicly validated by streamlx." if validated_family else
                    "MoE family is not one of streamlx's explicitly validated families; generic SwitchGLU support may still work."),
            remediation=None if validated_family else "Run `outerram probe` after launch before trusting long coding sessions.",
        ))

    if plan.strategy == Strategy.DENSE_STREAM:
        quant_ok = model.quantized
        checks.append(CompatibilityCheck(
            name="dense_quantized_checkpoint", ok=quant_ok, severity="warning",
            detail=(f"Quantized checkpoint detected ({model.quant_bits}-bit)." if quant_ok else
                    "No quantization metadata detected; dense SSD streaming of high-precision weights can be extremely slow."),
            remediation=None if quant_ok else "Prefer a 3-4 bit MLX checkpoint for practical local coding.",
        ))

    hard_fail = any((not c.ok) and c.severity == "error" for c in checks)
    return CompatibilityReport(compatible=not hard_fail, checks=tuple(checks))


def ensure_compatible(report: CompatibilityReport) -> None:
    if report.compatible:
        return
    failures = [c for c in report.checks if not c.ok and c.severity == "error"]
    detail = "; ".join(
        f"{c.name}: {c.detail}" + (f" Fix: {c.remediation}" if c.remediation else "") for c in failures
    )
    raise RuntimeError(f"Compatibility gate failed: {detail}")
