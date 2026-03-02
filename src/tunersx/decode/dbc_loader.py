from __future__ import annotations

import json
from pathlib import Path


DEFAULT_DBC_MAP = {
    "0x100": [{"channel": "IAT", "byte": 0, "scale": 0.5, "offset": 0.0, "unit": "degC"}],
    "0x101": [{"channel": "KR", "byte": 0, "scale": 0.1, "offset": 0.0, "unit": "deg"}],
    "0x102": [
        {"channel": "FUEL_PRESSURE_ACTUAL", "byte": 0, "scale": 1.0, "offset": 0.0, "unit": "kPa"},
        {"channel": "FUEL_PRESSURE_TARGET", "byte": 1, "scale": 1.0, "offset": 0.0, "unit": "kPa"},
    ],
}


def load_dbc_map(dbc_file: str | None) -> tuple[dict, str]:
    if dbc_file is None:
        return DEFAULT_DBC_MAP, "builtin-demo-1.1"
    merged = {}
    versions = []
    for piece in dbc_file.split(","):
        path = Path(piece.strip())
        if not path.exists():
            raise FileNotFoundError(f"DBC file not found: {piece}")
        merged.update(json.loads(path.read_text(encoding="utf-8")))
        versions.append(path.name)
    return merged, "+".join(versions)
