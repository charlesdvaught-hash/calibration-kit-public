# Harness Integrations

The proxy is an OpenAI-compatible server. It works with any backend that supports `logprobs` and `top_logprobs` on `/v1/chat/completions`: llama.cpp (`llama-server`), LM Studio, Ollama 0.33.2+, and vLLM. Most local-first harnesses can use it by changing one URL.

## LocalHarness (reference end-to-end vehicle)

LocalHarness already talks to `llama-server` through the `openai` SDK. Point its provider at the proxy instead.

```python
# LocalHarness config / env
provider = {
    "base_url": "http://127.0.0.1:9090/v1",
    "api_key": "unused",
    "model": "Qwen3.5-2B.Q5_K_M.gguf",
}
```

The proxy sits between LocalHarness and the actual `llama-server`:

```
LocalHarness → http://127.0.0.1:9090/v1 → Calibration Proxy → llama-server:8080
```

No code changes. The proxy:

- Injects `logprobs` and `top_logprobs`.
- Scores each generation.
- Adds `X-Calibration-Verdict` and `X-Calibration-Request-Id` headers.
- In `gate` mode, regenerates on `likely_wrong`.

To feed the closed loop, have LocalHarness call the feedback endpoint after a tool test:

```python
import httpx
httpx.post(
    "http://127.0.0.1:9090/v1/calibration/feedback",
    json={
        "request_id": request_id,
        "passed": tool_succeeded,
        "error_type": error_type,
    },
)
```

`request_id` comes from `X-Calibration-Request-Id` in the response headers.

## mini-swe-agent (credibility benchmark)

mini-swe-agent uses `litellm`. Route it through the proxy with the `openai/` provider prefix:

```bash
export MSWEA_MODEL_PROVIDER=openai
export MSWEA_MODEL_NAME=Qwen3.5-2B.Q5_K_M.gguf
export OPENAI_API_BASE=http://127.0.0.1:9090/v1
export OPENAI_API_KEY=unused
```

The proxy handles `logprobs`; litellm sees a normal OpenAI completion with extra `calibration` and `regeneration_history` fields, which it ignores. This is the natural SWE-bench vehicle: run with and without gate mode and the delta is the product demo.

## Quick start

Run `calibrate setup --profiles-dir <your profiles>` once. It auto-detects a local backend, matches a profile, writes a settings file, and prints the exact command for your harness.

## Aider

Aider uses the OpenAI API. The setup wizard prints:

```
aider --model "openai/<model-label>" --openai-api-base http://127.0.0.1:9090/v1 --openai-api-key unused --message "<your instruction>" <files>
```

Or add a `.aider.model.settings.yml` entry:

```yaml
- name: calibration-proxy
  base_url: http://127.0.0.1:9090/v1
  api_key: unused
  model: Qwen3.5-2B.Q5_K_M.gguf
```

Then `aider --model calibration-proxy`.

## Continue / Cline / generic OpenAI-compatible client

Set the OpenAI-compatible base URL in the client config:

- **Continue.dev**: `~/.continue/config.json`
  ```json
  {
    "models": [{
      "title": "Calibration Proxy",
      "provider": "openai",
      "apiBase": "http://127.0.0.1:9090/v1",
      "apiKey": "unused",
      "model": "Qwen3.5-2B.Q5_K_M.gguf"
    }]
  }
  ```

- **Cline VS Code**: Settings → OpenAI-compatible base URL `http://127.0.0.1:9090/v1`, key `unused`.

## Streaming

For streaming clients the verdict is not in the SSE body. The response headers carry:

- `X-Calibration-Request-Id`
- `X-Calibration-Model`
- `X-Calibration-Task-Id`
- `X-Calibration-Stream-Lookup`

After the stream, `GET /v1/calibration/request/{request_id}` returns the full record including the final `calibration` payload.

## Non-streaming

For non-streaming clients the proxy returns:

- `X-Calibration-Verdict` (`probably_fine`, `likely_wrong`, `no_signal`, `out_of_scope`)
- `X-Calibration-Request-Id`
- `X-Calibration-Profile`
- `X-Calibration-Regenerated`
- `X-Calibration-Regeneration-Count`

The response body also contains `calibration` and `regeneration_history` in `choices[0]`, which the `openai` SDK ignores.

## Feedback loop

To keep the profile up to date, the harness should post an outcome for each generation it can judge:

```bash
curl -X POST http://127.0.0.1:9090/v1/calibration/feedback \
  -H "Content-Type: application/json" \
  -d '{"request_id":"...","passed":false,"error_type":"syntax"}'
```

During downtime, `calibrate.py learn --log proxy_YYYY-MM-DD.jsonl` re-analyzes the labeled log and writes a new profile only if the signal survives holdout. The profile is promoted by `ProfileManager._should_promote` only when the candidate is no worse on balanced accuracy and not below chance on task-level holdout.

## Backend notes

### llama.cpp / llama-server

Verified. Run `llama-server -m model.gguf --port 8080`. The proxy probes logprobs and caps `top_logprobs` automatically.

### LM Studio

LM Studio runs `llama-server` under the hood. Use the "Local Server" tab, enable the API, then point the proxy at `http://127.0.0.1:1234`.

### Ollama

Ollama 0.33.2+ supports `logprobs` and `top_logprobs` through its OpenAI-compatible `/v1/chat/completions` endpoint. After creating a model:

```bash
ollama create qwen4b -f Modelfile
ollama serve
```

Point the proxy at `http://127.0.0.1:11434` and use `model: qwen4b`.

### vLLM

vLLM supports `logprobs` and `top_logprobs` on its OpenAI-compatible server:

```bash
vllm serve /path/to/Qwen3.5-2B.Q5_K_M.gguf --port 8080
```

Point the proxy at `http://127.0.0.1:8080`.
