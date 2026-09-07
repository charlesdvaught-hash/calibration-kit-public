# Refund policy

Sold by **Charles D. Vaught**, sole proprietor, through **Polar**, which
is the merchant of record. Polar processes the payment and the refund;
the terms below are mine.

## The guarantee

**A completed run gives you something you can act on, or your money
back.**

Concretely, a run satisfies the guarantee if it produces either:

- a **usable signal** — a statistic, a threshold, and a direction you can
  implement as a gate on your own model; **or**
- a **repair order** — an intervention ranking where at least one
  strategy measurably recovers failures your model produced; **or**
- an explicit **`none` verdict backed by a power analysis** — the effect
  size observed, the smallest effect the run could have detected, and the
  `--repeats` setting that would settle the question.

If a completed run gives you none of those three, email me and I will
refund you in full.

## Why `none` counts

This is the part worth reading before you buy, because it is the part
people are surprised by.

Not every model has a usable entropy signal. On the models tested so far,
most did not. That is a real property of the models, not a defect in the
kit, and the kit is built to report it honestly rather than manufacture a
threshold that will not hold up.

A `none` verdict with the statistics behind it is a delivered result: it
tells you that building an entropy gate for that model would be spending
compute to buy nothing, and it tells you how much more data it would take
to be sure. That is worth the price on its own — it is cheaper than finding out
the slow way.

What is **not** a delivered result is a run that tells you nothing at
all: no signal, no working repair, and no power analysis to interpret the
silence. That is what the guarantee covers.

## Other refunds

- **It will not run on your hardware** and we cannot get it running
  together: full refund.
- **You bought it twice**, or bought it by mistake and have not used it:
  full refund, just ask.
- **Something is materially different from what the README described**
  at the time you bought: full refund.

## How to request one

Email **charlesdvaught@gmail.com** with `refund` in the subject line and
your Polar order number. Say briefly what happened; if it is a guarantee
claim, attach the `_calibration_<label>.json` profile from the run, since
that is what shows what the run actually produced.

I aim to answer within 2–3 business days. Approved refunds are issued
through Polar and land back on your original payment method on their
timeline, typically 5–10 business days.

## What happens to your access

A refund ends the license. Your collaborator access to the private
repository is removed, and you are asked to delete your copy of the kit.
Anything the kit produced from your own models — profiles, reports,
analyses — remains yours.

## What is not refundable

- Time or electricity spent on calibration runs.
- A run that produced a verdict you did not like. "My model has no
  signal" and "my model has a signal I hoped was stronger" are both
  results.
- Requests made after the kit has been redistributed to someone who did
  not buy it, which the license does not permit.
