# Custom task files

Calibrate your model on **your** tasks, not just the built-in bank.

The built-in 60-task bank is tuned to the "cusp of failure" region for small
coding models. But the most informative tasks for your deployment are the
ones your deployment actually runs — the kit's whole point is that the
signal is per-model, per-quantization, and per-task-set. A custom task file
lets you measure what your model does on the work you care about.

## The file format

A JSON file containing either a list of tasks or `{"tasks": [...]}`.
Each task is one object:

```json
{
  "tasks": [
    {
      "id": "csv_dedup",
      "filename": "csv_dedup.py",
      "func_name": "dedup_rows",
      "desc": "Write a function dedup_rows(rows) that takes a list of equal-length string lists and returns the list with exact-duplicate rows removed, preserving first-seen order.",
      "tests": [
        ["dedup_rows([[\"a\",\"b\"],[\"a\",\"b\"],[\"c\"]])", "[[\"a\",\"b\"],[\"c\"]]"],
        ["dedup_rows([])", "[]"]
      ],
      "reference": "def dedup_rows(rows):\n    seen = set()\n    out = []\n    for r in rows:\n        k = tuple(r)\n        if k not in seen:\n            seen.add(k)\n            out.append(r)\n    return out\n"
    }
  ]
}
```

| field | required | meaning |
|---|---|---|
| `id` | yes | unique short name — appears in reports and checkpoints |
| `filename` | yes | the `.py` module the model is asked to write |
| `func_name` | yes | the function the tests call |
| `desc` | yes | the prompt. See below — this is the field that makes or breaks a task |
| `tests` | yes | list of `[expression, expected_expression]` pairs |
| `reference` | yes | a known-good implementation, as source text |

## `desc` must fully determine the behaviour

Every edge case a test checks has to be answerable from `desc` alone. If a
test checks `dedup_rows([])` but `desc` never says what an empty input should
return, a model that fails has not failed at coding — it has failed at
reading your mind. Those failures measure the prompt, not the model, and
they are noise in every statistic the kit reports.

## Prove your file before you spend GPU time

```bash
python calibrate.py validate-tasks my_tasks.json
```

This runs each task's `reference` implementation against its own `tests` —
the same check `python _task_bank.py` performs on the built-in bank. A file
with a wrong expected value is **refused**, not warned about: bad ground
truth corrupts every downstream signal invisibly. Validation runs the code
in the same sandboxed harness the pipeline uses.

## Run it

```bash
# Only your tasks
python calibrate.py run --model your-model.gguf --tasks my_tasks.json

# Your tasks plus the built-in bank (ids must not collide)
python calibrate.py run --model your-model.gguf --tasks my_tasks.json --tasks-mode extend

# How long will it take?
python calibrate.py estimate --model your-model.gguf --tasks my_tasks.json
```

## What the profile records

A run on custom tasks stamps the file's content hash into the profile and
the checkpoint signature (`task_source`). Results from different task sets
are different measurements — the kit will never silently resume a checkpoint
across a task-file change, and two profiles always say which tasks produced
them.

## v1 limits

- Custom tasks are **function tasks only**: one module, one function, eval-
  based tests. The multi-file assembly format is internal.
- The task count is the sample size. At temperature 0 each task yields one
  independent observation — a 5-task file cannot support a signal claim no
  matter how many `--repeats` you run. The power analysis in the report
  tells you what your task set can and cannot resolve.
- Keep tasks in the cusp region: things your model passes and fails
  wholesale carry no signal. The data lives in the tasks it *sometimes*
  gets right.

## The shipped HumanEval bank

`_humaneval_tasks.json` is a converted copy of OpenAI's HumanEval dataset
(164 function-completion tasks, MIT-licensed � original:
github.com/openai/human-eval). `_humaneval_convert.py` performs the
conversion: each task's docstring becomes the spec, the prompt plus
canonical solution becomes the reference, and the `check()` asserts are
parsed into eval-based tests. Every converted task was proven against its
canonical solution before it entered the bank.

**Contamination caveat.** HumanEval has been public since 2021 and is
known to appear in model training corpora � treat raw pass rates on it as
a floor, not a ceiling. What it cannot fake is the *signal* question: a
memorized answer that happens to be right still goes through the model's
own logit distribution, and the task-level holdout is exactly the check
that asks whether the signal generalizes to tasks the calibration never
saw. Where contamination would inflate a claim, the docs and report say
so; the Qwen3-8B results quote the task-level transfer number alongside
the headline accuracy for this reason.

Regenerate the bank with `python _humaneval_convert.py` � requires a
local copy of the HumanEval parquet (`_humaneval_data/`, not shipped;
`huggingface_hub` snapshot download) plus `pandas`/`pyarrow`.
