from outerram.planner import plan_runtime
from outerram.types import MachineInfo, ModelInfo, Strategy


def mac16():
    return MachineInfo("Darwin", "arm64", 16.0, True)


def model(size, moe=False):
    return ModelInfo(model="test/model", local_path=None, architecture="Test", model_type="test_moe" if moe else "test", weight_size_gib=size, is_moe=moe, num_experts=128 if moe else None, top_k=8 if moe else None, quant_bits=4)


def test_16gb_small_model_is_resident():
    plan = plan_runtime(mac16(), model(9.0)); assert plan.strategy is Strategy.RESIDENT and plan.runtime == "mlx-lm"


def test_16gb_dense_oversize_streams_layers():
    plan = plan_runtime(mac16(), model(14.0)); assert plan.strategy is Strategy.DENSE_STREAM and plan.runtime == "mlx-flash"


def test_16gb_moe_oversize_streams_experts():
    plan = plan_runtime(mac16(), model(22.0, moe=True)); assert plan.strategy is Strategy.MOE_STREAM and plan.runtime == "streamlx" and plan.expert_budget_gib == 6.0


def test_force_strategy_wins():
    assert plan_runtime(mac16(), model(9.0), force=Strategy.DENSE_STREAM).strategy is Strategy.DENSE_STREAM


def test_near_fit_dense_plan_recommends_resident_comparison():
    machine = MachineInfo("Darwin", "arm64", 16.0, True); candidate = ModelInfo("q", None, "Q", "q", 11.8, False, None, None, 3)
    plan = plan_runtime(machine, candidate)
    assert plan.strategy is Strategy.DENSE_STREAM and any("forced resident" in warning for warning in plan.warnings)


def test_planner_matrix_never_exceeds_memory_or_returns_invalid_budget():
    for ram in (8.0, 16.0, 24.0, 32.0, 64.0):
        machine = MachineInfo("Darwin", "arm64", ram, True)
        for size in (2.0, 6.0, 10.0, 14.0, 22.0, 40.0, 80.0):
            for moe in (False, True):
                p = plan_runtime(machine, model(size, moe=moe))
                assert 0 < p.reserved_memory_gib < ram and 0 < p.resident_budget_gib < ram
                if p.strategy is Strategy.MOE_STREAM:
                    assert p.expert_budget_gib is not None and 0 < p.expert_budget_gib < ram
