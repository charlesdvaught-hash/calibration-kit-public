---
license: cc-by-4.0
task_categories:
  - text-generation
language:
  - en
tags:
  - calibration
  - uncertainty
  - entropy
  - local-llm
  - gguf
  - signal-detection
  - wrongness-prediction
size_categories:
  - n<1K
---

# Calibration Probe Results

Public evidence corpus of entropy-based wrongness signals in local coding models.
Collected via the [calibration probe](https://github.com/charlesdvaught-hash/calibration-kit-public).

## What this dataset contains

Each row is one probe run — a single execution of `probe.py` against a local
GGUF model on 42 standard Python coding tasks. The probe captures per-token
entropy trajectories during code generation, tests each generated solution,
and scans ~30 candidate signals for separation between passing and failing
generations.

| Field | Type | Description |
|-------|------|-------------|
| `model_label` | string | GGUF filename (e.g. `qwen3-4b-Q5_K_M.gguf`) |
| `n_ok` | int | Number of tasks passed |
| `n_fail` | int | Number of tasks failed |
| `per_task` | list | Per-task: `task_id`, `ok`, `n_semantic`, `trajectory_ds` (16-point downsampled entropy), `think_frac` |
| `scan_rows` | list | Top 20 signal candidates with Cohen's d, p-values, BH correction |
| `best_signal` | object\|null | The winning signal (if any survived correction) |
| `preset` | object | Sampling parameters used (temp, top_p, top_k) |
| `thinking` | bool | Whether thinking mode was enabled |

## What this dataset does NOT contain

- **No generated code** — the probe only sends entropy trajectories and pass/fail
- **No prompts** — tasks are standard public tasks from the calibration kit
- **No user identity** — no accounts, no names, no IP addresses
- **No model weights** — only the filename/quant label

## How to use

```python
from datasets import load_dataset

ds = load_dataset("charlesdvaught-hash/calibration-probe-results")

# Per-model signal rates
import pandas as pd
df = ds["train"].to_pandas()
df.groupby("model_label").agg(
    n_runs=("model_label", "count"),
    signal_rate=("best_signal", lambda x: x.notna().mean()),
    avg_pass=("n_ok", "mean"),
)
```

## How to contribute

Run the probe on your local model:

```bash
pip install llama-cpp-python numpy
python probe.py --model your-model.gguf
```

Then upload your results:

```bash
pip install huggingface_hub
python upload_to_hf.py probe_your-model_results.json --token hf_xxxxx
```

Get a token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

## Methodology

See [METHODOLOGY.md](https://github.com/charlesdvaught-hash/calibration-kit-public/blob/main/METHODOLOGY.md)
for the full statistical methodology: permutation tests, Benjamini-Hochberg
correction, record-level vs task-level holdout, and the reliability/validity
framing.

## Important caveats

1. **Signals are per-model and per-task-distribution.** A signal found on
   Qwen3-4B does not imply the same signal exists on other models. This
   dataset maps which models have signals and which don't — it does not
   establish universal rules.

2. **"No signal" is a valid result.** Some models genuinely don't have a
   usable entropy gating signal on this task distribution. This is not a
   failure of the method — it's an honest null.

3. **Underpowered runs are common.** If a model passes all 42 tasks, there
   are no failures to analyze. The dataset includes these runs but they
   should be filtered out when computing signal rates.

4. **The probe scans ~30 candidates, not the full 170.** The commercial
   calibration kit scans 170+ signals, adds task-level holdout, intervention
   routing, and a live proxy. This dataset reflects the stripped-down public
   probe only.

## License

CC-BY-4.0. See [LICENSE-CONTENT.md](https://github.com/charlesdvaught-hash/calibration-kit-public/blob/main/LICENSE-CONTENT.md).
