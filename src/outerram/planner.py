from __future__ import annotations

from .types import MachineInfo, ModelInfo, RuntimePlan, Strategy


def _default_reserve(total_gib: float) -> float:
    if total_gib <= 16.5:
        return 4.0
    if total_gib <= 24.5:
        return 5.0
    if total_gib <= 32.5:
        return 6.0
    return max(6.0, total_gib * 0.18)


def plan_runtime(
    machine: MachineInfo,
    model: ModelInfo,
    *,
    reserve_gib: float | None = None,
    force: Strategy | None = None,
) -> RuntimePlan:
    reserve = reserve_gib if reserve_gib is not None else _default_reserve(machine.total_memory_gib)
    if reserve <= 0 or reserve >= machine.total_memory_gib:
        raise ValueError("reserve_gib must be > 0 and smaller than total memory")

    budget = machine.total_memory_gib - reserve
    if budget < 1.0:
        raise ValueError(
            "reserve_gib leaves less than 1 GiB for model/runtime working memory; reduce the reserve"
        )
    size = model.weight_size_gib
    warnings: list[str] = []
    if not machine.apple_silicon:
        warnings.append("Current execution runtimes target macOS on Apple Silicon; this host can only be used for planning/tests.")

    safe_resident_limit = max(1.0, budget - max(0.75, budget * 0.06))

    if force is not None:
        strategy = force
        reason = f"Strategy forced to {force.value}."
        confidence = "forced"
    elif size is not None and size <= safe_resident_limit:
        strategy = Strategy.RESIDENT
        reason = (
            f"Weights ({size:.2f} GiB) fit below the conservative resident limit "
            f"({safe_resident_limit:.2f} GiB) after reserving macOS/IDE/KV headroom."
        )
        confidence = "high"
    elif model.is_moe:
        strategy = Strategy.MOE_STREAM
        reason = "Model is MoE and exceeds the safe resident limit; preserve routing fidelity and stream required experts from SSD."
        confidence = "high" if size is not None else "medium"
    else:
        strategy = Strategy.DENSE_STREAM
        reason = "Dense weights exceed the safe resident limit; use out-of-core layer/weight streaming from SSD."
        confidence = "high" if size is not None else "low"

    runtime = {
        Strategy.RESIDENT: "mlx-lm",
        Strategy.DENSE_STREAM: "mlx-flash",
        Strategy.MOE_STREAM: "streamlx",
    }[strategy]

    expert_budget = None
    if strategy == Strategy.MOE_STREAM:
        expert_budget = max(1.0, round(budget * 0.55, 1))
        if machine.total_memory_gib <= 16.5:
            expert_budget = min(expert_budget, 6.0)
    if strategy == Strategy.DENSE_STREAM:
        warnings.append("Dense SSD streaming reads a much larger fraction of the model per token than MoE streaming; SSD bandwidth can dominate latency.")
        if size is not None and size <= budget:
            warnings.append(
                "This is a near-fit dense model: once physical hardware is available, benchmark both auto dense-stream and forced resident mode; "
                "resident may be much faster if real peak memory pressure remains acceptable."
            )
    if size is None:
        warnings.append("Weight size is unknown; the plan is architecture-driven and has lower confidence until the checkpoint is local or fully indexed.")
    if size is not None and strategy == Strategy.RESIDENT and size > budget * 0.85:
        warnings.append("The model is close to the resident memory ceiling; long context or a heavy IDE may still trigger memory pressure.")

    return RuntimePlan(
        strategy=strategy,
        runtime=runtime,
        total_memory_gib=machine.total_memory_gib,
        reserved_memory_gib=round(reserve, 2),
        resident_budget_gib=round(budget, 2),
        weight_size_gib=size,
        expert_budget_gib=expert_budget,
        reason=reason,
        warnings=tuple(warnings),
        confidence=confidence,
    )
