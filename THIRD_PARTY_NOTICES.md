# Third-party notices

_Last reviewed: 2026-08-25._

OuterRAM is licensed under MIT. That license applies to OuterRAM code only.

OuterRAM currently orchestrates third-party runtimes instead of vendoring their implementation. Each runtime is installed separately and remains subject to its own license, notices, trademarks, and upstream terms.

| Component | Tested revision | License | Integration mode |
|---|---|---|---|
| `ml-explore/mlx-lm` | `cc8521569694a3240b52c98acffd100d59b4c755` | MIT | separately installed runtime |
| `matt-k-wong/mlx-flash` | `f01b6f15affc054e143c1426ef2c3cc500cdbea8` | MIT | separately installed runtime |
| `srcterm/streamlx` | `146507b59293058b3a1cecc43f47947b25012297` | MIT | separately installed runtime |
| `huggingface-hub` | resolved by package installer | Apache-2.0 | Python dependency |

The current `mlx-lm` pin above reports package version `0.32.0` and requires MLX `>=0.32.1` on Darwin. Runtime revision pins are reproducibility targets, not ownership or endorsement claims.

Source/license references:

- https://github.com/ml-explore/mlx-lm
- https://github.com/matt-k-wong/mlx-flash
- https://github.com/srcterm/streamlx
- https://github.com/huggingface/huggingface_hub

### Reviewed metadata exception: streamlx 0.1.0

The pinned `streamlx` repository contains an MIT `LICENSE`, but version `0.1.0` does not declare that license in its Python package metadata, so `importlib.metadata` reports `UNKNOWN`. OuterRAM does **not** globally ignore unknown licenses. `legal/LICENSE_OVERRIDES.json` records a narrow reviewed override for exactly `streamlx==0.1.0` and exactly revision `146507b59293058b3a1cecc43f47947b25012297`, with a link to the license evidence. A different package version or Git revision does not inherit that override.

## Models are not bundled

OuterRAM does **not** grant rights to any model, tokenizer, dataset, adapter, quantization, or generated output. Model repositories may use Apache-2.0, MIT, community licenses, research-only licenses, non-commercial licenses, custom terms, or no clearly declared license.

Users and distributors must review the exact model repository, revision, base-model terms, and any additional acceptable-use terms before use or redistribution. A model being downloadable or technically compatible does not mean commercial use or redistribution is permitted.

The built-in virtual Qwen profile records public model-license metadata only as descriptive provenance. It does not bundle the model and does not convert that metadata into legal clearance.

## Future vendoring rule

If OuterRAM ever copies, modifies, bundles, statically links, or redistributes third-party source/binaries rather than installing them independently, the change must include a new license review and all required copyright, NOTICE, attribution, source-offer, or other obligations before merge.

This file is informational and is not a substitute for the full text of any third-party license.
