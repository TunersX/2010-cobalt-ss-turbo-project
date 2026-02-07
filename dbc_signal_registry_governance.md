# DBC + Signal Registry governance

DBC = decoding contract. Registry = meaning + confidence + derivation.

Versioning:
- DBC semantic versions
- Registry semantic versions
- breaking changes require major bumps

Registry entry fields:
- canonical_name, frame/signal ref, units, platform applicability, confidence
- validation evidence: trace bundle IDs and notes
- reviewer sign-off

Quality gates:
- no duplicate canonical names
- no unit changes without breaking bump
- derived channels must document formulas + inputs
