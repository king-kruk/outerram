from __future__ import annotations

import json

from outerram.entry import main


def test_entry_delegates_existing_commands(capsys):
    assert main(["pins", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mlx-lm"] and payload["mlx-flash"] and payload["streamlx"]


def test_entry_runs_virtual_matrix(capsys):
    assert main(["simulate-matrix", "--profiles", "m5-16gb", "--scenarios", "baseline", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["rows"] == 1
    assert payload["simulation_only"] is True
    assert payload["physical_apple_silicon_validation"] is False


def test_entry_virtual_failure_is_nonzero(capsys):
    assert main(["simulate", "--inject-failure", "health", "--json"]) == 10
    payload = json.loads(capsys.readouterr().out)
    assert payload["simulation_passed"] is False
