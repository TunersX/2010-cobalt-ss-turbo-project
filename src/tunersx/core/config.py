from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DecodeConfig:
    dbc_confidence: float = 0.95
    pid_confidence: float = 0.90
    derived_confidence: float = 0.70


@dataclass
class AnomalyConfig:
    iat_delta_c: float = 20.0
    iat_min_samples: int = 3
    kr_threshold_deg: float = 3.0
    kr_min_samples: int = 2
    fuel_pressure_deviation_pct: float = 10.0
    min_sample_rate_hz: float = 1.0


@dataclass
class AppConfig:
    bundle_schema_version: str = "1.1"
    registry_version: str = "1.1"
    policy_version: str = "1.1"
    vehicle_profile_version: str = "1.0"
    decode: DecodeConfig = field(default_factory=DecodeConfig)
    anomaly: AnomalyConfig = field(default_factory=AnomalyConfig)
