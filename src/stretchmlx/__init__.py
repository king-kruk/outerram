"""Deprecated compatibility namespace for the pre-public OuterRAM project name.

New code must import :mod:`outerram`. This namespace remains for the
0.3.0rc1 transition release only and forwards legacy module imports to the
single OuterRAM implementation so the two names cannot drift.
"""

from __future__ import annotations

import importlib
import sys

from outerram import __version__

_MODULE_ALIASES = (
    "bootstrap", "cli", "cli_parser", "client", "compat", "dense_server",
    "diskbench", "entry", "launch", "machine", "model", "planner",
    "runtime_pins", "software", "types", "upstream_contracts", "validate",
    "virtual", "adapters", "adapters.base", "adapters.dense_stream",
    "adapters.moe_stream", "adapters.resident",
)

for _name in _MODULE_ALIASES:
    _module = importlib.import_module(f"outerram.{_name}")
    sys.modules[f"{__name__}.{_name}"] = _module

del _name, _module
