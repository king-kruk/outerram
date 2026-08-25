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
- clean public-repository history baseline with GitHub noreply identity; the prior development repository is retained separately as a private archive

## Still required before repository visibility changes

- enable repository ruleset/branch protection and public security features documented in `docs/PUBLICATION_CHECKLIST.md`
- run the final source-publication gates on the exact public candidate commit

## Separate validated-release work

Physical Apple Silicon inference evidence and manual full validation are required before making real hardware/performance claims. They are not prerequisites for publishing source code as an experimental open-source project.
