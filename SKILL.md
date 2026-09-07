---
name: local-model-calibration-kit
version: 2.0.0
category: developer-tools
price_usd: 59.99
storefront: polar
runtime: local-python
requires_gpu: false
requires_api_keys: false
sends_telemetry: false
tags: [calibration, local-models, gguf, entropy, optimization, agent-tools, llm]
---

# Local Model Calibration Kit

## What this is

A runtime calibration layer for local coding models. Install it, run
`calibrate setup`, start `calibrate proxy`, and point your existing coding
harness at one URL. It records every generation, scores it with a
model-specific entropy signal, and re-learns from your recent work every night.

It runs entirely on your hardware — no API calls, no cloud, no telemetry unless
you explicitly approve it. It is not a harness; it sits between Aider, Continue,
Cline, LocalHarness, mini-swe-agent, or any OpenAI-compatible client and your
local inference server (llama-server, LM Studio, Ollama, vLLM).

You can also run a full offline calibration from a task bank to build a profile
from scratch.

**Scope:** this calibrates against benchmark-verifiable pass/fail tasks —
code with automated tests. Every signal and rank it produces comes from
"did the generated code pass its tests." It is not tested on open-ended or
subjective output, and the entropy signal is not assumed to transfer there.

## Quickstart for buyers

```bash
# 1. Auto-detect backend, pick a profile, write settings.
calibrate setup --profiles-dir examples

# 2. Start the proxy.
calibrate proxy --config /path/to/settings.json

# 3. Point your harness at http://127.0.0.1:9090/v1.
```

The proxy returns `X-Calibration-Verdict` and an `intervention_plan` for every
response, and re-builds the profile from the last `--window-tasks` every
`--reanalyze-at` night.

## Why buy this instead of building it?

You could build this. The methodology is published. The signals are known. The
intervention strategies are standard. But building it from scratch means:

- Writing ~7,000 lines of calibration infrastructure (model loading, entropy
  capture, trajectory analysis, intervention sweep, test harness, task suite)
- Debugging silent failures (thinking models with low max_tokens produce no
  code — no error, just garbage data)
- Discovering edge cases by wasting electricity on bad runs (wrong sampling
  params, missing presence_penalty, inverted entropy signals)
- Re-implementing the greedy set-cover intervention ordering, per-error-type
  routing, and adaptive early-stop logic

This kit gives you all of that, done, tested, and ready to run. The value is
**time and electricity saved**, not a secret algorithm. You're paying $59.99 to
skip weeks of infrastructure work and focus on what matters: calibrating your
model and using the results.

Each calibration scan tries 5-6 different methods and combinations. We
eliminated several other options through trial and error across thousands of
coding attempts over a variety of small (>4B) models, but the philosophies
hold for most open-weight local models — the research papers confirm. You
get the benefit of that work without paying for the electricity it took to
do it.

## What you get

The runtime proxy plus one calibration run (time depends on your hardware —
minutes on a recent GPU, longer on CPU):

- **An OpenAI-compatible runtime proxy** — `calibrate setup` + `calibrate proxy`
  auto-detects a local backend, matches the profile, records every request,
  scores generations in real time, and re-learns from the last N tasks on a
  nightly schedule.
- **A tested verdict on whether entropy predicts correctness for your model.**
  Two of four models calibrated so far have a usable signal — see "The core
  claim" below. The kit reports a direction and threshold only when the
  difference survives a permutation test and a multiple-comparison
  correction; otherwise it reports `none` and ships no threshold. A `none`
  on the entropy signal still comes with a full repair routing rule — the
  kit always tells you what to do with failures, just not always how to
  predict them before tests run.
- **The statistical power behind that verdict**, so `none` is interpretable:
  observed effect size, the smallest effect the run could have detected, and
  the `--repeats` setting that would settle it
- **An intervention order** — which repair strategies work, ranked by coverage,
  with per-error-type routing
- **Pre-test failure routing** — which signal split best separates the
  failure modes, and which intervention to try first for each side, readable
  before any test executes
- **A cost ceiling** — max recovery stages, bail conditions, when to stop trying
- **Negative results** — what doesn't work for your model, so you don't waste
  time on it
- **An `AgentAnalysis.md` file** — drop it into any project and Devin, Claude
  Code, Cursor, or 20+ other agents read it as standing instructions.

If you provide an architect/planner model, you also get:

- **Planner->coder channel sweep** — trace vs prompt vs decompose, short vs long,
  with coverage numbers per channel
- **Architect entropy signals** — plateau and first-spike trajectory that predict
  whether the architect's output will be useful to the coder
- **Cross-signal** — does the architect's entropy spike location predict whether
  the coder will recover from failure?

## The core claim

**Usable uncertainty signals exist in small local models. They are per-model,
and they are not the statistics the field reports.** That is the whole
product, and it is now demonstrated rather than asserted.

### Demonstrated

For `Qwen_Qwen3-4B-Instruct-2507-Q5_K_L.gguf`, the **first ten tokens** of a
generation predict whether the finished code passes its tests. Confirmed on
three independent samples, pre-registered before the confirming data existed:

| signal | direction | run 2 | run 3 | p |
|---|---|---|---|---|
| `first10_max` | high=good | +0.784 | **+0.765** | <0.0001 |
| `first10_std` | high=good | +0.707 | **+0.670** | 0.0005 |
| `phi_first10_mean` | high=bad | −0.594 | **−0.624** | 0.0014 |
| `q_argmax` | high=good | +0.634 | **+0.821** | 0.00005 |
| `q1_over_mean` | high=bad | −0.665 | **−0.630** | 0.0010 |

**Scoped to the 18-task bank.** On the 60-task bank (two independent
samples, 2026-09-05) these directions held but significance did not
replicate — the signature is a property of the model *and the task
distribution*, not the model alone. See `research/OUTCOME_005`. On the
60-task bank the surviving signal was different: `max_entropy`/`plateau`
(high=bad, d≈−1.0), and it **transfers to unseen tasks** — 0.73 mean
balanced accuracy on held-out tasks across 300 random task splits, above
chance in 92% of draws. The kit now reports both record-level and
task-level holdout in every profile, so a buyer can see whether a signal
generalizes to new questions or only to new generations of known ones.

A correct generation opens with a brief sharp burst of genuine uncertainty and
then settles; an incorrect one opens flat and uniformly committed. **Early
confidence predicts wrongness.**

The same per-model, validated-signal pattern held on `Qwen3-8B` (Q5_K_M,
thinking mode, 224-task bank): `think_frac` (fraction of generation spent in
reasoning tokens) separates pass from fail at d=+2.07 and transfers to unseen
tasks — 0.838 mean balanced accuracy across 300 task splits, above chance in
100% of draws. Different model, different signal, same methodology: the kit
finds whatever signature exists for *your* model, or reports `none`.

On the same data, the reported statistics find nothing: `max_entropy` d=+0.17
(p=0.39), `mean_entropy` d=+0.15 (p=0.46). A short opening spike plus a long
calm tail averages to the same number as a flat middling trajectory. Averaging
across a generation destroys the signal; pooling across models cancels what
survives. One prominent measure advertises being "comparable across models and
tasks without threshold recalibration" — that is the assumption this result
contradicts.

### Honest hit rate

Two of four models calibrated have a usable entropy signal — Qwen3-8B
(thinking mode) and Qwen3-4B-Instruct-2507. Granite-4.1-3b has neither a
signal nor a sharp repair edge. Mini-coder-4b has no entropy signal but
returns a working repair routing rule (test_retry first, logic vs assertion
routing, stop after chain). A `none` on the entropy signal is not a `none`
on the calibration — the kit still tells you what to do with failures, just
not how to predict them before tests run. **You cannot know which case you
are in without measuring your own model**, which is the reason this runs on
your machine against your file.

### Scope

Every result is scoped to one model, one size, **one quantization**. Entropy
is a property of the logit distribution and quantization changes it, so a Q4
of the same weights is a different subject. Profiles record the filename, the
quantization tag and a file fingerprint.

### What keeps per-model claims falsifiable

Permutation test; Benjamini-Hochberg correction across all ~170 candidates;
held-out split (signal chosen and fitted on train, scored on unseen records —
qwen: 0.631 → 0.707); and `--seed`, because re-running with the same seed
replays identical generations and a real second sample needs a different one.
Anything surviving all four still got pre-registered and re-tested on fresh
data. The full chain — including a withdrawn claim and a confirmation test
that was designed wrong — is in `research/`.

Every entropy claim published before 2026-09-04 has been withdrawn: those
directions were read off the sign of a mean difference with no test. See
CHANGELOG.md.

## Built to keep improving

This kit ships with ~170 candidate statistics captured in a single
generation pass (entropy cropped and full-vocab, surprisal, KL series,
commitment mass, trajectory shape, thinking-phase splits) and 7 known
interventions. That is not a claim that they are exhaustive — it's a
starting point.
`core_sweep.py`'s reflective prompts exist specifically to push the host
agent past what's already coded: investigate the raw profile JSON, look for
signal interactions the automated exporter didn't surface, and if your
model responds to a pattern none of the candidates capture, that is the
interesting outcome of a calibration run, not a failure. The task set is
yours too: `calibrate.py run --tasks my_tasks.json` calibrates on the
buyer's own pass/fail tasks (see CUSTOM_TASKS.md). `federation.py` exists to receive exactly that — a genuine code
change, not just a config tweak — gated behind a mandatory human y/n before
anything leaves the machine. Verified improvements get folded into future
releases; buyers keep ongoing access through the private repo their purchase
invited them to, so this is closer to a living, crowd-calibrated project
than a one-time script purchase.

## What this is NOT

- Not a universal prompt or config. Every finding is model-specific.
- Not a replacement for RAG or repository context. Calibration can make candidate
  search more efficient, but it cannot provide context your model never received.
- Not a longitudinal benchmark. Each playbook is a single-run snapshot. If you
  change tasks, configs, or methodology between runs, score differences do NOT
  mean the model improved.
- Not limited to simple tasks. The pipeline can sweep 200+ candidates across
  temperatures, channels, and interventions. Calibration makes that search more
  efficient when a useful signal exists.

---

## How to run it (full instructions for agents)

There are two paths. **The runtime proxy is the product** — the full
calibration exists to build a profile for it.

- **Path 1 — runtime proxy (primary).** `calibrate setup` + `calibrate proxy`,
  point the harness at the proxy URL, done. If a profile matching your model
  exists, live scoring starts immediately. If not, run the proxy in `observe`
  mode and it records data anyway; `calibrate learn` turns a labeled proxy log
  into a profile with no GPU time.
- **Path 2 — full calibration (profile builder).** The offline pipeline below:
  probe a task bank, sweep recovery interventions, analyze, export. This is
  still the strongest way to build a robust profile from scratch when no
  example profile exists for your model and quantization.

Path 1 is covered in the Quickstart above and expanded under "The runtime
proxy" below. The steps that follow are Path 2.

### Prerequisites (for Path 2 — full calibration)

- Python 3.10+
- A local GGUF model file (the coder model you want to calibrate)
- Optionally: a second GGUF model (architect/planner) for planner-coder tests
- `llama-cpp-python` and `numpy` (see `requirements.txt`)
- A GPU is recommended but not required. The kit works on any hardware
  llama-cpp-python supports — NVIDIA CUDA, AMD ROCm, Apple Metal, or CPU-only.
  CUDA is the easiest to set up and gives the fastest calibration runs. CPU
  mode works but calibration will take significantly longer.
- The kit auto-detects available VRAM and system RAM. It does not assume a
  specific GPU model or memory size. If your model fits in your available
  memory, calibration will run.

### Step 1: Install dependencies

```bash
pip install -r requirements.txt
```

For GPU acceleration (CUDA):

```bash
# Linux/macOS
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --force-reinstall --upgrade --no-cache-dir

# Windows PowerShell
$env:CMAKE_ARGS="-DGGML_CUDA=on"; pip install llama-cpp-python --force-reinstall --upgrade --no-cache-dir
```

### Step 2: Repo updates (nothing to run)

Repository access came with the purchase — Polar invites the buyer's GitHub
account as a collaborator automatically at checkout. Accepting that invite
(GitHub emails it) is all it takes; `git pull` then gets future updates.
There is no key to enter and no registration step.

If the invite never arrived, that is a support question, not a setup step —
see `SUPPORT.md`.

### Step 3: Check your model's config (MANDATORY)

You are an autonomous agent with file access. You already know (or can read)
the user's local config files, their existing model settings, and their
hardware setup. Use that knowledge. This step has two parts:

**Part A: Check the user's local configs (you already have access)**

- Look for existing config files the user has for this model (e.g. their
  llama-cpp-python settings, their Ollama Modelfile, their LM Studio config,
  a `sampling_params` block in their own harness, etc.)
- Check what sampling parameters they already use — these are a starting
  point, not a constraint. The calibration will sweep around them.
- Note their hardware: available VRAM, system RAM, GPU type. The kit
  auto-detects this but confirming avoids surprises.
- If the user has an existing `AGENTS.md` or `AgentAnalysis.md` for this
  model, read it — it may contain prior calibration findings.

**Part B: Check the HuggingFace model card**

Fetch the model card from HuggingFace (or the official repo) and verify:

1. **Sampling parameters** — what does the card recommend? These differ
   significantly between model families. The card is the authority, not
   guesses or family assumptions.
2. **Thinking mode** — does the model generate reasoning tokens? If yes:
   use max_tokens=8192+ (1200 will silently produce no code), strip thinking
   blocks before extraction, and the calibration should test both thinking
   and no-thinking modes to compare bandwidth cost.
3. **Architecture** — hybrid attention, MoE, multimodal? Affects VRAM and KV
   cache. Hybrid attention models have smaller KV cache than standard
   transformers of the same size.
4. **Framework compatibility** — does llama-cpp-python support this model?
   Check the minimum version required.
5. **Recommended output length** — some cards specify max_tokens per task
   type. Using too few silently truncates output.

The `CORE_MODEL_CONFIGS.md` file has verified configs for common models —
check it first to avoid re-verifying a model that's already been looked up.

**Do NOT skip this step.** Wrong configs produce silent garbage data that
wastes your entire calibration run and the user's electricity.

**Important: the sweep discovers values — it does not hardcode them.** The
calibration pipeline sweeps sampling parameters, intervention strategies, and
entropy signals. It does not assume "sweep temp at 0.0, 0.3, 0.6" or "try
tail_tokens 50, 100, 250, 400." It uses the model's card-recommended values
as a starting point and explores around them. The pipeline finds what works
for THIS model — you don't tell it what to try, it tells you what worked.
The analytical-vs-deliberative (thinking vs no-thinking) comparison is part
of the sweep, not a separate manual step.

### Step 4: Run calibration

**Execution environment:**

The calibrator includes a Python-level sandbox (`_sandbox.py`) that is
auto-injected into every piece of model-generated code before it runs.
The sandbox blocks:

- **Network access** — `socket`, `create_connection` blocked
- **Process spawning** — `subprocess.run/call/Popen`, `os.system/popen` blocked
- **ctypes** — direct C function calls blocked
- **Dangerous os functions** — `exec*`, `spawn*`, `fork`, `kill`, `chmod`,
  `chown`, `symlink`, `link` blocked
- **File writes outside the temp directory or cwd** — `open(..., "w")` to
  paths outside the task's temp dir or the process's current working
  directory is blocked
- **Blocked imports** — `ctypes`, `multiprocessing`, `signal`, `pickle`,
  `marshal`

The sandbox is on by default. You can disable it per-run by passing
`sandbox=False` to the test harness, but don't unless you understand why.

**What the sandbox does NOT block** (be honest about this):

- Escape via `__subclasses__` introspection. A determined adversary can
  walk `().__class__.__bases__[0].__subclasses__()` to find blocked
  objects and call them directly. This sandbox is not designed to stop
  that.
- C extensions that bypass Python-level restrictions.
- Memory exhaustion. Use `resource.setrlimit` on Unix if you need that.
- CPU exhaustion beyond the 15-second wall-clock timeout.

**Threat model:** accidental damage from a local model's generated code
— a 2-9B model producing code that makes network calls, writes outside
the temp dir, or spawns processes. NOT a determined adversary trying to
escape. For hard sandboxing, run the calibrator inside a container, VM,
or firejail. The calibrator works fine inside any of those.

You can also use your own sandbox instead — the calibrator doesn't care
where it runs as long as it can load the model and execute Python.

**Coder-only calibration:**

```bash
python calibrate.py run --model /path/to/your-model.gguf
```

**With an architect/planner model:**

```bash
python calibrate.py run --model /path/to/coder.gguf --architect /path/to/architect.gguf
```

**Adaptive (minimum-compute) calibration** — stops early when it has enough data:

```bash
python calibrate.py adaptive --model /path/to/your-model.gguf
```

The calibrator runs 4 phases:
1. **Probe** — run tasks, capture entropy trajectories, record pass/fail
2. **Intervention sweep** — try every recovery strategy on every failure
3. **Analysis** — rank entropy signals, compute coverage, greedy set-cover
   intervention ordering, per-error-type routing
4. **Recommend** — write a `_calibration_profile_<model-label>.json`

### Step 5: Export the analysis

```bash
python calibrate.py export --profile _calibration_<label>.json --output AgentAnalysis.md
```

**With an architect profile:**

```bash
python calibrate.py export \
    --profile _calibration_<coder>.json \
    --architect _calibration_<architect>.json \
    --output AgentAnalysis.md
```

The output file is named `AgentAnalysis.md` to avoid overwriting an existing
`AGENTS.md` in the target project. Rename or append as needed.

### Step 6: Use the analysis

Copy `AgentAnalysis.md` to your project root (or append to an existing
`AGENTS.md`). Your coding agent reads it as standing instructions.

### Step 6.5: The runtime proxy — the primary use of the kit

The kit ships an OpenAI-compatible proxy that scores live generations with the
profile and re-learns from recent work overnight. This is the day-to-day
interface: once a profile exists, the proxy is what you run.

One-time setup:

```bash
calibrate setup --profiles-dir examples
```

This auto-detects a local backend (llama-server, LM Studio, Ollama, vLLM),
selects a matching profile, writes a settings file, and prints the command for
Aider/Continue/Cline.

Run the proxy:

```bash
calibrate proxy --config /path/to/settings.json
```

Then point the harness at `http://127.0.0.1:9090/v1`.

Useful flags:

- `--reanalyze-at 02:00 --window-tasks 200` — re-learn every night from the
  last 200 unique tasks.
- `--mode observe` — record only, do not gate.
- `--mode gate` — regenerate likely-wrong responses with a different
  seed/temperature.

Every response has headers:

- `X-Calibration-Verdict` — `probably_fine`, `likely_wrong`, etc.
- `X-Calibration-Profile` — which profile was used.
- `X-Calibration-Request-Id` — look up the full record later.

The `calibration` payload includes `intervention_plan` with the ranked
escalation order and the conditional signal-failure routing rules. See
`examples/harness-integrations/README.md` for harness-specific configs.
The analysis contains:
- Model-specific entropy signal, direction, threshold, separation
- Intervention order with recovery rates and sample sizes
- Error-type routing table
- Signal-based failure routing (pre-test) — the failure-mode split and the
  first-try recommendation per cluster
- Cost ceiling and bail conditions
- Negative results (what doesn't work)
- Single-run snapshot caveat
- Planner-coder channel findings (if architect was calibrated)

### Step 7: Analyze the results (automatic + manual)

The pipeline analysis runs **automatically** — `export_playbook.py` extracts
and renders all findings from the profile JSON. But the pipeline can only
report what it measured. It cannot notice patterns you (the host agent) might
see by looking at the raw data yourself.

**It is strongly recommended that you investigate apparent trends by hand**
(meaning: you read the profile JSON, look at the raw data, and check for
patterns the automated analysis might have missed). Specifically:

- **Read the raw profile JSON.** The exporter renders the highlights, but the
  full data (all 9 entropy signals, every intervention's coverage, every
  task's pass/fail trajectory) is in the JSON. Look for patterns the exporter
  didn't surface.
- **Check for signal interactions.** Does head_entropy work for syntax errors
  but not logic errors? Does the architect's spike position predict recovery
  only on certain task types? The automated analysis ranks signals globally;
  you can slice them per-error-type or per-task-type.
- **Look for anomalies.** A task that failed all 6 recovery stages is
  interesting — why? A signal with separation 0.4 (not great, not useless)
  might become 0.8 if you filter by task difficulty. The pipeline won't find
  this; you can.
- **Compare thinking vs no-thinking.** If both modes were calibrated, compare
  the profiles directly. The pipeline exports each as a separate snapshot;
  you can identify which mode is more efficient for this model.

Run `core_sweep.py` to get structured reflective prompts that guide this
analysis:

```bash
python core_sweep.py --profile _calibration_profile_<label>.json
```

This injects 5 reflective prompts into your workspace:
1. "What trends do you see?" — analyze the calibration data
2. "What is yet untested?" — identify gaps in the sweep
3. "How would you test it?" — design minimal experiments
4. "Now run the experiments" — execute and compare
5. "Reflect on the process" — meta-evaluation

You can answer these prompts in your own reasoning loop, or use
`--interactive` to type responses, or use `--export-prompts` to save them
as a markdown file for later. The prompts are a guide, not a constraint —
follow your own analysis instincts too.

### Step 8 (optional): Contribute improvements back

If your experiments produce a verified improvement over the stock baseline,
run `federation.py` to submit it:

```bash
python federation.py --profile _calibration_profile_<label>.json
```

This runs the federation gate:
1. Benchmarks your experimental branch against the stock baseline
2. Sanitizes all data (scrubs PII, company names, private code)
3. Shows you (the human) a y/n prompt with the diff and metrics
4. **Track A (yes):** submits the diff + metrics to the developer's webhook
5. **Track B (no):** submits a 4-sentence anonymized summary instead

**No telemetry is sent until you explicitly approve it.** The script pauses
terminal execution and requires a keyboard y/n input. If you say no, the diff
is purged from memory and only an anonymized conceptual summary is sent.

See `LICENSE.md` for the legal terms (grant-back clause, Track A/B).

---

## File manifest

| File | What it is |
|---|---|
| `SKILL.md` | This file — your entry point. Read this first. |
| `LICENSE.md` | Custom EULA with grant-back clause. Read before using. |
| `SUPPORT.md` | How to get help, what support covers, and what it does not. |
| `REFUND_POLICY.md` | The guarantee, and how to claim it. |
| `METHODOLOGY.md` | The building blocks: every knob, every phase, every signal. Read this to understand what the calibration actually does. |
| `CORE_MODEL_CONFIGS.md` | Verified sampling configs for common GGUF models. Check before calibrating. |
| `requirements.txt` | Python dependencies (llama-cpp-python, numpy). |
| `calibrate.py` | The CLI entry point — `run`, `adaptive`, `export`, `report`, `learn`, `reanalyze`, `converge`, `setup`, `proxy`. |
| `calibration_proxy/` | The runtime proxy: OpenAI-compatible server, verdict scoring, profile manager, gate mode, nightly reanalysis. |
| `_calibrate_pipeline.py` | Full 4-phase calibration runner (probe -> sweep -> analyze -> recommend), behind `calibrate.py run`. |
| `_calibrate_adaptive.py` | Minimum-compute adaptive calibration (stops early when enough data), behind `calibrate.py adaptive`. |
| `_calibration_signals.py` | Signal analysis, early-exit logic, bail thresholds. |
| `_multifile_assembly.py` | Model loading, task definitions, prompts, code extraction, thinking stripping. |
| `_solve_pipeline.py` | Entropy capture, generation with trajectories, architect generation, test execution. |
| `_final_combined_test_v2.py` | Dynamic calibration and adaptive prompt functions. |
| `_arch_skel_hard.py` | The original four single-function tasks, the eval-based test runner, and the architect skeleton prompts. |
| `_task_bank.py` | The rest of the single-function task bank (42 tasks), each with a reference implementation. Run `python _task_bank.py` to verify every expected value. |
| `_test_harness.py` | Test harness used by the solving pipeline. |
| `_sandbox.py` | Python-level execution sandbox — blocks network, subprocess, ctypes, writes outside temp dir in model-generated code. |
| `export_playbook.py` | Profile JSON -> AgentAnalysis.md exporter (the renderer), behind `calibrate.py export`. |
| `core_sweep.py` | Reflective prompt injection — asks you to analyze trends and propose experiments. |
| `federation.py` | Local verification gate — benchmarks, sanitizes, human y/n, writes a local file. You send it by opening a PR or issue; nothing is transmitted automatically. |
| `examples/qwen3-8b_*` | Qwen3-8B Q5_K_M thinking-mode run on the 224-task bank — signal found, transfers to unseen tasks (0.838). |
| `examples/qwen60_*` | Qwen3-4B-Instruct-2507 on the 60-task bank — signal found, transfers (0.73). |
| `examples/granite60_*` | Granite-4.1-3b on the 60-task bank — `none`, task-level holdout caught a false positive. |
| `examples/mini-coder-4b_*` | mini-coder-4b on the 18-task bank — `none`. |
| `examples/qwen_*`, `examples/granite_*` | Early 18-task runs, kept for history — superseded by the 60-task sets. |
| `examples/harness-integrations/` | Copy-paste proxy configs for LocalHarness, mini-swe-agent, Aider, Continue, Cline, plus backend notes. |

## Example outputs

**Qwen3-8B Q5_K_M, thinking mode** (224-task bank — 164 HumanEval + 60
built-in, 224 probes, 37 failures):
- Signal: `think_frac`, high=good, d=+2.07, survives correction.
- Transfers to unseen tasks: 0.838 mean balanced accuracy across 300 task
  splits, above chance in 100% of draws.
- Pre-test failure routing: `think_frac` splits "didn't engage" failures
  (syntax/empty output) from "thought but wrong" (assertion/logic/name/type),
  each cluster with its own first-try intervention.
- Recovery: 17 of 37 failures recoverable coder-side.

**Qwen3-4B-Instruct-2507 Q5_K_L** (60-task bank, 108 probes, 20 failures):
- Signal: `max_entropy`/plateau shape, high=bad, d≈−1.0.
- Transfers to unseen tasks: 0.73 mean balanced accuracy, above chance in
  92% of draws.
- Recovery: 11 of 20 failures recoverable.

**Granite-4.1-3b Q5_K_M** (60-task bank, 60 probes, 8 failures):
- Signal: **none** — underpowered at 8 failures (MDE d≥1.06), and the
  task-level holdout caught a false positive (0.87 train → 0.47 test).
- Recovery: 4 of 8 failures recoverable coder-side.

**mini-coder-4b Q8_0** (18-task bank, 36 probes, 11 failures):
- Entropy signal: **none** (d=+0.09, underpowered — could only detect d≥1.01).
- But the repair rule is real and actionable: `test_retry` recovers 4/11,
  logic errors route to `test_retry` first (3/4, 75%), assertion errors are
  mostly unrecoverable (1/7, 14% — try once then escalate). The kit told
  the user exactly what to do with failures; what it couldn't do was gate
  generation preemptively, because 11 failures wasn't enough to sharpen a
  signal from.

Two of four models have entropy signals that hold up on tasks they never
saw; granite has neither signal nor a sharp repair edge; mini-coder has no
entropy signal but a usable repair routing rule. The kit tells you which
case you are in — and "no gating signal, here's your repair order" is still
a real result.

## Security and privacy

- **No telemetry during execution.** The calibration runs entirely locally.
- **Nothing is transmitted.** `federation.py` completes Phase 3+4, takes a
  human y/n at a visible CLI prompt, and then writes a local file. There is no
  endpoint on the other end.
- **Data sanitization.** All submitted data is scrubbed: PII, company names,
  API keys, private variable names, comments are stripped via regex before
  any network transmission.
- **Boundary isolation.** `federation.py` only diffs files within the
  `calibration-kit/` subdirectory. It cannot read or diff parent directories,
  environment variables, or your private source code.
- **Track B fallback.** If you say no, only a 4-sentence anonymized conceptual
  summary is written — no code, no diffs, no identifiers.

## Pricing

$59.99, one time, through Polar (merchant of record). The purchase grants
collaborator access to the private repository, which is how updates are
delivered. Full terms in `REFUND_POLICY.md` and `SUPPORT.md`.

## License

Custom source-available EULA with a grant-back clause. You can:
- Use the kit on your own models
- Modify and adapt the code
- Use modifications in commercial projects

You must (see `LICENSE.md` for full terms):
- Submit verified improvements back via Track A (diff) or Track B (anonymized
  summary) — `federation.py` prepares the file; you open the PR or issue
- Not redistribute the unmodified kit to non-buyers

This is modeled on the Avaya SDK grant-back and Epic Games Unreal Engine EULA
precedents: core optimizations are granted back to the engine provider so the
community benefits.
