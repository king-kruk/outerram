#!/usr/bin/env python3
"""Fail-closed privacy audit for the clean pre-public OuterRAM repository.

Run this only while the repository is still private. It verifies that every
reachable ref belongs to the new clean history and that no personal commit
email was imported into that history.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPECTED_ROOT = "d63f3f0abe492ee6ec4c633f4127c8e92d26f968"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def _noreply(email: str) -> bool:
    value = email.strip().lower()
    return value == "noreply@github.com" or value.endswith("@users.noreply.github.com")


def audit(expected_root: str = DEFAULT_EXPECTED_ROOT) -> list[str]:
    errors: list[str] = []
    if not SHA40.fullmatch(expected_root.lower()):
        return ["expected root must be a 40-character lowercase Git SHA"]

    roots = sorted(set(line for line in _git("rev-list", "--all", "--max-parents=0").splitlines() if line))
    if roots != [expected_root.lower()]:
        errors.append(
            "reachable history must have exactly the clean OuterRAM root "
            f"{expected_root}; found {roots or 'no roots'}"
        )

    # Include all local/remotely-fetched refs. The CI checkout uses fetch-depth: 0,
    # so this also covers publication/dependabot branches and PR merge refs fetched
    # for the run rather than checking only the current branch.
    records = _git("log", "--all", "--format=%H%x09%ae%x09%ce").splitlines()
    if not records:
        errors.append("no reachable commits found")
    for record in records:
        parts = record.split("\t")
        if len(parts) != 3:
            errors.append(f"could not parse commit identity record: {record!r}")
            continue
        sha, author_email, committer_email = parts
        if not _noreply(author_email):
            errors.append(f"{sha}: author email is not GitHub noreply: {author_email}")
        if not _noreply(committer_email):
            errors.append(f"{sha}: committer email is not GitHub noreply: {committer_email}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit clean pre-public Git history and commit privacy")
    parser.add_argument("--expected-root", default=DEFAULT_EXPECTED_ROOT)
    args = parser.parse_args()
    errors = audit(args.expected_root)
    if errors:
        print("pre-public history gate: FAIL")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"pre-public history gate: PASS (root {args.expected_root})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
