# OuterRAM project status

Current candidate: **0.3.0rc1**

OuterRAM is now a public-source project. The former private provisional StretchMLX name remains only in the one-release compatibility surface and historical migration notes.

## Completed

- resident / dense-stream / exact MoE-stream planner and adapters
- Apple Silicon + macOS compatibility gates
- immutable runtime pins and upstream contract verification
- local checkpoint provenance/completeness guards
- bounded local OpenAI-compatible dense-stream server
- virtual planner/API qualification and stress matrix
- package/legal metadata, SBOM and release evidence
- security hardening: secret/action pin gate, Bandit, pip-audit, safe model fetch, transport/resource guards
- public contribution/security templates and publication checklist
- clean public-repository history baseline with GitHub `noreply` identity; the prior development repository is retained separately as a private archive
- automated pre-public history/privacy gate covering all fetched reachable refs
- repository visibility changed to **Public** on 2026-08-25
- `main` branch protection enabled with required `pr-gate` enforcement for everyone
- secret scanning enabled
- secret scanning push protection enabled
- dependency graph and Dependabot security updates enabled
- Private Vulnerability Reporting enabled
- pinned CodeQL workflow completed successfully on public `main` (run 32887055503)
- repository description and public topics configured
- public-release platform approvals recorded in `legal/RELEASE_APPROVALS.json`
- CI permanently enforces `legal-gate.py --mode public` while the repository is public

## Public source status

The public-source publication gate is complete once the protected PR carrying the final platform approvals passes `pr-gate` and is merged. This source-publication status does **not** imply physical Apple Silicon performance validation, patent/FTO clearance, or a production/commercial support commitment.

## Separate validated-release work

Physical Apple Silicon inference evidence and manual full validation are required before making real hardware/performance claims or calling a release hardware validated. They are not prerequisites for publishing source code as an experimental open-source project.
