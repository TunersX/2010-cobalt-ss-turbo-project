# Tuning notes

This document summarizes calibration changes and tuning considerations for the LNF platform using HP Tuners.  Each section should document baseline parameters, modifications and rationale.

## Baseline calibration

The factory GM Stage 1 tune for the 2010 Cobalt SS raises boost targets to ~18 psi and refines spark timing.  Baseline parameters:

- **Desired boost:**  18 psi (124 kPa gauge) ramping in by 3 000 rpm.
- **Spark advance:**  15–20° BTDC under load, reduced under high knock conditions.
- **Fueling:**  11.5 AFR commanded under boost with stock injectors (42 lb/hr).  Lambda ~0.78.
- **Rev limiter:**  7 000 rpm, fuel cut with spark retard.

## Stage 2 calibrations

With bolt‑on upgrades (high‑flow downpipe, larger intercooler, K04+ turbo) the tune must be adjusted:

- Increase boost target to 22–23 psi while monitoring knock retard; adjust wastegate duty table accordingly.
- Calibrate MAF transfer function for intake mods to avoid fuel trim errors.
- Retard timing by 2–3° at high load to account for increased cylinder pressure; restore if knock remains low.
- Enrich commanded AFR to ~11.0–11.2 to maintain safe exhaust gas temperatures; consider larger injectors (60 lb/hr) and a high‑pressure fuel pump upgrade.
- Raise torque management limiters to avoid throttle closing; adjust driver demand tables for smoother response.

## Safety considerations

- **Fuel quality:**  Always use premium 94 RON fuel or ethanol blends (E30–E50) when running elevated boost.  Lower octane will cause knock and reduce reliability.
- **EGT monitoring:**  Install a wideband and pyrometer to monitor AFR and exhaust temperatures.  High EGTs (> 850 °C) indicate insufficient fueling or timing.
- **Clutch and transmission limits:**  The stock F35 and clutch can handle ~350 lb‑ft of torque.  Exceeding this can lead to premature failure; upgrade the clutch and limited‑slip differential if aiming beyond 350 whp.
- **Cooling:**  High boost increases heat.  Upgrade the intercooler and consider adding an auxiliary oil cooler.  Monitor coolant temps via HP Tuners and avoid exceeding 105 °C.

Document all changes with HP Tuners file names, log snapshots, and dyno results.  Record baseline runs before making adjustments to better quantify gains.
