# OuterRAM 0.3.0rc2

Public release candidate focused on Windows planning/diagnostics compatibility and release hygiene.

## Highlights

- Fixes `outerram doctor` on Windows by using the native Windows physical-memory API instead of incorrectly falling through to the Linux detector.
- Keeps execution fail-closed: Windows and Linux remain planning/testing hosts only; current real MLX execution requires supported Apple Silicon macOS.
- Adds a dedicated `windows-latest` GitHub Actions gate covering native memory detection, compilation and the expected `doctor` behavior on a non-Mac host.
- Refreshes PyPI installation guidance and release metadata for `0.3.0rc2`.
- Keeps `outerram` as the canonical project, package and CLI identity.

## Validation boundary

This candidate validates package/platform detection and synthetic planning contracts. It does **not** claim physical Apple Silicon performance, TTFT/tok/s, thermal behavior or coding-agent stability until those measurements are recorded through the physical validation workflow.

## Compatibility window

`outerram` is canonical. The former `stretchmlx` CLI/import surface remains only as a deprecated migration compatibility path during the `0.3.0` release-candidate transition window and is scheduled for removal after that window.
