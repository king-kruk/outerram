#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== OuterRAM pre-public visibility gate =="
python scripts/pre-public-history-gate.py
python scripts/security-gate.py
python scripts/legal-gate.py --mode pre-public
./scripts/quality-gate.sh

echo "OuterRAM pre-public visibility gate: PASS"
echo "Repository source is ready for a visibility change; complete public-only GitHub controls immediately after the change and before announcement."
