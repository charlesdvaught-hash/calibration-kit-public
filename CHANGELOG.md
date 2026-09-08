# Changelog

## 2026.09.07 (audit) — probe fixes cross-checked against the full kit

The probe's statistics were rewritten with stricter standards. Each fix was
cross-checked against the full calibration kit to confirm the pro
implementation didn't carry the same bug. Results are in
`public_probe_audit_checklist.md`.

### Fixes in the probe
- **Cohen's d** — pooled within-group SD (was grand-mean, deflated all |d|)
- **Quartile boundaries** — spike_quartile now matches quartile_entropies chunks
- **Failure classification** — per-failure majority vote with explicit categories
- **Unclosed thinking** — truncated thinking blocks return empty, not graded as code
- **Structural-signal gating** — n_tokens/think_frac can't be the sole gate

### Found in the pro kit during cross-check
- Cohen's d had the same denominator bug (fixed in the pro kit)
- spike_quartile/plateau_start_quartile had the same boundary bug (fixed)
- test_function_code had no TimeoutExpired catch (fixed)
- classify_error used first-match on joined text (upgraded to majority vote)
- extract_code kept truncated thinking as code (fixed)

### Added to both
- Composite candidates (n_tokens/think_frac ×/÷ entropy) under BH correction
- Structural-signal policy: reported as `structural_best`, never the sole gate
- Failure-type histogram + all-same-type warning

---

## 2026.09.07 — the product becomes a runtime calibration layer

This release changes what the kit is *for*. It began as an offline profiler
that ran a task bank and exported an `AgentAnalysis.md`. That still exists,
but the main path is now:

1. Install the binary.
2. Run `calibrate setup` once. It finds your local backend, matches a profile,
   and prints the harness command.
3. Run `calibrate proxy`. It sits between your harness and the backend,
   records every request, scores live generations, and re-learns from the
   last window of work every night.

The kit is now a closed-loop runtime layer, not just a report generator.

### What's new in this release

**1. Self-setup wizard.** `calibrate setup` auto-detects local OpenAI-compatible
backends on common ports (`8080` llama-server, `1234` LM Studio, `11434`
Ollama, `8000` vLLM), matches the loaded model to a profile, writes a
`settings.json`, and prints the exact start command for Aider, Continue, Cline,
LocalHarness, or mini-swe-agent.

**2. Rolling-window nightly reanalysis.** `calibrate proxy --reanalyze-at 02:00
--window-tasks 200` keeps the last 200 unique tasks and re-runs the calibration
pipeline on that window every night. `--window-hours` adds an age cutoff. The
profile fingerprint drifts with the actual task pool.

**3. Intervention plan in every response.** The proxy's `calibration` verdict
now includes `intervention_plan`: the ranked escalation order plus conditional
`signal_failure_routing` rules with predicted error types and recovery rates.
Harnesses can read the full "if it fails, try X first" plan without touching
headers.

**4. Backend auto-detection.** `BackendProbe` tries the configured upstream,
then common local endpoints, so `calibrate proxy` with no explicit `--upstream`
discovers a running backend.

**5. Exact model matching with path stripping.** Profiles now match even when
backends report the full GGUF path as the model id; harmless path/case/punctuation
differences are normalized but the underlying identity must still match exactly.

**1. Self-setup wizard.** New `calibrate setup` command auto-detects a local
OpenAI-compatible backend on common ports (`8080` llama-server, `1234` LM
Studio, `11434` Ollama, `8000` vLLM), matches the loaded model to a profile,
writes a `settings.json`, and prints the exact command for Aider, Continue,
Cline, or the generic proxy start. One run of `setup` plus one run of `proxy`
gets a harness calibrated and recording.

**2. Rolling-window nightly reanalysis.** `calibrate proxy --reanalyze-at 02:00
--window-tasks 200` keeps only the most recent 200 unique tasks and re-runs
the calibration pipeline on that window every night. `--window-hours` adds an
age cutoff. The profile fingerprint now drifts with the user's actual recent
task pool instead of growing stale on the whole log.

**3. Intervention plan in every response.** The proxy's `calibration` verdict
now includes `intervention_plan`: the ranked escalation order from
`recommended_intervention_order` plus the conditional `signal_failure_routing`
rules with predicted error types and recovery rates. Harnesses that read the
response can see the full "if it fails, try X first" plan.

**4. Backend auto-detection.** `BackendProbe` now tries the configured
upstream, then the common local endpoints, before giving up. `calibrate proxy`
with no explicit `--upstream` will discover a running backend.

**5. Verdict-level profile matching fix.** Model identity matching now strips
Windows/Unix path components before comparing, so `llama_cpp.server` and other
backends that return a full GGUF path as the model id still match their
profile exactly.

## 2026.09.06 — signal-based failure routing, 224-task HumanEval bank, Qwen3-8B calibration

**1. Signal-based failure routing (pre-test).** New Phase-3 analysis step:
`signal_failure_routing` in the profile. It splits the run's failures on
whichever captured signal best separates their error-type distributions
(median/mean/midpoint thresholds over every candidate — the pass/fail
calibrated signal gets no preference, since the best splitter is
model-specific), then reports each cluster's dominant error types and
per-intervention recovery rates. The output is a pre-test routing rule:
*"if the signal reads this way, expect these failure modes — try this
intervention first"* — usable before any test executes. Distinct from the
existing per-error-type table, which applies only after tests have run.
Rendered in the text report, the HTML report, and the exported
AgentAnalysis playbook.

**2. HumanEval-derived task bank.** `_humaneval_convert.py` converts the
OpenAI HumanEval dataset (MIT-licensed) into the kit's task format, with
every converted task proven against its canonical solution before use.
Combined with the built-in bank: 224 tasks (164 HumanEval + 60 built-in).
Provenance, license, and the contamination caveat are documented in
`CUSTOM_TASKS.md`.

**3. Qwen3-8B Q5_K_M thinking-mode calibration** — the largest bank run so
far. 224 probes, 37 failures, 111 intervention runs, 17 recoverable.
Signal: `think_frac` (fraction of generation spent in reasoning tokens),
high=good, d=+2.072, permutation p=0.000, held-out balanced accuracy 0.809
record-level / 0.773 task-level, transfer 0.838 mean across 300 task
splits (above chance in 100%). Failure routing on `n_tokens` splits
"didn't engage" failures (syntax/empty output) from "thought but wrong"
(assertion/logic). A prior non-thinking probe of the same model was
contaminated by spontaneous-reasoning/truncation artifacts and was
discarded — see the run notes.

Also: `--max-tokens` flag for thinking models whose effective budget needs
raising, `__FULL_CHECK__` test handling, and a fix for `max_tokens=None`
crashing the thinking-mode probe.

## 2026.09.05 — task-level validation, transfer estimate, benchmark audit, v1.0

Three things shipped today after the initial v1.0 push:

**1. Task-level holdout + transfer estimate.** A review question exposed a
hole in the held-out check: the split was by generation record, not by
task. A held-out record could come from the same task as a training
record, so a signal detecting *which task it is* — not wrongness — would
pass while being useless on a new task.

- **`task_holdout_validation` is now part of every profile** (and every
  `reanalyze` of an old raw file). Whole tasks are excluded from signal
  selection and threshold fitting, then scored. The report shows both
  holdouts side by side and explains which question each answers.
- **`transfer_estimate`** takes the signal the full run selected and
  re-scores it on held-out tasks across 300 random task splits — the
  usable number at this bank size, where the strict selection path is
  low-power with ~10 failing tasks.
- Applied to the current runs: qwen's selected signal **transfers** (0.73
  mean balanced accuracy on unseen tasks, above chance in 92% of draws);
  granite's task-selected signal scored **below chance** (0.87 train →
  0.47 test) — the exact failure mode this check exists to catch.
- The guarantee now has sharper teeth: a "usable signal" claim must be
  read together with the task-level field, and where task-transfer can't
  be shown the report says so explicitly.

**2. Benchmark audit (no false failures).** Audited every failure record
in both 60-task raws for harness-level mislabeling (timeouts, empty
extractions, import errors, sandbox crashes). Found none — every
`TRACEBACK` failure was the model's own code crashing. Found 3 assembly
tests that penalized behavior the spec never stated (filter/missing
column, validator/output-on-valid, report/output-shape); specs clarified
so future runs don't get unfair failures. No test was impossible (every
test passed in at least one generation). The 3 spec clarifications mean
future runs may show slightly fewer "unfair" failures — the published
60-task numbers were measured on the pre-clarification specs.

**3. v1.0 tagged and pushed.** `v1.0` is on `LocalLLMLab/calibration-kit`
(commit 14593ea, verified via `git ls-remote --tags origin`). Polar
product is live at $59.99 with early-bird code `thanksforyourtesting`;
checkout link is in the README; GitHub Repository Access benefit
auto-invites buyers with Read access.

## 2026.09.05 (later) — one pass now captures everything the output distribution can tell you

The signal search's job is to find *this* model's tell, not to test a list
of expected tells. Until now the scan covered ~30 statistics derived mostly
from one series: top-20-cropped entropy. The collector now records every
distribution-level signal the logits can support in the same single
generation pass — nothing below costs an extra token of GPU time:

- **Full-vocabulary entropy** alongside the top-20 crop — the mass leaking
  past the crop is itself a candidate.
- **Commitment curve**: true probability mass of the top-1, top-5 and
  top-20 tokens (not crop-renormalized).
- **KL-divergence series**: step-to-step `KL(p_t ‖ p_{t−1})` (belief
  revision), `KL(p_t ‖ uniform)`, and `KL(p_t ‖ running centroid)`
  (excursions from the generation's own mean).
- **Sampled-token surprisal and rank** — which token was actually chosen
  and how unexpected it was, computed in-processor from the previous
  step's stored logits (the response `logprobs` field would have required
  `logits_all=True` at model load; this way costs nothing).
- **Structural-token entropy** — uncertainty leaking into punctuation and
  formatting, summarized separately.
- **Thinking-phase split (EAT).** When a thinking-close marker token is
  emitted, every series is also summarized over the thinking region and
  the answer region separately — pooling the two phases averages away the
  structure a signature may live in. Marker detection is id-based and only
  armed when the tag is a single special token, so a tokenizer that splits
  the tag cannot set a false boundary.

Every new field is automatically a tested, Benjamini-Hochberg-corrected
candidate — the scan now covers **~170 statistics** instead of ~30. A wider
search means a higher corrected bar for each candidate, which is the honest
direction: the report language reflects that a `none` after a wide scan has
earned more confidence, not less. Downsampled (32-point) copies of every
per-token series are stored in the raw run file, so a statistic invented
later is a `reanalyze` away — zero GPU.

Also in this change:

- **Custom task files.** `--tasks my_tasks.json` on `calibrate.py run` and
  `estimate`, plus `calibrate.py validate-tasks` — every custom task's
  reference implementation is proven against its own tests in the sandbox
  before any GPU time is spent, and a file with a wrong expected value is
  refused outright. `--tasks-mode extend` mixes custom tasks with the
  bank. The task file's content hash goes into the profile and the
  checkpoint signature. Schema and rules: `CUSTOM_TASKS.md`.
- **`federation.py` contains no network code at all now.** The
  `CALIBRATION_KIT_WEBHOOK_URL` opt-in POST was removed entirely — under
  the Polar storefront there is no endpoint, and "no network code" is
  easier for a buyer to verify than "opt-in network code."
- **The Phase-3 recovery-rate bug is fixed.** It summed per-strategy
  recoveries over total failures, counting one failure once per strategy
  that fixed it — 190.9% on the qwen profile. It now unions the recovered
  failure keys; the same profile correctly reports 90.9%.
- **Backend limits are documented, not implied.** Techniques needing
  intermediate-layer hidden states (logit lens, linear probes) are
  unavailable through llama.cpp/GGUF and are explicitly not claimed.
- `SECURITY.md` is new; `LICENSE.md` no longer describes a phone-home
  sequence or webhook that do not exist.
- `PIPELINE_VERSION` bumped to 2026.09.05 — old checkpoints will not mix
  with runs on the new capture.

## 2026.09.05 — the task bank goes from 18 to 60, and every answer in it is verified

The task count was the ceiling on every statistic the kit produces. At
temperature 0 a model is deterministic, so one task yields exactly one
independent observation and `--repeats` only makes byte-identical copies of
it — which is what made the granite run pseudo-replicated. 18 tasks at a
~20% failure rate is about 4 failures, below the 8-per-outcome floor the
rule fitter needs.

- **42 new single-function tasks**, in a new `_task_bank.py`. The bank is now
  60 tasks: 46 single-function and 14 multi-file wiring. At ~20% that is
  12–16 failures per run, enough for the cross-validated fitting the report
  already does honestly but had too little data to do well.
- **Every expected value is verified.** Each task ships a reference
  implementation, and `python _task_bank.py` runs every reference against
  its own tests. A wrong expected value would be scored as a model failure
  and would corrupt every downstream statistic invisibly; this is what rules
  that out. Writing the bank caught one such error before it shipped.
- **A pre-run warning** when `temp=0` and `--repeats > 1`, so the wasted GPU
  time is flagged before it is spent rather than diagnosed afterwards. Now
  that a run is 60 tasks instead of 18, `--repeats 2` at temp 0 costs hours
  and buys nothing.
- Adding tasks changes the checkpoint signature, so old checkpoints will not
  resume into the new bank. That is deliberate — two banks must never be
  mixed inside one run.
- **`METHODOLOGY.md` no longer advertises task suites that do not exist.**
  It listed a "Core 12-task", a "Hard 10-task" and a "SWE-bench Lite (6)"
  suite with astropy and django instances. None of them are in the code, and
  there is no suite selection: every run uses the whole bank. The section now
  describes what actually runs, and why the count is the number that matters.

**Existing results are not comparable to new ones.** Every published profile
was measured on the 18-task bank. A run on the 60-task bank is a different
measurement, not a longer version of the same one.

## 2026.09.05 — the storefront no longer needs a server, and the report says what a rule costs

**Storefront.** The kit is sold through Polar at **$59.99** one time
(launched at $29; price updated at release, early-bird discount on the
store page). Polar is
the merchant of record and its GitHub Repository Access benefit issues the
collaborator invite at checkout, so the purchase→access path has no code in
it at all. This retires three things that were never finished: the AgentMart
integration, `register.py`, and the undeployed Cloudflare Worker. Lemon
Squeezy was the intended replacement and was dropped — it has no GitHub
integration, so the invite would still have required that Worker, and its own
team has said publicly they are steering users toward Stripe Managed
Payments.

- `register.py` is **deleted**. There is no registration step; accepting the
  GitHub invite is the whole of it.
- `federation.py` no longer validates a license key and no longer POSTs
  anywhere. It writes the sanitized contribution to
  `contribution_track_A.json` / `contribution_track_B.json` and tells you to
  open a pull request or an issue with it. (The short-lived
  `CALIBRATION_KIT_WEBHOOK_URL` opt-in was later removed entirely — the
  file now contains no network code at all.)
- The license's "our backend rejects payloads without a valid key" clause is
  gone, because there is no backend to describe.
- `SUPPORT.md` and `REFUND_POLICY.md` are new: response window, what support
  covers, and the guarantee.

**The guarantee.** A completed run yields a usable signal, a working repair
order, or an explicit `none` backed by a power analysis — or the purchase is
refunded. `none` counts as a delivered result, and `REFUND_POLICY.md` says so
in plain terms before anyone buys. Promising "a rule or it's free" would have
contradicted the kit's own central finding, that most models tested do not
have one.

## 2026.09.05 — a hung generation can no longer stall an unattended sweep

`--gen-timeout SECONDS` sets a wall-clock budget for a single generation.
The budget is enforced from inside the logits processor, which llama.cpp
calls once per token, so an over-budget generation is aborted mid-stream
rather than after it finishes. An aborted generation is scored as a failure
and the sweep continues.

- Available on `calibrate.py run`, `calibrate.py adaptive`, and the
  underlying pipelines; also settable with `CALKIT_GEN_TIMEOUT`.
- Off by default. Unset means the previous behaviour exactly.

## 2026.09.05 — the HTML report now shows where to cut the signal

`recommend_rules` had been wired into the text report only, so the HTML
report — the one a buyer actually looks at — never showed the operating
points. It does now, in a new section between the rule and the evidence:

- **Catch wrong**, **trust right**, and **both**, each with its
  cross-validated numbers and the folds that agreed on the signal.
- The token economics per 1000 generations, and — new — an explicit note
  when *no* operating point pays for itself in tokens. On the qwen run it
  does not, because the winning signal is only readable once a generation is
  complete; the report now says that instead of leaving a reader to infer it
  from a negative number.
- A warning in the signal-combination section when no signal in the shipped
  combination was picked in more than half the folds, pointing the reader at
  the single-signal operating points instead. The recall figure there is
  real; *which* signals produce it is not stable, and the report now
  distinguishes those two claims.


## 2026.09.04 — runs were silently deterministic; re-running was not a second sample
`load_model()` never passed a seed, so llama.cpp used a fixed default. Repeats
*within* a run vary normally, but **re-running the same command replayed the
identical generations** — verified at 180/180 probes bit-identical across two
runs of qwen3-4b-instruct: same code text, same entropy values, same pass/fail.

Why this mattered more than a missing flag: anyone re-running to check whether
their signal was stable would get a perfect match and conclude it was rock
solid, having actually just re-read the same data. Replication was impossible
and nothing said so.

- `--seed` is now a first-class flag on `calibrate.py run`, defaulting to a
  fixed value so published results stay reproducible.
- The seed is recorded in the profile and included in the checkpoint
  signature, so two seeds can never share a checkpoint or be mixed.
- The flag's help and the README state plainly that the same seed replays the
  same generations, and that changing it is how you draw a second sample.
- With `--probe-only`, an independent second sample now costs minutes.

## 2026.09.04 — the architect is optional, and worth about 3%
Measured across the two runs that used one:

| model | recoverable, all 7 | recoverable, coder-only 3 | needs architect |
|---|---|---|---|
| qwen3-4b-instruct | 30/33 (91%) | 29/33 (88%) | 1 failure (3%) |
| granite-4.1-3b | 18/29 (62%) | 17/29 (59%) | 1 failure (3%) |

Single-model mode keeps **97%** and **94%** of all achievable recoveries. The
three coder-only strategies do nearly all the work; the four architect-driven
ones uniquely rescued exactly one failure per model. The architect was already
optional in code — this documents what skipping it actually costs, so nobody
downloads a second model believing it is required.

## 2026.09.04 — architect preset was mislabeled and its thinking flag missing
Verified every shipped preset against the model's own Hugging Face card.
Two of three were already correct; the architect was not.

- **qwen3-4b-instruct — correct.** `Qwen/Qwen3-4B-Instruct-2507`'s
  `generation_config.json` gives `temperature=0.7, top_k=20, top_p=0.8`,
  matching what ships exactly. Card is silent on min_p / repeat_penalty /
  presence_penalty, and neutral values are used rather than invented ones.
- **granite — correct.** `ibm-granite/granite-4.1-3b` ships no sampling
  parameters at all in `generation_config.json`, and the card's own usage
  example calls `model.generate()` with no sampling arguments, i.e. greedy.
  The shipped `temp=0.0, top_p=1.0, top_k=0` is exactly that.
- **architect (Qwen3.5-4B) — two errors, both fixed.**
  1. **The comment did not match the values.** It read "Qwen3.5 instruct
     reasoning" while the values (`temp=1.0, top_p=0.95, top_k=20,
     presence_penalty=1.5`) are the card's *thinking-mode general* set. The
     card's actual instruct-reasoning set is `temp=1.0, top_p=1.0, top_k=40,
     presence_penalty=2.0` — nothing ever shipped that. The values had a real
     source; the label pointed at the wrong one.
  2. **`thinking` was never declared**, so it defaulted to `False`. The card
     states Qwen3.5 thinks by default, and the preset in use was a
     thinking-mode preset — so the pipeline was running a thinking model
     under non-thinking handling: no bumped `max_tokens`, no `<think>` block
     expectation. This affected every architect-driven intervention
     (`arch_design`, `arch_trace_short`, `arch_trace_long`, `decompose`) —
     4 of 7 — in every run that used an architect.
  Now set to the card's **"Thinking mode for precise coding tasks"** set —
  `temp=0.6, top_p=0.95, top_k=20, min_p=0.0, presence_penalty=0.0` — with
  `thinking: True`. Chosen from the card's own menu because the architect's
  task is writing skeletons, design traces and decompositions for a coder.
  Note `Qwen/Qwen3.5-4B` ships **no** `generation_config.json`; the four
  sampling sets come from the README's "Best Practices" section.

**Consequence:** architect-driven intervention results from before this entry
were produced under a preset/handling mismatch. Coder-only interventions
(`test_retry`, `temp_retry`, `skeleton_fill`) and every entropy result are
unaffected — those never touch the architect.

## 2026.09.04 — --probe-only, and probe runs no longer overwrite full profiles
- `calibrate.py run --probe-only` runs Phase 1 and skips the repair sweep.
  The entropy/signal analysis needs only Phase 1, so bringing a model onto a
  newer feature set costs minutes instead of hours. The resulting profile
  states that it carries no repair guidance rather than reporting "0 failures
  recoverable".
- A probe-only run writes to `_calibration_<label>_probe.*`. Writing to the
  full profile's name would have silently replaced a complete profile — repair
  order, error-type routing and all — with a partial one, discarding the part
  of the run that took the most GPU time.
- The checkpoint signature includes the probe-only flag, so a partial run can
  never resume into a full one.

## 2026.09.04 — capture the trajectory, not just summaries of it
The entropy collector discarded the per-token trajectory and kept only
summary statistics, which is why questions about *where* in a generation the
model was uncertain could not be answered without re-running the model.

- New at capture: `first_token_entropy`, `first3/5/10_mean`, `first10_max`,
  `first10_std`, `early_slope` (least-squares over the opening tokens),
  `early_vs_rest`, `first_to_max_ratio`, and `trajectory_ds` — a 16-point
  downsample of the whole trajectory, about 0.2KB per generation.
- Confidence, from the same softmax already being computed: `phi_first`,
  `phi_first10_mean`, `phi_mean`, `margin_first`, `margin_mean` (top1−top2).
  Entropy measures spread; these measure commitment.
- Derived at analysis time, so they apply to older runs too via `reanalyze`:
  quartile shape (`q_slope`, `q_early_drop`, `q_curvature`, `q_argmax`,
  `q1_over_mean`, …) and, where a trajectory was recorded, monotonicity and
  oscillation (`mono_down_frac`, `osc_sign_changes`, `osc_rate`,
  `path_ratio`, `trend_rho`) and spike structure (`n_spikes`,
  `spike_height`, `late_vs_early_half`).

**More candidates makes the search worse, not better** — which is why the
next two entries exist.

## 2026.09.04 — held-out validation, and pre-registration
- **Held-out split.** The signal is now selected and its threshold fitted on
  a training subset, then scored on records that played no part in either
  decision. That number needs no correction for how many candidates were
  searched, and it is the one to quote. A winner scoring below 0.55 on
  held-out data is demoted to a lead and no gate ships. Needs ~30+ failures;
  below that the report says why it could not run.
- **Pre-registration.** `CALIBRATION_KIT_PREREGISTER="sig1,sig2"` restricts
  the scan to named signals and records itself in the profile, so a
  confirming run is a confirmation rather than a second search.
- Both exist because a 22-candidate scan on one model produced a winner at
  adjusted p=0.009. See `research/` for that finding and what came of it.

## 2026.09.04 — HTML report: the rule, the evidence, and what shows promise
- `calibrate.py report --profile <profile.json>` renders a run as a
  self-contained HTML page — inline CSS and inline SVG, no scripts or fonts
  fetched, no build step, light and dark. Structure mirrors what a buyer
  actually needs:
  - **The rule** — implementable as written, stated only from what the run
    tested. Whether to gate on entropy, the repair order, per-error-type
    routing, and when to stop.
  - **The evidence** — every probe generation plotted by its entropy, correct
    versus incorrect, with group means. When there is no signal the overlap
    shows it faster than any p-value.
  - **Every candidate signal, corrected** — effect size per statistic against
    a shaded band marking what the run was too small to detect at all.
  - **What repairs failures** — including the strategies that recovered
    nothing, which used to disappear from the output entirely.
  - **What shows promise** — leads with the exact follow-up run that would
    settle each, explicitly labelled as leads rather than findings.
- Routing advice is now honest about weak results: a best-strategy recovery
  rate under 25% reads "expect little, try once, then escalate" instead of
  "route here first", and an error type nothing recovered says so.
- Settings table distinguishes a recorded provenance from one that was never
  saved, rather than printing "unknown" for both.

## 2026.09.04 — export --data could destroy a run's raw records
- `export_playbook.py --data` is an *output* path (it writes a machine-readable
  companion). Pointed at a run's `_raw.jsonl` it silently overwrote it — and
  the raw records are the one artifact a run cannot be recovered from, the
  thing `reanalyze` depends on. This destroyed the granite run's raw records
  during this session's own work.
- The flag is now `--companion` (with `--data` kept as an alias), its help says
  OUTPUT in capitals, and it **refuses to write** to any path that looks like a
  raw record file instead of overwriting it.
- Input flags elsewhere are `--raw` (`reanalyze`, `report`) so an input and an
  output flag are never one letter apart.

## 2026.09.04 — directional claims are now significance-gated (MAJOR, invalidates prior entropy findings)
- **The pipeline decided `entropy_direction` from the sign of a difference in
  means, with no test of any kind.** `fail_mean > ok_mean` became "high=bad",
  `fail_mean < ok_mean` became "high=good", and "none" was only produced on
  exact float equality — which never happens. The kit could therefore *never*
  output "no signal" from this path, despite the README advertising "an entropy
  signal (or explicit proof none works)".
- A threshold was then fitted to that direction and shipped, and its balanced
  accuracy was printed as "Accuracy" with nothing to compare it against.
- **What this means for every previously published number: the entropy
  direction, separation and threshold in every profile shipped before this
  entry were the sign of a noisy mean difference, not findings.**
- Fixes:
  - Direction is gated on a two-sided **permutation test** (20,000 resamples,
    fixed seed, no scipy) AND a minimum separation of 0.08. It fails closed to
    "none". The ungated sign is still recorded as
    `raw_direction_before_gating`, labelled as not a finding.
  - **No threshold is shipped when no direction survives.** The previous
    behaviour of falling back to a hardcoded `1.5` on insufficient data also
    went — it handed out an invented number that read as measured.
  - `balanced_accuracy` is now named as such and reported against chance (0.5),
    alongside the raw score of always guessing "pass" so an imbalanced sample
    can't be misread as skill.
  - **Statistical power is now reported.** "No signal" and "this run was too
    small to see one" are different answers, and the report says which:
    observed Cohen's d, the minimum effect the run could detect, and — when
    underpowered — the `--repeats` value that would reach ~80% power, or a
    plain statement that no practical run would settle it.
- Re-analysis of all three shipped profiles under the gate:
  | model | n_fail | separation | Cohen's d | permutation p | verdict |
  |---|---|---|---|---|---|
  | granite | 9 | 0.036 | +0.16 | 0.688 | none (underpowered; not practical to settle) |
  | qwen3-4b-instruct | 5 | 0.236 | +0.61 | 0.207 | none (underpowered; --repeats 10 would settle it) |
  | mini-coder-4b | 11 | 0.026 | +0.09 | 0.807 | none (underpowered; not practical to settle) |
- The default `--repeats 2` yields 5–11 failures per run, enough to detect only
  d>=1.0 or larger. **The kit's headline claim cannot be evidenced at its own
  default setting.** The intervention/repair layer is unaffected — recovery
  rates are direct measurements, not correlational claims.

## 2026.09.04 — reanalyze: recompute analysis without GPU time
- `calibrate.py reanalyze --raw _calibration_<label>_raw.jsonl` rebuilds the
  profile and report from a past run's stored generations. When the analysis
  improves, historical runs are re-derived instead of re-run, so old and new
  results stay comparable. Provenance (`config`, `config_provenance`,
  `model_file`) is carried forward from the previous profile.

## 2026.09.04 — sandbox coverage gap closed (affects all prior results)
- **Three execution paths ran model-generated code with no sandbox at all.**
  The prelude from `_sandbox.py` was only ever applied by
  `_test_harness.run_bundle`. It was NOT applied by:
  - `_arch_skel_hard.test_function_code` — **a live path.** The current
    pipeline routes all 4 hard function tasks through it. Model code was
    written to disk and executed via `from <mod> import *` in a subprocess
    with no restrictions: network, subprocess spawning, and file writes
    anywhere the user could write were all permitted.
  - `_multifile_assembly.test_wiring_file`
  - `_final_combined_test_v2.run_tests`
- All three now prepend the prelude. `_arch_skel_hard` additionally pins
  its test subprocess to `cwd=tmpdir`, so the prelude's "writes allowed in
  cwd" allowance can no longer reach the repo or the user's working
  directory.
- `_sandbox.py`: `importlib.import_module` is now blocked alongside
  `builtins.__import__`. `import_module` does not route through
  `__import__`, so the module blocklist (ctypes, multiprocessing, signal,
  pickle, marshal) had a one-line bypass.
- Verified: correct code still passes; network, subprocess, `os.system`,
  direct `ctypes` import, `importlib`-laundered `ctypes` import, and
  writes outside the temp dir are each blocked, and a write to the repo
  directory now lands in the temp dir instead.
- **⚠️ This changes what a run measures on the 4 function tasks.** Code
  that previously passed by writing outside its sandbox now fails there.
  Every profile generated before this entry — including the two
  post-heredoc-fix runs (`qwen`, `mini-coder-4b`) — is stale for the
  function-task portion and should be re-run.
- The `__subclasses__` escape remains open and remains documented. Threat
  model is unchanged: accidental damage from model output, not a
  determined adversary.

## 2026.09.04 — resumable runs, single entry point, config provenance
- **`_checkpoint.py` (new).** Every completed probe generation and
  intervention attempt is appended to `_ckpt_<label>.jsonl` and fsynced
  immediately. An interrupted run resumes on the next identical command
  instead of starting over. Reuse is gated on an exact run signature —
  model label, full sampling preset, repeat count, thinking flag,
  architect, task id list, and pipeline version — so results produced
  under different settings can never be silently mixed. A signature
  mismatch sets the old checkpoint aside as `.stale` and starts clean.
  `--no-resume` forces a clean start. Checkpoints are deleted on
  successful completion. Torn final writes are tolerated.
- **`calibrate.py` (new) — single entry point.** `models`, `estimate`,
  `run`, `adaptive`, `export`, `converge`. Sampling flags are defined once
  and forwarded, so `run` and `adaptive` can no longer drift apart on what
  they accept. The underlying scripts still work directly.
- **`calibrate.py estimate`** loads the model, measures its real
  tokens/sec on this machine, and prints a wall-clock estimate and range
  for a full run before you commit hours to it.
- **Config provenance.** Every sampling value is now tagged with where it
  came from — card-verified registry, CLI override, or generic default —
  printed as a table at run start and stored in the profile as
  `config_provenance`, alongside `pipeline_version` and an
  `unverified_preset` flag. A published number can always be traced back
  to the settings that produced it, and a run on unverified defaults says
  so in its own output file.
- Progress lines now carry `[done/total]` and a running ETA.
- `calibrate.py models` lists visible GGUF files and flags which ones have
  no preset on file.

## 2026.09.04 — scope claim to benchmark-verifiable pass/fail tasks
- The task bank behind every calibration run is 18 Python code-gen tasks
  (14 multi-file assembly + 4 hard algorithmic functions), all graded by
  automated test pass/fail. That's the actual proven domain — not "model
  correctness" broadly.
- Added an explicit "Scope" section to README.md and SKILL.md: this kit
  calibrates benchmark-verifiable pass/fail tasks (code with automated
  tests). Entropy signal and intervention ranks are not tested on
  open-ended/subjective output and are not assumed to transfer there.
- Reasoning: pitching "it'll work for you" off an all-code task set risks
  reading as overselling. Scoping the claim to what's actually measured
  costs nothing to ship, vs. broadening the task set which is real future
  work.

## 2026.09.04 — outlier recovery-rate flagging in export_playbook.py
- `export_playbook.py` now flags any intervention whose recovery rate
  jumps sharply above the others (>=25pt gap, own rate >=50%) in both
  the intervention-order table and the error-type routing table, with
  an inline ⚠️ and a note to hand-inspect samples before trusting it.
- Motivation: a high recovery rate isn't automatically "this
  intervention works" — it can mean the intervention is leaking the
  shape of the answer (e.g. skeleton_fill revealing code structure)
  rather than genuinely repairing the model's reasoning. This has
  helped surface real bugs before (see the extract_code() entry below)
  and is now baked into the tool's own output instead of relying on
  manually noticing it.
- Verified against `examples/mini-coder-4b_profile.json`: correctly
  flags `test_retry` (75%) as an outlier vs `skeleton_fill` (25%) for
  logic errors; no false-flag on the overall intervention-order table.

## 2026.09.03 — extract_code() bash-heredoc fix
- Fixed `extract_code()` in `_multifile_assembly.py`: the markdown-fence
  regex only matched a literal ` ```python ` or bare ` ``` ` tag. When a
  model wrapped its answer in a different fence (observed: ` ```bash `
  containing a `cat > file << 'EOF' ... EOF` heredoc), extraction silently
  failed and the raw fenced text was compiled as Python as-is — an
  instant `SyntaxError` on line 1, misclassified as a genuine model
  coding mistake (`error_type: "syntax"`).
- Fix: the fence regex now accepts any/no language tag, and a heredoc
  body inside a fence is detected and unwrapped instead of being treated
  as literal Python.
- **⚠️ All calibration runs before this fix are suspect for models that
  ever emit non-`python`-tagged fences or shell-heredoc wrapping.**
  Confirmed impact on the `mini-coder-4b-q8_0` run (2026-09-03,
  `examples/mini-coder-4b_agents.md`): 7 of 15 probe-phase failures
  (~47%) were this exact bash-heredoc miss, not real model errors —
  contaminating that run's entropy separation, threshold accuracy, and
  `syntax`-error-type intervention rates. Not yet checked on
  `granite_agents.md` / `qwen_agents.md` (2026-08-27/28) or any other
  pre-2026-09-03 profile — treat all of them as unverified until
  re-run or manually checked for this pattern.

## 2026.08.28 — initial release
- First public release of the Calibration Kit.

<!-- Template for future entries:
## YYYY.MM.DD — <short description>
- What changed.
- Contributor credit: <buyer handle> (via federation Track A).
-->
