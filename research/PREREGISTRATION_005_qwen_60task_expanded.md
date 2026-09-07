# Pre-registration 005 — qwen on the 60-task bank with expanded capture

**Written 2026-09-05, before the run existed.** The run this predicts has
not been started at time of writing.

## Why this run exists

Three things changed since the qwen findings were published, and each one
is a reason the published numbers are no longer the current measurement:

1. **The task bank went 18 → 60** (46 function + 14 assembly). Every qwen
   number on record came from the 18-task bank. A different task set is a
   different measurement, not a longer version of the old one.
2. **The capture expanded.** The collector now records, in the same single
   generation pass: full-vocabulary entropy, the commitment curve (true
   top-1/5/20 probability mass and tail leak), KL-divergence series
   (step-to-step, vs-uniform, vs-own-centroid), sampled-token surprisal and
   rank, structural-token entropy, and a thinking-phase split. The candidate
   scan now covers ~170 statistics, up from ~30 — a harsher
   Benjamini-Hochberg bar by design.
3. **The granite withdrawal is remediable.** Granite was withdrawn for
   pseudo-replication, not for a failed measurement. A 60-task run with an
   independent seed is the legitimate second model.

## The runs

- `Qwen_Qwen3-4B-Instruct-2507-Q5_K_L.gguf`, card-verified preset
  (temp=0.7, top_p=0.8, top_k=20), `--repeats 2`, full run (probe +
  repair sweep).
- Replication: same command with `--seed 77 --probe-only` — a genuinely
  independent sample (seed change = new generations).
- `granite-4.1-3b-Q5_K_M.gguf`, card-verified preset, `--repeats 2`, full
  run, then `--seed 4002 --probe-only` replication.

## Part A — does the early-window signal survive? (pre-registered, primary)

The confirmed qwen finding across three independent 18-task samples: the
first ~10 tokens predict pass/fail, direction high=good for
`first10_max`/`first10_std`/`q_argmax`, high=bad for
`phi_first10_mean`/`q1_over_mean`.

Confirmation scan restricted via
`CALIBRATION_KIT_PREREGISTER="first10_max,first10_std,q_argmax,phi_first10_mean,q1_over_mean"`.

Predictions on the **new** run:

| signal | predicted direction | prior d (run 2 / run 3) |
|---|---|---|
| `first10_max` (**primary**) | high=good | +0.784 / +0.765 |
| `first10_std` | high=good | +0.707 / +0.670 |
| `q_argmax` | high=good | +0.634 / +0.821 |
| `phi_first10_mean` | high=bad | −0.594 / −0.624 |
| `q1_over_mean` | high=bad | −0.665 / −0.630 |

Success on the primary = **p < 0.05, two-sided permutation, direction
high=good**, on the 60-task run, and again on the seed-77 replication.
Effect-size shrinkage is expected — the original runs discovered and
measured the effect on the same data.

**Outcomes:**
- *Confirms on both new samples.* The early-window signal is a robust
  property of this model file across two task banks and five independent
  samples.
- *Fails.* The 18-task finding does not generalize across task sets — a
  genuine and publishable result about how local these signatures are.
  It gets reported as such, not quietly dropped.
- *Direction flips.* Treated as failure, not a new finding.

Nothing in Part B can rescue a failed Part A.

## Part B — the expanded feature families (exploratory, NOT confirmation)

The full ~170-statistic scan runs on both models' new data with BH
correction and held-out validation. New families — KL series, surprisal,
commitment mass, thinking-phase splits — are leads at best. **Anything
Part B turns up gets its own pre-registration and its own confirming run
before it is claimed.** This is recorded in advance so a Part B hit cannot
later be presented as predicted.

## Part C — the honest-expectation note

Prior evidence: 1 of 3 models has a usable signal. The 60-task bank raises
the floor on statistical power (more tasks = more independent observations
at temp>0), and the wider scan raises the bar each candidate must clear.
`none` on either model is a legitimate result the guarantee already covers.

## Recorded before the fact

- Prior qwen data: `examples/qwen_raw.jsonl`, `qwen_seed77_probe_raw.jsonl`,
  `qwen_seed1312_probe_raw.jsonl` — three independent samples, 18-task bank.
- The expanded collector and 60-task bank are in the working tree; no run
  on either existed when this was written.
