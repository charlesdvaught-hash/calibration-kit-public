# Outcome 002 — qwen's shape signal replicated

**Primary endpoint confirmed.** Tested against
`PREREGISTRATION_002_qwen_confirmation.md`, written before the run existed.

## First: the run that wasn't

The initial attempt returned exactly 147/180 passed, matching the original.
Checking, all **180 of 180 probes were bit-identical** — same generated code,
same entropy values, same pass/fail. `load_model()` passed no seed, so
llama.cpp used a fixed default: repeats *within* a run vary, but re-running
the same command replays the identical generations.

That attempt confirmed nothing, and the bug it exposed is worse than a broken
experiment — any buyer re-running to check stability would get a perfect match
and conclude their signal was rock solid, having re-read the same data.
Replication was impossible and nothing said so. `--seed` is now a first-class
flag, recorded in the profile and part of the checkpoint signature.

## The real confirmation

`--probe-only --repeats 10 --seed 77`, card-verified preset, 18-task bank.
**167 of 180 generations differ from run 1; 14 probes flipped outcome.** The
matching 147/180 headline was coincidence — an illustration of how an
aggregate can be stable while everything under it moves.

n = 147 correct / 33 incorrect. MDE d ≥ 0.54. Only the three declared signals
were tested.

| signal | role | predicted | run 1 d | run 2 d | p | outcome |
|---|---|---|---|---|---|---|
| `q1_over_mean` | **primary** | high=bad | −0.665 | **−0.630** | **0.0010** | **CONFIRMED** |
| `q_argmax` | secondary | high=good | +0.634 | **+0.821** | **0.00005** | **CONFIRMED** |
| `q_early_drop` | secondary | high=bad | −0.636 | −0.357 | 0.0565 | right direction, misses |

Effect sizes **held** rather than collapsing. That is the behaviour of a real
effect, and precisely what the original "d = +0.61 from five failures" failed
to do when it was properly powered.

Held-out validation on this sample: selected `q_argmax` on 126 training
records, scored on 54 it never saw — balanced accuracy **train 0.631 → test
0.707**.

## The finding

**qwen3-4b-instruct has a usable entropy-shape signal**, replicated across two
independent samples, pre-registered, corrected for a 22-candidate search, and
held-out validated. Granite-4.1-3b does not have it.

Both statements are findings. Under this project's premise the disagreement
between them is the product; it was never evidence against either.

## Part B — exploratory scan (leads, declared as such in advance)

Full scan of all 43 candidates on the seed-77 sample, BH-corrected. Five
survive:

| signal | d | adjusted p | status |
|---|---|---|---|
| `q_argmax` | +0.821 | <0.0001 | confirmed above |
| `first10_max` | +0.784 | <0.0001 | **lead** |
| `first10_std` | +0.707 | 0.0029 | **lead** |
| `q1_over_mean` | −0.630 | 0.0108 | confirmed above |
| `phi_first10_mean` | −0.594 | 0.0172 | **lead** |

Two of the three leads are first-ten-token window features and one is top-1
confidence — both families added in response to a direct question about
whether first-token trajectory carries what the level does not.

**What they say.** Correct generations reach a *higher* entropy peak in their
first ten tokens, *vary more* across them, and carry *lower* top-1 confidence
there — while their first quarter sits *low* relative to their own mean. A
correct generation opens with a brief sharp burst of genuine uncertainty and
then settles; an incorrect one opens flat and uniformly committed. **Early
confidence predicts wrongness.**

This also explains the null results on `mean_entropy` and `max_entropy`: a
short opening spike followed by a long calm tail averages to the same value as
a flat middling trajectory. The signal is in the shape of the opening, and
summary statistics destroy it by construction.

Confirmation of the three leads is pre-registered in
`PREREGISTRATION_003_early_window.md` against a third sample at `--seed 1312`.

## Scope

Everything above concerns **qwen3-4b-instruct**, one 18-task Python bank, one
card-verified preset. None of it is claimed to transfer, and granite's null
result is not a mark against it.
