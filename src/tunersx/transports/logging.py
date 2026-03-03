from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field


@dataclass
class BusStats:
    frame_count: int = 0
    id_histogram: Counter = field(default_factory=Counter)
    top_talkers: list[tuple[str, int]] = field(default_factory=list)


class CANLogFramework:
    """In-memory CAN logging framework with deterministic stats extraction."""

    def __init__(self) -> None:
        self._bus_frames: dict[str, list[dict]] = defaultdict(list)

    def ingest(self, frame: dict) -> None:
        bus = frame.get("bus", "hs_can")
        self._bus_frames[bus].append(frame)

    def summary(self, seconds: int, bitrate: int = 500000) -> dict:
        out_buses: dict[str, dict] = {}
        id_hist_global = Counter()
        for bus, frames in sorted(self._bus_frames.items()):
            hist = Counter(hex(f["can_id"]) for f in frames)
            id_hist_global.update(hist)
            out_buses[bus] = {
                "frame_count": len(frames),
                "msg_rate_hz": round(len(frames) / max(seconds, 1), 3),
                "bitrate": bitrate,
                "top_talkers": sorted(hist.items(), key=lambda x: (-x[1], x[0]))[:10],
            }
        return {
            "buses": out_buses,
            "id_histogram": dict(sorted(id_hist_global.items())),
            "top_talkers": sorted(id_hist_global.items(), key=lambda x: (-x[1], x[0]))[:10],
            "drop_count": 0,
        }
