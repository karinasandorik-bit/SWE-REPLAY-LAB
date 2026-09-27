# SWE-REPLAY-LAB

Replayable coding-agent experiments with pre-model workspace snapshots and an independent terminal oracle.

Invariant: no model action may occur before S0 is recorded.

States: BOOTSTRAP -> S0_SEALED -> TRAJECTORY -> ORACLE -> REPLAY.
