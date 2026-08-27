from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Iterable

from huggingface_hub import HfApi, hf_hub_download, snapshot_download

from .types import CheckpointKind, ModelInfo, ModelSource

_GIB = 1024 ** 3
_SOURCE_SIDECAR = ".outerram-source.json"


def _infer_hf_snapshot_revision(path: Path) -> str | None:
    parts = path.parts
    for idx, part in enumerate(parts[:-1]):
        if part == "snapshots":
            candidate = parts[idx + 1]
            if re.fullmatch(r"[0-9a-fA-F]{7,64}", candidate):
                return candidate.lower()
    return None


def _infer_hf_snapshot_origin(path: Path) -> str | None:
    for part in path.parts:
        if not part.startswith("models--"):
            continue
        encoded = part[len("models--"):]
        pieces = encoded.split("--", 1)
        if len(pieces) == 2 and all(pieces):
            return f"{pieces[0]}/{pieces[1]}"
    return None


def _safe_weight_path(root: Path, name: str) -> Path | None:
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        return None
    try:
        candidate = (root / name).resolve()
        candidate.relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    return candidate


def _text_cfg(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("text_config") if isinstance(config.get("text_config"), dict) else config


def _quant_bits(config: dict[str, Any], model_name: str) -> int | None:
    quant = config.get("quantization") or config.get("quantization_config") or {}
    if isinstance(quant, dict):
        for key in ("bits", "nbits", "weight_bits"):
            value = quant.get(key)
            if isinstance(value, int):
                return value
    m = re.search(r"(?:^|[-_])(2|3|4|5|6|8)bit(?:$|[-_])", model_name, flags=re.I)
    return int(m.group(1)) if m else None


def _checkpoint_kind(names: Iterable[str]) -> tuple[CheckpointKind, int]:
    names = list(names)
    safes = [name for name in names if name.endswith(".safetensors")]
    ggufs = [name for name in names if name.endswith(".gguf")]
    if safes and ggufs:
        return CheckpointKind.MIXED, len(safes) + len(ggufs)
    if safes:
        return CheckpointKind.SAFETENSORS, len(safes)
    if ggufs:
        return CheckpointKind.GGUF, len(ggufs)
    return CheckpointKind.UNKNOWN, 0


def _card_data_dict(card_data: Any) -> dict[str, Any]:
    if card_data is None:
        return {}
    if isinstance(card_data, dict):
        return dict(card_data)
    to_dict = getattr(card_data, "to_dict", None)
    if callable(to_dict):
        try:
            value = to_dict()
            if isinstance(value, dict):
                return value
        except Exception:
            pass
    out: dict[str, Any] = {}
    for key in ("license", "license_name", "license_link", "base_model"):
        value = getattr(card_data, key, None)
        if value is not None:
            out[key] = value
    return out


def _text_or_none(value: Any) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return None


def _base_models(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        value = value.strip()
        return (value,) if value else ()
    if isinstance(value, (list, tuple, set)):
        items = []
        for item in value:
            if isinstance(item, str) and item.strip():
                items.append(item.strip())
            elif isinstance(item, dict):
                candidate = item.get("name") or item.get("repo_id") or item.get("model_id")
                if isinstance(candidate, str) and candidate.strip():
                    items.append(candidate.strip())
        return tuple(dict.fromkeys(items))
    if isinstance(value, dict):
        candidate = value.get("name") or value.get("repo_id") or value.get("model_id")
        if isinstance(candidate, str) and candidate.strip():
            return (candidate.strip(),)
    return ()


def _hf_license_metadata(info: Any) -> dict[str, Any]:
    card = _card_data_dict(getattr(info, "card_data", None))
    if not card:
        return {
            "declared_license": None,
            "license_name": None,
            "license_link": None,
            "base_models": (),
            "license_metadata_source": None,
        }
    return {
        "declared_license": _text_or_none(card.get("license")),
        "license_name": _text_or_none(card.get("license_name")),
        "license_link": _text_or_none(card.get("license_link")),
        "base_models": _base_models(card.get("base_model")),
        "license_metadata_source": "huggingface-model-card",
    }


def _config_to_info(
    model: str,
    local_path: str | None,
    config: dict[str, Any],
    size: int | None,
    *,
    source: ModelSource,
    checkpoint_kind: CheckpointKind,
    weight_file_count: int,
    revision: str | None = None,
    weight_files: Iterable[str] = (),
    origin: str | None = None,
    checkpoint_complete: bool = True,
    missing_weight_files: Iterable[str] = (),
    declared_license: str | None = None,
    license_name: str | None = None,
    license_link: str | None = None,
    base_models: Iterable[str] = (),
    license_metadata_source: str | None = None,
) -> ModelInfo:
    text = _text_cfg(config)
    archs = config.get("architectures") or text.get("architectures") or []
    arch = archs[0] if archs else None
    model_type = text.get("model_type") or config.get("model_type")
    num_experts = text.get("num_experts") or text.get("num_local_experts") or config.get("num_experts") or config.get("num_local_experts")
    top_k = text.get("num_experts_per_tok") or text.get("num_experts_per_token") or config.get("num_experts_per_tok") or config.get("num_experts_per_token")
    name_signal = " ".join(filter(None, [arch, model_type, model])).lower()
    is_moe = bool((isinstance(num_experts, int) and num_experts > 1) or "moe" in name_signal or "switch" in name_signal)
    bits = _quant_bits(config, model)
    return ModelInfo(
        model=model,
        local_path=local_path,
        architecture=arch,
        model_type=model_type,
        weight_size_gib=round(size / _GIB, 3) if size is not None else None,
        is_moe=is_moe,
        num_experts=int(num_experts) if isinstance(num_experts, int) else None,
        top_k=int(top_k) if isinstance(top_k, int) else None,
        quant_bits=bits,
        source=source,
        checkpoint_kind=checkpoint_kind,
        weight_file_count=weight_file_count,
        quantized=bits is not None,
        revision=revision,
        weight_files=tuple(weight_files),
        origin=origin,
        checkpoint_complete=checkpoint_complete,
        missing_weight_files=tuple(missing_weight_files),
        declared_license=declared_license,
        license_name=license_name,
        license_link=license_link,
        base_models=tuple(base_models),
        license_metadata_source=license_metadata_source,
        legal_clearance=False,
    )


def _local_selected_weight_size(p: Path, *, expected_files: Iterable[str] = ()) -> tuple[int | None, list[str], list[str], bool]:
    expected = [str(name) for name in expected_files if str(name)]
    if expected:
        resolved = [_safe_weight_path(p, name) for name in expected]
        unsafe = [name for name, path in zip(expected, resolved) if path is None]
        if unsafe:
            return None, expected, [f"{name} (unsafe path)" for name in unsafe], False
        paths = [path for path in resolved if path is not None]
        missing = [name for name, path in zip(expected, paths) if not path.is_file()]
        if missing:
            return None, expected, missing, False
        return sum(path.stat().st_size for path in paths), expected, [], True

    index_path = p / "model.safetensors.index.json"
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
            shards = sorted(set((index.get("weight_map") or {}).values()))
            if shards:
                resolved = [_safe_weight_path(p, shard) for shard in shards]
                unsafe = [shard for shard, path in zip(shards, resolved) if path is None]
                if unsafe:
                    return None, shards, [f"{name} (unsafe path)" for name in unsafe], False
                shard_paths = [path for path in resolved if path is not None]
                missing = [shard for shard, path in zip(shards, shard_paths) if not path.is_file()]
                if missing:
                    return None, shards, missing, False
                return sum(path.stat().st_size for path in shard_paths), shards, [], True
        except (OSError, json.JSONDecodeError, AttributeError):
            return None, [], ["model.safetensors.index.json (unreadable)"], False

    single = p / "model.safetensors"
    if single.exists():
        return single.stat().st_size, [single.name], [], True

    safes = sorted(path for path in p.glob("*.safetensors") if path.is_file())
    standard = [path for path in safes if re.search(r"model-\d{5}-of-\d{5}\.safetensors$", path.name)]
    if standard:
        totals = set()
        numbers = set()
        for path in standard:
            m = re.search(r"model-(\d{5})-of-(\d{5})\.safetensors$", path.name)
            if m:
                numbers.add(int(m.group(1)))
                totals.add(int(m.group(2)))
        if len(totals) == 1:
            total = next(iter(totals))
            expected_names = [f"model-{i:05d}-of-{total:05d}.safetensors" for i in range(1, total + 1)]
            missing = [name for name in expected_names if not (p / name).is_file()]
            if missing:
                return None, expected_names, missing, False
            return sum((p / name).stat().st_size for name in expected_names), expected_names, [], True
        return None, [path.name for path in standard], ["inconsistent shard totals"], False

    if len(safes) == 1:
        return safes[0].stat().st_size, [safes[0].name], [], True
    if len(safes) > 1:
        return None, [path.name for path in safes], [], False

    ggufs = sorted(path for path in p.glob("*.gguf") if path.is_file())
    if len(ggufs) == 1:
        return ggufs[0].stat().st_size, [ggufs[0].name], [], True
    if len(ggufs) > 1:
        return None, [path.name for path in ggufs], [], False
    return None, [], [], False


def download_space(model: ModelInfo, destination: str | Path | None = None) -> tuple[float | None, float | None]:
    if model.source != ModelSource.HUGGINGFACE or model.weight_size_gib is None:
        return None, None
    target = Path(destination).expanduser().resolve() if destination else Path.home()
    if destination and not target.exists():
        target.mkdir(parents=True, exist_ok=True)
    try:
        free = shutil.disk_usage(target).free / _GIB
    except OSError:
        return None, max(2.0, model.weight_size_gib * 1.15)
    needed = max(2.0, model.weight_size_gib * 1.15)
    return round(free, 2), round(needed, 2)


def inspect_local_model(path: str | Path) -> ModelInfo:
    p = Path(path).expanduser().resolve()
    cfg = p / "config.json"
    if not cfg.exists():
        raise FileNotFoundError(f"Missing config.json in {p}")
    config = json.loads(cfg.read_text(encoding="utf-8"))
    revision = _infer_hf_snapshot_revision(p)
    origin = _infer_hf_snapshot_origin(p)
    expected_files: list[str] = []
    declared_license = None
    license_name = None
    license_link = None
    base_models: tuple[str, ...] = ()
    license_metadata_source = None
    sidecar = p / _SOURCE_SIDECAR
    if sidecar.exists():
        try:
            source_meta = json.loads(sidecar.read_text(encoding="utf-8"))
            if isinstance(source_meta, dict):
                sidecar_revision = source_meta.get("revision")
                sidecar_origin = source_meta.get("repo_id")
                sidecar_weights = source_meta.get("weight_files")
                if isinstance(sidecar_revision, str) and sidecar_revision:
                    revision = sidecar_revision
                if isinstance(sidecar_origin, str) and sidecar_origin:
                    origin = sidecar_origin
                if isinstance(sidecar_weights, list) and all(isinstance(x, str) for x in sidecar_weights):
                    expected_files = list(sidecar_weights)
                declared_license = _text_or_none(source_meta.get("declared_license"))
                license_name = _text_or_none(source_meta.get("license_name"))
                license_link = _text_or_none(source_meta.get("license_link"))
                base_models = _base_models(source_meta.get("base_models"))
                if any((declared_license, license_name, license_link, base_models)):
                    license_metadata_source = _text_or_none(source_meta.get("license_metadata_source")) or "outerram-source-sidecar"
        except (OSError, json.JSONDecodeError):
            pass
    files = [f for f in p.iterdir() if f.is_file() and f.name.endswith((".safetensors", ".gguf"))]
    size, selected, missing, complete = _local_selected_weight_size(p, expected_files=expected_files)
    kind, _ = _checkpoint_kind([f.name for f in files] + selected)
    count = len(selected)
    return _config_to_info(
        str(p), str(p), config, size, source=ModelSource.LOCAL,
        checkpoint_kind=kind, weight_file_count=count, revision=revision,
        weight_files=selected, origin=origin, checkpoint_complete=complete,
        missing_weight_files=missing, declared_license=declared_license,
        license_name=license_name, license_link=license_link, base_models=base_models,
        license_metadata_source=license_metadata_source,
    )


def _hf_selected_weight_size(model_id: str, siblings: list[Any], *, revision: str | None = None) -> tuple[int | None, list[str]]:
    sizes = {s.rfilename: int(s.size) for s in siblings if getattr(s, "size", None)}
    names = [s.rfilename for s in siblings]
    if "model.safetensors.index.json" in names:
        try:
            index_path = hf_hub_download(repo_id=model_id, filename="model.safetensors.index.json", revision=revision)
            index = json.loads(Path(index_path).read_text(encoding="utf-8"))
            shards = sorted(set((index.get("weight_map") or {}).values()))
            if shards and all(shard in sizes for shard in shards):
                return sum(sizes[shard] for shard in shards), shards
        except Exception:
            pass
    if "model.safetensors" in sizes:
        return sizes["model.safetensors"], ["model.safetensors"]
    safe_names = [n for n in names if n.endswith(".safetensors")]
    standard_shards = [n for n in safe_names if re.search(r"model-\d{5}-of-\d{5}\.safetensors$", n)]
    if standard_shards and all(n in sizes for n in standard_shards):
        return sum(sizes[n] for n in standard_shards), standard_shards
    ggufs = [n for n in names if n.endswith(".gguf")]
    if len(ggufs) == 1 and ggufs[0] in sizes:
        return sizes[ggufs[0]], ggufs
    return None, safe_names or ggufs


def inspect_hf_model(model_id: str) -> ModelInfo:
    info = HfApi().model_info(model_id, files_metadata=True)
    revision = getattr(info, "sha", None)
    cfg_path = hf_hub_download(repo_id=model_id, filename="config.json", revision=revision)
    config = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
    siblings = list(info.siblings or [])
    all_weight_names = [s.rfilename for s in siblings if s.rfilename.endswith((".safetensors", ".gguf"))]
    kind, _ = _checkpoint_kind(all_weight_names)
    size, selected = _hf_selected_weight_size(model_id, siblings, revision=revision)
    license_meta = _hf_license_metadata(info)
    return _config_to_info(
        model_id, None, config, size, source=ModelSource.HUGGINGFACE,
        checkpoint_kind=kind, weight_file_count=len(selected), revision=revision,
        weight_files=selected, origin=model_id,
        checkpoint_complete=bool(selected and size is not None),
        **license_meta,
    )


def inspect_model(model: str) -> ModelInfo:
    p = Path(model).expanduser()
    if p.exists():
        return inspect_local_model(p)
    return inspect_hf_model(model)


def fetch_model(
    model_id: str,
    destination: str | Path | None = None,
    *,
    revision: str | None = None,
    weight_files: Iterable[str] = (),
    full_snapshot: bool = False,
    declared_license: str | None = None,
    license_name: str | None = None,
    license_link: str | None = None,
    base_models: Iterable[str] = (),
    license_metadata_source: str | None = None,
) -> Path:
    if Path(model_id).expanduser().exists():
        return Path(model_id).expanduser().resolve()

    base_models_tuple = tuple(base_models)
    if not any((declared_license, license_name, license_link, base_models_tuple, license_metadata_source)):
        provenance_info = HfApi().model_info(model_id, revision=revision)
        if revision is None:
            revision = getattr(provenance_info, "sha", None)
        provenance = _hf_license_metadata(provenance_info)
        declared_license = provenance["declared_license"]
        license_name = provenance["license_name"]
        license_link = provenance["license_link"]
        base_models_tuple = tuple(provenance["base_models"])
        license_metadata_source = provenance["license_metadata_source"]

    kwargs: dict[str, Any] = {"repo_id": model_id}
    if revision:
        kwargs["revision"] = revision
    if destination is not None:
        dst = Path(destination).expanduser().resolve()
        dst.mkdir(parents=True, exist_ok=True)
        kwargs["local_dir"] = str(dst)
    selected = tuple(weight_files)
    if selected and not full_snapshot:
        metadata_patterns = [
            "config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json",
            "special_tokens_map.json", "added_tokens.json", "vocab.json", "merges.txt",
            "*.model", "*.tiktoken", "tekken.json", "chat_template*.jinja", "*.jinja",
            "model.safetensors.index.json",
        ]
        kwargs["allow_patterns"] = list(selected) + metadata_patterns
    path = snapshot_download(**kwargs)
    resolved = Path(path).resolve()
    metadata = {
        "schema_version": 2,
        "repo_id": model_id,
        "revision": revision,
        "weight_files": list(selected),
        "declared_license": declared_license,
        "license_name": license_name,
        "license_link": license_link,
        "base_models": list(base_models_tuple),
        "license_metadata_source": license_metadata_source,
        "legal_clearance": False,
        "legal_note": "License metadata is descriptive evidence only and is not legal clearance for use or redistribution.",
    }
    (resolved / _SOURCE_SIDECAR).write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return resolved
