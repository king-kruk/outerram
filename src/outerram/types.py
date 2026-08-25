from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class Strategy(str, Enum):
    RESIDENT = "resident"
    DENSE_STREAM = "dense-stream"
    MOE_STREAM = "moe-stream"


class ModelSource(str, Enum):
    LOCAL = "local"
    HUGGINGFACE = "huggingface"


class CheckpointKind(str, Enum):
    SAFETENSORS = "safetensors"
    GGUF = "gguf"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class MachineInfo:
    system: str
    machine: str
    total_memory_gib: float
    apple_silicon: bool
    free_disk_gib: float | None = None
    python_version: str | None = None
    os_version: str | None = None
    chip: str | None = None
    swap_used_gib: float | None = None
    memory_free_percent: float | None = None
    power_source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelInfo:
    model: str
    local_path: str | None
    architecture: str | None
    model_type: str | None
    weight_size_gib: float | None
    is_moe: bool
    num_experts: int | None
    top_k: int | None
    quant_bits: int | None
    source: ModelSource = ModelSource.HUGGINGFACE
    checkpoint_kind: CheckpointKind = CheckpointKind.UNKNOWN
    weight_file_count: int = 0
    quantized: bool = False
    revision: str | None = None
    weight_files: tuple[str, ...] = ()
    origin: str | None = None
    checkpoint_complete: bool = True
    missing_weight_files: tuple[str, ...] = ()
    declared_license: str | None = None
    license_name: str | None = None
    license_link: str | None = None
    base_models: tuple[str, ...] = ()
    license_metadata_source: str | None = None
    legal_clearance: bool = False
    legal_note: str = "License metadata is descriptive evidence only and is not legal clearance for use or redistribution."

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source"] = self.source.value
        data["checkpoint_kind"] = self.checkpoint_kind.value
        return data


@dataclass(frozen=True)
class RuntimePlan:
    strategy: Strategy
    runtime: str
    total_memory_gib: float
    reserved_memory_gib: float
    resident_budget_gib: float
    weight_size_gib: float | None
    expert_budget_gib: float | None
    reason: str
    warnings: tuple[str, ...] = ()
    confidence: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["strategy"] = self.strategy.value
        return data


@dataclass(frozen=True)
class CompatibilityCheck:
    name: str
    ok: bool
    severity: str
    detail: str
    remediation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompatibilityReport:
    compatible: bool
    checks: tuple[CompatibilityCheck, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "compatible": self.compatible,
            "checks": [check.to_dict() for check in self.checks],
        }
