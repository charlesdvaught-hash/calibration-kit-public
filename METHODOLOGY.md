# Calibration Methodology

This document explains what the calibration kit does, what the knobs are,
and how the search/filter/calibrate process works. It's the building-blocks
reference — read this to understand what you're tuning and why.

There are two ways to use the kit:

1. **Runtime proxy** (fastest path): `calibrate setup` + `calibrate proxy`.
   The proxy scores live generations and re-learns from recent work on a
   nightly schedule.
2. **Full calibration** (strongest profile): `calibrate run` sweeps a task
   bank, interventions, and signals to build a profile from scratch.

---

## What this calibrates

The kit measures how a local LLM (GGUF, 3-8B) generates and repairs code.
The pipeline can sweep large candidate spaces -- it may generate 200
candidates to find the one that fixes an obscure Python bug. What
calibration changes is **how efficiently** it searches that space.

Without calibration, the pipeline tests every candidate to find the right
one. With a calibrated entropy signal, it can test the most-likely-wrong
candidates first, bail early on hopeless runs, and cut a 200-candidate
sweep to ~60. The signal doesn't need to be perfect -- it just needs to
separate likely-wrong from likely-right well enough to prioritize.

**What calibration does:**

- Finds which entropy signal (if any) predicts wrongness for this model
- Finds which recovery interventions work and in what order
- Finds the planner->coder channel sweet spot (trace length, prompt vs
  trace vs decompose)
- Estimates compute savings from early-stop

**What calibration does NOT do:**

- Give the model context it doesn't have. If the model can't see the bug,
  no amount of sweeping will produce the right answer. Calibration makes
  the search efficient; it can't manufacture capability.
- Improve multi-turn reasoning over thousands of lines (that's a
  context/RAG problem)
- Calibrate tool use, agentic loops, or long-horizon planning (the kit
  tests code generation and repair, not orchestration)
- Handle tasks with no deterministic pass/fail signal (creative writing,
  design, open-ended exploration)

The pipeline's power is breadth: it can sweep 200 candidates across
temperatures, channels, and intervention strategies. Calibration's power
is efficiency: it tells you which 60 to actually test.

---

## The knobs

These are the variables the calibration can sweep. Each one is a lever
that affects how the model generates, how it recovers from failure, and
how the planner communicates with the coder.

**The sweep discovers values — it does not hardcode them.** The examples
below (Qwen3.5 temp=1.0, Phi greedy, etc.) are illustrations of how
different models need different settings, NOT a list of values to try.
The calibration uses the model's card-recommended values as a starting
point and explores around them. It finds what works for THIS model.

### Sampling parameters (always relevant)

| Knob | What it does | When to sweep | Gotchas |
|---|---|---|---|
| `temp` | Controls randomness. 0.0 = deterministic, 1.0+ = creative | Always -- this is the primary knob | Different models need wildly different temps. The card is the authority. Don't assume. |
| `top_p` | Nucleus sampling -- cuts off low-probability tokens | Sweep alongside temp | Different families have different defaults. Check the card. |
| `top_k` | Limits to top-K tokens | Usually fixed | Some models disable it (top_k=0). Check the card. |
| `min_p` | Minimum probability threshold | Rarely swept | Most small models use 0.0 (disabled). |
| `repeat_penalty` | Discourages token repetition | Usually 1.0 (off) | High values (1.1+) can break code generation by suppressing common tokens. |
| `presence_penalty` | Discourages already-seen tokens | Model-specific | Some models require it (without it, outputs degenerate). Others use 0.0. Check the card. |

**Rule:** Before sweeping any of these, check the model's HuggingFace card.
The card tells you the recommended values. The sweep starts from those
values and explores around them — it does not impose a universal range.
The `CORE_MODEL_CONFIGS.md` file has verified configs for common GGUFs --
check there first to avoid re-verifying a model that's already been looked up.

### Recovery knobs (swept during intervention phase)

| Knob | What it does | How it's set |
|---|---|---|
| `retry_temps` | Temps to try on failure (fresh generation) | Discovered by sweep — starts from card-recommended temp, explores around it |
| `nudge_temp` | Small temp bump for error-feedback retry | Discovered by sweep — model-specific |
| `spike_threshold` | Entropy threshold for "likely wrong" signal | Calibrated from data (not assumed) |
| `tail_tokens` | How many tokens of architect trace to feed coder | Discovered by sweep — the pipeline finds the optimal trace length for this model |
| `thinking_mode` | Whether the model generates reasoning tokens before output | Swept: on vs off (see below) |
| `MAX_RECOVERY_STAGES` | Max interventions per failed task before bailing | 6 (bail condition, not a sweep knob) |
| `MAX_TASKS` | Max tasks per calibration run | 15 (compute budget, not a sweep knob) |

### Thinking vs no-thinking (bandwidth sweep)

Some models can run in two modes:

- **Thinking mode:** the model generates reasoning tokens (often 1000+ tokens)
  before producing its actual output. This can improve reasoning quality but
  consumes massive output budget -- a 4096-token generation might spend most
  of the budget thinking and leave little for code.
- **No-thinking mode:** the model answers directly. Faster, cheaper, uses less
  VRAM for the KV cache, but may produce worse code on complex tasks.

The calibration should test **both modes** on the same model and compare:

1. **Solve rate:** does thinking actually help on these tasks, or does it just
   burn tokens? The answer is model- and task-specific. The sweep finds it.
2. **Token cost:** how many tokens does thinking mode waste per task? The
   cost-per-solve ratio tells you whether thinking is worth the bandwidth.
3. **Entropy signal behavior:** thinking tokens have very different entropy
   profiles than code tokens. The entropy signals calibrated in thinking mode
   may not apply in no-thinking mode, and vice versa. Calibrate separately.
4. **Recovery stage interaction:** if the model thinks before each
   intervention, recovery stages cost more tokens. The bail threshold may
   need to be lower in thinking mode for the sweep to be cost-effective.

**To sweep this:** run the calibrator twice on the same model -- once with
thinking enabled (max_tokens high enough to fit reasoning + code, thinking
block stripping on) and once with thinking disabled (max_tokens at a normal
coding budget, no stripping). Export both analyses and compare. The analysis
from each run is a single-run snapshot for that specific mode -- don't mix
them.

**Bandwidth saving:** if no-thinking mode solves the same tasks at the same
rate with fewer tokens, that's a bandwidth saving with no accuracy loss. The
analysis should note the specific token savings for this model. The exact
ratio is model-specific — the sweep finds it, we don't assume it.

**Important:** calibrate in the same mode you'll deploy in. If your runtime
disables thinking by default, calibrate with thinking off. The entropy
signals, thresholds, and recovery rates are mode-specific.

### What the knobs control

The knobs interact. The calibration doesn't sweep them independently --
it runs the model, observes outcomes, and learns which combinations work.
But the knobs define the space being searched:

- **Temp** affects generation diversity. Higher temp = more varied candidates,
  but also more noise. The calibration finds whether temp diversity helps
  (it sometimes does for logic tasks, rarely for parsing tasks).
- **Nudge temp** is a per-step temp change. Sometimes bumping temp only at
  the error-feedback step helps, while bumping it at the architect-trace
  step hurts. The calibration measures this asymmetry.
- **Tail tokens** controls how much of the architect's reasoning the coder
  sees. Too little = coder lacks context. Too much = coder gets lost in
  reasoning instead of code. The sweep finds the sweet spot.
- **Spike threshold** determines when the entropy signal fires "this is
  likely wrong." Too low = too many false positives (wasted regenerations).
  Too high = misses real failures. The calibration finds the threshold
  that best separates correct from incorrect outputs for this model.

---

## The plan (calibration procedure)

The calibration runs in 4 phases:

### Phase 1: Probe

Run the model on every task in the task suite. Capture:
- Whether the code passes tests (pass/fail)
- The entropy trajectory during generation (per-token entropy, spike
  location, plateau detection)
- Error type if it failed (syntax, name_error, logic, etc.)
- Time and call count

This produces the raw data: which tasks the model gets right, which it
gets wrong, and what the generation looked like in each case.

### Phase 2: Intervention sweep

For every failure from Phase 1, try every intervention in isolation:

1. **test_retry** -- feed test failures back to the model, ask it to fix
2. **temp_retry** -- fresh generation at a different temperature
3. **skeleton_fill** -- two-call split: generate skeleton, then fill bodies
4. **arch_design** -- architect writes a prompt for the coder
5. **arch_trace_short** -- 50-token tail of architect's reasoning trace
6. **arch_trace_long** -- 400-token tail of architect's reasoning trace
7. **decompose** -- architect breaks task into numbered steps

Each intervention is tried independently on each failure. This gives the
coverage matrix: which interventions fix which failures.

### Phase 3: Analysis

From the probe + intervention data, compute:

- **Signal scan, corrected for multiple comparisons.** Every numeric
  statistic the generation pass captured — roughly 170 of them across the
  series below — is tested against the same pass/fail data. See
  "Statistical method" below — this step is where the kit is most likely
  to fool itself, and the correction is not optional.

**What one generation pass captures.** A logits processor sees every
token's full logit vector as it is generated, so all of these come from a
single pass at zero extra GPU cost:

- *top-20-cropped entropy* (isolates true competition between near-ties)
- *full-vocabulary entropy* (tail mass outside the crop is itself a signal)
- *top-1 probability and top1−top2 margin* (commitment)
- *commitment curve*: true probability mass of the top-1 / top-5 / top-20
  tokens, and the tail mass `1 − mass20`
- *KL divergence series*: step-to-step `KL(p_t ‖ p_{t−1})` (belief
  revision), `KL(p_t ‖ uniform)` (normalised competition), and
  `KL(p_t ‖ running centroid)` (excursions from the generation's own mean)
- *sampled-token surprisal and rank*: which token was actually chosen and
  how unexpected it was — taken from the response's `logprobs`, since the
  processor sees the distribution *before* sampling
- *structural-token entropy*: uncertainty leaking into punctuation and
  formatting, kept separate from semantic tokens
- *trajectory shape* over all of the above: windowed means, slopes,
  quartiles, spike counts and locations, oscillation, path ratios

Each per-token series is also stored in the raw run file as a 32-point
downsample, so a statistic invented later can be tested by `reanalyze`
with no GPU time. The scan assumes nothing about direction: a statistic
where *high* means *right* on one model and *high* means *wrong* on
another is a per-model signature, and both directions are tested for.

**What this backend cannot capture.** Everything above is a property of
the output logit distribution. Techniques that read intermediate-layer
hidden states — logit lens, activation probes, linear probes for an
internal "doubt" direction — are not available through llama.cpp/GGUF and
are not claimed. They would require a transformers/vLLM capture path and
are a possible future extension, not a v1 feature.
- **A direction is only reported if it survives testing.** Separation
  alone is not evidence.
- **Coverage matrix:** which interventions recovered which failures,
  including unique coverage (failures only this intervention fixed).
- **Greedy set cover:** the minimum set of interventions that covers the
  most failures, in order. This becomes the recommended intervention order.
- **Per-error-type effectiveness:** which intervention works best for each
  error type (syntax, name_error, logic, etc.).
- **Signal-based failure routing (pre-test):** the per-error-type table
  tells you what to try *once the tests have told you* what kind of failure
  you have. This step goes one level earlier: it splits the failures on
  whichever captured signal best separates their error-type distributions
  (median/mean/midpoint thresholds over every candidate statistic — the
  pass/fail calibrated signal gets no preference, because the best splitter
  is model-specific), then reports each cluster's dominant error types and
  per-intervention recovery rates. The output is a routing rule of the form
  *"if signal X is below T, expect failure modes A/B — try intervention Y
  first,"* usable before a single test executes. Small clusters (<5
  failures) are flagged provisional in the report; the rule is a
  prioritization hint, not a guarantee, and it sits alongside the
  per-error-type table rather than replacing it.
- **Architect spike vs coder quality:** does the architect's entropy spike
  location predict whether the coder will recover?

### Statistical method (why most runs report "none")

This section exists because an earlier version of this kit got it wrong,
and the mistake is easy to make.

**The failure mode.** `entropy_direction` used to be decided by the sign of
a difference in two group means, with no test. If the mean max_entropy of
correct generations exceeded that of incorrect ones, the kit reported
"high=good"; otherwise "high=bad". "none" was reachable only on exact float
equality, so it never happened. A threshold was then fitted to that
direction and shipped. Every entropy finding published before 2026-09-04
came out of that path, and re-testing showed all of them were noise — one
model's documented direction flipped sign on a clean re-run.

**What the kit does now.**

1. **Permutation test.** The observed difference in means is compared
   against 20,000 random relabellings of the same data, with a fixed seed
   so any given dataset yields a reproducible p-value. No scipy dependency.
2. **Minimum effect size.** A difference can be statistically detectable
   and still too small to route decisions on. A direction also has to clear
   a separation floor of 0.08.
3. **Fails closed.** Anything that doesn't clear both is reported as
   `none`, with the ungated sign preserved as
   `raw_direction_before_gating` and explicitly labelled as not a finding.
4. **No threshold without a direction.** A cut point fitted to a
   non-signal is a cut point fitted to noise. The kit also no longer falls
   back to a hardcoded default threshold on insufficient data — that
   handed out an invented number that read as measured.
5. **Multiple-comparison correction.** The scan tests ~170 statistics
   against the same outcome. Keeping whichever clears p<0.05 would find a
   "signal" in pure noise several times per run. Benjamini-Hochberg FDR
   is applied across the whole scan, and a signal is called usable only if
   its adjusted p clears alpha *and* |Cohen's d| >= 0.2. Statistics that
   clear p<0.05 alone but not after correction are listed separately as
   candidates for a pre-registered test — never as findings.

   The trade-off is real: looking at more candidate patterns raises the
   bar each one must clear. That is the correct direction — a tool whose
   selling point is "we find the pattern your model responds to" must pay
   for every place it looked — but it means a `none` verdict after a wide
   scan has earned more confidence than one after a narrow scan, not less.

   **Confirming a candidate on new data.** Set
   `CALIBRATION_KIT_PREREGISTER=signal_a,signal_b` before a run (or
   `reanalyze`) to restrict the scan to exactly those signals. A
   restricted scan is a confirmation, not a second search — it is how a
   candidate found in run 1 gets honestly re-tested on run 2.

   **Signal classes.** Every candidate is one of three kinds: *entropy-based*
   (computed from the logit distribution — the actual wrongness evidence),
   *structural/behavioral* (`n_tokens`, `n_semantic`, `think_frac`,
   `think_boundary` — how long or how "thought-through" the output was), and
   *composite* (a product or ratio of a structural signal with an entropy
   feature, e.g. `think_frac_x_kl_uniform_mean`). A structural signal can
   separate pass from fail for the wrong reason: a generation cut off by the
   token budget scores high on think_frac *because* it was truncated, not
   because the model was uncertain. Structural signals therefore can never be
   shipped as the sole gate — the scan reports the strongest one separately
   as `structural_best` for transparency — while composites remain eligible
   (they carry real entropy content), and structural signals stay available
   for failure-type routing, where splitting failure *modes* is a
   different job than gating on correctness.
6. **Statistical power is reported.** "This model has no entropy signal"
   and "this run was too small to see one" are different answers. Each run
   reports the observed effect size, the smallest effect that sample could
   have detected, and the `--repeats` value that would reach ~80% power.

**Why this matters more here than in most tools.** The kit's selling point
is that it searches a large candidate space for whatever pattern your
specific model responds to. That is exactly the machinery that manufactures
false findings when it is uncorrected. A search tool without a correction
is a random-result generator with good ergonomics.

**Consequence for the default settings.** `--repeats 2` produces 36 probes
and typically 5-11 failures — enough to detect only effects of d >= 1.0.
An entropy claim should not be published from a default-repeats run. Raise
`--repeats` until the report says the run was adequately powered.

**Honest current state (60-task bank, 2026-09-05).** On the current bank,
`max_entropy` high=bad survives correction for qwen3-4b-instruct at
record level (d = −0.94, adjusted p = 0.008) and nothing survives for
granite-4.1-3b. The earlier 18-task early-window finding did not
replicate across task sets — see `research/OUTCOME_005`.

**Two holdouts, two questions — reliability and validity.** The
record-level held-out split is a *reliability* check: does this signal
separate *new generations* of tasks the model has already seen? A held-out
record can come from the same task as a training record, so a signal that
detects task identity (not wrongness) passes while being useless on a new
task — it repeats, but it doesn't generalize. The profile therefore also
runs `task_holdout_validation`, the *validity* check: whole tasks are
excluded from selection and fitting, then scored — plus a
`transfer_estimate` that takes the signal the full run selected and
re-scores it on held-out tasks across 300 random task splits. On the
current runs: qwen's selected signal **does** transfer (0.73 mean
balanced accuracy on unseen tasks, above chance in 92% of draws), while
granite's task-selected signal went below chance (0.87 train → 0.47
test) — the failure mode this check exists to catch. With ~10 failing
tasks the selection path is low-power: a pass is meaningful, a fail means
"not proven", not "proven false"; the transfer estimate is the usable
number at this scale.

The filter for both checks: *what observable signature would this claim's
failure leave, and did you agree to look for it before you had the result?*
If the failure leaves no trace you pre-committed to inspect, you measured
agreement and called it truth. The permutation test, BH correction, and
both holdouts are pre-committed checks — they were decided before the
result was known, not selected after.

**What the disagreement means.** Pool those three models' records together
and the per-model effects cancel — `spike_relative_pos` runs +0.196, +0.306
and −0.393 across them and pools to d = −0.012, p = 0.925. A study that
aggregates across models and looks for a rule that transfers would report no
pattern here, and would be right about the aggregate and wrong about every
model in it. See `research/FINDING_002_pooling_artifact.md`, including what
that evidence does not yet establish.

**Why the rigor above is not in tension with per-model claims.** All three
checks — permutation test, correction, held-out split — run inside a single
model's own data and never appeal to another model. They exist so that a
per-model claim can still be wrong. Without them, "every model is different"
would mean every model gets whatever story its noise suggests.

The intervention and recovery layer is unaffected by any of this: recovery
rates are direct measurements of "did this repair strategy fix this failure",
not correlational claims, and they remain the kit's most solid output.

### Architect calibration (when an architect model is provided)

The architect is itself a full calibration target. When you provide an
architect GGUF via `--architect`, the same entropy trajectory capture
runs on the architect's generations:

- **Architect entropy signals:** the same full set of series (entropy,
  margin, commitment mass, KL, surprisal — plateau, spike position, etc.)
  is computed on the architect's trace. These can predict whether the architect's output (the prompt or
  trace it hands the coder) will be useful -- before the coder even runs.
- **Architect plateau and first-spike trajectory:** if the architect's
  entropy plateaus early, it may be producing a generic, low-information
  trace. If it spikes late, it may be still reasoning when the trace is
  cut off. The calibration finds which patterns predict good coder
  outcomes for this specific architect model.
- **Cross-signal (architect spike -> coder recovery):** the architect's
  entropy spike quartile (0=head/early, 3=tail/late) is correlated with
  whether the coder recovered. If recovered cases cluster in a different
  quartile than not-recovered cases, the architect's spike location
  predicts coder success -- you can filter architect traces before
  feeding them to the coder.
- **Channel sweep:** the architect's output is delivered to the coder
  through 4 channels (design prompt, short trace, long trace, decompose).
  Coverage is measured per channel. A frontier planner may produce traces
  that help the coder 71% of the time, while a small local planner's
  traces may only help 12%. Calibration finds which one you have.

To calibrate the architect independently (without a coder), just run the
calibrator with the architect as the `--model`:

```bash
python _calibrate_pipeline.py --model your-architect.gguf
```

This produces a `_calibration_profile_<architect-label>.json` that you
can pass to the exporter via `--architect`:

```bash
python export_playbook.py --profile _calibration_<coder>.json \
    --architect _calibration_<architect>.json --output AGENTS.md
```

### Phase 4: Export

Render the findings into an AGENTS.md playbook using `export_playbook.py`.
The playbook is a single-run snapshot -- it reports what this calibration
found, not a historical trend.

---

## How search/filter/calibrate works

### Search

The intervention sweep searches the space of recovery strategies. Each
intervention is a different way to recover from a failure:

- **Regeneration strategies:** fresh gen at different temp, error feedback,
  skeleton-then-fill
- **Architect strategies:** architect writes prompt, architect trace
  (short/long), architect decomposes
- **Repair strategies:** SEARCH/REPLACE patches at different architect
  presets (thinking, halfway, coding, instruct)

Every strategy is tried on every failure, independently. This is an
exhaustive search of the recovery space, not a greedy walk.

### Filter

After the search, signals are filtered by reliability:

- **Entropy signals** are filtered by separation score. A signal with
  separation < 0.5 is marked "NOT reliable" -- it doesn't consistently
  separate correct from incorrect outputs for this model. The playbook
  lists these under "what didn't work" so the buyer doesn't use them.
- **Interventions** are filtered by recovery rate. An intervention that
  recovered 0 failures is marked "skip this stage for this model."
- **Channels** (trace vs prompt vs decompose) are filtered by coverage.
  A channel that hurt (decompose broke tasks the model already solved)
  is flagged with a warning.

### Calibrate

Thresholds are calibrated per-model, never assumed:

- **Entropy threshold:** found by exhaustive search over the midpoints
  between adjacent observed values, keeping the split with the best
  balanced accuracy. An earlier version of this document described a
  `(passed_mean + failed_mean) / 2` midpoint-of-means formula; that is
  not what the code does and has not been for some time. The search
  handles skewed and overlapping distributions, where the midpoint of
  two means can sit outside any useful cut point.
- **Direction:** learned from the data, and reported only if it survives
  the significance gate above. Canonical values are **`high=bad`** (high
  values predict failure) and **`high=good`** (high values predict
  correctness), or `none`.

  > **Vocabulary note.** Older code and older versions of this document
  > used `higher_means_bad` / `higher_means_good`. Both spellings appear
  > in profiles written at different times. Everything that compares a
  > direction must go through `normalize_direction()` in
  > `_calibrate_pipeline.py`. This is not pedantry: the compute-savings
  > estimator in `export_playbook.py` compared against the old spelling
  > only, so it silently reported zero savings for every model ever
  > calibrated until 2026-09-04.

- **Operating point:** a direction and a threshold are not yet a rule.
  The same signal is cut differently depending on the job -- see
  "Choosing an operating point" below.
### Choosing an operating point

A direction and a threshold describe a *curve*, not a decision. The same
signal is cut in different places depending on what you want from it, and the
pipeline reports each cut with what it costs:

| job | rule | judged by |
|---|---|---|
| **catch wrong** | regenerate when the signal is on the bad side | failures caught, correct work wrongly discarded |
| **trust right** | ship without testing when the signal is on the good side | how much output it covers, how pure that zone is |
| **both** | two ordered cut points with a band between | all of the above, plus how much still needs testing |

These are one fit read at different points, not three findings. The two-sided
rule is fitted **jointly** so its cut points are ordered by construction —
fitting the two sides independently produces overlapping zones, where a value
is simultaneously "ship untested" and "regenerate".

### What a signal is worth depends on when it is readable

This matters more than effect size for anything compute-related.

- `first10_max`, `phi_first10_mean`, `early_slope` and the other early-window
  statistics are computable **after ten tokens**. A bail rule on one of these
  aborts a doomed generation before most of its tokens are spent.
- `q_argmax`, `osc_rate`, `tail_entropy` and every whole-trajectory statistic
  are only available once the generation is **finished and already paid for**.
  A rule on one of these can save you running the tests. It cannot save you
  the generation.

So a weaker signal readable at token 10 is often worth more than a stronger
one that arrives at the end. `signal_availability()` tags each statistic, and
the savings estimate prices them differently. Savings are computed from the
run's own measured generation lengths and failure rate — not from a fixed
assumed fraction.

- **Intervention order:** learned via greedy set cover. The intervention
  that covers the most new failures goes first, then the one that covers
  the most remaining, etc.
- **Tail length:** learned from the trace sweep. Short (50) vs long (400)
  tail coverage is compared directly.

### Mid-flight optimization

The adaptive calibrator (`_calibrate_adaptive.py`) doesn't wait until the
end to start learning. It:

1. **Runs each task once.** No repeats of winners -- if the model solves
   a task on the first try, move on.
2. **Stops when it has enough data.** Once it has `MIN_FAILURES=2` failures
   and `MIN_SOLVES=2` solves, it has enough signal to calibrate. No need
   to run all 15 tasks.
3. **Reorders stages after each sample.** After every task, it recalculates
   per-stage effectiveness and reorders the recovery stages. If
   `errors_nudge` solved 2/3 and `trace` solved 0/3, `errors_nudge` moves
   to the front.
4. **Bumps hard tasks up.** Tasks that needed recovery get priority in the
   plan -- they're where the model struggles, so they're where calibration
   data is most valuable.
5. **Bails early on hopeless tasks.** If the test gap is >= 2 after
   non-SR stages, bail (0% solve rate at gap >= 2 across all tested
   models). Don't waste compute on tasks that won't recover.

---

## Why no universal config exists

The same calibration pipeline produces opposite conclusions for different
models:

| Finding | Granite 4.1 3B | Qwen3-4B-Instruct |
|---|---|---|
| Best entropy signal | head_entropy (separation 0.91) | none (separation 0.00) |
| Entropy direction | higher = wrong | n/a -- doesn't work |
| Best recovery stage | errors_nudge (33%) + bounce (25%) | none recovered (0%) |
| Converged? | yes | no (only 1 failure) |

Same tasks, same architect, same pipeline. Opposite results. This is why
the kit calibrates per-model rather than shipping a universal config.

The same pattern holds for interventions:

| Intervention | Effect on Phi-4-mini | Effect on Agent007 |
|---|---|---|
| Decompose on math_eval | 2/4 -> 4/4 (helped) | 0/4 -> 1/4 (barely) |
| Decompose on json_flatten | 4/4 (no change) | 4/4 -> 1/4 (hurt) |
| Decompose on config_parser | 3/3 -> 0/3 (hurt) | 3/3 -> 1/3 (hurt) |

Decompose is a double-edged sword. It helps on hard logic tasks the model
can't do monolithically, but hurts on tasks the model can already do by
confusing it with unnecessary structure. The calibration detects this
per-model and per-task.

### Inverted entropy signals (some models are confidently wrong)

Most models follow the intuition that high entropy = uncertainty = likely
wrong. Granite, Qwen3.5, and most models in our testing show
`higher_means_bad` -- high entropy during generation predicts failure.

**But some models are confidently wrong.** Phi-4-mini-instruct, for example,
produces low-entropy (high-confidence) outputs even on hard tasks it gets
wrong. For Phi, low entropy does NOT mean "likely correct" -- it means
"the model is sure of itself, regardless of whether it's right." The
entropy signal is inverted: `higher_means_good` (higher entropy actually
correlates with correct outputs, because it means the model is genuinely
engaging with the problem rather than confidently producing garbage).

This is why the calibration **learns direction from data** rather than
assuming. The exporter renders whatever direction the data shows:

- Granite: `higher_means_bad` (high entropy = wrong) -- the normal case
- Phi-4-mini: `higher_means_good` (high entropy = correct) -- inverted
- Qwen3-4B-Instruct: `none` (entropy doesn't separate at all)

**If your playbook says `higher_means_good` for a model, do not assume
this is a bug.** It means the model is confidently wrong on hard tasks.
The actionable guidance is inverted too: test the *lowest* entropy
candidate first (it's most likely wrong), not the highest. The exporter
handles this automatically -- the direction in the playbook matches the
data, and the instructions adapt to the direction.

---

## Compute savings: how early-stop works

When the entropy signal works (separation > 0.5), it can predict wrongness
*before* testing. This enables early-stop:

1. Model generates code. Entropy trajectory is captured during generation.
2. If the calibrated signal (e.g., head_entropy) exceeds the threshold,
   the generation is flagged as "likely wrong."
3. Instead of running all 6 recovery stages, run only 2-3 (the highest-
   yield ones), then bail.

The savings depend on how accurate the signal is:

- **Granite:** head_entropy at 0.059 properly flags ~70% of wrong answers
  with ~22% false-positive rate. Early-stop saves ~40% of intervention
  compute on flagged-wrong tasks.
- **Qwen3-4B-Instruct:** no signal works. Early-stop is not possible.
  You must test every candidate -- entropy gives you no prioritization.

The playbook reports the specific savings estimate from the calibration
data, including false positives (correct answers incorrectly flagged)
and false negatives (wrong answers not flagged).

---

## Re-calibrating

The playbook is a snapshot. To re-calibrate with different tasks, a
different architect, or more repeats:

```bash
# Full pipeline (sweeps all interventions per failure)
python _calibrate_pipeline.py --model your-model.gguf --architect arch.gguf --repeats 5

# Adaptive (minimum compute -- stops when enough data)
python _calibrate_adaptive.py

# Export the new profile
python export_playbook.py --profile _calibration_<label>.json --output AGENTS.md
```

More repeats = more data = higher confidence, but more compute. The
playbook includes a caveat when calibrated on fewer than 10 failures:
"findings are directional, not statistically confirmed."

---

## The task bank

There is one task bank and every run uses all of it. There is no suite to
choose: the whole point of the bank is sample size, and selecting a subset
would only shrink it.

| Kind | Count | What it tests |
|---|---|---|
| Single-function | 46 | Algorithmic coding graded by exact-value tests — string and list manipulation, parsing, matrices, graphs, dynamic programming, formatting |
| Multi-file wiring | 14 | Wiring modules together, plus SWE-lite bug fixes: `filter`, `report`, `cache`, `validator`, `pipeline`, `merger`, `counter`, `scheduler`, `converter`, `indexer`, `api_client`, `fix_offbyone`, `add_errorhandling`, `refactor_rename` |
| **Total** | **60** | |

The single-function tasks live in `_task_bank.py`; the original four are in
`_arch_skel_hard.py` and the wiring tasks in `_multifile_assembly.py`.

### Why the count is the number that matters

At temperature 0 a model is deterministic. Every repeat of a task returns
the identical generation, so `--repeats` produces copies, not samples, and
the analysis deduplicates them before computing anything. The number of
independent observations a run can ever have is therefore the number of
tasks.

This is not a detail. At 18 tasks and a ~20% failure rate a run sees about
4 failures — below the 8-per-outcome floor the rule fitter needs, and far
below what a signal test can resolve. The bank is sized so that a run has
enough failures for its own statistics to mean something:

| Tasks | Failures at ~20% | What that supports |
|---|---|---|
| 18 | ~4 | Nothing. Below the fitter's floor. |
| 60 | ~12–16 | Cross-validated rule fitting, with the folds honest |
| 110 | ~30 | Comfortable margin; stable signal selection across folds |

If your model has a much lower failure rate than 20%, the same arithmetic
applies to it and the run will say so: the report's power section gives the
observed effect, the smallest effect the run could have detected, and what
it would take to settle the question.

### Ground truth is verified, not assumed

Every single-function task in `_task_bank.py` ships with a reference
implementation, and `python _task_bank.py` runs each reference against that
task's own tests. A task whose expected value is wrong would be recorded as
a model failure and would corrupt every statistic derived from it, silently.
The validator is what rules that out; run it after editing or adding a task.

---

## Runtime proxy and continuous re-calibration

The same signals, thresholds, and intervention ordering can be used on live
generations through the OpenAI-compatible proxy (`calibrate proxy`).

- **Setup:** `calibrate setup --profiles-dir <path>` auto-detects a local
  backend, matches a profile, and writes a `settings.json`.
- **Recording:** the proxy injects `logprobs` into every request and appends
  the entropy trajectory plus verdict to a JSONL log.
- **Live verdicts:** each response carries `X-Calibration-Verdict` and the
  `calibration` payload, which now includes `intervention_plan` — the ranked
  escalation order plus conditional signal-failure routing rules.
- **Nightly re-learn:** `calibrate proxy --reanalyze-at 02:00 --window-tasks
  200` re-runs the calibration pipeline on the last 200 unique tasks every
  night, promoting a new profile only if it is no worse on held-out data. The
  fingerprint drifts with the actual task pool.

### Adding your own tasks

Append a dict to `FUNCTION_TASKS` in `_task_bank.py` with `id`, `filename`,
`func_name`, `desc`, `tests`, and `reference`, then run `python
_task_bank.py` until it passes. Two rules matter more than the rest:

- **The `desc` must fully determine the behaviour every test checks.** If a
  test probes an edge case the description does not answer, the resulting
  failure measures your prompt, not your model, and it becomes noise in
  every statistic.
- **Adding tasks invalidates existing checkpoints**, by design — the task
  set is part of the checkpoint signature, so a resumed run can never mix
  two different banks.
