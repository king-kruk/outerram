# Model license policy

OuterRAM separates **technical compatibility** from **legal permission**.

A successful `inspect`, `plan`, `ready`, `serve`, benchmark, or qualification result is never a representation that a model may be used commercially, redistributed, modified, hosted, fine-tuned, or used for a particular purpose.

## Rules

1. Every compatibility claim must identify the exact model repository and revision.
2. Model-family names are not enough; sibling repos and quantizations can carry different terms.
3. Quantized or converted weights may have obligations from both the conversion repository and the base model.
4. `license: unknown`, `license: other`, custom terms, research-only terms, and non-commercial terms require explicit human review.
5. OuterRAM releases do not bundle model weights unless a separate redistribution review is completed and documented.
6. Marketing must not describe a model as "free", "open source", "commercially usable", or "redistributable" solely because it can be downloaded or loaded.
7. A license review is revision-specific and should be repeated when the model repository or license changes.

Hugging Face documents repository license metadata and explicitly instructs users to seek out and respect the applicable project license: https://huggingface.co/docs/hub/repositories-licenses

## Provenance captured by OuterRAM

For a Hugging Face model, OuterRAM resolves the immutable repository revision and reads the model card's declared license metadata when available. A materialized checkpoint receives `.outerram-source.json` schema v2 containing:

- repository ID;
- immutable revision;
- selected checkpoint weight files;
- declared `license`, `license_name`, and `license_link` metadata when present;
- declared base model(s) when present;
- the metadata source; and
- `legal_clearance: false` plus an explicit note that metadata is descriptive evidence only.

`inspect`, `report`, and environment-bound `qualify` include these fields through `ModelInfo`. This makes the evidence portable and available offline after materialization, but it **does not** transform model-card metadata into a legal opinion or usage grant.

If a repository has no clear license metadata, OuterRAM records the absence rather than guessing from the model family, organization, README wording, or a related base model.

## Compatibility results

A public compatibility row should contain at minimum:

- repository ID;
- immutable revision or commit;
- quantization or conversion repository when applicable;
- declared license identifier;
- base-model license identifier or link when different;
- a field stating whether legal or commercial status was reviewed or remains `unknown`.

The legal-status field is informational and must not be presented as legal advice.
