# Local Model Calibration Kit

A runtime calibration layer for local coding models. Install it, point your
coding harness at the proxy, and it watches every generation, scores it with a
model-specific entropy signal, and re-learns from your recent work every night.

It is not a new coding harness. It sits between your existing harness (Aider,
Continue, Cline, LocalHarness, mini-swe-agent, or any OpenAI-compatible client)
and your local inference server (llama-server, LM Studio, Ollama, vLLM). One
URL change and the harness is calibrated.

## What it does

1. **Observes invisibly.** The proxy records token-level logprobs and outcomes
   from every request. In `observe` mode it does not change behavior; it just
   builds data.
2. **Scores live generations.** For every response it returns a
   `calibration` verdict — `probably_fine`, `likely_wrong`, `uncertain`,
   `no_signal`, or `out_of_scope` — plus the signal value and the profile it
   used.
3. **Passes a plan.** The `intervention_plan` lists ranked recovery strategies
   and conditional "if the signal reads this way, expect these failure modes,
   try X first" rules from the model's profile.
4. **Re-learns overnight.** `calibrate proxy --reanalyze-at 02:00
   --window-tasks 200` re-runs the calibration pipeline on the last 200 unique
   tasks every night and promotes a new profile only if it is no worse on
   held-out data. The fingerprint drifts with your actual task pool.
5. **Gates only when asked.** `gate` mode regenerates likely-wrong responses
   with a different seed/temperature, bounded by `--max-regenerations`.

Everything is local: no API calls, no telemetry, no cloud.

## Quickstart

```bash
# 1. One-time setup: auto-detect backend, match profile, write settings.
calibrate setup --profiles-dir examples

# 2. Start the proxy using the settings file it wrote.
calibrate proxy --config /path/to/settings.json

# 3. Point your harness at http://127.0.0.1:9090/v1 and use it normally.
```

`calibrate setup` probes common local ports (`8080` llama-server, `1234` LM
Studio, `11434` Ollama, `8000` vLLM), matches the loaded model to a profile in
`examples/`, writes a settings file, and prints the exact command for Aider,
Continue, Cline, or a generic start. See
`examples/harness-integrations/README.md` for harness-specific configs.

### If you do not have a profile yet

The kit can still run in `observe` mode and record data. Once you have a log
with outcomes, build a profile offline:

```bash
python calibrate.py learn --log proxy_YYYY-MM-DD.jsonl --output my_profile.json
```

Or run a full calibration from a task bank to generate a profile from scratch:

```bash
python calibrate.py run --model your-model.gguf
python calibrate.py export --profile _calibration_<label>.json --output AgentAnalysis.md
```

The full calibration is the original offline path. It is still the right way to
produce a robust profile when no example profile exists for your exact model and
quantization.

## Scope

This is not a "know if your model is right about anything" tool. It calibrates
against **benchmark-verifiable pass/fail tasks** — code with automated tests.
Every entropy signal, threshold, and intervention rank comes from one question:
did the generated code pass its tests, yes or no. It has not been tested on
open-ended or subjective output (freeform Q&A, creative writing, anything
without an automated correctness check) — the entropy signal there is unproven,
not assumed to transfer. If your use case does not reduce to pass/fail, this is
not calibrated for it.

## The runtime proxy in detail

### Response headers

Non-streaming responses carry:

- `X-Calibration-Verdict`
- `X-Calibration-Profile`
- `X-Calibration-Request-Id` — look up the full record later at
  `/v1/calibration/request/{request_id}`
- `X-Calibration-Regenerated` / `X-Calibration-Regeneration-Count` when in
  gate mode

Streaming clients get the same `request_id` in the final SSE chunk and can call
the lookup endpoint after the stream.

### The `calibration` payload

When verbose mode is on, the response body includes a `calibration` object:

```json
{
  "verdict": "likely_wrong",
  "signal": {"name": "plateau_start_quartile", "value": 0.0, "threshold": -0.5, "direction": "high=bad"},
  "predicted_failure_class": null,
  "recommended_intervention": "test_retry",
  "intervention_plan": [
    {"intervention": "test_retry", "new_coverage": 7, "recovered": 7, "unique_recovered": 4},
    {"intervention": "temp_retry", "new_coverage": 3, "recovered": 6, "unique_recovered": 1},
    {"intervention": "test_retry", "when": "n_tokens below 3528.0541",
     "predicted_error_types": ["assertion"], "recovered": 3, "attempted": 9, "recovery_rate": 0.33}
  ],
  "scope_note": "Profile for qwen3-4b-instruct calibrated 2026-09-05 on 108 generations."
}
```

`intervention_plan` combines the greedy-set-cover escalation order with
conditional rules from `signal_failure_routing`. That is the pre-test plan:
before the tests run, the signal predicts which failure modes are likely and
which repair strategy has the best recovery rate for them.

### Nightly reanalysis

The proxy can re-build the profile from recent records on a schedule:

```bash
calibrate proxy --reanalyze-at 02:00 --window-tasks 200 --window-hours 168
```

- `--window-tasks` keeps the N most recent unique tasks. Older tasks fall out of
  the window.
- `--window-hours` adds an age cutoff.
- A candidate profile is promoted only if it is at least as good as the active
  one on held-out data and not below chance. Older profiles are backed up to
  `profiles.bak/`.

This is the closed loop: today's work becomes tonight's training data; tomorrow
uses the updated fingerprint.

## What the full calibration still gives you

A full `calibrate run` is the strongest way to build a profile when you do not
have one. It:

- Searches ~170 candidate statistics in a single generation pass.
- Corrects for multiple comparisons.
- Validates the winner on held-out records and held-out *tasks* (task-level
  holdout is the check for "does this apply to new questions?").
- Sweeps 7 recovery interventions and ranks them by coverage.
- Exports `AgentAnalysis.md` that any agent reads as standing instructions.

```bash
python calibrate.py run --model your-model.gguf
python calibrate.py report --profile _calibration_<label>.json
python calibrate.py export --profile _calibration_<label>.json --output AgentAnalysis.md
```

`reanalyze` re-runs the analysis on saved raw data with no GPU time:

```bash
python calibrate.py reanalyze --raw _calibration_<label>_raw.jsonl
```

## Reproducibility

Runs are reproducible by default: a fixed sampling seed means the same command
produces the same generations. That is deliberate — a published result should be
reproducible. It also means re-running the same command is not a second sample;
change the seed to draw an independent sample:

```bash
python calibrate.py run --model your-model.gguf --repeats 10
python calibrate.py run --model your-model.gguf --repeats 10 --seed 77
```

Interrupted runs resume themselves from checkpoint. Change any setting and the
old checkpoint is set aside as `.stale`.

## Requirements

- Python 3.10+ (for the Python workflow), or the `dist/calibrate.exe` binary on
  Windows.
- `llama-cpp-python` and `numpy` (see `requirements.txt`) for full calibration.
- A GGUF model (3-8B recommended).
- A GPU is recommended but not required. Works on NVIDIA CUDA, AMD ROCm, Apple
  Metal, or CPU-only.

The runtime proxy itself only needs a local OpenAI-compatible inference server
and a profile. It does not load the GGUF itself.

## Known limitations

- **The `__subclasses__` sandbox escape is open.** The threat model is
  accidental damage from model output, not a determined adversary.
- **Scope is benchmark-verifiable pass/fail code tasks.** The entropy signal is
  not tested on open-ended or subjective output.
- **Signals are distribution-level only.** No intermediate-layer hidden states.
- **The evidence base is small.** See Examples.

## Before you calibrate

Check your model's config. The calibration sweeps sampling parameters around the
model's recommended values — wrong starting values produce garbage data. Check
`CORE_MODEL_CONFIGS.md` or the model's HuggingFace card.

## Execution sandbox

The calibrator includes a Python-level sandbox that blocks network access,
process spawning, `ctypes`, and file writes outside the task temp directory.
See `METHODOLOGY.md` for the threat model and what is not blocked.

## Examples

`examples/` holds every calibration run, with raw records. Read these before
buying. They disagree with each other, and that is the point.

### Verified signals

| model | bank | probes | failures | signal | transfer | recoverable |
|---|---|---|---|---|---|---|
| Qwen3-8B Q5_K_M (thinking) | 224-task | 224 | 37 | `think_frac` high=good | 0.838 mean, 100% above chance | 17/37 |
| Qwen3-4B-Instruct-2507 Q5_K_L | 60-task | 108 | 20 | `max_entropy`/plateau high=bad | 0.73 mean, 92% above chance | 11/20 |
| granite-4.1-3b Q5_K_M | 60-task | 60 | 8 | none — below chance | — | 4/8 |
| mini-coder-4b Q8_0 | 18-task | 36 | 11 | none | — | 4/11 |

Two models have usable signals that transfer to unseen tasks; two do not. That
is the honest number, and it is why you run this rather than copy someone else's
config.

On the same data, the statistics everyone reports find nothing: `max_entropy`
d=+0.17, `mean_entropy` d=+0.15. A short opening spike plus a long calm tail
averages to the same number as a flat middling trajectory. Averaging across a
generation destroys the signal; pooling across models cancels what survives. One
prominent measure advertises being "comparable across models and tasks without
threshold recalibration" — that is the assumption these results contradict.

See `CHANGELOG.md` for feature history and `METHODOLOGY.md` for the full
statistical pipeline.
