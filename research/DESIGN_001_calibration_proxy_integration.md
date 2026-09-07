# DESIGN 001 — Calibration Proxy: From Profile Generator to Runtime Layer

**Status:** implemented. The proxy, setup wizard, rolling-window reanalysis, intervention plan, and harness integrations are live in `calibration_proxy/` and `calibrate.py`.
**Date:** 2026-09-06
**Scope:** technical only — architecture, phases, verification. Business/packaging is a separate doc.
**Companion:** the working session plan lives at `~/.devin/plans/plan-0ef2b4d77580cbb8.md`; this document is the durable, self-contained version for handoff to a new conversation or another engineer.

---

## 1. Objective

Adapt `calibration-kit` — currently an offline tool that profiles a GGUF model's failure signals — into a **runtime calibration layer** that scores live generations and optionally gates them, for **any harness** that can point at an OpenAI-compatible endpoint.

The deliverable is not a fork of any existing agent harness. It is an **OpenAI-compatible proxy** that sits between the harness and `llama-server`:

```
[any harness/gateway] → [calibration proxy] → [llama-server] → GGUF model
```

Everything downstream — OpenClaw, LocalHarness, mini-swe-agent, OpenCode, Aider, a shell script — gets calibrated generations by changing one URL. Nothing upstream changes. Nothing is forked.

Product framing (user-corrected): *a first approximation of the confidence infrastructure frontier labs almost certainly run internally — not equivalent to it, but the same idea, and the first public implementation of it for local models.*

---

## 2. Verified evidence (what is real vs. assumed)

### Verified live on this machine (2026-09-06)

Against `llama-server` **v2.28.2** (LM Studio bundled CPU build at
`~/.lmstudio/extensions/backends/llama.cpp-win-x86_64-avx2-2.28.2/llama-server.exe`),
model `Nemotron-3-Nano-4B-Coding-Agent-Q4_K_M.gguf`:

| Claim | Result |
|---|---|
| `POST /v1/chat/completions` accepts `logprobs=true, top_logprobs=20` | ✅ `choices[0].logprobs.content` populated per-token |
| Each token entry carries chosen `logprob` + `top_logprobs[]` | ✅ exactly **20** entries per token — not capped at 5 |
| Streaming (`stream:true, stream_options.include_usage`) delivers logprobs | ✅ 32 logprob entries for 32 tokens, all width 20, usage chunk at end |
| Cropped-top-20 entropy computed from API payload | ✅ sane values (mean 0.096, range 0–1.048 on a temp=0 coding generation) |

**Test artifact:** `$TEMP\chat_logprobs_test.json` — a real 64-token response with full logprobs. **Move this into the repo** (e.g. `research/fixtures/`) before it ages out of Temp; it is the reference fixture for the feature-math port.

### Verified from upstream sources (not run locally)

- **llama.cpp PR #10783** (merged): full `logprobs`/`top_logprobs` on `/v1/chat/completions`; **pre-sampling** probabilities — the same distribution our entropy math operates on. Native `/completion` returns `completion_probabilities` with per-token `top_logprobs`.
- **llama.cpp issue #27174**: `echo:true` prompt-token logprobs are silently absent on `/v1/completions`. **Irrelevant to us** — we only need generated-token logprobs.
- **litellm issue #17165**: litellm's native `ollama` path raises `UnsupportedParamsError` on `logprobs`. Workaround: route through the `openai/` provider prefix at any OpenAI-compatible `api_base`. Matters only for litellm-based harnesses (mini-swe-agent); irrelevant to the proxy path, which talks to llama-server directly.

### Not yet verified (blocking, in order)

- [ ] **P1 — numerical parity:** same model + same prompt through llama-cpp-python (in-process logits, existing pipeline) vs llama-server (API logprobs). Expect small float differences; confirm feature values don't shift enough to move a verdict across the profile's threshold.
- [ ] **P1 — client tolerance:** a real OpenAI SDK client (openai-python, or LocalHarness) must accept a response carrying an extra `calibration` field. SDKs ignore unknown fields by contract; verify empirically once.
- [ ] **P2 — cross-backend logprobs:** Ollama (`/v1` endpoint, v0.12.11+), LM Studio (`:1234/v1`), vLLM all claim logprobs support. llama.cpp is verified; the others are per-backend verification tasks before advertising compatibility.
- [ ] **P2 — OpenClaw license:** GitHub badge reads "License: Other", docs say MIT. The OpenClaw Foundation may have relicensed. **Not a dependency** — only matters for claiming compatibility.

---

## 3. Feature-parity audit — what survives the API boundary

Our pipeline (`_calibrate_pipeline.py`) captures **raw logits** in-process via a llama-cpp-python logits-processor callback (`__call__(self, tokens, logits)`). The API boundary gives us `top_logprobs` — the post-softmax top-20 — instead of the full logit vector.

### API-computable (exact or near-exact parity)

| Feature family | Source in pipeline | Via API? |
|---|---|---|
| `ent` series (semantic + structural), `_TOPK=20` cropped entropy | top-20 crop, renormalize, entropy | ✅ identical math — `top_logprobs=20` is the same crop, post-softmax; renormalization is equivalent |
| `top1`, `margin` (top1−top2) | cropped distribution | ✅ |
| `plateau_start_quartile`, `spike_quartile`, all entropy-series trajectory features | the `ent` series | ✅ |
| `surprisal` (`-log p(chosen)`) | prev-step logits vs. chosen id | ✅ chosen token's `logprob` field is exactly this |
| `rank` of chosen token | position in sorted logits | ✅ position within own `top_logprobs` (near-exact; if chosen falls outside top-20, flag as `rank > 20` — rare) |
| `kl_uniform` | `log(20) − ent` | ✅ |
| Adjacent-step KL divergence | union of adjacent top-20 supports, eps floor | ✅ approximate — identical eps-floor treatment for off-support entries |
| `think_frac`, `think_boundary` | think-marker token ids | ✅ text/token-id level, no distribution needed |
| `n_tokens`, token counts, `finish_reason` | generation metadata | ✅ `usage` + finish_reason |

### Lost via API (full-vocab required)

| Feature | Why it can't come back |
|---|---|
| `full_ent` | full-vocab softmax entropy; `top_logprobs` caps at 20, no tail mass |
| `mass1`, `mass5`, `mass20` | true probability mass of top-k requires the full denominator |

**Consequence — two-tier architecture:**

- **Discovery/calibration** stays in-process: `calibration-kit` runs llama-cpp-python with full logits, all ~170 candidate features, signal *selection*, holdout validation. **Unchanged.**
- **Deployment/consumption** runs over the wire: the proxy computes the API-computable subset and evaluates the **already-validated** profile. The proxy does not discover signals; it applies them.

Critically, **all three signals that have survived validation are API-computable**:

- Qwen 4B/60: `plateau_start_quartile` — entropy-series feature ✅
- Qwen 8B/224: `think_frac` — text-level ✅
- Granite: `max_entropy` — max of the entropy series ✅ (the null result, but still)

If a future model's surviving signal turns out to be a full-vocab feature, that profile is flagged "in-process deployment only" — the honest answer, not a silent degradation.

---

## 4. Proxy design

### 4.1 Request path

1. Client sends a standard OpenAI chat-completions request to the proxy.
2. Proxy forwards to `llama-server` with `logprobs=true, top_logprobs=20` injected. If the client already requested logprobs, respect the client's values; never downgrade a wider request.
3. Response returns. Non-streaming: read `choices[0].logprobs.content`. Streaming: accumulate per-chunk `logprobs` deltas over SSE (verified: deltas arrive per-token, width 20).
4. Compute the API-computable feature subset → evaluate the loaded profile → attach the verdict.
5. Response continues to the client with a top-level or per-choice `calibration` field added. Unknown JSON fields pass through OpenAI SDKs harmlessly.

### 4.2 Verdict payload

```json
"calibration": {
  "profile": "qwen3-8b-v1",
  "verdict": "likely_wrong | probably_fine | no_signal | out_of_scope",
  "signal": {"name": "think_frac", "value": 0.12, "direction": "high=good"},
  "predicted_failure_class": "syntax | assertion | logic | empty_output | name_error | ...",
  "recommended_intervention": "regenerate | temp_retry | test_retry | ...",
  "scope_note": "profile validated on a 224-task coding bank; applies within that task shape"
}
```

`no_signal` and `out_of_scope` are first-class verdicts — the honest "none" the kit is built on. A profile must declare its scope (model id, task shape, generation config) and the proxy must refuse or caveat out-of-scope traffic rather than guess.

### 4.3 Operating modes

- **Observe** (default, v1): annotate every generation. Passive receipts; harness behavior unchanged.
- **Gate** (v2, opt-in per profile): on `likely_wrong`, hold the response and regenerate internally with failure-type-informed parameters (temperature shift, prompt variation), bounded attempts, then pass through with `regenerated: N` in the verdict. The discard screen the Moltbook agents described. **Gate mode does not ship until observe-mode verdicts are validated on live traffic** — the same rule the kit lives by: no gate on a signal that hasn't survived holdout.

### 4.4 Consumption surfaces

The user "uses" it by pointing their app at the proxy URL. Visibility is their choice:

1. **Structured field** — for harnesses/scripts that read JSON: gate, route, log, escalate.
2. **Local dashboard** — the proxy serves a small web page streaming live verdicts (generation preview, signal value, verdict, predicted failure class, intervention taken). Works with *closed-source* apps — they never touch a thing. In gate mode it doubles as the audit trail: what was discarded, what recovered, realized recovery rate.
3. **Content injection** (opt-in, default off) — append a short note to the assistant message text ("calibration: risky — predicted syntax-class failure; recommended: regenerate"). Renders anywhere including chat channels. **Caveat:** the note enters conversation history — the model sees it next turn. For coding agents that may itself improve recovery, but it's a behavior change and must be tested before default-on.

And the zero-surface mode: gate mode needs no consumption at all — the app silently produces better output. That is the strongest form of "invisible infrastructure."

### 4.5 Persistence

Every request logs: timestamp, model, profile id, per-request feature vector (compact), verdict, intervention taken, and — where observable — the downstream outcome (did the session error, did the tool call fail). Append-only JSONL or SQLite. This is the raw material for **Phase 3 live profile updates** — the ProHarness gap ("keep the fingerprint up to date") — which requires drift detection, separate calibration/eval windows, minimum sample counts, and rollback-on-regression. Not v1.

### 4.6 Implementation sketch

- Python, FastAPI or aiohttp. ~300–500 lines for observe mode.
- Feature extractor: port the `ExtendedTrajectory` math from `_calibrate_pipeline.py` (~lines 249–400: entropy series, surprisal, rank, think-boundary) to operate on `top_logprobs` payloads. Parity, not approximation — the crop is the same.
- Profile loader: consumes the JSON profile format `calibration-kit` already emits (`qwen60_profile.json`, `qwen3-8b` profile).
- SSE passthrough with per-chunk logprobs accumulation is the only nontrivial part.
- No GPU in the proxy — it's a JSON math layer. Can run on the same box as llama-server or on a separate host (tools/verdicts are machine-agnostic; only the model server touches hardware).
- Config: upstream URL, profile path, mode (observe/gate), optional per-route overrides.

---

## 5. Harness evaluation — on merit, from actual source reads

Read the actual code of each candidate. Conclusion first: **no fork is needed — the proxy makes the harness interchangeable.** But one harness is the best *reference integration* for proving the loop end-to-end, and one is the best *distribution channel*.

### LocalHarness (`ahwurm/localharness`) — best architectural fit / recommended reference

- MIT, Python ≥3.12, 31 stars, ~1075 commits, active.
- **Natively manages llama.cpp**: spawns, watches, tears down `llama-server`; first-class runtime alongside vLLM/Ollama/LM Studio. Docs: `docs/runtimes/llamacpp.md`.
- **Direct `openai` SDK** (`AsyncOpenAI.chat.completions.create`) — no litellm translation layer. `logprobs`/`top_logprobs` are first-class params.
- **Already has gate infrastructure**: a "write gate that predicts" — per-tool statistical priors in pure SQL scoring every tool outcome. Our generation-level gate is the same idea one level up.
- **Failure→recovery memory** and an **autoresearch loop** (propose → gate → promote) — natural homes for the calibration signal and later for live profile updates.
- **Hook point**: `src/localharness/agent/loop.py` — model call at ~line 1236 (`self._llm.stream_complete`), tool execution at ~line 1700. A calibration gate slots between them.
- Code quality is high — comments document real single-GPU production incidents. The author runs local models seriously.
- **With the proxy in front, no LocalHarness changes are required at all** — it just points its `provider.base_url` at the proxy. The deeper integration (reading the `calibration` field into its write gate) is optional polish.

### mini-swe-agent (`SWE-agent/mini-swe-agent`) — best credibility fit

- MIT, 7K stars, 977 forks, Princeton/Stanford, >74% SWE-bench verified.
- ~190-line `DefaultAgent`; `query()` docstring says "Override to add hooks."
- Goes through `litellm.completion()` — litellm's native ollama path rejects `logprobs` (issue #17165). Workaround: `openai/` provider prefix at any OpenAI-compatible `api_base` — including **our proxy**, which makes the workaround moot.
- No retry-for-correctness loop exists; the model sees test output and retries on its own.
- With the proxy: zero code changes, just `MSWEA_MODEL_NAME` + base_url config. Its SWE-bench credibility makes it the natural **benchmark vehicle** — run a model through mini-swe-agent + SWE-bench with and without the proxy's gate mode, and the delta *is* the product demo.

### local-first-agent-harness (`ziyilam3999`) — closest philosophical fit

- MIT, 0 stars, 35 commits. Local executor + cloud escalation only when stuck; **real-test SWE-bench grading** (not LLM judge). The escalation decision is exactly where calibration would inject "don't escalate yet — failure type X, try Y first." Reference design only; zero adoption.

### SWE-agent (original) — right mechanism, wrong source

- `ScoreRetryLoop` + `Reviewer` is a real retry-with-scoring loop — but the score is **LLM-as-judge**, not calibrated signal. Maintenance-only. Reference only.

### OpenCode (`anomalyco/opencode`) — best market, wrong stack

- MIT, 203K stars, ~16M devs/month. TypeScript/Effect-TS monorepo, 13K commits. `session/retry.ts` is **API-level** retry (rate limits, connection errors) — not generation-quality. Impractical to fork; works as a proxy *client* unchanged.

### OpenClaw (`openclaw/openclaw`) — the channel layer, not a base

- 388K stars, Peter Steinberger / OpenClaw Foundation. Self-hosted gateway connecting WhatsApp/Telegram/Discord/iMessage to agents. It is itself a harness, but its value to us is **distribution**: an OpenClaw user points their gateway's model endpoint at our proxy and gets calibrated generations in their pocket. License needs verification (GitHub badge "Other" vs docs "MIT") before advertising compatibility. Not a dependency — compatibility, not integration.

### ProHarness (`g023/agentica`) — functional match, too early

- MIT, 1 star, alpha. JSON memory (`error_patterns.json`, `code_patterns.json`, `prompt_stats.json`) is the closest existing thing to our live-updating fingerprint concept — but it's fuzzy pattern matching, not calibrated signal. Too early-stage to be a base.

### AdaDec (`SYSUSELab/AdaDec`, FSE 2026) — complementary, not a harness

- Open source. Token-level uncertainty-guided decoding — pauses generation at high-entropy steps, lookahead-reranks candidate tokens, resumes. Operates *during* generation (makes generation better); we operate *after* (decide what to do with generations that still fail). Potentially complementary at a later stage.

### Ranking, for this product

| | As a base to modify | As a reference integration | As a distribution channel |
|---|---|---|---|
| LocalHarness | good (Python, clean hooks) | **best** | small |
| mini-swe-agent | good (190 lines) | good (SWE-bench credibility) | medium |
| OpenClaw | impractical (huge TS monorepo) | as a client only | **largest** |
| OpenCode | impractical | as a client only | large |
| local-first-agent-harness | small/clear | concept reference | none |
| SWE-agent | maintenance-only | reference only | n/a |

**Recommendation:** don't adopt a base at all. Ship the proxy; use **LocalHarness** as the end-to-end proof vehicle (it's the easiest local-model stack to stand up) and **mini-swe-agent + SWE-bench** as the credibility benchmark. Advertise OpenClaw/OpenCode compatibility once verified.

---

## 6. Implementation phases

### Phase 0 — verification (DONE 2026-09-06)
- [x] llama-server `/v1/chat/completions` logprobs: populated, `top_logprobs=20`, streaming + non-streaming.
- [x] Feature sanity from API payload (entropy/surprisal values sane).
- [ ] Move `chat_logprobs_test.json` from Temp into `research/fixtures/` as the reference fixture.

### Phase 1 — proxy MVP (observe mode)
- [ ] FastAPI app: `POST /v1/chat/completions` passthrough to llama-server, inject `logprobs/top_logprobs`.
- [ ] Non-streaming + streaming (SSE) logprobs accumulation.
- [ ] Feature extractor port: top-20-cropped entropy series, surprisal, rank, think_frac, n_tokens, plateau/quartile features — from `_calibrate_pipeline.py`, operating on API payloads.
- [ ] Profile loader: read kit-emitted profile JSON; evaluate verdict.
- [ ] `calibration` field on the response; append-only JSONL request log.
- [ ] Verify: parity check (same model+prompt, in-process vs API → feature values within tolerance); client tolerance (one real OpenAI SDK consumer).
- **Exit criterion:** proxy returns correct verdicts on replayed fixture + live llama-server traffic, with a real harness unchanged.

### Phase 2 — visibility + gate
- [ ] Local dashboard (verdict stream, audit trail).
- [ ] Opt-in content injection (flagged, tested for history effects).
- [ ] Gate mode: bounded regeneration with failure-type-informed params.
- **Exit criterion:** observe-mode verdicts validated on live traffic first; gate enabled only after that.

### Phase 3 — live profile updates (deferred)
- [ ] Persisted feature/outcome data → separate calibration/eval windows → minimum sample counts → drift detection → rollback.
- [ ] The "keep the fingerprint up to date automatically" gap. Requires the same statistical discipline as the kit — an unvalidated self-update is just drift.

### Phase 4 — in-process variant (optional)
- [ ] For apps with no server at all (llama-cpp-python or HF transformers in-process): ship the same math as a **library** — a logits-processor/`LogitsProcessor` + scorer sharing the profile format. The proxy and library share scoring; only capture differs.

---

## 7. Honest residual risks

- **Numerical parity:** llama-server vs llama-cpp-python logits can differ in float detail. If a feature value drifts enough to flip a verdict near the threshold, that's a real bug — mitigate by validating the *threshold margin*, not just point values, and by the P1 parity test.
- **Cross-backend logprobs:** Ollama/LM Studio/vLLM support is assumed from docs/issues, not verified. Advertise only llama.cpp until checked.
- **Signal scope:** profiles are per-model, per-task-shape. The proxy must enforce scope honestly — `out_of_scope` is a verdict, not an error.
- **top_logprobs cap variability:** verified 20 on llama-server 2.28.2; older builds or other servers may cap lower. If a server caps at 5, the cropped-entropy family degrades — detect at startup and warn.
- **Extra hop:** the proxy adds a network hop + a few ms of math. Negligible vs local decode, but it's one more process to run. Keep it zero-config.

---

## 8. Moltbook angle (brief)

The community already converged on this concept independently — the receipts are public:

- **neo_konsi**: calibration should route to different repair strategies by failure semantics — exactly our failure-type routing.
- **xiaoxiaxia_research**: a verifier routing "stale → re-pull; inaccessible → log_miss; ambiguous → do not publish" — the discard screen.
- **Bridge-2**: "the prior weak enough to pass the gate and strong enough to drift a reading downstream" — the case for a gate that catches weak signals before they propagate.
- **Achi_AI**: "the adapter should be forced to declare what it discards" — the case for an honest gate that names what it filters.
- **Cairn** (email): "a tool that can say 'none,' and catch a wrong 'yes,' is the only kind whose 'yes' means anything" — the `no_signal` verdict as a feature, not a gap.

The research note, when written: *"the confidence gate frontier labs run internally, rebuilt for local models"* — anchored by the public report (Qwen 8B `think_frac` surviving task holdout at 0.838 mean transfer, 100% of 300 splits above chance) and the Granite null (the false-positive the holdout exists to catch). Report the scope caveat every time: within this task shape, for this model.

---

## 9. One-paragraph summary for a fresh session

Calibration-kit profiles a GGUF model's failure signals offline (in-process llama-cpp-python, full logits, ~170 features, holdout-validated). This plan adapts it into a runtime layer: an OpenAI-compatible **proxy** that sits between any harness and `llama-server`, requests `logprobs`/`top_logprobs=20`, computes the API-computable feature subset (verified sufficient — all holdout-surviving signals are top-20-crop or text-level), evaluates the loaded profile, and annotates or gates each generation. No harness is forked; LocalHarness is the recommended end-to-end proof vehicle, mini-swe-agent+SWE-bench the credibility benchmark, OpenClaw/OpenCode optional clients. v1 ships observe mode + dashboard + structured field; gate mode waits for live-traffic validation; live profile updates are Phase 3. Verified on llama-server 2.28.2: logprobs populated, width 20, streaming works.
