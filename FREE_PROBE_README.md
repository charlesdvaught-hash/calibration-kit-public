# Calibration Probe

A free, standalone demo that tests whether your local GGUF coding model has a
usable entropy-based wrongness signal on 150 example coding tasks. It runs the
standard public task bank, captures per-token entropy trajectories, scans ~160
candidate signals with permutation tests and Benjamini-Hochberg correction, and
prints an honest verdict.

This is a **hobbyist science kit**, not a lab implementation. It proves the
method can find a signal on example tasks. The full calibration kit learns the
signal on your own tasks and turns it into a live gate:
  https://github.com/charlesdvaught-hash/calibration-kit-public

The probe stops after it collects enough failures (default 15) to look for a
signal, then runs up to 30 extra holdout tasks to test whether the discovered
signal predicts out-of-sample outcomes at the cusp of the model's capability on
the demo task distribution.

## Quick start

```bash
pip install llama-cpp-python numpy
python probe.py --model your-model.gguf
```

That's it. No API keys, no cloud, no accounts. Everything runs locally.

## What it does

1. Loads your GGUF model via `llama-cpp-python`
2. Generates code for 150 standard Python function tasks, sorted by difficulty
   (easy → hard) on the demo task bank
3. Captures per-token entropy trajectories during generation (top-20 cropped
   softmax entropy, structural/semantic token split, plateau/spike detection,
   thinking-phase boundaries, and one-pass series summaries)
4. Tests each generated solution against the task's test cases
5. Scans ~160 candidate entropy signals for separation between passing and
   failing generations
6. Corrects for multiple comparisons (Benjamini-Hochberg, alpha=0.05)
7. Stops once `--target-failures` (default 15) failures are collected
8. Runs `--holdout` (default 30) extra unseen tasks to test the signal
9. Optionally reranks predicted failures on the holdout with `--holdout-rerank N`
10. Prints one of four honest verdicts:
   - **SIGNAL FOUND** — a signal survived correction with |d| >= 0.2
   - **NO SIGNAL FOUND** — nothing survived (honest null result)
   - **UNDERPOWERED** — too few failures to detect anything
   - **NO FAILURES** — your model passed everything

## What the verdict means

**SIGNAL FOUND** means: on this specific model, on these 150 demo tasks, in
this specific run, there is an entropy trajectory feature whose value
systematically differs between correct and incorrect generations. This is a
fingerprint on the demo bank, not a universal rule. It may not transfer to your
actual tasks, other models, or other task types. The full calibration kit
learns the signal on your own tasks.

**NO SIGNAL FOUND** means: this run did not detect a usable signal on the demo
tasks. This is an honest null result. Some models genuinely don't have a usable
entropy signal on this task distribution, or need more failures. The full
calibration kit also checks for repair routing rules that may be useful even
when no gating signal exists.

**UNDERPOWERED** means: there weren't enough failures to detect anything.
Try `--repeats 2` or `--repeats 3` with a higher temperature to generate
more variance. No signal found in an underpowered run does NOT mean no
signal exists.

## Command-line options

```
python probe.py --model your-model.gguf [options]

  --model PATH          Path to GGUF model file
  --validate            Validate the task bank and exit (no model needed)
  --temp FLOAT          Temperature (default 0.7)
  --top-p FLOAT         Top-p (default 0.8)
  --top-k INT           Top-k (default 20)
  --min-p FLOAT         Min-p (default 0 = off)
  --repeat-penalty F    Repetition penalty (default 1.0 = off)
  --presence-penalty F  Presence penalty (default 0)
  --thinking            Model is a thinking model (4096 max_tokens, strips <think> blocks)
  --repeats INT         Repeat each task N times (default 1; use 2+ for stochastic models)
  --target-failures INT Stop after this many failures (default 15)
  --holdout INT         Run this many extra holdout tasks after early stop (default 30; 0 to disable)
  --holdout-rerank INT  For predicted failures, generate 1 + N samples, keep best signal, compare to random (0 to disable; 2 for best-of-3)
  --no-early-stop       Run all 150 tasks even after reaching target failures
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

With `--repeats 1` (default), each task is run once. The probe stops after
`--target-failures` (default 15) failures are collected, then runs `--holdout`
(default 30) extra tasks to test the signal on unseen near-cusp work on the demo
task bank. If your model passes all 150 tasks, you will get NO FAILURES and no
signal can be detected. Use `--repeats 2` or `--repeats 3` with a higher temperature
to generate more variance, or `--no-early-stop` to force a full sweep.

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

This probe is a stripped-down discovery tool. The full calibration kit adds:

- 170-candidate signal scan (vs ~160 here)
- Intervention routing (retry, repair, rephrase strategies)
- Repair strategy sweeps (test_retry, rephrase, scaffold)
- Live OpenAI-compatible proxy with real-time gating
- Nightly relearning as your model distribution shifts
- HTML reports and AgentAnalysis.md export
- Custom task support

The probe finds the signal, tests it on a small holdout, and reports whether it
looks useful. The full kit turns it into a product.

## Validating the task bank

The probe includes reference implementations for all 100 tasks. You can
verify they all pass before running:

```bash
python probe.py --validate
```

This runs each reference against its own test cases. If any fail, something
is wrong with your Python environment.

## License

This probe is released under CC-BY-4.0 (see LICENSE-CONTENT.md). The full
calibration kit is commercial software under a separate EULA.
