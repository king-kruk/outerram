# OuterRAM legal policy

_Last reviewed: 2026-08-27._

This document records project policy and engineering controls. It is not legal advice or a legal opinion.

## Project license

OuterRAM source code is released under the MIT License in `LICENSE`. Third-party runtimes, libraries, models and datasets retain their own terms. OuterRAM does not grant rights to model weights merely because it can inspect, download or run them.

## Third-party runtime policy

OuterRAM orchestrates external runtimes rather than vendoring their implementations. Reviewed runtime revisions and licenses are recorded in `legal/APPROVED_COMPONENTS.json`, `legal/LICENSE_OVERRIDES.json`, `THIRD_PARTY_NOTICES.md` and `src/outerram/runtime_pins.py`.

Any future vendoring, code copying or new runtime integration requires a fresh license and provenance review before release.

## Model policy

OuterRAM releases do not bundle model weights. Model licenses and base-model terms are separate from the OuterRAM license. Hugging Face metadata captured by the tool is descriptive provenance only, not legal clearance. See `docs/MODEL_LICENSE_POLICY.md`.

## Trademark and affiliation

OuterRAM is not affiliated with, endorsed by, sponsored by or certified by Apple, OpenAI, Hugging Face, model vendors or third-party runtime maintainers. Project naming and automated checks are not a trademark-clearance opinion. See `TRADEMARKS.md`.

## OpenAI-compatible interface

“OpenAI-compatible” describes local request/response protocol shape. It does not mean the project provides OpenAI services, requires an OpenAI account, or has an OpenAI partnership.

## Privacy

OuterRAM has no project telemetry, analytics service, advertising or automatic crash upload. Network access occurs for explicit user actions such as model/runtime downloads, upstream contract checks and user-selected inference endpoints. Diagnostic reports can contain machine, model and path information and should be reviewed before public sharing. See `PRIVACY.md`.

## Security and user safety

The project defaults to loopback serving, fails closed on unsupported runtime/model combinations, bounds HTTP and disk diagnostic resources, avoids automatic model-repository Python-code execution, pins reviewed upstream revisions, and runs automated static, dependency and security gates. See `SECURITY.md`.

## Validation and claims

Source publication and package validation do not prove real-Mac performance. Inference, memory, throughput or workload claims require physical Apple Silicon evidence for the exact host, model revision, strategy and runtime configuration.

Automated legal and supply-chain checks validate facts that code can establish: repository license metadata, required notices, reviewed runtime pins and explicit dependency-license overrides. They deliberately do **not** self-certify trademark clearance, patent freedom-to-operate or model-use rights.
