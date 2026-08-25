# OuterRAM project status

Current candidate: **0.3.0rc1**

OuterRAM is the selected public project name. The former private provisional StretchMLX name remains only in the one-release compatibility surface and historical migration notes.

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

## Required immediately around the visibility change

Before changing visibility, the exact candidate must pass:

```bash
./scripts/pre-public-release-gate.sh
```

GitHub controls that are available while the repository is private should be configured before the change. Controls that are public-only on the current account tier — such as public CodeQL/secret-scanning/Private Vulnerability Reporting, and branch rules on GitHub Free personal repositories — must be enabled or verified immediately after the repository becomes public and **before announcement**. Then run the strict public gate:

```bash
./scripts/public-release-gate.sh
```

See `docs/PUBLICATION_CHECKLIST.md` for the exact platform checklist.

## Separate validated-release work

Physical Apple Silicon inference evidence and manual full validation are required before making real hardware/performance claims. They are not prerequisites for publishing source code as an experimental open-source project.
