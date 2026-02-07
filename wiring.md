# Wiring and CANbus notes

This document collects pinouts, wire colours and CANbus identifiers for the LNF engine harness, F35 transmission sensors and common aftermarket integrations (e.g., wideband O₂ controllers, boost gauges, methanol injection).  Always refer to the GM service manual for complete diagrams; these notes highlight modifications and integration points used on this build.

## Engine control module (ECM) connectors

| Connector | Pin | Function                   | Wire colour | Notes |
|----------|-----|----------------------------|-------------|-------|
| X2       | 15  | Fuel pump relay control    | Dark green  | Used to trigger aftermarket fuel pump booster. |
| X3       | 36  | Manifold absolute pressure | Brown/white | Tap here for aftermarket MAP sensor logging. |
| X4       | 8   | CAN H                      | White       | High speed CANbus, 500 kbps. |
| X4       | 9   | CAN L                      | Blue        | Low speed CANbus. |

## Aftermarket integrations

- **Wideband O₂ controller:**  Connect analog output to ECM X3 pin 55 (spare analog input).  Use shielded cable and ground at engine block.
- **Boost gauge:**  T‑tap into vacuum line post‑throttle body.  Electrical illumination power from fuse F17 (ignition).  Ground to chassis.
- **Methanol injection:**  Use a dedicated relay triggered from ECM fuel pump control (X2 pin 15) to avoid overloading factory circuits.

## CANbus IDs

When logging via HP Tuners or a custom CAN interface, the following arbitration IDs are relevant:

- **0x100 –** Engine RPM, knock retard and load.  Sample at 10 ms intervals.
- **0x12C –** Accelerator pedal position and throttle angle.
- **0x1F0 –** Boost pressure command and wastegate duty cycle.
- **0x200 –** Transmission input shaft speed and gear position (F35 sensors).

Always terminate the bus with 120 Ω resistors at each end.  Keep wire twists tight and avoid splices that can introduce noise.
