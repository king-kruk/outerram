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


def test_internal_legal_gate_passes_static_repository_checks():
    proc = run_gate("internal")
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(proc.stdout)
    assert report["ok"] is True
    assert report["errors"] == []


def test_public_gate_passes_but_does_not_claim_legal_clearance():
    proc = run_gate("public")
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(proc.stdout)
    assert report["ok"] is True
    warnings = "\n".join(report["warnings"]).lower()
    assert "constitute" in warnings
    assert "legal clearance" in warnings
    assert "trademark" in warnings
    assert "patent" in warnings


def test_removed_human_approval_modes_are_not_cli_modes():
    proc = run_gate("commercial")
    assert proc.returncode != 0
    assert "invalid choice" in proc.stderr


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
