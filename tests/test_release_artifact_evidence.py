from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-release-artifacts.py"


def load_module():
    spec = importlib.util.spec_from_file_location("outerram_release_artifacts", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sbom_validator_binds_root_identity_and_version(tmp_path):
    module = load_module(); path = tmp_path / "SBOM.cdx.json"
    path.write_text(json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.6", "metadata": {"component": {"name": "outerram", "version": "0.3.0rc1"}}, "components": []}), encoding="utf-8")
    assert module.validate_sbom(path, "0.3.0rc1") == []
    assert any("version" in error for error in module.validate_sbom(path, "9.9.9"))
    bad = json.loads(path.read_text()); bad["metadata"]["component"]["name"] = "legacy-name"; path.write_text(json.dumps(bad))
    assert any("outerram" in error for error in module.validate_sbom(path, "0.3.0rc1"))


def test_release_evidence_validator_binds_project_version_commit_and_disclaimer(tmp_path):
    module = load_module(); commit = "a" * 40; path = tmp_path / "RELEASE-EVIDENCE.json"
    path.write_text(json.dumps({"project": "OuterRAM", "version": "0.3.0rc1", "git_commit": commit, "project_license": "MIT", "statements": {"artifact_is_legal_opinion": False}}), encoding="utf-8")
    assert module.validate_release_evidence(path, "0.3.0rc1", commit) == []
    bad = json.loads(path.read_text()); bad["statements"]["artifact_is_legal_opinion"] = True; path.write_text(json.dumps(bad))
    assert any("legal opinion" in error for error in module.validate_release_evidence(path, "0.3.0rc1", commit))
