from __future__ import annotations

import json
from pathlib import Path

from tunersx.core.config import AnomalyConfig


def detect_anomalies(signals_file: Path, anomalies_file: Path, config: AnomalyConfig) -> tuple[int, list[dict]]:
    signals = [json.loads(line) for line in signals_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    grouped: dict[str, list[dict]] = {}
    for s in signals:
        grouped.setdefault(s["channel"], []).append(s)

    out: list[dict] = []

    iat = grouped.get("IAT", [])
    if iat:
        baseline = min(v["value"] for v in iat)
        hot = [x for x in iat if x["value"] > baseline + config.iat_delta_c]
        if len(hot) >= config.iat_min_samples:
            out.append(
                {
                    "id": "ANOM-IAT-001",
                    "timestamp_start": hot[0]["timestamp"],
                    "timestamp_end": hot[-1]["timestamp"],
                    "severity": "MED",
                    "channels": ["IAT"],
                    "value_summary": {"baseline": baseline, "max": max(x["value"] for x in hot)},
                    "evidence_pointers": [hot[0]["evidence_pointer"], hot[-1]["evidence_pointer"]],
                    "recommended_next_test": "Heat-soak cooldown pull and re-check intercooler efficiency",
                }
            )

    kr = grouped.get("KR", [])
    high_kr = [x for x in kr if x["value"] > config.kr_threshold_deg]
    if len(high_kr) >= config.kr_min_samples:
        out.append(
            {
                "id": "ANOM-KR-001",
                "timestamp_start": high_kr[0]["timestamp"],
                "timestamp_end": high_kr[-1]["timestamp"],
                "severity": "HIGH",
                "channels": ["KR"],
                "value_summary": {"peak": max(x["value"] for x in high_kr), "density": round(len(high_kr) / max(len(kr), 1), 4)},
                "evidence_pointers": [high_kr[0]["evidence_pointer"], high_kr[-1]["evidence_pointer"]],
                "recommended_next_test": "STOP_LOGGING_AND_INSPECT",
            }
        )

    ferr = grouped.get("FUEL_PRESSURE_ERROR_PCT", [])
    if ferr and max(abs(x["value"]) for x in ferr) > config.fuel_pressure_deviation_pct:
        mx = max(ferr, key=lambda x: abs(x["value"]))
        out.append(
            {
                "id": "ANOM-FUEL-001",
                "timestamp_start": mx["timestamp"],
                "timestamp_end": mx["timestamp"],
                "severity": "MED",
                "channels": ["FUEL_PRESSURE_ERROR_PCT"],
                "value_summary": {"max_abs_error_pct": abs(mx["value"])},
                "evidence_pointers": [mx["evidence_pointer"]],
                "recommended_next_test": "Run rail pressure hold test",
            }
        )

    out = sorted(out, key=lambda x: (x["timestamp_start"], x["id"]))
    with anomalies_file.open("w", encoding="utf-8") as f:
        for row in out:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    return len(out), out
