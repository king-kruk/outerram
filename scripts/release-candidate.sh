#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

STATUS="$(git status --porcelain --untracked-files=normal)"
if [ -n "$STATUS" ]; then
  echo "Release candidate packaging requires a clean worktree." >&2
  echo "$STATUS" >&2
  echo "Commit, ignore, or remove changes, then rerun." >&2
  exit 1
fi

./scripts/quality-gate.sh

VERSION="$(PYTHONPATH=src python -c 'from outerram import __version__; print(__version__)')"
COMMIT="$(git rev-parse HEAD)"
mkdir -p dist
WHEEL="$(ls dist/outerram-${VERSION}-*.whl 2>/dev/null | head -1 || true)"
if [ -z "$WHEEL" ]; then
  echo "Expected wheel for OuterRAM ${VERSION} was not produced." >&2
  exit 1
fi
python scripts/verify-wheel-legal-metadata.py "$WHEEL"

SOURCE="dist/outerram-${VERSION}-source.zip"
git archive --format=zip --prefix="outerram-${VERSION}/" HEAD > "$SOURCE"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python -m zipfile -e "$SOURCE" "$TMP"
(
  cd "$TMP/outerram-${VERSION}"
  python -m pytest -q
  python -m compileall -q src/outerram tests
  bash ./scripts/smoke-synthetic.sh
)

VENV="$TMP/wheel-env"
python -m venv "$VENV"
"$VENV/bin/python" -m pip install -q "$WHEEL"
LICENSE_INVENTORY="$TMP/dependency-licenses.json"
"$VENV/bin/python" scripts/dependency-license-report.py \
  --overrides legal/LICENSE_OVERRIDES.json \
  --output "$LICENSE_INVENTORY" \
  --fail-on-risk --fail-on-unknown

SBOM="dist/SBOM.cdx.json"
"$VENV/bin/python" scripts/generate-sbom.py \
  --inventory "$LICENSE_INVENTORY" \
  --root-name outerram \
  --root-version "$VERSION" \
  --output "$SBOM"

EVIDENCE="dist/RELEASE-EVIDENCE.json"
python scripts/release-evidence.py --commit "$COMMIT" --output "$EVIDENCE"

SUMS="dist/SHA256SUMS.txt"
if command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "$WHEEL" "$SOURCE" "$SBOM" "$EVIDENCE" | sed 's#  dist/#  #' > "$SUMS"
elif command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$WHEEL" "$SOURCE" "$SBOM" "$EVIDENCE" | sed 's#  dist/#  #' > "$SUMS"
else
  echo "Neither shasum nor sha256sum is available." >&2
  exit 1
fi

MANIFEST="dist/RELEASE-MANIFEST.json"
python - "$VERSION" "$COMMIT" "$WHEEL" "$SOURCE" "$SUMS" "$SBOM" "$EVIDENCE" > "$MANIFEST" <<'PY'
import json, pathlib, sys
version, commit, wheel, source, sums, sbom, evidence = sys.argv[1:]
print(json.dumps({
    "schema_version": 3,
    "project": "OuterRAM",
    "version": version,
    "git_commit": commit,
    "artifacts": {
        "wheel": pathlib.Path(wheel).name,
        "source": pathlib.Path(source).name,
        "checksums": pathlib.Path(sums).name,
        "sbom": pathlib.Path(sbom).name,
        "release_evidence": pathlib.Path(evidence).name,
    },
    "local_release_gates": {
        "quality_gate": "pass",
        "source_archive_extract_test": "pass",
        "synthetic_smoke": "pass",
        "wheel_legal_metadata": "pass",
        "dependency_license_inventory": "pass",
        "sbom_generation": "pass",
        "release_evidence_generation": "pass",
        "artifact_integrity": "pending-until-verifier",
    },
    "network_ci_gates": {
        "full_validation": "required-before-hardware-validated-release",
    },
    "physical_apple_silicon_validation": "pending",
}, indent=2, sort_keys=True))
PY

python scripts/verify-release-artifacts.py \
  --wheel "$WHEEL" --source "$SOURCE" --manifest "$MANIFEST" --checksums "$SUMS" \
  --sbom "$SBOM" --evidence "$EVIDENCE"

python - "$MANIFEST" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
data["local_release_gates"]["artifact_integrity"] = "pass"
path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

python scripts/verify-release-artifacts.py \
  --wheel "$WHEEL" --source "$SOURCE" --manifest "$MANIFEST" --checksums "$SUMS" \
  --sbom "$SBOM" --evidence "$EVIDENCE"

printf 'OuterRAM %s release candidate: PASS\n' "$VERSION"
printf '  commit: %s\n' "$COMMIT"
printf '  %s\n' "$WHEEL" "$SOURCE" "$SBOM" "$EVIDENCE" "$SUMS" "$MANIFEST"
