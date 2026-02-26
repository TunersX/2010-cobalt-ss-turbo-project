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
    timestamp: str
    can_id: int
    data: list[int]
    bus: str = "can0"


@dataclass
class Signal:
    timestamp: str
    channel: str
    value: float
    unit: str
    source: str
    confidence: float
    frame_id: int


@dataclass
class Anomaly:
    timestamp: str
    channel: str
    severity: str
    description: str
    evidence: dict[str, Any] = field(default_factory=dict)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
