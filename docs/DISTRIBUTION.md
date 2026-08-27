# Distribution

OuterRAM uses package-manager distribution for end users and keeps source and development installation separate.

## End-user targets

### PyPI

OuterRAM release candidates are published on PyPI. The primary install command is:

```bash
uv tool install outerram
```

Alternative isolated Python CLI install:

```bash
pipx install outerram
```

For development snapshots that are not published to PyPI:

```bash
uv tool install git+https://github.com/king-kruk/outerram.git
```

### Homebrew

A project tap can provide:

```bash
brew install king-kruk/tap/outerram
```

A plain `brew install outerram` must not be advertised until a formula is accepted into `homebrew/core`.

## PyPI trusted publishing

PyPI publication uses GitHub OIDC Trusted Publishing. No long-lived PyPI API token belongs in GitHub secrets.

Publisher configuration:

- PyPI project: `outerram`
- GitHub owner: `king-kruk`
- GitHub repository: `outerram`
- Workflow filename: `release.yml`
- Environment: `pypi`

## Release procedure

1. Ensure `main` is green and `pyproject.toml` contains the intended version.
2. Create a GitHub Release whose tag is exactly `v<project.version>`; for example `v0.3.0rc3` for project version `0.3.0rc3`.
3. `.github/workflows/release.yml` verifies the tag/version match, builds wheel and sdist, validates metadata, smoke-installs the wheel, and publishes to PyPI through OIDC.
4. Verify the package on PyPI and test `uv tool install outerram` on a clean host.
5. Update any Homebrew tap formula from immutable released artifacts and checksums.

## Security rules

- Publishing workflow actions remain pinned to full commit SHAs.
- PyPI uses OIDC Trusted Publishing, not stored API tokens.
- Release tags must match `pyproject.toml` exactly.
- Published artifacts are built and smoke-tested by the release workflow before upload.
- Homebrew sources and resources must be immutable and checksum-verified.
- Physical Apple Silicon validation remains a separate claim from package publication.
