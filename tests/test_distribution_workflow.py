from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def test_pypi_release_workflow_uses_trusted_publishing_and_release_events():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "types: [published]" in text
    assert "environment: pypi" in text
    assert "id-token: write" in text
    assert "PYPI_TOKEN" not in text
    assert "password:" not in text
    assert "github.event.release.tag_name" in text
    assert '"v$VERSION"' in text


def test_pypi_publish_action_is_immutably_pinned():
    text = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(r"uses:\s*pypa/gh-action-pypi-publish@([^\s]+)", text)
    assert match is not None
    assert re.fullmatch(r"[0-9a-f]{40}", match.group(1))
