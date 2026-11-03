2026-11-03 R120 initial 4-way build: control/sight/collision/both; no ROMs in artifacts.
Retry: the previous run passed all ROM builds and RAM, but demo3 control returned a transient BlastEm RSP EOF with zero checkpoints. Retry zero-checkpoint EOF only; never ignore mismatches.
