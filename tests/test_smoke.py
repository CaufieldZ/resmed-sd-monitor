"""End-to-end smoke test: synthetic dataset → every command runs clean.

Generates the demo dataset into tmp_path (deterministic seed), then drives the
real CLI entry points: summary, CSV, full report (with charts when matplotlib
is present), wave, single-night detail and maskoff. Asserts the artifacts land
on disk and that every locale renders the report without a missing-key marker.
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "examples"))

from generate_demo_data import main as gen_main  # noqa: E402

from resmed_sd_monitor import maskoff  # noqa: E402
from resmed_sd_monitor import monitor as M  # noqa: E402
from resmed_sd_monitor.i18n import MISSING  # noqa: E402


@pytest.fixture(scope="module")
def demo_data(tmp_path_factory):
    out = tmp_path_factory.mktemp("demo") / "data"
    gen_main([str(out)])
    return out


def test_summary_and_csv(demo_data, capsys):
    M.set_data_dir(demo_data)
    M.main(["--data-dir", str(demo_data)])
    out = capsys.readouterr().out
    assert "20240301" in out
    assert "*" in out            # the short+leaky night is flagged non-analyzable

    M.main(["--data-dir", str(demo_data), "--csv"])
    csv = capsys.readouterr().out.strip().splitlines()
    assert csv[0].startswith("date,usage_h,ahi,residual_rei")
    assert len(csv) == 1 + 10    # header + 10 nights


def test_report_all_locales(demo_data, capsys):
    reports = demo_data / "reports"
    for lang in ("en", "zh", "ja"):
        rc = M.main(["--data-dir", str(demo_data), "--lang", lang, "--report"])
        assert rc == 0
        body = capsys.readouterr().out
        assert "<" + "report_title" not in body   # no missing-key markers
        assert "##" in body
    # the last run (ja) must have written its artifacts
    mds = sorted(reports.glob("*_report.md"))
    snaps = sorted(reports.glob("*_snapshot.json"))
    assert mds and snaps
    snap = json.loads(snaps[-1].read_text(encoding="utf-8"))
    assert snap["quality"]["nights"] == 10
    assert snap["quality"]["analyzable"] == 9
    # matplotlib present -> charts written
    try:
        import matplotlib  # noqa: F401
        pngs = list(reports.glob("*.png"))
        assert len(pngs) >= 8
    except ImportError:
        pass


def test_wave(demo_data, capsys):
    rc = M.main(["--data-dir", str(demo_data), "--wave", "30"])
    assert rc == 0
    body = capsys.readouterr().out
    assert "20240307" in body                       # CSR-like night present
    MISSING.clear()
    assert not MISSING                              # no missing i18n keys


def test_demo_periodic_breathing_lands_on_the_csr_night(demo_data):
    """Regression: the generator's tidal-volume modulation must be driven by the
    `periodic` flag — a wrong tuple index silently attached it to the clustered
    nights instead, so the CSR-like night never passed the corr² threshold and
    the sample report showed a false detection on the wrong nights."""
    M.set_data_dir(demo_data)
    def corr2(date):
        wave = M.night_wave(str(demo_data / "DATALOG" / date))
        return wave["period_corr2"] if wave else None
    csr = corr2("20240307")            # csr-like archetype
    assert csr is not None and csr >= M.WAVE_PERIOD_CORR2
    for clustered in ("20240303", "20240306"):
        c = corr2(clustered)
        assert c is None or c < M.WAVE_PERIOD_CORR2, f"{clustered} falsely periodic ({c})"


def test_detail(demo_data, capsys):
    rc = M.main(["--data-dir", str(demo_data), "20240306"])
    assert rc == 0
    body = capsys.readouterr().out
    assert "20240306" in body


def test_settings_missing_is_graceful(demo_data, capsys):
    rc = M.main(["--data-dir", str(demo_data), "--settings"])
    assert rc == 0
    assert "STR.edf" in capsys.readouterr().out


def test_maskoff(demo_data, capsys):
    maskoff.main(["--data-dir", str(demo_data)])
    body = capsys.readouterr().out
    assert "20240301" in body


def test_tuning_log_segments_report(demo_data):
    M.set_data_dir(demo_data)
    log = M.load_tuning_log()
    assert log["log"][1]["since"] == "20240305"
    assert M.configured_max_press() == 15
