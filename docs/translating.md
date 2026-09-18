# Translating

The UI, reports and chart labels are fully localized. English is the base table;
`zh` (Simplified Chinese) and `ja` (Japanese) ship with the repo — the Japanese
table is machine-assisted and would especially benefit from native review.

The README is localized too (`README.md` / `README.zh.md` / `README.ja.md`), with a
language switcher line under the title of each. When you add a locale, add a README
variant and register it in the switcher lines of all existing READMEs and in this
file's header.

## Adding a locale

1. Copy `src/resmed_sd_monitor/i18n/en.py` to `<code>.py` (ISO 639-1: `de`, `fr`,
   `pt`…; regional variants like `pt-BR` resolve to their stem, so use the stem
   unless two variants genuinely differ).
2. Translate the values. Rules:
   - **Keep placeholders intact**: `{n}`, `{med}`, `{pct}` are `str.format` named
     fields and may be reordered freely within a string, but never renamed, added
     or dropped — CI checks placeholder parity with `en`.
   - Keep markdown (`**bold**`, `> quote`, `\n`) and the warning markers (`⚠`)
     where they carry meaning.
   - Medical-safety sentences (disclaimers, "not a diagnosis", emergency
     guidance) deserve extra care — when in doubt, prefer stricter wording.
   - Table headers are pre-spaced literals; character-count alignment is fine,
     don't fight CJK double-width.
3. Register the code in `_EXTRA` in `src/resmed_sd_monitor/i18n/__init__.py`.
4. `pytest tests/test_i18n.py` — key parity and placeholder parity must pass.
5. Render a demo report in your locale to eyeball it:
   `python -m resmed_sd_monitor --data-dir examples/demo/data --lang <code> --report`
   (generate demo data first). Chart labels need a CJK-capable font for
   non-Latin scripts; matplotlib falls back through a stack that covers
   PingFang/Hiragino/Yu Gothic/Noto CJK on macOS/Windows/Linux.

Locale detection order: `--lang` flag → `$RSDM_LANG` → `LC_ALL`/`LANG` (language
prefix) → English. Missing keys fall back to English at runtime; a table that is
complete at commit time is enforced by tests, partial fallback is only a safety
net.

## Reviewing an existing locale

Read-throughs comparing against `en.py` count as contributions. The strings most
worth a native speaker's eyes: every key starting with `assess_`, `report_s4b_`,
`wave_feedback`, and the disclaimer keys.
