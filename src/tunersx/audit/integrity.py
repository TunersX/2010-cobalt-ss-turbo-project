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


def validate_audit_chain(audit_path: Path) -> tuple[bool, str]:
    prev = "0" * 64
    for idx, line in enumerate(audit_path.read_text(encoding="utf-8").splitlines(), start=1):
        entry = json.loads(line)
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

    hashes_doc = json.loads((bundle_dir / "hashes.json").read_text(encoding="utf-8"))
    for name, meta in hashes_doc.items():
        p = bundle_dir / name
        if not p.exists():
            errors.append(f"missing_hashed_file:{name}")
            continue
        if p.stat().st_size != meta["size"]:
            errors.append(f"size_mismatch:{name}")
        if sha256_file(p) != meta["sha256"]:
            errors.append(f"hash_mismatch:{name}")

    audit_ok, audit_msg = validate_audit_chain(bundle_dir / "audit.jsonl")
    if not audit_ok:
        errors.append(audit_msg)

    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    schema = manifest.get("software", {}).get("bundle_schema_version")
    if schema not in {"1.0", "1.1"}:
        errors.append(f"unsupported_schema:{schema}")

    return not errors, {"ok": not errors, "errors": errors, "schema": schema, "audit": audit_msg}
