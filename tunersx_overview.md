# TUNERSX Overview

**TUNERSX** is a vehicle diagnostics and telemetry toolkit being developed for the 2010 Cobalt SS Turbo platform.  It focuses on read‑only access to the vehicle’s high‑speed CAN bus and diagnostic services.  The project seeks to enable comprehensive logging, decoding and analysis while respecting GM’s security policies and avoiding any write or security‑critical operations.

## Legal Notice

This project is licensed under the MIT License.  Copyright © 2025 Brody McNelly.  “TUNERSX” is a trademark of Brody McNelly, and “COBALTGPT/COBALT_AI” is an internal codename.  This project is not affiliated with, sponsored by, or endorsed by any vehicle manufacturer or tool vendor.  See `LICENSE` for the full text of the license.

## Scope and Boundaries

The toolkit deliberately excludes write or security functions:

- **No SecurityAccess routines** – seed/key unlocking is out of scope.
- **No ECU writes or routine control** – read‑only diagnostics and logging only.
- **No immobilizer/theft logic manipulation.**

This ensures that the tool remains a safe, legal companion for diagnostics and tuning.

## Repository Structure

The project is organised into clear modules to support repeatability and maintainability:

- **docs/** – planning documents, requirements, architecture and test plans.
- **src/tunersx/** – Python package implementing transports, logging, decoding and policy enforcement.
- **examples/** – sample logs, parsers and demo scripts.
- **data/** – reference datasets and sample outputs.
- **dbc/** – CAN database files and loaders.
- **gm_pack/** – GM‑facing deliverables such as one‑pagers and demo scripts.
- **legal/** – licence, notice and trademark texts.

## Project Planning Phases

The development roadmap is split into incremental phases to build a reliable logging and analysis ecosystem:

1. **Dev Environment Setup** – Configure a Windows or Linux machine with Python 3.11+, `python‑can`, `pandas`, `numpy` and optional GUI libraries.  Acquire a USB CAN adapter supporting 500 kbps (e.g. CANable or Kvaser) and verify connectivity via the OBD‑II port.
2. **Baseline Data Capture** – Log OBD‑II PIDs and raw CAN frames during varied driving conditions.  Store logs in CSV for correlation.
3. **Signal Analysis and Mapping** – Use `pandas` and CAN libraries to correlate PIDs with CAN IDs and create mapping files that translate raw frames into engineering values.
4. **Minimal Logging Tool** – Build a Python‑based logger that maps CAN frames to channels, outputs CSV, and optionally renders live gauges.  Consider merging external sensor data (e.g. wideband, boost, fuel pressure) via analog interfaces.
5. **Framework Expansion** – Develop additional modules for DBC integration, unknown frame exploration, and analysis suites (knock analysis, boost control behaviour, heat soak, etc.).  Gradually introduce GUI dashboards and provenance tracking.

Throughout these phases, emphasise repeatability and safety.  Keep logs, test plans, and configuration in version control so that every change can be validated against known baselines.

## Next Steps

Refer to the project roadmap and plan documents in the `docs/` directory for detailed tasks and milestones.  Use the glossary in `docs/cobalt/glossary.md` for definitions of key terms.  The COBALTGPT system prompt described in `docs/cobalt/system_prompt.md` provides guidance on how the assistant integrates with this project.

**Note:** Any instruction or content that references external servers or passphrases has been removed to keep this file focused on legitimate project planning and documentation.
