# Core Model Configs — Verified Sampling Configurations

Verified sampling configurations for common GGUF models used with the
Calibration Kit. Each entry is double-checked against the HuggingFace
model card or official docs.

Each entry is double-checked against the HuggingFace model card or official docs.
Fine-tunes inherit their base model's guidance unless the fine-tune card overrides.

**Legend:**
- **Status**: `verified` = confirmed from official HF card/docs; `inherited` = base model config; `unknown` = no official guidance found
- **Mode**: `thinking` = generates reasoning tokens before output; `instruct` = standard chat; `base` = completion model (no chat template)

---

## Quick Reference Table

| GGUF File | Base Model | Status | Thinking? | Official Temp | Official top_p | Official top_k | Presence Penalty | Notes |
|---|---|---|---|---|---|---|---|---|
| `Qwen3.5-text-4B-Q5_K_M.gguf` | Qwen3.5-4B | verified | dual mode | 0.6–1.0 (mode-dep) | 0.8–0.95 | 20 | 0.0–1.5 (mode-dep) | 4 mode-specific configs below |
| `Qwen3.5-2B.Q5_K_M.gguf` | Qwen3.5-2B | verified | dual mode | 0.6–1.0 (mode-dep) | 0.8–1.0 | 20 | 0.0–2.0 (mode-dep) | Same 4-mode scheme; pp=2.0 for non-thinking text |
| `Qwen3.5-9B-UD-Q4_K_XL.gguf` | Qwen3.5-9B (unsloth dynamic) | verified | dual mode | 0.6–1.0 (mode-dep) | 0.8–1.0 | 20 | 0.0–2.0 (mode-dep) | Same as Qwen3.5-2B/4B; hybrid arch, multimodal |
| `qwen3.5-4B-super-coder.Q4_0.gguf` | Qwen3.5-4B (jica98 fine-tune) | verified | thinking | 0.6 | 0.95 | 20 | 0.0 | Uses precise-coding config from Qwen3.5 |
| `Qwen_Qwen3-4B-Instruct-2507-Q5_K_L.gguf` | Qwen3-4B-Instruct-2507 | verified | no (instruct only) | 0.7 | 0.8 | 20 | 0 (optional 0–2) | Do NOT use Qwen3.5 configs |
| `qwen3-4b-thinking-2507.Q8_0.gguf` | Qwen3-4B-Thinking-2507 | verified | yes (thinking only) | 0.6 | 0.95 | 20 | 0 (optional 0–2) | Do NOT use Qwen3.5 configs |
| `Qwen3-0.6B-BF16.gguf` | Qwen3-0.6B | verified | dual mode | 0.6 / 0.7 | 0.95 / 0.8 | 20 | 1.5 (quantized) | thinking=0.6/0.95; non-thinking=0.7/0.8 |
| `Qwen3.8-2B-BF16.gguf` | Qwen3.8-2B (empero-ai) | verified | yes (thinking) | 0.6 | 0.95 | 20 | — | Uses Qwen3.5 recommended settings |
| `Qwen3.8-4B-Q8_0.gguf` | Qwen3.8-4B (empero-ai) | verified | yes (thinking) | 0.6 | 0.95 | 20 | — | Uses Qwen3.5 recommended settings |
| `granite-4.0-h-tiny-Q4_K_M.gguf` | Granite-4.0-H-Tiny | verified | no | 0 | — | — | — | IBM: "temp=0 for most inferencing" |
| `granite-4.0-h-tiny-imatrix-Q4_K_M.gguf` | Granite-4.0-H-Tiny | verified | no | 0 | — | — | — | Same as above (imatrix quant) |
| `granite-4.0-h-tiny-APEX-i-quality-torch.gguf` | Granite-4.0-H-Tiny | verified | no | 0 | — | — | — | Same as above (APEX quant) |
| `ibm-granite_granite-4.0-h-micro-Q5_K_L.gguf` | Granite-4.0-H-Micro | verified | no | 0 | — | — | — | IBM: "temp=0 for most inferencing" |
| `granite-4.1-3b-Q5_K_M.gguf` | Granite-4.1-3B | verified | no | 0 (default) | — | — | — | Card example uses default generate(); Granite family temp=0 |
| `granite-3b-thinkingcapQ4_K_M.gguf` | Granite-4.1-3B (user fine-tune) | inherited | no | 0 | 1.0 | 0 | — | User's fine-tune; inherits Granite family temp=0; KV cache fix needed |
| `microsoft_Phi-4-mini-instruct-Q5_K_L.gguf` | Phi-4-mini-instruct | verified | no | 0 (greedy) | — | — | — | do_sample=False; Microsoft designed for deterministic |
| `omega-coder-phi-3-mini-1K.Q6_K.gguf` | Phi-3-mini (community fine-tune) | inherited | no | 0 (greedy) | — | — | — | Inherits Phi-3-mini greedy; no card-specific override found |
| `LFM2.5-2.6B-Q5_K_M.gguf` | LFM2.5-2.6B (Liquid AI) | verified | no | 0.1 | — | 50 | — | repetition_penalty=1.1 |
| `MiniCPM5-1B-F16.gguf` | MiniCPM5-1B (OpenBMB) | verified | dual mode | 0.7 / 0.9 | 0.95 | — | — | no-think=0.7; think=0.9 |
| `NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf` | Nemotron-3-Nano-4B | verified | dual mode | 0.6 / 1.0 | 0.95 | — | — | reasoning=1.0; tool-calling=0.6; reasoning toggle via system prompt |
| `nvidia_Nemotron-3-Nano-4B-Q4_K_L.gguf` | Nemotron-3-Nano-4B | verified | dual mode | 0.6 / 1.0 | 0.95 | — | — | Same as above (different quant) |
| `DeltaCoder-9B-v1.1-DPO-Q4_K_M.gguf` | Qwen3.5-DeltaCoder-9B | verified | no | 0.6 (coding) / 1.0 (chat) | 0.95 | 20 | 0.0 (coding) / 1.5 (chat) | Do NOT use temp < 0.5 |
| `VibeThinker-3B.Q8_0.gguf` | VibeThinker-3B | verified | yes | 1.0 | 0.95 | -1 (disabled) | — | |
| `TwIL-LM3-Q5_K_M.gguf` | TwIL-LM3 (webAI) | verified | yes | 0 (eval) / 0.6 (default) | 0.95 | — | — | Eval uses greedy; generation_config inherits SmolLM3 defaults |
| `TwIL-LM3-Q8_0.gguf` | TwIL-LM3 (webAI) | verified | yes | 0 (eval) / 0.6 (default) | 0.95 | — | — | Same as above (different quant) |
| `mythos-nano-Q8_0.gguf` | Mythos-nano (squ11z1) | verified | yes | 0.6–1.0 | — | — | — | Range; reasoning model with long CoT |
| `LocoOperator-4B.i1-Q4_K_M.gguf` | Qwen3-4B-Instruct-2507 (LocoreMind) | verified | no | 0.7 | — | — | — | Uses qwen3_nothinking template; inherits Qwen3 instruct base |
| `mini-coder-4b-q8_0.gguf` | Qwen3-4B-Instruct-2507 (ricdomolm) | inherited | no | 0.7 | 0.8 | 20 | 0 (optional 0–2) | No card-specific override; inherits Qwen3-4B-Instruct |
| `Mini-AGI-4B.Q8_0.gguf` | unknown (Guilherme34) | empirical | unknown | **0.0 (greedy)** | 1.0 | 0 | — | Sweet spot from past sweeps; see below |
| `Llama-3.2-3B-Agent007-Coder.Q6_K.gguf` | Llama-3.2-3B-Instruct (EpistemeAI) | inherited | no | — | — | — | — | Llama 3.2 has no official sampling recommendation |
| `Dolphin3.0-Llama3.1-8B-abliterated.Q4_K_S.gguf` | Llama-3.1-8B (huihui-ai abliteration) | inherited | no | — | — | — | — | No official sampling params; Llama 3.1 defaults |
| `Dolphin3.0-Llama3.1-8B-abliterated.Q5_K_M.gguf` | Llama-3.1-8B (huihui-ai abliteration) | inherited | no | — | — | — | — | Same as above (different quant) |
| `Dolphin-X1-8B-Q4_K_M.gguf` | Llama-3.1-8B-Instruct (dphn) | inherited | no | — | — | — | — | No official sampling params; Llama 3.1 defaults |
| `dolphin-x1-nano-Q6_K.gguf` | Trinity Nano (dphn) | verified | no | 0.15 | — | — | — | vLLM example uses temp=0.15; may be example-specific |
| `dolphin-2.9.4-gemma2-2b-q4_k_m.gguf` | Gemma2-2B (cognitivecomputations) | inherited | no | — | — | — | — | No official sampling params; Gemma2 defaults |
| `starcoder2-3b.Q8_0.gguf` | StarCoder2-3B (bigcode) | verified | no (base) | 0.2 | 0.95 | — | — | Base completion model (FIM); not a chat model |
| `mmproj-F16.gguf` | — | — | — | — | — | — | — | Multimodal projector file, not a standalone model |

---

## Detailed Configs

### Qwen3.5 Family (4B, 2B, 9B) — VERIFIED

**Source:** HuggingFace model cards for Qwen/Qwen3.5-4B, Qwen/Qwen3.5-2B, Qwen/Qwen3.5-9B

Four mode-specific configurations. All share top_k=20, min_p=0.0, repetition_penalty=1.0.

| Mode | temp | top_p | presence_penalty | Use case |
|---|---|---|---|---|
| Thinking, general | 1.0 | 0.95 | 1.5 | Reasoning, math, multi-step |
| Thinking, precise coding | 0.6 | 0.95 | 0.0 | WebDev, code generation |
| Instruct, general | 0.7 | 0.8 | 1.5 | Fast assistant, latency-bound |
| Instruct, reasoning | 1.0 | 0.95 | 1.5 | Non-thinking reasoning tasks |

**Qwen3.5-2B specific notes:**
- Non-thinking text mode uses top_p=1.00, presence_penalty=2.0 (differs from 4B/9B)
- Card warns: Qwen3.5-2B is more prone to thinking loops than larger siblings
- May need sampling tuning + streaming to avoid non-terminating generation

**Qwen3.5-9B specific notes:**
- Hybrid architecture: 3:1 Gated DeltaNet (linear attn) to full attn
- KV cache only on 1/4 of layers
- Multimodal (vision encoder loaded even for text-only)
- Card recommends 32K output tokens general, 81K for complex problems
- No /think /no_think soft switch (unlike Qwen3)
- llama-cpp-python 0.3.35+ required (hybrid architecture fix)

**GGUFs covered:**
- `Qwen3.5-text-4B-Q5_K_M.gguf`
- `Qwen3.5-2B.Q5_K_M.gguf`
- `Qwen3.5-9B-UD-Q4_K_XL.gguf` (unsloth dynamic quant — same configs)

---

### Qwen3.5-4B-super-coder — VERIFIED

**Source:** HuggingFace card for jica98/qwen3.5-4B-super-coder

Fine-tune of Qwen3.5-4B. Uses the precise-coding config from the Qwen3.5 family.

| Parameter | Value |
|---|---|
| temperature | 0.6 |
| top_p | 0.95 |
| top_k | 20 |
| min_p | 0.0 |
| presence_penalty | (not specified — use 0.0 per Qwen3.5 precise-coding) |

**GGUFs covered:**
- `qwen3.5-4B-super-coder.Q4_0.gguf`
- `qwen3.5-4B-super-coder.Q4_0 (1).gguf` (duplicate)

---

### Qwen3-4B-Instruct-2507 — VERIFIED

**Source:** HuggingFace card for Qwen/Qwen3-4B-Instruct-2507

Non-thinking only. Do NOT use Qwen3.5 configs — different family.

| Parameter | Value |
|---|---|
| temperature | 0.7 |
| top_p | 0.8 |
| top_k | 20 |
| min_p | 0.0 |
| presence_penalty | 0 (optional 0–2; card warns higher values may cause language mixing) |

**GGUFs covered:**
- `Qwen_Qwen3-4B-Instruct-2507-Q5_K_L.gguf`

---

### Qwen3-4B-Thinking-2507 — VERIFIED

**Source:** HuggingFace card for Qwen/Qwen3-4B-Thinking-2507

Thinking only. Do NOT use Qwen3.5 configs — Qwen3 thinking uses temp=0.6, NOT 1.0.

| Parameter | Value |
|---|---|
| temperature | 0.6 |
| top_p | 0.95 |
| top_k | 20 |
| min_p | 0.0 |
| presence_penalty | 0 (optional 0–2; same warning as Instruct) |

**Notes:**
- Recommended output length: 32,768 tokens general; up to 81,920 for complex math/programming
- Thinking content should NOT be included in multi-turn history
- Requires current Transformers support (older versions < 4.51 can fail with KeyError: 'qwen3')

**GGUFs covered:**
- `qwen3-4b-thinking-2507.Q8_0.gguf`

---

### Qwen3-0.6B — VERIFIED

**Source:** HuggingFace card for Qwen/Qwen3-0.6B

Dual-mode (thinking/non-thinking). Same scheme as Qwen3-4B.

| Mode | temp | top_p | top_k | min_p | presence_penalty |
|---|---|---|---|---|---|
| Thinking | 0.6 | 0.95 | 20 | 0 | 1.5 (for quantized) |
| Non-thinking | 0.7 | 0.8 | 20 | 0 | 1.5 (for quantized) |

**Notes:**
- DO NOT use greedy decoding — causes performance degradation and endless repetitions
- presence_penalty=1.5 recommended for quantized models to suppress repetitive outputs

**GGUFs covered:**
- `Qwen3-0.6B-BF16.gguf`

---

### Qwen3.8-2B / Qwen3.8-4B (empero-ai) — VERIFIED

**Source:** HuggingFace cards for empero-ai/Qwen3.8-2B, empero-ai/Qwen3.8-4B

Reasoning models with thinking blocks. Uses Qwen3.5 recommended settings.

| Parameter | Value |
|---|---|
| temperature | 0.6 |
| top_p | 0.95 |
| top_k | 20 |

**Notes:**
- Greedy decoding on long generations is a known repetition-loop failure mode
- Allow generous max_new_tokens (16,384 recommended)
- Every answer opens with a thinking block; parse and strip for end users
- Qwen3.8-4B: trace mix emphasizes math, reasoning, instruction following; for strongest code performance use Qwen3.8-9B

**GGUFs covered:**
- `Qwen3.8-2B-BF16.gguf`
- `Qwen3.8-4B-Q8_0.gguf`

---

### Granite 4.0 H-Tiny / H-Micro — VERIFIED

**Source:** IBM Granite docs (ibmgranite.mintlify.app), HuggingFace cards

IBM Granite docs state: "The Granite 4 models work best with temperature set to 0 for most inferencing tasks."

| Parameter | Value |
|---|---|
| temperature | 0 |

**Notes:**
- H-Tiny: 7B total / 1B activated (MoE), hybrid Mamba-2/transformer
- H-Micro: 3B dense, hybrid Mamba-2/transformer
- Card generation examples use `model.generate(**input_tokens, max_new_tokens=N)` with no temp override (defaults to greedy)
- Default system prompt added 2025-10-07 for professional/accurate/safe responses
- Empirical note: finalist sweep showed Granite-tiny at temp=0.1 scored 84.8% vs temp=0.0 at 80.4% — a slight nudge off deterministic helped, but official guidance is temp=0

**GGUFs covered:**
- `granite-4.0-h-tiny-Q4_K_M.gguf`
- `granite-4.0-h-tiny-imatrix-Q4_K_M.gguf`
- `granite-4.0-h-tiny-APEX-i-quality-torch.gguf`
- `ibm-granite_granite-4.0-h-micro-Q5_K_L.gguf`

---

### Granite 4.1-3B — VERIFIED

**Source:** HuggingFace card for ibm-granite/granite-4.1-3B

Dense 3B model. Card generation example uses `model.generate(**input_tokens, max_new_tokens=100)` with no temperature specified (defaults to greedy). Consistent with Granite 4 family guidance.

| Parameter | Value |
|---|---|
| temperature | 0 (default/greedy) |

**Notes:**
- Dense architecture (not MoE, not hybrid — unlike Granite 4.0)
- 131K context length
- Enhanced tool calling, instruction following, coding capabilities
- No explicit sampling section in card; follows Granite family convention

**GGUFs covered:**
- `granite-4.1-3b-Q5_K_M.gguf`

---

### granite-3b-thinkingcap — INHERITED (user fine-tune)

**Source:** Fine-tune of Granite-4.1-3B (`granite-4.1-3b-Q5_K_M.gguf`).

Inherits Granite 4.1-3B's config (temp=0, greedy). The fair benchmark used temp=0.0, top_p=1.0, top_k=0.

| Parameter | Value |
|---|---|
| temperature | 0 (greedy) |
| top_p | 1.0 |
| top_k | 0 (disabled) |

**Empirical findings from past benchmarks:**
- **KV cache incompatibility:** head_dim=80 is not divisible by 32, so forcing type_k=8/type_v=8 fails with "KV cache type q8_0 (block size 32) does not divide n_embd_head_k=80". **Fix: use default f16 KV cache, do not force type_k=8/type_v=8.**
- **Failed to load** in the model sweep and fair benchmark due to the KV cache issue above.
- **v2 architect assessment** (101 records in `_contaminated/results_granite-3b-thinkingcap.jsonl`): used as architect/planner. Scored 130 total points across architect tests. Strong on plan restraint and verdicts, weak on format compliance (no search/replace blocks, no code blocks, no answer directives).
- **Integration/planner finding:** 2/3 integration tasks solved. Tied for first on "assemble from scraps" (module integration). Only 26% on raw code generation, but high entropy = deliberation.
- **Best role: planner/architect/integrator**, not raw coder.

**GGUFs covered:**
- `granite-3b-thinkingcapQ4_K_M.gguf`

---

### Phi-4-mini-instruct — VERIFIED

**Source:** HuggingFace card for microsoft/Phi-4-mini-instruct

| Parameter | Value |
|---|---|
| temperature | 0.0 (greedy) |
| do_sample | False |

**Notes:**
- Both vLLM and Transformers official examples use greedy decoding
- No top_p, top_k, or presence_penalty specified
- Microsoft designed it for deterministic decoding
- Chat format recommended; context length 128K
- Transformers guidance references version 4.49.0+

**GGUFs covered:**
- `microsoft_Phi-4-mini-instruct-Q5_K_L.gguf`

---

### omega-coder-phi-3-mini — INHERITED

**Source:** No card-specific sampling params found. Inherits from Phi-3-mini.

Phi-3-mini official examples use:
| Parameter | Value |
|---|---|
| temperature | 0.0 (greedy) |
| do_sample | False |

**Notes:**
- This is a community fine-tune of Phi-3-mini for coding
- No official sampling guidance on the fine-tune card
- Inherits Phi-3-mini's greedy decoding default

**GGUFs covered:**
- `omega-coder-phi-3-mini-1K.Q6_K.gguf`

---

### LFM2.5-2.6B — VERIFIED

**Source:** HuggingFace card for LiquidAI/LFM2.5-2.6B

| Parameter | Value |
|---|---|
| temperature | 0.1 |
| top_k | 50 |
| repetition_penalty | 1.1 |

**Notes:**
- 2.69B parameters, 128K context
- Hybrid architecture: 22 double-gated short convolution blocks + 8 GQA
- Trained for agentic workloads with native tool calling
- Blog notes: Qwen models in their evals use temp=0.6 (greedy degrades due to doom looping); LFM uses 0.1
- **THINKING MODEL**: "LFM2.5-2.6B is a pure reasoning model that always thinks
  before it answers" (HF model card). Chat template always prepends `imd` to
  the assistant generation prompt. P(think)=100% (deterministic, unlike Qwen3.5's
  ~60%). Must: (1) prepend `imd` in prompt, (2) strip thinking blocks after
  generation, (3) use max_tokens >= 4096 (thinking consumes the budget).

**GGUFs covered:**
- `LFM2.5-2.6B-Q5_K_M.gguf`

---

### MiniCPM5-1B — VERIFIED

**Source:** HuggingFace card for openbmb/MiniCPM5-1B

Dual-mode model with thinking toggle.

| Mode | temp | top_p | enable_thinking |
|---|---|---|---|
| Think | 0.9 | 0.95 | True |
| No Think | 0.7 | 0.95 | False |

**Notes:**
- Standard LlamaForCausalLM — no custom modeling code needed
- generation_config.json tuned for think mode by default
- Think mode: hard reasoning, math, code, multi-step
- No-think mode: fast assistant, latency-bound

**GGUFs covered:**
- `MiniCPM5-1B-F16.gguf`

---

### NVIDIA Nemotron-3-Nano-4B — VERIFIED

**Source:** HuggingFace cards for nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16, FP8, GGUF

Dual-mode: reasoning on/off controlled via system prompt or `enable_thinking` in chat template.

| Mode | temp | top_p | Use case |
|---|---|---|---|
| Reasoning on | 1.0 | 0.95 | Complex tasks requiring reasoning traces |
| Reasoning off / tool calling | 0.6 | 0.95 | Tool calling, fast responses |

**Notes:**
- Hybrid architecture: Mamba-2 + MLP layers + 4 attention layers
- Compressed from NVIDIA-Nemotron-Nano-9B-v2
- Edge-ready: Jetson Thor, GeForce RTX, DGX Spark
- Reasoning off slightly decreases accuracy on harder prompts

**GGUFs covered:**
- `NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf`
- `nvidia_Nemotron-3-Nano-4B-Q4_K_L.gguf`

---

### DeltaCoder-9B — VERIFIED

**Source:** HuggingFace card for danielcherubini/Qwen3.5-DeltaCoder-9B

Fine-tune of Qwen3.5-9B. Two profiles:

| Profile | temp | top_k | top_p | min_p | presence_penalty | repeat_penalty |
|---|---|---|---|---|---|---|
| Coding | 0.6 | 20 | 0.95 | 0.0 | 0.0 | 1.0 |
| Chat | 1.0 | 20 | 0.95 | 0.0 | 1.5 | 1.0 |

**WARNING:** Do NOT use temperature below 0.5 — low temperatures cause deterministic looping in multi-turn agentic use.

**GGUFs covered:**
- `DeltaCoder-9B-v1.1-DPO-Q4_K_M.gguf`

---

### VibeThinker-3B — VERIFIED

**Source:** HuggingFace card for VibeThinker-3B

| Parameter | Value |
|---|---|
| temperature | 1.0 |
| top_p | 0.95 |
| top_k | -1 (disabled) |

**GGUFs covered:**
- `VibeThinker-3B.Q8_0.gguf`

---

### TwIL-LM3 — VERIFIED

**Source:** HuggingFace card for webAI-Official/TwIL-LM3

Reasoning model (opens `<think>` block before answering).

| Context | temp | top_p | do_sample |
|---|---|---|---|
| Evaluation (reported numbers) | 0 (greedy) | — | False |
| General use (generation_config default) | 0.6 | 0.95 | True |

**Notes:**
- generation_config.json inherits SmolLM3's defaults (temp=0.6, top_p=0.95)
- Must pass do_sample=False explicitly to reproduce evaluation results
- Short generation budget truncates reasoning and scores far worse
- Eval protocol: max_new_tokens=2048 (retry at 4096 for truncated rows)

**GGUFs covered:**
- `TwIL-LM3-Q5_K_M.gguf`
- `TwIL-LM3-Q8_0.gguf`

---

### Mythos-nano — VERIFIED

**Source:** HuggingFace card for squ11z1/Mythos-nano

| Parameter | Value |
|---|---|
| temperature | 0.6–1.0 (range) |

**Notes:**
- Reasoning model — expect long chain-of-thought before final answer
- Up to 40,960 output tokens for hard problems
- No top_p, top_k, or presence_penalty specified

**GGUFs covered:**
- `mythos-nano-Q8_0.gguf`

---

### LocoOperator-4B — VERIFIED

**Source:** HuggingFace card for LocoreMind/LocoOperator-4B

Fine-tune of Qwen3-4B-Instruct-2507 via distillation from Qwen3-Coder-Next.

| Parameter | Value | Rationale |
|---|---|---|
| temperature | 0.7 | Balanced between determinism and exploration |
| context size | 50K | Covers multi-turn exploration |
| max turns | 10 | Focused codebase exploration |

**Notes:**
- Uses qwen3_nothinking template (non-thinking mode)
- Specializes in multi-turn codebase exploration (Read, Grep, Glob, Bash, Write, Edit, Task)
- 100% JSON validity in tool calls
- Card recommends temp=0.7; inherits Qwen3-4B-Instruct base (top_p=0.8, top_k=20)

**GGUFs covered:**
- `LocoOperator-4B.i1-Q4_K_M.gguf`

---

### mini-coder-4b — INHERITED

**Source:** HuggingFace card for ricdomolm/mini-coder-4b

Fine-tune of Qwen3-4B-Instruct-2507, distilled from Qwen 3 Coder 30B A3B. No card-specific sampling params. Inherits Qwen3-4B-Instruct-2507 settings.

| Parameter | Value |
|---|---|
| temperature | 0.7 |
| top_p | 0.8 |
| top_k | 20 |
| presence_penalty | 0 (optional 0–2) |

**GGUFs covered:**
- `mini-coder-4b-q8_0.gguf`

---

### Mini-AGI-4B — EMPIRICAL (sweet spot from past sweeps)

**Source:** No official HuggingFace model card with sampling params (Guilherme34/Mini-AGI-4B has no card). Config determined empirically from past benchmark sweeps.

| Parameter | Value | Source |
|---|---|---|
| temperature | **0.0 (greedy)** | Empirical sweet spot |
| top_p | 1.0 | Used in earlier assessment |
| top_k | 0 (disabled) | Used in earlier assessment |

**Empirical sweep data:**

| Config | Score | Tasks passed | Source |
|---|---|---|---|
| temp=0.0 (greedy) | **72%** | 8/12 | `_miniagi_assess.py` earlier run |
| temp=0.6, top_p=0.95, top_k=20 (Qwen3 preset) | 59% | 4/12 | `_fair_benchmark.py` |

The fair benchmark log explicitly states: "mini-agi-4b: Ran with Qwen3 preset (temp=0.6) got 59%. Earlier run at temp=0.0 got 78%. Use the earlier data instead."

**Sweet spot: temp=0.0 (greedy).** This is 13 percentage points better than the Qwen3-family preset. The model appears to be a Qwen3-4B base fine-tune (4B params, Q8_0 quant at 3.99 GB), but it performs best with deterministic decoding — unlike Qwen3 instruct models which warn against greedy.

**Note:** The `_miniagi_assess.py` script was specifically written to test Mini-AGI at temp=0.0 against the same tasks Granite failed (stack_class, text_stats, math_eval). The earlier run results file (`_miniagi_results.jsonl`) is not present in the kit directory, but the log confirms the 72%/8-of-12 figure.

**GGUFs covered:**
- `Mini-AGI-4B.Q8_0.gguf`

---

### Llama-3.2-3B-Agent007-Coder — INHERITED

**Source:** HuggingFace card for EpistemeAI/Llama-3.2-3B-Agent007-Coder

Fine-tune of Llama-3.2-3B-Instruct. No card-specific sampling params. Llama 3.2 has no official sampling recommendation — use standard instruct defaults (temp=0.6–0.8 typical).

**GGUFs covered:**
- `Llama-3.2-3B-Agent007-Coder.Q6_K.gguf`

---

### Dolphin 3.0 Llama 3.1 8B (abliterated) — INHERITED

**Source:** HuggingFace card for huihui-ai/Dolphin3.0-Llama3.1-8B-abliterated

Abliterated version of cognitivecomputations/Dolphin3.0-Llama3.1-8B. No official sampling params on either card. Llama 3.1 has no official sampling recommendation.

**GGUFs covered:**
- `Dolphin3.0-Llama3.1-8B-abliterated.Q4_K_S.gguf`
- `Dolphin3.0-Llama3.1-8B-abliterated.Q5_K_M.gguf`

---

### Dolphin-X1-8B — INHERITED

**Source:** HuggingFace card for dphn/Dolphin-X1-8B

Fine-tune of Llama-3.1-8B-Instruct. No card-specific sampling params. Llama 3.1 defaults.

**GGUFs covered:**
- `Dolphin-X1-8B-Q4_K_M.gguf`

---

### Dolphin-X1-Trinity-Nano (dolphin-x1-nano) — VERIFIED

**Source:** HuggingFace card for dphn/Dolphin-X1-Trinity-Nano

| Parameter | Value |
|---|---|
| temperature | 0.15 |

**Notes:**
- The vLLM example uses temp=0.15; this may be example-specific rather than a firm recommendation
- Fine-tune of Arcee AI's Trinity Nano model
- 6B params

**GGUFs covered:**
- `dolphin-x1-nano-Q6_K.gguf`

---

### Dolphin 2.9.4 Gemma2 2B — INHERITED

**Source:** HuggingFace card for cognitivecomputations/dolphin-2.9.4-gemma2-2b

Fine-tune of Google Gemma2-2B. No card-specific sampling params. Gemma2 has its own defaults.

**GGUFs covered:**
- `dolphin-2.9.4-gemma2-2b-q4_k_m.gguf`

---

### StarCoder2-3B — VERIFIED

**Source:** HuggingFace card for bigcode/starcoder2-3b

Base code completion model (not instruct/chat). FIM (Fill-in-the-Middle) trained.

| Parameter | Value |
|---|---|
| temperature | 0.2 |
| top_p | 0.95 |

**Notes:**
- The 15B variant's card explicitly lists temp=0.2, top_p=0.95
- The 3B card doesn't specify but the family shares this guidance
- This is a base/completion model, not a chat model — no chat template
- Context window: 16,384 tokens with sliding window attention of 4,096

**GGUFs covered:**
- `starcoder2-3b.Q8_0.gguf`

---

### mmproj-F16.gguf — NOT A MODEL

This is a multimodal projector file (mmproj), not a standalone language model. It is loaded alongside a multimodal GGUF to enable vision input. Do not load it as a standalone model.

---

## Cross-Family Warnings

1. **Qwen3 ≠ Qwen3.5**: Qwen3 thinking uses temp=0.6; Qwen3.5 thinking uses temp=1.0. Carrying configs between families produces wrong results.

2. **Qwen3.5 presence_penalty is required (1.5)**; Qwen3 presence_penalty is optional and may hurt. Different guidance.

3. **Phi-4-mini is greedy (temp=0.0)**. Do not use temp=0.7 — that was an invented config in `_fair_benchmark.py`.

4. **Granite 4 family uses temp=0**. The empirical "slight nudge to 0.1" helped in one sweep but is not official guidance.

5. **DeltaCoder warns: never use temp < 0.5** — causes deterministic looping in agentic use. This conflicts with Granite/Phi greedy guidance; do not carry configs.

6. **Thinking models need large max_tokens**: 1200 tokens will be consumed by reasoning and produce NO code output (silent failure). Use 4096+ for coding, 8192+ for complex, 32K+ per card recommendations.

7. **Thinking content must be stripped** from response before extracting code, and must NOT be included in multi-turn history.

8. **LFM2.5 uses repetition_penalty=1.1**, not presence_penalty. Different parameter name, different mechanism.

9. **Nemotron reasoning toggle** is via system prompt or `enable_thinking` in chat template — not via sampling params. The temp difference (1.0 vs 0.6) tracks the mode.

10. **TwIL-LM3 has dual configs**: greedy (temp=0) for evaluation reproducibility, but generation_config defaults to temp=0.6/top_p=0.95 (SmolLM3 inherited). Must explicitly set do_sample=False for greedy.
