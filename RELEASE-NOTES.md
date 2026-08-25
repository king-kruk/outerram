# OuterRAM 0.3.0rc1

Public-source release candidate.

## Highlights

- OuterRAM is the canonical project, Python package and CLI identity.
- Resident, dense SSD streaming and exact MoE expert streaming strategies remain fail-closed behind host/model/runtime compatibility checks.
- Public-repository hardening includes immutable GitHub Action pins, Bandit, `pip-audit`, secret/action policy checks, bounded HTTP/disk diagnostics, model-download trust guards and supply-chain checks.
- The public repository starts from a clean Git history baseline using a GitHub `noreply` maintainer identity; prior private development history remains in a separate private archive.
- Model weights are not bundled, and technical compatibility is not represented as model-license clearance.

## Claim boundary

This release candidate is suitable for source publication only after the repository-level publication controls and final gates are complete. It does **not** claim physical Apple Silicon performance, TTFT/tok/s, thermal behavior or coding-agent stability until those measurements are recorded through the physical validation workflow.

## Compatibility window

`outerram` is canonical. The former `stretchmlx` CLI/import surface remains only as a one-release migration compatibility path and is scheduled for removal after `0.3.0rc1`.
