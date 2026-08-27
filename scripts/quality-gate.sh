#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git diff --check
  GENERATED=$(git ls-files | grep -E '(^build/|^dist/|__pycache__|\.egg-info/|\.pyc$)' || true)
  if [ -n "$GENERATED" ]; then
    echo "Tracked generated artifacts are not allowed:" >&2
    echo "$GENERATED" >&2
    exit 1
  fi
fi

python scripts/legal-gate.py --mode internal
python scripts/security-gate.py
python -m pytest -q
python -m compileall -q src/outerram tests scripts
./scripts/smoke-synthetic.sh

rm -rf build dist src/*.egg-info
python -m pip wheel . --no-deps --no-build-isolation -w dist >/dev/null
WHEEL=$(ls dist/outerram-*.whl | head -1)
[ -n "$WHEEL" ]
python scripts/verify-wheel-legal-metadata.py "$WHEEL"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
python -m pip install --no-deps --target "$TMP/site" "$WHEEL" >/dev/null
(
  cd "$TMP"
  PYTHONPATH="$TMP/site${PYTHONPATH:+:$PYTHONPATH}" python -m outerram.cli --version
  PYTHONPATH="$TMP/site${PYTHONPATH:+:$PYTHONPATH}" python -m outerram.cli pins --json >/dev/null
)

echo "OuterRAM quality gate: PASS"
