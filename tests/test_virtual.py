from outerram.types import Strategy
from outerram.virtual import QWEN38_27B_3BIT_TEXT, run_virtual_qualification


def test_qwen_profile_uses_decimal_to_gib_size():
    assert 10.9 < QWEN38_27B_3BIT_TEXT.model.weight_size_gib < 11.1
    assert QWEN38_27B_3BIT_TEXT.model.quant_bits == 3
    assert QWEN38_27B_3BIT_TEXT.model.is_moe is False
    assert QWEN38_27B_3BIT_TEXT.model.declared_license == "apache-2.0"
    assert QWEN38_27B_3BIT_TEXT.model.legal_clearance is False


def test_m5_16gb_virtual_qualification_passes_contracts():
    result = run_virtual_qualification()
    assert result["simulation_passed"] is True
    assert result["physical_apple_silicon_validation"] is False
    assert result["metal_inference_executed"] is False
    assert result["performance_claim_allowed"] is False
    assert result["api_contract"]["qualified"] is True
    assert all(result["api_contract"]["gates"].values())


def test_baseline_qwen_plan_is_near_fit_resident():
    result = run_virtual_qualification()
    assert result["plan"]["strategy"] == "resident"
    assert result["plan"]["weight_size_gib"] < result["plan"]["resident_budget_gib"]
    assert any("close to the resident memory ceiling" in w for w in result["plan"]["warnings"])


def test_heavier_reserve_flips_qwen_to_dense_stream():
    result = run_virtual_qualification(reserve_gib=4.5)
    assert result["simulation_passed"] is True
    assert result["plan"]["strategy"] == "dense-stream"
    assert result["plan"]["runtime"] == "mlx-flash"


def test_forced_dense_stream_contract_passes():
    result = run_virtual_qualification(strategy=Strategy.DENSE_STREAM)
    assert result["simulation_passed"] is True
    assert result["plan"]["strategy"] == "dense-stream"
    assert result["compatibility"]["compatible"] is True
    assert "dense_server" in " ".join(result["launch_contract"]["argv"])


def test_forced_moe_stream_on_dense_model_fails_closed():
    result = run_virtual_qualification(strategy=Strategy.MOE_STREAM)
    assert result["simulation_passed"] is False
    assert result["compatibility"]["compatible"] is False
    checks = {c["name"]: c for c in result["compatibility"]["checks"]}
    assert checks["strategy_architecture"]["ok"] is False


def test_sensitivity_sweep_contains_strategy_flip():
    result = run_virtual_qualification()
    strategies = {row["case"]: row["strategy"] for row in result["sensitivity"]}
    assert strategies["baseline"] == "resident"
    assert strategies["heavier-os-ide"] == "dense-stream"
    assert strategies["high-headroom"] == "dense-stream"
    assert strategies["runtime-footprint-plus-5pct"] == "dense-stream"


def test_injected_failures_fail_closed():
    for failure in ("health", "marker", "tool-call", "tool-roundtrip", "empty-stream", "usage"):
        assert run_virtual_qualification(failure=failure)["simulation_passed"] is False


def test_virtual_matrix_covers_six_machine_profiles_and_six_stress_scenarios():
    from outerram.virtual import PROFILES, SCENARIOS, run_virtual_matrix
    result = run_virtual_matrix()
    assert len(PROFILES) == 6
    assert len(SCENARIOS) == 6
    assert result["summary"]["rows"] == 36
    assert result["summary"]["compatible_rows"] == 36


def test_m5_16gb_matrix_flips_under_realistic_headroom_stress():
    from outerram.virtual import run_virtual_matrix
    result = run_virtual_matrix(profile_names=["m5-16gb"])
    rows = {row["scenario"]: row for row in result["rows"]}
    assert rows["baseline"]["strategy"] == "resident"
    assert rows["heavy-ide"]["strategy"] == "dense-stream"
    assert rows["long-context"]["strategy"] == "dense-stream"
    assert rows["footprint-plus-10pct"]["strategy"] == "dense-stream"


def test_24gb_and_larger_profiles_keep_target_resident_in_current_stress_set():
    from outerram.virtual import run_virtual_matrix
    result = run_virtual_matrix(profile_names=["m5-24gb", "m5-32gb", "m5-pro-48gb", "m5-max-64gb"])
    assert {row["strategy"] for row in result["rows"]} == {"resident"}


def test_slow_ssd_is_high_risk_only_when_streaming_is_selected():
    from outerram.virtual import run_virtual_matrix
    result = run_virtual_matrix(profile_names=["m5-16gb", "m5-24gb"], scenario_names=["slow-ssd"])
    rows = {row["profile"]: row for row in result["rows"]}
    assert rows["m5-16gb"]["strategy"] == "dense-stream"
    assert rows["m5-16gb"]["ssd"]["streaming_risk"] == "high"
    assert rows["m5-24gb"]["strategy"] == "resident"
    assert rows["m5-24gb"]["ssd"]["streaming_risk"] == "not-critical"


def test_matrix_never_claims_metal_or_physical_validation():
    from outerram.virtual import run_virtual_matrix
    result = run_virtual_matrix()
    assert result["simulation_only"] is True
    assert result["physical_apple_silicon_validation"] is False
    assert result["metal_inference_executed"] is False
    assert result["performance_claim_allowed"] is False
    assert all(row["physical_validation"] is False for row in result["rows"])
