# Distribution

OuterRAM uses package-manager distribution for end users and keeps source/development installation separate.

## End-user targets

### PyPI

Once the PyPI publisher is activated and the first release is published, the primary install command is:

```bash
uv tool install outerram
```

Alternative isolated Python CLI install:

```bash
pipx install outerram
```

Until the first PyPI upload exists, users can install directly from GitHub:

```bash
uv tool install git+https://github.com/king-kruk/outerram.git
```

### Homebrew

The immediately achievable Homebrew path is an official project tap:

```bash
brew install king-kruk/tap/outerram
```

A plain:

```bash
brew install outerram
```

must not be advertised until an `outerram` formula has been accepted into `homebrew/core`. Homebrew Core requires a stable, tagged, versioned release and applies its own acceptance and review policy.

## PyPI trusted publishing

PyPI publication is designed to use GitHub OIDC Trusted Publishing. No long-lived PyPI API token belongs in GitHub secrets.

One-time PyPI publisher configuration:

- PyPI project: `outerram`
- GitHub owner: `king-kruk`
- GitHub repository: `outerram`
- Workflow filename: `release.yml`
- Environment: `pypi`

For a new PyPI project, configure these values as a **pending Trusted Publisher**. The first successful upload creates the project and converts the publisher to a normal Trusted Publisher.

## Release procedure

1. Ensure `main` is green and the intended package version in `pyproject.toml` is correct.
2. Create a GitHub Release whose tag is exactly `v<project.version>`; for example `v0.3.0rc1` for project version `0.3.0rc1`.
3. `.github/workflows/release.yml` verifies the tag/version match, builds wheel + sdist, validates metadata, smoke-installs the wheel, and publishes to PyPI through OIDC.
4. Verify the package on PyPI and test `uv tool install outerram` on a clean Mac.
5. Build/update the Homebrew tap formula from immutable released artifacts and checksums.

## Homebrew packaging policy

For a project tap, use a separate public repository named `king-kruk/homebrew-tap` with the formula under `Formula/outerram.rb`. The formula should install from an immutable tagged release/PyPI source archive, pin SHA-256 checksums, and declare recursive Python resources rather than resolving moving dependencies during installation.

After the tap formula is published, first-time users can install it in one command:

```bash
brew install king-kruk/tap/outerram
```

After OuterRAM has a stable release and meets Homebrew Core's acceptance requirements, submit the formula upstream. Only after that PR is accepted may the README promote:

```bash
brew install outerram
```

## Security rules

- Publishing workflow actions remain pinned to full commit SHAs.
- PyPI uses OIDC Trusted Publishing, not stored API tokens.
- Release tags must match `pyproject.toml` exactly.
- Published artifacts are built by the release workflow and smoke-tested before upload.
- Homebrew sources/resources must be immutable and checksum-verified.
- Physical Apple Silicon validation remains a separate claim from package publication.
