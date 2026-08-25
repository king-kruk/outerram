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
- Its history begins with a parentless OuterRAM root commit and has no ancestry to the private development archive.
- Pre-publication maintainer commits use the GitHub `noreply` identity.
- The former development repository is retained separately as a private archive and must remain private.
- Final hardening CI runs the repository security gate over the tracked publication tree.

### 3. Pre-public GitHub controls — platform verification required

Before changing visibility, configure every control that GitHub makes available to the current private repository/account tier:

- protect `main` with a ruleset/branch protection requiring pull requests;
- require the always-on `pr-gate` status check;
- block force pushes and branch deletion on `main`;
- keep normal contributor/admin bypass disabled except for deliberate break-glass recovery;
- enable the dependency graph, Dependabot alerts and Dependabot security updates;
- keep GitHub Actions default workflow permissions read-only unless a workflow explicitly needs more;
- allow only reviewed GitHub Actions and keep external actions pinned to immutable commit SHAs.

The repository already contains a pinned CodeQL workflow, Dependabot configuration, `SECURITY.md`, and an always-on Bandit/security/pip-audit PR gate.

### 4. Public-only security controls — enable/verify immediately after visibility changes

Some GitHub security capabilities are not available to ordinary user-owned private repositories without paid GitHub security products, but become available for public repositories. Visibility must not be treated as the end of the publication procedure. Immediately after changing the repository to public:

- verify GitHub secret scanning is active for the public repository;
- verify user/repository push protection behavior and enable repository-level push protection if the account exposes that control;
- run/dispatch the pinned CodeQL workflow and require a successful result before announcement;
- enable Private Vulnerability Reporting;
- re-check Dependabot alerts/security updates and the dependency graph;
- verify branch protection/rulesets remain effective after the visibility transition.

Do not announce the repository until this post-visibility verification is complete.

### 5. Public-facing repository metadata — required before announcement

- add a concise repository description;
- add relevant topics such as `apple-silicon`, `mlx`, `llm`, `local-llm`, `python` and `macos`;
- disable unused Wiki/Projects features if they will not be maintained;
- enable automatic deletion of merged branches if desired;
- confirm Issues are enabled and issue templates render correctly;
- confirm `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `LICENSE`, notices and privacy documentation are visible from the repository root/community profile.

### 6. Final source-publication gates — required

From a clean checkout of the exact commit intended for publication:

```bash
python scripts/security-gate.py
python scripts/legal-gate.py --mode public
./scripts/quality-gate.sh
```

All pre-public gates must pass. Review the generated dependency/license/SBOM evidence and confirm no unsupported performance or legal claims were introduced. Platform controls that are technically public-only are handled by the immediate post-visibility procedure above and must be verified before announcement.

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
