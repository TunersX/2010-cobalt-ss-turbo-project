# 2010 Cobalt SS Turbo LNF Project

This repository is the technical archive for Brody’s 2010 Chevrolet Cobalt SS Turbo equipped with the 2.0 LNF engine, F35 5‑speed transmission, and G85 limited‑slip differential.  Its purpose is to track every modification, maintenance action, diagnostic finding, and tuning adjustment performed on this specific Delta‑platform build.  The goal is to maximize reliability and performance while documenting lessons learned for future reference.

## Quick start

1. Install Git if you haven’t already and clone the repository:

   ```sh
   git clone https://github.com/yourusername/2010-cobalt-ss-turbo-project.git
   cd 2010-cobalt-ss-turbo-project
   ```

2. Review the documentation in the `docs/` folder.  The `build_log.md` chronicles changes in chronological order, and `maintenance_schedule.md` lists recommended service intervals.  Wiring diagrams and CANbus information live in `wiring.md`.

3. If you plan to contribute, please read `CONTRIBUTING.md` and follow the code‑of‑conduct in `CODE_OF_CONDUCT.md`.

## Project overview

| Component             | Specification                                        |
|----------------------|------------------------------------------------------|
| Vehicle              | 2010 Chevrolet Cobalt SS Turbo                       |
| Engine               | 2.0 LNF Ecotec turbocharged (stock bottom end)       |
| Transmission         | F35 5‑speed manual with short‑ratio G85 LSD         |
| Purpose              | Document maintenance, upgrades, diagnostics & tuning |

This build targets a street‑friendly, track‑capable configuration balancing power, drivability and longevity.  Supporting modifications, tuning parameters and test results are included as the project evolves.

## Repository contents

- `docs/build_log.md` – chronological record of repairs, modifications and tuning changes.
- `docs/maintenance_schedule.md` – recommended fluid service, inspection intervals and torque values.
- `docs/wiring.md` – wiring diagrams, pinouts and CANbus integration notes.
- `docs/tuning_notes.md` – high‑level tuning and HP Tuners parameters for the LNF platform.
- `.github/ISSUE_TEMPLATE/bug_report.md` – template for reporting issues with documentation or procedures.
- `.github/ISSUE_TEMPLATE/feature_request.md` – template for suggesting new documentation or performance goals.
- `CHANGELOG.md` – versioned record of changes to this repository.

## Prerequisites and environment

This repository is documentation‑centric, so there are no software dependencies beyond a Markdown editor and Git.  To reproduce the procedures on the vehicle you’ll need standard mechanic tools (metric sockets, torque wrench, jack stands, etc.) and an HP Tuners setup for flashing calibrations.  Safety glasses, gloves and proper lifting equipment are mandatory.  See the individual guides in `docs/` for detailed tool lists and torque specifications.

## License

This work is licensed under the MIT License.  See the `LICENSE` file for full terms.  You are free to fork and adapt these procedures for your own use, but please credit the original author and do not misrepresent documented results.
