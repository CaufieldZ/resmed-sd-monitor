# Interpretation guide

How to read what this tool prints — the discipline that keeps device data from
becoming folk medicine. Everything here assumes you have read the scope boundary
in the README: these are therapy-monitoring cues, not diagnoses.

## Core metrics

- **REI (residual event index)** — events per hour of *therapy usage*, the device's
  own estimate. Common bands for context: < 5 typical therapy target, 5–15 mild,
  15–30 moderate, > 30 severe residual burden. **A residual REI ≥ 10 that persists
  across nights suggests treatment failure and re-evaluation** (insufficient
  pressure, leak, adherence, comorbidity — the tool cannot tell you which).
  The device index does not include RERAs, so true burden may be slightly higher.
- **OAI / CAI / HI** — the split that decides the next question:
  - **CAI rising after a pressure increase or a larger EPR → suspect treatment-emergent
    central sleep apnea (TECSA) / complex apnea.** Common contributors: pre-existing
    CSA tendency, excessive pressure, large EPR levels, heart failure, opioids.
    Direction: lower EPR / lower the ceiling first; bilevel or ASV if it persists —
    a specialist decision, not an APAP tweak.
  - OAI dominant → the pressure-headroom question (below).
- **Statistics over means.** Compare segments by median [IQR] + the Mann–Whitney p the
  report prints. **p ≥ 0.05 is "no clear difference", not "equal"** — single-night
  swings of 1–10 events/h are normal; averaging two nights per segment and calling
  the delta an improvement is how people chase ghosts.

## The pressure-headroom question

**Only the pressure–flatness curve answers "is there room for more pressure"** —
background flow limitation (FI) compared *across pressure bins within the same
nights*, with Ramp drive-by bins excluded.

- Curve flat from low to high bins (gain < 0.02) → the current range has already
  flattened the limitation background; raising floor or ceiling has limited expected
  benefit. Direction shifts to position, sleep stage, timing.
- Clear gain remaining → raising the floor is worth trying; re-evaluate after 1–2 weeks.
- **U/J-shape** (bottom mid-range, right end still climbing toward the ceiling) →
  the low segment is near its optimum and the high segment still wants more:
  that is a *ceiling* conversation, not a floor one.

Two disciplines are built into the tool — do not re-commit them when reading:

1. **Event-rate ratios are not evidence.** AutoSet raises pressure *after* events
   (measured on real data: median +0.3 cmH2O within 120 s of an event vs +0.03 at
   random times). "Many events in the high-pressure band" is that feedback loop's
   echo — it cannot show that pressure is ineffective. The report runs this feedback
   check explicitly and prints it before any pressure metric.
2. **Ramp bins must be excluded.** The climb from start pressure to therapy pressure
   leaves hundreds of low-pressure breaths; comparing them against fully-loaded high
   bins measures "ramp vs therapy", not a dose effect. Bins under 3 % of exposure are
   dropped automatically.

**Peak touching the ceiling ≠ the ceiling binding.** Look at *dwell*: sporadic
transient touches (< 3 % of breaths) are normal control behaviour; sustained dwell is
what means the ceiling is actually limiting therapy.

## Waveform layer

- **Flattening index (FI)** — per-breath inspiratory plateau relative to the night's
  own baseline (AASM v3's RERA wording: flattening "compared to baseline breathing").
  Absolute FI values mean nothing across devices/masks; only within-night comparisons
  and the cross-pressure curve are used.
- **Event clustering** — ≥ 3 events with adjacent gaps ≤ 2 min form a cluster. A high
  in-cluster share is the classic positional / REM-related cue: pressure usually does
  not fix it; position and timing do. The device records neither position nor stage,
  so clusters are a cue to investigate, never an attribution.
- **Periodic breathing** — reported when the sine-fit corr² reaches 0.10 (synthetic
  calibration: unmodulated ≈ 0.000, modulation depth 0.5 ≈ 0.12; real non-periodic
  nights ≈ 0.000–0.001). Short cycles (< 40 s) lean toward TECSA / high loop gain;
  long cycles toward classical Cheyne–Stokes (cardiac). Neither is a diagnosis —
  that requires PSG with effort channels; this flags the waveform for manual review.
- **Late-night event load** — the back two-thirds of the record naturally runs about
  **twice** the rate of the first two hours (measured: 4.0 → 8.3 events/h across 90
  nights). Consequence: **a short night's REI is not comparable to a full night's** —
  it only sampled the easy part; its lower value is sampling bias, not improvement.

## Ventilation and oxygenation

- **SpO2 (SAD)** — nightly minimum and, when coverage passes the gate, T90 and
  minutes < 88 %. T90 > 20 % associates with moderate-severe OSA burden. **REI low
  but SpO2 low → think overlap syndrome (OSA + COPD) / obesity-hypoventilation.**
- **FlowLim** — the upstream precursor of obstruction. Stable REI with rising FL95
  is an early warning of increasing collapse tendency.
- **Minute ventilation / tidal volume** chronically low → consider
  hypoventilation/neuromuscular comorbidity; device accuracy is limited, cue only.

## Adherence and data quality

- **Usage** — < 4 h/night is insufficient exposure. The clinical adherence bar:
  ≥ 4 h on ≥ 70 % of 30 consecutive nights (CMS/AASM). **Diagnose "can't keep it on"
  via session structure**: one continuous short session = tolerance problem
  (comfort, habituation); fragmented sessions with terminal event clusters = arousal
  then unconscious removal (fix the events, not the willpower). The
  `resmed-sd-monitor-maskoff` audit does exactly this classification.
- **Quality gates** — nights < 2 h, missing EVE/Leak, or Leak95 > 24 L/min are
  excluded from trends and listed with reasons. Large leaks can *fool* the machine
  (leak flow read as breathing → false hypopneas / missed events), so a leaky night's
  numbers are not conservative estimates — they are noise.
- **REI from a flagged night appears in tables with `*` but never enters statistics.**

## When the numbers look fine but you don't

AHI at target plus persistent daytime sleepiness is not a paradox to solve with more
pressure. Check: actual wear time, insomnia, PLMS (needs PSG), depression, narcolepsy
spectrum, and whether pressure is genuinely adequate. The machine measures the
treatment; the symptom is the outcome.

## Boundaries

- Parameter changes are medical decisions. This tool will tell you what the data
  shows and how confident to be; it will not emit a prescription value.
- Follow-up cadence: 1–2 weeks after a change, then 3–6 months in the first stable
  year, annually after. Acute swings wait for the 5-night rolling median.
- Persistent CAI with EPR/pressure reductions exhausted → specialist evaluation for
  complex apnea (bilevel/ASV). Don't fight TECSA on an APAP.
