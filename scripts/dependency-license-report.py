#!/usr/bin/env python3
"""Generate a machine-readable license inventory for the installed environment.

The report is evidence for human review. It does not decide whether a license is
legally compatible with a particular distribution/business model.

A reviewed override may replace UNKNOWN package metadata only when package name
and version match exactly. The override remains visible in the report together
with its evidence instead of pretending the upstream package declared it.
"""

from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import re
from pathlib import Path
from typing import Any

RISK_MARKERS = (
    "AGPL",
    "Affero",
    "GPL",
    "SSPL",
    "BUSL",
    "Business Source",
    "Non-Commercial",
    "Noncommercial",
    "Research Only",
)

IGNORE = {"pip", "setuptools", "wheel"}


def normalized_license(dist: md.Distribution) -> str:
    meta = dist.metadata
    expr = meta.get("License-Expression")
    if expr:
        return expr.strip()
    value = meta.get("License")
    if value and value.strip() and value.strip().upper() != "UNKNOWN":
        return value.strip()
    classifiers = [c for c in meta.get_all("Classifier", []) if c.startswith("License ::")]
    return "; ".join(classifiers) if classifiers else "UNKNOWN"


def load_overrides(path: Path | None) -> dict[tuple[str, str], dict[str, Any]]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for item in data.get("overrides", []):
        if not isinstance(item, dict):
            continue
        package = str(item.get("package", "")).strip().lower()
        version = str(item.get("version", "")).strip()
        license_text = str(item.get("license", "")).strip()
        evidence = str(item.get("evidence", "")).strip()
        source = str(item.get("source", "")).strip()
        revision = str(item.get("revision", "")).strip()
        if not package or not version or not license_text or not evidence or not source:
            raise ValueError("license override requires package, version, license, source, and evidence")
        # Git-backed overrides used by OuterRAM must remain immutable/reviewable.
        if revision and not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
            raise ValueError(f"invalid immutable revision in license override for {package} {version}")
        key = (package, version)
        if key in result:
            raise ValueError(f"duplicate license override for {package} {version}")
        result[key] = item
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--fail-on-risk", action="store_true")
    parser.add_argument("--fail-on-unknown", action="store_true")
    args = parser.parse_args()

    overrides = load_overrides(args.overrides)
    packages = []
    risky = []
    unknown = []
    used_overrides = []

    for dist in sorted(md.distributions(), key=lambda d: (d.metadata.get("Name") or "").lower()):
        name = dist.metadata.get("Name") or "UNKNOWN"
        if name.lower() in IGNORE:
            continue
        declared = normalized_license(dist)
        license_text = declared
        row: dict[str, Any] = {
            "name": name,
            "version": dist.version,
            "license": license_text,
            "license_source": "package_metadata",
        }

        override = overrides.get((name.lower(), dist.version))
        if declared == "UNKNOWN" and override is not None:
            license_text = str(override["license"])
            row.update(
                license=license_text,
                license_source="reviewed_override",
                declared_license="UNKNOWN",
                override_evidence=override.get("evidence"),
                override_evidence_url=override.get("evidence_url"),
                override_source=override.get("source"),
                override_revision=override.get("revision"),
                override_reason=override.get("reason"),
            )
            used_overrides.append(
                {
                    "name": name,
                    "version": dist.version,
                    "license": license_text,
                    "source": override.get("source"),
                    "revision": override.get("revision"),
                    "evidence": override.get("evidence"),
                    "evidence_url": override.get("evidence_url"),
                }
            )

        packages.append(row)
        if license_text == "UNKNOWN":
            unknown.append(name)
        if any(re.search(re.escape(marker), license_text, re.I) for marker in RISK_MARKERS):
            risky.append(row)

    report = {
        "schema_version": 2,
        "packages": packages,
        "reviewed_overrides_applied": used_overrides,
        "risky_or_review_required": risky,
        "unknown_license_metadata": unknown,
        "note": "Inventory only. Reviewed overrides repair missing package metadata for exact package/version evidence; human/legal review remains required for release decisions.",
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    failed = (args.fail_on_risk and bool(risky)) or (args.fail_on_unknown and bool(unknown))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
