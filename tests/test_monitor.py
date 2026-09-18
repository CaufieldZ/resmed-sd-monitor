"""Pure-function unit tests: no real EDF files needed, intervals/events are
constructed in memory (ported from the original cpap/tests suite)."""
import math

import numpy as np
import pytest

from resmed_sd_monitor import monitor as R
from resmed_sd_monitor.i18n import set_lang, t

set_lang('en')


# ── event label classification ──────────────────────────────────────────────

class TestClassifyEventLabel:
    def test_obstructive(self):
        assert R.classify_event_label("Obstructive Apnea") == 'oa'
        assert R.classify_event_label("  obstructive apnea  ") == 'oa'

    def test_central(self):
        assert R.classify_event_label("Central Apnea") == 'ca'

    def test_hypopnea(self):
        assert R.classify_event_label("Hypopnea") == 'hyp'

    def test_unclassified_apnea(self):
        # bare "Apnea" carries no qualifier: must be ua, never default oa
        assert R.classify_event_label("Apnea") == 'ua'

    def test_unknown_label_returns_none(self):
        assert R.classify_event_label("RERA") is None
        assert R.classify_event_label("Snore") is None
        assert R.classify_event_label("") is None


# ── interval merging ────────────────────────────────────────────────────────

class TestMergeIntervals:
    def test_empty(self):
        merged, gap, overlap = R._merge_intervals([])
        assert merged == [] and gap == 0.0 and overlap == 0.0

    def test_single(self):
        merged, gap, overlap = R._merge_intervals([(0, 100)])
        assert merged == [(0.0, 100.0)] and gap == 0.0 and overlap == 0.0

    def test_disjoint(self):
        merged, gap, overlap = R._merge_intervals([(0, 50), (100, 200)])
        assert merged == [(0.0, 50.0), (100.0, 200.0)]
        assert gap == pytest.approx(50.0)
        assert overlap == pytest.approx(0.0)

    def test_overlap(self):
        merged, gap, overlap = R._merge_intervals([(0, 100), (80, 150)])
        assert merged == [(0.0, 150.0)]
        assert overlap == pytest.approx(20.0)
        assert gap == pytest.approx(0.0)

    def test_adjacent(self):
        merged, _gap, _overlap = R._merge_intervals([(0, 100), (100, 200)])
        assert merged == [(0.0, 200.0)]

    def test_invalid_intervals_skipped(self):
        # intervals with b <= a don't count
        merged, _gap, _ = R._merge_intervals([(10, 5), (0, 100)])
        assert merged == [(0.0, 100.0)]

    def test_nan_skipped(self):
        merged, _, _ = R._merge_intervals([(float('nan'), 100), (0, 50)])
        assert merged == [(0.0, 50.0)]


class TestIntervalDuration:
    def test_single(self):
        assert R._interval_duration([(0, 3600)]) == pytest.approx(3600.0)

    def test_multiple(self):
        assert R._interval_duration([(0, 100), (200, 350)]) == pytest.approx(250.0)

    def test_empty(self):
        assert R._interval_duration([]) == pytest.approx(0.0)


class TestInIntervals:
    def test_inside(self):
        assert R._in_intervals(50.0, [(0, 100)])

    def test_outside_before(self):
        assert not R._in_intervals(-1.0, [(0, 100)])

    def test_outside_after(self):
        assert not R._in_intervals(100.0, [(0, 100)])   # half-open, right end excluded

    def test_in_gap(self):
        assert not R._in_intervals(75.0, [(0, 50), (100, 200)])

    def test_in_second_interval(self):
        assert R._in_intervals(150.0, [(0, 50), (100, 200)])


class TestFiniteValues:
    def test_removes_nan_inf(self):
        v = R._finite_values([1.0, float('nan'), float('inf'), 2.0])
        np.testing.assert_array_equal(v, [1.0, 2.0])

    def test_low_bound(self):
        v = R._finite_values([1.0, 2.0, 3.0], low=2.0)
        np.testing.assert_array_equal(v, [2.0, 3.0])

    def test_high_bound(self):
        v = R._finite_values([1.0, 2.0, 3.0], high=2.0)
        np.testing.assert_array_equal(v, [1.0, 2.0])

    def test_both_bounds(self):
        v = R._finite_values([0.0, 1.5, 3.0, 5.0], low=1.0, high=4.0)
        np.testing.assert_array_equal(v, [1.5, 3.0])


# ── therapy-interval event filtering ────────────────────────────────────────

class TestEventTreatmentWindowFilter:
    """Mirrors _event_records' filtering logic: events outside intervals stay
    out of the numerator."""

    def _make_record(self, t_, kind):
        return {'time': float(t_), 'duration': 10.0, 'label': kind, 'kind': kind}

    def test_event_inside_counts(self):
        ivs = [(1000.0, 2000.0)]
        records = [self._make_record(1500.0, 'oa')]
        inside = [r for r in records if R._in_intervals(r['time'], ivs)]
        assert len(inside) == 1

    def test_event_outside_excluded(self):
        ivs = [(1000.0, 2000.0)]
        records = [self._make_record(500.0, 'oa')]
        inside = [r for r in records if R._in_intervals(r['time'], ivs)]
        assert len(inside) == 0

    def test_event_in_gap_excluded(self):
        ivs = [(1000.0, 1100.0), (1200.0, 1300.0)]
        records = [self._make_record(1150.0, 'ca')]
        inside = [r for r in records if R._in_intervals(r['time'], ivs)]
        assert len(inside) == 0


# ── pressure alignment tolerance (no gluing across gaps) ────────────────────

class TestPressureAlignmentTolerance:
    """_nearest_within: events inside a gap must not glue to a neighbouring
    segment's pressure."""

    def test_within_tolerance_aligns(self):
        times = np.array([1000.0, 1002.0, 1004.0])
        # nearest is times[2]=1004, distance 0.5s < tolerance 5s
        idx, delta = R._nearest_within(times, 1003.5, 5.0)
        assert idx == 2
        assert abs(delta - 0.5) < 1e-9

    def test_outside_tolerance_no_align(self):
        times = np.array([1000.0, 1002.0])
        # nearest distance 8s > tolerance 5s -> no gluing
        idx, delta = R._nearest_within(times, 1010.0, 5.0)
        assert idx is None and delta is None

    def test_empty_times(self):
        idx, delta = R._nearest_within(np.array([]), 1000.0, 5.0)
        assert idx is None and delta is None

    def test_boundary_exactly_at_tolerance(self):
        # boundary: delta exactly equal to tolerance counts as inside (impl is <=)
        times = np.array([1000.0, 1005.0])
        idx, delta = R._nearest_within(times, 1000.0, 5.0)
        assert idx == 0 and delta == 0.0

    def test_before_first_point(self):
        times = np.array([1000.0, 1002.0])
        idx, delta = R._nearest_within(times, 999.0, 5.0)
        assert idx == 0 and delta == 1.0


# ── empty analyzable set must not crash ─────────────────────────────────────

class TestEmptyAnalyzableSet:
    def test_clinical_assessment_empty(self):
        result = R.clinical_assessment([])
        assert result['level'] == t('assess_level_insufficient')
        assert t('assess_summary_insufficient') == result['summary']
        assert result['findings'] == []

    def test_timing_verdict_empty(self):
        assert R.timing_verdict([]) is None

    def test_pressure_response_insufficient(self):
        # fewer than MIN_PATTERN_EVENTS clearly-obstructive events
        rows = [{'press_95': 12.0, 'oai': 3.0, 'oa_press_med': None,
                 'press_med': 11.0, 'n_oa_aligned': 0, 'n_oa_high': 0,
                 'n_press_samples': 100, 'n_press_high': 10}]
        pr = R.pressure_response(rows)
        assert pr['verdict'] == t('pr_insufficient')


# ── Mann-Whitney + Hodges-Lehmann ───────────────────────────────────────────

class TestMannWhitney:
    def test_empty_returns_none(self):
        mw = R.mann_whitney([], [1, 2, 3])
        assert mw['p'] is None

    def test_identical_distributions(self):
        mw = R.mann_whitney([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
        assert mw['p'] is not None and mw['p'] > 0.05

    def test_clearly_different(self):
        mw = R.mann_whitney([1, 2, 3, 4, 5], [100, 101, 102, 103, 104])
        assert mw['p'] is not None and mw['p'] < 0.05

    def test_rank_biserial_range(self):
        mw = R.mann_whitney([1, 2, 3, 4, 5], [6, 7, 8, 9, 10])
        assert 0.0 <= mw['r'] <= 1.0


class TestHodgesLehmann:
    def test_empty(self):
        hl = R._hodges_lehmann([], [1, 2])
        assert math.isnan(hl['hl'])

    def test_point_estimate_direction(self):
        # b overall greater than a: HL estimate should be positive
        hl = R._hodges_lehmann([1, 2, 3], [10, 11, 12])
        assert hl['hl'] > 0

    def test_ci_contains_estimate(self):
        hl = R._hodges_lehmann([1, 2, 3, 4, 5], [6, 7, 8, 9, 10])
        assert hl['ci95_lo'] <= hl['hl'] <= hl['ci95_hi']


class TestSegVerdict:
    def _rows(self, vals):
        return [{'ahi': v, 'oai': v * 0.8} for v in vals]

    def test_not_p05_gives_no_equivalence_claim(self):
        # p>=0.05 must read "no clear difference / equivalence not proven", never "no difference"
        v = R.seg_verdict(self._rows([3, 4, 5]), self._rows([3, 4, 5]))
        assert v['verdict'] == t('verdict_no_clear_diff')

    def test_clear_drop_detected(self):
        v = R.seg_verdict(self._rows([10, 11, 12, 13, 14]), self._rows([1, 2, 3, 4, 5]))
        assert v['verdict'] == t('verdict_decrease')

    def test_clear_rise_detected(self):
        v = R.seg_verdict(self._rows([1, 2, 3, 4, 5]), self._rows([10, 11, 12, 13, 14]))
        assert v['verdict'] == t('verdict_increase')

    def test_hl_field_present(self):
        v = R.seg_verdict(self._rows([5, 6, 7]), self._rows([1, 2, 3]))
        assert 'hl' in v and not math.isnan(v['hl'])

    def test_insufficient_sample(self):
        v = R.seg_verdict(self._rows([3]), self._rows([1]))
        assert v['verdict'] == t('verdict_insufficient_n')


# ── SAD SpO2 coverage quality: continuous-oximetry gate ─────────────────────

class TestSpo2CoverageLogic:
    """Verifies the sad_spo2_continuous semantics: T90 is not computed below the
    coverage gate."""

    def test_insufficient_coverage_means_t90_unavailable(self):
        coverage = 0.3   # below the 0.70 gate
        sad_spo2_continuous = coverage >= R.MIN_SIGNAL_COVERAGE
        assert not sad_spo2_continuous


# ── quality-gate reason codes ───────────────────────────────────────────────

class TestQualityReasonCodes:
    def test_reasons_render_in_every_locale(self):
        from resmed_sd_monitor.i18n import available
        from resmed_sd_monitor.i18n import set_lang as _sl
        for lang in available():
            _sl(lang)
            for code in (R.QR_SHORT_USE, R.QR_NO_EVE, R.QR_NO_LEAK, R.QR_HIGH_LEAK):
                text = R.quality_reason_text(code)
                assert text and text != code and not text.startswith('<')
        _sl('en')


# ── waveform layer: per-breath detection ────────────────────────────────────
#
# Synthetic-signal conventions (matching the development calibration):
#   _synth_flow(mod_amp, mod_period, jitter, seed) builds "asymmetric
#   inspiration/expiration + breath-by-breath variability" flow, optionally with
#   periodic tidal-volume modulation. Known input -> known detector output.


def _synth_flow(dur=700.0, rate_hz=0.22, mod_amp=0.0, mod_period=None,
                jitter=0.0, seed=1, fs=25.0):
    """Synthetic flow: sinusoidal breathing + optional periodic modulation +
    optional per-breath jitter."""
    rng = np.random.default_rng(seed)
    t_ = np.arange(0, dur, 1.0 / fs)
    amp = 1.0 + (mod_amp * np.sin(2 * np.pi * t_ / mod_period) if mod_period else 0.0)
    sig = amp * np.sin(2 * np.pi * rate_hz * t_)
    if jitter:
        sig = sig + rng.normal(0, jitter, sig.size)
    return sig


class TestFindBreaths:
    def test_counts_known_rate(self):
        # 0.22 Hz = 13.2 breaths/min
        sig = _synth_flow(dur=120.0)
        peaks, _troughs = R.find_breaths(sig, 25.0)
        assert 24 <= peaks.size <= 28          # 120s x 13.2/min ~= 26

    def test_empty_and_short_input(self):
        assert R.find_breaths(np.array([]), 25.0)[0].size == 0
        assert R.find_breaths(np.zeros(10), 25.0)[0].size == 0

    def test_flat_signal_no_peaks(self):
        # zero flow must not fabricate breaths (prominence gate blocks it)
        assert R.find_breaths(np.zeros(60 * 25), 25.0)[0].size == 0


class TestBreathe:
    def test_period_and_rate(self):
        br = R.breathe(_synth_flow(dur=200.0), 25.0)
        assert len(br) > 30
        rr = 60.0 / np.median([b['T'] for b in br])
        assert 12.0 <= rr <= 14.5

    def test_skips_central_pause(self):
        # 20 s of zero flow mid-signal: that period stretches and must not be
        # miscounted as one normal breath
        sig = _synth_flow(dur=120.0)
        sig[int(50 * 25):int(70 * 25)] = 0.0
        br = R.breathe(sig, 25.0)
        assert len(br) < 28
        assert max(b['T'] for b in br) <= 10.0     # over-long periods filtered

    def test_tidal_volume_positive_unimodal(self):
        br = R.breathe(_synth_flow(dur=120.0), 25.0)
        tvs = np.array([b['tv'] for b in br])
        assert (tvs > 0).all()
        assert np.isfinite([b['fi'] for b in br]).sum() > 0


class TestFlatteningIndex:
    """Low FI = plateau-like waveform = flow limitation; high = rounded normal."""

    def test_flat_plateau_lower_than_rounded(self):
        n = 60
        rounded = np.sin(np.linspace(0, np.pi, n))          # rounded inspiration
        plateau = np.clip(np.sin(np.linspace(0, np.pi, n)), 0, 1) ** 0.15  # plateau-like
        fi_r = R._flattening_index(rounded)
        fi_p = R._flattening_index(plateau)
        assert fi_p < fi_r

    def test_degenerate_inputs_return_nan(self):
        assert math.isnan(R._flattening_index(np.array([])))
        assert math.isnan(R._flattening_index(np.zeros(10)))
        assert math.isnan(R._flattening_index(np.array([-1.0, -2.0, -3.0, -4.0])))


class TestPeriodicityFit:
    """Periodic breathing: strong synthetic modulation is detected, unmodulated
    is not.

    Threshold calibration (measured during development): no modulation
    corr2 ~= 0.000; modulation depth 0.5 ~= 0.12, 0.7 ~= 0.21; real
    non-periodic nights ~= 0.000-0.001.
    """

    def _series(self, mod_amp=0.0, mod_period=None):
        sig = _synth_flow(dur=1200.0, mod_amp=mod_amp, mod_period=mod_period,
                          jitter=0.08, seed=7)
        br = R.breathe(sig, 25.0)
        return (np.array([b['t'] for b in br]), np.array([b['tv'] for b in br]))

    def test_detects_strong_modulation(self):
        tt, tv = self._series(0.7, 50.0)
        fit = R.periodicity_fit(tt, tv)
        assert fit['corr2'] >= R.WAVE_PERIOD_CORR2
        assert abs(fit['period_s'] - 50.0) <= 4.0

    def test_rejects_unmodulated(self):
        tt, tv = self._series()
        fit = R.periodicity_fit(tt, tv)
        assert fit['corr2'] < R.WAVE_PERIOD_WEAK

    def test_too_short_returns_none(self):
        fit = R.periodicity_fit(np.arange(0, 100, 4.0), np.random.default_rng(0).normal(1, .2, 25))
        assert fit['corr2'] is None and fit['period_s'] is None

    def test_period_search_bounded(self):
        # slow drift (>90s) must not be reported as periodic breathing
        tt, tv = self._series()
        drift = 1.0 + 0.5 * np.sin(2 * np.pi * tt / 400.0)
        fit = R.periodicity_fit(tt, tv * drift)
        assert fit['corr2'] < R.WAVE_PERIOD_CORR2


class TestPeriodicityVerdict:
    def test_none_inputs_are_cover_too_short(self):
        assert R.periodicity_verdict(None, None, 1000.0) == 'cover_too_short'

    def test_short_span_is_cover_too_short(self):
        assert R.periodicity_verdict(0.5, 50.0, 100.0) == 'cover_too_short'

    def test_weak_band_labeled_weak(self):
        v = R.periodicity_verdict(0.06, 50.0, 1000.0)
        assert v.startswith('weak_')

    def test_short_vs_long_cycle_split_at_40s(self):
        assert R.periodicity_verdict(0.5, 30.0, 1000.0) == 'periodic_short_cycle'
        assert R.periodicity_verdict(0.5, 60.0, 1000.0) == 'periodic_long_cycle'

    def test_below_weak_is_no_periodic(self):
        assert R.periodicity_verdict(0.01, 50.0, 1000.0) == 'no_periodic'


class TestClusterEvents:
    def test_groups_within_gap(self):
        # 3 events with adjacent gaps <=120s -> 1 cluster; the isolated one doesn't count
        ts = [0.0, 60.0, 120.0, 1000.0]
        c = R.cluster_events(ts)
        assert c['n_clusters'] == 1
        assert c['n_events_in_clusters'] == 3
        assert c['longest'] == 3

    def test_below_min_events_not_a_cluster(self):
        assert R.cluster_events([0.0, 60.0])['n_clusters'] == 0

    def test_empty(self):
        c = R.cluster_events([])
        assert c['n_clusters'] == 0 and c['cluster_frac'] is None

    def test_gap_boundary_is_inclusive(self):
        # gaps exactly equal to the threshold belong to the same cluster (impl is <=)
        c = R.cluster_events([0.0, 120.0, 240.0])
        assert c['n_clusters'] == 1

    def test_nan_times_skipped(self):
        c = R.cluster_events([float('nan'), 0.0, 60.0, 120.0])
        assert c['n_events'] == 3


class TestPressureExposure:
    def test_bins_and_event_attribution(self):
        # sample at bin centres to avoid landing exactly on bin edges
        press = np.concatenate([np.full(600, 10.25), np.full(600, 12.25)])
        ev = np.array([10.3, 12.3, 12.4])
        ex = R.pressure_exposure(press, ev)
        assert ex['n_breaths'] == 1200 and ex['n_events'] == 3
        assert ex['delivered_p90'] is not None
        b10 = [b for b in ex['bins'] if b['lo'] == 10.0][0]
        b12 = [b for b in ex['bins'] if b['lo'] == 12.0][0]
        assert b10['events'] == 1 and b12['events'] == 2

    def test_empty_press(self):
        ex = R.pressure_exposure(np.array([]), np.array([]))
        assert ex['bins'] == [] and ex['n_breaths'] == 0

    def test_rate_is_per_100_breaths(self):
        press = np.full(200, 10.25)
        ex = R.pressure_exposure(press, np.array([10.2, 10.3]))
        b = ex['bins'][0]
        assert b['event_per_100_breaths'] == pytest.approx(1.0)


class TestPressureFiBins:
    # 6 bins, 2000 breaths each (1/6 of exposure each > WAVE_BIN_MIN_FRAC)
    _LEVELS = (9.25, 10.25, 11.25, 12.25, 13.25, 14.25)

    def _mk(self, fi_by_level):
        press = np.concatenate([np.full(2000, lv) for lv in self._LEVELS])
        fi = np.concatenate([np.full(2000, v) for v in fi_by_level])
        return R._pressure_fi_bins(press, fi)

    def test_ramp_bins_excluded(self):
        # a low bin with only a few dozen breaths (Ramp drive-by) stays off the curve
        press = np.concatenate([np.full(30, 5.25), np.full(2000, 10.25), np.full(2000, 12.25)])
        fi = np.concatenate([np.full(30, 0.05), np.full(2000, 0.17), np.full(2000, 0.18)])
        c = R._pressure_fi_bins(press, fi)
        assert c is not None
        assert min(b['lo'] for b in c['bins']) >= 10.0

    def test_flat_curve_gives_small_gain(self):
        c = self._mk([0.17] * 6)
        assert abs(c['gain_lo_to_hi']) < 0.02

    def test_rising_curve_gives_positive_gain(self):
        c = self._mk([0.08, 0.10, 0.12, 0.14, 0.16, 0.18])
        assert c['gain_lo_to_hi'] > 0.02
        assert c['slope_per_cmH2O'] > 0

    def test_therapy_range_reported(self):
        c = self._mk([0.17] * 6)
        assert c['therapy_lo'] == pytest.approx(9.0)
        assert c['therapy_hi'] == pytest.approx(14.5)

    def test_insufficient_bins_returns_none(self):
        assert R._pressure_fi_bins(np.full(100, 10.25), np.full(100, 0.17)) is None


class TestSampleAt:
    def test_prev_and_next(self):
        times = np.array([0.0, 1.0, 2.0, 3.0])
        vals = np.array([10.0, 11.0, 12.0, 13.0])
        assert R._sample_at(times, vals, 2.4, 'prev') == 12.0
        assert R._sample_at(times, vals, 2.4, 'next') == 13.0

    def test_out_of_range_is_nan(self):
        times = np.array([0.0, 1.0])
        vals = np.array([10.0, 11.0])
        assert math.isnan(R._sample_at(times, vals, -5.0, 'prev'))
        assert math.isnan(R._sample_at(times, vals, 99.0, 'next'))

    def test_empty(self):
        assert math.isnan(R._sample_at(np.array([]), np.array([]), 0.0))


class TestSummarizeBreathsPressureAlignment:
    """Regression: per-breath times are seconds relative to the flow-array start
    and must have flow_t0 added before aligning to the PLD pressure time axis
    (absolute epoch). Missing that conversion silently empties the alignment
    arrays (breath_press length 0) and the pressure-flatness section vanishes
    without any error."""

    def _breaths(self):
        sig = _synth_flow(dur=400.0, jitter=0.02, seed=3)
        return R.breathe(sig, 25.0)

    def test_relative_times_without_offset_do_not_align(self):
        """No flow_t0: pressure times are absolute epoch, relative seconds all miss."""
        br = self._breaths()
        t0 = 1_700_000_000.0
        press_times = t0 + np.arange(0, 400 * 0.5) / 0.5
        press_vals = np.full(press_times.size, 11.0)
        agg = R.summarize_breaths(br, press_times, press_vals)
        assert agg['breath_press'] is None or agg['breath_press'].size == 0

    def test_with_flow_t0_alignment_succeeds(self):
        br = self._breaths()
        t0 = 1_700_000_000.0
        press_times = t0 + np.arange(0, 400 * 0.5) / 0.5
        press_vals = np.full(press_times.size, 11.0)
        agg = R.summarize_breaths(br, press_times, press_vals, flow_t0=t0)
        assert agg['breath_press'] is not None
        assert agg['breath_press'].size == agg['n_breaths']
        np.testing.assert_allclose(agg['breath_press'], 11.0)

    def test_pressure_values_follow_time(self):
        """Aligned pressure must vary with the segment each breath falls in, not
        stay constant."""
        br = self._breaths()
        t0 = 1_700_000_000.0
        press_times = t0 + np.arange(0, 400 * 0.5) / 0.5
        press_vals = np.where(np.arange(press_times.size) < press_times.size // 2, 9.0, 14.0)
        agg = R.summarize_breaths(br, press_times, press_vals, flow_t0=t0)
        got = agg['breath_press']
        assert got.min() == pytest.approx(9.0) and got.max() == pytest.approx(14.0)


# ── data-directory plumbing ─────────────────────────────────────────────────

class TestSetDataDir:
    def test_rebinds_paths(self, tmp_path):
        before = R.DATA_DIR
        R.set_data_dir(tmp_path)
        try:
            assert R.ROOT == str(tmp_path / 'DATALOG')
            assert R.TUNING_LOG == str(tmp_path / 'tuning_log.json')
            assert R.REPORT_DIR == str(tmp_path / 'reports')
            assert R.STR_EDF == tmp_path / 'STR.edf'
        finally:
            R.set_data_dir(before)

    def test_tuning_log_segments(self):
        rows = [{'date': '20240101'}, {'date': '20240201'}, {'date': '20240301'}]
        log = [{'since': '20240101', 'label': 'A'},
               {'since': '20240215', 'label': 'B'}]
        segs = R.segment_nights(rows, log)
        assert [e['label'] for e, _ in segs] == ['A', 'B']
        assert [r['date'] for _, rs in segs for r in rs] == ['20240101', '20240201', '20240301']
