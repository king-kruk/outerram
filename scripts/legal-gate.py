#!/usr/bin/env python3
"""Static legal and supply-chain gate for OuterRAM.

This is an engineering compliance aid, not legal advice. It validates durable
repository facts: project license metadata, required policy files, reviewed
runtime pins and explicit license overrides. Human/commercial approvals are not
stored as machine-certifiable source files.
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
    "legal/APPROVED_COMPONENTS.json",
    "legal/LICENSE_OVERRIDES.json",
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


def _license_metadata_errors(pyproject: str) -> list[str]:
    errors: list[str] = []
    if not re.search(r'^\s*license\s*=\s*["\']MIT["\']\s*$', pyproject, re.M):
        errors.append('pyproject.toml must declare PEP 639 SPDX license = "MIT"')
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
        trademarks = _read("TRADEMARKS.md").lower()
        for marker in ("not affiliated", "openai-compatible", "outerram"):
            if marker not in trademarks:
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

    if mode == "public":
        warnings.append("Static repository checks do not constitute trademark, patent, FTO, or model-use legal clearance.")

    return {
        "mode": mode,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "disclaimer": "Automated compliance aid only; not legal advice or a legal opinion.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="OuterRAM legal and supply-chain policy gate")
    parser.add_argument("--mode", choices=("internal", "public"), default="internal")
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
