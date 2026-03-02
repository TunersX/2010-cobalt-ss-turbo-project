"""Readiness-only J2534 backend scaffolding.

No write/programming/security access services are exposed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class J2534Device:
    name: str
    dll_path: str


class J2534Backend:
    def __init__(self) -> None:
        self._opened = False
        self._connected = False

    def enumerate(self) -> list[J2534Device]:
        return []

    def open(self, device_name: str) -> bool:
        self._opened = True
        return True

    def connect(self, protocol: str = "CAN", baudrate: int = 500000) -> bool:
        if not self._opened:
            return False
        self._connected = True
        return protocol == "CAN" and baudrate > 0

    def close(self) -> bool:
        self._connected = False
        self._opened = False
        return True


def enumerate_devices() -> list[str]:
    return [d.name for d in J2534Backend().enumerate()]


def open_close_smoke() -> bool:
    backend = J2534Backend()
    return backend.open("mock") and backend.connect("CAN", 500000) and backend.close()


def is_ready() -> bool:
    return open_close_smoke()
