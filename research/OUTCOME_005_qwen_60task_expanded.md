# Outcome 005 — qwen on the 60-task bank with expanded capture

**Written 2026-09-05, after the runs.** Run against
`PREREGISTRATION_005_qwen_60task_expanded.md`.

## What ran

- `Qwen_Qwen3-4B-Instruct-2507-Q5_K_L.gguf`, card-verified preset,
  `--repeats 2`, full run: 120 probes → **100 passed, 20 failures**; repair
  sweep over all 7 interventions (3 coder-side ran; 4 architect-driven
  skipped — no architect loaded).
- Replication: `--seed 77 --probe-only`, restricted confirmation scan via
  `CALIBRATION_KIT_PREREGISTER` over the five Part-A signals plus the two
  signals that survived the unrestricted scan on run 1
  (`plateau_start_quartile`, `max_entropy`).

## Part A result — the early-window signal did NOT replicate across task sets

On the 18-task bank the first-10-token signals replicated across three
independent samples at d≈0.6–0.8. On the 60-task bank, on two independent
samples:

| signal | predicted | run 1 (60-task) | run 2 (seed 77) |
|---|---|---|---|
| `first10_max` | high=good | +0.381, p=0.139 | +0.358, p=0.159 |
| `first10_std` | high=good | +0.364, p=0.159 | +0.333, p=0.189 |
| `q_argmax` | high=good | not top-ranked | +0.179, p=0.502 |
| `phi_first10_mean` | high=bad | −0.345, p=0.182 | −0.328, p=0.197 |
| `q1_over_mean` | high=bad | not top-ranked | +0.073, p=0.777 |

Directions mostly held; significance did not come close. **Verdict: the
early-window signature is real on the 18-task bank and does not generalize
to the 60-task bank.** Under this project's own premise that is not a
contradiction — a signature is per-model *and per task set* — but it means
the 18-task claims cannot be presented as a property of the model file.
They are a property of the model file on that task distribution. The
published tables are marked accordingly rather than deleted.

## Part B result — a different signal survived on run 1

The unrestricted ~160-signal scan on run 1 found:

- **`plateau_start_quartile`, high=bad, d=−1.015, p_adj=0.0105** — selected
  and fitted on train, scored on held-out records; cross-validated
  balanced accuracy 0.75, picked in 4/5 folds.
- **`max_entropy`, high=bad, d=−0.938, p_adj=0.0079** — survives
  correction. On this bank the classic "high entropy = wrong" direction
  holds for this model.

On the seed-77 replication (restricted scan, 7 tests):

- `plateau_start_quartile`: d=−0.676, p=0.009 raw — same direction, clears
  the pre-registered bar (p<0.05 on the named signal) but not the
  7-test correction (p_adj=0.063). **Borderline replication.**
- `max_entropy`: d=−0.435, p=0.084 — same direction, under the bar.

## Part D — the task-transfer check (added after a review challenge)

A later question exposed a hole in the record-level holdout: it splits
generations, not tasks, so a held-out record can come from a task the
training half also contains. A signal detecting *task identity* rather
than wrongness passes that check while being useless on a new task. A
task-level holdout (whole tasks excluded from selection and fitting) was
added to the pipeline and applied to these raws via `reanalyze`:

- **Qwen:** under the strict task-level selection path, nothing survived
  on training tasks — 13 failing tasks cannot clear the corrected bar
  with ~9 in training. That answers "can the pipeline *find* a
  transferable signal at this scale" (no — underpowered), not "does the
  found signal transfer". For the second question the profile also
  reports `transfer_estimate`: the run's selected signal
  (`plateau_start_quartile`, high=bad) scored **0.73 mean balanced
  accuracy on unseen tasks over ~300 random task splits, above chance in
  92% of draws**. It transfers — with wide variance on unlucky task draws,
  and with the caveat that the signal was chosen on the full data, so
  this estimates the travel of a known signal, not unbiased selection.
- **Granite:** `margin_mean` was selected on training tasks at 0.87
  balanced accuracy and scored **0.47 — below chance — on the 18 held-out
  tasks**. A textbook case of the failure mode: real-looking effect,
  zero transfer. (Granite has no transfer estimate — its full-data scan
  selected nothing to test.)

**Consequence for the claims:** the correct summary is "qwen's signal
transfers to unseen tasks of the same bank, demonstrated; granite's does
not — and its `none` verdict stands". The profile now reports both
`holdout_validation` (record-level: does it work on new generations) and
`task_holdout_validation` (task-level selection + the repeated-split
transfer estimate), and reports say which question each answers.

## The honest summary

- Qwen on the 60-task bank: **a signal survives record-level validation
  and transfers to unseen tasks** (0.73 mean balanced accuracy, above
  chance in 92% of 300 task splits) — see Part D. The direction that
  survives is "high entropy / presence of a sustained-uncertainty plateau
  predicts failure" — the opposite shape claim from the 18-task
  early-spike result. Two independent samples agree on direction and
  disagree on magnitude.
- Task sets are part of the signature. "This model, this bank" is the unit
  of truth — which is the kit's premise operating on the kit's own
  history.
- Repair order is unaffected: `test_retry` leads (7 new recoveries),
  then `temp_retry` (+3), then `skeleton_fill` (+1). 20 failures, ~11
  recoverable coder-side.

## What changed in the kit because of this run

- The recommended-rule text and the markdown exporter hardcoded
  `max_entropy` in the gate description even when a different signal was
  fitted — fixed; the rule now names the signal it was fitted on.
- `decompose` (architect-dependent) crashed without an architect instead
  of skipping — the skip check only matched the `arch_` prefix. Fixed.
- `federation.py`'s Phase-3 recovery rate summed per-strategy recoveries
  (190.9% on the old qwen profile) — fixed to union recovered keys (90.9%).

## Artifacts

- `_calibration_qwen3-4b-instruct.json` / `_raw.jsonl` (full run)
- `_calibration_qwen3-4b-instruct_probe.json` / `_raw.jsonl` (seed-77
  replication, restricted scan)
