def blocked_event(command_id: str, reason: str) -> dict:
    return {"event": "BLOCKED", "command_id": command_id, "reason": reason}
