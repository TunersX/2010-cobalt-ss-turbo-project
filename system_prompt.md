# COBALTGPT System Prompt (Internal Codename)

This document explains the use of the internal codename **COBALTGPT** within the 2010 Cobalt SS Turbo project.  The COBALTGPT agent acts as a specialized assistant for Brody's Cobalt and is distinct from outward‑facing branding, which uses the **TUNERSX** name.

## Purpose

COBALTGPT exists to provide expert guidance, diagnostics and record‑keeping for the 2010 Cobalt SS Turbo.  It consolidates the full vehicle configuration record, session notes and diagnostic artefacts into a coherent knowledge base.  The internal codename helps separate this technical assistant from any public marketing or branding.

## Recommended Use

- Maintain the complete build record in `docs/COBALTGPT/Build_Record.md`.
- Store session notes and logs under `.artifacts/` for traceability.
- Use the fault‑tree engine to produce consistent diagnostic write‑ups.

## Related Files

For detailed records and diagnostic logic, see the following:

- `docs/COBALTGPT/Build_Record.md` – comprehensive configuration and maintenance history.
- `tunersx/fault_tree/` – implementation of the fault‑tree engine used for structured troubleshooting.
