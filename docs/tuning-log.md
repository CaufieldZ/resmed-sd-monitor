# The tuning log

`tuning_log.json` is a small file **you maintain by hand**: every time your
prescription changes, append one entry. It is what turns a pile of nights into
a segmented before/after study.

## Schema

```json
{
  "device": "ResMed AirSense 10 AutoSet",
  "mask": "nasal",
  "log": [
    {
      "since": "20240301",
      "label": "initial 9-14 EPR1",
      "min_press": 9,
      "max_press": 14,
      "epr": 1,
      "note": "optional free text"
    },
    {
      "since": "20240305",
      "label": "floor raised",
      "min_press": 10,
      "max_press": 15,
      "epr": 1
    }
  ]
}
```

- `since` — **YYYYMMDD, the first night the new settings were in effect** (must
  match the DATALOG directory name convention). Required.
- `label` — segment name shown in tables and chart color bands. Defaults to the date.
- `min_press` / `max_press` / `epr` — displayed and used for the ceiling-binding
  analysis (`max_press` of the *last* entry is the assumed current ceiling).
- `note`, `device`, `mask` — free text / report header, optional.

## Semantics

- Nights are assigned to segments as half-open date ranges: `[since_i, since_{i+1})`.
- The **current segment** is the last one; if it has no analyzable nights the
  report says "insufficient data" instead of quietly falling back to older settings.
- Segment comparisons (Mann–Whitney + Hodges–Lehmann) run between *consecutive
  segments that both have analyzable nights*.
- Without a tuning log everything is one segment labelled "All".

## Adding an entry after a change

1. Note the date the change takes effect (the night you first sleep on it).
2. Append the entry to the `log` array, keeping dates ascending.
3. Rerun `--report` — the new segment appears with its own stats and the
   comparison against the previous segment.

Keep it boring: one line per change, no editorializing in `label` (it goes on
charts).
