from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tunersx.packaging.canonical_json import canonical_dumps


def stable_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding='utf-8')


def stable_bundle_files(bundle_dir: Path) -> list[Path]:
    return sorted([p for p in bundle_dir.iterdir() if p.is_file()], key=lambda p: p.name)


def environment_fingerprint(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    base = {"json_canonical": True, "format": "sorted-keys"}
    if extra:
        base.update(extra)
    return base
