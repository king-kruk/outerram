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
