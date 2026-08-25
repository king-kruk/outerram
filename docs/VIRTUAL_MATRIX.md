# Virtual hardware/stress matrix

OuterRAM retains a deterministic planner matrix for pre-hardware validation. It exists to find strategy-boundary bugs before a physical Mac is available; it is **not** a hardware benchmark.

## Profiles

- `m4-16gb`
- `m5-16gb`
- `m5-24gb`
- `m5-32gb`
- `m5-pro-48gb`
- `m5-max-64gb`

The chip labels and SSD figures are synthetic planning profiles. Only memory capacity and planner inputs are used to exercise OuterRAM behavior.

## Scenarios

- `baseline` — default reserve and healthy telemetry;
- `heavy-ide` — +1 GiB protected headroom for IDE/agent tooling;
- `long-context` — +2.5 GiB conservative reserve at a modeled 64K context;
- `swap-pressure` — pre-existing 2 GiB swap and 7% free-memory signal;
- `slow-ssd` — synthetic 70–75% SSD throughput reduction to exercise storage-risk advisories;
- `footprint-plus-10pct` — +10% effective weight footprint sensitivity.

The long-context reserve is intentionally conservative. It is not presented as a measured Qwen KV-cache allocation.

## Run

```bash
outerram simulate --json
outerram simulate-matrix --json
```

Limit the matrix when investigating one boundary:

```bash
outerram simulate-matrix \
  --profiles m5-16gb m5-24gb \
  --scenarios baseline heavy-ide long-context slow-ssd \
  --json
```

## Transition target-model result

For `lukaskremla/Qwen3.8-27B-3bit-MLX-TextOnly`:

| Virtual profile | Baseline | Heavy IDE | Long context | Slow SSD setup |
|---|---|---|---|---|
| M4 16 GiB | resident | dense-stream | dense-stream | dense-stream |
| M5 16 GiB | resident | dense-stream | dense-stream | dense-stream |
| M5 24 GiB | resident | resident | resident | resident |
| M5 32 GiB | resident | resident | resident | resident |
| M5 Pro 48 GiB | resident | resident | resident | resident |
| M5 Max 64 GiB | resident | resident | resident | resident |

The built-in model profile records public license metadata as descriptive provenance only. It does not bundle model weights and does not represent legal clearance for use or redistribution.

A streamed row with a synthetic SSD rate below the matrix threshold is marked as storage-risk, but that classification never becomes a physical performance claim.

## What remains impossible to simulate faithfully

- Metal kernel execution and architecture-specific performance;
- Apple unified-memory allocator behavior;
- real macOS compression/swap dynamics;
- thermal/power throttling;
- internal/external SSD latency under the exact expert/layer access pattern;
- real TTFT, decode tokens/sec and coding-agent stability.
