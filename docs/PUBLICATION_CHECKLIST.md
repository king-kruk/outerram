# Public repository publication checklist

This checklist is specifically for changing the **source repository visibility** from private to public. It is intentionally separate from physical Apple-Silicon performance validation and from a commercial product launch.

## Required before changing visibility

### 1. Public name / trademark decision — ✅ resolved by rename

- The provisional `StretchMLX` product name was retired in favor of **OuterRAM** for the `0.3.0rc1` transition release.
- `stretchmlx` remains only as a temporary one-release CLI/import compatibility path and historical identifier; it is not the current product identity.
- Third-party names such as MLX, Apple, OpenAI, Hugging Face and Qwen are used only for factual compatibility/dependency references and remain subject to `TRADEMARKS.md`.
- The rename reduces the specific risk created by embedding `MLX` in the public product name; it is not a worldwide trademark opinion for OuterRAM.

### 2. Public Git history/privacy — ✅ resolved by clean repository baseline

- `king-kruk/outerram` was created as a new empty private repository rather than publishing the prior development repository.
- Its history begins with clean OuterRAM commits using the maintainer's GitHub `noreply` identity and has no ancestry to the private development archive.
- The former development repository is retained separately as a private archive and must remain private.
- Before visibility changes, re-check all reachable branches/commits in `king-kruk/outerram`, confirm no personal commit email or secret is present, and verify the current tree with the repository security gate.

### 3. Repository protection and security settings — pending

Configure GitHub before the visibility change:

- protect `main` with a ruleset/branch protection requiring pull requests;
- require the always-on `pr-gate` status check;
- block force pushes and branch deletion on `main`;
- keep normal contributor/admin bypass disabled except for deliberate break-glass recovery;
- enable secret scanning and push protection when available;
- enable dependency graph, Dependabot alerts and Dependabot security updates;
- enable Private Vulnerability Reporting for confidential security reports;
- keep GitHub Actions default workflow permissions read-only unless a workflow explicitly needs more;
- allow only reviewed GitHub Actions and keep external actions pinned to immutable commit SHAs.

### 4. Public-facing repository metadata — pending

Before announcement:

- add a concise repository description;
- add relevant topics such as `apple-silicon`, `mlx`, `llm`, `local-llm`, `python` and `macos`;
- disable unused Wiki/Projects features if they will not be maintained;
- enable automatic deletion of merged branches if desired;
- confirm Issues are enabled and issue templates render correctly;
- confirm `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `LICENSE`, notices and privacy documentation are visible from the repository root/community profile.

### 5. Final source-publication gates — pending

From a clean checkout of the exact commit intended for publication:

```bash
python scripts/security-gate.py
python scripts/legal-gate.py --mode public
./scripts/quality-gate.sh
```

All must pass. Review the generated dependency/license/SBOM evidence and confirm no unsupported performance or legal claims were introduced.

## Required before calling a release “hardware validated”

These are **not prerequisites merely to publish source code**, but they are prerequisites to advertise real Mac inference/performance validation:

- run the manual CI workflow with `full_validation=true` on the exact release commit;
- complete physical Apple-Silicon inference qualification using `docs/MAC_VALIDATION.md`;
- retain exact model revision, strategy, macOS/hardware, disk, memory/swap, TTFT/tok/s and tool-roundtrip evidence;
- publish only measurements that came from the recorded physical qualification.

Use:

```bash
python scripts/legal-gate.py --mode validated
```

for this stronger release level.

## Commercial launch

A material commercial launch may require additional legal work beyond open-source publication, including patent/Freedom-to-Operate review and revision-specific model-license analysis for any model promoted, bundled, redistributed or used as part of a commercial offering.

Automated gates are compliance aids, not legal advice.
