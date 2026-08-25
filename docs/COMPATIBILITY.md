# Compatibility contract

OuterRAM distinguishes **detected compatibility** from **measured validation**.

## Execution host

Current execution adapters target **Apple Silicon macOS**.

Minimum host requirements for the pinned transition runtime stack:

- Apple Silicon (M-series Mac).
- **macOS 14.0 (Sonoma) or newer.** This follows the official MLX 0.32.1 installation requirement.
- Native Python 3.10+ for OuterRAM/resident/MoE paths.
- Python 3.11+ for `dense-stream` with pinned `mlx-flash` v0.4.x.

OuterRAM checks the detected macOS version as part of its fail-closed compatibility gate. macOS 13.x and older are rejected before real execution. If the macOS version cannot be parsed, execution is also rejected rather than assuming compatibility.

Linux/other hosts are supported for planning, tests and package development only. OuterRAM does not currently expose MLX's Linux/CUDA backends as execution strategies.

## Checkpoint formats

| Format | Current execution |
|---|---|
| MLX/safetensors | Primary path |
| Sharded safetensors | Supported for sizing/inspection; runtime support depends on adapter |
| Single GGUF | Inspected but execution rejected by current adapters |
| Multiple GGUF variants | Size intentionally reported unknown; user must select a concrete quantization in a future GGUF adapter |

## Strategy requirements

### resident

- Apple Silicon.
- macOS 14.0+.
- **Local materialized checkpoint**; remote Hugging Face IDs are discovery/fetch inputs, not execution inputs.
- Model architecture supported by the installed `mlx-lm` revision.
- Checkpoint working set should fit below OuterRAM's conservative resident budget.

### dense-stream

- Apple Silicon.
- macOS 14.0+.
- **Local materialized checkpoint** tied to an immutable revision when it originated from Hugging Face.
- Python 3.11+ for the pinned `mlx-flash` runtime.
- MLX/safetensors-oriented model supported by `mlx-flash`/MLX.
- Quantized 3–4 bit checkpoints are strongly preferred for practical coding latency.

### moe-stream

- Apple Silicon.
- macOS 14.0+.
- **Local materialized** MLX model directory.
- Standard `SwitchGLU`-style expert layout compatible with `streamlx`; known public validation includes Qwen3.6/qwen3_5_moe, Laguna and kimi_linear families.
- Exact Top-K routing remains enabled.

## Empirical matrix

A row should only be marked validated after a physical run records:

| Mac | RAM | macOS | Model + revision | Quant | Strategy | Context | SSD | Peak memory | Swap | TTFT | tok/s | Tool calls | Result |
|---|---:|---|---|---|---|---:|---|---:|---:|---:|---:|---|---|
| pending | | | | | | | | | | | | | |

Upstream project benchmarks are useful design evidence but do not count as an OuterRAM validation row.
