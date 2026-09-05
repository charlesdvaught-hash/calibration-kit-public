# Local Model Calibration Kit

Calibrate your local GGUF model's coding behavior. Get a model-specific
analysis file any AI coding agent reads as standing instructions.

This is the **public evidence repository** — it contains the methodology,
example analyses, and documentation that prove the concept. The source
code lives in a private repository you get access to when you buy the kit.
See [Pricing](#pricing) below.

## Scope

This is not a "know if your model is right about anything" tool. It
calibrates against **benchmark-verifiable pass/fail tasks** — code with
automated tests. Every entropy signal, threshold, and intervention rank in
this kit comes from one question: did the generated code pass its tests,
yes or no. It has not been tested on open-ended or subjective output
(freeform Q&A, creative writing, anything without an automated correctness
check) — the entropy signal there is unproven, not assumed to transfer.
If your use case doesn't reduce to pass/fail, this isn't calibrated for it.

## What you get

After one calibration run:

- **A signal matched to what *your* model's own right and wrong look like**
  — or an explicit `none`. The kit searches ~170 candidate statistics over
  your model's own generations, corrects for having searched them all, and
  validates the winner two ways: on held-out records (does it separate
  new generations?) and on held-out *tasks* (does it separate generations
  of tasks it never saw?). Direction is discovered, never assumed: high can
  mean wrong, high can mean right, and which one it is differs by model.
  So far one of three models has a usable signal, and it transfers to
  unseen tasks — the other two got an honest `none`. Nothing here
  transfers between models, which is exactly why it has to be run against
  yours.
- **The statistical power behind that verdict**, so `none` is
  interpretable. "This model has no entropy signal" and "this run was too
  small to see one" are different answers, and the report tells you which,
  with the observed effect size, the smallest effect the run could have
  detected, and the `--repeats` setting that would settle it.
- **An intervention order** — which repair strategies work, ranked by
  coverage, with per-error-type routing. This works on every model
  calibrated so far, including the ones with no entropy signal.
- **A cost ceiling** — max recovery stages, bail conditions, when to stop
  trying.
- **An `AgentAnalysis.md` file** — drop it into any project and Devin,
  Claude Code, Cursor, or 20+ other agents read it as standing
  instructions.

## The evidence

### What you should expect

| model | bank | probes (unique) | failures | usable signal | recoverable |
|---|---|---|---|---|---|
| Qwen3-4B-Instruct-2507 (Q5_K_L) | 60-task | 108 | 20 | yes — `max_entropy`/plateau, high=bad; **transfers to unseen tasks** (0.73, above chance in 92% of splits) | 11/20 |
| granite-4.1-3b (Q5_K_M) | 60-task | 60 | 8 | none — underpowered (MDE d≥1.06); task-level check: below chance | 4/8 |
| Qwen3-4B-Instruct-2507 (Q5_K_L) | 18-task (superseded) | 180 ×3 | 32–33 | yes — early-window, replicated *on that bank only* | 30/33 |
| granite-4.1-3b (Q5_K_M) | 18-task (superseded) | 108 | 29 | none, at MDE d≥0.61 | 18/29 |
| mini-coder-4b (Q8_0) | 18-task (superseded) | 36 | 11 | none | 4/11 |

On the current task bank: one model has a usable signal, one does not.
**That is the honest number, and it is why you run this rather than copy
someone's config.** A model with no signal is a real answer — it tells
you not to spend compute on a gate that buys nothing, and you still get
the repair routing, which works on all three.

### Two holdouts, two questions

The record-level held-out split asks "does this signal separate *new
generations*?" It cannot ask "does it separate generations of *tasks the
bank never contained*?" — a held-out record can come from the same task
as a training record, so a signal that detects task identity (not
wrongness) passes while being useless on a new task. The profile therefore
also runs `task_holdout_validation`: whole tasks are excluded from
selection and fitting, then scored — plus a `transfer_estimate` that
takes the signal the full run selected and re-scores it on held-out tasks
across 300 random task splits.

On the current runs: qwen's selected signal **does** transfer (0.73 mean
balanced accuracy on unseen tasks, above chance in 92% of draws), while
granite's task-selected signal went below chance (0.87 train → 0.47 test)
— the failure mode this check exists to catch.

### What keeps per-model honest

If every model gets its own story, no story can be wrong. Four checks run
inside each single run:

- a **permutation test**, so a direction is never read off the sign of a
  noisy mean difference;
- **Benjamini-Hochberg correction** across all ~170 candidate statistics,
  so scanning cannot manufacture a winner;
- a **held-out split** — signal chosen and threshold fitted on training
  records, scored on records neither decision touched;
- a **task-level holdout** — whole tasks excluded from selection and
  fitting, then scored, so a signal must generalize to new questions, not
  just new generations of known ones.

Findings that survived those got pre-registered and re-tested on fresh
data anyway. The full chain, including a withdrawn claim and a test that
was designed wrong, is in the private repo's `research/` directory.

### Scope: the file, not the family

Every result above is scoped to one model, at one size, **at one
quantization**. Entropy is a property of the logit distribution and
quantization changes that distribution, so a Q4 of the same weights is a
different subject and needs its own run. Profiles record the exact
filename, the detected quantization tag and a file fingerprint; a run
from a different file will not overwrite an existing profile.

### The examples

The `examples/` directory contains pre-rendered analyses from the current
60-task bank:

- **`qwen_agents.md`** / **`qwen60_profile.json`** / **`qwen60_report.html`**
  — the model with a signal on this bank: `max_entropy`/plateau, high=bad,
  and a clear demonstration that a signature is per-model *and
  per-task-set*: the 18-task early-window result did not replicate here.
  The signal transfers to unseen tasks (0.73 balanced accuracy, 92% of
  task splits above chance).
- **`granite_agents.md`** / **`granite60_profile.json`** / **`granite60_report.html`**
  — no usable signal, underpowered at 8 failures (MDE d≥1.06), with a
  working coder-side repair order. The `none` case, delivered honestly.
  Its task-level check went below chance — the failure mode the check
  exists to catch.

Same calibrator, opposite conclusions. There is no universal config. Your
model needs its own calibration.

## How it works

1. **Probe:** Run your model on calibration tasks. Capture ~170 candidate
   statistics in a single generation pass — full-vocab entropy, commitment
   curves, KL divergence series, sampled-token surprisal and rank,
   trajectory-shape features, thinking-phase splits. Every signal the
   logits can support, captured once, reused for every analysis.
2. **Intervention sweep:** For each failure, try all recovery
   interventions in isolation (error feedback, temp retry, skeleton-fill,
   architect prompt, architect trace short/long, decompose).
3. **Analysis:** Rank entropy signals by separation. Compute coverage
   matrix. Greedy set cover for intervention order. Per-error-type
   effectiveness. Both holdout levels (record and task) plus the transfer
   estimate.
4. **Export:** Render findings into `AgentAnalysis.md` with specific
   numbers, negative results, and compute savings estimates.

See `METHODOLOGY.md` for the full explanation.

## Task suite

The kit ships with a built-in coding task battery aimed at 2-6B models.
These are the tasks that broke *my* models — the weak spots I kept hitting
when trying to get small local models to code competently. They may not
be your weak spots.

**What's included:**
- **Assembly tasks** — multi-file wiring problems (import resolution,
  interface matching, module assembly)
- **Hard function tasks** — single-function algorithmic problems
  (rle_decode, missing_ranges, merge_intervals, normalize_path, and 38
  more) with deterministic eval-based tests

Every task has a deterministic pass/fail signal — the kit executes the
model's code in a sandbox and checks test cases. No LLM-as-judge, no
subjective grading.

**Bringing your own tasks:** The task format is simple — a JSON file with
`id`, `desc`, `filename`, `func_name`, and `tests`. The kit's
`validate-tasks` command proves each task's reference against its own
tests before calibration starts, so a broken task can't produce a broken
signal.

## Security and privacy

- **No network calls at all.** The calibration pipeline, the exporter, the
  report renderer, and `federation.py` contain no network code. Not
  gated, not opt-in — there is none.
- **No telemetry during execution.** Calibration runs entirely locally.
- **`federation.py`** writes a sanitized contribution file locally. What
  you do with it is up to you.
- **Execution sandbox.** Model-generated code runs in a Python-level
  sandbox that blocks network access, process spawning, `ctypes`, and
  dangerous `os` functions. The threat model is accidental damage from
  model output, not a determined adversary — for hard sandboxing, run
  inside a container or VM.

## Requirements

- Python 3.10+
- `llama-cpp-python` and `numpy` (see `requirements.txt`)
- A GGUF model — **2-8B recommended and tested**. Larger models have stronger signals according to the research- but are beyond my current capability to test.
- The calibration method assumes the model fails often
  enough to measure failure patterns; very competent models may not
  produce enough signal.
- A GPU is recommended but not required. Works on NVIDIA CUDA, AMD ROCm,
  Apple Metal, or CPU-only. CUDA is fastest; CPU works but takes longer.

## Before you calibrate

Check your model's config. The calibration sweeps sampling parameters
around the model's recommended values — wrong starting values produce
garbage data. Check `CORE_MODEL_CONFIGS.md` for verified configs, or check
the model's HuggingFace card.

Common gotchas:
- **Thinking models** need higher `max_tokens` (4096+) or they produce no
  output — thinking tokens consume the budget silently
- **Some models** require `presence_penalty` in instruct mode or outputs
  degenerate — check the card
- **Some models** are designed for greedy decoding (`temp=0.0`) — check
  the card

See `METHODOLOGY.md` for the full knob reference and `CORE_MODEL_CONFIGS.md`
for verified configs.

## Pricing

**$59.99, one time** — with launch pricing for early buyers (currently  50%- less than $30 to test every model you own or run through Ollama). That buys the kit and
collaborator access to the private repository, so updates arrive with
`git pull`. No subscription, no seats, no usage metering. 

**[Buy it here →](https://buy.polar.sh/polar_cl_oPEsqZL29Nvuo6oX0GRF1DHDXgE75NOFAmy7V3oAjcU)**

Sold through [Polar](https://polar.sh), which is the merchant of record —
they handle payment and sales tax, and your purchase triggers the GitHub
invite automatically.

### What is guaranteed

The kit runs on your model and returns a **definite, statistically-backed
verdict**: either a signal with a threshold you can implement, or an
explicit `none` with the effect size observed, the smallest effect the run
could have detected, and the `--repeats` setting that would settle it.

If a completed run gives you neither a usable signal **nor** a repair
order that beats doing nothing — that is, nothing you can act on — email
the address in `SUPPORT.md` with your Polar order number for a full
refund. The guarantee is in `REFUND_POLICY.md` (shipped with the kit).

## License

Custom source-available EULA with a grant-back clause. See `LICENSE.md`
for full terms.
