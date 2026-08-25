# Changelog

## 0.3.0rc1 — pre-release

First OuterRAM public-source release candidate.

- Establish **OuterRAM** as the canonical public project, Python package and CLI identity.
- Support fail-closed planning across resident `mlx-lm`, dense SSD streaming through `mlx-flash`, and compatible exact MoE expert streaming through `streamlx`.
- Require Apple Silicon with macOS 14.0+ for current execution adapters and validate model/checkpoint/runtime compatibility before launch.
- Require local materialized checkpoints for execution and preserve immutable Hugging Face revision/provenance metadata.
- Harden checkpoint handling against incomplete shards, ambiguous checkpoint selection and path traversal.
- Harden the local dense-stream API with loopback-first networking, bounded request/token/concurrency limits, secret-safe transport rules and redacted server errors.
- Pin reviewed upstream runtime revisions and reject modified/redirected managed StreamLX checkouts.
- Add virtual qualification/stress testing without presenting synthetic results as physical Mac benchmarks.
- Add repository secret/action-pin policy checks, Bandit, dependency vulnerability auditing, strict dependency-license inventory, CycloneDX SBOM, PEP 639 wheel metadata and deterministic release evidence.
- Publish MIT project licensing, third-party notices, privacy/security guidance, contribution policy and model-license boundaries.
- Start the public candidate from a clean Git history with GitHub `noreply` maintainer identity and no ancestry to the private development repository.

### Compatibility window

The project used a different provisional name during private development. For `0.3.0rc1` only, the deprecated `stretchmlx` CLI/import alias and legacy migration metadata/env fallbacks remain available so early private-test setups do not break. New integrations must use `outerram`, `OuterRAM` and `OUTERRAM_*`.

The compatibility alias is scheduled for removal after this transition release.
