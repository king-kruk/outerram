## What changes?

Describe the change and why it is needed.

## Engineering checks

- [ ] Tests/regression coverage added or updated where behavior changed.
- [ ] `./scripts/quality-gate.sh` passes locally or equivalent CI is green.
- [ ] Performance claims include reproducible hardware/model/revision/context measurements.

## Rights, license, privacy and provenance

- [ ] I have the right to submit everything in this PR and my commits comply with [DCO.md](../DCO.md).
- [ ] I did not include confidential information, secrets, proprietary model weights, datasets, or employer/customer material without authorization.
- [ ] If this PR adds or changes a third-party dependency/runtime, I identified its exact source/revision/license and updated `THIRD_PARTY_NOTICES.md` / `legal/APPROVED_COMPONENTS.json` as needed.
- [ ] If this PR copies, vendors, bundles, modifies, or redistributes third-party code/binaries, I preserved all required copyright/NOTICE/license obligations and requested explicit license review.
- [ ] If this PR adds a model compatibility claim, it identifies the exact model repository/revision and does not equate technical compatibility with commercial-use/redistribution permission.
- [ ] If this PR changes network, diagnostics, telemetry, hosted behavior, or data collection, `PRIVACY.md` and `SECURITY.md` are updated.
- [ ] If AI tools materially assisted the change, I reviewed the resulting code and remain responsible for provenance, correctness, and licensing.

## Public-release impact

- [ ] This change does not weaken or bypass `scripts/legal-gate.py`, DCO, license inventory, or public-release blockers merely to make CI pass.
