# Prior art and project boundary

OuterRAM exists in an active Apple-Silicon inference ecosystem. It does not claim to have invented SSD-backed inference, expert offload, MLX serving, or prompt caching.

## What OuterRAM is

OuterRAM is a **fail-closed orchestration, reproducibility, validation and benchmarking layer**. Its job is to inspect a concrete checkpoint and machine, choose an execution strategy, bootstrap tested runtime revisions, launch them behind a predictable local workflow, and make compatibility claims only after measurable gates pass.

It intentionally does not reimplement transformer math or vendor third-party runtime code in `0.3.0rc1`.

## Closest execution/runtime projects

- **MLX / MLX-LM** — the Apple ML framework and language-model runtime used as the resident baseline. MLX-LM's upstream work on MoE expert streaming is tracked separately; OuterRAM treats mature upstream support as preferable when available.
- **streamlx** — exact router-selected MoE expert SSD streaming using explicit safetensors byte-range reads, expert pools, coalescing and prefetch. This is OuterRAM's current MoE streaming runtime.
- **mlx-flash** — dense MLX weight/layer streaming while retaining native model logic. This is OuterRAM's current dense out-of-core runtime.
- **SwiftLM** — a native Swift/MLX OpenAI-compatible server with SSD expert streaming and KV-cache work. It is a serious alternative native engine and a possible future optional backend; OuterRAM does not copy or vendor it.
- **Astronomical** — a Rust/C++/MLX performance-first Mac runner with adaptive expert residency/paging, memory admission and persistent prompt reuse. It occupies the native-engine/product space; OuterRAM differentiates by orchestrating multiple independently maintained runtimes and recording reproducible compatibility evidence.

## Additional design references

- Apple, **LLM in a Flash** — flash-backed inference techniques.
- `doramirdor/mbolt` — routing-profile-driven expert layout/co-activation ordering for reducing explicit-read SSD I/O; interesting future preprocessing work, not part of the current execution path.
- `mu-hashmi/mlx-moe` — lazy expert loading, profiles and cache coverage experiments.
- Flash-MoE variants — custom Metal/C SSD-aware MoE experiments.
- FreeToken — heterogeneous execution, cache and memory-management ideas on NVIDIA/Linux.
- AirLLM — layer-wise out-of-core inference inspiration.
- oMLX — coding-agent server functionality, prompt/prefix caching and speculative decoding references.

## Current boundary

OuterRAM only presents a runtime as reproducible when:

1. the model is a **local, materialized checkpoint**;
2. a Hugging Face origin can be tied to an immutable revision where available;
3. the selected runtime matches OuterRAM's tested revision pins unless the user explicitly opts out;
4. compatibility checks pass for the model format, strategy and host;
5. real-hardware validation is recorded separately from package/unit-test validation.

A future backend or optimization is not added merely because its README reports a high benchmark. It must pass the same correctness, memory, tool-calling and reproducibility gates.

## Licensing

OuterRAM is MIT licensed. Current runtime dependencies are installed separately and retain their own licenses. No third-party inference implementation source is vendored in the current release candidate. Any future source copying, vendoring or patch distribution must preserve the upstream license and required notices.
