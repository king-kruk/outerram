from pathlib import Path
import re

from outerram import __version__

ROOT = Path(__file__).resolve().parents[1]


def _pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project = text.split("[project]", 1)[1]
    match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', project, re.MULTILINE)
    assert match is not None
    return match.group(1)


def test_python_and_pyproject_versions_match():
    assert _pyproject_version() == __version__


def test_external_tester_guide_names_current_version():
    text = (ROOT / "docs" / "EXTERNAL_TESTING.md").read_text(encoding="utf-8")
    expected = re.findall(r"Expected version[^`]*`([^`]+)`", text)
    assert expected == [__version__]


def test_changelog_has_current_version_entry():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## {__version__} — pre-release" in text
