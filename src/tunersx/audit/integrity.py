from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tunersx.core.types import utc_now


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_jsonable(data: dict[str, Any]) -> str:
    wire = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(wire).hexdigest()


class AuditLogger:
    def __init__(self, audit_path: Path):
        self.audit_path = audit_path
        self.prev_hash = "0" * 64
        if audit_path.exists():
            for line in audit_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                obj = json.loads(line)
                self.prev_hash = obj["entry_hash"]

    def log(self, event_type: str, payload: dict[str, Any]) -> None:
        entry = {
            "timestamp": utc_now(),
            "event_type": event_type,
            "payload": payload,
            "prev_hash": self.prev_hash,
        }
        entry_hash = hash_jsonable(entry)
        entry["entry_hash"] = entry_hash
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")
        self.prev_hash = entry_hash


def validate_audit_chain(audit_path: Path) -> tuple[bool, str]:
    prev = "0" * 64
    for idx, line in enumerate(audit_path.read_text(encoding="utf-8").splitlines(), start=1):
        entry = json.loads(line)
        actual_prev = entry.get("prev_hash")
        if actual_prev != prev:
            return False, f"audit chain mismatch at line {idx}"
        check = dict(entry)
        stored = check.pop("entry_hash", "")
        expect = hash_jsonable(check)
        if stored != expect:
            return False, f"audit entry hash mismatch at line {idx}"
        prev = stored
    return True, "ok"


def build_hashes(bundle_dir: Path, file_names: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in file_names:
        path = bundle_dir / name
        hashes[name] = sha256_file(path)
    return hashes


def write_manifest(
    bundle_dir: Path,
    file_hashes: dict[str, str],
    schema_version: str,
    registry_version: str,
    dbc_version: str,
    policy_mode: str,
) -> None:
    manifest = {
        "generated_at": utc_now(),
        "schema_version": schema_version,
        "registry_version": registry_version,
        "dbc_version": dbc_version,
        "policy_mode": policy_mode,
        "files": [{"name": n, "sha256": h} for n, h in sorted(file_hashes.items())],
    }
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def verify_bundle(bundle_dir: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    required = ["manifest.json", "frames.jsonl", "signals.jsonl", "anomalies.jsonl", "audit.jsonl", "hashes.json"]
    for name in required:
        if not (bundle_dir / name).exists():
            errors.append(f"missing required file {name}")
    if errors:
        return False, errors

    hash_doc = json.loads((bundle_dir / "hashes.json").read_text(encoding="utf-8"))
    for name, old_hash in hash_doc.items():
        new_hash = sha256_file(bundle_dir / name)
        if new_hash != old_hash:
            errors.append(f"hash mismatch for {name}")

    ok, msg = validate_audit_chain(bundle_dir / "audit.jsonl")
    if not ok:
        errors.append(msg)

    return not errors, errors
