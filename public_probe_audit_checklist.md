# Public probe fixes / tests → check against pro kit

This is the list of things we fixed or changed in `calibration-kit-public/probe.py` and `_realistic_tasks.py` that should be cross-checked one-by-one against the full `calibration-kit` implementation (in another conversation).

**Audit completed 2026-09-07.** Each item below is marked and annotated.

## Math / statistics

- [x] **Cohen's d**: public probe now uses separate group means and pooled *within-group* variance. Check pro `cohens_d` (or equivalent) does not use combined pass/fail std around a grand mean.
  → **BUG FOUND AND FIXED.** `cohens_d` in `_calibrate_pipeline.py` pooled both groups around the grand mean, which inflates the SD by the between-group difference and deflates every |d| the kit reports. Replaced with pooled within-group SD (matches probe). Affects `scan_signals`, `holdout_validate`, `task_holdout_validate`, `entropy_direction`, power analysis, and the `learn` reanalysis path.
- [x] **Permutation p-values**: public probe uses the same permutation loop for every candidate. Check pro uses a fixed `PERM_SEED` and consistent null construction.
  → **Already correct.** Pro `permutation_p` is identical: fixed `PERM_SEED`, same null construction, +1 smoothing, min n=3 per group.
- [x] **Multiple comparison correction**: public probe uses Benjamini-Hochberg with `ALPHA = 0.05`. Check pro BH matches the same procedure and alpha.
  → **Already correct.** Identical BH procedure and alpha.
- [x] **Minimum detectable effect**: public probe uses `MDE_CONST = 2.80`. Check pro MDE formula and constant.
  → **Already correct.** Same constant and formula.
- [x] **Shape/trajectory features**: public probe fixed `spike_quartile`, `trend_rho`, and quartile chunking. Check pro's versions of these features for the same off-by-one / correlation formula bugs.
  → **`spike_quartile` BUG FIXED** (`max_idx * 4 // n` → `max_idx // qsize`) in both `_calibrate_pipeline.py` and `calibration_proxy/feature_extract.py`; `plateau_start_quartile` got the same fix (probe left it, but pro must stay internally consistent). `trend_rho` verified mathematically equivalent (rank_of is always a permutation, so both denominators are equal). Quartile chunking identical.

## Signal design

- [x] **Structural/behavioral variables**: public probe now blacklists `n_tokens`, `n_semantic`, `think_frac`, `think_boundary` from being the *sole* gating signal, but allows them in product/ratio composites with entropy features. Check pro does not accidentally declare a single behavioral/length variable as the gate.
  → **ADDED.** `NON_ENTROPY_BEHAVIORAL` frozenset added; `scan_signals` now returns `(rows, best, structural_best)` and never selects a structural signal as the gate. Structural signals remain in the scan table, remain eligible inside composites, and remain available to `signal_failure_routing` (routing failure *modes* is a different job than gating on correctness). Also excluded from `recommend_rules` candidate sets since combos OR their members. Verified live: `reanalyze` on the Qwen3-8B raw now reports `structural_best: think_frac` and ships `think_frac_x_kl_uniform_mean` (a composite) as the gate.
- [x] **Composite candidates**: public probe explicitly generates `n_tokens * <entropy>` and `n_tokens / <entropy>` style composites and tests them under the same BH correction. Check pro composites are not treated as separate, un-corrected claims.
  → **ADDED.** `shape_features` now emits `n_tokens_x_*`, `n_tokens_div_*`, `think_frac_x_*`, `think_frac_div_*` composites over `mean_entropy`, `q3`, `full_ent_mean`, `tail_mass_mean`, `kl_uniform_mean`. They flow into `scan_signals` and are corrected under the same BH pass as every other candidate.
- [x] **Verdict wording**: public probe distinguishes `SIGNAL FOUND`, `STRUCTURAL SIGNAL ONLY`, `NO ENTROPY-BASED SIGNAL FOUND`, `UNDERPOWERED`. Check pro reports the same categories.
  → **Partially added.** Pro already had an equivalent taxonomy via `power_verdict` (underpowered / adequately powered / signal detected). Now also reports `structural_best` + `structural_note` in `signal_scan`, and the text report prints "Structural signal (not a gate)" alongside "No entropy-based signal survives correction."

## Failure classification

- [x] **Error types**: public probe labels failures as `syntax`, `name_error`, `type_error`, `index_error`, `value_error`, `key_error`, `assertion`, `structural`, `timeout`, `empty_output`, `logic`, `other`. Check pro classification categories and assignment logic match.
  → **UPGRADED.** `classify_error` now classifies each failure separately and takes the majority vote (previously: first match against the joined failure text, which let one stray "expected" drown out several type_errors). Added `value_error`, `key_error`, `other` categories. This feeds `error_type_effectiveness` and `signal_failure_routing`.
- [x] **Failure histogram**: public probe prints a `Counter` of failure types. Check pro reports failure-type mix and warns when all failures are one type.
  → **ADDED.** `profile["failure_type_mix"]` records the Counter + `all_same_type` flag + warning note; rendered in the text report.

## Task bank

- [x] **60-bank source**: public `_realistic_tasks.py` is the 14 pro assembly tasks (`_multifile_assembly.TASKS`) + 46 function tasks (`_arch_skel_hard.HARD_TASKS`). Verify the port did not drop test cases or alter specs.
  → **Verified faithful.** 14 assembly + 46 function = 60 tasks; 274 tests on both sides (44 assembly + 230 function).
- [x] **60-bank order**: public probe sorts by `_difficulty_score` with assembly treated as harder (no reference, weighted per test). Check pro's 60-bank order / sorting matches or is intentionally different.
  → **Intentionally different.** The probe's difficulty sort exists because it early-stops and holds out "the last N tasks" — order matters there. Pro runs the full bank and uses random task splits, so ordering is irrelevant.
- [x] **Assembly test harness**: public probe writes `wiring_file` + `siblings`, then runs each test as `python -c <test_code>` in the temp dir. Check pro assembly harness (`_test_harness` / `_solve_pipeline.run_tests_with_failures`) matches this behavior or is more robust.
  → **Pro is more robust.** Batched runner with syntax gate, per-test tracking, traceback detection, sandbox prelude, `TimeoutExpired` handling.
- [x] **HumanEval 150 fallback**: public `--bank human` uses `_hard_tasks.py` (150 tasks). Check pro hard bank still exists and validates.
  → **Present and larger.** `_humaneval_tasks.json` (164 tasks) + `_humaneval_convert.py`; `python _task_bank.py` validates.
- [x] **Validation**: public `validate()` skips tasks without reference and reports counts. Check pro validation does not require references for assembly or hard tasks.
  → **Intentionally stricter in the right place.** `_custom_tasks.load_task_file` requires `reference` for buyer-provided tasks (and *proves* it against the tests — ground truth can't be trusted otherwise). Built-in bank validates via `python _task_bank.py`.

## Holdout / generalization

- [x] **Separate holdout set**: public probe reserves the last `N` tasks (default 20) before the run and never sees them during signal discovery. Check pro has task-level holdout and is not just "next N tasks after early stop."
  → **Pro is stronger.** `task_holdout_validate` does proper task-level splits (whole tasks excluded from selection AND fitting), plus `transfer_estimate` re-scores the selected signal across 300 random task splits. Not a positional "next N" trick.
- [x] **Balanced accuracy on holdout**: public probe reports accuracy, baseline, sensitivity, specificity, and balanced accuracy vs random. Check pro holdout validation uses balanced accuracy (or equivalent) when the holdout is imbalanced.
  → **Already correct.** Both holdout validators report balanced accuracy vs 0.5 chance.
- [x] **No-failures holdout warning**: public probe explicitly warns if the holdout has 0 actual failures. Check pro does the same so it does not overclaim a rule that never got tested on a failure.
  → **ADDED.** Report now prints a note when `n_test_failures == 0`, and a "Ran, but nothing selected" branch covers the previously silent `ran: True, selected_signal: None` case.

## Model handling

- [x] **Thinking mode**: public probe strips `\u003cthink\u003e`...`\u003c\u002fthink\u003e` and has `--thinking` / `--no-think`. Check pro thinking tag handling and Qwen3 `/no_think` switch.
  → **ADDED.** `--no-think` flag appends `/no_think` to every prompt (Qwen3 dual-mode soft switch). Distinct from `--no-thinking`, which only changes how output is *handled* — without it, a Qwen3 can still spontaneously reason and fill the token budget with thinking (the contamination that invalidated the discarded non-thinking probe run).
- [x] **Unclosed thinking block**: public `strip_thinking()` returns empty if thinking starts but never closes (rather than grading reasoning as code). Check pro handles unclosed thinking.
  → **BUG FIXED.** `extract_code` in `_multifile_assembly.py` kept leftover text if any line started with `def`/`import`/etc. — but reasoning traces mention function names in prose, so truncated thinking was graded `syntax` instead of `empty_output`. Now salvages only from a clear boundary (code fence or blank line), else returns `""`.
- [x] **Model config discipline**: public probe now requires/uses card-verified presets. Check pro enforces or records Qwen3 (temp 0.7, optional pp 0), Qwen3.5 (temp 1.0, pp 1.5), etc.
  → **Already handled.** `find_config` + `KNOWN_CONFIGS` registry + provenance tracking + CLI overrides + a warning when a model has no preset on file.

## Grading / extraction

- [x] **Code extraction**: public `extract_code()` uses a regex for ` ```python ` code blocks. Check pro extractor does not accidentally return markdown or explanation as code.
  → **Pro is a superset.** Generic fenced blocks (any language marker), heredocs, Aider SEARCH/REPLACE, LFM `edit()` calls, raw fallback. Kept as-is.
- [x] **Empty output**: public probe fails empty outputs and classifies them. Check pro handles empty/zero-length code.
  → **Already handled** (`len < 10` → `empty_output`).
- [x] **Timeout**: public `test_function_code` uses `DEFAULT_TEST_TIMEOUT_S`. Check pro timeout handling and error classification.
  → **BUG FIXED.** `subprocess.run(timeout=...)` was called with no `except TimeoutExpired` in `_arch_skel_hard.test_function_code` — a hung test (e.g. an infinite loop in generated code) propagated up and killed the whole calibration run. Now caught and recorded as a `TIMEOUT` failure, which `classify_error` maps correctly. The assembly path (`_test_harness`) already handled this.

## CLI / UX

- [x] **Default to full 40-task sweep**: public `--target-failures` default is `1000` (effectively no early stop on 60-bank). Check if pro should also default to a full sweep or keep early stop.
  → **N/A.** Pro runs the full bank by design (no early-stop equivalent in the probe phase).
- [x] **`--bank` selector**: public supports `realistic` / `human` / `easy`. Check pro task selection / custom task flags are consistent.
  → **N/A.** Pro always uses the full bank; `--tasks` + `--tasks-mode` provide custom/replace/extend.
- [x] **Result JSON**: public JSON now includes `best_signal`, `structural_best`, `error_type`, `holdout` with `predicted_pass`. Check pro JSON output has the same fields and schema.
  → **Covered by richer fields.** Pro profile JSON has `signal_scan.best_surviving_signal`, `signal_scan.structural_best` (new), `error_type` per record, `holdout_validation` + `task_holdout_validation` + `transfer_estimate`. No schema alignment needed — the pro schema is a superset.

## Last verified public result

- Model: `Qwen3-8B-Q5_K_M.gguf`, `--no-think`, 60-bank, 20 holdout.
- Signal: `kl_cent_f10_mean`, d = +1.557, p_adj = 0.0085.
- Holdout: 16/20 accuracy (80%), balanced accuracy 60%, caught 1/5 holdout failures.

## Post-fix note (2026-09-07)

Re-running `reanalyze` on existing raws after the `cohens_d` fix produces **larger** |d| values than previously published (the bug deflated d by inflating the denominator). Published directions and verdicts are unaffected — the bias was strictly conservative — but a fresh reanalyze of the Qwen3-8B raw now reports `structural_best: think_frac` (d=+4.169, previously +2.072 under the biased formula) and ships a composite gate (`think_frac_x_kl_uniform_mean`, d=+4.344). Historical profiles stand as artifacts of their runs.
