# Changelog

## 0.3.0rc1 — pre-release

OuterRAM brand/package transition candidate.

- Rename the public product from the private provisional **StretchMLX** name to **OuterRAM** before public launch.
- Make `outerram` the canonical Python package and CLI.
- Keep `stretchmlx` only as a one-release deprecated CLI/package compatibility surface for early private testers.
- Remove the older `macllm` CLI alias.
- Move new cache/runtime defaults to `~/.cache/outerram` and make `OUTERRAM_API_KEY` canonical, with narrow migration compatibility for the previous private-test settings.
- Rebrand qualification/report/SBOM metadata to OuterRAM.
- Record the rename as the closure for the known MLX-in-product-name publication blocker; this is risk reduction, not formal trademark clearance for OuterRAM.
- Preserve all RC6 planner, security, legal, virtual-qualification and publication-hardening behavior.

## 0.2.0rc6 — pre-release

Virtual-qualification and upstream-lock synchronization candidate, layered on top of the rc4 legal/release hardening work already present in the repository.

- Add deterministic `stretchmlx simulate` API-contract qualification without claiming Metal execution.
- Add `stretchmlx simulate-matrix` covering six virtual Apple-Silicon memory profiles × six stress scenarios.
- Model M5/16GB Qwen3.8-27B 3-bit as a near-fit boundary: baseline resident, with conservative headroom/stress scenarios automatically falling back to `dense-stream`.
- Inject health, marker, tool-call, tool-result continuation, SSE and token-accounting failures to verify the virtual gate fails closed.
- Advance the tested `mlx-lm` pin to `cc8521569694a3240b52c98acffd100d59b4c755` (package 0.32.0; MLX >=0.32.1 on Darwin).
- Retain `mlx-flash` v0.4.0 and `streamlx` v0.1 immutable pins.
- Keep model-license metadata descriptive only; bundle no model weights and never imply legal clearance.
- Preserve PEP 639 wheel metadata, DCO, model-license provenance, trademark/non-affiliation policy, SBOM, deterministic release evidence and fail-closed release gates.

## 0.2.0rc4 — pre-release

Legal/release hardening candidate: trademark/non-affiliation policy, third-party notices, privacy disclosure, model-license provenance, DCO, strict dependency-license inventory, release approvals, PEP 639 wheel metadata, SBOM and deterministic release evidence.

## 0.2.0rc3 — pre-release

Checkpoint completeness/path hardening, planner fuzz/property coverage, macOS telemetry, random-range disk benchmarking, token-accounting qualification, pinned upstream source/API/license contracts and artifact integrity verification.

## 0.2.0rc2 — pre-release

Immutable local checkpoint execution, revision-preserving fetch, runtime pin enforcement, tool-call round-trip qualification, external tester workflow and release-candidate packaging.

## 0.2.0rc1 — pre-release

The project moved from an earlier internal `macllm` working name to the later private provisional `StretchMLX` name. This historical entry predates the final OuterRAM public-name decision.

## 0.1.0 — internal MVP

Initial resident / dense-stream / MoE-stream planner and launch adapters, synthetic smoke tests and minimal dense OpenAI-style chat server.
