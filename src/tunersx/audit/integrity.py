from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from tunersx.core.types import utc_now


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


class AuditLogger:
    def __init__(self, audit_path: Path):
        self.audit_path = audit_path
        self.prev_hash = "0" * 64
        if audit_path.exists():
            for line in audit_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.prev_hash = json.loads(line)["entry_hash"]

    def log(self, event_type: str, actor: str, state: str, command_id: str, result: str, details: dict[str, Any]) -> None:
        entry = {
            "ts": utc_now(),
            "event_type": event_type,
            "actor": actor,
            "state": state,
            "command_id": command_id,
            "result": result,
            "details": details,
            "prev_hash": self.prev_hash,
        }
        entry_hash = hashlib.sha256((self.prev_hash + canonical_json(entry)).encode("utf-8")).hexdigest()
        entry["entry_hash"] = entry_hash
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(canonical_json(entry) + "\n")
        self.prev_hash = entry_hash


def _is_sha256_hex(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _validate_manifest_schema(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest_schema:not_object"]
    required_top = {"generated_at", "software", "policy_snapshot", "transport_config", "capture_stats", "files"}
    missing = sorted(required_top - set(manifest.keys()))
    errors.extend([f"manifest_schema:missing:{k}" for k in missing])

    software = manifest.get("software", {})
    required_sw = {
        "version",
        "bundle_schema_version",
        "registry_version",
        "dbc_version",
        "vehicle_profile_version",
        "git_commit",
        "build_id",
    }
    if not isinstance(software, dict):
        errors.append("manifest_schema:software_not_object")
    else:
        errors.extend([f"manifest_schema:missing_software:{k}" for k in sorted(required_sw - set(software.keys()))])

    files = manifest.get("files", [])
    if not isinstance(files, list):
        errors.append("manifest_schema:files_not_list")
    else:
        for idx, row in enumerate(files, start=1):
            if not isinstance(row, dict):
                errors.append(f"manifest_schema:file_entry_not_object:{idx}")
                continue
            if not isinstance(row.get("name"), str):
                errors.append(f"manifest_schema:file_name_invalid:{idx}")
            if not isinstance(row.get("size"), int) or row.get("size", -1) < 0:
                errors.append(f"manifest_schema:file_size_invalid:{idx}")
            if not _is_sha256_hex(row.get("sha256")):
                errors.append(f"manifest_schema:file_sha256_invalid:{idx}")
    return errors


def _validate_frames_schema(frames_path: Path) -> list[str]:
    errors: list[str] = []
    for idx, line in enumerate(frames_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"frames_schema:invalid_json:{idx}")
            continue
        required = {"ts", "monotonic_s", "can_id", "data", "dlc", "bus"}
        missing = sorted(required - set(obj.keys()))
        errors.extend([f"frames_schema:missing:{idx}:{k}" for k in missing])
        if not isinstance(obj.get("ts"), str):
            errors.append(f"frames_schema:ts_type:{idx}")
        if not isinstance(obj.get("monotonic_s"), (float, int)):
            errors.append(f"frames_schema:monotonic_s_type:{idx}")
        if not isinstance(obj.get("can_id"), int):
            errors.append(f"frames_schema:can_id_type:{idx}")
        data = obj.get("data")
        if not isinstance(data, list) or len(data) != 8:
            errors.append(f"frames_schema:data_shape:{idx}")
        elif any((not isinstance(b, int) or b < 0 or b > 255) for b in data):
            errors.append(f"frames_schema:data_bytes:{idx}")
        if not isinstance(obj.get("dlc"), int):
            errors.append(f"frames_schema:dlc_type:{idx}")
        if not isinstance(obj.get("bus"), str):
            errors.append(f"frames_schema:bus_type:{idx}")
    return errors


def validate_audit_chain(audit_path: Path) -> tuple[bool, str]:
    prev = "0" * 64
    for idx, line in enumerate(audit_path.read_text(encoding="utf-8").splitlines(), start=1):
        entry = json.loads(line)
        required = {"ts", "event_type", "actor", "state", "command_id", "result", "details", "prev_hash", "entry_hash"}
        missing = sorted(required - set(entry.keys()))
        if missing:
            return False, f"audit_schema:missing:{idx}:{','.join(missing)}"
        if not isinstance(entry["details"], dict):
            return False, f"audit_schema:details_not_object:{idx}"
        if not _is_sha256_hex(entry.get("prev_hash")):
            return False, f"audit_schema:prev_hash_invalid:{idx}"
        if not _is_sha256_hex(entry.get("entry_hash")):
            return False, f"audit_schema:entry_hash_invalid:{idx}"
        if entry.get("prev_hash") != prev:
            return False, f"audit chain mismatch line {idx}"
        chk = dict(entry)
        stored = chk.pop("entry_hash", "")
        calc = hashlib.sha256((entry.get("prev_hash", "") + canonical_json(chk)).encode("utf-8")).hexdigest()
        if stored != calc:
            return False, f"audit hash mismatch line {idx}"
        prev = stored
    return True, "ok"


def build_hashes(bundle_dir: Path, file_names: list[str]) -> dict[str, dict[str, Any]]:
    out = {}
    for n in sorted(file_names):
        p = bundle_dir / n
        out[n] = {"size": p.stat().st_size, "sha256": sha256_file(p)}
    return out


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return None


def write_manifest(bundle_dir: Path, file_hashes: dict[str, dict[str, Any]], *, versions: dict[str, str], policy_snapshot: dict[str, Any], capture_stats: dict[str, Any], transport_config: dict[str, Any]) -> None:
    manifest = {
        "generated_at": utc_now(),
        "software": {
            "version": versions.get("app_version"),
            "bundle_schema_version": versions.get("bundle_schema_version"),
            "registry_version": versions.get("registry_version"),
            "dbc_version": versions.get("dbc_version"),
            "vehicle_profile_version": versions.get("vehicle_profile_version"),
            "git_commit": _git_commit(),
            "build_id": os.getenv("TUNERSX_BUILD_ID", "local"),
        },
        "policy_snapshot": policy_snapshot,
        "transport_config": transport_config,
        "capture_stats": capture_stats,
        "files": [{"name": k, **v} for k, v in sorted(file_hashes.items())],
    }
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def verify_bundle(bundle_dir: Path) -> tuple[bool, dict[str, Any]]:
    required = ["manifest.json", "frames.jsonl", "signals.jsonl", "anomalies.jsonl", "audit.jsonl", "hashes.json"]
    errors: list[str] = []
    for name in required:
        if not (bundle_dir / name).exists():
            errors.append(f"missing:{name}")
    if errors:
        return False, {"ok": False, "errors": errors}

    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    errors.extend(_validate_manifest_schema(manifest))

    errors.extend(_validate_frames_schema(bundle_dir / "frames.jsonl"))

    hashes_doc = json.loads((bundle_dir / "hashes.json").read_text(encoding="utf-8"))
    for name, meta in hashes_doc.items():
        p = bundle_dir / name
        if not p.exists():
            errors.append(f"missing_hashed_file:{name}")
            continue
        if not isinstance(meta, dict) or "size" not in meta or "sha256" not in meta:
            errors.append(f"hashes_schema:invalid_entry:{name}")
            continue
        if p.stat().st_size != meta["size"]:
            errors.append(f"size_mismatch:{name}")
        if sha256_file(p) != meta["sha256"]:
            errors.append(f"hash_mismatch:{name}")

    audit_ok, audit_msg = validate_audit_chain(bundle_dir / "audit.jsonl")
    if not audit_ok:
        errors.append(audit_msg)

    schema = manifest.get("software", {}).get("bundle_schema_version")
    if schema not in {"1.0", "1.1"}:
        errors.append(f"unsupported_schema:{schema}")

    return not errors, {"ok": not errors, "errors": errors, "schema": schema, "audit": audit_msg}
