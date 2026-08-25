from pathlib import Path

from outerram import __version__


ROOT = Path(__file__).resolve().parents[1]

ACTIVE_OUTERRAM_FILES = (
    "CONTRIBUTING.md",
    "SECURITY.md",
    "PRIVACY.md",
    "DCO.md",
    "CODE_OF_CONDUCT.md",
    "THIRD_PARTY_NOTICES.md",
    "REFERENCES.md",
    "docs/ARCHITECTURE.md",
    "docs/COMPATIBILITY.md",
    "docs/VIRTUAL_MATRIX.md",
    "docs/MAC_VALIDATION.md",
    "compatibility/README.md",
    "scripts/install-mac.sh",
    "scripts/release-candidate.sh",
    "scripts/public-release-gate.sh",
    "scripts/release-evidence.py",
    "scripts/verify-release-artifacts.py",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
)


def test_outerram_is_primary_package_and_cli_identity():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "outerram"' in pyproject
    assert f'version = "{__version__}"' in pyproject
    assert 'outerram = "outerram.entry:main"' in pyproject
    assert 'stretchmlx = "outerram.entry:main"' in pyproject
    assert "macllm" not in pyproject.lower()
    assert __version__ == "0.3.0rc2"


def test_active_product_surfaces_do_not_use_retired_name():
    offenders = []
    for relative in ACTIVE_OUTERRAM_FILES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        if "StretchMLX" in text:
            offenders.append(relative)
    assert offenders == []


def test_readme_identifies_outerram_and_limits_retired_name_to_migration_context():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert text.startswith("# OuterRAM\n")
    assert "## Rename / compatibility window" in text
    assert "provisional name **StretchMLX**" in text
    assert "`outerram` is the canonical command and package identity" in text


def test_model_sidecar_writes_outerram_and_keeps_legacy_read_fallback():
    text = (ROOT / "src" / "outerram" / "model.py").read_text(encoding="utf-8")
    assert '_SOURCE_SIDECAR = ".outerram-source.json"' in text
    assert '_LEGACY_SOURCE_SIDECAR = ".stretchmlx-source.json"' in text


def test_model_license_policy_documents_legacy_sidecar_as_migration_only():
    text = (ROOT / "docs" / "MODEL_LICENSE_POLICY.md").read_text(encoding="utf-8")
    assert "Provenance captured by OuterRAM" in text
    assert "`.outerram-source.json`" in text
    assert "legacy `.stretchmlx-source.json`" in text
    assert "new materializations write `.outerram-source.json`" in text


def test_legacy_namespace_contains_no_duplicate_implementation():
    legacy = ROOT / "src" / "stretchmlx"
    tracked_python = sorted(path.relative_to(legacy).as_posix() for path in legacy.rglob("*.py"))
    assert tracked_python == ["__init__.py"]
    text = (legacy / "__init__.py").read_text(encoding="utf-8")
    assert "single OuterRAM implementation" in text
    assert 'importlib.import_module(f"outerram.{_name}")' in text


def test_retired_name_only_exists_as_explicit_transition_cli_alias():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert pyproject.count('stretchmlx = "outerram.entry:main"') == 1
