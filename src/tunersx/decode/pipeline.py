from __future__ import annotations

import json
from pathlib import Path

from tunersx.core.config import DecodeConfig


def decode_frames_to_signals(
    frames_file: Path,
    signals_file: Path,
    dbc_map: dict,
    config: DecodeConfig,
) -> int:
    count = 0
    with frames_file.open("r", encoding="utf-8") as src, signals_file.open("w", encoding="utf-8") as dst:
        for idx, line in enumerate(src):
            frame = json.loads(line)
            key = hex(frame["can_id"])
            defs = dbc_map.get(key, [])
            for sig in defs:
                raw = frame["data"][sig["byte"]]
                value = raw * sig["scale"] + sig.get("offset", 0.0)
                out = {
                    "timestamp": frame["timestamp"],
                    "channel": sig["channel"],
                    "value": value,
                    "unit": sig.get("unit", ""),
                    "source": "DBC",
                    "confidence": config.dbc_confidence,
                    "frame_index": idx,
                }
                dst.write(json.dumps(out) + "\n")
                count += 1
    return count
