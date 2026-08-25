from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate-sbom.py"


def load_module():
    spec = importlib.util.spec_from_file_location("outerram_generate_sbom", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cyclonedx_sbom_is_deterministic_and_excludes_root_duplicate():
    module = load_module()
    report = {"packages": [
        {"name": "outerram", "version": "0.3.0rc1", "license": "MIT", "license_source": "package_metadata"},
        {"name": "huggingface-hub", "version": "1.0.0", "license": "Apache-2.0", "license_source": "package_metadata"},
    ]}
    first = module.build_sbom(report, "outerram", "0.3.0rc1")
    second = module.build_sbom(report, "outerram", "0.3.0rc1")
    assert first == second
    assert first["bomFormat"] == "CycloneDX"
    assert first["specVersion"] == "1.6"
    assert first["serialNumber"].startswith("urn:uuid:")
    assert first["metadata"]["component"]["name"] == "outerram"
    assert [component["name"] for component in first["components"]] == ["huggingface-hub"]
    assert first["dependencies"][0]["dependsOn"] == [first["components"][0]["bom-ref"]]


def test_sbom_preserves_reviewed_override_evidence():
    module = load_module()
    report = {"packages": [{"name": "streamlx", "version": "0.1.0", "license": "MIT", "license_source": "reviewed_override", "declared_license": "UNKNOWN", "override_evidence": "LICENSE", "override_revision": "1" * 40}]}
    sbom = module.build_sbom(report, "outerram", "0.3.0rc1")
    props = {item["name"]: item["value"] for item in sbom["components"][0]["properties"]}
    assert props["org.outerram.license_source"] == "reviewed_override"
    assert props["org.outerram.declared_license"] == "UNKNOWN"
    assert props["org.outerram.license_override_evidence"] == "LICENSE"
    assert props["org.outerram.license_override_revision"] == "1" * 40
