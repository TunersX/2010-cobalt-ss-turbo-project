from __future__ import annotations

import json
from pathlib import Path

from tunersx.core.types import Frame
from tunersx.transports.logging import CANLogFramework


def generate_demo_frames(seconds: int, out_file: Path, bus: str = "hs_can") -> dict:
    framework = CANLogFramework()
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
                row = fr.__dict__
                f.write(json.dumps(row, sort_keys=True) + "\n")
                framework.ingest(row)
            monotonic += 0.1
    return framework.summary(seconds=seconds, bitrate=500000)
