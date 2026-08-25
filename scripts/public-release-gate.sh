#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== OuterRAM public source publication gate =="
python scripts/security-gate.py
python scripts/legal-gate.py --mode public
./scripts/quality-gate.sh

echo "Public source publication gate PASS"
