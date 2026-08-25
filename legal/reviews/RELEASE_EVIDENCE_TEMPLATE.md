# Public release evidence

Copy this file to a dated review file for each intended public release. Do not mark an approval complete without the underlying evidence.

## Release identity

- Version:
- Exact Git commit SHA:
- Release date:
- Reviewer:

## Routine PR gate

- PR number:
- `pr-gate` status:
- Relevant run/check URL or ID:

## Manual full validation

- GitHub Actions run ID:
- Workflow ref/commit SHA matches release commit: yes / no
- `full_validation=true`: yes / no
- `pr-gate`: pass / fail
- Python 3.10 compatibility: pass / fail
- Python 3.11 compatibility: pass / fail
- Python 3.13 compatibility: pass / fail
- upstream contracts: pass / fail
- macOS 3.12: pass / fail
- macOS 3.13: pass / fail
- resident runtime license audit: pass / fail
- dense-stream runtime license audit: pass / fail
- moe-stream runtime license audit: pass / fail
- retained artifact names / SHA-256:

## Physical Apple Silicon qualification

- Mac model/chip:
- Unified memory:
- macOS version:
- Model repository:
- Immutable model revision:
- Quantization:
- Declared model license:
- Base model / terms reviewed:
- Selected strategy:
- Runtime pin status:
- Model storage path/type:
- sequential disk result:
- random-range disk result / p95 latency:
- qualification artifact path/hash:
- TTFT:
- tokens/sec:
- peak process/system memory:
- swap / memory pressure:
- structured tool-call round trip: pass / fail
- 10+ turn coding/tool session: pass / fail
- crashes/OOM/pathological swap: none / describe

## Project-name / trademark-risk path

- Public name:
- Rename completed or qualified-counsel clearance:
- Review type (`rename` or `qualified-counsel`):
- Evidence:
- Non-affiliation wording rechecked: yes / no

## Repository controls

- `main` protected: yes / no
- PR required: yes / no
- `pr-gate` required: yes / no
- force push blocked: yes / no
- deletion blocked: yes / no
- routine bypass disabled/restricted: yes / no
- evidence:

## Dependency / model distribution review

- Approved runtime pins unchanged or re-reviewed: yes / no
- Package dependency license inventory reviewed: yes / no
- Runtime license inventories reviewed: yes / no
- Unknown/restricted licenses unresolved: none / describe
- Model weights bundled: no / if yes, separate redistribution review reference

## Public claims review

- README limitations match measured hardware evidence: yes / no
- No technical-compatibility claim presented as legal permission: yes / no
- No OpenAI/Apple/third-party affiliation implied: yes / no
- Compatibility rows are measured, not extrapolated: yes / no

## Gate results

```text
python scripts/legal-gate.py --mode public
bash scripts/public-release-gate.sh
```

- public legal gate: pass / fail
- public release gate: pass / fail

## Approval updates

List every `legal/RELEASE_APPROVALS.json` entry changed to `approved` and the evidence supporting it.

This template is an engineering/compliance record, not legal advice or a legal opinion.
