from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dependency-license-report.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dependency_license_report", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reviewed_override_requires_exact_package_version(tmp_path: Path):
    module = load_module()
    path = tmp_path / "overrides.json"
    path.write_text(json.dumps({"overrides": [{"package": "streamlx", "version": "0.1.0", "license": "MIT", "source": "srcterm/streamlx", "revision": "146507b59293058b3a1cecc43f47947b25012297", "evidence": "LICENSE at pinned revision"}]}), encoding="utf-8")
    overrides = module.load_overrides(path)
    assert ("streamlx", "0.1.0") in overrides
    assert ("streamlx", "0.1.1") not in overrides


def test_reviewed_override_rejects_nonimmutable_git_revision(tmp_path: Path):
    module = load_module()
    path = tmp_path / "overrides.json"
    path.write_text(json.dumps({"overrides": [{"package": "streamlx", "version": "0.1.0", "license": "MIT", "source": "srcterm/streamlx", "revision": "main", "evidence": "LICENSE"}]}), encoding="utf-8")
    with __import__("pytest").raises(ValueError, match="immutable revision"):
        module.load_overrides(path)


def test_repository_override_is_locked_to_streamlx_pin():
    data = json.loads((ROOT / "legal" / "LICENSE_OVERRIDES.json").read_text(encoding="utf-8"))
    item = data["overrides"][0]
    from outerram.runtime_pins import STREAMLX_REF
    assert item["package"] == "streamlx"
    assert item["version"] == "0.1.0"
    assert item["license"] == "MIT"
    assert item["revision"] == STREAMLX_REF
