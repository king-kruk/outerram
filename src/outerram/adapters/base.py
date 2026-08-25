from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LaunchSpec:
    argv: tuple[str, ...]
    install_hint: str
    description: str
    # Environment values may contain secrets. shell() NEVER renders values.
    env: tuple[tuple[str, str], ...] = ()
    # Files that must exist before launch (for adapters driven by scripts).
    required_paths: tuple[str, ...] = ()

    def shell(self) -> str:
        import shlex

        prefix = " ".join(f"{key}=<redacted>" for key, _value in self.env)
        command = " ".join(shlex.quote(x) for x in self.argv)
        return f"{prefix} {command}".strip()


class Adapter:
    name: str

    def build(self, *, model: str, host: str, port: int, **kwargs) -> LaunchSpec:
        raise NotImplementedError
