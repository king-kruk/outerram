#!/usr/bin/env python3
"""Cheap fail-closed checks for secrets and GitHub Actions supply-chain policy.

This complements (not replaces) GitHub secret scanning, CodeQL and dependency
vulnerability scanning. It is intentionally dependency-free so it runs on every PR.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("github-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("huggingface-token", re.compile(r"\bhf_[A-Za-z0-9]{20,}\b")),
    ("openai-style-secret", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
)

ACTION_LINE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)")
FULL_SHA = re.compile(r"^[0-9a-fA-F]{40}$")

TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".json", ".sh",
    ".ps1", ".ini", ".cfg", ".conf", ".xml", ".csv", ".jinja",
}
TEXT_NAMES = {"LICENSE", "Dockerfile", ".gitignore", ".gitattributes"}


def tracked_files() -> list[Path]:
    proc = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, stdout=subprocess.PIPE)
    return [ROOT / item.decode() for item in proc.stdout.split(b"\0") if item]


def is_text_candidate(path: Path) -> bool:
    return path.name in TEXT_NAMES or path.suffix.lower() in TEXT_SUFFIXES


def scan_secrets(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        if path.resolve() == SELF or not is_text_candidate(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        relative = path.relative_to(ROOT)
        for name, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"{relative}:{line}: possible {name}")
    return errors


def scan_actions(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    workflow_root = ROOT / ".github" / "workflows"
    for path in paths:
        try:
            path.resolve().relative_to(workflow_root.resolve())
        except ValueError:
            continue
        if path.suffix.lower() not in {".yml", ".yaml"}:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        relative = path.relative_to(ROOT)
        for lineno, line in enumerate(lines, 1):
            match = ACTION_LINE.match(line)
            if not match:
                continue
            action = match.group(1)
            if action.startswith("./"):
                continue
            if "@" not in action:
                errors.append(f"{relative}:{lineno}: external action is missing an immutable ref")
                continue
            _, ref = action.rsplit("@", 1)
            if not FULL_SHA.fullmatch(ref):
                errors.append(f"{relative}:{lineno}: external action must be pinned to a full 40-character commit SHA")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="OuterRAM repository security policy gate")
    parser.parse_args()
    paths = tracked_files()
    errors = scan_secrets(paths) + scan_actions(paths)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"security gate: PASS ({len(paths)} tracked files checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
