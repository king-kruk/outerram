# Changelog

## 0.3.0rc3 — pre-release

Memory-path simplification and public-repository cleanup.

- Replace the waiting OuterRAM launcher process with the selected runtime on POSIX/macOS using process replacement, so the CLI/planner interpreter does not remain as an avoidable second Python process during inference.
- Keep Python as the current orchestration language because the selected execution backends are Python-facing; a Go-only control-plane rewrite would not remove those runtimes and would add an IPC or C-bridge boundary.
- Document Swift/C++/C native execution as a measurement-driven future option because MLX exposes official native APIs, not as a speculative rewrite before physical profiling.
- Remove the retired compatibility CLI/import namespace from the package; `outerram` is now the only executable and package identity.
- Simplify public CI and release checks around durable security, license, runtime-pin, package, SBOM and vulnerability controls.
- Remove obsolete pre-public publication scaffolding and internal approval bookkeeping from the public repository.
- Keep real inference/performance claims blocked until physical Apple Silicon qualification records actual process footprint, memory pressure, swap and workload performance.

## 0.3.0rc2 — pre-release

Windows planning and diagnostics compatibility fix.

- Fix `outerram doctor` on Windows by detecting physical memory through the native `GlobalMemoryStatusEx` API instead of routing Windows through the Linux memory detector.
- Preserve fail-closed execution semantics: Windows hosts can be inspected and planned, but real MLX execution still requires supported Apple Silicon macOS.
- Add cross-platform regression coverage and a `windows-latest` CI gate that verifies host detection and the expected non-Mac `doctor` exit behavior.
- Refresh release metadata and PyPI installation documentation.

## 0.3.0rc1 — pre-release

First public-source release candidate.

- Establish **OuterRAM** as the public project, Python package and CLI identity.
- Support fail-closed planning across resident `mlx-lm`, dense SSD streaming through `mlx-flash`, and compatible exact MoE expert streaming through `streamlx`.
- Require Apple Silicon with macOS 14.0+ for current execution adapters and validate model, checkpoint and runtime compatibility before launch.
- Require local materialized checkpoints for execution and preserve immutable Hugging Face revision and provenance metadata.
- Harden checkpoint handling against incomplete shards, ambiguous checkpoint selection and path traversal.
- Harden the local dense-stream API with loopback-first networking, bounded request/token/concurrency limits, secret-safe transport rules and redacted server errors.
- Pin reviewed upstream runtime revisions and reject modified or redirected managed StreamLX checkouts.
- Add virtual qualification and stress testing without presenting synthetic results as physical Mac benchmarks.
- Add repository security checks, Bandit, dependency vulnerability auditing, strict dependency-license inventory, CycloneDX SBOM, PEP 639 wheel metadata and deterministic release evidence.
- Publish MIT licensing, third-party notices, privacy/security guidance, contribution policy and model-license boundaries.
