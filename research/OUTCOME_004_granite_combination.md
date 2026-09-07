# Outcome 004 — granite's result is withdrawn: pseudo-replication

**The pre-registered test could not be run. Every granite statistic reported
before this file is withdrawn.**

## What happened

Run A (`--seed 4001`) and Run B (`--seed 4002`) returned **byte-identical
output on all 216 generations**. Investigating why exposed a deeper problem
than a seed that didn't take.

`granite-4.1-3b` runs at **temp=0.0** — greedy decoding, correctly taken from
IBM's own card, whose usage example passes no sampling arguments. A greedy
model is deterministic, so:

- the seed has no effect, and Run B is not an independent sample; and
- more importantly, **`--repeats` produces copies, not samples.**

| run | probe rows | unique generations | duplication |
|---|---|---|---|
| granite, repeats 12 | 216 | **24** | **9.0×** |
| granite, repeats 6 (earlier) | 108 | **24** | 4.5× |
| qwen, repeats 10 (temp 0.7) | 180 | 155 | 1.2× |

Twelve of eighteen tasks produced identical output on every single repeat.

## Why this invalidates the result

Every statistic treated 216 rows as 216 independent observations when there
were 24. Duplicating an observation nine times adds no information but shrinks
a p-value dramatically. Worse, cross-validation splits *rows*, so exact copies
of training rows landed in the test folds — the CV was measuring memorisation
and reporting it as generalisation.

**The label-shuffle null did not catch this, and could not.** Shuffling labels
destroys the correspondence between duplicated rows and their shared label, so
shuffled runs land at chance while the real result stays inflated. The null
tests whether a *relationship* exists, not whether the observations are
independent. That is a real limitation of the guard, found the hard way.

## Granite, analysed correctly

Deduplicated to unique generations: **24 generations, 8 failures.**

| | reported before | after deduplication |
|---|---|---|
| combination CV balanced accuracy | 0.862 | **cannot run** (needs 12+ failures, has 8) |
| `osc_rate` univariate | d=1.123, adjusted p≈0.0000 | clears p<0.05 alone, **fails correction** across 45 tests |
| `max_entropy` direction | none | none (p=0.878) |
| held-out validation | — | cannot run (6 train / 2 test failures) |

Seven statistics — `osc_rate`, `n_spikes`, `late_vs_early_half`,
`spike_height`, `spike_token_idx`, `total_variation`, `osc_sign_changes` —
clear p<0.05 individually and none survive correction. With 45 candidates
that is what noise looks like.

**Granite has no usable signal, and has never had a valid analysis.** Its
earlier "no signal" conclusions happened to be directionally right, but they
were computed on inflated n too.

## Qwen is unaffected

Sampling at temp=0.7 produced genuine variation: 155 unique of 180 rows,
1.2× duplication. Re-analysed on unique generations only (155 generations,
29 failures):

| | before dedup | after dedup |
|---|---|---|
| combination CV balanced accuracy | 0.757 | **0.768** |
| held-out (train → test) | 0.631 → 0.707 | **0.705 → 0.839** |
| selected signal | `first10_max` | `first10_max` |
| null | beats 40/40, p=0.024 | **beats 40/40, p=0.024** |

Every confirmed qwen finding stands.

## The structural limit this exposes

**The kit cannot calibrate a deterministic model with an 18-task bank.** At
temp=0 the ceiling is one generation per task — 18 observations, of which
perhaps 5 fail. No amount of `--repeats` changes that, and the flag silently
implies otherwise.

Three honest options for such a model, none free:

1. **More tasks.** The only real fix. Statistical power on a greedy model
   comes from task count alone.
2. **Run it off-card at temp>0.** Produces variation, but stops measuring the
   model as its vendor specifies it — a different subject.
3. **Say so.** The kit now detects the condition, warns loudly, deduplicates
   before every statistic, and reports how many unique generations it actually
   had.

Option 3 shipped. Option 1 is the roadmap item.

## Fixes shipped with this outcome

- `deduplicate_probes()` collapses byte-identical generations; **all** phase-3
  statistics run on unique generations.
- Profiles carry `sampling_independence`: row count, unique count, duplication
  factor, and a `deterministic` flag.
- A loud warning at run time and a `!! SAMPLING WARNING` block in the report
  when duplication exceeds 40%, stating plainly that more repeats will not add
  power on this model and more tasks will.

## Status of Pre-registration 004

**Not testable as written.** Its Run B could not be an independent sample,
because no independent sample of a greedy model can be produced by changing a
seed. The primary endpoint is neither confirmed nor refuted — the experiment
was impossible, and the pre-registration was written without noticing that
granite's own preset made it so.
