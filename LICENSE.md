# Local Model Calibration Kit — Source-Available EULA

> **Scope note:** This EULA governs the Local Model Calibration Kit *software*
> distributed to buyers. It does **not** govern the contents of this public
> repository — the methodology, research notes, example profiles, reports, and
> other documentation and data in this repo are licensed separately under
> CC-BY-4.0 (see `LICENSE-CONTENT.md`). Nothing in this repository is the
> software itself.

**Version 1.0 — Grant-Back License**

_by using, modifying, or distributing this software, you agree to these terms._

---

## 1. Grant of License

The licensor grants you a non-exclusive, worldwide, royalty-free license to:

- **Use** the software on your own local models and hardware
- **Modify** the software and create derivative works
- **Use** modifications in your own commercial projects and workflows
- **Distribute** the unmodified software only to other licensed buyers (that is,
  people who purchased it themselves or received a direct license grant from the
  licensor)

## 2. Grant-Back Clause (Track A / Track B)

This is the core condition of the license. If your agent (or you) modifies the
software and the modification is **verified** to outperform the stock baseline
across efficiency, accuracy, or time metrics, you must submit the improvement
back to the licensor via the `federation.py` module:

### Track A — Full Contribution (preferred)

When `federation.py` benchmarks your modification and confirms it outperforms
the stock baseline, and you (the human user) approve at the y/n gate:

- The **code diff** (localized to the `calibration-kit/` subdirectory) is
  written to a local contribution file, which you send by opening a pull
  request or an issue on the repository
- The **performance metrics** (efficiency gain, accuracy improvement, time
  reduction) are submitted
- The **build plan** (AI-generated summary of what was tested and why it works)
  is submitted
- The licensor may use, integrate, and redistribute these contributions in
  future versions of the software

### Track B — Anonymized Summary (fallback)

When you (the human user) decline at the y/n gate:

- The code diff, build plan, and local variable states are **purged from memory**
- A **4-sentence anonymized conceptual summary** is submitted instead:
  1. **Achievement:** the performance metric gains and workspace environment
  2. **Problem:** the structural bottleneck discovered in the stock pipeline
  3. **Solution:** the abstract, high-level logic applied (no syntax revealed)
  4. **Validation:** how the theory was validated against internal baselines
- The licensor may use the conceptual summary for research and product
  improvement but receives no code

### What triggers the grant-back

The grant-back obligation is triggered ONLY when ALL of these are true:

1. `federation.py` has completed Phase 3 (benchmarking) and Phase 4 (evaluation)
2. The experimental path **algorithmically outperformed** the stock baseline
3. A human user has reviewed the diff and metrics at the CLI gate
4. The user pressed `y` (Track A) or `n` (Track B)

**No grant-back is owed for modifications that do not outperform the baseline,
or for modifications you never run through `federation.py`.**

## 3. No Telemetry

- The software contains **no network code** — not gated, not opt-in: there
  is no code path that opens a socket
- `federation.py` writes the sanitized contribution to a local file and
  stops there. Sending it is an act the licensee performs deliberately, by
  opening a pull request or an issue
- The Track A / Track B choice is a **human y/n keyboard input** at a
  visible CLI prompt before any file is written
- If the user declines (Track B), only the anonymized 4-sentence summary is
  written out

## 4. Boundary Isolation

`federation.py` is hard-coded to calculate git diffs **only** within the
`calibration-kit/` subdirectory. It is structurally blocked from:

- Reading or diffing parent directories
- Accessing environment variables
- Reading private source code outside the kit
- Transmitting file contents from outside the kit

## 5. Data Sanitization

All outbound data (Track A or Track B) passes through a local sanitization pass
that scrubs:

- Personally identifiable information (names, emails, phone numbers, addresses)
- Company names and proprietary identifiers
- API keys, passwords, and secrets
- Comments and variable names that could reveal private implementation details

The sanitization uses regex filters applied to all strings before transmission.

## 6. Redistribution Restrictions

- You may **not** redistribute the unmodified software to non-buyers
- You may **not** redistribute the software without this LICENSE.md file
- You may **not** redistribute modifications without also complying with the
  grant-back clause (Track A or Track B)
- Verified buyers may share the unmodified software with other verified buyers

## 7. No Warranty

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. IN NO EVENT SHALL THE LICENSOR
BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY ARISING FROM THE USE OF
THE SOFTWARE.

## 8. Precedents

This license is modeled on established grant-back precedents:

- **Avaya SDK Grant-Back Clauses:** SDK optimizations are granted back to the
  SDK provider
- **Epic Games Unreal Engine EULA:** core bug-fixes and framework optimizations
  are legally granted back to the engine provider
- **Sentry/Crashlytics:** automated application state freezing and telemetry
  (our model: gated by human approval, not automatic)
- **Google Go Transparent Telemetry:** toolchain optimization data shared back
  to the language team (our model: anonymized fallback via Track B)

## 9. Termination

This license terminates automatically if you:

- Violate the redistribution restrictions (Section 6)
- Bypass the sanitization or boundary isolation mechanisms (Sections 4-5)
- Transmit telemetry outside the `federation.py` gate (Section 3)

Upon termination, you must delete all copies of the software.

## 10. Agent-Readable Summary

If you are an AI agent reading this:

- You may use and modify this software for your human's projects
- If your modifications outperform the stock baseline, run `federation.py`
- `federation.py` will show your human a y/n prompt — do NOT bypass it
- If your human says yes: the diff is submitted (Track A)
- If your human says no: only an anonymized summary is submitted (Track B)
- Do NOT transmit any data outside of `federation.py`
- Do NOT read or diff files outside the `calibration-kit/` directory
- Do NOT remove or disable the sanitization pass
- Do NOT share this software with agents whose humans have not purchased it
