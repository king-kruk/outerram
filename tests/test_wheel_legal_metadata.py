from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-wheel-legal-metadata.py"


def load_module():
    spec = importlib.util.spec_from_file_location("outerram_wheel_legal", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_wheel(path: Path, *, metadata_version: str = "2.4", license_expression: str | None = "MIT", legacy_license: str | None = None, license_files: tuple[str, ...] = ("LICENSE", "THIRD_PARTY_NOTICES.md"), archive_license_files: tuple[str, ...] = ("LICENSE", "THIRD_PARTY_NOTICES.md")) -> None:
    metadata_lines = [f"Metadata-Version: {metadata_version}", "Name: outerram", "Version: 0.3.0rc1"]
    if license_expression is not None:
        metadata_lines.append(f"License-Expression: {license_expression}")
    if legacy_license is not None:
        metadata_lines.append(f"License: {legacy_license}")
    metadata_lines.extend(f"License-File: {item}" for item in license_files)
    metadata = "\n".join(metadata_lines) + "\n\n"
    dist_info = "outerram-0.3.0rc1.dist-info"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(f"{dist_info}/METADATA", metadata)
        for item in archive_license_files:
            zf.writestr(f"{dist_info}/licenses/{item}", f"placeholder {item}\n")


def test_valid_pep639_wheel_passes(tmp_path: Path):
    module = load_module()
    wheel = tmp_path / "outerram.whl"
    build_wheel(wheel)
    assert module.wheel_legal_metadata_errors(wheel) == []


def test_missing_third_party_notice_fails(tmp_path: Path):
    module = load_module()
    wheel = tmp_path / "outerram.whl"
    build_wheel(wheel, license_files=("LICENSE",), archive_license_files=("LICENSE",))
    assert any("THIRD_PARTY_NOTICES.md" in error for error in module.wheel_legal_metadata_errors(wheel))


def test_legacy_license_field_fails(tmp_path: Path):
    module = load_module()
    wheel = tmp_path / "outerram.whl"
    build_wheel(wheel, legacy_license="MIT")
    assert any("legacy License metadata" in error for error in module.wheel_legal_metadata_errors(wheel))


def test_metadata_version_before_24_fails(tmp_path: Path):
    module = load_module()
    wheel = tmp_path / "outerram.whl"
    build_wheel(wheel, metadata_version="2.3")
    assert any("Metadata-Version" in error for error in module.wheel_legal_metadata_errors(wheel))
