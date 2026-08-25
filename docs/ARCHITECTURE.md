# Architecture

OuterRAM is intentionally an **orchestration layer**, not a fourth inference engine.

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
                  \          |          /
                   probe / benchmark
```

## Planner

The planner subtracts an explicit memory reserve for macOS, IDE/tools, KV cache and runtime overhead. A second safety margin is applied before calling a model resident. The result is intentionally conservative because checkpoint bytes are not peak working-set bytes.

## Dense out-of-core

Dense transformers activate essentially all model layers for each token, so MoE expert caching does not apply. The dense strategy delegates weight/layer streaming to `mlx-flash`, which patches native MLX model layers instead of rebuilding architecture math. OuterRAM supplies a uniform local chat API, validation and security layer around it.

## MoE out-of-core

For sparse MoE models, only router-selected experts are needed at each layer/token. `streamlx` keeps the trunk resident and maintains a bounded expert pool. Cache misses are fetched from safetensors byte ranges. OuterRAM's policy is **exact routing**: a missing required expert is fetched, not dropped for speed.

## API boundary

OuterRAM targets a common OpenAI-style `/v1/chat/completions` workflow for coding clients. The custom dense adapter translates tokenizer-specific tool-call control syntax through `mlx-lm`'s tokenizer parser when available.

## Future integrations

Potential additions are intentionally adapter-based:

- richer resident serving through oMLX (Responses/Anthropic/SSD prefix cache);
- llama.cpp/GGUF adapter;
- MTP/speculative decoding when supported by the selected model/runtime;
- machine-readable empirical compatibility database;
- dynamic RAM budget tuning from live memory pressure;
- optional native Swift/Metal backend research informed by SwiftLM, with full-quality routing required by default.

Performance features are strategy-aware: speculative/MTP decoding should not be enabled automatically on SSD-streamed MoE paths because verification can multiply unique expert reads and erase the compute-side speedup.
