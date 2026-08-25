# Runtime references and dependency policy

OuterRAM does **not** vendor third-party inference implementation code. It orchestrates separately installed runtimes and studies public techniques from the projects below.

Primary execution dependencies:

- `ml-explore/mlx-lm` — Apple MLX model loading/generation, tokenizers and tool-call parsers.
- `matt-k-wong/mlx-flash` — dense out-of-core MLX weight/layer streaming.
- `srcterm/streamlx` — exact router-selected MoE expert SSD streaming with range coalescing and prefetch.

Research/design references:

- Apple “LLM in a Flash” — flash-backed inference techniques.
- `Anemll/anemll-flash-mlx` — expert slot-bank experiments on Apple Silicon.
- `mu-hashmi/mlx-moe` — lazy experts, profiling/pinning and MLX MoE serving.
- `danveloper/flash-moe` and related forks — C/Metal SSD-aware MoE inference.
- `FlashML-org/FreeToken` — bandwidth-adaptive heterogeneous execution and cache/memory ideas; currently NVIDIA/Linux focused.
- `lyogavin/airllm` — layer-wise out-of-core inference inspiration.
- `jundot/omlx` — coding-agent serving, SSD KV/prefix cache and speculative-decoding ideas. Its DFlash feature is speculative decoding, not dense weight offload.
- `SharpAI/SwiftLM` — native Swift/custom-MLX SSD expert streaming, Metal primitives and compressed KV experiments; useful evidence for a future native backend.
- `aosama/astronomical` — native Rust/C++/MLX adaptive expert residency + SSD paging and persistent prompt reuse; a close native-engine comparison point rather than code vendored by OuterRAM.
- `doramirdor/mbolt` — routing-profile/co-activation-aware expert layout experiments for reducing explicit-read SSD I/O; future preprocessing research.
- MLX-LM issue `#1438` / PR `#1588` — upstream discussion and an unmerged expert-offload primitive; important prior art for lazy-load and disk-backed expert caches.

## Reproducibility

`outerram bootstrap` defaults to tested Git revisions recorded in `outerram.runtime_pins`. Users can inspect them with:

```bash
outerram pins --json
```

`--latest` deliberately opts into upstream HEAD and therefore weaker reproducibility.

## Licensing

OuterRAM's MIT license applies only to OuterRAM code. Runtime projects are installed as independent dependencies and retain their own licenses and notices. Before any future vendoring, copying, or modification of third-party source, the relevant license must be reviewed and required attribution/notices preserved.
