# Pre-registration 002 — confirming qwen's shape signal on qwen

**Written 2026-09-04, before the confirming run existed.** The run this
predicts has not been started at time of writing.

## Why this run exists

Two separate reasons, and they must not be allowed to blur into each other.

**1. Pre-registration 001 used the wrong confirmation set.** It tested a qwen
finding against granite. Under this project's premise — each model is its own
organism — a signal holding on qwen and not granite is the ordinary case, not
a refutation. The confirmation for a qwen finding is *another qwen run*. That
is what this is.

**2. The models were searched over different feature spaces.** The qwen run
recorded 12 entropy fields. Granite's recorded 25. Later runs record 30 (φ
confidence landed after granite started). Comparing "does this model have a
signal" across models searched over different candidate sets is not a fair
comparison — the model searched over more candidates gets more chances to find
something *and* a harsher multiple-comparison correction. Both models are
being brought onto the same feature set.

## The runs

Both with `--probe-only` (the signal question needs Phase 1 only; the repair
sweep is unaffected by entropy features and is not being re-run):

- `qwen3-4b-instruct`, `--repeats 10`, card-verified preset, no overrides.
- `granite-4.1-3b`, `--repeats 6`, card-verified preset, no overrides.

Both on the current collector, which records all 30 fields including
`first_token_entropy`, `first3/5/10_mean`, `early_slope`, `early_vs_rest`,
`phi_first`, `phi_mean`, `margin_first`, and a 16-point `trajectory_ds` from
which monotonicity, oscillation and spike-structure features are derived at
analysis time.

## Part A — the confirmation (pre-registered, primary)

Restricted to the three signals from Pre-registration 001, enforced by
`CALIBRATION_KIT_PREREGISTER="q1_over_mean,q_early_drop,q_argmax"`.

Predictions for the **new qwen run**, from the original qwen run:

| signal | predicted direction | original d |
|---|---|---|
| `q1_over_mean` (**primary**) | high=bad | −0.665 |
| `q_early_drop` | high=bad | −0.636 |
| `q_argmax` | high=good | +0.634 |

Success on the primary = **p < 0.05, two-sided permutation, direction
high=bad**. Effect size is expected to shrink; the original run both
discovered and measured the effect, so its d is an overestimate. Anything
retaining the direction at p < 0.05 counts as confirmed.

**Outcomes:**
- *Primary confirms.* The qwen shape signal is real for qwen. It becomes a
  shipped per-model rule with two independent runs behind it.
- *Primary fails.* The original was a false positive on its own data. It is
  withdrawn for qwen, and the withdrawal is published the same way the
  finding was.
- *Direction flips.* Treated as failure, not as a new finding.

Nothing in Part B can rescue a failed Part A.

## Part B — the new feature families (exploratory, NOT a confirmation)

Separately, and clearly labelled exploratory, both models' new data will be
scanned over the **full** current feature set — first-token entropy, early
slope, φ confidence, top1−top2 margin, monotonicity, oscillation rate, path
ratio, trend rho, spike structure — with Benjamini-Hochberg correction across
everything tested and held-out validation of any winner.

**Anything Part B turns up is a lead, not a finding**, and gets its own
pre-registration and its own confirming run before it is claimed. This is
recorded here in advance precisely so a Part B hit cannot later be presented
as though it had been predicted.

## Part C — the cross-model comparison (descriptive)

With both models on the same feature set, the per-model effect table in
`FINDING_002_pooling_artifact.md` becomes an equal comparison rather than one
between models searched over different candidate spaces. The pooling analysis
will be recomputed on that basis.

This is descriptive. It is the case against universality, and it is never a
test of any single model's signal.

## Recorded before the fact
- Prior qwen data: `examples/qwen_raw.jsonl`, 180 probes, 12 entropy fields.
- Granite full run (with repair sweep) in flight at time of writing on the
  25-field collector; its repair results stand regardless of anything here.
- No new probe data existed when this was written.
