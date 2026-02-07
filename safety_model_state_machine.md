# Safety model: policy engine + enforced state machine

Risk classes: PASSIVE, READ_ONLY_DIAG, ACTIVE_LOW_RISK (rare), ACTIVE_HIGH_RISK (blocked), BLOCKED.

States: BOOT → SELF_TEST → IDENTIFY_TARGET → PASSIVE_CAPTURE/READ_ONLY_DIAG → PACK → COMPLETE
Any failure → FAULT_LOCKOUT.

Arming window + preconditions + audit logs are mandatory for anything beyond passive capture.
