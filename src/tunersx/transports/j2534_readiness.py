"""Readiness-only J2534 transport stub: enumeration + diagnostics-only open/close smoke."""


def enumerate_devices() -> list[str]:
    return []


def open_close_smoke() -> bool:
    return True


def is_ready() -> bool:
    return True
