from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from . import __version__
from .client import qualify_server
from .compat import assess_compatibility
from .launch import build_launch_spec
from .planner import plan_runtime
from .runtime_pins import (
    MLX_FLASH_REF,
    MLX_FLASH_VERSION,
    MLX_LM_REF,
    MLX_LM_VERSION,
    MLX_MIN_VERSION,
    STREAMLX_REF,
    STREAMLX_VERSION,
)
from .types import CheckpointKind, MachineInfo, ModelInfo, ModelSource, Strategy

_GB_TO_GIB = 1_000_000_000 / (1024 ** 3)


@dataclass(frozen=True)
class VirtualProfile:
    name: str
    machine: MachineInfo
    description: str
    nominal_ssd_seq_mib_s: float = 3000.0
    nominal_ssd_random_mib_s: float = 1800.0


@dataclass(frozen=True)
class VirtualScenario:
    name: str
    reserve_extra_gib: float = 0.0
    weight_scale: float = 1.0
    swap_used_gib: float = 0.0
    memory_free_percent: float = 70.0
    ssd_seq_scale: float = 1.0
    ssd_random_scale: float = 1.0
    context_tokens: int = 8192
    description: str = ""


@dataclass(frozen=True)
class VirtualModelProfile:
    name: str
    model: ModelInfo
    source_size_gb: float
    source_note: str


M4_16GB = VirtualProfile(
    name="m4-16gb",
    machine=MachineInfo(
        system="Darwin", machine="arm64", total_memory_gib=16.0, apple_silicon=True,
        free_disk_gib=200.0, python_version="3.12.7", os_version="26.6",
        chip="Apple M4 (virtual profile)", swap_used_gib=0.0,
        memory_free_percent=70.0, power_source="AC Power",
    ),
    description="Synthetic Apple M4 / 16 GiB unified-memory planning profile.",
    nominal_ssd_seq_mib_s=2800.0,
    nominal_ssd_random_mib_s=1600.0,
)

M5_16GB = VirtualProfile(
    name="m5-16gb",
    machine=MachineInfo(
        system="Darwin", machine="arm64", total_memory_gib=16.0, apple_silicon=True,
        free_disk_gib=200.0, python_version="3.12.7", os_version="26.6",
        chip="Apple M5 (virtual profile)", swap_used_gib=0.0,
        memory_free_percent=70.0, power_source="AC Power",
    ),
    description="Synthetic Apple M5 / 16 GiB unified-memory planning profile.",
    nominal_ssd_seq_mib_s=3200.0,
    nominal_ssd_random_mib_s=1900.0,
)

M5_24GB = VirtualProfile(
    name="m5-24gb",
    machine=MachineInfo(
        system="Darwin", machine="arm64", total_memory_gib=24.0, apple_silicon=True,
        free_disk_gib=300.0, python_version="3.12.7", os_version="26.6",
        chip="Apple M5 / 24 GiB (virtual profile)", swap_used_gib=0.0,
        memory_free_percent=72.0, power_source="AC Power",
    ),
    description="Synthetic Apple M5 / 24 GiB unified-memory planning profile.",
    nominal_ssd_seq_mib_s=3200.0,
    nominal_ssd_random_mib_s=1900.0,
)

M5_32GB = VirtualProfile(
    name="m5-32gb",
    machine=MachineInfo(
        system="Darwin", machine="arm64", total_memory_gib=32.0, apple_silicon=True,
        free_disk_gib=400.0, python_version="3.12.7", os_version="26.6",
        chip="Apple M5 / 32 GiB (virtual profile)", swap_used_gib=0.0,
        memory_free_percent=74.0, power_source="AC Power",
    ),
    description="Synthetic Apple M5 / 32 GiB unified-memory planning profile.",
    nominal_ssd_seq_mib_s=3400.0,
    nominal_ssd_random_mib_s=2000.0,
)

M5_PRO_48GB = VirtualProfile(
    name="m5-pro-48gb",
    machine=MachineInfo(
        system="Darwin", machine="arm64", total_memory_gib=48.0, apple_silicon=True,
        free_disk_gib=500.0, python_version="3.12.7", os_version="26.6",
        chip="Apple M5 Pro / 48 GiB (virtual profile)", swap_used_gib=0.0,
        memory_free_percent=76.0, power_source="AC Power",
    ),
    description="Synthetic Apple M5 Pro / 48 GiB unified-memory planning profile.",
    nominal_ssd_seq_mib_s=4200.0,
    nominal_ssd_random_mib_s=2400.0,
)

M5_MAX_64GB = VirtualProfile(
    name="m5-max-64gb",
    machine=MachineInfo(
        system="Darwin", machine="arm64", total_memory_gib=64.0, apple_silicon=True,
        free_disk_gib=750.0, python_version="3.12.7", os_version="26.6",
        chip="Apple M5 Max / 64 GiB (virtual profile)", swap_used_gib=0.0,
        memory_free_percent=78.0, power_source="AC Power",
    ),
    description="Synthetic Apple M5 Max / 64 GiB unified-memory planning profile.",
    nominal_ssd_seq_mib_s=5200.0,
    nominal_ssd_random_mib_s=2800.0,
)

QWEN38_27B_3BIT_TEXT = VirtualModelProfile(
    name="qwen38-27b-3bit-text",
    model=ModelInfo(
        model="lukaskremla/Qwen3.8-27B-3bit-MLX-TextOnly",
        local_path="/virtual/models/Qwen3.8-27B-3bit-MLX-TextOnly",
        architecture="Qwen3_5ForConditionalGeneration",
        model_type="qwen3_5_text",
        weight_size_gib=round(11.77 * _GB_TO_GIB, 3),
        is_moe=False,
        num_experts=None,
        top_k=None,
        quant_bits=3,
        source=ModelSource.LOCAL,
        checkpoint_kind=CheckpointKind.SAFETENSORS,
        weight_file_count=3,
        quantized=True,
        revision="c98bba5",
        weight_files=(
            "model-00001-of-00003.safetensors",
            "model-00002-of-00003.safetensors",
            "model-00003-of-00003.safetensors",
        ),
        origin="lukaskremla/Qwen3.8-27B-3bit-MLX-TextOnly",
        checkpoint_complete=True,
        declared_license="apache-2.0",
        license_metadata_source="virtual-profile/public-model-metadata",
    ),
    source_size_gb=11.77,
    source_note=(
        "Public Hugging Face tree reports ~11.8 GB total; visible shard sizes are "
        "5.35 GB + 5.37 GB + 1.05 GB. This virtual profile converts that decimal size to GiB."
    ),
)

PROFILES = {profile.name: profile for profile in (M4_16GB, M5_16GB, M5_24GB, M5_32GB, M5_PRO_48GB, M5_MAX_64GB)}
MODELS = {QWEN38_27B_3BIT_TEXT.name: QWEN38_27B_3BIT_TEXT}

SCENARIOS = {
    scenario.name: scenario
    for scenario in (
        VirtualScenario(name="baseline", description="Default OuterRAM reserve and healthy machine telemetry."),
        VirtualScenario(name="heavy-ide", reserve_extra_gib=1.0, memory_free_percent=45.0, description="IDE, terminals and coding-agent tools consume an extra 1 GiB of protected headroom."),
        VirtualScenario(name="long-context", reserve_extra_gib=2.5, memory_free_percent=35.0, context_tokens=65536, description="Conservative 64K-context stress reserve; this is not a measured KV-cache size."),
        VirtualScenario(name="swap-pressure", reserve_extra_gib=0.5, swap_used_gib=2.0, memory_free_percent=7.0, description="Pre-existing swap and red-zone memory pressure before inference."),
        VirtualScenario(name="slow-ssd", reserve_extra_gib=0.5, ssd_seq_scale=0.30, ssd_random_scale=0.25, description="External/contended SSD stress profile; throughput values are synthetic risk inputs only."),
        VirtualScenario(name="footprint-plus-10pct", weight_scale=1.10, description="Model/runtime footprint sensitivity test at +10% effective weight bytes."),
    )
}


class _VirtualRuntime:
    def __init__(self, model_id: str, *, failure: str | None = None):
        self.model_id = model_id
        self.failure = failure

    def handler(self):
        runtime = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, format: str, *args: Any) -> None:
                return

            def _json(self, status: int, payload: dict[str, Any]) -> None:
                raw = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:
                if self.path == "/health":
                    status = "error" if runtime.failure == "health" else "ok"
                    self._json(200, {"status": status, "runtime": "outerram-virtual"})
                    return
                if self.path == "/v1/models":
                    self._json(200, {"object": "list", "data": [{"id": runtime.model_id, "object": "model"}]})
                    return
                self._json(404, {"error": {"message": "not found"}})

            def do_POST(self) -> None:
                if self.path != "/v1/chat/completions":
                    self._json(404, {"error": {"message": "not found"}})
                    return
                length = int(self.headers.get("Content-Length", "0"))
                try:
                    payload = json.loads(self.rfile.read(length) or b"{}")
                except json.JSONDecodeError:
                    self._json(400, {"error": {"message": "invalid json"}})
                    return
                if payload.get("stream"):
                    self._stream(payload)
                else:
                    self._chat(payload)

            def _chat(self, payload: dict[str, Any]) -> None:
                messages = payload.get("messages") or []
                has_tool_result = any(isinstance(m, dict) and m.get("role") == "tool" for m in messages)
                if has_tool_result:
                    content = "BROKEN_TOOL" if runtime.failure == "tool-roundtrip" else "OUTERRAM_TOOL_OK"
                    message: dict[str, Any] = {"role": "assistant", "content": content}
                elif payload.get("tools"):
                    if runtime.failure == "tool-call":
                        message = {"role": "assistant", "content": "I will add them myself."}
                    else:
                        message = {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": "call_virtual_add",
                                "type": "function",
                                "function": {"name": "add_numbers", "arguments": "{\"a\":2,\"b\":3}"},
                            }],
                        }
                else:
                    user_text = " ".join(str(m.get("content") or "") for m in messages if isinstance(m, dict) and m.get("role") == "user")
                    if "OUTERRAM_OK" in user_text:
                        content = "BROKEN_MARKER" if runtime.failure == "marker" else "OUTERRAM_OK"
                    else:
                        content = "def binary_search(items, target):\n    return -1\n"
                    message = {"role": "assistant", "content": content}
                self._json(200, {
                    "id": "chatcmpl-virtual",
                    "object": "chat.completion",
                    "model": runtime.model_id,
                    "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 16, "completion_tokens": 8, "total_tokens": 24},
                })

            def _stream(self, payload: dict[str, Any]) -> None:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                if runtime.failure == "empty-stream":
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
                    return
                time.sleep(0.015)
                chunks = ["def ", "binary_search", "(items, target):\n", "    return -1\n"]
                for idx, text in enumerate(chunks):
                    obj = {"id": "chatcmpl-virtual", "object": "chat.completion.chunk", "model": runtime.model_id, "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}]}
                    self.wfile.write(("data: " + json.dumps(obj) + "\n\n").encode("utf-8"))
                    self.wfile.flush()
                    if idx < len(chunks) - 1:
                        time.sleep(0.005)
                if runtime.failure != "usage":
                    usage = {"id": "chatcmpl-virtual", "object": "chat.completion.chunk", "model": runtime.model_id, "choices": [], "usage": {"prompt_tokens": 24, "completion_tokens": 12, "total_tokens": 36}}
                    self.wfile.write(("data: " + json.dumps(usage) + "\n\n").encode("utf-8"))
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()

        return Handler


def _sensitivity(machine: MachineInfo, model: ModelInfo) -> list[dict[str, Any]]:
    baseline_reserve = plan_runtime(machine, model).reserved_memory_gib
    cases = [
        ("baseline", baseline_reserve, 1.00),
        ("heavier-os-ide", baseline_reserve + 0.5, 1.00),
        ("high-headroom", baseline_reserve + 1.0, 1.00),
        ("runtime-footprint-plus-5pct", baseline_reserve, 1.05),
        ("runtime-footprint-plus-10pct", baseline_reserve, 1.10),
    ]
    out: list[dict[str, Any]] = []
    for name, reserve, scale in cases:
        adjusted = ModelInfo(**{**asdict(model), "weight_size_gib": round((model.weight_size_gib or 0) * scale, 3)})
        plan = plan_runtime(machine, adjusted, reserve_gib=reserve)
        out.append({
            "case": name,
            "reserve_gib": reserve,
            "effective_weight_scale": scale,
            "effective_weight_gib": adjusted.weight_size_gib,
            "strategy": plan.strategy.value,
            "resident_budget_gib": plan.resident_budget_gib,
            "reason": plan.reason,
        })
    return out


def _scenario_machine(profile: VirtualProfile, scenario: VirtualScenario) -> MachineInfo:
    data = asdict(profile.machine)
    data["swap_used_gib"] = scenario.swap_used_gib
    data["memory_free_percent"] = scenario.memory_free_percent
    return MachineInfo(**data)


def _scenario_model(model: ModelInfo, scenario: VirtualScenario) -> ModelInfo:
    data = asdict(model)
    if model.weight_size_gib is not None:
        data["weight_size_gib"] = round(model.weight_size_gib * scenario.weight_scale, 3)
    return ModelInfo(**data)


def _ssd_risk(strategy: Strategy, sequential_mib_s: float) -> str:
    if strategy == Strategy.RESIDENT:
        return "not-critical"
    if sequential_mib_s < 1200:
        return "high"
    if sequential_mib_s < 2200:
        return "medium"
    return "low"


def _memory_risk(machine: MachineInfo) -> str:
    if (machine.swap_used_gib or 0.0) >= 1.0 or (machine.memory_free_percent or 100.0) < 10.0:
        return "high"
    if (machine.memory_free_percent or 100.0) < 25.0:
        return "medium"
    return "low"


def evaluate_virtual_scenario(profile: VirtualProfile, model_profile: VirtualModelProfile, scenario: VirtualScenario) -> dict[str, Any]:
    machine = _scenario_machine(profile, scenario)
    model = _scenario_model(model_profile.model, scenario)
    baseline_reserve = plan_runtime(profile.machine, model_profile.model).reserved_memory_gib
    reserve = min(baseline_reserve + scenario.reserve_extra_gib, machine.total_memory_gib - 1.0)
    plan = plan_runtime(machine, model, reserve_gib=reserve)
    compatibility = assess_compatibility(machine, model, plan)
    seq = round(profile.nominal_ssd_seq_mib_s * scenario.ssd_seq_scale, 1)
    rnd = round(profile.nominal_ssd_random_mib_s * scenario.ssd_random_scale, 1)
    advisory = [check.detail for check in compatibility.checks if (not check.ok) and check.severity == "warning"]
    if plan.strategy != Strategy.RESIDENT and _ssd_risk(plan.strategy, seq) in {"medium", "high"}:
        advisory.append("Synthetic SSD stress input suggests streamed inference may be storage-bound; measure the real model volume before making a performance claim.")
    return {
        "profile": profile.name,
        "chip": machine.chip,
        "memory_gib": machine.total_memory_gib,
        "scenario": scenario.name,
        "scenario_description": scenario.description,
        "context_tokens": scenario.context_tokens,
        "reserve_gib": plan.reserved_memory_gib,
        "effective_weight_gib": model.weight_size_gib,
        "strategy": plan.strategy.value,
        "runtime": plan.runtime,
        "compatible": compatibility.compatible,
        "planner_confidence": plan.confidence,
        "memory_risk": _memory_risk(machine),
        "ssd": {"synthetic": True, "sequential_mib_s": seq, "random_mib_s": rnd, "streaming_risk": _ssd_risk(plan.strategy, seq)},
        "warnings": list(plan.warnings),
        "advisory": advisory,
        "physical_validation": False,
        "performance_claim_allowed": False,
    }


def run_virtual_matrix(*, model_name: str = QWEN38_27B_3BIT_TEXT.name, profile_names: list[str] | tuple[str, ...] | None = None, scenario_names: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    model_profile = MODELS[model_name]
    selected_profiles = [PROFILES[name] for name in (profile_names or tuple(PROFILES))]
    selected_scenarios = [SCENARIOS[name] for name in (scenario_names or tuple(SCENARIOS))]
    rows = [evaluate_virtual_scenario(profile, model_profile, scenario) for profile in selected_profiles for scenario in selected_scenarios]
    counts = {strategy.value: 0 for strategy in Strategy}
    for row in rows:
        counts[row["strategy"]] += 1
    transitions = {}
    for profile in selected_profiles:
        by_scenario = {row["scenario"]: row for row in rows if row["profile"] == profile.name}
        transitions[profile.name] = {
            "baseline": by_scenario.get("baseline", {}).get("strategy"),
            "heavy_ide": by_scenario.get("heavy-ide", {}).get("strategy"),
            "long_context": by_scenario.get("long-context", {}).get("strategy"),
            "slow_ssd": by_scenario.get("slow-ssd", {}).get("strategy"),
        }
    return {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "outerram_version": __version__,
        "qualification_scope": "virtual-planner-stress-matrix",
        "simulation_only": True,
        "physical_apple_silicon_validation": False,
        "metal_inference_executed": False,
        "performance_claim_allowed": False,
        "model_profile": {"name": model_profile.name, "source_size_gb": model_profile.source_size_gb, "model": model_profile.model.to_dict()},
        "profiles": [profile.name for profile in selected_profiles],
        "scenarios": [scenario.name for scenario in selected_scenarios],
        "rows": rows,
        "summary": {"rows": len(rows), "compatible_rows": sum(1 for row in rows if row["compatible"]), "strategy_counts": counts, "transitions": transitions},
        "limitations": [
            "Machine and SSD figures are synthetic planning inputs, not Apple performance measurements.",
            "Long-context reserve is a conservative stress knob, not a measured Qwen KV-cache allocation.",
            "The matrix validates planner/compatibility behavior only; API contracts are exercised by `outerram simulate`.",
            "Physical Metal, unified-memory, swap, thermal and SSD behavior still require a real Mac.",
        ],
    }


def run_virtual_qualification(*, profile_name: str = M5_16GB.name, model_name: str = QWEN38_27B_3BIT_TEXT.name, strategy: Strategy | None = None, reserve_gib: float | None = None, failure: str | None = None) -> dict[str, Any]:
    profile = PROFILES[profile_name]
    model_profile = MODELS[model_name]
    machine = profile.machine
    model = model_profile.model
    plan = plan_runtime(machine, model, reserve_gib=reserve_gib, force=strategy)
    compatibility = assess_compatibility(machine, model, plan)
    spec = build_launch_spec(plan, model=model.local_path or model.model, host="127.0.0.1", port=8080)
    virtual_runtime = _VirtualRuntime(model.model, failure=failure)
    server = ThreadingHTTPServer(("127.0.0.1", 0), virtual_runtime.handler())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])
        api = qualify_server(f"http://127.0.0.1:{port}/v1", prompt="Implement a correct Python LRU cache with tests.", max_tokens=128, timeout=5.0, require_tool_call=True)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)
    runtime_contract = {
        "runtime": plan.runtime,
        "installed": True,
        "reproducible": True,
        "virtual": True,
        "pins": {
            "mlx-lm": {"ref": MLX_LM_REF, "version": MLX_LM_VERSION, "mlx_min": MLX_MIN_VERSION},
            "mlx-flash": {"ref": MLX_FLASH_REF, "version": MLX_FLASH_VERSION},
            "streamlx": {"ref": STREAMLX_REF, "version": STREAMLX_VERSION},
        },
    }
    sensitivity = _sensitivity(machine, model)
    simulation_passed = bool(compatibility.compatible and api.get("qualified"))
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "outerram_version": __version__,
        "qualification_scope": "virtual-hardware+api-contract",
        "simulation_only": True,
        "physical_apple_silicon_validation": False,
        "metal_inference_executed": False,
        "performance_claim_allowed": False,
        "simulation_passed": simulation_passed,
        "profile": {"name": profile.name, "description": profile.description, "machine": machine.to_dict()},
        "model_profile": {"name": model_profile.name, "source_size_gb": model_profile.source_size_gb, "source_note": model_profile.source_note, "model": model.to_dict()},
        "plan": plan.to_dict(),
        "compatibility": compatibility.to_dict(),
        "runtime_contract": runtime_contract,
        "launch_contract": {"argv": list(spec.argv), "shell": spec.shell(), "required_paths": list(spec.required_paths)},
        "api_contract": api,
        "sensitivity": sensitivity,
        "limitations": [
            "No Apple GPU, Metal kernels, unified-memory allocator, macOS swap daemon, thermal controller, or real M5 SSD is present.",
            "TTFT/tokens-per-second from the virtual API exist only to test accounting and gates; they are not hardware benchmarks.",
            "Runtime pin status is a simulated contract assertion; upstream binaries are not executed in this Linux environment.",
            "A physical-Mac qualification remains required before claiming inference or coding-agent performance on M5 hardware.",
        ],
    }
