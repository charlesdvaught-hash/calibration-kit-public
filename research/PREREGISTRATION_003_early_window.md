# Pre-registration 003 — early-window and confidence features

**Written 2026-09-04, before the confirming run was started.**

## Where these came from

Pre-registration 002 Part B was an exploratory scan of all 43 candidate
statistics on an independent qwen3-4b-instruct sample (`--seed 77`, 147
correct / 33 incorrect). Five survived Benjamini-Hochberg correction:

| signal | d | raw p | adjusted p | pre-registered in 002? |
|---|---|---|---|---|
| `q_argmax` | +0.821 | <0.0001 | <0.0001 | **yes — confirmed** |
| `first10_max` | +0.784 | <0.0001 | <0.0001 | no — new |
| `first10_std` | +0.707 | 0.0002 | 0.0029 | no — new |
| `q1_over_mean` | −0.630 | 0.0010 | 0.0108 | **yes — confirmed** |
| `phi_first10_mean` | −0.594 | 0.0020 | 0.0172 | no — new |

The two that were pre-registered are confirmed findings. **The three new ones
are leads**, exactly as Part B said in advance they would be, and this file is
their confirmation test.

## The reading

The three new survivors all describe the opening ten tokens, and they agree:

- `first10_max` **+0.784** — correct generations reach a *higher* peak entropy
  in their opening tokens.
- `first10_std` **+0.707** — and vary *more* across those tokens.
- `phi_first10_mean` **−0.594** — and carry *lower* top-1 confidence there.

Read together with `q1_over_mean` (−0.630, correct generations have a *lower*
first quarter relative to their own mean): a correct generation appears to
open with a brief sharp burst of genuine uncertainty — the model weighing
alternatives — and then settle. An incorrect one opens flat and uniformly
committed.

That is the opposite of the naive expectation that early confidence indicates
correctness. It is also why summary statistics find nothing: a short spike
plus a long calm tail averages to the same number as a flat middling
trajectory.

## The prediction

A third independent qwen3-4b-instruct sample: `--probe-only --repeats 10
--seed 1312`, card-verified preset, same 18-task bank. Different seed, so
genuinely new generations (verified for seed 77: 167 of 180 differed).

Restricted to these three, enforced by
`CALIBRATION_KIT_PREREGISTER="first10_max,first10_std,phi_first10_mean"`:

1. **`first10_max`** separates with direction **high=good**, p < 0.05. *(primary)*
2. **`first10_std`** separates with direction **high=good**, p < 0.05.
3. **`phi_first10_mean`** separates with direction **high=bad**, p < 0.05.

Effect sizes are expected to shrink — run 2 both discovered and measured
these, so its d values are overestimates. Direction retained at p < 0.05 is
the bar.

## Outcomes

- **Primary confirms.** The early-window burst is a real property of this
  model, with two independent samples behind it. It joins `q_argmax` and
  `q1_over_mean` as shipped per-model signals for qwen3-4b-instruct.
- **Primary fails.** Withdrawn for qwen, published as withdrawn.
- **Direction flips.** Treated as failure, not as a new finding.

No re-scanning. If these three fail, the next step is not to find a different
winner in the same data.

## Scope

This concerns **qwen3-4b-instruct only**. Granite showed none of these. Under
this project's premise that is expected and is not evidence against anything
here — see `research/FINDING_002_pooling_artifact.md`.
