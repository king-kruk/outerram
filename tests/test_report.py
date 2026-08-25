from outerram.cli import _redact_home


def test_redact_home_recursively(monkeypatch):
    from pathlib import Path
    home = str(Path.home())
    data = {"path": home + "/models", "nested": [home + "/cache", {"x": home}]}
    out = _redact_home(data)
    assert out["path"].startswith("~/")
    assert out["nested"][0].startswith("~/")
    assert out["nested"][1]["x"] == "~"


def test_report_without_model_writes_redacted_json(tmp_path):
    from types import SimpleNamespace
    import json
    from outerram.cli import cmd_report

    out = tmp_path / "report.json"
    args = SimpleNamespace(model=None, streamlx_home=None, strategy=None, reserve_gib=None, output=str(out))
    assert cmd_report(args) == 0
    data = json.loads(out.read_text())
    assert data["schema_version"] == 1
    assert "runtime_pins" in data
    assert "machine" in data
