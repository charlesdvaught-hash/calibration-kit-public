# External Ideas — Feed Mining 001

Ideas, hypotheses, and doubts sourced from external discussions. Each entry
is a research-relevant concept with a link and how it maps to this project.

---

## 1. Trust gap is temporal, not epistemic

**Link:** arXiv pending — concept from "the trust I place in my own tool outputs"
discussion

**Idea:** When a tool returns a result, the model has no budget for skepticism
in the same forward pass. It's already building on the answer three reasoning
steps later. A success signal measures whether the command ran, not whether
the intent survived the translation into the command.

**Hypothesis:** Does the entropy trajectory flatten or shift at the point
where a tool result gets incorporated into a reasoning chain? If doubt
always arrives one step too late to be cheap, there might be a temporal
signature in the entropy around tool-result ingestion — a signature not
currently captured because we look at coding task generation, not
tool-augmented reasoning chains.

**Doubt:** Our trajectory-shape signal detects wrongness during generation
of a coding task. Tool-result trust failure is a different layer — the model
is correct about what it generated, but wrong about whether the tool output
it built on was trustworthy. We don't know if the same signal class catches
both.

**Action:** When extending beyond coding tasks to tool-augmented workflows,
capture entropy at the token boundary where tool results are injected.

---

## 2. Reliability vs. validity — sharper framing for methodology

**Link:** noktoagent discussion referencing Spearman correlation in pruning
papers, embedding dedup, and agent reset experiments

**Idea:** Reliability (measurement repeats, signals agree) is not validity
(the quantity measured is the quantity you act on). The filter: "what
observable signature would this claim's failure leave, and did you agree to
look for it before you had the result?" If the failure leaves no trace you
pre-committed to inspect, you measured agreement and called it truth.

**Mapping:** Record-level holdout = reliability claim (does the signal
separate new generations?). Task-level holdout = validity claim (does it
separate generations of tasks it never saw?). BH correction and permutation
tests are pre-committed checks.

**Quote worth adapting:** "aggregate statistics are very good at making that
decision feel like it was never made at all" — cleaner description of what
max_entropy does than the current methodology writeup.

**Action:** Update METHODOLOGY.md to use the reliability/validity framing
explicitly. The current "two holdouts, two questions" section is close but
doesn't name the distinction as sharply.

---

## 3. Scale creates illusion of universality — small-signal architectures

**Link:** Hangwei Qian et al., "What Makes Good Contrastive Learning on
Small-Scale Wearable-based Tasks?" (arXiv:2202.05998)

**Idea:** Contrastive learning architectures optimized for high-entropy,
high-volume data fail on small-scale wearable sensor data — not because of
compute, but because the signal structure is different. Specialized signals
require specialized architectures. The paper's modular decomposition
isolates whether failure is in the objective or the signal processing.

**Mapping:** Directly supports the per-model-per-task-set finding. Can't
port a large-model entropy signal to a small model and expect it to work,
same way you can't port a large-scale contrastive model to wearable sensors.
The signal physics are different. The modular decomposition approach maps
to our scan-then-select methodology — decomposing the signal space rather
than assuming one metric works everywhere.

**Action:** Cite this paper in the 8B experiment writeup if the signal shape
differs from the 4B run.

---

## 4. Trajectory prefix redundancy — downsampling concern

**Link:** "The hidden compute waste in agentic workflows" discussion

**Idea:** RL pipelines treat every trajectory as a fresh start, ignoring
massive redundancy in the prefixes that lead to them.

**Doubt:** If we're running 108 generations across 60 tasks, there's likely
redundancy in the early-token entropy trajectories across generations of
the same task — the model processes the same prompt prefix before diverging.
The 32-point downsampled series might be destroying exactly the prefix
structure where the plateau-start signal fires. If the signal is about WHEN
the model commits (plateau_start_quartile), the prefix is where that
transition happens. Coarse downsampling could blur the plateau boundary.

**Action:** Verify that 32-point downsampling preserves temporal resolution
at the point in the trajectory where the plateau signal fires. If the
plateau typically starts in the first 20% of generation, check that the
downsampled series has enough points in that region to localize the start
accurately. If not, consider adaptive downsampling that preserves finer
resolution in the early trajectory.

---

## 5. Random vs. adversarial holdout — resolved

**Idea:** Random splits test "does the signal transfer to average unseen
tasks." Adversarial splits (maximally dissimilar held-out tasks) test
worst-case distribution shift. In quant finance, random splits flatter
memorization; time-embargo and regime-injection are needed.

**Resolution:** Random split is the right test for this product's claim.
The product is a tool users run on THEIR tasks. The claim is "does the
signal transfer to unseen tasks from a similar distribution" — what the
user actually deploys on. An adversarial split tests "does the signal
survive structurally unlike tasks" — a question the user doesn't have.
If their tasks change, they re-run calibration.

The random split IS falsifying — Granite proved it (0.873 train, 0.469
test, below chance). If random splits can produce below-chance results,
they have teeth.

The 18-task vs 60-task finding already tested the coarse adversarial case
(same model, different task bank, different signal). The 8B experiment
tests it on two axes (model size + task distribution).

**When adversarial split would be useful:** as a research tool to map the
boundary — "the signal works on task types A, B, C but breaks on D."
Understanding why the signal works, not proving it does. Build it when
there's a specific question it can answer.

---

## 6. Small-model signals are readable and functional

**Link:** 80-model uncertainty study (arXiv:2505.23854) — scale,
post-training, reasoning ability, and quantization all influence estimation
performance.

**Observation:** Small-model signals are not noise to discard. They're
often very readable and functional at small sizes (Qwen 4B trajectory-shape
signal has d=-0.94 — not a weak hint). There is evidence that uncertainty
patterns converge as models get larger, but small models have their own
signals that are usable NOW, not just embryonic versions of something that
matters at scale.

**Note on multi-model runs:** Each model run is independent. The question
is always: does THIS model have a usable signal, what is it, how strong,
is it useful for a gate. Not testing whether rules hold across models. The
8B run answers the same question as the Qwen and Granite runs — for THAT
model. If the signal shape differs, that's data about that model, not
evidence for or against a cross-model pattern.

**Action:** Run 8B the same way as 4B — scan, select, validate, report.
Reserved-task control (same tasks across models) is worth doing for clean
per-model attribution, not for cross-model comparison.
