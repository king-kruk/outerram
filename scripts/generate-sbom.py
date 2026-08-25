#!/usr/bin/env python3
"""Generate a deterministic CycloneDX SBOM from reviewed Python inventory data."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import urllib.parse
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LICENSE_REPORT = ROOT / "scripts" / "dependency-license-report.py"


def _purl(name: str, version: str) -> str:
    normalized = name.lower().replace("_", "-").replace(".", "-")
    return f"pkg:pypi/{urllib.parse.quote(normalized, safe='-')}@{urllib.parse.quote(version, safe='.-_')}"


def _component(row: dict) -> dict:
    name = str(row["name"])
    version = str(row["version"])
    license_text = str(row.get("license") or "UNKNOWN")
    component = {
        "type": "library", "bom-ref": _purl(name, version), "name": name,
        "version": version, "purl": _purl(name, version),
        "licenses": [{"license": {"name": license_text}}],
        "properties": [{"name": "org.outerram.license_source", "value": str(row.get("license_source") or "unknown")}],
    }
    if row.get("declared_license") is not None:
        component["properties"].append({"name": "org.outerram.declared_license", "value": str(row["declared_license"])})
    if row.get("override_evidence"):
        component["properties"].append({"name": "org.outerram.license_override_evidence", "value": str(row["override_evidence"])})
    if row.get("override_revision"):
        component["properties"].append({"name": "org.outerram.license_override_revision", "value": str(row["override_revision"])})
    return component


def build_sbom(report: dict, root_name: str, root_version: str) -> dict:
    components = [_component(row) for row in report.get("packages", []) if str(row.get("name", "")).lower() != root_name.lower()]
    components.sort(key=lambda item: (item["name"].lower(), item["version"]))
    identity = json.dumps({"root": [root_name, root_version], "components": [(c["name"], c["version"], c["licenses"]) for c in components]}, sort_keys=True, separators=(",", ":"))
    serial = uuid.uuid5(uuid.NAMESPACE_URL, "https://outerram.local/sbom/" + identity)
    root_ref = _purl(root_name, root_version)
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.6", "serialNumber": f"urn:uuid:{serial}", "version": 1,
        "metadata": {
            "tools": {"components": [{"type": "application", "name": "OuterRAM SBOM generator"}]},
            "component": {"type": "application", "bom-ref": root_ref, "name": root_name, "version": root_version, "purl": root_ref},
            "properties": [{"name": "org.outerram.note", "value": "Inventory evidence only; not legal advice or a license-compatibility opinion."}],
        },
        "components": components,
        "dependencies": [{"ref": root_ref, "dependsOn": [component["bom-ref"] for component in components]}],
    }


def _inventory(overrides: Path | None, inventory: Path | None) -> dict:
    if inventory is not None:
        return json.loads(inventory.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "licenses.json"
        cmd = [sys.executable, str(LICENSE_REPORT), "--output", str(output)]
        if overrides is not None:
            cmd.extend(["--overrides", str(overrides)])
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or proc.stdout or "dependency license inventory failed")
        return json.loads(output.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a deterministic CycloneDX 1.6 SBOM")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--root-name", default="outerram")
    parser.add_argument("--root-version", required=True)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--inventory", type=Path, help="Reuse an existing dependency-license-report JSON instead of rescanning")
    args = parser.parse_args()
    report = _inventory(args.overrides, args.inventory)
    sbom = build_sbom(report, args.root_name, args.root_version)
    args.output.write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"CycloneDX SBOM: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
