# J2534 on Windows (TUNERSX)

## Purpose (in this repo)
- Environment readiness checks (device present, driver/DLL loads)
- Diagnostics-only smoke tests (read-only posture)
- Audit logging of all interaction

## Explicit non-goals (here)
- OEM programming
- Flash or calibration writes
- Anything requiring SecurityAccess

## Smoke test concept
- Enumerate installed PassThru devices
- Load vendor DLL (if present)
- Open device, connect ISO15765 (CAN) channel
- Perform a single safe read (if implemented on your platform/tooling)
- Close/cleanup

This repo ships only the scaffold in `tunersx/transports/j2534/`.
