# legacy/ — retained, not retracted

Modules here are off the live import path. Nothing in `src/`, `tests/`, or
`examples/` imports from this package, and the test suite does not exercise it.

**Moving a file here does not withdraw its claims. Precedence carries.**

That is the whole point of the folder. A claim that was made, dated, and left
standing is evidence about what was tried — deleting it destroys the only record
of the path taken. Anything moved here stays readable, stays runnable, and keeps
its original authorship and reasoning intact.

## Two reasons a file lands here

| Reason | What it means | What precedence means for it |
|--------|---------------|------------------------------|
| **Superseded** | A later claim replaced this one. The original was tested and falsified. | The falsified version is the record of *how* the current claim was arrived at. Read it with the entry in [`docs/method.md`](../docs/method.md) that retired it. |
| **Unwired** | The claim was never falsified. It was never load-bearing either — no module depends on it, no test constrains it. | The claim still stands as written. It is dormant, not wrong. Re-wiring it is a live option, not a reversal. |

The second case is easy to mistake for the first. An unwired module has *no
evidence against it*, because nothing ever ran that could have produced any.
Absence of a load path is not a result.

## Current contents

### `architecture_mismatch.py` + `schema.py` — unwired

**Moved:** 2026-08-15. **Origin:** vendored from the
[`calibration-audit`](https://github.com/JinnZ2/calibration-audit) repository
(commit `1a93760`, "Add architecture_mismatch module and calibration schema").

`architecture_mismatch.py` detects mismatch between language-primary and
substrate-primary cognitive architectures, emitting a `CalibrationReport`.
`schema.py` supplies the `Band` / `DimensionScore` / `CalibrationReport` types
it scores into; it is imported by `architecture_mismatch.py` and nothing else,
so the two move together.

**Why unwired, not superseded:** the audit is a general-purpose instrument. It
was never connected to the trust-exit model — no `src/` module imports it, and
no test constrains its 5 dimensions, its band cutoffs (0.30 / 0.60 / 0.85), or
its `0.6 * mean + 0.4 * worst` aggregation. Its claims are untested here, not
disproved here.

**The contrast that decided the move:** `support_cartography.py` arrived the
same way — vendored from another repo — but was then bridged into the model by
`znp_gate_bridge.py`, which maps ZNP fingerprint signals onto its
emission/capture/retention gates. That bridge is tested, and `Gate` is part of
the published 1.0.0 contract via `dominant_gate`. Same provenance, opposite
outcome: one earned a load path, one did not. `support_cartography.py` stays in
`src/`; these two do not.

**What would bring them back:** a bridge module analogous to
`znp_gate_bridge.py` — something that reads trust-exit state and scores it
through `run_architecture_mismatch_audit`, with tests pinning the mapping. The
plausible seam is that substrate-primary users are systematically the ones who
exit without emitting a complaint, which is the same population the ZNP
fingerprint already scores. That is a hypothesis, and it is recorded as an open
unknown (U4) in [`docs/method.md`](../docs/method.md) rather than asserted here.

## Rules

1. **Do not delete files from this folder.** Retention is the function.
2. **Do not edit them to make them correct.** They are a dated record. Corrections
   belong in the superseding module, and the correction gets a log entry in
   [`docs/method.md`](../docs/method.md).
3. **Import fixups are allowed** — path rewrites needed to keep a file importable
   after a move do not change any claim. `architecture_mismatch.py` had exactly
   one, `src.schema` → `legacy.schema`.
4. **Every entry states which of the two reasons applies**, with a date and the
   commit it came from.
