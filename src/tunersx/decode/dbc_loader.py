from __future__ import annotations

import json
import re
from pathlib import Path


DEFAULT_DBC_MAP = {
    "0x100": [{"channel": "IAT", "byte": 0, "scale": 0.5, "offset": 0.0, "unit": "degC"}],
    "0x101": [{"channel": "KR", "byte": 0, "scale": 0.1, "offset": 0.0, "unit": "deg"}],
    "0x102": [
        {"channel": "FUEL_PRESSURE_ACTUAL", "byte": 0, "scale": 1.0, "offset": 0.0, "unit": "kPa"},
        {"channel": "FUEL_PRESSURE_TARGET", "byte": 1, "scale": 1.0, "offset": 0.0, "unit": "kPa"},
    ],
}


_SIG_RE = re.compile(r"^\s*SG_\s+(?P<name>\w+)\s*:\s*(?P<start>\d+)\|(?P<len>\d+)@\d+[+-]\s*\((?P<scale>[-0-9.]+),(?P<offset>[-0-9.]+)\)\s*\[[^\]]*\]\s*\"(?P<unit>[^\"]*)\"")


def _parse_dbc_text(path: Path) -> dict:
    mapping: dict[str, list[dict]] = {}
    current_id: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        l = line.strip()
        if l.startswith("BO_"):
            parts = l.split()
            if len(parts) >= 2 and parts[1].isdigit():
                current_id = hex(int(parts[1]))
                mapping.setdefault(current_id, [])
            continue
        m = _SIG_RE.match(line)
        if m and current_id:
            start = int(m.group("start"))
            bit_len = int(m.group("len"))
            if bit_len != 8:
                continue
            mapping[current_id].append(
                {
                    "channel": m.group("name"),
                    "byte": start // 8,
                    "scale": float(m.group("scale")),
                    "offset": float(m.group("offset")),
                    "unit": m.group("unit"),
                }
            )
    return mapping


def load_dbc_map(dbc_file: str | None) -> tuple[dict, str]:
    if dbc_file is None:
        return DEFAULT_DBC_MAP, "builtin-demo-1.1"
    merged = {}
    versions = []
    for piece in dbc_file.split(","):
        path = Path(piece.strip())
        if not path.exists():
            raise FileNotFoundError(f"DBC file not found: {piece}")
        if path.suffix.lower() == ".dbc":
            merged.update(_parse_dbc_text(path))
        else:
            merged.update(json.loads(path.read_text(encoding="utf-8")))
        versions.append(path.name)
    return merged, "+".join(versions)
