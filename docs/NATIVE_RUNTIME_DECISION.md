# Native runtime decision

OuterRAM remains a Python orchestration layer for the current runtime stack.

## Decision

Do **not** rewrite the control plane in Go before physical profiling.

The current execution backends (`mlx-lm`, `mlx-flash`, and `streamlx`) are Python-facing. A Go launcher would therefore either keep Python runtime processes behind an IPC boundary or introduce a C bridge without removing the memory-heavy inference runtime. That adds implementation and failure surface before evidence shows it buys meaningful memory.

Instead, `outerram serve` performs a POSIX process replacement when launching the selected runtime. The planning/CLI interpreter is removed from the steady-state process tree rather than waiting as a parent process for the inference server.

## Native options if profiling justifies them

If physical Apple Silicon measurements show the Python-facing runtime itself is a material memory or latency bottleneck, investigate a direct MLX-native backend through the official C++, C, or Swift APIs. That would be an execution-backend project, not a cosmetic control-plane rewrite.

A native backend is justified only after measurements isolate a recoverable cost that is large enough to matter relative to model weights, KV cache, Metal allocations, streaming cache, and macOS memory pressure.

## Required measurements

Physical qualification must record, at minimum:

- process tree and per-process resident memory before model load;
- runtime RSS after model load and during generation;
- peak unified-memory pressure and swap;
- model/quantization/revision and context length;
- resident vs streamed strategy;
- TTFT and decode throughput;
- SSD throughput/latency for streamed paths.

The goal is to optimize measured bottlenecks, not language choice in isolation.
