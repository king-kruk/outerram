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
- explicit `pre-public` release-policy gate separated from the stricter post-visibility `public` gate
- repository visibility changed to **Public** on 2026-08-25
- `main` branch protection remains enabled and requires the `pr-gate` status check for everyone
- dependency graph / Dependabot graph update is active on the public repository

## Post-public activation in progress

The source repository is public, but announcement remains on hold until the public-only controls are verified:

- successful CodeQL run on the public `main` branch
- secret scanning and push protection verified
- Private Vulnerability Reporting enabled
- final `public` legal gate recorded as passing

After these controls are verified, run:

```bash
./scripts/public-release-gate.sh
```

See `docs/PUBLICATION_CHECKLIST.md` for the exact platform checklist.

## Separate validated-release work

Physical Apple Silicon inference evidence and manual full validation are required before making real hardware/performance claims. They are not prerequisites for publishing source code as an experimental open-source project.
