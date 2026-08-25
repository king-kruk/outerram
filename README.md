# OuterRAM

**Bigger models. Same Mac.**

OuterRAM is a fail-closed orchestration and compatibility layer for running large local LLMs on Apple Silicon — including models whose weights do not safely fit in unified memory.

It does not reimplement model math. OuterRAM inspects the Mac and checkpoint, reserves headroom for macOS/IDE/KV cache/runtime work, validates the selected path, and launches a compatible runtime.

> **Release candidate:** `0.3.0rc1`. Package, planner, API, security and virtual qualification are automated. Real Metal/performance claims remain hardware- and model-specific until physical Apple Silicon qualification is recorded.

## How it works

| Model state | Strategy | Runtime |
|---|---|---|
| Fits safely in unified memory | `resident` | `mlx-lm` |
| Dense model exceeds safe RAM budget | `dense-stream` | `mlx-flash` + OuterRAM local API server |
| MoE model exceeds safe RAM budget | `moe-stream` | `streamlx` exact expert streaming |

OuterRAM intentionally fails closed when it cannot prove that a model/runtime/host combination is compatible.

## Supported platforms and current limits

OuterRAM is **not tied to one Mac configuration**. The planner uses the detected host, available unified memory, macOS/Python versions, checkpoint format and model architecture.

| Host / capability | Status | Notes |
|---|---|---|
| Apple Silicon M-series Macs | ✅ Supported host class | M1/M2/M3/M4/M5 families, including Pro/Max/Ultra variants; exact runtime/model compatibility is checked at runtime. |
| Different unified-memory sizes | ✅ Supported | No single RAM size is hard-coded. |
| macOS 14.0+ | ✅ Supported | Current minimum for the pinned MLX runtime stack. |
| macOS 13.x or older | ❌ Execution unsupported | Fails closed before real runtime execution. |
| Intel Macs | ❌ Execution unsupported | Current adapters require Apple Silicon. |
| Linux / Windows | ⚠️ Planning/tests only | No real MLX execution backend is exposed there today. |
| Python 3.10+ | ✅ Core/resident/MoE | `dense-stream` requires Python 3.11+. |
| MLX / safetensors checkpoints | ✅ Primary format | Completeness and architecture are validated before launch. |
| Dense models | ✅ | Resident or dense streaming when the pinned backend supports the family. |
| MoE models | ✅ Compatible families | Resident or exact expert streaming through `streamlx`. |
| GGUF | ⚠️ Inspect only | Execution is rejected instead of silently guessing an unsupported backend. |

**Supported does not mean every model is guaranteed to run on every Mac.** Size, architecture, quantization, context length, available memory, runtime support and storage performance still matter. Use `outerram doctor`, `outerram check` and `outerram ready` on the actual machine.

See [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) for the full contract.

## Install for development / source testing

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
outerram --version
```

For contributors:

```bash
python -m pip install -e '.[dev]'
./scripts/quality-gate.sh
python scripts/legal-gate.py --mode internal
```

## Basic workflow

Real execution requires a local materialized checkpoint so inspection and launch cannot silently resolve different remote revisions.

```bash
outerram doctor
REMOTE=owner/model
LOCAL="$(outerram fetch "$REMOTE" --path-only)"
outerram inspect "$LOCAL"
outerram plan "$LOCAL"
outerram bootstrap "$LOCAL"
outerram ready "$LOCAL"
outerram serve "$LOCAL" --port 8080
```

Then verify the running API:

```bash
outerram probe --base-url http://127.0.0.1:8080/v1 --tool-call
outerram benchmark --base-url http://127.0.0.1:8080/v1
outerram qualify \
  --base-url http://127.0.0.1:8080/v1 \
  --checkpoint "$LOCAL" \
  --disk-path "$(dirname "$LOCAL")" \
  --output qualification.json
```

## Virtual qualification

When physical Apple Silicon is unavailable, OuterRAM can test planner boundaries and API contracts without pretending simulation is a hardware benchmark:

```bash
outerram simulate --json
outerram simulate-matrix --json
```

Simulation results always identify themselves as synthetic and do not authorize Metal, throughput, thermal or SSD performance claims. See [docs/VIRTUAL_MATRIX.md](docs/VIRTUAL_MATRIX.md).

## Safety-first defaults

OuterRAM is designed for a single-user local workstation and deliberately favors refusal over guessing:

- execution uses a local materialized checkpoint;
- incomplete/ambiguous checkpoints fail validation;
- model snapshots do not automatically download repository Python code;
- strategy overrides do not bypass compatibility checks;
- non-loopback plaintext HTTP serving is refused by default;
- API keys are not sent to remote plaintext HTTP endpoints;
- request sizes, tokens and server concurrency are bounded;
- disk benchmarks have hard size limits and free-space safety slack;
- runtime bootstrap uses reviewed immutable upstream revisions by default;
- managed StreamLX checkouts are verified for origin, revision and local modifications.

Read [SECURITY.md](SECURITY.md) before exposing any endpoint outside localhost.

## Local OpenAI-compatible API

The dense-stream adapter exposes a local compatibility interface:

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`
- SSE streaming
- token usage when available
- structured tool-call round trips where supported
- optional Bearer authentication

“OpenAI-compatible” describes protocol shape only. OuterRAM is not an OpenAI product and does not require OpenAI services for local inference.

## Runtime reproducibility

```bash
outerram pins --json
outerram bootstrap <local-model> --dry-run
outerram upstream-check --json
```

`--latest` is an explicit opt-out from tested upstream pins; `ready`/`serve` then require `--allow-unpinned`.

## Security and supply chain

Routine PR CI includes:

- repository secret/action-pin policy checks;
- Bandit static security analysis;
- unit/regression tests and compile checks;
- synthetic smoke tests;
- wheel build and legal metadata verification;
- dependency-license inventory and CycloneDX SBOM generation;
- `pip-audit` vulnerability scanning.

GitHub Actions are pinned to immutable commit SHAs. CodeQL is configured for the public-repository phase. See [SECURITY.md](SECURITY.md) and [docs/PUBLICATION_CHECKLIST.md](docs/PUBLICATION_CHECKLIST.md).

## Rename / compatibility window

OuterRAM was developed privately under the provisional name **StretchMLX**. The project was renamed before public launch so the product name no longer embeds the name of Apple's MLX framework.

For **one transition release (`0.3.0rc1`) only**:

- `outerram` is the canonical command and package identity;
- the `stretchmlx` CLI entry point remains as a deprecated compatibility alias;
- `OUTERRAM_API_KEY` is canonical, while the previous environment variable may still be read internally for migration;
- legacy private-test metadata/cache locations may still be recognized.

New integrations should use only `outerram` / `OuterRAM` / `OUTERRAM_*`. The compatibility alias is scheduled for removal after the transition window.

## Legal / third-party software

OuterRAM code is MIT licensed. Runtime projects and model weights retain their own licenses and are not relicensed by OuterRAM. Model availability or technical compatibility is not legal clearance for a model.

OuterRAM is independent and **not affiliated with, endorsed by, sponsored by, or certified by Apple, OpenAI, Hugging Face, model vendors, or third-party runtime maintainers**.

See [LEGAL.md](LEGAL.md), [TRADEMARKS.md](TRADEMARKS.md), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), [PRIVACY.md](PRIVACY.md), and [docs/MODEL_LICENSE_POLICY.md](docs/MODEL_LICENSE_POLICY.md).

## Validation levels

OuterRAM separates claims that are often mixed together:

1. **Package validated** — tests/build/security gates pass.
2. **Runtime compatible** — host/model/adapter pass compatibility checks.
3. **Inference validated** — a real model runs correctly on physical Apple Silicon.
4. **Coding-agent validated** — tools, multi-turn work, TTFT/throughput and stability meet the scenario.
5. **Publication/commercial reviewed** — separate repository, legal and commercial gates are satisfied.

Source publication does not imply level 3 or 4 performance validation.

## Project docs

- [Architecture](docs/ARCHITECTURE.md)
- [Compatibility](docs/COMPATIBILITY.md)
- [External testing](docs/EXTERNAL_TESTING.md)
- [Physical Mac validation](docs/MAC_VALIDATION.md)
- [Virtual matrix](docs/VIRTUAL_MATRIX.md)
- [Publication checklist](docs/PUBLICATION_CHECKLIST.md)
- [Release checklist](docs/RELEASE_CHECKLIST.md)
- [Prior art](docs/PRIOR_ART.md)

**OuterRAM — run bigger local models than your memory can hold.**
