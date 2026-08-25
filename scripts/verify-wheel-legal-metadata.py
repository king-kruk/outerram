#!/usr/bin/env python3
"""Verify that a built wheel carries the expected PEP 639 legal metadata."""

from __future__ import annotations

import argparse
import sys
import zipfile
from email.parser import BytesParser
from email.policy import compat32
from pathlib import Path

EXPECTED_LICENSE = "MIT"
EXPECTED_LICENSE_FILES = {"LICENSE", "THIRD_PARTY_NOTICES.md"}


def _metadata_version_tuple(value: str) -> tuple[int, int] | None:
    try:
        major, minor = value.strip().split(".", 1)
        return int(major), int(minor)
    except (AttributeError, TypeError, ValueError):
        return None


def wheel_legal_metadata_errors(wheel: Path) -> list[str]:
    errors: list[str] = []
    try:
        with zipfile.ZipFile(wheel) as zf:
            names = set(zf.namelist())
            metadata_members = [name for name in names if name.endswith(".dist-info/METADATA")]
            if len(metadata_members) != 1:
                return [f"wheel must contain exactly one METADATA file, found {metadata_members}"]

            metadata_name = metadata_members[0]
            metadata = BytesParser(policy=compat32).parsebytes(zf.read(metadata_name))
            metadata_version = _metadata_version_tuple(metadata.get("Metadata-Version", ""))
            if metadata_version is None or metadata_version < (2, 4):
                errors.append(f"wheel Metadata-Version must be >=2.4 for PEP 639 fields, got {metadata.get('Metadata-Version')!r}")

            if metadata.get("License-Expression") != EXPECTED_LICENSE:
                errors.append(f"wheel License-Expression must be {EXPECTED_LICENSE!r}, got {metadata.get('License-Expression')!r}")
            if metadata.get("License"):
                errors.append("wheel must not emit legacy License metadata when License-Expression is present")

            declared = set(metadata.get_all("License-File", []))
            missing_declared = EXPECTED_LICENSE_FILES - declared
            if missing_declared:
                errors.append("wheel METADATA missing License-File declarations: " + ", ".join(sorted(missing_declared)))

            dist_info = metadata_name.rsplit("/", 1)[0]
            for legal_file in sorted(EXPECTED_LICENSE_FILES):
                member = f"{dist_info}/licenses/{legal_file}"
                if member not in names:
                    errors.append(f"wheel archive missing legal file: {member}")
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"cannot inspect wheel {wheel}: {exc}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args(argv)

    errors = wheel_legal_metadata_errors(args.wheel)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Wheel legal metadata: PASS ({args.wheel.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
