# OuterRAM legal and release notes

_Last reviewed: 2026-08-25._

This document records project policy and engineering controls. It is not legal advice or a legal opinion.

## Project license

OuterRAM source code is released under the MIT License in `LICENSE`. Third-party runtimes, libraries, models and datasets retain their own terms. OuterRAM does not grant rights to model weights merely because it can inspect, download or run them.

## Third-party runtime policy

OuterRAM currently orchestrates external runtimes rather than vendoring their implementations. Reviewed runtime revisions and licenses are recorded in `legal/APPROVED_COMPONENTS.json`, `legal/LICENSE_OVERRIDES.json`, `THIRD_PARTY_NOTICES.md` and `src/outerram/runtime_pins.py`.

Any future vendoring, code copying or new runtime integration requires a fresh license/provenance review before release.

## Model policy

OuterRAM code releases do not bundle model weights. Model licenses and base-model terms are separate from the OuterRAM license. Hugging Face metadata captured by the tool is descriptive provenance only, not legal clearance. See `docs/MODEL_LICENSE_POLICY.md`.

## Trademark / affiliation

The former provisional product name StretchMLX was retired before public launch. The public product name is **OuterRAM**. The rename removes the known issue of embedding Apple's MLX framework name in the project brand; it is not a formal trademark-clearance opinion for OuterRAM.

OuterRAM is not affiliated with, endorsed by, sponsored by or certified by Apple, OpenAI, Hugging Face, model vendors or third-party runtime maintainers. See `TRADEMARKS.md`.

## OpenAI-compatible interface

“OpenAI-compatible” describes local request/response protocol shape. It does not mean the project provides OpenAI services, requires an OpenAI account, or has an OpenAI partnership.

## Privacy

OuterRAM has no project telemetry, analytics service, advertising or automatic crash upload. Network access occurs only for user-directed functions such as model/runtime downloads, upstream contract checks, and user-selected inference endpoints. Diagnostic reports can contain machine/model/path information and must be reviewed before public sharing. See `PRIVACY.md`.

## Security / user safety

The project defaults to loopback serving, fails closed on unsupported runtime/model combinations, bounds HTTP/disk diagnostic resources, avoids automatic model-repository Python-code downloads, pins reviewed upstream revisions, and runs automated static/dependency/security gates. See `SECURITY.md`.

## Publication vs validation

OuterRAM deliberately separates three decisions:

1. **Public source publication** — repository/history/privacy/security/legal publication controls are satisfied.
2. **Validated release claims** — full validation plus physical Apple Silicon evidence exists for the advertised scenario.
3. **Commercial release/branding claims** — any additional professional trademark/patent/FTO/business review appropriate to the intended use has been completed.

Source publication alone must never be represented as proof of real-Mac performance.

## Automated release policy

`legal/RELEASE_APPROVALS.json` is the machine-readable source for release blockers. `scripts/legal-gate.py` fails closed for requested public/validated/commercial modes while required approvals remain pending.
