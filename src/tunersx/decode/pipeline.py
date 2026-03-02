from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from tunersx.core.config import DecodeConfig


def decode_frames_to_signals(frames_file: Path, signals_file: Path, dbc_map: dict, config: DecodeConfig, labels_file: Path | None = None) -> dict:
    labels = {}
    if labels_file and labels_file.exists():
        labels = json.loads(labels_file.read_text(encoding="utf-8"))

    decoded = 0
    total = 0
    unknown = Counter()
    derived_rows = []
    fp_actual = []
    fp_target = []

    with frames_file.open("r", encoding="utf-8") as src, signals_file.open("w", encoding="utf-8") as dst:
        for idx, line in enumerate(src, start=1):
            frame = json.loads(line)
            total += 1
            key = hex(frame["can_id"])
            defs = dbc_map.get(key, [])
            if not defs:
                unknown[(key, frame.get("dlc", len(frame.get("data", []))))] += 1
                continue
            for sig in defs:
                raw = frame["data"][sig["byte"]]
                value = raw * sig["scale"] + sig.get("offset", 0.0)
                row = {
                    "timestamp": frame["ts"],
                    "channel": labels.get(sig["channel"], sig["channel"]),
                    "value": round(value, 4),
                    "unit": sig.get("unit", ""),
                    "scale": sig.get("scale", 1.0),
                    "offset": sig.get("offset", 0.0),
                    "source": "DBC",
                    "confidence": config.dbc_confidence,
                    "evidence_pointer": {"file": "frames.jsonl", "line": idx, "id": key, "timestamp": frame["ts"]},
                }
                dst.write(json.dumps(row, sort_keys=True) + "\n")
                decoded += 1
                if row["channel"] == "FUEL_PRESSURE_ACTUAL":
                    fp_actual.append((row["timestamp"], row["value"], idx))
                if row["channel"] == "FUEL_PRESSURE_TARGET":
                    fp_target.append((row["timestamp"], row["value"], idx))

        for (ts, av, li), (_, tv, _) in zip(fp_actual, fp_target):
            if tv <= 0:
                continue
            err = ((av - tv) / tv) * 100.0
            derived_rows.append(
                {
                    "timestamp": ts,
                    "channel": "FUEL_PRESSURE_ERROR_PCT",
                    "value": round(err, 4),
                    "unit": "%",
                    "source": "DERIVED",
                    "confidence": config.derived_confidence,
                    "formula_id": "DER-BOOST-001",
                    "dependencies": ["FUEL_PRESSURE_ACTUAL", "FUEL_PRESSURE_TARGET"],
                    "evidence_pointer": {"file": "signals.jsonl", "timestamp": ts},
                }
            )

        for row in derived_rows:
            dst.write(json.dumps(row, sort_keys=True) + "\n")

    return {
        "decoded_signals": decoded + len(derived_rows),
        "decoded_frames": total - sum(unknown.values()),
        "total_frames": total,
        "decode_coverage_pct": round(((total - sum(unknown.values())) / total * 100.0) if total else 0.0, 3),
        "unknown": unknown,
    }


def write_unknown_frames_csv(path: Path, unknown_counter: Counter, total_duration_s: float) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "dlc", "rate_hz", "entropy", "changed_bytes_mask", "correlation_candidates"])
        for (fid, dlc), count in sorted(unknown_counter.items()):
            w.writerow([fid, dlc, round(count / max(total_duration_s, 1), 3), 0.0, "0x00", "[]"])
