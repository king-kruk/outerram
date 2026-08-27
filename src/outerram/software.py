from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from importlib import metadata
from pathlib import Path


def _dist_version(*names: str) -> str | None:
    for name in names:
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return None


def _dist_commit(*names: str) -> str | None:
    """Best-effort VCS commit from PEP 610 direct_url.json metadata."""
    for name in names:
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        try:
            raw = dist.read_text("direct_url.json")
            if not raw:
                continue
            data = json.loads(raw)
            vcs = data.get("vcs_info") or {}
            commit = vcs.get("commit_id")
            if isinstance(commit, str) and commit:
                return commit
        except (json.JSONDecodeError, OSError, AttributeError):
            continue
    return None


def _module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def _git_head(path: Path) -> str | None:
    if not (path / ".git").exists() or shutil.which("git") is None:
        return None
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _default_streamlx_home() -> Path:
    return Path.home() / ".cache" / "outerram" / "streamlx"


def software_report(*, streamlx_home: str | None = None) -> dict[str, object]:
    home = Path(streamlx_home).expanduser() if streamlx_home else _default_streamlx_home()
    return {
        "mlx": {"installed": _module("mlx"), "version": _dist_version("mlx")},
        "mlx_lm": {
            "installed": _module("mlx_lm"),
            "version": _dist_version("mlx-lm", "mlx_lm"),
            "commit": _dist_commit("mlx-lm", "mlx_lm"),
        },
        "mlx_flash": {
            "installed": _module("mlx_flash"),
            "version": _dist_version("mlx-flash"),
            "commit": _dist_commit("mlx-flash"),
        },
        "streamlx": {
            "installed": _module("streamlx") or (home / "examples" / "serve.py").exists(),
            "version": _dist_version("streamlx"),
            "commit": _git_head(home) or _dist_commit("streamlx"),
            "home": str(home),
        },
        "omlx": {"installed": shutil.which("omlx") is not None or _module("omlx"), "version": _dist_version("omlx")},
        "git": {"installed": shutil.which("git") is not None},
    }
