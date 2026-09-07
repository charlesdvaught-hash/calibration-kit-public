# Pre-registration 001 — trajectory shape as a correctness signal

**Written 2026-09-04, before the confirming run's results existed.**
The granite run this tests against was already in flight at the time of
writing and its analysis had not been read. This file is committed so the
prediction cannot be adjusted after the fact.

## Background

On this task bank, the *level* of a model's generation entropy does not
predict whether the generated code passes its tests. Measured on
qwen3-4b-instruct at `--repeats 10` (180 probes, 147 correct / 33 incorrect,
minimum detectable effect d≥0.54):

| statistic | Cohen's d | permutation p |
|---|---|---|
| `max_entropy` | +0.169 | 0.387 |
| `mean_entropy` | +0.353 | 0.066 |

Neither separates. The same result holds on granite and mini-coder-4b.

## The hypothesis

The level washes out *when* during a generation the model was uncertain. A
confident opening that degenerates and a hesitant opening that resolves
produce the same mean. **The shape of the entropy trajectory may carry the
signal that its level does not.**

Derived from the four per-quartile entropy averages already recorded, tested
on the qwen data alongside every other candidate (22 signals, Benjamini-
Hochberg FDR at alpha 0.05):

| signal | d | raw p | adjusted p | survives |
|---|---|---|---|---|
| `q1_over_mean` | -0.665 | 0.0008 | 0.0088 | yes |
| `q_argmax` | +0.634 | 0.0007 | 0.0088 | yes |
| `q_early_drop` | -0.636 | 0.0015 | 0.0110 | yes |
| `q_slope` | +0.530 | 0.0058 | 0.0319 | yes |
| `q4` | +0.494 | 0.0103 | 0.0440 | yes |
| `q_curvature` | -0.482 | 0.0120 | 0.0440 | yes |

These are six views of one effect, not six findings — all six are functions
of the same four numbers. Stated as one claim:

> **Incorrect generations open with a burst of uncertainty that then
> subsides. Correct generations open calmer and stay level or rise.**

## Why this needs confirming rather than shipping

The correction above covers the 22 tests that were run. It does not cover
the fact that these features were *constructed in response to* a negative
result on the same dataset. That is a garden-of-forking-paths problem, and
no multiple-comparison correction fixes it. The effect must reproduce on
data that played no part in choosing the features.

## The prediction

On **granite-4.1-3b** at `--repeats 6` (~108 probes, a different model
family, a different failure rate, data collected before this file was
written and not yet analysed):

1. `q1_over_mean` separates correct from incorrect with **direction
   high=bad** (higher opening quarter relative to the generation's own mean
   predicts failure), at **p < 0.05** on a two-sided permutation test.
2. `q_early_drop` separates with **direction high=bad**.
3. `q_argmax` separates with **direction high=good** (a later entropy peak
   predicts correctness).

Primary endpoint is (1). Secondary are (2) and (3).

**Only these three signals will be tested**, enforced by
`CALIBRATION_KIT_PREREGISTER="q1_over_mean,q_early_drop,q_argmax"`, which
restricts the scan and records itself in the profile. No re-scanning, and no
substituting a different winner if these fail.

## What each outcome means

- **All three reproduce, same directions.** The effect is real and
  cross-model. Trajectory shape becomes the kit's headline signal and the
  entropy-level claim stays retired.
- **The primary reproduces, secondaries don't.** One real effect, weaker
  than the qwen run suggested. Report it with both runs' effect sizes and
  keep collecting models.
- **The primary fails.** The qwen result was model-specific or a false
  positive. It gets reported as such — a signal that survived correction on
  one model and did not reproduce on another is exactly the kind of result
  this kit exists to catch, including in its own findings.
- **Directions flip.** Treat as a failure to reproduce, not as a new
  finding. A flipped sign is what noise does.

## Recorded before the fact

- qwen3-4b-instruct run: `examples/qwen_raw.jsonl` (180 probes, complete)
- granite run: in flight at time of writing, `--repeats 6`, with an
  architect, card-verified preset, pipeline 2026.09.04
- Neither the granite profile nor its report had been generated or read when
  this was written.
