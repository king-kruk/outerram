from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

from .runtime_pins import MLX_FLASH_REF, MLX_LM_REF, STREAMLX_REF
from .types import RuntimePlan, Strategy

_STREAMLX_ORIGIN = "https://github.com/srcterm/streamlx.git"


def _git_text(home: Path, *args: str) -> str:
    proc = subprocess.run(
        ("git", "-C", str(home), *args),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Could not verify managed streamlx checkout: {' '.join(args)}")
    return proc.stdout.strip()


def verify_streamlx_checkout(home: str | Path, *, expected_ref: str | None = None) -> None:
    """Fail closed if the managed streamlx checkout is redirected or modified."""
    path = Path(home).expanduser().resolve()
    if not (path / ".git").exists():
        raise RuntimeError(f"Refusing unverified streamlx directory without .git metadata: {path}")
    origin = _git_text(path, "remote", "get-url", "origin")
    if origin.rstrip("/") != _STREAMLX_ORIGIN.rstrip("/"):
        raise RuntimeError(
            f"Refusing streamlx checkout with unexpected origin {origin!r}; expected {_STREAMLX_ORIGIN}"
        )
    dirty = _git_text(path, "status", "--porcelain", "--untracked-files=all")
    if dirty:
        raise RuntimeError(
            "Refusing to install or execute a modified streamlx checkout. "
            "Move local changes elsewhere or use a fresh managed checkout."
        )
    if expected_ref:
        head = _git_text(path, "rev-parse", "HEAD").lower()
        if head != expected_ref.lower():
            raise RuntimeError(f"streamlx HEAD mismatch: expected {expected_ref}, found {head}")


def bootstrap_commands(
    plan: RuntimePlan,
    *,
    streamlx_home: str | None = None,
    latest: bool = False,
) -> list[tuple[str, ...]]:
    py = sys.executable
    mlx_lm = "git+https://github.com/ml-explore/mlx-lm.git" + ("" if latest else f"@{MLX_LM_REF}")
    mlx_flash = "git+https://github.com/matt-k-wong/mlx-flash.git" + ("" if latest else f"@{MLX_FLASH_REF}")

    if plan.strategy == Strategy.RESIDENT:
        return [(py, "-m", "pip", "install", "-U", mlx_lm)]
    if plan.strategy == Strategy.DENSE_STREAM:
        return [
            (py, "-m", "pip", "install", "-U", mlx_flash),
            (py, "-m", "pip", "install", "-U", mlx_lm),
        ]

    home = Path(streamlx_home or (Path.home() / ".cache" / "outerram" / "streamlx")).expanduser()
    cmds: list[tuple[str, ...]] = []
    if not home.exists():
        home.parent.mkdir(parents=True, exist_ok=True)
        cmds.append(("git", "clone", _STREAMLX_ORIGIN, str(home)))
    if latest:
        cmds.append(("git", "-C", str(home), "fetch", "origin", "main"))
        cmds.append(("git", "-C", str(home), "checkout", "--detach", "origin/main"))
    else:
        cmds.append(("git", "-C", str(home), "fetch", "origin", "main"))
        cmds.append(("git", "-C", str(home), "checkout", "--detach", STREAMLX_REF))
    cmds.extend([
        (py, "-m", "pip", "install", "-e", str(home)),
        (py, "-m", "pip", "install", "-U", mlx_lm),
    ])
    return cmds


def render_commands(commands: list[tuple[str, ...]]) -> list[str]:
    return [" ".join(shlex.quote(part) for part in command) for command in commands]


def run_bootstrap(commands: list[tuple[str, ...]]) -> int:
    expected_heads: dict[Path, str] = {}
    for command in commands:
        if len(command) >= 5 and command[0:2] == ("git", "-C"):
            home = Path(command[2]).expanduser().resolve()
            operation = command[3]
            if operation == "fetch" and home.exists():
                verify_streamlx_checkout(home)
            if operation == "checkout" and len(command) >= 6:
                target = command[-1]
                if len(target) == 40 and all(ch in "0123456789abcdefABCDEF" for ch in target):
                    expected_heads[home] = target

        proc = subprocess.run(command, check=False)
        if proc.returncode != 0:
            return int(proc.returncode)

        if len(command) >= 5 and command[0:2] == ("git", "-C") and command[3] == "checkout":
            home = Path(command[2]).expanduser().resolve()
            verify_streamlx_checkout(home, expected_ref=expected_heads.get(home))

        if len(command) >= 5 and command[1:4] == ("-m", "pip", "install") and "-e" in command:
            editable_index = command.index("-e")
            if editable_index + 1 < len(command):
                editable = Path(command[editable_index + 1]).expanduser().resolve()
                if (editable / ".git").exists():
                    verify_streamlx_checkout(editable, expected_ref=expected_heads.get(editable))
    return 0
