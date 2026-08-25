import random

import pytest

from outerram.planner import plan_runtime
from outerram.types import CheckpointKind, MachineInfo, ModelInfo, ModelSource, Strategy


def _model(size, moe):
    return ModelInfo(model="synthetic", local_path="/tmp/synthetic", architecture="SyntheticMoE" if moe else "SyntheticDense", model_type="synthetic_moe" if moe else "synthetic_dense", weight_size_gib=size, is_moe=moe, num_experts=64 if moe else None, top_k=4 if moe else None, quant_bits=4, source=ModelSource.LOCAL, checkpoint_kind=CheckpointKind.SAFETENSORS, weight_file_count=1, quantized=True)


def test_planner_randomized_invariants_are_stable():
    rng = random.Random(20260824)
    mapping = {Strategy.RESIDENT: "mlx-lm", Strategy.DENSE_STREAM: "mlx-flash", Strategy.MOE_STREAM: "streamlx"}
    for _ in range(500):
        total = rng.uniform(8.0, 256.0); reserve = rng.uniform(0.5, max(0.6, total - 1.05)); size = rng.uniform(0.1, 500.0); moe = bool(rng.getrandbits(1))
        machine = MachineInfo("Darwin", "arm64", total, True, python_version="3.12.5")
        plan = plan_runtime(machine, _model(size, moe), reserve_gib=reserve)
        assert plan.runtime == mapping[plan.strategy]
        assert plan.resident_budget_gib > 0
        assert abs((plan.resident_budget_gib + plan.reserved_memory_gib) - round(total, 2)) <= 0.02
        if plan.strategy is Strategy.MOE_STREAM:
            assert moe and plan.expert_budget_gib is not None and 1.0 <= plan.expert_budget_gib <= plan.resident_budget_gib
        else:
            assert plan.expert_budget_gib is None
        if plan.strategy is Strategy.DENSE_STREAM: assert not moe


def test_forced_strategy_is_honored_for_random_models():
    machine = MachineInfo("Darwin", "arm64", 64.0, True, python_version="3.12.5")
    for forced in Strategy:
        for moe in (False, True):
            plan = plan_runtime(machine, _model(1.0, moe), force=forced)
            assert plan.strategy is forced and plan.confidence == "forced"


def test_invalid_reserve_values_always_fail_closed():
    machine = MachineInfo("Darwin", "arm64", 16.0, True); model = _model(8.0, False)
    for reserve in (-10.0, -0.1, 0.0, 15.5, 16.0, 20.0):
        with pytest.raises(ValueError): plan_runtime(machine, model, reserve_gib=reserve)
