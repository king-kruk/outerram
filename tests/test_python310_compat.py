import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_source_parses_as_python_310():
    for package in ("outerram", "stretchmlx"):
        for path in sorted((ROOT / "src" / package).rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            ast.parse(source, filename=str(path), feature_version=(3, 10))
