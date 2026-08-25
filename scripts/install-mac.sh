#!/bin/zsh
set -euo pipefail

ROOT="${0:A:h:h}"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "OuterRAM inference requires macOS on Apple Silicon." >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required. Install Python 3.11+ (3.12 recommended) and rerun this script." >&2
  exit 3
fi

if ! python3 - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
then
  echo "The convenience installer requires Python 3.11+ so every current runtime strategy is available." >&2
  echo "Install Python 3.11+ (3.12 recommended), then rerun. OuterRAM core itself can be installed manually on 3.10." >&2
  exit 3
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is required to install the tested runtime revisions." >&2
  echo "On macOS, install Command Line Tools (for example: xcode-select --install) and rerun." >&2
  exit 4
fi

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .

echo
echo "OuterRAM installed."
echo "Activate: source $ROOT/.venv/bin/activate"
echo "Next: outerram doctor"
