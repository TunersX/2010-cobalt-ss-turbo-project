from __future__ import annotations

from collections import Counter


SEVERITY_PENALTY = {"INFO": 1.0, "WARN": 3.0, "MED": 8.0, "HIGH": 18.0}


def compute_engine_health(signals: list[dict], anomalies: list[dict]) -> dict:
    score = 100.0
    sev_counts = Counter(a.get("severity", "INFO") for a in anomalies)
    for sev, cnt in sev_counts.items():
        score -= SEVERITY_PENALTY.get(sev, 2.0) * cnt

    channels = {s.get("channel") for s in signals}
    coverage_bonus = 0.0
    for needed in ["IAT", "KR", "FUEL_PRESSURE_ACTUAL"]:
        if needed in channels:
            coverage_bonus += 1.0
    score += coverage_bonus

    score = max(0.0, min(100.0, round(score, 2)))
    if score >= 85:
        tier = "GOOD"
    elif score >= 65:
        tier = "WATCH"
    else:
        tier = "CRITICAL"

    return {
        "score": score,
        "tier": tier,
        "severity_counts": dict(sorted(sev_counts.items())),
        "method": "prototype_v1_rule_penalty",
    }
