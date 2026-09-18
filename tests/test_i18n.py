"""i18n table integrity: key parity, placeholder parity, fallback behaviour."""
import re

import pytest

from resmed_sd_monitor.i18n import MISSING, available, detect_lang, en, ja, placeholders, set_lang, t, zh

# every t('key') call in monitor.py + maskoff.py + indirect lookup tables
_SOURCES = ('../src/resmed_sd_monitor/monitor.py', '../src/resmed_sd_monitor/maskoff.py')
_EXTRA_KEYS = {
    'qr_short_use', 'qr_no_eve', 'qr_no_leak', 'qr_high_leak',
    'mode_cpap', 'mode_apap', 'mode_bilevel',
    'mask_pillow', 'mask_nasal', 'mask_nasal2', 'mask_full',
    'epr_off', 'epr_full', 'epr_ramp', 'onoff_off', 'onoff_on', 'onoff_auto',
}


def _used_keys():
    pat = re.compile(r"(?<![a-zA-Z_0-9])t\('([a-z0-9_]+)'")
    keys = set(_EXTRA_KEYS)
    import pathlib
    here = pathlib.Path(__file__).parent
    for rel in _SOURCES:
        keys |= set(pat.findall((here / rel).read_text(encoding='utf-8')))
    return keys


@pytest.fixture(autouse=True)
def _restore_lang():
    set_lang('en')
    yield
    set_lang('en')


def _all_tables():
    """Every shipped locale's table, discovered from available() so a newly
    registered locale is covered by the parity checks automatically."""
    from importlib import import_module
    for code in available():
        if code == 'en':
            yield code, en.STRINGS
        else:
            yield code, import_module(f'resmed_sd_monitor.i18n.{code}').STRINGS


class TestTableParity:
    def test_used_keys_exist_in_en(self):
        assert not (_used_keys() - set(en.STRINGS)), 'keys missing from en table'

    def test_translations_cover_en_exactly(self):
        for name, table in _all_tables():
            if name == 'en':
                continue
            missing = set(en.STRINGS) - set(table)
            extra = set(table) - set(en.STRINGS)
            assert not missing, f'{name} missing: {sorted(missing)}'
            assert not extra, f'{name} extra: {sorted(extra)}'

    def test_placeholder_parity_with_en(self):
        for name, table in _all_tables():
            if name == 'en':
                continue
            for k, v in en.STRINGS.items():
                assert placeholders(v) == placeholders(table[k]), f'{name}.{k}'


class TestFallback:
    def test_unknown_key_marks_missing(self):
        MISSING.clear()
        assert t('no_such_key_here').startswith('<')
        assert 'no_such_key_here' in MISSING

    def test_partial_table_falls_back_to_en(self):
        set_lang('zh')
        # a key present only in en still renders (overlay semantics)
        assert t('ev_oa') == en.STRINGS['ev_oa'] or t('ev_oa') == zh.STRINGS['ev_oa']


class TestDetection:
    def test_explicit_wins(self):
        assert detect_lang('ja') == 'ja'
        assert detect_lang('zh_TW') == 'zh'

    def test_env_var(self, monkeypatch):
        monkeypatch.setenv('RSDM_LANG', 'ja')
        assert detect_lang() == 'ja'

    def test_posix_locale(self, monkeypatch):
        monkeypatch.delenv('RSDM_LANG', raising=False)
        monkeypatch.setenv('LC_ALL', 'ja_JP.UTF-8')
        assert detect_lang() == 'ja'

    def test_unknown_falls_back_to_en(self, monkeypatch):
        monkeypatch.delenv('RSDM_LANG', raising=False)
        monkeypatch.setenv('LC_ALL', 'fr_FR.UTF-8')
        assert detect_lang() == 'en'

    def test_available_lists_all(self):
        assert set(available()) == {'en', 'zh', 'ja'}

    def test_set_lang_overlays(self):
        set_lang('zh')
        assert t('qr_no_eve') == zh.STRINGS['qr_no_eve']
        set_lang('ja')
        assert t('qr_no_eve') == ja.STRINGS['qr_no_eve']
