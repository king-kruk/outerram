#!/usr/bin/env python3
"""Fail-closed verification for OuterRAM release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".safetensors", ".gguf", ".bin", ".npz"}
FORBIDDEN_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "build", "dist", "models"}
FORBIDDEN_BASENAMES = {".env", ".DS_Store"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_checksums(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(.+)", raw)
        if not match:
            raise ValueError(f"malformed checksum line: {raw!r}")
        digest, name = match.groups()
        out[name] = digest.lower()
    return out


def unsafe_member(name: str) -> str | None:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        return "unsafe archive path"
    if any(part in FORBIDDEN_PARTS or part.endswith(".egg-info") for part in path.parts):
        return "generated/private directory"
    if path.name in FORBIDDEN_BASENAMES or path.name.startswith(".env."):
        return "environment/OS artifact"
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        return "generated/model-weight artifact"
    return None


def validate_zip_members(path: Path) -> list[str]:
    errors: list[str] = []
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            reason = unsafe_member(name)
            if reason:
                errors.append(f"{path.name}: {name}: {reason}")
    return errors


def wheel_version(wheel: Path) -> str:
    with zipfile.ZipFile(wheel) as zf:
        metadata = [n for n in zf.namelist() if n.endswith(".dist-info/METADATA")]
        if len(metadata) != 1:
            raise ValueError(f"wheel must contain exactly one METADATA file, found {metadata}")
        text = zf.read(metadata[0]).decode("utf-8")
    match = re.search(r"^Version:\s*(\S+)\s*$", text, re.MULTILINE)
    if not match:
        raise ValueError("wheel METADATA has no Version field")
    return match.group(1)


def source_version(source: Path) -> str:
    with zipfile.ZipFile(source) as zf:
        pyprojects = [n for n in zf.namelist() if n.endswith("/pyproject.toml")]
        if len(pyprojects) != 1:
            raise ValueError(f"source archive must contain exactly one pyproject.toml, found {pyprojects}")
        text = zf.read(pyprojects[0]).decode("utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', text, re.MULTILINE)
    if not match:
        raise ValueError("source pyproject.toml has no project version")
    return match.group(1)


def validate_sbom(path: Path, version: str) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"SBOM JSON: {exc}"]
    if data.get("bomFormat") != "CycloneDX":
        errors.append("SBOM bomFormat must be CycloneDX")
    if data.get("specVersion") != "1.6":
        errors.append("SBOM specVersion must be 1.6")
    component = data.get("metadata", {}).get("component", {})
    if component.get("name") != "outerram":
        errors.append("SBOM root component name must be outerram")
    if component.get("version") != version:
        errors.append("SBOM root component version does not match manifest")
    if not isinstance(data.get("components"), list):
        errors.append("SBOM components must be a list")
    return errors


def validate_release_evidence(path: Path, version: str, commit: str) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"release evidence JSON: {exc}"]
    if data.get("project") != "OuterRAM":
        errors.append("release evidence project must be OuterRAM")
    if data.get("version") != version:
        errors.append("release evidence version does not match manifest")
    if str(data.get("git_commit", "")).lower() != commit.lower():
        errors.append("release evidence git_commit does not match manifest")
    if data.get("project_license") != "MIT":
        errors.append("release evidence project_license must be MIT")
    if data.get("statements", {}).get("artifact_is_legal_opinion") is not False:
        errors.append("release evidence must explicitly state that it is not a legal opinion")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wheel", required=True, type=Path)
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--checksums", required=True, type=Path)
    ap.add_argument("--sbom", type=Path)
    ap.add_argument("--evidence", type=Path)
    args = ap.parse_args(argv)

    errors: list[str] = []
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    version = str(manifest.get("version", ""))
    commit = str(manifest.get("git_commit", ""))
    if manifest.get("project") != "OuterRAM":
        errors.append("manifest project must be OuterRAM")
    if not version:
        errors.append("manifest has no version")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        errors.append("manifest has no valid git_commit")

    expected_names = {"wheel": args.wheel.name, "source": args.source.name, "checksums": args.checksums.name}
    if args.sbom is not None:
        expected_names["sbom"] = args.sbom.name
    if args.evidence is not None:
        expected_names["release_evidence"] = args.evidence.name
    for key, expected in expected_names.items():
        actual = manifest.get("artifacts", {}).get(key)
        if actual != expected:
            errors.append(f"manifest artifacts.{key}={actual!r}, expected {expected!r}")

    try:
        if wheel_version(args.wheel) != version:
            errors.append("wheel METADATA version does not match manifest")
    except Exception as exc:
        errors.append(f"wheel metadata: {exc}")
    try:
        if source_version(args.source) != version:
            errors.append("source pyproject version does not match manifest")
    except Exception as exc:
        errors.append(f"source metadata: {exc}")

    errors.extend(validate_zip_members(args.wheel))
    errors.extend(validate_zip_members(args.source))
    if args.sbom is not None:
        errors.extend(validate_sbom(args.sbom, version))
    if args.evidence is not None:
        errors.extend(validate_release_evidence(args.evidence, version, commit))

    checksum_artifacts = [args.wheel, args.source]
    if args.sbom is not None:
        checksum_artifacts.append(args.sbom)
    if args.evidence is not None:
        checksum_artifacts.append(args.evidence)
    try:
        sums = parse_checksums(args.checksums)
        for artifact in checksum_artifacts:
            expected = sums.get(artifact.name)
            actual = sha256(artifact)
            if expected is None:
                errors.append(f"checksum missing for {artifact.name}")
            elif expected != actual:
                errors.append(f"checksum mismatch for {artifact.name}")
    except Exception as exc:
        errors.append(f"checksums: {exc}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OuterRAM {version} release artifacts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
