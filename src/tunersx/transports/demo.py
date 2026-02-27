from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from tunersx.core.types import Frame


def generate_demo_frames(seconds: int, out_file: Path, bus: str = "hs_can") -> dict:
    frame_count = 0
    id_hist = Counter()
    monotonic = 0.0
    with out_file.open("w", encoding="utf-8") as f:
        for t in range(seconds * 10):
            ts = f"{t/10:.3f}"
            iat = int((30.0 + (t % 40) * 0.75) * 2)
            kr = int(0 if t < 20 else min(100, (t - 20) * 3))
            fuel_actual = int(550 + (20 if t % 17 else 90))
            fuel_target = 580
            frames = [
                Frame(ts=ts, monotonic_s=monotonic, can_id=0x100, dlc=8, data=[iat & 0xFF, 0, 0, 0, 0, 0, 0, 0], bus=bus),
                Frame(ts=ts, monotonic_s=monotonic, can_id=0x101, dlc=8, data=[kr & 0xFF, 0, 0, 0, 0, 0, 0, 0], bus=bus),
                Frame(ts=ts, monotonic_s=monotonic, can_id=0x102, dlc=8, data=[fuel_actual & 0xFF, fuel_target & 0xFF, 0, 0, 0, 0, 0, 0], bus=bus),
            ]
            for fr in frames:
                f.write(json.dumps(fr.__dict__, sort_keys=True) + "\n")
                id_hist[hex(fr.can_id)] += 1
                frame_count += 1
            monotonic += 0.1
    duration = max(seconds, 1)
    return {
        "buses": {bus: {"frame_count": frame_count, "msg_rate_hz": round(frame_count / duration, 3), "bitrate": 500000}},
        "id_histogram": dict(sorted(id_hist.items())),
        "top_talkers": sorted(id_hist.items(), key=lambda x: (-x[1], x[0]))[:10],
        "drop_count": 0,
    }
