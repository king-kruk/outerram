#!/usr/bin/env python3
"""Create deterministic release and supply-chain evidence for an OuterRAM commit.

The artifact records machine-verifiable repository state. It is not legal
advice and deliberately does not encode human trademark, patent or FTO approval.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGAL_GATE = ROOT / "scripts" / "legal-gate.py"

EVIDENCE_FILES = (
    "LICENSE",
    "LEGAL.md",
    "TRADEMARKS.md",
    "THIRD_PARTY_NOTICES.md",
    "PRIVACY.md",
    "DCO.md",
    "SECURITY.md",
    "docs/MODEL_LICENSE_POLICY.md",
    "legal/APPROVED_COMPONENTS.json",
    "legal/LICENSE_OVERRIDES.json",
)

PIN_NAMES = {
    "mlx-lm": "MLX_LM_REF",
    "mlx-flash": "MLX_FLASH_REF",
    "streamlx": "STREAMLX_REF",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project = text.split("[project]", 1)[1]
    match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', project, re.M)
    if not match:
        raise RuntimeError("could not resolve project version")
    return match.group(1)


def runtime_pins() -> dict[str, str]:
    text = (ROOT / "src" / "outerram" / "runtime_pins.py").read_text(encoding="utf-8")
    result: dict[str, str] = {}
    for component, symbol in PIN_NAMES.items():
        match = re.search(rf'^\s*{re.escape(symbol)}\s*=\s*["\']([0-9a-fA-F]{{40}})["\']\s*$', text, re.M)
        if not match:
            raise RuntimeError(f"could not resolve runtime pin {symbol}")
        result[component] = match.group(1).lower()
    return result


def git_commit() -> str:
    proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False)
    value = proc.stdout.strip()
    if proc.returncode != 0 or not re.fullmatch(r"[0-9a-fA-F]{40}", value):
        raise RuntimeError(proc.stderr.strip() or "could not resolve git commit")
    return value.lower()


def gate_results() -> dict[str, dict]:
    spec = importlib.util.spec_from_file_location("outerram_legal_gate_evidence", LEGAL_GATE)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load legal gate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {mode: module.run(mode) for mode in ("internal", "public")}


def build_evidence(commit: str) -> dict:
    hashes: dict[str, str] = {}
    for relative in EVIDENCE_FILES:
        path = ROOT / relative
        if not path.is_file():
            raise RuntimeError(f"required evidence file missing: {relative}")
        hashes[relative] = sha256_file(path)

    return {
        "schema_version": 2,
        "project": "OuterRAM",
        "version": project_version(),
        "git_commit": commit.lower(),
        "project_license": "MIT",
        "runtime_pins": runtime_pins(),
        "legal_gate_results": gate_results(),
        "evidence_file_sha256": hashes,
        "statements": {
            "model_weights_bundled": False,
            "legal_clearance_inferred_from_model_metadata": False,
            "human_legal_clearance_encoded": False,
            "artifact_is_legal_opinion": False,
        },
        "note": "Deterministic machine-verifiable release evidence only; trademark, patent, FTO and model-use rights require separate human review where applicable.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate OuterRAM release and supply-chain evidence")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--commit")
    args = parser.parse_args()

    commit = args.commit or git_commit()
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        raise SystemExit("--commit must be a 40-character Git SHA")
    data = build_evidence(commit)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Release evidence: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
