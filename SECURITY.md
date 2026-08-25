# Security policy

OuterRAM is designed primarily for a **single-user local workstation**. Security-sensitive defaults therefore prefer loopback access, bounded resource use, immutable runtime revisions and fail-closed compatibility checks.

## Supported security scope

Security fixes are currently provided for the latest pre-release line on `main`. Older snapshots and deliberately unpinned upstream runtimes may not receive fixes.

## Network exposure

The default bind address is loopback (`127.0.0.1`). Do not expose an inference endpoint directly to an untrusted LAN or the public Internet merely because the model is local.

- OuterRAM's custom dense-stream server supports Bearer authentication via `--api-key`.
- **An API key does not encrypt HTTP traffic.** Non-loopback plaintext HTTP is refused by default even when an API key is configured.
- For remote use, keep OuterRAM bound to loopback and use an SSH tunnel or a properly configured TLS/authenticated reverse proxy.
- For upstream servers where OuterRAM cannot enforce authentication itself, non-loopback binding is refused by default.
- `--allow-unauthenticated-remote` is an explicit insecure-network override retained for controlled experiments. Do not use it on an untrusted network.
- Client commands refuse to transmit an API key over non-loopback plaintext HTTP.

The `/health` endpoint on the custom dense server intentionally does not require authentication and exposes only basic runtime status.

## HTTP and resource-exhaustion protections

The dense-stream server applies bounded request/body/output limits, socket timeouts and a small maximum concurrent-connection count. These controls reduce accidental or trivial local denial-of-service risk; they are **not** a multi-tenant production gateway or full rate-limiting system.

The SSD benchmark also caps file size, chunk size and random-read counts, checks free space before writing and deletes its temporary file after the run.

## Model and tokenizer trust

Model repositories can contain configuration, tokenizer data and other artifacts that change behavior. Treat all model repositories as third-party input.

- Normal filtered OuterRAM model fetches do **not** download repository `*.py` files.
- OuterRAM does not silently enable arbitrary `trust_remote_code` behavior.
- `outerram fetch --force` intentionally requests an unfiltered snapshot and may therefore download additional repository files. Downloading a file is not authorization to execute it; review unexpected repository content before using other tooling that may execute custom code.
- Pin model revisions for reproducibility and review the exact model license separately from technical compatibility.

## Runtime supply chain

Runtime bootstrap defaults to immutable Git revisions. The managed `streamlx` editable checkout is rejected if its origin is redirected, the checkout is modified, or a pinned HEAD does not match the expected revision.

GitHub Actions used by this repository are pinned to immutable commit SHAs. Routine CI includes a repository secret-pattern/action-pin gate, static security analysis, dependency integrity checks and dependency vulnerability auditing. Public repositories additionally run CodeQL.

## Secrets

Do not commit API keys, Hugging Face tokens, GitHub tokens, model-provider credentials or private keys. Prefer environment variables or local secret stores. OuterRAM never needs a cloud LLM credential for local inference.

The public OuterRAM repository starts from a clean history baseline that is separate from the private development archive. If a credential is ever committed in the future, rotate it immediately and follow GitHub's sensitive-data removal process rather than relying on a later deletion commit.

## Reporting a vulnerability

Do **not** open a public issue for a confidential vulnerability, credential exposure or exploit details that could put users at risk.

Once the repository is public, the preferred disclosure path is **GitHub Private Vulnerability Reporting** from the repository's **Security** tab. This feature should be enabled before public announcement. If private vulnerability reporting is temporarily unavailable, contact the repository maintainer privately through GitHub before sharing sensitive details.

For non-sensitive hardening suggestions that do not reveal an exploitable vulnerability, a normal GitHub issue is appropriate.

When reporting privately, include the affected commit/version, platform, minimal reproduction, expected impact and any mitigation you already identified. Do not include unrelated personal data or credentials.
