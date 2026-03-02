from __future__ import annotations

from tunersx.policy.capabilities import Capability


COMMAND_CAPS = {
    'session.start': {Capability.PASSIVE_CAPTURE},
    'decode': {Capability.PASSIVE_CAPTURE},
    'dashboard.build': {Capability.EXPORT_REPORT},
}


def check_capability(command_id: str, granted: set[Capability]) -> tuple[bool, str]:
    req = COMMAND_CAPS.get(command_id, set())
    missing = sorted([c.value for c in req if c not in granted])
    if missing:
        return False, f"missing capabilities: {','.join(missing)}"
    return True, 'allowed'
