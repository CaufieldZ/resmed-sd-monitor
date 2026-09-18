"""Lightweight string-table i18n for resmed-sd-monitor.

Locale tables live next to this file as plain Python dicts (``en.py`` base,
``zh.py`` / ``ja.py`` translations). Selection order:

1. explicit ``set_lang(code)`` (fed by the CLI ``--lang`` flag),
2. ``RSDM_LANG`` environment variable,
3. ``LC_ALL`` / ``LANG`` (language prefix only, e.g. ``ja_JP.UTF-8`` → ``ja``),
4. ``en``.

Unknown codes silently fall back to ``en``; a key missing from a translation
falls back to the English string. All placeholders use :meth:`str.format`
named fields (``{n_nights}``), so translations may reorder freely.

``t()`` never raises on a missing key: it returns the key wrapped in
``<...>`` and records it in :data:`MISSING` so tests/CI can assert table
completeness.
"""

from __future__ import annotations

import os
import re

from . import en as _en

# Populated lazily in set_lang() so that `import resmed_sd_monitor.monitor`
# does not pay for every table.
_EXTRA = ("zh", "ja")

_active_table: dict = dict(_en.STRINGS)
_active_lang = "en"

# Keys requested but absent from the active table (test/CI hook).
MISSING: set[str] = set()

_PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def available() -> list[str]:
    """Locale codes with a shipped table (always includes 'en')."""
    return sorted(["en", *_EXTRA])


def current() -> str:
    return _active_lang


def detect_lang(explicit: str | None = None) -> str:
    """Resolve the locale from the explicit flag / env / POSIX locale."""
    for cand in (explicit, os.environ.get("RSDM_LANG")):
        if cand:
            code = cand.strip().lower().replace("-", "_").split(".")[0]
            stem = code.split("_", 1)[0]
            if stem in _EXTRA or stem == "en":
                return stem
    for var in ("LC_ALL", "LANG"):
        val = os.environ.get(var)
        if val:
            code = val.strip().lower().replace("-", "_").split(".")[0]
            stem = code.split("_", 1)[0]
            if stem in _EXTRA:
                return stem
    return "en"


def set_lang(lang: str | None = None) -> str:
    """Switch the active locale; returns the locale actually set."""
    global _active_table, _active_lang
    code = detect_lang(lang)
    if code == "en":
        _active_table = dict(_en.STRINGS)
    else:
        from importlib import import_module

        table = import_module(f".{code}", __package__).STRINGS
        # Overlay on en so a partially translated table still renders.
        merged = dict(_en.STRINGS)
        merged.update(table)
        _active_table = merged
    _active_lang = code
    return code


def placeholders(s: str) -> set[str]:
    """Named ``{field}`` placeholders referenced by a table string."""
    return set(_PLACEHOLDER.findall(s))


def t(key: str, **kw) -> str:
    """Look up ``key`` in the active table and format with named fields."""
    s = _active_table.get(key)
    if s is None:
        s = _en.STRINGS.get(key)
        if s is None:
            MISSING.add(key)
            return f"<{key}>"
    if kw:
        return s.format(**kw)
    return s
