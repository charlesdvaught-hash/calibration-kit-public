# Calibration Methodology

This document explains what the calibration kit measures and why.
The full implementation reference (signal formulas, algorithm details,
task suite source) is in the private repo — access it after purchasing.

---

## What this calibrates

The kit measures how a local LLM (GGUF, 3-8B) generates and repairs
code. It sweeps four axes simultaneously:

1. **Sampling parameters** — temp, top_p, top_k, presence_penalty, etc.
2. **Entropy signals** — which (if any) entropy trajectory feature
   predicts whether the model's output will be correct or wrong
3. **Intervention strategies** — which recovery methods work when the
   model fails, and in what order
4. **Architect/coder channel** — how the planner's output should be
   delivered to the coder (prompt vs trace vs decompose, short vs long)

The sweep tests combinations of these axes, not just each one
independently. Mid-run adaptive pruning cuts unproductive branches
before completion.

---

## What calibration finds

For your specific model, the kit determines:

- **Whether failures are predictable.** Some models produce entropy
  patterns that reliably predict wrongness before testing. Others
  don't — failures are random and unpredictable. You need to know
  which one you have.
- **Which recovery interventions work.** When the model fails, which
  repair strategies actually recover the task? The kit ranks them by
  coverage and finds the optimal order.
- **When to stop trying.** If the test gap is too wide after recovery
  stages, bailing saves compute. The kit finds the bail threshold.
- **How the architect should communicate with the coder.** Trace vs
  prompt vs decompose, short vs long — the kit measures which channel
  produces the best coder outcomes for your specific model pair.

---

## What calibration does NOT do

- Give the model context it doesn't have. If the model can't see the
  bug, no amount of calibration will produce the right answer.
- Improve multi-turn reasoning over thousands of lines (that's a
  context/RAG problem).
- Calibrate tool use, agentic loops, or long-horizon planning.
- Handle tasks with no deterministic pass/fail signal.

---

## Why no universal config exists

The same calibration pipeline produces opposite conclusions for
different models:

| Finding | Granite 4.1 3B | Qwen3-4B-Instruct |
|---|---|---|
| Best entropy signal | head_entropy (separation 0.91) | none (separation 0.00) |
| Best recovery stage | errors_nudge (33%) + bounce (25%) | none recovered (0%) |
| Converged? | yes | no |

Same tasks, same architect, same pipeline. Opposite results. This is
why the kit calibrates per-model rather than shipping a universal
config. The model designers tested on full-precision weights on A100
clusters — not your quantization on your hardware with your tasks.

---

## The calibration procedure (4 phases)

1. **Probe** — Run the model on calibration tasks. Capture entropy
   trajectory, pass/fail, error type, time.
2. **Intervention sweep** — For each failure, try recovery
   interventions in isolation (error feedback, temp retry,
   skeleton-fill, architect prompt, architect trace, decompose).
3. **Analysis** — Rank entropy signals by separation. Compute coverage
   matrix. Find optimal intervention order. Per-error-type routing.
4. **Export** — Render findings into `AgentAnalysis.md` with specific
   numbers, negative results, and compute savings estimates.

The adaptive variant (`_calibrate_adaptive.py`) doesn't wait until the
end to start learning — it reorders stages after each task and stops
early when it has enough data.

---

## Task suite

The kit ships with a built-in coding task battery aimed at 2-6B models.
These are tasks that broke our models — they may not be yours. Every
task has a deterministic pass/fail signal (eval-based tests, no
LLM-as-judge).

The task format is documented in the private repo. If your models fail
on different things, you can add your own tasks and calibrate against
your weak spots instead of ours.

---

## Re-calibrating

The playbook is a snapshot. To re-calibrate with different tasks, a
different architect, or more repeats, use the full pipeline or the
adaptive variant. More repeats = more data = higher confidence, but
more compute.

The full knob reference, signal formulas, algorithm details, and task
suite source are in the private repo's `METHODOLOGY.md`. Access it
after purchasing via `register.py`.
