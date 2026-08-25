import json
from pathlib import Path

from outerram.model import inspect_local_model
from outerram.types import CheckpointKind, ModelSource


def test_detects_dense_model_and_checkpoint_kind(tmp_path: Path):
    (tmp_path / "config.json").write_text(json.dumps({"model_type": "qwen3_8", "architectures": ["Qwen3_8ForCausalLM"], "quantization_config": {"bits": 3}}))
    (tmp_path / "model.safetensors").write_bytes(b"x" * 128)
    info = inspect_local_model(tmp_path)
    assert not info.is_moe and info.quant_bits == 3 and info.quantized
    assert info.source is ModelSource.LOCAL and info.checkpoint_kind is CheckpointKind.SAFETENSORS and info.weight_file_count == 1
    assert info.legal_clearance is False


def test_detects_nested_moe_model(tmp_path: Path):
    (tmp_path / "config.json").write_text(json.dumps({"architectures": ["QwenMoEForCausalLM"], "text_config": {"model_type": "qwen3_5_moe", "num_experts": 512, "num_experts_per_tok": 10}}))
    (tmp_path / "model.safetensors").write_bytes(b"x")
    info = inspect_local_model(tmp_path)
    assert info.is_moe and info.num_experts == 512 and info.top_k == 10


def test_detects_gguf_only_checkpoint(tmp_path: Path):
    (tmp_path / "config.json").write_text(json.dumps({"model_type": "llama"})); (tmp_path / "model.Q4_K_M.gguf").write_bytes(b"x")
    assert inspect_local_model(tmp_path).checkpoint_kind is CheckpointKind.GGUF


def test_hf_size_does_not_sum_alternative_gguf_quantizations():
    from types import SimpleNamespace
    from outerram.model import _hf_selected_weight_size
    siblings = [SimpleNamespace(rfilename="model-Q4.gguf", size=4_000), SimpleNamespace(rfilename="model-Q8.gguf", size=8_000)]
    size, selected = _hf_selected_weight_size("x/y", siblings)
    assert size is None and len(selected) == 2


def test_hf_size_sums_standard_safetensor_shards_without_counting_extra_file():
    from types import SimpleNamespace
    from outerram.model import _hf_selected_weight_size
    siblings = [SimpleNamespace(rfilename="model-00001-of-00002.safetensors", size=4_000), SimpleNamespace(rfilename="model-00002-of-00002.safetensors", size=5_000), SimpleNamespace(rfilename="adapter.safetensors", size=99_000)]
    size, selected = _hf_selected_weight_size("x/y", siblings)
    assert size == 9_000 and len(selected) == 2


def test_local_multiple_ggufs_are_not_summed(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"model_type": "qwen"})); (tmp_path / "model-Q3.gguf").write_bytes(b"x" * 1024); (tmp_path / "model-Q4.gguf").write_bytes(b"x" * 2048)
    info = inspect_local_model(tmp_path)
    assert info.weight_size_gib is None and info.weight_file_count == 2


def test_local_safetensor_index_selects_only_referenced_shards(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"model_type": "qwen"}))
    (tmp_path / "model-00001-of-00002.safetensors").write_bytes(b"a" * 1024); (tmp_path / "model-00002-of-00002.safetensors").write_bytes(b"b" * 2048); (tmp_path / "adapter.safetensors").write_bytes(b"c" * 4096)
    (tmp_path / "model.safetensors.index.json").write_text(json.dumps({"weight_map": {"a": "model-00001-of-00002.safetensors", "b": "model-00002-of-00002.safetensors"}}))
    info = inspect_local_model(tmp_path)
    assert info.weight_file_count == 2 and info.weight_size_gib is not None


def test_hf_inspection_pins_config_and_license_metadata_to_resolved_revision(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import outerram.model as model_mod
    cfg = tmp_path / "config.json"; cfg.write_text(json.dumps({"model_type": "qwen", "quantization_config": {"bits": 4}}))
    sibling = SimpleNamespace(rfilename="model.safetensors", size=1234)
    class FakeApi:
        def model_info(self, model_id, files_metadata=False, revision=None):
            return SimpleNamespace(sha="deadbeef", siblings=[sibling], card_data={"license": "apache-2.0", "license_name": "Apache License 2.0", "license_link": "https://example.invalid/license", "base_model": ["Qwen/base", {"repo_id": "org/ancestor"}]})
    calls = []
    def fake_download(*, repo_id, filename, revision=None): calls.append((repo_id, filename, revision)); return str(cfg)
    monkeypatch.setattr(model_mod, "HfApi", FakeApi); monkeypatch.setattr(model_mod, "hf_hub_download", fake_download)
    info = model_mod.inspect_hf_model("owner/model")
    assert info.revision == "deadbeef" and calls == [("owner/model", "config.json", "deadbeef")]
    assert info.declared_license == "apache-2.0" and info.base_models == ("Qwen/base", "org/ancestor") and info.legal_clearance is False


def test_fetch_model_passes_revision_to_snapshot_download(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import outerram.model as model_mod
    captured = {}
    class FakeApi:
        def model_info(self, model_id, revision=None): return SimpleNamespace(sha="server-sha", card_data={})
    def fake_snapshot_download(**kwargs): captured.update(kwargs); return str(tmp_path)
    monkeypatch.setattr(model_mod, "HfApi", FakeApi); monkeypatch.setattr(model_mod, "snapshot_download", fake_snapshot_download)
    out = model_mod.fetch_model("owner/model", revision="abc123", weight_files=("model.safetensors",))
    assert captured["revision"] == "abc123" and "model.safetensors" in captured["allow_patterns"]
    sidecar = json.loads((out / ".outerram-source.json").read_text()); assert sidecar["revision"] == "abc123" and sidecar["legal_clearance"] is False


def test_fetch_model_without_revision_resolves_commit_before_snapshot(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import outerram.model as model_mod
    captured = {}
    class FakeApi:
        def model_info(self, model_id, revision=None): return SimpleNamespace(sha="resolved123", card_data={"license": "mit", "base_model": "org/base"})
    def fake_snapshot_download(**kwargs): captured.update(kwargs); return str(tmp_path)
    monkeypatch.setattr(model_mod, "HfApi", FakeApi); monkeypatch.setattr(model_mod, "snapshot_download", fake_snapshot_download)
    out = model_mod.fetch_model("owner/model", weight_files=("model.safetensors",))
    assert captured["revision"] == "resolved123"
    sidecar = json.loads((out / ".outerram-source.json").read_text()); assert sidecar["declared_license"] == "mit" and sidecar["base_models"] == ["org/base"]


def test_local_hf_snapshot_preserves_revision(tmp_path):
    snap = tmp_path / "hub" / "models--owner--model" / "snapshots" / "abcdef1234567890"; snap.mkdir(parents=True)
    (snap / "config.json").write_text(json.dumps({"model_type": "qwen"})); (snap / "model.safetensors").write_bytes(b"x")
    assert inspect_local_model(snap).revision == "abcdef1234567890"


def test_fetch_to_custom_dir_writes_reproducibility_and_license_sidecar(tmp_path, monkeypatch):
    import outerram.model as model_mod
    destination = tmp_path / "downloaded"; destination.mkdir(); (destination / "config.json").write_text(json.dumps({"model_type": "qwen"})); (destination / "model.safetensors").write_bytes(b"x")
    monkeypatch.setattr(model_mod, "snapshot_download", lambda **kwargs: str(destination))
    path = model_mod.fetch_model("owner/model", destination, revision="abc123def456", weight_files=("model.safetensors",), declared_license="apache-2.0", license_name="Apache License 2.0", license_link="https://example.invalid/license", base_models=("org/base",), license_metadata_source="huggingface-model-card")
    sidecar = json.loads((path / ".outerram-source.json").read_text())
    assert sidecar["schema_version"] == 2 and sidecar["repo_id"] == "owner/model" and sidecar["legal_clearance"] is False
    info = model_mod.inspect_local_model(path); assert info.origin == "owner/model" and info.declared_license == "apache-2.0"


def test_incomplete_indexed_checkpoint_fails_closed_instead_of_summing_partial_shards(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"model_type": "qwen"})); (tmp_path / "model-00001-of-00002.safetensors").write_bytes(b"a" * 1024)
    (tmp_path / "model.safetensors.index.json").write_text(json.dumps({"weight_map": {"a": "model-00001-of-00002.safetensors", "b": "model-00002-of-00002.safetensors"}}))
    info = inspect_local_model(tmp_path)
    assert info.checkpoint_complete is False and info.weight_size_gib is None and info.missing_weight_files == ("model-00002-of-00002.safetensors",)


def test_incomplete_standard_shards_without_index_are_detected(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"model_type": "qwen"})); (tmp_path / "model-00001-of-00003.safetensors").write_bytes(b"a"); (tmp_path / "model-00003-of-00003.safetensors").write_bytes(b"c")
    info = inspect_local_model(tmp_path)
    assert info.checkpoint_complete is False and info.missing_weight_files == ("model-00002-of-00003.safetensors",)


def test_legacy_sidecar_expected_weights_are_still_read_during_transition(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"model_type": "qwen"})); (tmp_path / "part-a.safetensors").write_bytes(b"a")
    (tmp_path / ".stretchmlx-source.json").write_text(json.dumps({"schema_version": 1, "repo_id": "owner/model", "revision": "abc123", "weight_files": ["part-a.safetensors", "part-b.safetensors"]}))
    info = inspect_local_model(tmp_path)
    assert info.checkpoint_complete is False and info.missing_weight_files == ("part-b.safetensors",) and info.origin == "owner/model"


def test_outerram_sidecar_takes_precedence_over_legacy_sidecar(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"model_type": "qwen"})); (tmp_path / "model.safetensors").write_bytes(b"x")
    (tmp_path / ".stretchmlx-source.json").write_text(json.dumps({"repo_id": "legacy/model", "revision": "old", "weight_files": ["model.safetensors"]})); (tmp_path / ".outerram-source.json").write_text(json.dumps({"repo_id": "new/model", "revision": "new", "weight_files": ["model.safetensors"]}))
    info = inspect_local_model(tmp_path); assert info.origin == "new/model" and info.revision == "new"


def test_standard_hf_cache_snapshot_preserves_origin_and_revision(tmp_path):
    snap = tmp_path / "hub" / "models--owner--model" / "snapshots" / "abcdef1234567890"; snap.mkdir(parents=True)
    (snap / "config.json").write_text(json.dumps({"model_type": "qwen"})); (snap / "model.safetensors").write_bytes(b"x")
    info = inspect_local_model(snap); assert info.origin == "owner/model" and info.revision == "abcdef1234567890"


def test_legacy_sidecar_weight_path_cannot_escape_model_directory(tmp_path):
    model_dir = tmp_path / "model"; model_dir.mkdir(); (model_dir / "config.json").write_text(json.dumps({"model_type": "qwen"})); (tmp_path / "outside.safetensors").write_bytes(b"secret")
    (model_dir / ".stretchmlx-source.json").write_text(json.dumps({"schema_version": 1, "repo_id": "owner/model", "revision": "abc", "weight_files": ["../outside.safetensors"]}))
    info = inspect_local_model(model_dir); assert info.checkpoint_complete is False and "unsafe path" in info.missing_weight_files[0]


def test_safetensors_index_weight_path_cannot_escape_model_directory(tmp_path):
    model_dir = tmp_path / "model"; model_dir.mkdir(); (model_dir / "config.json").write_text(json.dumps({"model_type": "qwen"})); (tmp_path / "outside.safetensors").write_bytes(b"secret")
    (model_dir / "model.safetensors.index.json").write_text(json.dumps({"weight_map": {"x": "../outside.safetensors"}}))
    info = inspect_local_model(model_dir); assert info.checkpoint_complete is False and "unsafe path" in info.missing_weight_files[0]
