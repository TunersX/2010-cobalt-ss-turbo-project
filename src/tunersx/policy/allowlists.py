from tunersx.policy.enforcer import COMMAND_REGISTRY

def list_allowlisted_commands() -> list[str]:
    return sorted(COMMAND_REGISTRY.keys())
