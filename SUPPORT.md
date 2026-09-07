# Support

Sold by **Charles D. Vaught**, sole proprietor. This is a one-person
project, and the promises below are sized to be ones a one-person project
can actually keep.

## How to get help

**Email:** charlesdvaught@gmail.com

Put `calibration-kit` in the subject line.

**Response window:** 2–3 business days. If you have not heard back in
three business days, resend — assume it went astray rather than that it
was ignored.

Bug reports and feature requests can also go to the issue tracker on the
repository your purchase gave you access to. Issues are public to other
buyers, which is usually a feature: someone else has often hit the same
thing.

## What support covers

- The kit will not install, or crashes on your hardware
- A calibration run fails, hangs, or produces a profile the exporter
  cannot read
- The report says something you think is wrong, and you can point at the
  run that shows it
- Your repository invite never arrived, or you lost access
- Questions about what a number in your own report means

Send the failing command, the console output, and — if the run got far
enough to write one — the `_calibration_<label>.json` profile. That file
is what makes a report diagnosable. It contains no code from your machine
and no identifiers.

## What support does not cover

- Making a model score better. The kit measures your model; it does not
  improve it, and no support ticket can make a model have a signal it
  does not have.
- Choosing, downloading, quantizing, or tuning models.
- Getting CUDA, ROCm, or `llama-cpp-python` built on your system. There is
  install guidance in `SKILL.md`, but a broken local toolchain is between
  you and that toolchain's maintainers.
- Interpreting results for use cases the kit is not calibrated for. It
  measures pass/fail code tasks. If your use case has no automated
  correctness check, the kit has nothing to say about it, and that is
  documented before you buy.
- Writing your integration code. The kit ships an OpenAI-compatible proxy and documented configs for Aider, Continue, Cline, LocalHarness, and mini-swe-agent in `examples/harness-integrations/README.md`, and a `calibrate setup` wizard that prints the exact command for your harness. Support still does not write bespoke integrations beyond that.

## Hardware and prerequisites

You need a machine that can run GGUF models locally through
`llama-cpp-python`, and enough VRAM or RAM for the model you want to
calibrate. A calibration run is hours of generation, not minutes. Run
`python calibrate.py estimate --model your-model.gguf` before committing
to a full run — it tells you what the run will cost you in time on your
own hardware.

## Updates

Updates ship through the private repository. `git pull` gets them. There
is no update server, no version check, and nothing in the kit contacts
the network on its own.

## Security and privacy

The kit makes no network calls during calibration. `federation.py` writes
a local file and sends nothing. If you find something that contradicts
that, treat it as a security report and email it — that one gets answered
faster than 2–3 days.
