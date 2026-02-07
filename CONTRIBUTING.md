# Contributing

Thank you for taking the time to contribute to this documentation and technical archive.  Maintaining accurate records of modifications, diagnostics and tuning changes on a single vehicle requires attention to detail and consistent formatting.  The following guidelines help ensure that contributions are clear, reproducible and safe.

## Ways to contribute

- **Documentation updates:**  Add detailed steps, torque specifications, tool lists, or diagnostic procedures that are missing or inaccurate.  Ensure that procedures are specific to the 2010 LNF/F35/G85 configuration and include safety notes.
- **Build log entries:**  Document completed modifications or maintenance in `docs/build_log.md` with date, mileage, parts used and test results.
- **Wiring or CANbus notes:**  Update `docs/wiring.md` with pinouts, wire colours and bus traffic analysis.  Include photos or diagrams where possible.
- **Issues and feature requests:**  If you identify an error or want to suggest a new guide or performance target, open an issue using the provided templates.

## Branching and pull requests

1. **Fork the repository** and create your own branch for the change.  Use descriptive branch names such as `fix-intake-torque-specs` or `add-clutch-upgrade-guide`.
2. **Make atomic commits.**  Each commit should contain a logically related set of changes.  Commit messages should have the form:

   ```
   Subject line summarizing change (max 72 characters)

   * Detailed description of what was changed and why
   * Reference any related issues if applicable
   ```

3. **Ensure builds and linting pass.**  Although this repository is primarily text, run a Markdown linter or view the files locally to ensure formatting is correct before submitting.
4. **Create a pull request (PR).**  Use the PR template and describe the motivation for the change, including any test results or dyno logs if relevant.
5. **Discuss and review.**  Project maintainers will review your PR, request changes if necessary and merge once approved.

## Style guide

- Write in a clear, technical style.  Use metric units and include conversions if necessary.
- Provide torque values in N·m and lb‑ft.  List required tools and part numbers.
- For code snippets (e.g., HP Tuners configuration), use fenced code blocks and include context.
- Avoid generic automotive information; focus on the 2010 Cobalt SS Turbo platform.  If you must reference generic procedures, clearly mark assumptions and differences.

## Safety

Always prioritize safety when performing mechanical work.  If a procedure could lead to personal injury or vehicle damage if done incorrectly, include warnings and recommended personal protective equipment.  Document jack points, torque sequences and any one‑time‑use fasteners.  When in doubt, consult the factory service manual.

By contributing to this project, you agree to abide by the `CODE_OF_CONDUCT.md` and ensure that your contributions are accurate and safe.
