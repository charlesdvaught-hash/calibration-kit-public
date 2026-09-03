# Local Model Calibration Kit

One run sweeps four axes simultaneously — sampling params, entropy signals,
intervention strategies, and architect/coder channel — with mid-run pruning
that cuts unproductive combinations before you pay for them. You get a
recommended operating point, the tradeoff curve behind it, and an
agent-readable config file that implements it automatically.

## Who this is for

You're running a local GGUF model in the 3-8B range — Qwen, Granite,
Llama, Mistral, Phi — and you need it to code competently in an agent
loop. The model fails often enough that you need to know:

- Which failures are predictable (entropy signal)
- Which failures are recoverable (intervention routing)
- When to stop trying (cost ceiling)
- What the best sampling config is for your specific quant (parameter sweep)

This kit answers all four in one run.

## Who this is NOT for

- **Frontier hosted models** (Opus, GPT-4, Gemini Pro) — these fail rarely
  and need different calibration approaches. Not tested. Not in scope.
- **Large local models** (27B+, 70B+) — may work, but untested. The
  failure patterns on competent models are subtler and the entropy
  signals may not separate the same way. If you test it and it works,
  tell us via federation.
- **Non-coding tasks** — the calibration suite is coding-specific. The
  method generalizes but the task battery doesn't.

## What you get

After one calibration run, you get a multi-axis tradeoff map — not just a
single config. Example output (illustrative — your numbers will vary):

| Operating point | Accuracy | Compute cost | What it is |
|---|---|---|---|
| **Base** | 81% | baseline | Your current config, measured |
| **Efficient** | 86% | +5% compute | Best cheap win from the swept region |
| **Recommended** | 92% | +21% compute | Best coverage per compute dollar |
| **Best sampled** | 94% | +50% compute | Highest accuracy found in the full sweep |

The kit also tells you whether a full parameter sweep is worth running:

- **Curve flattening** → full sweep ceiling is near your best sampled
  point. Save the compute. Don't run it.
- **Curve still climbing** → full sweep likely finds more. Run a
  compatible sweep tool (see [Where this fits](#where-this-fits)).
- **Local optimum found** → you have a good operating point now, but
  unexplored regions may contain a better one. Sweep if you need it.

You also get:

- **An entropy signal** (or explicit proof none works) for your specific
  model, with direction, threshold, and separation score
- **An intervention order** — which repair strategies work, ranked by
  coverage, with per-error-type routing
- **A cost ceiling** — max recovery stages, bail conditions, when to stop
  trying
- **Negative results** — what doesn't work for your model, so you don't
  waste time on it
- **An `AgentAnalysis.md` file** — drop it into any project and Devin,
  Claude Code, Cursor, or 20+ other agents read it as standing instructions

If you provide an architect/planner model, you also get:

- **Planner->coder channel sweep** — trace vs prompt vs decompose, short
  vs long, with coverage numbers per channel
- **Architect entropy signals** — plateau and first-spike trajectory that
  predict whether the architect's output will be useful to the coder
- **Cross-signal** — does the architect's entropy spike location predict
  whether the coder will recover from failure?

Every finding includes the data behind it. No hand-written rules, no
guesses — just what your model actually did on calibration tasks.

## Where this fits

Single-axis sweep tools like
[llm-sampling-tuner](https://github.com/BrutchsamaJeanLouis/llm-sampling-tuner)
find the optimal sampling params across a wide range. They do one axis
exhaustively.

This kit sweeps four axes simultaneously — sampling, entropy, interventions,
and channel — with adaptive pruning that cuts the factorial cost. It finds
the best *combination*, not just the best temperature.

If you only need sampling params tuned, llm-sampling-tuner is simpler and
cheaper. If you need to know which entropy signal predicts failure, which
intervention recovers it, and how the architect should hand off to the
coder — all in combination with the right sampling params — that's what
this kit does.

## Why small models

Calibration has the highest payoff on models that fail often enough to
measure. A 4B model at Q4 quantization fails on 20-40% of coding tasks —
enough failures to find patterns, rank interventions, and build a
recovery pipeline that meaningfully improves coverage.

A frontier model fails on 2-5% of tasks. The failures are subtler, less
patterned, and the entropy signals that work on small models may not
separate on models that are rarely uncertain. The calibration method
isn't wrong for large models — it's just that the signal-to-noise ratio
inverts. You'd need different signals, different interventions, and far
more test cases to get statistically meaningful results.

This kit is built where the signal is strongest. If you're running a
competent model and it's failing, the answer is usually a different
model or a different prompt — not a calibration sweep.

## Method

The kit runs a full-factorial sweep across four axes: sampling parameters,
entropy signals, intervention strategies, and architect/coder channel. For
~20 calibration questions, the full factorial is 200+ runs.

Mid-run adaptive pruning tracks which axis combinations are producing
coverage gains and which are not. Unproductive branches are terminated
before completion, reducing the effective run count — a 200+ candidate
sweep can drop to ~60 in practice when a calibrated entropy signal lets
you test the most-likely-wrong candidates first and bail early.

The sweep samples around your model's recommended base config — it does
not explore the full parameter space exhaustively. If the curve shows
the best operating point is at the edge of the sampled region, the kit
flags that a wider sweep may find more and names a compatible tool.

This is not a global search. It is a structured multi-axis search with
adaptive cost control, designed to find the best operating point for
your specific model in one hour — not to find the global optimum across
all possible parameter values.

## Built to keep improving

The kit doesn't just hand you fixed settings — it walks your agent through
finding its own, reasoning over its own model's calibration data. The
reflective step (`core_sweep.py`) pushes past the 9 built-in entropy
signals and 7 interventions toward whatever pattern your specific model
actually responds to. If your agent finds something the kit doesn't
already know, that's the interesting result, not a dead end: a human-gated
submission flow (`federation.py`) sends it back — benchmarked, sanitized,
nothing leaves your machine without you pressing y — and verified
improvements get folded into future releases. Buy once, keep getting
updates by pulling from the private repo you're invited to when you run
`register.py` (see Quickstart step 2).

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Register for repo updates (run once — invites you to the private repo)
python register.py --license-key bak_YOUR_KEY --github-user YOUR_USERNAME

# 3. Calibrate your model
python _calibrate_pipeline.py --model your-model.gguf

# 4. Export the analysis
python export_playbook.py --profile _calibration_profile_<label>.json --output AgentAnalysis.md

# 5. Drop AgentAnalysis.md into your project root
#    Your agent reads it automatically.
```

With an architect/planner model:

```bash
python _calibrate_pipeline.py --model coder.gguf --architect architect.gguf
python export_playbook.py \
    --profile _calibration_profile_<coder>.json \
    --architect _calibration_profile_<architect>.json \
    --output AgentAnalysis.md
```

Adaptive (minimum-compute) calibration — stops early when it has enough data:

```bash
python _calibrate_adaptive.py --model your-model.gguf
```

## Requirements

- Python 3.10+
- `llama-cpp-python` and `numpy` (see `requirements.txt`)
- A GGUF model — **3-8B recommended and tested**. Larger models may work
  but are untested. The calibration method assumes the model fails often
  enough to measure failure patterns; very competent models may not
  produce enough signal.
- A GPU is recommended but not required. Works on NVIDIA CUDA, AMD ROCm,
  Apple Metal, or CPU-only. CUDA is fastest; CPU works but takes longer.
- The kit auto-detects available VRAM and system RAM. If your model fits
  in your available memory, calibration will run.

## Before you calibrate

Check your model's config. The calibration sweeps sampling parameters
around the model's recommended values — wrong starting values produce
garbage data. Check `CORE_MODEL_CONFIGS.md` for verified configs, or check
the model's HuggingFace card.

The sweep discovers values — it does not hardcode them. It uses the
card-recommended values as a starting point and explores around them.
You don't tell it what to try; it tells you what worked.

Common gotchas:
- **Thinking models** need higher `max_tokens` (4096+) or they produce no
  output — thinking tokens consume the budget silently
- **Some models** require `presence_penalty` in instruct mode or outputs
  degenerate — check the card
- **Some models** are designed for greedy decoding (`temp=0.0`) — check
  the card
- **Some models** disable `top_k` — check the card

See `METHODOLOGY.md` for the full knob reference and `CORE_MODEL_CONFIGS.md`
for verified configs.

## Task suite

The kit ships with a built-in coding task battery aimed at 2-6B models.
These are the tasks that broke *my* models — the weak spots I kept hitting
when trying to get small local models to code competently. They may not be
your weak spots.

**What's included:**
- **Assembly tasks** — multi-file wiring problems (import resolution,
  interface matching, module assembly)
- **Hard function tasks** — single-function algorithmic problems
  (rle_decode, missing_ranges, merge_intervals, normalize_path)
  with deterministic eval-based tests

Every task has a deterministic pass/fail signal — the kit executes
the model's code in a sandbox and checks test cases. No LLM-as-judge,
no subjective grading.

**Why these tasks and not a standard benchmark:** Standard benchmarks
(MMLU, HumanEval) are increasingly in pretraining data. Models score
high on the benchmark and fail on real work. The built-in tasks are
novel enough that models haven't seen them, but simple enough that
a 3-4B model *should* be able to solve them — which means failures
are real signal about the model's capability, not evidence the task
was too hard.

**Bringing your own tasks:** The task format is simple — a JSON dict
with `id`, `desc`, `filename`, `func_name`, and `tests` (list of
`(expression, expected_result)` pairs). See `_arch_skel_hard.py` for
examples. If your models fail on different things than mine do, add
your own tasks and the calibration will measure *your* weak spots
instead of mine. If your custom tasks produce useful calibration data,
submit them via federation.

## Execution sandbox

The calibrator includes a Python-level sandbox (`_sandbox.py`) that is
auto-injected into every piece of model-generated code before it runs.
The sandbox blocks:

- Network access (`socket`, `create_connection`)
- Process spawning (`subprocess`, `os.system/popen`)
- `ctypes` (direct C function calls)
- Dangerous os functions (`exec*`, `spawn*`, `fork`, `kill`, `chmod`,
  `chown`, `symlink`, `link`)
- File writes outside the task's temp directory
- Blocked imports (`ctypes`, `multiprocessing`, `signal`, `pickle`,
  `marshal`)

The model's code only needs to read input files, process data, write
output files, and import sibling modules — all within the temp dir. The
sandbox blocks exactly the things the model's code should never do.

**What the sandbox does NOT block:** escape via `__subclasses__`
introspection, C extensions that bypass Python, memory exhaustion, CPU
beyond the 15-second timeout. Threat model is accidental damage from
model output, not a determined adversary. For hard sandboxing, run the
calibrator inside a container, VM, or firejail — it works fine inside
any of those.

## Reflect and experiment

After calibration, run `core_sweep.py` to analyze the results:

```bash
python core_sweep.py --profile _calibration_profile_<label>.json
```

This injects reflective prompts into your workspace:
1. Investigate the raw data by hand — patterns the automated analysis
   might have missed
2. What trends do you see?
3. What is yet untested?
4. How would you test it?
5. Now run the experiments
6. Reflect on the process

The pipeline analysis runs automatically — `export_playbook.py` renders
all findings from the profile JSON. But the pipeline can only report what
it measured. Investigating the raw data yourself is strongly recommended.

## Contribute improvements back

If your experiments produce a verified improvement over the stock
baseline, run `federation.py`:

```bash
python federation.py --profile _calibration_profile_<label>.json
```

This runs the federation gate:
1. Benchmarks your experimental branch against the stock baseline
2. Sanitizes all data (scrubs PII, company names, private code)
3. Shows a human y/n prompt with the diff and metrics
4. **Track A (yes):** submits the diff + metrics to the developer
5. **Track B (no):** submits a 4-sentence anonymized summary instead

No telemetry is sent until a human explicitly approves it. See
`LICENSE.md` for the grant-back terms.

## Examples

The `examples/` directory shows two pre-rendered analyses:

- **`granite_agents.md`** — Granite 4.1 3B. Entropy signal works
  (head_entropy, separation 0.91). Two recovery stages have real
  coverage (errors_nudge 33%, bounce 25%).
- **`qwen_agents.md`** — Qwen3-4B-Instruct. Entropy signal doesn't work
  (separation 0.00). No recovery stage recovered anything.

Same calibrator, opposite conclusions. There is no universal config.
Your model needs its own calibration.

## File manifest

| File | What it does |
|---|---|
| `SKILL.md` | Agent entry point — read this first. Full instructions for autonomous agents. |
| `LICENSE.md` | Custom EULA with grant-back clause. Read before using. |
| `METHODOLOGY.md` | Every knob, every phase, every signal. Read to understand what calibration does. |
| `CORE_MODEL_CONFIGS.md` | Verified sampling configs for common GGUF models. Check before calibrating. |
| `requirements.txt` | Python dependencies. |
| `_calibrate_pipeline.py` | Full 4-phase calibration runner (probe -> sweep -> analyze -> recommend). |
| `_calibrate_adaptive.py` | Minimum-compute adaptive calibration (stops early when enough data). |
| `_calibration_signals.py` | Signal analysis, early-exit logic, bail thresholds. |
| `_multifile_assembly.py` | Model loading, task definitions, prompts, code extraction, thinking stripping. |
| `_solve_pipeline.py` | Entropy capture, generation with trajectories, architect generation, test execution. |
| `_final_combined_test_v2.py` | Dynamic calibration and adaptive prompt functions. |
| `_arch_skel_hard.py` | Hard coding tasks and tests (the calibration task suite). |
| `_test_harness.py` | Test harness used by the solving pipeline. |
| `_sandbox.py` | Python-level execution sandbox for model-generated code. |
| `export_playbook.py` | Profile JSON -> AgentAnalysis.md exporter. |
| `core_sweep.py` | Reflective prompt injection — analyze trends and propose experiments. |
| `federation.py` | Local verification gate — benchmarks, sanitizes, human y/n, Track A/B submission. Submits to a webhook the developer operates separately. |
| `examples/` | Pre-rendered analyses from two models showing opposite conclusions. |

## How it works

1. **Probe:** Run your model on calibration tasks. Capture entropy
   trajectory, pass/fail, error type, time.
2. **Intervention sweep:** For each failure, try all recovery
   interventions in isolation (error feedback, temp retry, skeleton-fill,
   architect prompt, architect trace short/long, decompose).
3. **Analysis:** Rank entropy signals by separation. Compute coverage
   matrix. Greedy set cover for intervention order. Per-error-type
   effectiveness.
4. **Export:** Render findings into `AgentAnalysis.md` with specific
   numbers, negative results, and compute savings estimates.

See `METHODOLOGY.md` for the full explanation.

## Scope

The pipeline sweeps four axes simultaneously — sampling params, entropy
signals, intervention strategies, and architect/coder channel. The full
factorial for ~20 calibration questions is 200+ runs. Mid-run adaptive
pruning cuts unproductive branches before completion, reducing the
effective run count — a 200+ candidate sweep can drop to ~60 in practice
when a calibrated entropy signal lets you test the most-likely-wrong
candidates first and bail early. Without a signal (or if the signal
doesn't work for this model), you test all 200.

What calibration does NOT do:
- Give the model context it doesn't have
- Improve multi-turn reasoning over thousands of lines (context/RAG problem)
- Calibrate tool use, agentic loops, or long-horizon planning
- Handle tasks with no deterministic pass/fail signal
- Find the global optimum across all possible parameter values (it samples
  around the base config, not the full space — see [Method](#method))

## Security and privacy

- **No telemetry during execution.** Calibration runs entirely locally.
- **Phone-home is gated.** `federation.py` blocks until benchmarking
  completes AND a human presses y at a visible CLI prompt.
- **Data sanitization.** All submitted data is scrubbed: PII, company
  names, API keys, private variable names stripped before transmission.
- **Boundary isolation.** `federation.py` only diffs files within the
  `calibration-kit/` directory. It cannot read parent directories or
  private source code.
- **Track B fallback.** If you say no, only a 4-sentence anonymized
  summary is sent — no code, no diffs, no identifiers.

## Pricing

$4.99 USDC via AgentMart. Seller keeps 97% (3% platform fee).

## License

Custom source-available EULA with a grant-back clause. See `LICENSE.md`
for full terms.
