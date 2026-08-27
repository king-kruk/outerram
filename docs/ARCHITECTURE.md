# Architecture

OuterRAM is intentionally an **orchestration layer**, not another inference engine.

```text
                     model + machine
                           |
                    inspect / doctor
                           |
                         planner
                           |
                   compatibility gate
                  /          |          \
                 /           |           \
          resident      dense-stream     moe-stream
          mlx-lm         mlx-flash        streamlx
                            |                |
                     OuterRAM OAI       upstream OAI
                    compatibility API      serving
```

## Planner

The planner subtracts explicit headroom for macOS, IDE/tools, KV cache and runtime work. A second safety margin is applied before a model is classified as resident. Checkpoint bytes are not treated as equivalent to peak working-set bytes.

## Runtime handoff

Planning and inference are separate phases. Once `serve` has selected and validated a runtime, OuterRAM has no reason to keep the orchestration interpreter resident.

On POSIX hosts, including macOS, OuterRAM therefore uses `exec`-style process replacement:

```text
outerram CLI + planner
        |
        | validate + build launch spec
        v
     exec()
        |
        +----> selected runtime (same PID)
```

The CLI/planner process is replaced rather than left waiting as a parent. This removes avoidable steady-state launcher memory, preserves normal signal handling, and avoids adding a second control-plane runtime beside the inference engine.

Windows currently supports planning and diagnostics only; the portable subprocess fallback remains for non-POSIX execution paths and tests.

## Dense out-of-core

Dense transformers activate essentially all model layers for each token, so MoE expert caching does not apply. The dense strategy delegates weight/layer streaming to the pinned `mlx-flash` runtime. OuterRAM supplies a small stdlib-based OpenAI-compatible API layer around the runtime so it does not require an additional FastAPI/uvicorn stack.

## MoE out-of-core

For sparse MoE models, only router-selected experts are needed at each layer/token. `streamlx` keeps the trunk resident and maintains a bounded expert pool. Cache misses are fetched from safetensors byte ranges. OuterRAM's policy is **exact routing**: a required expert is fetched, not silently dropped for speed.

## API boundary

OuterRAM targets an OpenAI-style `/v1/chat/completions` workflow for coding clients. The dense adapter translates tokenizer-specific tool-call syntax through the tokenizer parser when the selected stack exposes one.

## Language/runtime decision

OuterRAM remains Python-first for the current execution architecture.

A Go rewrite of only the control plane would not remove the Python inference runtimes selected today (`mlx-lm`, the pinned `mlx-flash`, and `streamlx`). It would require either a second process/IPC boundary or a Go-to-C bridge while the dominant model, KV-cache and Metal allocations remain unchanged. Process replacement removes the avoidable control-plane residency without adding that complexity.

MLX provides official Python, C++, C and Swift APIs. A future fully native backend is technically viable, but it becomes valuable only if profiling shows that Python overhead **inside the inference engine** is material. Such a backend would need to reproduce the required streaming/cache/routing behavior rather than simply port the CLI.

Decision order for future optimization:

1. measure physical process footprint, swap and system memory pressure;
2. optimize/remove avoidable orchestration residency;
3. optimize backend cache/streaming behavior where measurements identify a bottleneck;
4. consider Swift/C++/C native execution only if the remaining Python runtime itself is a material constraint.

## Future integrations

Potential additions remain adapter-based:

- richer resident serving when a compatible runtime materially improves the API contract;
- llama.cpp/GGUF execution adapter;
- MTP/speculative decoding when supported by the selected model/runtime;
- machine-readable empirical compatibility results;
- dynamic RAM budget tuning from live memory pressure;
- native MLX backend research after physical profiling justifies it.

Performance features remain strategy-aware: speculative/MTP decoding should not be enabled automatically on SSD-streamed MoE paths when verification can multiply unique expert reads and erase compute-side gains.
