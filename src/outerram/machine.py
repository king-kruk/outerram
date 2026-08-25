from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .types import MachineInfo

_GIB = 1024 ** 3


def _sysctl(name: str) -> str | None:
    try:
        out = subprocess.check_output(["sysctl", "-n", name], text=True, stderr=subprocess.DEVNULL).strip()
        return out or None
    except (OSError, subprocess.SubprocessError):
        return None


def _command(*argv: str) -> str | None:
    try:
        out = subprocess.check_output(list(argv), text=True, stderr=subprocess.DEVNULL).strip()
        return out or None
    except (OSError, subprocess.SubprocessError):
        return None


def _darwin_mem_bytes() -> int | None:
    value = _sysctl("hw.memsize")
    try:
        return int(value) if value else None
    except ValueError:
        return None


def _linux_mem_bytes() -> int | None:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return int(pages) * int(page_size)
    except (ValueError, OSError, AttributeError):
        return None


def _free_disk_gib(path: Path | None = None) -> float | None:
    try:
        target = path or Path.home()
        return round(shutil.disk_usage(target).free / _GIB, 2)
    except OSError:
        return None


def _parse_swap_used_gib(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"\bused\s*=\s*([0-9.]+)([KMGTP])", text, re.I)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).upper()
    scale = {"K": 1 / (1024 ** 2), "M": 1 / 1024, "G": 1, "T": 1024, "P": 1024 ** 2}[unit]
    return round(value * scale, 3)


def _parse_memory_free_percent(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"(?:system-wide\s+)?memory\s+free\s+percentage\s*:\s*([0-9.]+)%", text, re.I)
    if not match:
        return None
    value = float(match.group(1))
    return max(0.0, min(100.0, value))


def _parse_power_source(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"Now drawing from ['\"]([^'\"]+)['\"]", text, re.I)
    if match:
        return match.group(1).strip()
    if "Battery Power" in text:
        return "Battery Power"
    if "AC Power" in text:
        return "AC Power"
    return None


def detect_machine() -> MachineInfo:
    system = platform.system()
    machine = platform.machine()
    mem = _darwin_mem_bytes() if system == "Darwin" else _linux_mem_bytes()
    if not mem:
        raise RuntimeError("Could not determine total system memory")
    apple_silicon = system == "Darwin" and machine in {"arm64", "aarch64"}
    chip = None
    swap_used = None
    memory_free = None
    power_source = None
    if system == "Darwin":
        chip = _sysctl("machdep.cpu.brand_string") or _sysctl("hw.model")
        swap_used = _parse_swap_used_gib(_sysctl("vm.swapusage"))
        memory_free = _parse_memory_free_percent(_command("memory_pressure", "-Q"))
        power_source = _parse_power_source(_command("pmset", "-g", "batt"))
    return MachineInfo(
        system=system,
        machine=machine,
        total_memory_gib=round(mem / _GIB, 2),
        apple_silicon=apple_silicon,
        free_disk_gib=_free_disk_gib(),
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        os_version=platform.mac_ver()[0] if system == "Darwin" else platform.release(),
        chip=chip,
        swap_used_gib=swap_used,
        memory_free_percent=memory_free,
        power_source=power_source,
    )
