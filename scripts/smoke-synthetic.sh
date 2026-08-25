#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cat > "$TMP/config.json" <<'JSON'
{"model_type":"qwen_dense","architectures":["QwenForCausalLM"],"quantization_config":{"bits":3}}
JSON
truncate -s 1M "$TMP/model.safetensors"
PYTHONPATH="$ROOT/src" python -m outerram.cli inspect "$TMP" --json >/dev/null
PYTHONPATH="$ROOT/src" python -m outerram.cli plan "$TMP" --json >/dev/null
PYTHONPATH="$ROOT/src" python -m outerram.cli serve "$TMP" --dry-run >/dev/null
PYTHONPATH="$ROOT/src" python -m outerram.cli --version >/dev/null
echo "OuterRAM synthetic smoke: PASS"
