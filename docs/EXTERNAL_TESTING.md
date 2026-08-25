# External tester guide

OuterRAM `0.3.0rc1` is a technical release candidate for Apple Silicon. It is not a claim that every runtime/model combination works on every Mac, and technical compatibility is not legal clearance for any model.

## 0. Virtual qualification

```bash
outerram simulate --json
outerram simulate-matrix --json
```

These commands exercise planner/API contracts without claiming physical Metal or SSD performance.

## 1. Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
outerram --version
```

Expected version: `0.3.0rc1`.

## 2. Inspect the host

```bash
outerram doctor --json > doctor.json
```

Real execution requires supported Apple Silicon + macOS. Planning/package tests may run elsewhere.

## 3. Materialize an immutable checkpoint

```bash
REMOTE=owner/model
LOCAL="$(outerram fetch "$REMOTE" --path-only)"
outerram inspect "$LOCAL" --json > model.json
```

Review the exact model/revision license separately. Download success is not permission for commercial use or redistribution.

## 4. Plan and launch

```bash
outerram plan "$LOCAL" --json > plan.json
outerram check "$LOCAL"
outerram bootstrap "$LOCAL"
outerram ready "$LOCAL" --json > ready.json
outerram serve "$LOCAL" --port 8080
```

## 5. Qualify the running API

```bash
outerram probe --base-url http://127.0.0.1:8080/v1 --tool-call
outerram qualify \
  --base-url http://127.0.0.1:8080/v1 \
  --checkpoint "$LOCAL" \
  --disk-path "$(dirname "$LOCAL")" \
  --output qualification.json
```

A passing API/environment qualification is still not a blanket performance claim. Keep the exact model revision, host, strategy, runtime pins and evidence with any published result.

## Transition alias

The former private-development CLI name `stretchmlx` is retained only for the `0.3.0rc1` compatibility window. New testing and documentation must use `outerram`.
