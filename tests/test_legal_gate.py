from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "legal-gate.py"


def run_gate(mode: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--mode", mode, "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def load_gate_module():
    spec = importlib.util.spec_from_file_location("outerram_legal_gate", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_internal_legal_gate_passes_but_reports_pending_human_reviews():
    proc = run_gate("internal")
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(proc.stdout)
    assert report["ok"] is True
    assert not any("trademark_clearance" in warning for warning in report["warnings"])
    assert not any("dependency_license_review" in warning for warning in report["warnings"])


def test_public_legal_gate_reflects_machine_readable_release_approvals():
    proc = run_gate("public")
    report = json.loads(proc.stdout)
    approvals = json.loads((ROOT / "legal" / "RELEASE_APPROVALS.json").read_text(encoding="utf-8"))
    pending = [name for name, item in approvals["public_release"].items() if item.get("status") != "approved"]
    rendered = "\n".join(report["errors"])
    assert report["ok"] is (not pending)
    assert proc.returncode == (0 if not pending else 1)
    for name in pending:
        assert name in rendered


def test_validated_gate_adds_full_ci_and_physical_hardware_requirements():
    proc = run_gate("validated")
    assert proc.returncode != 0
    report = json.loads(proc.stdout)
    rendered = "\n".join(report["errors"])
    assert "full_release_validation" in rendered
    assert "physical_apple_silicon_validation" in rendered


def test_commercial_gate_adds_patent_fto_blocker():
    proc = run_gate("commercial")
    assert proc.returncode != 0
    report = json.loads(proc.stdout)
    rendered = "\n".join(report["errors"])
    assert "patent_freedom_to_operate" in rendered


def test_trademark_clearance_cannot_be_self_certified_as_internal_review():
    gate = load_gate_module()
    errors = gate._approval_errors("public_release", "trademark_clearance", {"status": "approved", "review_type": "internal-policy", "reviewed_by": "maintainer", "reviewed_at": "2026-08-24", "evidence": ["notes.md"]})
    assert any("qualified-counsel or rename" in error for error in errors)


def test_trademark_clearance_accepts_documented_rename_review():
    gate = load_gate_module()
    errors = gate._approval_errors("public_release", "trademark_clearance", {"status": "approved", "review_type": "rename", "reviewed_by": "project-maintainer", "reviewed_at": "2026-08-24", "evidence": ["TRADEMARKS.md", "CHANGELOG.md"]})
    assert errors == []


def test_patent_fto_requires_qualified_counsel_review_type():
    gate = load_gate_module()
    errors = gate._approval_errors("commercial_release", "patent_freedom_to_operate", {"status": "approved", "review_type": "internal-policy", "reviewed_by": "maintainer", "reviewed_at": "2026-08-24", "evidence": ["search-results.md"]})
    assert any("qualified-counsel" in error for error in errors)


def test_normal_approval_requires_reviewer_date_and_evidence():
    gate = load_gate_module()
    errors = gate._approval_errors("public_release", "privacy_disclosure", {"status": "approved", "review_type": "internal-policy"})
    assert any("reviewed_by" in error for error in errors)
    assert any("reviewed_at" in error for error in errors)
    assert any("evidence" in error for error in errors)


def test_pep639_metadata_requires_spdx_license_and_notice_files():
    gate = load_gate_module()
    valid = '''
[build-system]
requires = ["setuptools>=77.0.3", "wheel"]

[project]
license = "MIT"
license-files = ["LICENSE", "THIRD_PARTY_NOTICES.md"]
'''
    assert gate._license_metadata_errors(valid) == []
    legacy = valid.replace('license = "MIT"', 'license = {text = "MIT"}')
    assert any("PEP 639 SPDX" in error for error in gate._license_metadata_errors(legacy))
    missing_notice = valid.replace(', "THIRD_PARTY_NOTICES.md"', '')
    assert any("THIRD_PARTY_NOTICES.md" in error for error in gate._license_metadata_errors(missing_notice))


def test_pep639_metadata_requires_modern_setuptools():
    gate = load_gate_module()
    outdated = '''
[build-system]
requires = ["setuptools>=69", "wheel"]

[project]
license = "MIT"
license-files = ["LICENSE", "THIRD_PARTY_NOTICES.md"]
'''
    assert any("setuptools>=77.0.3" in error for error in gate._license_metadata_errors(outdated))
