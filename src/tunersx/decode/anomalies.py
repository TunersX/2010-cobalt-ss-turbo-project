from __future__ import annotations

import json
from pathlib import Path

from tunersx.core.config import AnomalyConfig


def _sustained(values: list[dict], threshold: float, op: str, min_samples: int) -> bool:
    hits = 0
    for row in values:
        val = row["value"]
        match = val > threshold if op == ">" else val < threshold
        hits = hits + 1 if match else 0
        if hits >= min_samples:
            return True
    return False


def detect_anomalies(signals_file: Path, anomalies_file: Path, config: AnomalyConfig) -> int:
    signals = [json.loads(line) for line in signals_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    grouped: dict[str, list[dict]] = {}
    for i, sig in enumerate(signals):
        sig["line_index"] = i + 1
        grouped.setdefault(sig["channel"], []).append(sig)

    anomalies: list[dict] = []

    timestamps = [float(s["timestamp"]) for s in signals if str(s.get("timestamp", "")).replace(".", "", 1).isdigit()]
    if not timestamps or len(timestamps) < len(signals):
        anomalies.append(
            {
                "timestamp": signals[0]["timestamp"] if signals else "0",
                "channel": "CAPTURE_QUALITY",
                "severity": "WARN",
                "description": "Missing or malformed timestamps detected",
                "evidence": {"signals_line": 1},
            }
        )
    if timestamps:
        duration = max(timestamps) - min(timestamps)
        rate = len(timestamps) / duration if duration > 0 else 0
        if rate < config.min_sample_rate_hz:
            anomalies.append(
                {
                    "timestamp": str(max(timestamps)),
                    "channel": "CAPTURE_QUALITY",
                    "severity": "WARN",
                    "description": f"Low sample rate detected ({rate:.2f}Hz)",
                    "evidence": {"timestamp_range": [min(timestamps), max(timestamps)]},
                }
            )

    iat = grouped.get("IAT", [])
    if iat:
        baseline = min(x["value"] for x in iat)
        if _sustained(iat, baseline + config.iat_delta_c, ">", config.iat_min_samples):
            anomalies.append(
                {
                    "timestamp": iat[-1]["timestamp"],
                    "channel": "IAT",
                    "severity": "MED",
                    "description": f"IAT sustained above baseline + {config.iat_delta_c}C",
                    "evidence": {"signals_line": iat[-1]["line_index"]},
                }
            )

    kr = grouped.get("KR", [])
    if kr and _sustained(kr, config.kr_threshold_deg, ">", config.kr_min_samples):
        anomalies.append(
            {
                "timestamp": kr[-1]["timestamp"],
                "channel": "KR",
                "severity": "HIGH",
                "description": f"Knock retard sustained above {config.kr_threshold_deg} deg",
                "evidence": {"signals_line": kr[-1]["line_index"]},
            }
        )

    actual = grouped.get("FUEL_PRESSURE_ACTUAL", [])
    target = grouped.get("FUEL_PRESSURE_TARGET", [])
    if actual and target:
        for a, t in zip(actual, target):
            if t["value"] <= 0:
                continue
            dev = abs(a["value"] - t["value"]) / t["value"] * 100
            if dev > config.fuel_pressure_deviation_pct:
                anomalies.append(
                    {
                        "timestamp": a["timestamp"],
                        "channel": "FUEL_PRESSURE",
                        "severity": "MED",
                        "description": f"Fuel pressure deviation {dev:.1f}% exceeds {config.fuel_pressure_deviation_pct}%",
                        "evidence": {"signals_line": a["line_index"]},
                    }
                )
                break

    with anomalies_file.open("w", encoding="utf-8") as f:
        for row in anomalies:
            f.write(json.dumps(row) + "\n")

    return len(anomalies)
