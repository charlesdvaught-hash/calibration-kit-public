# Calibration Probe

A free, standalone tool that tests whether your local GGUF coding model has a
usable entropy-based wrongness signal. One command, 60 realistic coding tasks,
~170 candidate signals scanned with permutation tests and Benjamini-Hochberg
correction, and an honest verdict.

This is a **hobbyist science kit**, not a lab implementation. It proves the
method can find a signal on example tasks. The full calibration kit learns
the signal on your own tasks and turns it into a live gate — see
[the upgrade path](#the-full-calibration-kit) below.

## Quick start

```bash
pip install llama-cpp-python numpy
python probe.py --model your-model.gguf
```

That's it. No API keys, no cloud, no accounts. Everything runs locally.

## What it does

1. Loads your GGUF model via `llama-cpp-python`
2. Generates code for the 60-task demo bank (14 assembly + 46 function tasks)
3. Captures per-token entropy trajectories during generation
4. Tests each generated solution against the task's test cases
5. Scans ~170 candidate entropy signals for pass/fail separation
6. Corrects for multiple comparisons (Benjamini-Hochberg, alpha=0.05)
7. Trains on the first 40 tasks, reserves the hardest 20 as holdout
8. Tests the discovered signal on the unseen holdout tasks
9. Prints one of four honest verdicts:
   - **SIGNAL FOUND** — a signal survived correction with |d| >= 0.2
   - **STRUCTURAL SIGNAL ONLY** — a length/budget signal separated pass/fail but can't be the sole gate
   - **NO SIGNAL FOUND** — nothing survived (honest null result)
   - **UNDERPOWERED** — too few failures to detect anything

## Example result

Qwen3-8B-Q5_K_M, with `--no-think` and the default 60-task bank:

- **Training:** 20 pass, 20 fail
- **Signal:** `kl_cent_f10_mean`, Cohen's d = +1.56, adjusted p = 0.0085
- **Holdout:** 16/20 correct predictions (80% vs 75% majority baseline)

This is a fingerprint on this model on these demo tasks, with some evidence it
generalizes to the held-out tasks.

## What the verdict means

**SIGNAL FOUND** means: on this specific model, on these 60 demo tasks, in
this specific run, there is an entropy trajectory feature whose value
systematically differs between correct and incorrect generations. This is a
fingerprint on the demo bank, not a universal rule. It may not transfer to your
actual tasks, other models, or other task types.

**STRUCTURAL SIGNAL ONLY** means: a length or thinking-budget signal (like
`n_tokens` or `think_frac`) separated pass from fail, but such signals can
reflect task shape or pipeline artifacts rather than wrongness — a generation
cut off by the token budget scores high on think_frac *because* it was
truncated, not because the model was uncertain. These are reported for
transparency but never shipped as the sole gate. They may still appear inside
composite signals (e.g. `think_frac × entropy`) that carry real entropy content.

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
  --thinking            Model is a thinking model (4096 max_tokens, strips thinking blocks)
  --no-think            Append /no_think to prompts (Qwen3 dual-mode soft switch)
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

If your model generates reasoning blocks before its answer (e.g. Qwen3-Thinking,
Qwen3.5), pass `--thinking`:

```bash
python probe.py --model qwen3-4b-thinking.gguf --thinking --temp 0.6 --top-p 0.95
```

This increases `max_tokens` to 4096 (thinking tokens consume budget) and
strips thinking blocks before extracting code. Without this flag, thinking
models will silently produce no code output because the thinking tokens
consume the entire 1200-token budget.

For Qwen3 dual-mode models, `--no-think` appends `/no_think` to prompts to
explicitly ask the model not to reason. This is distinct from `--thinking`
(which controls how output is handled) — without `--no-think`, a Qwen3 can
still spontaneously reason and fill the token budget with thinking.

**Important**: Check your model's HuggingFace card for the correct sampling
parameters. Qwen3 thinking uses temp=0.6, but Qwen3.5 thinking uses
temp=1.0. Using the wrong temperature produces bad results.

## Contributing your results

After running the probe, you can share your results to help map which models
have signals and which don't. See `contribute.py` or the
[submissions/](submissions/) directory. GitHub PRs auto-sync to the
HuggingFace dataset — no HF account needed.

**What gets shared:** model filename, quant label, per-task downsampled
entropy trajectory + pass/fail, signal scan results, timestamp.

**What does NOT get shared:** no prompts, no generated code, no user identity,
no IP address.

## Examples

`examples/` holds calibration runs with raw records. They disagree with each
other, and that is the point.

| model | bank | probes | failures | signal | transfer | recoverable |
|---|---|---|---|---|---|---|
| Qwen3-8B Q5_K_M (thinking) | 224-task | 224 | 37 | `think_frac` high=good | 0.838 mean, 100% above chance | 17/37 |
| Qwen3-4B-Instruct-2507 Q5_K_L | 60-task | 108 | 20 | `max_entropy`/plateau high=bad | 0.73 mean, 92% above chance | 11/20 |
| granite-4.1-3b Q5_K_M | 60-task | 60 | 8 | none — below chance | — | 4/8 |
| mini-coder-4b Q8_0 | 18-task | 36 | 11 | none | — | 4/11 |

Two models have usable signals that transfer to unseen tasks; two do not. That
is the honest number, and it is why you run this rather than copy someone else's
config.

## The full calibration kit

This probe is a stripped-down discovery tool. The full calibration kit adds:

- **Live proxy** — sits between your harness and your inference server, scores every generation in real time
- **Intervention routing** — retry, repair, rephrase strategies ranked by coverage
- **Nightly relearning** — the profile drifts with your actual task pool
- **Custom tasks** — calibrate on your own pass/fail tasks, not just the demo bank
- **HTML reports and AgentAnalysis.md** — agent-readable playbooks your coding assistant can follow
- **Mode separation** — thinking and non-thinking profiles are never pooled

The probe finds the signal, tests it on a small holdout, and reports whether it
looks useful. The full kit turns it into a product.

See `METHODOLOGY.md` for the full statistical pipeline, `CHANGELOG.md` for
feature history, and `public_probe_audit_checklist.md` for the cross-check
between the probe's fixes and the full kit.

## License

This probe is released under CC-BY-4.0 (see `LICENSE-CONTENT.md`). The full
calibration kit is commercial software under a separate EULA.
