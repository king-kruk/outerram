# Contributing

OuterRAM prioritizes correctness, reproducibility, provenance, and license hygiene over benchmark headlines.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
./scripts/quality-gate.sh
python scripts/legal-gate.py --mode internal
```

## Contributor license / DCO

OuterRAM uses the Developer Certificate of Origin process described in [DCO.md](DCO.md). Contributions intended for merge must be signed off, normally with:

```bash
git commit -s
```

Unless a separate written agreement applies, accepted inbound contributions are licensed under the same MIT license used by the project. A DCO sign-off is not a copyright assignment.

Do not submit code, model weights, datasets, documentation, tests, secrets, confidential information, employer-owned work, or other material you do not have the right to contribute.

If code was produced or materially assisted by an AI coding system, the contributor remains responsible for reviewing the contribution, confirming they are authorized to submit it, and avoiding unreviewed copying of third-party code or license text.

## Pull-request expectations

A change that touches planning, model inspection, runtime selection, API behavior, or compatibility must include a regression test. A performance claim must include hardware, macOS version, model/revision/quantization, context length, runtime strategy, RAM budget, SSD path, TTFT and decode tok/s.

Do not improve throughput by silently changing model semantics (for example dropping router-selected experts or lowering Top-K) unless the behavior is an explicit experimental mode and quality impact is measured.

Any change that adds, vendors, copies, bundles, statically links, or redistributes third-party code/binaries must update `THIRD_PARTY_NOTICES.md`, the approved-component manifest, and the relevant release/legal checks before merge.

## Runtime integrations

Prefer adapters around upstream projects over copied implementations. New runtime adapters should implement:

1. a deterministic compatibility predicate;
2. a reproducible install/bootstrap path;
3. a dry-run launch spec;
4. a health/probe path;
5. tests that run without downloading multi-GB models;
6. explicit upstream source, revision, and license review.

## Model licensing

Technical compatibility is not a license grant. Do not advertise a model as commercially usable, redistributable, or "free" unless its exact repository/revision and applicable base-model terms have been reviewed. Custom, unknown, research-only, or non-commercial terms require explicit review rather than inference from model family/name.

## Physical-Mac results

Use `docs/MAC_VALIDATION.md` and add measured results to the compatibility matrix. Self-reported upstream numbers may be cited as upstream results but must not be presented as OuterRAM measurements.
