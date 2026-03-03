from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from tunersx.audit.integrity import sha256_file


def _hash_map(files: list[Path], root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for fp in sorted(files, key=lambda p: str(p.relative_to(root))):
        out[str(fp.relative_to(root))] = sha256_file(fp)
    return out


def pack_calibration(input_file: Path, out_dir: Path, metadata: dict[str, Any]) -> Path:
    cap_dir = out_dir
    cap_dir.mkdir(parents=True, exist_ok=True)
    payload_dir = cap_dir / "payload"
    payload_dir.mkdir(exist_ok=True)
    payload_path = payload_dir / input_file.name
    shutil.copy2(input_file, payload_path)

    hashes = _hash_map([payload_path], cap_dir)
    manifest = {
        "cap_schema_version": "1.0",
        "metadata": metadata,
        "files": [{"path": k, "sha256": v} for k, v in hashes.items()],
    }
    (cap_dir / "cap_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (cap_dir / "cap_hashes.json").write_text(json.dumps(hashes, indent=2, sort_keys=True), encoding="utf-8")
    return cap_dir


def verify_calibration(cap_dir: Path) -> tuple[bool, dict[str, Any]]:
    errors: list[str] = []
    manifest_path = cap_dir / "cap_manifest.json"
    hashes_path = cap_dir / "cap_hashes.json"
    if not manifest_path.exists():
        errors.append("missing:cap_manifest.json")
    if not hashes_path.exists():
        errors.append("missing:cap_hashes.json")
    if errors:
        return False, {"ok": False, "errors": errors}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hashes = json.loads(hashes_path.read_text(encoding="utf-8"))

    if manifest.get("cap_schema_version") != "1.0":
        errors.append("unsupported_cap_schema")

    for rel, expected in hashes.items():
        fp = cap_dir / rel
        if not fp.exists():
            errors.append(f"missing_payload:{rel}")
            continue
        got = sha256_file(fp)
        if got != expected:
            errors.append(f"hash_mismatch:{rel}")

    return not errors, {"ok": not errors, "errors": errors, "file_count": len(hashes)}


def diff_calibrations(cap_a: Path, cap_b: Path) -> dict[str, Any]:
    ok_a, rep_a = verify_calibration(cap_a)
    ok_b, rep_b = verify_calibration(cap_b)
    hashes_a = json.loads((cap_a / "cap_hashes.json").read_text(encoding="utf-8")) if (cap_a / "cap_hashes.json").exists() else {}
    hashes_b = json.loads((cap_b / "cap_hashes.json").read_text(encoding="utf-8")) if (cap_b / "cap_hashes.json").exists() else {}

    keys = sorted(set(hashes_a) | set(hashes_b))
    changed = [k for k in keys if hashes_a.get(k) != hashes_b.get(k)]
    missing_in_a = [k for k in keys if k not in hashes_a]
    missing_in_b = [k for k in keys if k not in hashes_b]

    return {
        "cap_a_ok": ok_a,
        "cap_b_ok": ok_b,
        "cap_a_errors": rep_a.get("errors", []),
        "cap_b_errors": rep_b.get("errors", []),
        "changed": changed,
        "missing_in_a": missing_in_a,
        "missing_in_b": missing_in_b,
    }
