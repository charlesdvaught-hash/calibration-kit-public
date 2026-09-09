# Calibration Probe

A free, standalone demo that tests whether your local GGUF coding model has a
usable entropy-based wrongness signal on 60 realistic coding tasks. The default
bank mixes 14 small CLI/data-tool assembly tasks with 46 single-function tasks,
which is closer to a single user's repeated asks than a broad HumanEval sweep. It
captures per-token entropy trajectories, scans ~170 candidate signals with
permutation tests and Benjamini-Hochberg correction, and prints an honest verdict.

This is a **hobbyist science kit**, not a lab implementation. It proves the
method can find a signal on example tasks. The signal found here is a
fingerprint of your model on this task distribution — it is unlikely to
transfer to your own tasks, other models, or other task types.

The probe reserves the last 20 tasks as a holdout set. It trains on the first 40
tasks, discovers a signal, and then tests that signal on the reserved 20 unseen
tasks to see if it predicts out-of-sample outcomes at the cusp of the model's
capability.

## Quick start

```bash
pip install llama-cpp-python numpy
python probe.py --model your-model.gguf
```

That's it. No API keys, no cloud, no accounts. Everything runs locally.

## What it does

1. Loads your GGUF model via `llama-cpp-python`
2. Generates code for the task bank, sorted by difficulty (easy → hard)
3. Captures per-token entropy trajectories during generation (top-20 cropped
   softmax entropy, structural/semantic token split, plateau/spike detection,
   thinking-phase boundaries, and one-pass series summaries)
4. Tests each generated solution against the task's test cases
5. Scans ~170 candidate entropy signals for separation between passing and
   failing generations
6. Corrects for multiple comparisons (Benjamini-Hochberg, alpha=0.05)
7. Trains on the first N tasks (default: full bank; stop early with `--target-failures N`)
8. Tests the discovered signal on the reserved holdout tasks
9. **NEW: End-to-end gate validation** — flags likely-wrong holdout answers
   and runs three interventions (temp_retry, test_retry, skip_retry) to test
   whether acting on the signal improves final accuracy. Reports net accuracy
   gain with McNemar exact test and Wilson confidence intervals.
10. Optionally reranks predicted failures on the holdout with `--holdout-rerank N`
11. Prints one of four honest verdicts:
    - **SIGNAL FOUND** — a signal survived correction with |d| >= 0.2
    - **NO SIGNAL FOUND** — nothing survived (honest null result)
    - **UNDERPOWERED** — too few failures to detect anything
    - **NO FAILURES** — your model passed everything

## Task banks

| Bank | Tasks | Description |
|---|---|---|
| `realistic` (default) | 60 | 14 assembly + 46 single-function, closer to real user asks |
| `human` | 150 | HumanEval-derived with adversarial edge cases |
| `easy` | 42 | Simple single-function tasks |
| `mbpp` | 249 | Sanitized MBPP, harder, more failures on small models |

Use `--bank mbpp` for models that pass the demo banks too easily. MBPP produces
more failures, which gives the signal scan more data to work with.

## Example result

Qwen3-8B-Q5_K_M, with `--no-think` (disable Qwen3 thinking mode) and the default
60-task realistic bank, finds:

- **Training:** 20 pass, 20 fail
- **Signal:** `kl_cent_f10_mean`, Cohen's d = +1.56, adjusted p = 0.0085
- **Holdout:** 16/20 correct predictions (80% vs 75% majority baseline)

This is a fingerprint on this model on these demo tasks, with some evidence it
generalizes to the held-out tasks.

## Does acting on the signal improve final accuracy?

The probe now answers this directly. After finding a signal and running the
holdout, it applies the gate to flag likely-wrong holdout answers and runs
three interventions on each flagged task:

- **`temp_retry`** — fresh generation at +0.2 temperature (fix strategy)
- **`test_retry`** — show the model its test failures and ask it to fix (fix strategy)
- **`skip_retry`** — discard and regenerate up to 3 times, keep first pass (cull strategy)

It then reports:
- How many holdout tasks the gate flagged (true failures + false positives)
- Per-intervention rescue/worsen counts
- Baseline vs gated pass rate with 95% Wilson confidence intervals
- Net accuracy gain
- McNemar exact p-value (proper paired before/after test)
- Verdict: PROVEN / PROMISING BUT NOT PROVEN / NOT PROVEN / HARMFUL

### Full kit experiment result

The full calibration kit ran this experiment on 249 MBPP tasks (200 training /
49 holdout) with Qwen3-8B. **Result: PROMISING BUT NOT PROVEN.** The best
transfer gate caught 10 of 22 true failures with zero false positives.
`temp_retry` rescued 3 of 10 caught failures. Net accuracy gain: +6.1%
(55.1% to 61.2%). McNemar p=0.125 — not statistically significant at n=49,
but the direction is positive and no correct answers were worsened.

The probe's original signal (`think_frac`) transferred across datasets
(HumanEval to MBPP, 0% false-positive rate). The best intervention was
dataset-dependent: `temp_retry` worked on MBPP (where assertion failures
dominate) while `test_retry` worked on HumanEval (where syntax failures
dominate).

Full report in the kit: `research/OUTCOME_gate_validation_mbpp.md`.

## What the verdict means

**SIGNAL FOUND** means: on this specific model, on these 60 demo tasks, in
this specific run, there is an entropy trajectory feature whose value
systematically differs between correct and incorrect generations. This is a
fingerprint on the demo bank, not a universal rule. It may not transfer to your
actual tasks, other models, or other task types.

**NO SIGNAL FOUND** means: this run did not detect a usable signal on the demo
tasks. This is an honest null result. Some models genuinely don't have a usable
entropy signal on this task distribution, or need more failures.

**UNDERPOWERED** means: there weren't enough failures to detect anything.
Try `--repeats 2` or `--repeats 3` with a higher temperature to generate
more variance. No signal found in an underpowered run does NOT mean no
signal exists.

## Command-line options

```
python probe.py --model your-model.gguf [options]

  --model PATH          Path to GGUF model file
  --bank {realistic,human,easy}
                        Task bank: realistic (60 tasks, default), human
                        (150 HumanEval tasks), easy (42 easy function tasks)
  --validate            Validate the task bank and exit (no model needed)
  --temp FLOAT          Temperature (default 0.7)
  --top-p FLOAT         Top-p (default 0.8)
  --top-k INT           Top-k (default 20)
  --min-p FLOAT         Min-p (default 0 = off)
  --repeat-penalty F    Repetition penalty (default 1.0 = off)
  --presence-penalty F  Presence penalty (default 0)
  --thinking            Model is a thinking model (4096 max_tokens, strips <think> blocks)
  --repeats INT         Repeat each task N times (default 1; use 2+ for stochastic models)
  --target-failures INT Stop after this many failures during training (default 1000;
                        effectively no early stop on the 60-bank; use 15 for quick stop)
  --holdout INT         Reserve this many of the bank's hardest tasks as holdout
                        (default 20; 0 to disable)
  --holdout-rerank INT  For predicted failures, generate 1 + N samples, keep best signal, compare to random (0 to disable; 2 for best-of-3)
  --no-early-stop       Run all 60 tasks (or all of --bank) even after reaching target failures
  --n-gpu-layers INT    GPU layers for llama-cpp-python (default -1 = all)
  --upload-url URL      Opt-in upload endpoint (or set PROBE_UPLOAD_URL env var)
  --no-upload           Skip the upload prompt entirely
```

## Thinking models

If your model generates `<think>...</think>` reasoning blocks before its
answer (e.g. Qwen3-Thinking, Qwen3.5), pass `--thinking`:

```bash
python probe.py --model qwen3-4b-thinking.gguf --thinking --temp 0.6 --top-p 0.95
```

This increases `max_tokens` to 4096 (thinking tokens consume budget) and
strips thinking blocks before extracting code. Without this flag, thinking
models will silently produce no code output because the thinking tokens
consume the entire 1200-token budget.

**Important**: Check your model's HuggingFace card for the correct sampling
parameters. Qwen3 thinking uses temp=0.6, but Qwen3.5 thinking uses
temp=1.0. Using the wrong temperature produces bad results.

## Repeats and early stop

With `--repeats 1` (default), each task is run once. The probe trains on the
first 40 tasks of the 60-task bank and, by default, does **not** stop early.
It then runs the reserved 20 holdout tasks to test the signal on unseen
near-cusp work. If your model passes all 60 tasks, you will get NO FAILURES and
no signal can be detected. Use `--repeats 2` or `--repeats 3` with a higher
temperature to generate more variance, or `--target-failures 15` to stop early
as soon as a detectable signal might be available.

## Reranking with the signal

If you want to test whether the discovered signal can actually select better
answers on the example tasks, pass `--holdout-rerank 2` (or 1, 3, etc.). When the
first sample's signal predicts failure, the probe generates N more samples,
picks the best one by the signal, and compares it to a random control. This is
best-of-(N+1) selection on the demo bank. It costs extra generations only for
predicted failures. Your own task distribution may need a different signal.

## Contributing your results

After running the probe, you can share your results to help map which models
have signals and which don't. Three options:

### Option 1: GitHub PR (recommended — auto-syncs to HF dataset)

```bash
python contribute.py probe_your-model_results.json
```

Or manually: fork the [repo](https://github.com/charlesdvaught-hash/calibration-kit-public),
add your JSON to `submissions/`, open a PR. When merged, GitHub Actions
auto-syncs to the HuggingFace dataset via a trusted publisher. No HF account
or token needed — just a GitHub account.

### Option 2: HuggingFace PR (direct, needs HF account)

```bash
pip install huggingface_hub
python upload_to_hf.py probe_your-model_results.json --token hf_YOUR_TOKEN
```

Get a token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
This opens a PR directly on the HF dataset repo.

### Option 3: Cloudflare Worker (fastest, needs deployed worker)

```bash
python probe.py --model your-model.gguf \
  --upload-url https://calibration-probe-collector.workers.dev/submit
```

Or set `PROBE_UPLOAD_URL` as an environment variable. The probe will prompt
you with `[y/N]` before uploading.

**What gets shared (all options):**
- Model filename and quant label
- Per-task 16-point downsampled entropy trajectory + pass/fail
- Signal scan results (which signals survived, d values, p values)
- Timestamp

**What does NOT get shared:**
- NO prompts or task descriptions (standard public tasks only)
- NO generated code
- NO user identity or account info
- NO IP address

## How this differs from the full calibration kit

This probe is a discovery tool — it shows whether the method can find a signal
on a fixed task bank. A separate commercial calibration kit extends this into a
live proxy that learns the signal on your own tasks, with intervention routing,
nightly relearning, and custom task support. This probe exists to demonstrate
the underlying method, not to be deployed as-is.

## Validating the task bank

The probe includes reference implementations for the 42 easy function tasks. You
can verify they all pass before running:

```bash
python probe.py --validate
```

This runs each reference against its own test cases. Tasks without a reference
implementation (assembly tasks and 4 new function tasks) are skipped in this demo.

## License

This probe is released under CC-BY-4.0 (see LICENSE-CONTENT.md). The full
calibration kit is commercial software under a separate EULA.
