from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RiskClass(str, Enum):
    PASSIVE = "PASSIVE"
    READ_ONLY_DIAG = "READ_ONLY_DIAG"
    ACTIVE = "ACTIVE_*"


class PipelineState(str, Enum):
    BOOT = "BOOT"
    SELF_TEST = "SELF_TEST"
    IDENTIFY_TARGET = "IDENTIFY_TARGET"
    PASSIVE_CAPTURE = "PASSIVE_CAPTURE"
    READ_ONLY_DIAG = "READ_ONLY_DIAG"
    PACK = "PACK"
    COMPLETE = "COMPLETE"
    FAULT_LOCKOUT = "FAULT_LOCKOUT"


@dataclass
class Frame:
    ts: str
    monotonic_s: float
    can_id: int
    data: list[int]
    dlc: int
    bus: str = "hs_can"


@dataclass
class Anomaly:
    id: str
    timestamp_start: str
    timestamp_end: str
    severity: str
    channels: list[str]
    value_summary: dict[str, Any]
    evidence_pointers: list[dict[str, Any]] = field(default_factory=list)
    recommended_next_test: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
