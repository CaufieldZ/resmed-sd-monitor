# resmed-sd-monitor

PAP therapy monitoring and clinical decision support, from the SD card of your ResMed
AirSense machine — as a CLI. Point it at a copy of your SD card and it produces an
archived monitoring report: quality-gated efficacy trends segmented by your
prescription-change log, breath-by-breath flow-waveform analysis, and an explicit
audit of whether pressure still has headroom.

**Not a medical device.** It reads data your machine already records and turns it into
screening cues and review prompts. It cannot diagnose sleep apnea, decide pressure
settings, or replace your sleep physician. See the full disclaimer at the bottom.

## Why this exists

OSCAR and SleepHQ are great *viewers*. This is a different thing — an *analyst*:

- **Segmented efficacy with statistics.** Keep a `tuning_log.json` of prescription
  changes; every report compares segments with Mann–Whitney + Hodges–Lehmann estimates,
  and refuses to dress noise as improvement (p ≥ 0.05 reads "no clear difference,
  equivalence not proven").
- **Breath-by-breath waveform layer.** Rebuilds breathing from the 25 Hz BRP flow
  signal: inspiratory flattening index per breath, event clustering, periodic-breathing
  detection (sine-fit calibrated against synthetic signals, robust to breath-to-breath
  jitter that breaks autocorrelation).
- **The pressure-headroom question, done honestly.** Under APAP the machine *raises*
  pressure after events, so "high pressure ↔ many events" is feedback echo, not
  causality. The tool runs an explicit feedback check (post-event pressure delta vs
  random-time controls), then judges remaining headroom from the **pressure–flatness
  curve** (background flow limitation across pressure bins), with Ramp drive-by bins
  excluded so you don't measure "ramp vs therapy" and call it a dose effect.
- **Quality gates, stated, not hidden.** Nights under 2 h, missing channels or
  Leak95 > 24 L/min are excluded and the reasons are printed. SAD oximetry below 70 %
  coverage yields "undetermined", never a fabricated T90.
- **Everything is annotated for the clinician.** Report sections carry the caveats a
  sleep specialist needs (REI denominator is therapy time, no EEG/position/effort,
  device events are algorithmic estimates).

## 30-second demo

```bash
pip install -e .[charts]
python examples/generate_demo_data.py          # synthetic 10-night dataset
python -m resmed_sd_monitor --data-dir examples/demo/data --report
```

A full sample report generated this way lives in
[examples/demo/sample_report/](examples/demo/sample_report/sample_report.md).

## Using your own data

Copy the SD card contents somewhere (do **not** work on the card directly):

```
<data-dir>/
  DATALOG/<YYYYMMDD>/<timestamp>_{BRP,PLD,SAD,EVE,CSL}.edf
  STR.edf            (optional — enables --settings)
  tuning_log.json    (optional — segments the report; see docs/tuning-log.md)
```

Then:

```bash
python -m resmed_sd_monitor --data-dir /path/to/sdcard --report
```

| Command | What you get |
| --- | --- |
| `--report` | The full monitoring report: quality gates, segmented trends + statistics, clinical review cues, waveform layer, charts (md + json snapshot + png archived to `<data-dir>/reports/`) |
| `--wave [N]` | Waveform deep-dive over the last N nights: flattening index, clusters, periodic breathing, pressure–flatness curve, feedback check |
| `--pressure` | Descriptive event–pressure association (the older, coarser view) |
| `<YYYYMMDD>` | One night's detail: event list with the pressure at each event's onset |
| `--settings` | Current prescription parsed from `STR.edf` |
| (none) | Summary table of all nights |
| `--csv` | Same table as CSV (21 columns) for spreadsheets |
| `resmed-sd-monitor-maskoff` | Mask-off timing audit: was early mask removal event-driven or not |

Options: `--data-dir` (or `$RSDM_DATA_DIR` / legacy `$CPAP_DATA_DIR`), `--lang en|zh|ja`.

## Languages

English (base), 简体中文 and 日本語 ship with the repo — output, reports and chart
labels all switch via `--lang` / locale detection. Japanese is machine-assisted and
awaits native review; additional locales (de, fr, pt-BR, …) are one small file away:
see [docs/translating.md](docs/translating.md).

## Reading the output

The interpretation discipline is the point of this tool — start with
[docs/interpretation-guide.md](docs/interpretation-guide.md). The short version:

- Device REI is events per *therapy hour*, not PSG-AHI. Don't map it onto severity grades.
- A single night means nothing; read 5-night rolling medians and segment statistics.
- CAI rising after a pressure increase is a TECSA flag, not a tuning detail.
- Whether more pressure would help is judged from the pressure–flatness curve and
  ceiling dwell — never from "events happened at high pressure".
- Event-rate ratios across pressure bands are always contaminated by APAP's reactive
  pressurization; the report says so every time it shows one.

Data format reference: [docs/data-format.md](docs/data-format.md).

## Installation

Python ≥ 3.10. Core dependencies: `numpy`, `scipy`, `edfio`. Charts (matplotlib) are
optional — without them reports still generate, minus images.

```bash
pip install -e .            # core
pip install -e .[charts]    # + matplotlib
pip install -e .[dev]       # + pytest, for running the test suite (105 tests)
```

Works offline, fully local. Nothing leaves your machine.

## Contributing

Bug reports and PRs welcome, especially: additional ResMed device generations tested,
locale tables, and stricter parsers for edge-case EDF quirks. Medical-safety wording
changes are taken seriously — the non-diagnostic boundaries in the output are
deliberate and won't be loosened.

## Disclaimer

This software is provided for informational and educational purposes only. It is **not
a medical device** and has not been reviewed by any regulatory authority. Nothing it
outputs is a diagnosis, a treatment recommendation, or a prescription. Device-derived
metrics (event indices, pressures, oximetry) are algorithmic estimates with known
blind spots (leak, wakefulness, absent sleep staging). Always involve a qualified
sleep physician in therapy decisions. In an emergency, seek immediate medical care.

ResMed, AirSense and AutoSet are trademarks of ResMed Ltd. This is an independent,
unaffiliated hobby project that only reads data those machines already write to SD
cards.

## License

[MIT](LICENSE)
