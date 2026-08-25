from __future__ import annotations

import argparse
from pathlib import Path

from .types import Strategy
from . import __version__


def _add_plan_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("model")
    p.add_argument("--reserve-gib", type=float, default=None, help="RAM kept free for macOS/IDE/KV cache")
    p.add_argument("--strategy", choices=[s.value for s in Strategy], default=None)


def build_parser() -> argparse.ArgumentParser:
    from .cli import (
        cmd_doctor, cmd_inspect, cmd_plan, cmd_check, cmd_fetch, cmd_bootstrap,
        cmd_ready, cmd_serve, cmd_probe, cmd_benchmark, cmd_qualify, cmd_disk_bench,
        cmd_report, cmd_pins, cmd_upstream_check,
    )
    parser = argparse.ArgumentParser(prog="outerram", description="Plan, validate and serve oversized local LLMs on Apple Silicon.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Inspect Mac hardware, disk and inference software")
    doctor.add_argument("--json", action="store_true")
    doctor.add_argument("--streamlx-home", default=None)
    doctor.set_defaults(func=cmd_doctor)

    inspect = sub.add_parser("inspect", help="Inspect local or Hugging Face model metadata")
    inspect.add_argument("model")
    inspect.add_argument("--json", action="store_true")
    inspect.set_defaults(func=cmd_inspect)

    plan = sub.add_parser("plan", help="Choose resident vs dense streaming vs MoE expert streaming")
    _add_plan_args(plan)
    plan.add_argument("--json", action="store_true")
    plan.set_defaults(func=cmd_plan)

    check = sub.add_parser("check", help="Fail-closed compatibility check for model + machine + selected runtime")
    _add_plan_args(check)
    check.add_argument("--json", action="store_true")
    check.set_defaults(func=cmd_check)

    fetch = sub.add_parser("fetch", help="Materialize a Hugging Face model into a local directory/cache")
    fetch.add_argument("model")
    fetch.add_argument("--dir", default=None)
    fetch.add_argument("--force", action="store_true", help="Bypass download guards and allow an unfiltered full snapshot")
    fetch.add_argument("--path-only", action="store_true", help="Print only the materialized local path for shell scripting")
    fetch.add_argument("--json", action="store_true")
    fetch.set_defaults(func=cmd_fetch)

    bootstrap = sub.add_parser("bootstrap", help="Install the runtime selected for this model")
    _add_plan_args(bootstrap)
    bootstrap.add_argument("--streamlx-home", default=None)
    bootstrap.add_argument("--latest", action="store_true", help="Use upstream HEAD instead of OuterRAM's tested revision pins")
    bootstrap.add_argument(
        "--allow-system-python",
        action="store_true",
        help="Allow pip-based runtime installation outside a venv/Conda environment (may modify the base Python)",
    )
    bootstrap.add_argument("--dry-run", action="store_true")
    bootstrap.set_defaults(func=cmd_bootstrap)

    ready = sub.add_parser("ready", help="Check compatibility and whether the selected runtime is installed")
    _add_plan_args(ready)
    ready.add_argument("--streamlx-home", default=None)
    ready.add_argument("--allow-unpinned", action="store_true", help="Treat an installed but unverified upstream revision as ready")
    ready.add_argument("--json", action="store_true")
    ready.set_defaults(func=cmd_ready)

    serve = sub.add_parser("serve", help="Launch the selected runtime")
    _add_plan_args(serve)
    serve.add_argument("--streamlx-home", default=None)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    serve.add_argument("--api-key", default=None, help="Bearer token for OuterRAM's dense-stream server")
    serve.add_argument("--allow-unauthenticated-remote", action="store_true")
    serve.add_argument("--allow-unpinned", action="store_true", help="Run with installed upstream revisions that do not match OuterRAM's tested pins")
    serve.add_argument("--dry-run", action="store_true")
    serve.set_defaults(func=cmd_serve)

    probe = sub.add_parser("probe", help="End-to-end health + model + chat probe against a running local API")
    probe.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    probe.add_argument("--api-key", default=None)
    probe.add_argument("--timeout", type=float, default=30.0)
    probe.add_argument("--tool-call", action="store_true", help="Also verify a structured OpenAI tool call end to end")
    probe.add_argument("--json", action="store_true")
    probe.set_defaults(func=cmd_probe)

    bench = sub.add_parser("benchmark", help="Measure TTFT and decode throughput through the OpenAI-compatible API")
    bench.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    bench.add_argument("--model", default=None)
    bench.add_argument("--prompt", default="Write a Python function that performs binary search and explain its complexity in one sentence.")
    bench.add_argument("--max-tokens", type=int, default=128)
    bench.add_argument("--api-key", default=None)
    bench.add_argument("--timeout", type=float, default=300.0)
    bench.add_argument("--json", action="store_true")
    bench.set_defaults(func=cmd_benchmark)

    qualify = sub.add_parser("qualify", help="Run coding-agent qualification: marker, tool call, and streaming benchmark")
    qualify.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    qualify.add_argument("--model", default=None)
    qualify.add_argument("--prompt", default="Write a Python function that performs binary search and explain its complexity in one sentence.")
    qualify.add_argument("--max-tokens", type=int, default=128)
    qualify.add_argument("--api-key", default=None)
    qualify.add_argument("--timeout", type=float, default=300.0)
    qualify.add_argument("--skip-tool-call", action="store_true", help="Qualify inference only; coding-agent qualification normally requires a structured tool call")
    qualify.add_argument("--checkpoint", default=None, help="Local checkpoint path to bind the API result to machine/model/runtime evidence")
    qualify.add_argument("--reserve-gib", type=float, default=None, help="RAM reserve used when qualifying --checkpoint")
    qualify.add_argument("--strategy", choices=[s.value for s in Strategy], default=None, help="Force strategy when qualifying --checkpoint")
    qualify.add_argument("--streamlx-home", default=None)
    qualify.add_argument("--allow-unpinned", action="store_true", help="Allow an installed runtime whose revision does not match tested pins")
    qualify.add_argument("--disk-path", default=None, help="Also benchmark the filesystem containing model weights")
    qualify.add_argument("--disk-size-mib", type=int, default=256)
    qualify.add_argument("--disk-chunk-mib", type=int, default=4)
    qualify.add_argument("--disk-random-read-kib", type=int, default=1024)
    qualify.add_argument("--disk-random-reads", type=int, default=128)
    qualify.add_argument("--output", default=None, help="Write the qualification JSON to a file")
    qualify.add_argument("--json", action="store_true")
    qualify.set_defaults(func=cmd_qualify)

    disk = sub.add_parser("disk-bench", help="Measure sequential and explicit random-range SSD reads for out-of-core inference")
    disk.add_argument("--path", default=str(Path.home() / ".cache" / "outerram"))
    disk.add_argument("--size-mib", type=int, default=256)
    disk.add_argument("--chunk-mib", type=int, default=4)
    disk.add_argument("--random-read-kib", type=int, default=1024, help="Range size for explicit random pread measurements")
    disk.add_argument("--random-reads", type=int, default=128, help="Number of random range reads")
    disk.add_argument("--json", action="store_true")
    disk.set_defaults(func=cmd_disk_bench)

    report = sub.add_parser("report", help="Generate a redacted diagnostic bundle for bug reports")
    report.add_argument("model", nargs="?", default=None)
    report.add_argument("--reserve-gib", type=float, default=None)
    report.add_argument("--strategy", choices=[s.value for s in Strategy], default=None)
    report.add_argument("--streamlx-home", default=None)
    report.add_argument("--output", default=None)
    report.set_defaults(func=cmd_report)

    pins = sub.add_parser("pins", help="Show tested upstream runtime revisions used by bootstrap")
    pins.add_argument("--json", action="store_true")
    pins.set_defaults(func=cmd_pins)

    upstream = sub.add_parser("upstream-check", help="Verify pinned upstream source/API/license contracts over HTTPS")
    upstream.add_argument("--json", action="store_true")
    upstream.set_defaults(func=cmd_upstream_check)

    return parser
