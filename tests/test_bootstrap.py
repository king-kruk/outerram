from outerram.bootstrap import bootstrap_commands
from outerram.runtime_pins import MLX_FLASH_REF, MLX_LM_REF, STREAMLX_REF
from outerram.types import RuntimePlan, Strategy


def plan(strategy):
    return RuntimePlan(
        strategy=strategy,
        runtime="x",
        total_memory_gib=16,
        reserved_memory_gib=4,
        resident_budget_gib=12,
        weight_size_gib=20,
        expert_budget_gib=6 if strategy is Strategy.MOE_STREAM else None,
        reason="test",
    )


def test_resident_bootstrap_uses_pinned_mlx_lm():
    cmd = bootstrap_commands(plan(Strategy.RESIDENT))[0]
    assert any("ml-explore/mlx-lm" in part and MLX_LM_REF in part for part in cmd)


def test_dense_bootstrap_installs_flash_then_enforces_pinned_mlx_lm():
    cmds = bootstrap_commands(plan(Strategy.DENSE_STREAM))
    assert len(cmds) == 2
    assert any("matt-k-wong/mlx-flash" in part and MLX_FLASH_REF in part for part in cmds[0])
    assert any("ml-explore/mlx-lm" in part and MLX_LM_REF in part for part in cmds[1])


def test_moe_bootstrap_clones_and_checks_out_pin(tmp_path):
    home = tmp_path / "streamlx"
    cmds = bootstrap_commands(plan(Strategy.MOE_STREAM), streamlx_home=str(home))
    assert cmds[0][0:2] == ("git", "clone")
    assert any(STREAMLX_REF in part for cmd in cmds for part in cmd)
    assert str(home) in cmds[0]


def test_latest_bootstrap_omits_revision_pins():
    cmds = bootstrap_commands(plan(Strategy.DENSE_STREAM), latest=True)
    joined = " ".join(" ".join(cmd) for cmd in cmds)
    assert MLX_LM_REF not in joined
    assert MLX_FLASH_REF not in joined


def test_latest_existing_streamlx_checkout_tracks_origin_main(tmp_path):
    home = tmp_path / "streamlx"
    home.mkdir()
    cmds = bootstrap_commands(plan(Strategy.MOE_STREAM), streamlx_home=str(home), latest=True)
    joined = [" ".join(cmd) for cmd in cmds]
    assert any("fetch origin main" in cmd for cmd in joined)
    assert any("checkout --detach origin/main" in cmd for cmd in joined)
    assert all(STREAMLX_REF not in cmd for cmd in joined)
