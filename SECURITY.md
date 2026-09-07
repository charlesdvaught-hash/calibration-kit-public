# Security policy

## Reporting

Email **charlesdvaught@gmail.com** with `security` in the subject line.
Security reports get answered ahead of the normal 2–3 business day support
window — assume faster, not slower.

## What the kit does and does not do

- **No network calls.** The calibration pipeline, the exporter, the report
  renderer, and `federation.py` contain no network code. If you find a code
  path that opens a socket, that is a security bug — report it.
- **Model-generated code runs on your machine.** `_sandbox.py` blocks
  network access, process spawning, `ctypes`, dangerous `os` functions,
  and file writes outside the task temp dir. The known `__subclasses__`
  escape is documented in the README — the threat model is accidental
  damage from model output, not a determined adversary. For hard
  isolation, run the kit inside a container or VM.
- **What leaves your machine:** nothing, automatically. `federation.py`
  writes a sanitized contribution file locally; sending it (a pull request
  or an issue you open yourself) is a deliberate act you perform after
  reading the file.
- **What the kit stores:** run records (`_calibration_*_raw.jsonl`) contain
  model-generated code and test output from calibration tasks — not your
  files, not your prompts. Profiles contain no identifiers.

## Scope

Vulnerabilities in the kit itself: sandbox escapes beyond the documented
one, unexpected network activity, the contribution sanitizer leaking
identifiers. For issues in `llama-cpp-python` or your model files, report
upstream — but if it affects how the kit uses them, tell me too.
