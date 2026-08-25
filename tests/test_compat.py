from outerram.compat import assess_compatibility
from outerram.types import CheckpointKind, MachineInfo, ModelInfo, ModelSource, RuntimePlan, Strategy


def mac16(os_version="14.0"):
    return MachineInfo("Darwin", "arm64", 16.0, True, free_disk_gib=100, python_version="3.12.5", os_version=os_version)


def plan(strategy):
    return RuntimePlan(strategy, "x", 16, 4, 12, 22, 6 if strategy is Strategy.MOE_STREAM else None, "test")


def model(*, source=ModelSource.LOCAL, kind=CheckpointKind.SAFETENSORS, moe=False, quant_bits=4):
    return ModelInfo(model="m", local_path="/m" if source is ModelSource.LOCAL else None, architecture="A", model_type="qwen3_5_moe" if moe else "qwen3_8", weight_size_gib=22, is_moe=moe, num_experts=128 if moe else None, top_k=8 if moe else None, quant_bits=quant_bits, source=source, checkpoint_kind=kind, weight_file_count=2, quantized=quant_bits is not None)


def test_macos_14_is_supported():
    report = assess_compatibility(mac16("14.0"), model(), plan(Strategy.RESIDENT))
    check = next(c for c in report.checks if c.name == "macos_version")
    assert report.compatible and check.ok


def test_newer_macos_is_supported():
    report = assess_compatibility(mac16("26.6"), model(), plan(Strategy.RESIDENT))
    assert report.compatible and next(c for c in report.checks if c.name == "macos_version").ok


def test_macos_13_is_fail_closed():
    report = assess_compatibility(mac16("13.7.8"), model(), plan(Strategy.RESIDENT))
    assert not report.compatible
    check = next(c for c in report.checks if c.name == "macos_version")
    assert not check.ok and check.severity == "error" and "14.0" in (check.remediation or "")


def test_unknown_macos_version_is_fail_closed():
    report = assess_compatibility(mac16("not-a-version"), model(), plan(Strategy.RESIDENT))
    assert not report.compatible
    assert "could not be parsed" in next(c for c in report.checks if c.name == "macos_version").detail


def test_remote_moe_must_be_materialized_locally():
    report = assess_compatibility(mac16(), model(source=ModelSource.HUGGINGFACE, moe=True), plan(Strategy.MOE_STREAM))
    assert not report.compatible
    assert "outerram fetch" in next(c for c in report.checks if c.name == "moe_local_checkpoint").remediation


def test_remote_dense_is_also_fail_closed_until_materialized():
    report = assess_compatibility(mac16(), model(source=ModelSource.HUGGINGFACE), plan(Strategy.DENSE_STREAM))
    assert not report.compatible
    assert "outerram fetch" in (next(c for c in report.checks if c.name == "local_execution_checkpoint").remediation or "")


def test_remote_checkpoint_insufficient_disk_is_hard_failure():
    machine = MachineInfo("Darwin", "arm64", 16.0, True, free_disk_gib=1.0, python_version="3.12.5", os_version="14.0")
    report = assess_compatibility(machine, model(source=ModelSource.HUGGINGFACE), plan(Strategy.DENSE_STREAM))
    check = next(c for c in report.checks if c.name == "disk_space")
    assert not check.ok and check.severity == "error"


def test_gguf_is_fail_closed_for_current_adapters():
    assert not assess_compatibility(mac16(), model(kind=CheckpointKind.GGUF), plan(Strategy.DENSE_STREAM)).compatible


def test_quantized_local_moe_is_compatible():
    assert assess_compatibility(mac16(), model(moe=True), plan(Strategy.MOE_STREAM)).compatible


def test_dense_unquantized_is_warning_not_hard_failure():
    report = assess_compatibility(mac16(), model(quant_bits=None), plan(Strategy.DENSE_STREAM))
    assert report.compatible
    check = next(c for c in report.checks if c.name == "dense_quantized_checkpoint")
    assert not check.ok and check.severity == "warning"


def test_dense_stream_requires_python_311_or_newer():
    machine = MachineInfo("Darwin", "arm64", 16.0, True, free_disk_gib=100, python_version="3.10.14", os_version="14.0")
    report = assess_compatibility(machine, model(), plan(Strategy.DENSE_STREAM))
    assert not report.compatible and "3.11" in (next(c for c in report.checks if c.name == "dense_runtime_python").remediation or "")


def test_moe_stream_still_allows_python_310():
    machine = MachineInfo("Darwin", "arm64", 16.0, True, free_disk_gib=100, python_version="3.10.14", os_version="14.0")
    assert assess_compatibility(machine, model(moe=True), plan(Strategy.MOE_STREAM)).compatible


def test_incomplete_local_checkpoint_is_hard_failure():
    broken = model(); object.__setattr__(broken, "checkpoint_complete", False); object.__setattr__(broken, "missing_weight_files", ("model-00002-of-00002.safetensors",))
    report = assess_compatibility(mac16(), broken, plan(Strategy.DENSE_STREAM))
    assert not report.compatible and "missing" in next(c for c in report.checks if c.name == "checkpoint_complete").detail.lower()


def test_existing_swap_and_battery_are_warnings_not_false_hard_failures():
    machine = MachineInfo("Darwin", "arm64", 16.0, True, free_disk_gib=100, python_version="3.12.5", os_version="14.0", swap_used_gib=2.0, memory_free_percent=8.0, power_source="Battery Power")
    report = assess_compatibility(machine, model(), plan(Strategy.DENSE_STREAM))
    assert report.compatible
    names = {c.name for c in report.checks if not c.ok and c.severity == "warning"}
    assert {"existing_swap_pressure", "memory_pressure", "power_source"} <= names


def test_forced_moe_stream_on_dense_model_is_hard_failure():
    assert not assess_compatibility(mac16(), model(moe=False), plan(Strategy.MOE_STREAM)).compatible


def test_forced_dense_stream_on_moe_model_is_hard_failure():
    assert not assess_compatibility(mac16(), model(moe=True), plan(Strategy.DENSE_STREAM)).compatible
