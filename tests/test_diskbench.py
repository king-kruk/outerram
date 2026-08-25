from pathlib import Path
from types import SimpleNamespace

import pytest

import outerram.diskbench as diskbench
from outerram.diskbench import _random_offsets, benchmark_disk


def test_disk_benchmark_runs_captures_random_reads_and_cleans_up(tmp_path: Path):
    result = benchmark_disk(tmp_path, size_mib=32, chunk_mib=4, random_read_kib=256, random_reads=8)
    assert result.size_mib == 32
    assert result.write_mib_s > 0 and result.read_mib_s > 0
    assert result.random_read_mib_s > 0 and result.random_read_iops > 0
    assert result.random_read_p95_ms >= 0
    assert result.random_read_kib == 256 and result.random_reads == 8
    assert not list(tmp_path.glob("outerram-diskbench-*.bin"))


def test_disk_benchmark_rejects_tiny_or_excessive_samples(tmp_path: Path):
    with pytest.raises(ValueError): benchmark_disk(tmp_path, size_mib=8)
    with pytest.raises(ValueError): benchmark_disk(tmp_path, size_mib=2049)
    with pytest.raises(ValueError): benchmark_disk(tmp_path, size_mib=128, chunk_mib=65)


def test_disk_benchmark_rejects_invalid_random_ranges(tmp_path: Path):
    with pytest.raises(ValueError): benchmark_disk(tmp_path, size_mib=32, random_read_kib=64 * 1024)
    with pytest.raises(ValueError): benchmark_disk(tmp_path, size_mib=32, random_reads=2)
    with pytest.raises(ValueError): benchmark_disk(tmp_path, size_mib=32, random_reads=4097)


def test_disk_benchmark_refuses_when_safety_slack_is_unavailable(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(diskbench.shutil, "disk_usage", lambda path: SimpleNamespace(total=10**9, used=10**9 - 40 * 1024 * 1024, free=40 * 1024 * 1024))
    with pytest.raises(RuntimeError, match="safety slack"):
        benchmark_disk(tmp_path, size_mib=32, chunk_mib=4, random_reads=8)
    assert not list(tmp_path.glob("outerram-diskbench-*.bin"))


def test_random_offsets_are_deterministic_aligned_and_in_bounds():
    offsets_a = _random_offsets(32 * 1024 * 1024, 256 * 1024, 16)
    offsets_b = _random_offsets(32 * 1024 * 1024, 256 * 1024, 16)
    assert offsets_a == offsets_b
    assert all(offset % 4096 == 0 for offset in offsets_a)
    assert all(0 <= offset <= (32 * 1024 * 1024 - 256 * 1024) for offset in offsets_a)
