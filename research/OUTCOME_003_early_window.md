# Outcome 003 — the early-window signal replicated, 3 of 3

**All three predictions confirmed in the predicted direction.** Tested against
`PREREGISTRATION_003_early_window.md`, written before the run was started.

## The confirming sample

qwen3-4b-instruct, `Qwen_Qwen3-4B-Instruct-2507-Q5_K_L.gguf`,
`--probe-only --repeats 10 --seed 1312`, card-verified preset.
**173 of 180 generations differ from the seed-77 sample** — genuinely
independent data.

n = 148 correct / 32 incorrect. MDE d ≥ 0.55. Only the three declared signals
were tested.

| signal | role | predicted | run 2 (seed 77) | run 3 (seed 1312) | p | outcome |
|---|---|---|---|---|---|---|
| `first10_max` | **primary** | high=good | +0.784 | **+0.765** | **<0.0001** | **CONFIRMED** |
| `first10_std` | secondary | high=good | +0.707 | **+0.670** | **0.0005** | **CONFIRMED** |
| `phi_first10_mean` | secondary | high=bad | −0.594 | **−0.624** | **0.0014** | **CONFIRMED** |

Effect sizes held to within 0.04 across independent samples. That is not what
a false positive does.

## The finding

For **`Qwen_Qwen3-4B-Instruct-2507-Q5_K_L.gguf`**, the first ten tokens of a
generation predict whether the finished code will pass its tests:

- **`first10_max` +0.77** — correct generations reach a *higher* peak entropy
  in their opening tokens.
- **`first10_std` +0.67** — and vary *more* across those tokens.
- **`phi_first10_mean` −0.62** — and carry *lower* top-1 confidence there.

Together with the separately confirmed `q1_over_mean` (−0.63) and `q_argmax`
(+0.82): a correct generation opens with a brief sharp burst of genuine
uncertainty — the model visibly weighing alternatives — then settles. An
incorrect one opens flat and uniformly committed.

**Early confidence predicts wrongness.** The opposite of the intuition the
field's aggregate measures are built on.

## Why the summary statistics found nothing

On the same data, `max_entropy` gives d = +0.17 (p = 0.39) and `mean_entropy`
d = +0.15 (p = 0.46). A short opening spike followed by a long calm tail
averages to the same number as a flat middling trajectory. The signal is in
the shape of the opening ten tokens, and any statistic that averages over the
whole generation destroys it by construction.

## Scope — deliberately narrow

This applies to **one model, at one size, at one quantization**:
`Qwen_Qwen3-4B-Instruct-2507-Q5_K_L.gguf`, on an 18-task Python bank, at its
card-verified preset.

Quantization is not a footnote here. Entropy is a property of the logit
distribution, and quantization changes that distribution — a Q4 of the same
weights is a different organism for this purpose and is outside this result's
scope. The pipeline now records the exact filename, the detected quantization
tag, and a head+tail file fingerprint in every profile, and refuses to
overwrite a profile produced from a different file.

Granite-4.1-3b shows none of these signals. Under this project's premise that
is a finding about granite, not evidence against this one.

## What makes this credible

1. Discovered on run 1, which both discovered and measured it — so its effect
   sizes were overestimates and were treated as such.
2. Pre-registered before run 3 existed, with directions and a primary endpoint
   named in advance, restricted by `CALIBRATION_KIT_PREREGISTER` so the
   confirming scan could not wander.
3. Confirmed on genuinely independent data — verified generation-by-generation,
   not assumed. The first attempt at a "second sample" was a bit-identical
   replay caused by a missing seed, and was caught and discarded.
4. Corrected for a 43-candidate search when discovered.
5. Held-out validated within a single run: train 0.631 → test 0.707.

## Chain of results, in order

| # | claim | status |
|---|---|---|
| — | entropy level (`max_entropy`, `mean_entropy`) predicts correctness | withdrawn — never tested, was sign-of-mean |
| 001 | qwen shape signal reproduces **on granite** | wrong test; withdrawn as a category error |
| 002 | qwen shape signal reproduces **on qwen** | **confirmed** (`q1_over_mean` p=0.001, `q_argmax` p=0.00005) |
| 003 | early-window + confidence signals reproduce on qwen | **confirmed 3/3** |
| 002-B | pooling across models cancels per-model effects | mechanism shown; needs a second individually-significant model |
