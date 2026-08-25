# Release checklist

OuterRAM separates **source publication**, **hardware-validated release claims**, and **commercial launch**. Do not mix these gates.

## Normal pull-request gate

Routine pull requests run the Ubuntu `pr-gate` and must cover:

- [ ] internal legal-policy gate;
- [ ] DCO sign-off for external contributor commits;
- [ ] Python 3.12 tests, compile and synthetic smoke;
- [ ] Bandit/static security checks and repository security gate;
- [ ] wheel build and PEP 639 legal-metadata verification;
- [ ] clean-wheel install, `outerram --version`, `pins --json`, and `pip check`;
- [ ] dependency-license inventory with no unresolved unknown/risk-marked license;
- [ ] deterministic CycloneDX SBOM;
- [ ] `pip-audit` vulnerability scan.

## Source-publication gate

These are the requirements for changing the repository itself from private to public:

- [x] public product identity is **OuterRAM**; the former name is migration/history only;
- [x] public repository history begins from a clean OuterRAM baseline with GitHub `noreply` identity and no ancestry to the private development archive;
- [ ] `main` protection requires PR + `pr-gate` and blocks force-push/deletion;
- [ ] required repository security features in `docs/PUBLICATION_CHECKLIST.md` are enabled;
- [ ] public-facing repository metadata/community files are complete;
- [ ] reachable public-repository refs are re-scanned for secrets/private data;
- [ ] `TRADEMARKS.md`, `THIRD_PARTY_NOTICES.md`, `PRIVACY.md`, `DCO.md`, `SECURITY.md`, and model-license policy are reviewed;
- [ ] `legal/APPROVED_COMPONENTS.json` matches runtime pins;
- [ ] model weights/build caches/local diagnostics are not tracked;
- [ ] OpenAI/Apple/third-party compatibility wording does not imply affiliation or endorsement;
- [ ] `python scripts/security-gate.py` passes;
- [ ] `python scripts/legal-gate.py --mode public` passes;
- [ ] `./scripts/quality-gate.sh` passes on the exact publication candidate.

Physical Mac performance evidence and manual full-runtime validation are **not** requirements merely to publish the source repository.

## Hardware-validated release gate

Before advertising real Apple-Silicon inference/performance validation:

- [ ] manually run CI with `full_validation=true` on the exact release candidate;
- [ ] Python compatibility, upstream contracts, macOS tests and all three runtime-license audits pass;
- [ ] exact Mac hardware/macOS/model revision/quantization/context/strategy/storage are recorded;
- [ ] sequential + random-range disk measurements are recorded on the model filesystem;
- [ ] `qualify` passes with retained evidence;
- [ ] coherent coding smoke and 10+ turn coding/tool session pass where coding-agent validation is claimed;
- [ ] peak memory, memory pressure and swap are recorded;
- [ ] TTFT/tok/s are measured rather than estimated;
- [ ] no quality shortcut such as dropped experts/reduced Top-K is hidden;
- [ ] `python scripts/legal-gate.py --mode validated` passes.

## Release artifact gate

For an actual packaged release:

- [ ] `./scripts/release-candidate.sh` emits wheel, clean source archive, SBOM, `RELEASE-EVIDENCE.json`, manifest and SHA-256 checksums;
- [ ] wheel declares `License-Expression: MIT` and embeds `LICENSE` plus `THIRD_PARTY_NOTICES.md`;
- [ ] SBOM root is `outerram` and version matches the manifest;
- [ ] release evidence binds exact commit/version/runtime pins/legal-gate results;
- [ ] extracted source artifact reruns tests/compile/smoke successfully.

## Commercial launch gate

Before a material commercial launch or a representation that the project is patent-cleared:

- [ ] source-publication gate passes;
- [ ] any advertised model's exact license/base-model terms are separately reviewed;
- [ ] appropriate professional trademark/name review is completed for the intended commercial use;
- [ ] `legal/RELEASE_APPROVALS.json` records a qualified patent/FTO review or equivalent documented decision when required;
- [ ] `python scripts/legal-gate.py --mode commercial` passes.

Automated gates reduce risk but are not legal advice.
