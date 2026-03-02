from __future__ import annotations

from dataclasses import dataclass, field

from tunersx.core.types import PipelineState, RiskClass


@dataclass(frozen=True)
class CommandSpec:
    command_id: str
    risk_class: RiskClass
    required_states: set[PipelineState]
    rule_id: str
    preconditions: tuple[str, ...] = ()


COMMAND_REGISTRY: dict[str, CommandSpec] = {
    "session.start": CommandSpec("session.start", RiskClass.PASSIVE, {PipelineState.BOOT}, "POL-001"),
    "session.stop": CommandSpec("session.stop", RiskClass.PASSIVE, {PipelineState.COMPLETE, PipelineState.PACK}, "POL-002"),
    "trace.verify": CommandSpec("trace.verify", RiskClass.PASSIVE, {PipelineState.COMPLETE, PipelineState.PACK, PipelineState.PASSIVE_CAPTURE}, "POL-003"),
    "decode": CommandSpec("decode", RiskClass.PASSIVE, {PipelineState.PASSIVE_CAPTURE, PipelineState.COMPLETE}, "POL-004"),
    "dashboard.build": CommandSpec("dashboard.build", RiskClass.PASSIVE, {PipelineState.PACK, PipelineState.COMPLETE}, "POL-005"),
    "arm": CommandSpec("arm", RiskClass.PASSIVE, {PipelineState.COMPLETE, PipelineState.PASSIVE_CAPTURE}, "POL-006"),
    "diag.read_pid": CommandSpec("diag.read_pid", RiskClass.READ_ONLY_DIAG, {PipelineState.READ_ONLY_DIAG}, "POL-007", ("armed", "target_identified", "link_stable")),
    "j2534.enumerate": CommandSpec("j2534.enumerate", RiskClass.PASSIVE, {PipelineState.PASSIVE_CAPTURE, PipelineState.COMPLETE}, "POL-008"),
    "j2534.open": CommandSpec("j2534.open", RiskClass.PASSIVE, {PipelineState.PASSIVE_CAPTURE, PipelineState.COMPLETE}, "POL-009"),
    "j2534.connect": CommandSpec("j2534.connect", RiskClass.PASSIVE, {PipelineState.PASSIVE_CAPTURE, PipelineState.COMPLETE}, "POL-010"),
    "j2534.close": CommandSpec("j2534.close", RiskClass.PASSIVE, {PipelineState.PASSIVE_CAPTURE, PipelineState.COMPLETE}, "POL-011"),
    "orchestration.run": CommandSpec("orchestration.run", RiskClass.PASSIVE, {PipelineState.COMPLETE, PipelineState.PACK}, "POL-012"),
    "active.any": CommandSpec("active.any", RiskClass.ACTIVE, {PipelineState.READ_ONLY_DIAG}, "POL-999"),
}


@dataclass
class PolicySnapshot:
    risk_class: RiskClass = RiskClass.PASSIVE
    state: PipelineState = PipelineState.BOOT
    target_identified: bool = False
    link_stable: bool = True
    armed: bool = False
    transitions: list[str] = field(default_factory=list)

    def transition(self, new_state: PipelineState) -> None:
        allowed = {
            PipelineState.BOOT: {PipelineState.SELF_TEST},
            PipelineState.SELF_TEST: {PipelineState.IDENTIFY_TARGET, PipelineState.FAULT_LOCKOUT},
            PipelineState.IDENTIFY_TARGET: {PipelineState.PASSIVE_CAPTURE, PipelineState.READ_ONLY_DIAG, PipelineState.FAULT_LOCKOUT},
            PipelineState.PASSIVE_CAPTURE: {PipelineState.PACK, PipelineState.FAULT_LOCKOUT},
            PipelineState.READ_ONLY_DIAG: {PipelineState.PACK, PipelineState.FAULT_LOCKOUT},
            PipelineState.PACK: {PipelineState.COMPLETE, PipelineState.FAULT_LOCKOUT},
            PipelineState.COMPLETE: {PipelineState.PASSIVE_CAPTURE, PipelineState.READ_ONLY_DIAG, PipelineState.FAULT_LOCKOUT},
            PipelineState.FAULT_LOCKOUT: set(),
        }
        if new_state not in allowed[self.state]:
            self.state = PipelineState.FAULT_LOCKOUT
            self.transitions.append("FAULT_LOCKOUT:invalid_transition")
            raise RuntimeError("invalid state transition")
        self.transitions.append(f"{self.state.value}->{new_state.value}")
        self.state = new_state

    def evaluate(self, command_id: str) -> tuple[bool, str, str]:
        if command_id.startswith("j2534.") and command_id not in {"j2534.enumerate", "j2534.open", "j2534.connect", "j2534.close"}:
            return False, "POL-J2534-BLOCK", "J2534 risky services are blocked by policy"
        spec = COMMAND_REGISTRY.get(command_id)
        if not spec:
            return False, "POL-000", "unknown command"
        if spec.risk_class == RiskClass.ACTIVE or command_id.startswith("active"):
            return False, spec.rule_id, "ACTIVE operations blocked by default"
        if self.state not in spec.required_states:
            return False, spec.rule_id, f"state {self.state.value} not in required states"
        if self.risk_class == RiskClass.PASSIVE and spec.risk_class == RiskClass.READ_ONLY_DIAG:
            return False, spec.rule_id, "READ_ONLY_DIAG requires arming"
        for p in spec.preconditions:
            if p == "armed" and not self.armed:
                return False, spec.rule_id, "arming window not active"
            if p == "target_identified" and not self.target_identified:
                return False, spec.rule_id, "target not identified"
            if p == "link_stable" and not self.link_stable:
                return False, spec.rule_id, "link unstable"
        return True, spec.rule_id, "allowed"
