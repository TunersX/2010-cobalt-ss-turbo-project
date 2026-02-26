from __future__ import annotations

from dataclasses import dataclass, field

from tunersx.core.types import PipelineState, RiskClass


ALLOWED_ACTIONS = {
    RiskClass.PASSIVE: {"capture", "decode", "verify", "dashboard", "package", "session_stop"},
    RiskClass.READ_ONLY_DIAG: {
        "capture",
        "decode",
        "verify",
        "dashboard",
        "package",
        "session_stop",
        "diag_read_pid",
    },
}


@dataclass
class PolicySnapshot:
    risk_class: RiskClass = RiskClass.PASSIVE
    state: PipelineState = PipelineState.BOOT
    transitions: list[str] = field(default_factory=list)

    def transition(self, new_state: PipelineState) -> None:
        allowed = {
            PipelineState.BOOT: {PipelineState.SELF_TEST},
            PipelineState.SELF_TEST: {PipelineState.IDENTIFY_TARGET, PipelineState.FAULT_LOCKOUT},
            PipelineState.IDENTIFY_TARGET: {
                PipelineState.PASSIVE_CAPTURE,
                PipelineState.READ_ONLY_DIAG,
                PipelineState.FAULT_LOCKOUT,
            },
            PipelineState.PASSIVE_CAPTURE: {PipelineState.PACK, PipelineState.FAULT_LOCKOUT},
            PipelineState.READ_ONLY_DIAG: {PipelineState.PACK, PipelineState.FAULT_LOCKOUT},
            PipelineState.PACK: {PipelineState.COMPLETE, PipelineState.FAULT_LOCKOUT},
            PipelineState.COMPLETE: set(),
            PipelineState.FAULT_LOCKOUT: set(),
        }
        if new_state not in allowed[self.state]:
            self.state = PipelineState.FAULT_LOCKOUT
            self.transitions.append(f"{self.state.value}:invalid_transition")
            raise RuntimeError(f"Invalid transition from {self.state} to {new_state}")
        self.transitions.append(f"{self.state.value}->{new_state.value}")
        self.state = new_state

    def authorize(self, action: str) -> tuple[bool, str]:
        if action.startswith("active"):
            return False, "ACTIVE operations are blocked by policy"
        allowed = ALLOWED_ACTIONS.get(self.risk_class, set())
        if action in allowed:
            return True, "allowed"
        return False, f"Action '{action}' is not allowlisted for {self.risk_class.value}"
