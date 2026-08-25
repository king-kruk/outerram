from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from .bootstrap import bootstrap_commands, render_commands, run_bootstrap
from .client import benchmark_server, probe_server, qualify_server
from .compat import assess_compatibility, ensure_compatible, macos_runtime_check
from .diskbench import benchmark_disk
from .launch import build_launch_spec, executable_available, execute
from .machine import detect_machine
from .model import download_space, fetch_model, inspect_model
from .planner import plan_runtime
from .software import software_report
from .types import Strategy
from .runtime_pins import MLX_FLASH_REF, MLX_LM_REF, STREAMLX_REF, MLX_MIN_MACOS_VERSION
from . import __version__
from .validate import runtime_status
from .upstream_contracts import verify_upstream_contracts


def _print(data, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        for key, value in data.items():
            if isinstance(value, (list, tuple)):
                print(f"{key}:" + ("" if value else " []"))
                for item in value:
                    print(f"  - {item}")
            elif isinstance(value, dict):
                print(f"{key}: {json.dumps(value, ensure_ascii=False)}")
            else:
                print(f"{key}: {value}")


def _effective_api_key(args) -> str | None:
    return args.api_key or os.environ.get("OUTERRAM_API_KEY") or os.environ.get("STRETCHMLX_API_KEY")


def _isolated_python_environment() -> bool:
    """Return whether runtime bootstrap is isolated from the user's base Python."""
    if os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX"):
        return True
    base_prefix = getattr(sys, "base_prefix", sys.prefix)
    return sys.prefix != base_prefix


def cmd_doctor(args) -> int:
    machine = detect_machine()
    os_check = macos_runtime_check(machine)
    host_ready = bool(machine.apple_silicon and os_check.ok)
    data = machine.to_dict()
    data["host_requirements"] = {"minimum_macos": MLX_MIN_MACOS_VERSION, "macos_supported": os_check.ok, "detail": os_check.detail, "remediation": os_check.remediation}
    data["ready_for_apple_silicon"] = host_ready
    data["software"] = software_report(streamlx_home=args.streamlx_home)
    _print(data, args.json)
    return 0 if host_ready else 2


def cmd_inspect(args) -> int:
    info = inspect_model(args.model)
    _print(info.to_dict(), args.json)
    return 0


def _make_plan(args):
    machine = detect_machine()
    model = inspect_model(args.model)
    forced = Strategy(args.strategy) if getattr(args, "strategy", None) else None
    plan = plan_runtime(machine, model, reserve_gib=getattr(args, "reserve_gib", None), force=forced)
    return machine, model, plan


def cmd_plan(args) -> int:
    machine, model, plan = _make_plan(args)
    compat = assess_compatibility(machine, model, plan)
    _print({"machine": machine.to_dict(), "model": model.to_dict(), "plan": plan.to_dict(), "compatibility": compat.to_dict()}, args.json)
    return 0


def cmd_check(args) -> int:
    machine, model, plan = _make_plan(args)
    compat = assess_compatibility(machine, model, plan)
    _print({"model": model.to_dict(), "plan": plan.to_dict(), "compatibility": compat.to_dict()}, args.json)
    return 0 if compat.compatible else 5


def cmd_fetch(args) -> int:
    info = inspect_model(args.model)
    if info.local_path:
        data = {"model": args.model, "local_path": info.local_path, "revision": info.revision}
        print(info.local_path) if args.path_only else _print(data, args.json)
        return 0
    free, needed = download_space(info, args.dir)
    if not info.weight_files and not args.force:
        raise RuntimeError("Checkpoint selection is ambiguous or could not be proven. Refusing an unfiltered snapshot download. Choose a repo with one canonical checkpoint, use a local concrete checkpoint, or pass --force to download the full snapshot.")
    if free is not None and needed is not None and free < needed and not args.force:
        raise RuntimeError(f"Download preflight failed: {free:.1f} GiB free, about {needed:.1f} GiB recommended. Free space, choose --dir on a larger volume, or pass --force if you intentionally accept the risk.")
    path = fetch_model(args.model, args.dir, revision=info.revision, weight_files=info.weight_files, full_snapshot=args.force)
    data = {"model": args.model, "local_path": str(path), "free_gib_before": free, "recommended_gib": needed, "revision": info.revision}
    print(str(path)) if args.path_only else _print(data, args.json)
    return 0


def cmd_bootstrap(args) -> int:
    machine, _, plan = _make_plan(args)
    commands = bootstrap_commands(plan, streamlx_home=args.streamlx_home, latest=args.latest)
    print(f"strategy: {plan.strategy.value}")
    print(f"runtime: {plan.runtime}")
    print(f"reproducible_pins: {not args.latest}")
    for command in render_commands(commands):
        print(f"install: {command}")
    if args.dry_run:
        return 0
    os_check = macos_runtime_check(machine)
    if not machine.apple_silicon or not os_check.ok:
        print(os_check.detail, file=sys.stderr)
        if os_check.remediation:
            print(f"fix: {os_check.remediation}", file=sys.stderr)
        return 2
    if not _isolated_python_environment() and not args.allow_system_python:
        print(
            "Refusing runtime bootstrap outside an isolated Python environment because pip upgrades could modify the user's base Python. ",
            "Create/activate a venv (recommended) or Conda environment, then retry. Use --allow-system-python only if you intentionally accept base-environment modification.",
            file=sys.stderr,
        )
        return 3
    if shutil.which("git") is None:
        print("git is required for reproducible runtime bootstrap. Install macOS Command Line Tools and retry.", file=sys.stderr)
        return 3
    return run_bootstrap(commands)


def cmd_ready(args) -> int:
    machine, model, plan = _make_plan(args)
    status = runtime_status(plan, streamlx_home=args.streamlx_home)
    compat = assess_compatibility(machine, model, plan)
    data = {"machine_ok": machine.apple_silicon and macos_runtime_check(machine).ok, "model": model.to_dict(), "plan": plan.to_dict(), "compatibility": compat.to_dict(), "runtime": status, "ready": bool(machine.apple_silicon and compat.compatible and status["installed"] and (status.get("reproducible") is True or args.allow_unpinned))}
    _print(data, args.json)
    return 0 if data["ready"] else 4


def _remote_binding(host: str) -> bool:
    return host not in {"127.0.0.1", "localhost", "::1"}


def cmd_serve(args) -> int:
    machine, model, plan = _make_plan(args)
    compat = assess_compatibility(machine, model, plan)
    if not args.dry_run:
        ensure_compatible(compat)
        status = runtime_status(plan, streamlx_home=args.streamlx_home)
        if status.get("installed") and status.get("reproducible") is not True and not args.allow_unpinned:
            raise RuntimeError("Installed runtime does not match OuterRAM's tested revision pins. Run `outerram bootstrap <model>` to restore tested pins, or pass --allow-unpinned if you intentionally accept an unverified runtime.")
    if _remote_binding(args.host) and plan.strategy != Strategy.DENSE_STREAM and not args.allow_unauthenticated_remote:
        raise RuntimeError(f"Refusing remote bind for {plan.runtime}: OuterRAM cannot enforce authentication on this upstream server. Use localhost, or explicitly pass --allow-unauthenticated-remote at your own risk.")
    effective_api_key = _effective_api_key(args)
    if _remote_binding(args.host) and plan.strategy == Strategy.DENSE_STREAM and not effective_api_key and not args.allow_unauthenticated_remote:
        raise RuntimeError("Dense streaming remote bind requires OUTERRAM_API_KEY/--api-key (or explicit --allow-unauthenticated-remote).")
    spec = build_launch_spec(plan, model=args.model, host=args.host, port=args.port, streamlx_home=args.streamlx_home, api_key=effective_api_key, allow_unauthenticated_remote=args.allow_unauthenticated_remote)
    print(f"strategy: {plan.strategy.value}")
    print(f"runtime: {plan.runtime}")
    print(f"confidence: {plan.confidence}")
    print(f"reason: {plan.reason}")
    for warning in plan.warnings:
        print(f"warning: {warning}")
    print(f"command: {spec.shell()}")
    if args.dry_run:
        return 0
    if not executable_available(spec):
        print("runtime dependency is not installed.", file=sys.stderr)
        print(f"install: {spec.install_hint}", file=sys.stderr)
        return 3
    return execute(spec)


def cmd_probe(args) -> int:
    result = probe_server(args.base_url, api_key=_effective_api_key(args), timeout=args.timeout, test_tools=args.tool_call)
    _print(result, args.json)
    ok = bool(result["healthy"] and result["chat_completed"] and result["response_ok"])
    if args.tool_call:
        ok = bool(ok and result["tool_call_completed"])
    return 0 if ok else 6


def cmd_benchmark(args) -> int:
    result = benchmark_server(args.base_url, prompt=args.prompt, model=args.model, max_tokens=args.max_tokens, api_key=_effective_api_key(args), timeout=args.timeout)
    _print(result.to_dict(), args.json)
    ok = bool(result.ttft_seconds is not None and result.output_chars > 0 and result.chunks > 0 and isinstance(result.prompt_tokens, int) and isinstance(result.completion_tokens, int) and result.completion_tokens > 1 and result.tokens_per_second is not None and result.tokens_per_second > 0)
    return 0 if ok else 7


def cmd_qualify(args) -> int:
    api_result = qualify_server(args.base_url, prompt=args.prompt, model=args.model, max_tokens=args.max_tokens, api_key=_effective_api_key(args), timeout=args.timeout, require_tool_call=not args.skip_tool_call)
    api_qualified = bool(api_result.get("qualified"))
    result = {"schema_version": 2, "generated_at": datetime.now(timezone.utc).isoformat(), "outerram_version": __version__, "base_url": args.base_url, "qualification_scope": "api", "api_qualified": api_qualified, **api_result}
    if getattr(args, "checkpoint", None):
        machine = detect_machine()
        checkpoint = inspect_model(args.checkpoint)
        forced = Strategy(args.strategy) if getattr(args, "strategy", None) else None
        plan = plan_runtime(machine, checkpoint, reserve_gib=getattr(args, "reserve_gib", None), force=forced)
        compat = assess_compatibility(machine, checkpoint, plan)
        status = runtime_status(plan, streamlx_home=getattr(args, "streamlx_home", None))
        pinned_ok = status.get("reproducible") is True or bool(getattr(args, "allow_unpinned", False))
        environment_ready = bool(machine.apple_silicon and compat.compatible and status.get("installed") and pinned_ok)
        result["qualification_scope"] = "api+environment"
        result["environment_ready"] = environment_ready
        result["environment"] = {"machine": machine.to_dict(), "model": checkpoint.to_dict(), "plan": plan.to_dict(), "compatibility": compat.to_dict(), "runtime_status": status}
        result["qualified"] = bool(api_qualified and environment_ready)
    if getattr(args, "disk_path", None):
        result["disk"] = benchmark_disk(args.disk_path, size_mib=args.disk_size_mib, chunk_mib=args.disk_chunk_mib, random_read_kib=args.disk_random_read_kib, random_reads=args.disk_random_reads).to_dict()
    raw = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False)
    if args.output:
        output = Path(args.output).expanduser(); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(raw + "\n", encoding="utf-8")
        print(raw if args.json else str(output))
    else:
        print(raw)
    return 0 if result["qualified"] else 8


def cmd_disk_bench(args) -> int:
    result = benchmark_disk(args.path, size_mib=args.size_mib, chunk_mib=args.chunk_mib, random_read_kib=args.random_read_kib, random_reads=args.random_reads)
    _print(result.to_dict(), args.json)
    return 0


def _redact_home(value):
    home = str(Path.home())
    if isinstance(value, str): return value.replace(home, "~")
    if isinstance(value, list): return [_redact_home(item) for item in value]
    if isinstance(value, tuple): return [_redact_home(item) for item in value]
    if isinstance(value, dict): return {key: _redact_home(item) for key, item in value.items()}
    return value


def cmd_report(args) -> int:
    machine = detect_machine()
    data = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(), "outerram_version": __version__, "machine": machine.to_dict(), "host_requirements": {"minimum_macos": MLX_MIN_MACOS_VERSION, "macos": macos_runtime_check(machine).to_dict()}, "software": software_report(streamlx_home=args.streamlx_home), "runtime_pins": {"mlx-lm": MLX_LM_REF, "mlx-flash": MLX_FLASH_REF, "streamlx": STREAMLX_REF}}
    if args.model:
        model = inspect_model(args.model); forced = Strategy(args.strategy) if args.strategy else None; plan = plan_runtime(machine, model, reserve_gib=args.reserve_gib, force=forced)
        data["model"] = model.to_dict(); data["plan"] = plan.to_dict(); data["compatibility"] = assess_compatibility(machine, model, plan).to_dict(); data["runtime_status"] = runtime_status(plan, streamlx_home=args.streamlx_home)
    raw = json.dumps(_redact_home(data), indent=2, sort_keys=True, ensure_ascii=False)
    if args.output:
        output = Path(args.output).expanduser(); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(raw + "\n", encoding="utf-8"); print(str(output))
    else: print(raw)
    return 0


def cmd_pins(args) -> int:
    _print({"mlx-lm": MLX_LM_REF, "mlx-flash": MLX_FLASH_REF, "streamlx": STREAMLX_REF, "minimum_macos": MLX_MIN_MACOS_VERSION}, args.json)
    return 0


def cmd_upstream_check(args) -> int:
    result = verify_upstream_contracts(); _print(result, args.json); return 0 if result["ok"] else 9


from .cli_parser import build_parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try: return int(args.func(args))
    except KeyboardInterrupt: return 130
    except Exception as exc:
        print(f"outerram: {exc}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
