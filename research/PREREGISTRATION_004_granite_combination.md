# Pre-registration 004 — granite's combination signal

**Written 2026-09-04, before the confirming runs were started.**

## Background

`granite-4.1-3b` (`granite-4.1-3b-Q5_K_M.gguf`) has **no usable univariate
signal** — nothing survived Benjamini-Hochberg correction across the candidate
scan. It does appear to have a usable **combination**.

From 108 probes (79 correct / 29 incorrect), 5-fold cross-validated, with the
whole selection procedure re-run on 40 label shuffles:

| metric | value |
|---|---|
| CV balanced accuracy | **0.873** |
| CV recall (failures caught) | 100% |
| CV false-flag rate (correct work flagged) | 25% |
| typical combination size | 2.4 signals |
| label-shuffle null | median 0.476, max 0.630 |
| result vs null | beats 40/40, empirical p ≈ 0.024 |

Combination fitted on all 108: `q_range < 0.0525` **OR** `osc_rate < 0.5278`.

Signal stability across folds: `q_range` 3/5, `osc_sign_changes` 2/5,
`n_semantic` 2/5, `osc_rate` 2/5, `n_spikes` 1/5, `trend_rho` 1/5.

**Granite draws on a different family than qwen.** Qwen keys on opening-window
magnitude (`first10_max`); granite keys on oscillation and spread — how much
the trajectory ranges and how often it changes direction.

## Why this needs confirming

Two distinct weaknesses, and neither is fixed by the CV or the null:

1. **Low stability.** No signal appears in more than 3 of 5 folds. The
   cross-validation shows the *procedure* generalises; it does not show that
   the specific pair being shipped is the right one. Several near-equivalent
   pairs exist and the greedy step picks among them somewhat arbitrarily.
2. **29 failures is thin** for a procedure that selects from ~15 candidates
   and can combine up to 4 of them.

The qwen finding was confirmed on independent samples before being claimed.
Granite's has not been, and must not be presented at the same confidence until
it is.

## The runs

`--probe-only`, card-verified preset (temp=0.0, top_p=1.0, top_k=0 — greedy,
matching IBM's own card example), no architect:

- **Run A:** `--repeats 12 --seed 4001` (~216 probes, expect ~58 failures)
- **Run B:** `--repeats 12 --seed 4002` (independent sample)

Both on the current 30-field collector. Independence will be verified
generation-by-generation, not assumed — a missing seed previously produced a
bit-identical replay that looked like a second sample.

## The predictions

**Primary.** On Run A, the combination procedure produces a usable result:
CV balanced accuracy **≥ 0.60** AND beats the 40-shuffle label null at
**p < 0.05**.

**Secondary 1.** `q_range` appears in the selected combination with direction
**high=good** (flagged when *below* threshold).

**Secondary 2.** Run B reproduces the primary — CV balanced accuracy ≥ 0.60,
clearing the null — and its CV balanced accuracy is within **0.15** of Run A's.

**Expected shrinkage.** The 0.873 from the discovery run is an overestimate:
that run both discovered and measured the effect. A result in the 0.65–0.80
band at higher failure counts counts as full confirmation. Anything at or
above 0.60 clearing the null confirms the primary.

## Outcomes

- **Primary confirms on both runs.** Granite has a usable combination signal,
  from a different signal family than qwen. Two models, two mechanisms, one
  pipeline — and the strongest available demonstration that these signals are
  per-model rather than universal.
- **Primary confirms on A, fails on B.** Treated as failure. One run is not a
  finding, which is the whole point of this file.
- **Primary fails.** The 0.873 was a small-sample artefact that CV and the
  null both failed to catch, which would itself be an important negative
  result about the combination machinery and would be published as one.
- **Primary confirms, secondary 1 fails.** The combination is real but its
  membership is unstable. Reported as "granite has a combination signal; the
  specific signals vary run to run" — honest, and materially weaker than a
  named rule.

## Scope

`granite-4.1-3b-Q5_K_M.gguf` — that model, that size, that quantization, the
18-task Python bank, greedy decoding. Nothing here is claimed to transfer to
another model or another quantization of granite.
