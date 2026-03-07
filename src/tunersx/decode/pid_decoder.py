def decode_mode01(pid: str, raw: bytes) -> dict:
    return {"pid": pid, "raw": raw.hex(), "source": "PID", "confidence": 0.90}
