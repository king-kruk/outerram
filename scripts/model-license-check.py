#!/usr/bin/env python3
"""Inspect declared Hugging Face model-card license metadata.

This intentionally reports metadata rather than declaring a model legally
"approved". Custom/research/non-commercial/unknown terms fail closed when
--require-standard-declaration is requested.
"""

from __future__ import annotations

import argparse
import json
import re

from huggingface_hub import HfApi

REVIEW_REQUIRED_IDS = {
    "unknown",
    "other",
    "h-research",
    "apple-amlr",
    "fair-noncommercial-research-license",
    "deepfloyd-if-license",
}
REVIEW_PATTERNS = ("noncommercial", "non-commercial", "research", "nc-")


def card_value(card, key):
    if card is None:
        return None
    try:
        return card.get(key)
    except (AttributeError, TypeError):
        return getattr(card, key, None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("--revision")
    parser.add_argument("--require-standard-declaration", action="store_true")
    args = parser.parse_args()

    info = HfApi().model_info(args.model, revision=args.revision)
    card = getattr(info, "card_data", None)
    license_id = card_value(card, "license")
    license_name = card_value(card, "license_name")
    license_link = card_value(card, "license_link")
    base_model = card_value(card, "base_model")
    revision = getattr(info, "sha", None)

    normalized = str(license_id or "unknown").strip().lower()
    review_required = normalized in REVIEW_REQUIRED_IDS or any(
        re.search(re.escape(pattern), normalized, re.I) for pattern in REVIEW_PATTERNS
    )
    if not license_id:
        status = "unknown"
    elif review_required:
        status = "review_required"
    else:
        status = "declared_standard_license"

    report = {
        "model": args.model,
        "revision": revision,
        "declared_license": license_id,
        "license_name": license_name,
        "license_link": license_link,
        "base_model": base_model,
        "status": status,
        "legal_clearance": False,
        "note": "Model-card metadata only. This is not legal advice and does not determine commercial-use or redistribution rights.",
    }
    print(json.dumps(report, indent=2, sort_keys=True))

    if args.require_standard_declaration and status != "declared_standard_license":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
