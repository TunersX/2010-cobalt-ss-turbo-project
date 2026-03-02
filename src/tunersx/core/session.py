from __future__ import annotations

import json
from pathlib import Path

from tunersx.core.types import PipelineState, RiskClass, utc_now


SESSION_FILE = ".tunersx_session.json"


def save_session(bundle_dir: Path, state: PipelineState, risk_class: RiskClass, armed_until: str | None = None) -> None:
    payload = {
        "bundle_dir": str(bundle_dir),
        "state": state.value,
        "risk_class": risk_class.value,
        "armed_until": armed_until,
        "updated_at": utc_now(),
    }
    Path(SESSION_FILE).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_session() -> dict | None:
    p = Path(SESSION_FILE)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def clear_session() -> None:
    p = Path(SESSION_FILE)
    if p.exists():
        p.unlink()
