from __future__ import annotations

import hashlib
from pathlib import Path


def sign_blob(blob: bytes, key: str) -> str:
    return hashlib.sha256(key.encode('utf-8') + blob).hexdigest()


def sign_file(path: Path, key_path: Path) -> dict:
    key = key_path.read_text(encoding='utf-8').strip()
    sig = sign_blob(path.read_bytes(), key)
    return {"algorithm": "HMAC-SHA256", "signature": sig, "key_hint": key_path.name, "target": path.name}


def verify_file_signature(path: Path, signature: dict, key_path: Path | None) -> tuple[bool, str]:
    if not signature:
        return False, "missing"
    if key_path is None:
        return False, "missing_pubkey"
    key = key_path.read_text(encoding='utf-8').strip()
    expect = sign_blob(path.read_bytes(), key)
    if expect == signature.get('signature'):
        return True, 'valid'
    return False, 'invalid'
