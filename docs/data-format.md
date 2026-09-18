# Data format reference

What the tool reads, and the quirks you will meet. All files live in the data
directory you point `--data-dir` at (or `$RSDM_DATA_DIR`).

```
<data-dir>/
  DATALOG/
    <YYYYMMDD>/                          one directory per treatment date
      <HHMMSS>_BRP.edf                   flow + pressure, 25 Hz
      <HHMMSS>_PLD.edf                   summary channels, 0.5 Hz
      <HHMMSS>_SAD.edf                   pulse rate + SpO2, 1 Hz
      <HHMMSS>_EVE.edf                   respiratory event annotations (EDF+)
      <HHMMSS>_CSL.edf                   Cheyne-Stokes annotations (EDF+)
  STR.edf                                settings summary (non-standard EDF)
  tuning_log.json                        your prescription-change log
  reports/                               generated reports land here
```

## Channel map

| File | Channels | Rate |
| --- | --- | --- |
| BRP | `Flow`, `Press` | 25 Hz |
| PLD | `Press`, `Leak`, `RespRate`, `TidVol`, `MinVent`, `Snore`, `FlowLim` | 0.5 Hz |
| SAD | `SpO2`, `PR` | 1 Hz |
| EVE | EDF+ annotations: `Obstructive Apnea`, `Central Apnea`, `Hypopnea`, bare `Apnea` | — |

Channel matching is by label prefix (before the `.`), case-insensitive.

## Event labels

`classify_event_label` normalizes annotations to `oa` / `ca` / `hyp` / `ua`:

- `Central Apnea` → `ca`; `Obstructive Apnea` → `oa`; anything containing
  `hypopnea` → `hyp`.
- A bare `Apnea` (no qualifier) stays **unclassified** (`ua`) and is never silently
  counted as obstructive, including in the event–pressure alignment.
- Anything else (e.g. `RERA`, `Snore`) is ignored for event statistics.

## Quirks

- **STR.edf is not readable by edfio/pyedflib.** It is a non-standard EDF variant;
  `--settings` parses it by hand (fixed-offset header fields + per-day records).
- **The last STR day is usually an empty shell** (`Mode == -1`). The parser walks
  backwards to the last valid day.
- **EVE/CSL are EDF+ annotation files**; the tool reads the TAL stream directly
  (onset `\x15` duration `\x14` label `\x14`) rather than going through a library,
  partly for tolerance of ResMed's header quirks, partly because annotation-only
  EDF+D files trip some readers.
- **One night can have multiple files of each type** (therapy resumed after a
  mask-off). Therapy intervals are computed as the union of BRP segments: gaps
  are not counted as exposure, overlaps are not double-counted. Events
  outside the union are dropped; the dedup key is (time×2, duration, label).
- **Corrupt EDF headers** (`num data records = -1`): duration is estimated from the
  raw header bytes; unparseable files are skipped per-file, never fatal.
- **SpO2 sanity**: SAD values ≤ 50 are treated as "no signal" (ResMed writes -1
  when no oximeter is attached).
- **File read caching**: EDF objects are cached per night (a PLD file holds 7
  channels; without the cache one file gets opened 7 times). Caches are cleared
  when the next night starts.

## Apple Health

Not supported. SpO2 comes from the device's SAD channel only. The original
analysis pipeline this project was extracted from also merged Apple Watch nightly
SpO2/HR/RR. That integration was dropped here because on-demand spot sampling
cannot support T90, and a T90 built from spot samples is precisely the misreading
the quality gates exist to prevent.

## What is deliberately not parsed

- `CSL` (Cheyne-Stokes annotations): the waveform layer's periodicity fit covers
  the same ground with a calibrated threshold, and the tool refuses to declare
  Cheyne-Stokes from device data anyway.
- Detailed settings history beyond the fields `--settings` prints.
