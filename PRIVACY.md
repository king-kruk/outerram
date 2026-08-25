# Privacy and network behavior

_Last reviewed: 2026-08-25._

OuterRAM is designed for local inference on a single-user workstation. The project itself does not operate a hosted inference service and does not intentionally collect prompts, completions, repository contents, API keys, telemetry, analytics, advertising identifiers, or personal data.

## Local inference

By default the local API binds to loopback (`127.0.0.1`). Prompts and generated responses are processed by the local runtime/model unless the user connects OuterRAM to another service or explicitly exposes the endpoint.

## Commands that can access the network

OuterRAM is **local-first, not automatically fully offline**. Network access can occur when a user asks the tool to:

- inspect or download a Hugging Face model;
- bootstrap/update a runtime from GitHub or Python package indexes;
- run the upstream contract check;
- install Python dependencies.

Those third-party services may receive ordinary request metadata such as IP address, account/token information if supplied, requested repository/model identifiers, and other data governed by their own privacy terms.

## Diagnostic and qualification files

`doctor`, `report`, benchmark, and `qualification.json` artifacts can contain technical metadata such as OS/macOS version, chip/machine information, memory/swap/storage measurements, model repository/revision, runtime versions, endpoint URLs, and generated test responses.

Before sharing a diagnostic artifact publicly, users should inspect it and remove information they consider identifying, confidential, proprietary, or sensitive. OuterRAM must not silently upload diagnostic artifacts.

## Secrets

API keys and provider tokens must not be written to source control or diagnostic reports. OuterRAM documentation and test fixtures must use placeholders/redaction.

## Future hosted features

Any future feature that uploads prompts, benchmark results, diagnostics, model metadata, user identifiers, or other data to infrastructure operated by OuterRAM requires a separate privacy review, explicit disclosure, data-minimization design, retention/deletion rules, security controls, and an applicable privacy policy before launch.

This document describes current project behavior and is not legal advice.
