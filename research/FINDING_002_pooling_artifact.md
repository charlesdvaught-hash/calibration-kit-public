# Finding 002 — WITHDRAWN as a research goal

**Status: withdrawn 2026-09-04. Not because it was disproven — because it was
the wrong thing to chase.**

## What this file used to argue

That per-model signals pointing in opposite directions cancel when pooled, and
that this explains why aggregate studies report no usable signal in small
models. It presented a table of three models' effect sizes and their pooled
result.

## Why it is withdrawn

Two reasons, and the second matters more.

**1. The evidence is gone.** The table used granite and mini-coder numbers that
are now withdrawn — granite for 9x pseudo-replication (see
`OUTCOME_004_granite_combination.md`), mini-coder for being hopelessly
underpowered at 11 failures. Only qwen has a valid analysis. One model cannot
demonstrate cancellation.

**2. It is the wrong goal.** Proving the pooling artifact requires finding the
*same statistic* behaving oppositely across models. That is still a search for
shared structure — universality with a minus sign in front of it. It smuggles
back the assumption this project exists to reject: that models should be
compared on a common axis at all.

The claim this project actually makes is narrower and already established:
**usable signals exist for some models, they must be found against that model's
own right and wrong, and nothing is claimed to transfer.** Qwen demonstrates
that. A second model would demonstrate it again, independently — not jointly.

## What replaces it

Nothing needs to. The explanation for why aggregate studies miss these signals
does not require a cross-model experiment, because the mechanism is visible
*within a single model*: on qwen's own data, `first10_max` separates at d=+0.77
while `max_entropy` and `mean_entropy` — the statistics that get reported —
separate at +0.17 and +0.15. A short opening spike followed by a long calm tail
averages to the same number as a flat middling trajectory.

**The averaging destroys the signal before any pooling happens.** That is
sufficient, it is demonstrated on one model with three independent samples, and
it needs no comparison to any other model.

## The rule this leaves behind

Do not spend GPU time comparing models to each other. Spend it making the
per-model machinery work on more models — which currently means expanding the
task bank, the one constraint that locks out every deterministic model
regardless of how good the statistics are.
