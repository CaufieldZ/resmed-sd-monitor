<div align="center">

<img src="docs/assets/banner.png" alt="ResMed SD-card data analysis" width="880">

# resmed-sd-monitor

**Turn your ResMed SD card into an auditable therapy-monitoring report.**

Quality-gated efficacy trends · breath-by-breath waveform analysis · honest pressure-headroom curves

**English** · [简体中文](README.zh.md) · [日本語](README.ja.md)

[![CI](https://github.com/CaufieldZ/resmed-sd-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/CaufieldZ/resmed-sd-monitor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Not a medical device](https://img.shields.io/badge/%E2%9A%A0-not%20a%20medical%20device-red.svg)](#disclaimer)

[Quick start](#quick-start) · [What you get](#what-you-get) · [Commands](#commands) · [Reading the output](#reading-the-output) · [Disclaimer](#disclaimer)

</div>

---

`resmed-sd-monitor` reads the EDF files your AirSense/AirCurve machine already writes to
its SD card and produces a monitoring report your sleep clinician can actually review:
efficacy trends split by your own prescription-change log, per-breath flow analysis, and
a defensible answer to *"would more pressure help?"*

It is the analyst to OSCAR's viewer. Everything is local, offline, and reproducible.

> **Not a medical device.** It turns machine-recorded estimates into screening cues and
> review prompts — it cannot diagnose sleep apnea, decide your pressure settings, or
> replace a sleep physician. See the [full disclaimer](#disclaimer).

## How it works

<img src="docs/assets/pipeline.svg" alt="Pipeline: SD card → parse → quality gates → nightly summaries and waveform layer → pressure-headroom verdict → archived report" width="880">

## What you get

### Efficacy, segmented by your own prescription history

Keep a small `tuning_log.json` of every settings change. Each report splits the nights
into segments, compares them with Mann–Whitney + Hodges–Lehmann statistics, and refuses
to dress noise up as improvement — `p ≥ 0.05` reads *"no clear difference detected;
equivalence not proven"*, never *"no difference"*.

<p align="center"><img src="examples/demo/sample_report/residual_rei.png" width="820" alt="Nightly residual event index with 5-night rolling median, segment bands and target lines"></p>

### The pressure-headroom answer, with the confounders handled

The hard question in APAP tuning is *"is there room for more pressure?"* Two traps make
naive answers wrong, and both are handled explicitly:

- **APAP raises pressure *in response to* events.** So "many events happened at high
  pressure" is the echo of a feedback loop, not evidence that pressure fails. The tool
  runs a feedback check (post-event pressure change vs random-time controls) before any
  pressure metric, and prints the result.
- **Ramp drive-by bins.** The climb from start pressure to therapy pressure leaves
  hundreds of low-pressure breaths; comparing those against fully-loaded high bins
  measures "ramp vs therapy", not a dose effect. Bins under 3 % exposure are dropped.

What's left is the clean signal — background flow limitation (inspiratory flattening)
across pressure bins:

<p align="center"><img src="examples/demo/sample_report/pressure_fi.png" width="760" alt="Pressure vs inspiratory flatness with event histogram overlay"></p>

### Breath-by-breath waveform layer

Straight from the 25 Hz flow channel: inspiratory flattening index per breath, event
clustering (the positional/REM cue), periodic-breathing detection with a calibrated
sine-fit, and the timeline view that shows *where* events happen:

<p align="center"><img src="examples/demo/sample_report/cluster_timeline.png" width="860" alt="Event time map with in-cluster events in red"></p>

### Quality gates that are stated, not hidden

Nights under 2 h, missing channels or Leak95 > 24 L/min are excluded **with printed
reasons**. SAD oximetry below 70 % coverage yields "undetermined" rather than a
fabricated T90. Every report section carries the caveats a clinician needs (REI
denominator is therapy time, no EEG/position/effort channels, device events are
algorithmic estimates).

<details>
<summary><b>Sample report excerpt</b> (click to expand)</summary>

```text
## 4b. Flow waveform layer (per-breath, last 5 nights)
- Feedback check: within 120 s after 36 events, pressure changed by median
  +0.67 cmH2O (56% rose above 0.5, 0% fell below -0.5); across 150 random-time
  controls, median +0.03, 3% rose. The device does pressurize reactively to
  events, so any "high pressure <-> many events" co-occurrence is that
  feedback's echo — not "pressure is ineffective".
- Periodic-breathing fit: 1/5 nights reach the threshold (corr²>=0.1); dominant
  period 46 s. Periodic ventilatory instability needs manual waveform review —
  the device has no EEG/effort channels; Cheyne-Stokes or TECSA cannot be
  declared from this.
- Pressure–flatness curve: therapy pressure range 11.0–13.5 cmH2O (5 bins,
  Ramp drive-by low bins excluded): FI median at 11.0 bin 0.087 → at 13.0 bin
  0.071; weighted slope -0.0087/cmH2O.
```

Full sample: [examples/demo/sample_report/](examples/demo/sample_report/sample_report.md)

</details>

## Quick start

No SD card needed to try it — a deterministic synthetic 10-night dataset is generated
on the spot:

```bash
git clone https://github.com/CaufieldZ/resmed-sd-monitor
cd resmed-sd-monitor
pip install -e .[charts]

python examples/generate_demo_data.py                         # synthetic 10 nights
python -m resmed_sd_monitor --data-dir examples/demo/data --report
```

Then point it at your own card copy:

```bash
python -m resmed_sd_monitor --data-dir /path/to/sdcard --report
```

## Commands

| Command | What you get |
| --- | --- |
| `--report` | Full monitoring report: quality gates, segmented trends + statistics, clinical review cues, waveform layer, charts (md + json snapshot + png archived to `<data-dir>/reports/`) |
| `--wave [N]` | Waveform deep-dive over the last N nights: flattening index, clusters, periodic breathing, pressure–flatness curve, feedback check |
| `--pressure` | Descriptive event–pressure association (the older, coarser view) |
| `<YYYYMMDD>` | One night's detail: event list with the pressure at each event's onset |
| `--settings` | Current prescription parsed from `STR.edf` |
| *(none)* | Summary table of all nights |
| `--csv` | Same table as CSV (21 columns) for spreadsheets |
| `resmed-sd-monitor-maskoff` | Mask-off timing audit: was early mask removal event-driven or not |

Options: `--data-dir` (or `$RSDM_DATA_DIR` / legacy `$CPAP_DATA_DIR`), `--lang en|zh|ja`.

## Reading the output

The interpretation discipline *is* the product. Start with
[docs/interpretation-guide.md](docs/interpretation-guide.md); the short version:

| Question | Where to look | The trap |
| --- | --- | --- |
| Is therapy working? | 5-night rolling median, segment statistics | Single nights swing 1–10 events/h — never read one night |
| Would more pressure help? | Pressure–flatness curve; ceiling dwell time | "Events at high pressure" is APAP's own feedback echoing back |
| Positional / REM-related? | Event clustering; time-of-night distribution | The device records no position and no sleep stage — cues only |
| Central events emerging? | CAI trend after pressure/EPR changes | Rising CAI on more pressure = TECSA flag, not a tuning detail |
| Mask coming off early? | `resmed-sd-monitor-maskoff` | One short session = tolerance; fragmented = arousal-driven |

Data format reference and quirks (STR.edf hand-parsing, EDF+ annotations, multi-segment
nights): [docs/data-format.md](docs/data-format.md).
The tuning log schema: [docs/tuning-log.md](docs/tuning-log.md).

## Languages

English (base), 简体中文 and 日本語 ship with the repo — output, reports and chart labels
all switch via `--lang` or locale detection. The Japanese table is machine-assisted and
awaits native review; additional locales (de, fr, pt-BR, …) are one small file away:
see [docs/translating.md](docs/translating.md).

## Installation

Python ≥ 3.10. Core dependencies: `numpy`, `scipy`, `edfio`. Charts (matplotlib) are
optional — without them reports still generate, minus images.

```bash
pip install -e .            # core
pip install -e .[charts]    # + matplotlib
pip install -e .[dev]       # + pytest, for the test suite (106 tests)
```

Works offline, fully local. Nothing leaves your machine.

## Project layout

```text
src/resmed_sd_monitor/
  monitor.py      the analysis engine + CLI (report / wave / pressure / detail / settings)
  maskoff.py      mask-off timing audit
  i18n/           en / zh / ja string tables (+ parity tests)
examples/
  generate_demo_data.py   deterministic synthetic dataset generator
  demo/sample_report/     committed sample output (regenerate with CI check)
docs/             interpretation guide · data format · tuning log · translating
```

## Contributing

Bug reports and PRs welcome — especially: additional ResMed device generations tested,
locale tables, and stricter parsers for edge-case EDF quirks. Medical-safety wording
changes are taken seriously: the non-diagnostic boundaries in the output are deliberate
and won't be loosened.

```bash
pytest -q && ruff check src tests examples
```

## Disclaimer

This software is provided for informational and educational purposes only. It is **not
a medical device** and has not been reviewed by any regulatory authority. Nothing it
outputs is a diagnosis, a treatment recommendation, or a prescription. Device-derived
metrics (event indices, pressures, oximetry) are algorithmic estimates with known
blind spots (leak, wakefulness, absent sleep staging). Always involve a qualified sleep
physician in therapy decisions. In an emergency, seek immediate medical care.

ResMed, AirSense and AutoSet are trademarks of ResMed Ltd. This is an independent,
unaffiliated hobby project that only reads data those machines already write to SD
cards.

## License

[MIT](LICENSE)
