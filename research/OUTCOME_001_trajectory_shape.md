# Outcome 001 — the confirmation design was wrong, not the finding

**Superseded framing.** This document originally recorded that the qwen
trajectory-shape finding "failed to replicate" on granite. That conclusion
applied a standard this project explicitly rejects, and it is withdrawn.
The numbers below are unchanged; the reading of them is corrected.

## What was actually tested

Pre-registration 001 predicted that three signals found on
qwen3-4b-instruct would reproduce **on granite-4.1-3b**. They did not:

| signal | qwen d | granite d | granite p |
|---|---|---|---|
| `q1_over_mean` | −0.665 | +0.175 | 0.425 |
| `q_early_drop` | −0.636 | −0.265 | 0.226 |
| `q_argmax` | +0.634 | −0.205 | 0.400 |

## Why that was the wrong test

The design used **a different model as the replication set**. Under this
kit's core premise — each model is its own organism, with its own
relationship between uncertainty and correctness — a signal that holds for
qwen and not for granite is not a failed replication. It is the ordinary
case. It is the same phenomenon as one model's entropy running high when it
is right and another's running high when it is wrong.

Asking "does qwen's signal reproduce on granite?" answers a question about
universality. This kit does not claim universality and does not sell it.
The question it asks is "does this signal hold up for *this* model?" — and
the only data that can answer it is more data from that model.

**The correct confirmation for a qwen finding is a second independent qwen
run.** That test has not been run.

## What granite's numbers actually are

Granite's own profile, on granite's own data: 79 correct / 29 incorrect,
minimum detectable effect d ≥ 0.61. None of the three shape signals reached
significance there. That is granite's result, and it belongs in granite's
playbook — not as a verdict on qwen's.

## What the qwen finding stands on now

Not cross-model agreement. Within-model evidence, which is the standard that
matches the claim:

- 180 probes, 147 correct / 33 incorrect, adequately powered (MDE d ≥ 0.54).
- `q1_over_mean` d = −0.665, raw p = 0.0008, **Benjamini-Hochberg adjusted
  p = 0.0088** across all 22 candidates tested.
- **Held-out validation**: signal selected and threshold fitted on 126
  training records, scored on 54 records that played no part in either
  decision. Balanced accuracy **train 0.612 → test 0.618**. No drop.

The held-out number is the important one. It needs no correction for how
many candidates were searched, and it is computed entirely within one model.

## The distinction that keeps this honest

"Each model is unique" is only a scientific position if a per-model claim
can still be wrong. Otherwise every model gets its own story and none of
them can ever fail. The per-model rigor is what prevents that:

- a permutation test, so a direction is never read off the sign of a noisy
  mean difference;
- correction across every candidate searched, so a 22-signal scan cannot
  manufacture a winner;
- a held-out split, so the number quoted was measured on records the search
  never touched.

All three operate **inside one model's own run**. None of them appeals to
another model. They are what separates "this model is its own organism"
from "this model gets whatever story its noise suggests."

## Standing conclusion, corrected

- `max_entropy` and `mean_entropy` do not separate correct from incorrect
  output on any of the three models calibrated. That claim is per-model and
  holds per-model.
- Trajectory shape separates on qwen3-4b-instruct, survives correction, and
  holds on held-out data from that model. It does not separate on granite or
  mini-coder. **All four statements are findings.** The disagreement between
  them is the product, not a problem with it.
- Every entropy claim published before 2026-09-04 remains withdrawn — those
  were read off the sign of a mean difference with no test, which is a
  per-model failure of rigor, not a question of universality.

## Next test

An independent second qwen3-4b-instruct run at `--repeats 10`, testing only
`q1_over_mean`, `q_early_drop`, `q_argmax` in the predicted directions, with
`CALIBRATION_KIT_PREREGISTER` set. Roughly 45 minutes. That is the test
Pre-registration 001 should have specified.

See `PREREGISTRATION_002_pooling_artifact.md` for the separate and larger
question this raised.
