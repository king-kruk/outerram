# OuterRAM

**Bigger models. Same Mac.**

OuterRAM is a fail-closed orchestration layer for running large local LLMs on Apple Silicon, including models whose weights do not safely fit in unified memory.

OuterRAM does not reimplement model math. It inspects the host and checkpoint, reserves memory headroom, validates a compatible execution path, and hands control to the selected MLX runtime.

> **Release candidate:** `0.3.0rc3`. Package, planner, API, security, Windows diagnostics, and virtual qualification are automated. Real inference and performance claims still require physical Apple Silicon validation.

## How it works

| Model state | Strategy | Runtime |
|---|---|---|
| Fits safely in unified memory | `resident` | `mlx-lm` |
| Dense model exceeds safe RAM budget | `dense-stream` | `mlx-flash` + OuterRAM local API |
| MoE model exceeds safe RAM budget | `moe-stream` | `streamlx` exact expert streaming |

OuterRAM intentionally fails closed when it cannot prove that a host/model/runtime combination is compatible.

On macOS and other POSIX hosts, `outerram serve` **replaces the orchestration process with the selected runtime** instead of keeping a waiting OuterRAM parent alive. The planner and CLI therefore do not remain as an avoidable second Python process during steady-state inference.

## Supported platforms

| Host / capability | Status | Notes |
|---|---|---|
| Apple Silicon Macs | ✅ Execution target | M-series Macs; exact model/runtime compatibility is checked at runtime. |
| macOS 14.0+ | ✅ | Current minimum for the pinned MLX stack. |
| Intel Macs | ❌ | Current execution adapters require Apple Silicon. |
| Linux / Windows | ⚠️ Planning/tests | Host inspection and planning work; MLX execution is not exposed there. |
| Python 3.10+ | ✅ Core | `dense-stream` requires Python 3.11+. |
| MLX / safetensors checkpoints | ✅ | Completeness and architecture are validated before launch. |
| Dense models | ✅ | Resident or dense streaming when the pinned backend supports the family. |
| MoE models | ✅ Compatible families | Resident or exact expert streaming through `streamlx`. |
| GGUF | ⚠️ Inspect only | Execution is rejected rather than guessed. |

Supported does not mean every model will run on every Mac. Architecture, quantization, context length, available memory, runtime support and storage performance still matter.

See [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) for the compatibility contract.

## Install

### `uv` (recommended)

```bash
uv tool install outerram
outerram --version
```

### `pipx`

```bash
pipx install outerram
outerram --version
```

Release candidates are published on PyPI.

## Basic workflow

Real execution uses a materialized local checkpoint so inspection and launch cannot silently resolve different remote revisions.

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

Verify the running API:

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

When physical Apple Silicon is unavailable, OuterRAM can exercise planner boundaries and API contracts without presenting synthetic numbers as hardware benchmarks:

```bash
outerram simulate --json
outerram simulate-matrix --json
```

Simulation output is explicitly marked synthetic and never authorizes Metal, throughput, thermal or SSD performance claims. See [docs/VIRTUAL_MATRIX.md](docs/VIRTUAL_MATRIX.md).

## Safety-first defaults

OuterRAM is designed for a local workstation and favors refusal over guessing:

- execution uses a materialized local checkpoint;
- incomplete or ambiguous checkpoints fail validation;
- model snapshots do not automatically execute repository Python code;
- strategy overrides do not bypass compatibility checks;
- non-loopback plaintext HTTP serving is refused by default;
- request sizes, tokens and server concurrency are bounded;
- disk benchmarks have size limits and free-space slack;
- runtime bootstrap uses reviewed immutable upstream revisions by default;
- managed StreamLX checkouts are verified for origin, revision and local modifications.

Read [SECURITY.md](SECURITY.md) before exposing any endpoint outside localhost.

## Local OpenAI-compatible API

The dense-stream adapter exposes:

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`
- SSE streaming
- token usage when available
- structured tool-call round trips where supported
- optional Bearer authentication

“OpenAI-compatible” describes protocol shape only. OuterRAM is independent and does not require OpenAI services for local inference.

## Runtime reproducibility

```bash
outerram pins --json
outerram bootstrap <local-model> --dry-run
outerram upstream-check --json
```

`--latest` explicitly opts out of tested upstream pins; `ready` and `serve` then require `--allow-unpinned`.

## Why the orchestration layer stays in Python

The execution stack OuterRAM currently selects — `mlx-lm`, the pinned `mlx-flash`, and `streamlx` — is Python-facing. Rewriting only the OuterRAM control plane in Go would still require those runtimes and would either add another resident process or introduce a C/IPC bridge without removing the dominant model/Metal allocations.

MLX also provides official C++, C and Swift APIs. A fully native backend may become worthwhile if physical profiling shows material Python-runtime overhead inside the actual inference engine, but that would require replacing or reimplementing backend behavior rather than merely rewriting the CLI. Until measurements justify that cost, OuterRAM removes its own steady-state launcher overhead with POSIX process replacement and keeps runtime integration direct.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Development

```bash
git clone https://github.com/king-kruk/outerram.git
cd outerram
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[dev]'
./scripts/quality-gate.sh
```

Routine CI includes static security analysis, tests, compile checks, synthetic smoke tests, Windows host-detection regression coverage, package validation, dependency-license inventory, SBOM generation and vulnerability auditing.

## Legal / third-party software

OuterRAM code is MIT licensed. Runtime projects and model weights retain their own licenses and are not relicensed by OuterRAM. Technical compatibility is not legal clearance for a model.

OuterRAM is independent and **not affiliated with, endorsed by, sponsored by, or certified by Apple, OpenAI, Hugging Face, model vendors, or third-party runtime maintainers**.

See [LEGAL.md](LEGAL.md), [TRADEMARKS.md](TRADEMARKS.md), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), [PRIVACY.md](PRIVACY.md), and [docs/MODEL_LICENSE_POLICY.md](docs/MODEL_LICENSE_POLICY.md).

## Validation levels

1. **Package validated** — tests/build/security gates pass.
2. **Runtime compatible** — host/model/adapter pass compatibility checks.
3. **Inference validated** — a real model runs correctly on physical Apple Silicon.
4. **Workload validated** — tools, multi-turn work, memory, TTFT/throughput and stability meet the target scenario.

Source publication does not imply level 3 or 4 performance validation.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Compatibility](docs/COMPATIBILITY.md)
- [External testing](docs/EXTERNAL_TESTING.md)
- [Physical Mac validation](docs/MAC_VALIDATION.md)
- [Virtual matrix](docs/VIRTUAL_MATRIX.md)
- [Prior art](docs/PRIOR_ART.md)

**OuterRAM — run bigger local models than your memory can hold.**
