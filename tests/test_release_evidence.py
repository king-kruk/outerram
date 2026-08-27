from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release-evidence.py"


def load_module():
    spec = importlib.util.spec_from_file_location("outerram_release_evidence", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_evidence_records_machine_verifiable_public_state():
    module = load_module()
    commit = "a" * 40
    evidence = module.build_evidence(commit)
    assert evidence["schema_version"] == 2
    assert evidence["project"] == "OuterRAM"
    assert evidence["git_commit"] == commit
    assert evidence["project_license"] == "MIT"
    assert evidence["legal_gate_results"]["internal"]["ok"] is True
    assert evidence["legal_gate_results"]["public"]["ok"] is True
    assert evidence["statements"]["model_weights_bundled"] is False
    assert evidence["statements"]["legal_clearance_inferred_from_model_metadata"] is False
    assert evidence["statements"]["human_legal_clearance_encoded"] is False
    for required in ("LICENSE", "THIRD_PARTY_NOTICES.md", "TRADEMARKS.md", "legal/APPROVED_COMPONENTS.json"):
        assert len(evidence["evidence_file_sha256"][required]) == 64
    assert "legal/RELEASE_APPROVALS.json" not in evidence["evidence_file_sha256"]


def test_release_evidence_runtime_pins_are_immutable_shas():
    module = load_module()
    pins = module.runtime_pins()
    assert set(pins) == {"mlx-lm", "mlx-flash", "streamlx"}
    assert all(len(value) == 40 for value in pins.values())
    assert all(set(value) <= set("0123456789abcdef") for value in pins.values())
