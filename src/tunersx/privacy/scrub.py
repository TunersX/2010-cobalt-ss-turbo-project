from __future__ import annotations

import json
import shutil
from pathlib import Path

from tunersx.privacy.crypto import xor_encrypt
from tunersx.privacy.profiles import PROFILES


def scrub_bundle(bundle: Path, out: Path, profile: str, encrypt_private: bool = False, key: str | None = None) -> Path:
    fields = PROFILES[profile]
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(bundle, out)
    manifest = {"profile": profile, "removed": []}

    for file in ["manifest.json", "signals.jsonl", "anomalies.jsonl", "audit.jsonl", "frames.jsonl"]:
        p = out / file
        if not p.exists():
            continue
        lines = p.read_text(encoding='utf-8').splitlines()
        new_lines = []
        for line in lines:
            if not line.strip():
                continue
            obj = json.loads(line) if file.endswith('jsonl') else json.loads(p.read_text(encoding='utf-8'))
            if isinstance(obj, dict):
                for f in list(obj.keys()):
                    if f in fields:
                        manifest['removed'].append({"file": file, "field": f})
                        obj[f] = "REDACTED"
            new_lines.append(json.dumps(obj, sort_keys=True))
            if not file.endswith('jsonl'):
                break
        p.write_text(("\n".join(new_lines) + ("\n" if file.endswith('jsonl') and new_lines else "")), encoding='utf-8')

    (out / 'scrub_manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding='utf-8')
    if encrypt_private and key:
        raw = (bundle / 'manifest.json').read_bytes()
        (out / 'private_manifest.enc').write_bytes(xor_encrypt(raw, key))
    return out
