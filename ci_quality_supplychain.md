# CI, Quality Gates, and Supply Chain Integrity

## Test layers
- unit tests (DBC parser, decode scaling, schema validation)
- golden trace regression (expected output hashes)
- policy tests (blocked list + absence of unsafe surfaces)
- bundle validator tests (error taxonomy correctness)
- replay determinism tests

## Release gates
- SBOM generation (Python deps + OS deps if packaged)
- provenance metadata (commit hash, CI run ID)
- signed release artifacts (optional)
- “no unsafe surface” scan must pass
- golden trace suite must pass

## SLSA mindset (practical)
- pinned dependencies
- reproducible builds where feasible
- build provenance artifacts stored with releases
