#!/usr/bin/env python3
"""Static legal/release-policy gate for OuterRAM.

This is a compliance aid, not legal advice. It deliberately fails closed for
public/validated/commercial modes while required human approvals are pending.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "LICENSE",
    "LEGAL.md",
    "TRADEMARKS.md",
    "THIRD_PARTY_NOTICES.md",
    "PRIVACY.md",
    "DCO.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "docs/MODEL_LICENSE_POLICY.md",
    "docs/PUBLICATION_CHECKLIST.md",
    "legal/APPROVED_COMPONENTS.json",
    "legal/LICENSE_OVERRIDES.json",
    "legal/RELEASE_APPROVALS.json",
    "scripts/dependency-license-report.py",
    "scripts/generate-sbom.py",
    "scripts/release-evidence.py",
    "scripts/security-gate.py",
    "scripts/verify-wheel-legal-metadata.py",
    "scripts/verify-release-artifacts.py",
)

PIN_NAMES = {
    "mlx-lm": "MLX_LM_REF",
    "mlx-flash": "MLX_FLASH_REF",
    "streamlx": "STREAMLX_REF",
}


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _load_json(path: str) -> dict:
    return json.loads(_read(path))


def _runtime_pins() -> dict[str, str]:
    text = _read("src/outerram/runtime_pins.py")
    pins: dict[str, str] = {}
    for component, symbol in PIN_NAMES.items():
        match = re.search(rf'^\s*{re.escape(symbol)}\s*=\s*["\']([0-9a-fA-F]{{40}})["\']\s*$', text, re.M)
        if match:
            pins[component] = match.group(1).lower()
    return pins


def _approval_errors(section: str, name: str, item: dict) -> list[str]:
    errors: list[str] = []
    if item.get("status") != "approved":
        return errors
    reviewed_by = str(item.get("reviewed_by", "")).strip()
    reviewed_at = str(item.get("reviewed_at", "")).strip()
    review_type = str(item.get("review_type", "")).strip()
    evidence = item.get("evidence")
    if not reviewed_by:
        errors.append(f"approved {section}.{name} missing reviewed_by")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", reviewed_at):
        errors.append(f"approved {section}.{name} missing valid reviewed_at YYYY-MM-DD")
    if not review_type:
        errors.append(f"approved {section}.{name} missing review_type")
    if not isinstance(evidence, list) or not evidence or not all(isinstance(x, str) and x.strip() for x in evidence):
        errors.append(f"approved {section}.{name} missing non-empty evidence list")
    if name == "trademark_clearance" and review_type not in {"qualified-counsel", "rename"}:
        errors.append("trademark_clearance approval must use review_type qualified-counsel or rename")
    if name == "patent_freedom_to_operate" and review_type != "qualified-counsel":
        errors.append("patent_freedom_to_operate approval must use review_type qualified-counsel")
    return errors


def _license_metadata_errors(pyproject: str) -> list[str]:
    errors: list[str] = []
    if not re.search(r'^\s*license\s*=\s*["\']MIT["\']\s*$', pyproject, re.M):
        errors.append("pyproject.toml must declare PEP 639 SPDX license = \"MIT\"")
    match = re.search(r'^\s*license-files\s*=\s*\[([^\]]*)\]\s*$', pyproject, re.M)
    if not match:
        errors.append("pyproject.toml must declare project.license-files")
    else:
        declared = set(re.findall(r'["\']([^"\']+)["\']', match.group(1)))
        for required in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
            if required not in declared:
                errors.append(f"pyproject.toml license-files missing {required}")
    build_match = re.search(r'^\s*requires\s*=\s*\[([^\]]*)\]\s*$', pyproject, re.M)
    if not build_match or not re.search(r'setuptools\s*>=\s*77(?:\.0\.3)?', build_match.group(1), re.I):
        errors.append("build-system must require setuptools>=77.0.3 for PEP 639 metadata support")
    return errors


def _check_section_shape(approvals: dict, section: str, errors: list[str]) -> None:
    values = approvals.get(section, {})
    if not isinstance(values, dict):
        errors.append(f"approval section {section} must be an object")
        return
    for name, item in values.items():
        if not isinstance(item, dict):
            errors.append(f"approval entry {section}.{name} must be an object")
            continue
        errors.extend(_approval_errors(section, name, item))


def _require_section(approvals: dict, section: str, label: str, errors: list[str]) -> None:
    for name, item in approvals.get(section, {}).items():
        if not isinstance(item, dict) or item.get("status") != "approved":
            status = item.get("status", "missing") if isinstance(item, dict) else "invalid"
            note = item.get("note", "") if isinstance(item, dict) else ""
            errors.append(f"{label} blocker {name}: {status} — {note}")


def run(mode: str) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    for path in REQUIRED_FILES:
        if not (ROOT / path).is_file():
            errors.append(f"missing required legal/release file: {path}")
    if (ROOT / "LICENSE").is_file() and "MIT License" not in _read("LICENSE"):
        errors.append("project LICENSE is not the expected MIT license text")
    if (ROOT / "pyproject.toml").is_file():
        errors.extend(_license_metadata_errors(_read("pyproject.toml")))
    if (ROOT / "TRADEMARKS.md").is_file():
        trademarks = _read("TRADEMARKS.md")
        for marker in ("not affiliated", "OpenAI-compatible", "OuterRAM", "former provisional"):
            if marker.lower() not in trademarks.lower():
                errors.append(f"TRADEMARKS.md missing required marker: {marker}")

    manifest = _load_json("legal/APPROVED_COMPONENTS.json") if (ROOT / "legal/APPROVED_COMPONENTS.json").is_file() else {}
    components = {entry.get("name"): entry for entry in manifest.get("components", []) if isinstance(entry, dict)}
    actual_pins = _runtime_pins()
    for component, symbol in PIN_NAMES.items():
        actual = actual_pins.get(component)
        expected = components.get(component, {}).get("revision")
        if not actual:
            errors.append(f"could not parse runtime pin {symbol}")
        elif not expected:
            errors.append(f"approved-component manifest missing revision for {component}")
        elif actual != str(expected).lower():
            errors.append(f"runtime pin drift for {component}: code={actual} legal-manifest={expected}")

    if (ROOT / "legal/LICENSE_OVERRIDES.json").is_file():
        overrides = _load_json("legal/LICENSE_OVERRIDES.json")
        seen: set[tuple[str, str]] = set()
        for item in overrides.get("overrides", []):
            if not isinstance(item, dict):
                errors.append("license override entry must be an object")
                continue
            package = str(item.get("package", "")).strip().lower()
            version = str(item.get("version", "")).strip()
            license_text = str(item.get("license", "")).strip()
            source = str(item.get("source", "")).strip()
            revision = str(item.get("revision", "")).strip().lower()
            evidence = str(item.get("evidence", "")).strip()
            key = (package, version)
            if not all((package, version, license_text, source, evidence)):
                errors.append("license override missing package/version/license/source/evidence")
            if key in seen:
                errors.append(f"duplicate license override for {package} {version}")
            seen.add(key)
            if package in actual_pins:
                if revision != actual_pins[package]:
                    errors.append(f"license override revision drift for {package}: override={revision or 'missing'} pin={actual_pins[package]}")
                approved_license = str(components.get(package, {}).get("license", "")).strip()
                if approved_license and license_text != approved_license:
                    errors.append(f"license override mismatch for {package}: override={license_text} approved={approved_license}")

    approvals = _load_json("legal/RELEASE_APPROVALS.json") if (ROOT / "legal/RELEASE_APPROVALS.json").is_file() else {}
    for section in ("public_release", "validated_release", "commercial_release"):
        _check_section_shape(approvals, section, errors)
    if mode in {"public", "validated", "commercial"}:
        _require_section(approvals, "public_release", "public release", errors)
    if mode == "validated":
        _require_section(approvals, "validated_release", "validated release", errors)
    if mode == "commercial":
        _require_section(approvals, "commercial_release", "commercial release", errors)
    if mode == "internal":
        pending = []
        for section in ("public_release", "validated_release", "commercial_release"):
            for name, item in approvals.get(section, {}).items():
                if not isinstance(item, dict) or item.get("status") != "approved":
                    status = item.get("status", "missing") if isinstance(item, dict) else "invalid"
                    pending.append(f"{section}.{name}={status}")
        if pending:
            warnings.append("pending human/legal approvals: " + ", ".join(pending))
    return {
        "mode": mode,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "disclaimer": "Automated compliance aid only; not legal advice or a legal opinion.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="OuterRAM legal/release policy gate")
    parser.add_argument("--mode", choices=("internal", "public", "validated", "commercial"), default="internal")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run(args.mode)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"legal gate ({args.mode}): {'PASS' if result['ok'] else 'FAIL'}")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
        for error in result["errors"]:
            print(f"ERROR: {error}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
