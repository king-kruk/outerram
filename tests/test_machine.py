import platform

import pytest

import outerram.machine as machine_module
from outerram.machine import _parse_memory_free_percent, _parse_power_source, _parse_swap_used_gib


def test_parse_swap_usage_from_macos_sysctl():
    text = "total = 4096.00M  used = 1536.50M  free = 2559.50M  (encrypted)"
    assert _parse_swap_used_gib(text) == 1.5
    assert _parse_swap_used_gib("used = 2.25G") == 2.25
    assert _parse_swap_used_gib("nonsense") is None


def test_parse_memory_pressure_free_percentage():
    assert _parse_memory_free_percent("System-wide memory free percentage: 42%") == 42.0
    assert _parse_memory_free_percent("memory free percentage: 7.5%") == 7.5
    assert _parse_memory_free_percent(None) is None


def test_parse_power_source():
    assert _parse_power_source("Now drawing from 'AC Power'") == "AC Power"
    assert _parse_power_source("Now drawing from 'Battery Power'") == "Battery Power"
    assert _parse_power_source("unknown") is None


def test_detect_machine_routes_windows_to_windows_memory_api(monkeypatch):
    gib = 1024 ** 3
    monkeypatch.setattr(machine_module.platform, "system", lambda: "Windows")
    monkeypatch.setattr(machine_module.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(machine_module, "_windows_mem_bytes", lambda: 16 * gib)
    monkeypatch.setattr(
        machine_module,
        "_linux_mem_bytes",
        lambda: (_ for _ in ()).throw(AssertionError("Linux memory detector must not run on Windows")),
    )
    monkeypatch.setattr(
        machine_module,
        "_darwin_mem_bytes",
        lambda: (_ for _ in ()).throw(AssertionError("Darwin memory detector must not run on Windows")),
    )

    info = machine_module.detect_machine()

    assert info.system == "Windows"
    assert info.machine == "AMD64"
    assert info.total_memory_gib == 16.0
    assert info.apple_silicon is False


@pytest.mark.skipif(platform.system() != "Windows", reason="requires the native Windows memory API")
def test_windows_memory_api_returns_total_physical_memory():
    total = machine_module._windows_mem_bytes()
    assert total is not None
    assert total > 0
