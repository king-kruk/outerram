from pathlib import Path

from outerram import __version__


ROOT = Path(__file__).resolve().parents[1]

PUBLIC_SURFACES = (
    "README.md",
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
    "docs/MODEL_LICENSE_POLICY.md",
    "compatibility/README.md",
    "scripts/install-mac.sh",
    "scripts/release-candidate.sh",
    "scripts/release-evidence.py",
    "scripts/verify-release-artifacts.py",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
)


def test_outerram_is_the_only_package_and_cli_identity():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "outerram"' in pyproject
    assert f'version = "{__version__}"' in pyproject
    assert 'outerram = "outerram.entry:main"' in pyproject
    assert "stretchmlx" not in pyproject.lower()
    assert "macllm" not in pyproject.lower()
    assert __version__ == "0.3.0rc3"


def test_public_surfaces_use_only_outerram_identity():
    offenders = []
    for relative in PUBLIC_SURFACES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        if "stretchmlx" in text.lower() or "macllm" in text.lower():
            offenders.append(relative)
    assert offenders == []


def test_model_sidecar_is_outerram_only():
    text = (ROOT / "src" / "outerram" / "model.py").read_text(encoding="utf-8")
    assert '_SOURCE_SIDECAR = ".outerram-source.json"' in text
    assert ".stretchmlx-source.json" not in text


def test_retired_namespace_is_not_packaged():
    assert not (ROOT / "src" / "stretchmlx").exists()
