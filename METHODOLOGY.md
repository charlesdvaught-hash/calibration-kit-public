# Calibration Methodology

This document explains what the calibration kit does, what the knobs are,
and how the search/filter/calibrate process works. It's the building-blocks
reference -- read this to understand what you're tuning and why.

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

- **Entropy signal ranking:** 9 signals (head_entropy, max_entropy,
  mean_entropy, n_tokens, n_semantic, spike_position, spike_position_pct,
  plateau_start, plateau_start_pct) ranked by how well they separate
  correct from incorrect outputs. The best signal, its direction
  (higher_means_bad or higher_means_good), and its threshold are
  extracted.
- **Coverage matrix:** which interventions recovered which failures,
  including unique coverage (failures only this intervention fixed).
- **Greedy set cover:** the minimum set of interventions that covers the
  most failures, in order. This becomes the recommended intervention order.
- **Per-error-type effectiveness:** which intervention works best for each
  error type (syntax, name_error, logic, etc.).
- **Architect spike vs coder quality:** does the architect's entropy spike
  location predict whether the coder will recover?

### Architect calibration (when an architect model is provided)

The architect is itself a full calibration target. When you provide an
architect GGUF via `--architect`, the same entropy trajectory capture
runs on the architect's generations:

- **Architect entropy signals:** the same 9 signals (head_entropy,
  plateau_start, spike_position, etc.) are computed on the architect's
  trace. These can predict whether the architect's output (the prompt or
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

- **Entropy threshold:** computed using the midpoint formula
  `(passed_mean + failed_mean) / 2`. This places the threshold between
  the correct and incorrect distributions.
- **Direction:** learned from the data. If failed outputs have higher
  entropy than correct outputs, direction is `higher_means_bad`. If
  correct outputs have higher entropy, direction is `higher_means_good`.
  If there's no difference, direction is `none` -- entropy doesn't work
  for this model.
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

## Task suites

The kit includes several task suites. Use the one closest to your
application:

| Suite | Tasks | What it tests |
|---|---|---|
| Core 12-task | math_eval, text_stats, csv_counter, json_flatten, config_parser, stack_class, string_transform, prime_sieve, matrix_ops, date_utils, compress_string, binary_search | Single-function algorithmic coding |
| Hard 10-task | text_stats, compress_string, rle_decode, balanced_delimiters, merge_intervals, normalize_path, missing_ranges, stable_unique, version_compare, deep_get | Harder single-function tasks (where failures are more likely) |
| Multi-file wiring (14) | filter, report, cache, validator, pipeline, merger, counter, scheduler, converter, indexer, api_client, fix_offbyone, add_errorhandling, refactor_rename | Wiring modules together + SWE-lite bug fixes |
| SWE-bench Lite (6) | astropy, django (4 instances) | Real-world bug fixes from open-source projects |

The multi-file and SWE-bench suites are harder and produce more failures
-- which means more calibration data. If your model aces the core 12-task
suite, switch to the hard or multi-file suite to get failures to calibrate
on.
