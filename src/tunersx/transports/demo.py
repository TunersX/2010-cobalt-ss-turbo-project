from __future__ import annotations

import json
from pathlib import Path

from tunersx.core.types import Frame


def generate_demo_frames(seconds: int, out_file: Path) -> int:
    frame_count = 0
    base_temp = 35.0
    for t in range(seconds * 10):
        ts = f"{t/10:.1f}"
        iat = int((base_temp + (t % 30) * 0.8) * 2)
        kr = int(0 if t < 20 else min(80, (t - 20) * 2))
        fuel_actual = int(500 + (10 if t % 15 else 80))
        fuel_target = 550
        frames = [
            Frame(timestamp=ts, can_id=0x100, data=[iat & 0xFF, 0, 0, 0, 0, 0, 0, 0]),
            Frame(timestamp=ts, can_id=0x101, data=[kr & 0xFF, 0, 0, 0, 0, 0, 0, 0]),
            Frame(timestamp=ts, can_id=0x102, data=[fuel_actual & 0xFF, fuel_target & 0xFF, 0, 0, 0, 0, 0, 0]),
        ]
        with out_file.open("a", encoding="utf-8") as f:
            for fr in frames:
                f.write(json.dumps(fr.__dict__) + "\n")
                frame_count += 1
    return frame_count
