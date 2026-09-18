"""PAP therapy monitoring and clinical decision support from ResMed SD-card data.

Usage:
  resmed-sd-monitor --report        # therapy monitoring report: quality gates + segmented
                                    # efficacy + clinical review cues + charts
  resmed-sd-monitor --wave [N]      # breath-by-breath flow waveform: clustering / periodic
                                    # breathing / pressure-flatness (last 14 treatment nights)
  resmed-sd-monitor --pressure      # event-pressure association (descriptive only)
  resmed-sd-monitor --settings      # current device prescription (from STR.edf)
  resmed-sd-monitor 20240316        # one night's detail (event list with pressure at onset)
  resmed-sd-monitor                 # summary table of all nights
  resmed-sd-monitor --csv           # summary table as CSV on stdout

Options:
  --data-dir DIR    SD-card data directory (see layout below). Falls back to
                    $RSDM_DATA_DIR, then $CPAP_DATA_DIR, then ./data
  --lang en|zh|ja   Report/output language (default: from locale, else en)

Directory layout (a nightly directory per treatment date):
  <data-dir>/DATALOG/<YYYYMMDD>/<timestamp>_{BRP,PLD,SAD,EVE,CSL}.edf
    BRP flow+pressure 25 Hz | PLD pressure/leak/tidal volume/resp rate/minute ventilation/
        snore/flow-limitation 0.5 Hz | SAD pulse rate + SpO2 1 Hz
    EVE respiratory-event annotations | CSL Cheyne-Stokes annotations (EDF+, parsed by hand)
  <data-dir>/STR.edf            device settings summary (non-standard EDF, parsed by hand)
  <data-dir>/tuning_log.json    manual log of prescription changes; segments the report
  <data-dir>/reports/           generated reports, snapshots and charts

Scope boundary (read before interpreting anything): device events are estimated by the
flow/pressure algorithms and the denominator is therapy *usage* time, not EEG-confirmed
sleep time. Everything this tool outputs are PAP treatment-monitoring cues, not PSG
diagnoses: it cannot diagnose OSA severity, REM/positional OSA, treatment-emergent central
sleep apnea (TECSA), or set prescriptions. Statistics use scipy's standard implementations
(Mann-Whitney / Spearman) to describe multi-night trends; uncorrected observational p-values
do not imply causality and cannot replace symptoms, comorbidities and specialist assessment.

Waveform layer (--wave / report section 4b) has one more reading rule: AutoSet raises
pressure in response to events, so "high pressure <-> many events" is the echo of that
feedback loop, not causality — event-rate ratios must never be used to argue "more pressure
does not help". Whether pressure headroom remains is judged only from the pressure-flatness
curve (background flow limitation compared across pressures), and only after excluding
low-pressure bins that Ramp merely passed through, otherwise you measure "ramp vs therapy",
not a dose effect.
"""

import glob
import json
import math
import os
import re
import struct
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from edfio import read_edf
from scipy.signal import find_peaks

from .i18n import set_lang, t

# Windows terminals default to GBK; force UTF-8 output to avoid mojibake
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ── Data directory ───────────────────────────────────────────────────────────
#
# Resolution order: --data-dir flag (via set_data_dir from main()) >
# $RSDM_DATA_DIR > legacy $CPAP_DATA_DIR > ./data. All paths below are module
# globals so that set_data_dir() can rebind them in one place; every consumer
# reads them at call time.


def _default_data_dir() -> Path:
    env = os.environ.get("RSDM_DATA_DIR") or os.environ.get("CPAP_DATA_DIR")
    return Path(env) if env else Path("data")


def set_data_dir(path) -> None:
    """Point the module at a data directory (CLI --data-dir / tests)."""
    global DATA_DIR, ROOT, TUNING_LOG, REPORT_DIR, STR_EDF
    DATA_DIR = Path(path)
    ROOT = str(DATA_DIR / "DATALOG")
    TUNING_LOG = str(DATA_DIR / "tuning_log.json")
    REPORT_DIR = str(DATA_DIR / "reports")
    STR_EDF = DATA_DIR / "STR.edf"


DATA_DIR = _default_data_dir()
set_data_dir(DATA_DIR)

# Local trend-analysis data-quality thresholds (not diagnostic criteria)
MIN_ANALYZE_H = 2.0        # nights with <2h of therapy fluctuate too much for cross-night stats
COMPLIANCE_H = 4.0         # <4h only counts as insufficient therapy exposure; says nothing
                           # about true sleep time
LEAK_95_MAX = 24.0         # L/min, common ResMed large-leak screening line; depends on
                           # mask/device, judge against actuals
MIN_SIGNAL_COVERAGE = 0.70 # lower limit of usable channel coverage; below this, unusable

# Device-data screening thresholds (only trigger review/referral cues; never generate
# diagnoses or prescriptions on their own)
RESIDUAL_REI_TARGET = 5.0
RESIDUAL_REI_REVIEW = 10.0
CENTRAL_REVIEW_CAI = 5.0
MIN_PATTERN_EVENTS = 20
MIN_PATTERN_NIGHTS = 5

# Quality-gate reason codes (stable machine keys stored in summaries/snapshots;
# rendered through the i18n table only at display time)
QR_SHORT_USE = 'short_use'   # therapy record shorter than MIN_ANALYZE_H
QR_NO_EVE = 'no_eve'         # no EVE event-annotation files
QR_NO_LEAK = 'no_leak'       # no Leak channel
QR_HIGH_LEAK = 'high_leak'   # 95th-percentile leak above LEAK_95_MAX

_QR_KEYS = {QR_SHORT_USE: 'qr_short_use', QR_NO_EVE: 'qr_no_eve',
            QR_NO_LEAK: 'qr_no_leak', QR_HIGH_LEAK: 'qr_high_leak'}


def quality_reason_text(code: str) -> str:
    """Human-readable text for a quality-gate reason code (report/terminal)."""
    key = _QR_KEYS.get(code)
    if key is None:
        return code
    if code == QR_SHORT_USE:
        return t(key, h=MIN_ANALYZE_H)
    if code == QR_HIGH_LEAK:
        return t(key, v=LEAK_95_MAX)
    return t(key)


# Event-annotation TAL: +onset\x15duration\x14label\x14
_TAL = re.compile(rb'([+-]?\d+(?:\.\d+)?)\x15(\d*(?:\.\d+)?)\x14([^\x14]*)\x14')


def classify_event_label(label):
    """Normalize a ResMed event label to oa/ca/hyp/ua; unknown labels return None.

    A bare ``Apnea`` carries no obstructive/central qualifier and must stay
    unclassified (ua) — never default it to obstructive.
    """
    lab = label.strip().lower()
    if 'central apnea' in lab:
        return 'ca'
    if 'obstructive apnea' in lab:
        return 'oa'
    if 'hypopnea' in lab:
        return 'hyp'
    if re.search(r'\bapnea\b', lab):
        return 'ua'
    return None


def parse_annotations(path):
    """Parse an EDF+D annotation file into [(onset_s, dur_s, label), ...]."""
    b = open(path, 'rb').read()
    if len(b) < 256:
        raise ValueError(f'EDF header too short: {path}')
    nsig = int(b[252:256])
    data = b[256 + 256 * nsig:]
    out = []
    for m in _TAL.finditer(data):
        onset = float(m.group(1))
        dur = float(m.group(2)) if m.group(2) else 0.0
        label = m.group(3).decode('latin-1', 'replace').strip()
        if not label or label == 'Recording starts':
            continue
        out.append((onset, dur, label))
    return out


# Per-night channel cache: (path, name) -> (numpy array, fs)
_SIG_CACHE: dict = {}

# Per-night file-object cache: path -> Edf (same lifetime as _SIG_CACHE)
# Why it exists: edfio's read_edf builds an np.memmap over the whole data
# section and charges for it per call; a single PLD file has 7 channels and
# _concat / _channel_quality each request every channel name via
# read_signal_fs, so without the cache one file would be read 7 independent
# times (measured: one --report did 1264 read_edf calls for only 351 unique
# paths). Cleared per night; only that night's files are ever held.
_EDF_CACHE: dict = {}


def _load_edf(path):
    """Return the Edf for path, parsing it at most once per night."""
    e = _EDF_CACHE.get(path)
    if e is None:
        e = read_edf(path)
        _EDF_CACHE[path] = e
    return e


def _finite_values(values, low=None, high=None):
    """Signal values that are finite and (optionally) within physical range."""
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if low is not None:
        values = values[values >= low]
    if high is not None:
        values = values[values <= high]
    return values


def _merge_intervals(intervals):
    """Merge half-open time intervals; returns (merged, gap_seconds, overlap_seconds)."""
    source = sorted((float(a), float(b)) for a, b in intervals
                    if b > a and np.isfinite(a + b))
    if not source:
        return [], 0.0, 0.0
    merged = []
    gaps = overlaps = 0.0
    cur_a, cur_b = source[0]
    for a, b in source[1:]:
        if a > cur_b:
            gaps += a - cur_b
            merged.append((cur_a, cur_b))
            cur_a, cur_b = a, b
        else:
            overlaps += max(0.0, cur_b - a)
            cur_b = max(cur_b, b)
    merged.append((cur_a, cur_b))
    return merged, gaps, overlaps


def _interval_duration(intervals):
    return float(sum(b - a for a, b in intervals))


def _in_intervals(t, intervals):
    """Is time point t inside any half-open valid interval?"""
    return any(a <= t < b for a, b in intervals)


def _therapy_intervals(day_dir):
    """Build valid therapy intervals from BRP absolute times, avoiding double
    counting and treating gaps as exposure."""
    raw = []
    for p in glob.glob(f"{day_dir}/*_BRP.edf"):
        st = edf_start(p); dur = file_duration(p)
        if st is not None and dur > 0:
            raw.append((st.timestamp(), st.timestamp() + dur))
    merged, gaps, overlaps = _merge_intervals(raw)
    return merged, {
        'n_files': len(raw),
        'raw_h': _interval_duration(raw) / 3600.0,
        'union_h': _interval_duration(merged) / 3600.0,
        'gap_s': gaps,
        'overlap_s': overlaps,
    }


def read_signal_dimension(path, name):
    """Read the EDF physical dimension; returns None on failure (units are never guessed)."""
    try:
        e = _load_edf(path)
        for sig in e.signals:
            if sig.label.split('.')[0].lower() == name.lower():
                return str(getattr(sig, 'physical_dimension', '') or '').strip() or None
    except (OSError, ValueError):
        pass
    return None


def _channel_quality(files, name, therapy_intervals, low=None, high=None):
    """Valid samples, coverage and unit metadata for one channel."""
    valid_n = total_n = 0
    fs_values = set(); dimensions = set(); intervals = []
    for p in files:
        arr, fs = read_signal_fs(p, name); st = edf_start(p)
        if arr is None or not fs or st is None:
            continue
        arr = np.asarray(arr, dtype=float)
        mask = np.isfinite(arr)
        if low is not None: mask &= arr >= low
        if high is not None: mask &= arr <= high
        valid_n += int(mask.sum()); total_n += int(arr.size)
        fs_values.add(float(fs))
        dim = read_signal_dimension(p, name)
        if dim: dimensions.add(dim)
        start = st.timestamp(); intervals.append((start, start + arr.size / float(fs)))
    observed, _, _ = _merge_intervals(intervals)
    observed_h = _interval_duration(observed) / 3600.0
    exposure_h = _interval_duration(therapy_intervals) / 3600.0
    coverage = observed_h / exposure_h if exposure_h else 0.0
    finite_fraction = valid_n / total_n if total_n else 0.0
    return {
        'available': bool(total_n), 'valid_n': valid_n, 'total_n': total_n,
        'finite_fraction': finite_fraction, 'coverage': min(coverage, 1.0),
        'fs': sorted(fs_values), 'dimensions': sorted(dimensions),
        'valid_h': observed_h, 'usable': bool(valid_n and coverage >= MIN_SIGNAL_COVERAGE),
    }


def _event_records(day_dir, therapy_intervals):
    """Parse, deduplicate EVE events and keep only those inside valid therapy intervals."""
    records = []; raw_n = invalid_n = outside_n = duplicate_n = 0
    files = sorted(glob.glob(f"{day_dir}/*_EVE.edf"))
    for p in files:
        st = edf_start(p)
        if st is None:
            invalid_n += 1; continue
        try:
            annotations = parse_annotations(p)
        except (OSError, ValueError, IndexError):
            invalid_n += 1; continue
        base = st.timestamp()
        for onset, duration, label in annotations:
            raw_n += 1; kind = classify_event_label(label)
            if (not np.isfinite(onset) or not np.isfinite(duration) or onset < 0
                    or duration < 0 or kind is None):
                invalid_n += 1; continue
            t_ = base + onset
            if not _in_intervals(t_, therapy_intervals):
                outside_n += 1; continue
            key = (round(t_ * 2), round(duration, 1), label.strip().lower())
            if any(r['_dedup_key'] == key for r in records):
                duplicate_n += 1; continue
            records.append({'time': t_, 'duration': float(duration), 'label': label,
                            'kind': kind, '_dedup_key': key})
    records.sort(key=lambda r: r['time'])
    for r in records:
        r.pop('_dedup_key', None)
    return records, {
        'files': len(files), 'raw_n': raw_n, 'invalid_n': invalid_n,
        'outside_n': outside_n, 'duplicate_n': duplicate_n,
        'available': bool(files), 'parsed_n': len(records),
    }


def _nearest_within(times, event_t: float, tol: float):
    """Nearest point in times to event_t; returns (index, signed delta) or (None, None)
    beyond tol.

    Kept as its own function so unit tests can call it directly. This
    searchsorted + tolerance window used to live inside _event_pressure_at,
    which reads real EDF files tests cannot construct — so the tests copied
    the same code and verified a copy of it (still green if the impl changed).
    """
    if times is None or len(times) == 0:
        return None, None
    right = int(np.searchsorted(times, event_t))
    candidates = [i for i in (right - 1, right) if 0 <= i < len(times)]
    if not candidates:
        return None, None
    idx   = min(candidates, key=lambda i: abs(times[i] - event_t))
    delta = float(times[idx] - event_t)
    return (idx, delta) if abs(delta) <= tol else (None, None)


def _event_pressure_at(day_dir, event_t):
    """Nearest pressure inside the PLD segment containing the event; None outside/gaps."""
    paths = sorted(glob.glob(f"{day_dir}/*_PLD.edf"),
                   key=lambda x: (edf_start(x) or datetime.max))
    for p in paths:
        st = edf_start(p); arr, fs = read_signal_fs(p, 'Press')
        if st is None or arr is None or not fs:
            continue
        start = st.timestamp(); times = start + np.arange(len(arr), dtype=float) / fs
        idx, delta = _nearest_within(times, event_t, max(5.0, 2.0 / fs))
        if idx is not None:
            return float(arr[idx]), delta
    return None, None


def read_signal_fs(path, name):
    """Read one channel from an EDF file; returns (numpy array, sampling rate).
    (None, None) when missing/corrupt."""
    key = (path, name)
    if key in _SIG_CACHE:
        return _SIG_CACHE[key]
    try:
        e = _load_edf(path)
    except (OSError, ValueError):
        _SIG_CACHE[key] = (None, None)
        return None, None
    try:
        for sig in e.signals:
            if sig.label.split('.')[0].lower() == name.lower():
                _SIG_CACHE[key] = (sig.data, sig.sampling_frequency)
                return sig.data, sig.sampling_frequency
        _SIG_CACHE[key] = (None, None)
        return None, None
    except Exception:
        _SIG_CACHE[key] = (None, None)
        return None, None


def read_signal(path, name):
    """Read one channel from an EDF file as a numpy array (None when missing/corrupt)."""
    arr, _ = read_signal_fs(path, name)
    return arr


def _concat(files, name):
    """Concatenate one channel across multiple PLD/SAD segments."""
    arrs = [a for p in files if (a := read_signal(p, name)) is not None]
    return np.concatenate(arrs) if arrs else np.array([])


_DUR_CACHE: dict = {}


def file_duration(path):
    """File duration in seconds. Estimated from the byte header when the header
    is corrupt (ndr=-1). Cached per path (called repeatedly within a night)."""
    if path in _DUR_CACHE:
        return _DUR_CACHE[path]
    try:
        e = read_edf(path)
        return _DUR_CACHE.setdefault(path, float(e.duration))
    except (OSError, ValueError):
        b = open(path, 'rb').read()
        try:
            ndr = int(b[236:244]); durr = float(b[244:252])
            if ndr > 0:
                return _DUR_CACHE.setdefault(path, ndr * durr)
        except Exception:
            pass
        return _DUR_CACHE.setdefault(path, 0.0)


def edf_start(path):
    """EDF header start time (bytes 168:176 dd.mm.yy + 176:184 hh.mm.ss) → datetime.
    None when corrupt."""
    try:
        b = open(path, 'rb').read(184)
        d = b[168:176].decode('latin-1'); t = b[176:184].decode('latin-1')
        return datetime.strptime(d + " " + t, "%d.%m.%y %H.%M.%S")
    except Exception:
        return None


def _pld_pressure_timeline(day_dir):
    """All PLD Press concatenated with absolute timestamps; returns (times, press, fs)
    or (None, None, None)."""
    segs = []
    fs = None
    for p in sorted(glob.glob(f"{day_dir}/*_PLD.edf")):
        arr, f = read_signal_fs(p, 'Press')
        st = edf_start(p)
        if arr is None or st is None:
            continue
        fs = f
        t0 = st.timestamp()
        segs.append((t0 + np.arange(len(arr)) / f, arr))
    if not segs:
        return None, None, None
    times = np.concatenate([s[0] for s in segs])
    press = np.concatenate([s[1] for s in segs])
    order = np.argsort(times)
    return times[order], press[order], fs


def _session_span(day_dir):
    """Absolute therapy span (epoch seconds) — earliest BRP start to latest BRP end.
    (None, None) when empty."""
    starts, ends = [], []
    for p in sorted(glob.glob(f"{day_dir}/*_BRP.edf")):
        st = edf_start(p); dur = file_duration(p)
        if st:
            starts.append(st.timestamp()); ends.append(st.timestamp() + dur)
    if not starts:
        return None, None
    return min(starts), max(ends)


# public alias (maskoff + external consumers); the leading-underscore name
# stays for backward compatibility with existing callers
session_span = _session_span


def align_events_pressure(day_dir):
    """Align clearly-labelled obstructive events onto PLD Press.

    Only pressure samples within 5 s of the event are accepted, so events
    between therapy segments are not glued to the previous or next segment's
    pressure. Unclassified ``Apnea`` never impersonates an obstructive event.
    """
    times, press, fs = _pld_pressure_timeline(day_dir)
    if times is None:
        return []
    tolerance_s = max(5.0, 2.0 / fs) if fs else 5.0
    out = []
    for p in sorted(glob.glob(f"{day_dir}/*_EVE.edf")):
        st = edf_start(p)
        if st is None:
            continue
        base = st.timestamp()
        for onset, _dur, lab in parse_annotations(p):
            if classify_event_label(lab) != 'oa':
                continue
            event_t = base + onset
            right = int(np.searchsorted(times, event_t))
            candidates = [i for i in (right - 1, right) if 0 <= i < len(times)]
            if not candidates:
                continue
            idx = min(candidates, key=lambda i: abs(times[i] - event_t))
            if abs(times[idx] - event_t) <= tolerance_s:
                out.append((event_t, float(press[idx]), lab))
    return out


def _nan(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


def night_summary(day_dir):
    """Summarize one DATALOG date directory (therapy record, not whole-night sleep)."""
    _SIG_CACHE.clear(); _DUR_CACHE.clear(); _EDF_CACHE.clear()   # new night: evict last night's caches
    pld = sorted(glob.glob(f"{day_dir}/*_PLD.edf"))
    sad = sorted(glob.glob(f"{day_dir}/*_SAD.edf"))

    # Valid therapy intervals (union of BRP segments, gaps excluded)
    therapy_ivs, therapy_meta = _therapy_intervals(day_dir)
    usage_h = therapy_meta['union_h']   # union duration; gaps no longer count into the denominator

    # Event counts: only events inside valid therapy intervals; missing EVE is
    # reported explicitly as unavailable
    ev_records, ev_meta = _event_records(day_dir, therapy_ivs)
    oa  = sum(1 for r in ev_records if r['kind'] == 'oa')
    ca  = sum(1 for r in ev_records if r['kind'] == 'ca')
    hyp = sum(1 for r in ev_records if r['kind'] == 'hyp')
    ua  = sum(1 for r in ev_records if r['kind'] == 'ua')
    events = oa + ca + hyp + ua
    ev_abs = [r['time'] for r in ev_records]

    # REI denominator is valid therapy time; missing EVE means unavailable, not zero
    eve_available = ev_meta['available']
    if eve_available and usage_h > 0:
        ahi = events / usage_h
        rei_available = True
    else:
        ahi = float('nan')
        rei_available = False

    press = _concat(pld, 'Press'); leak = _concat(pld, 'Leak')
    flowlim = _concat(pld, 'FlowLim'); snore = _concat(pld, 'Snore')
    rr = _concat(pld, 'RespRate'); tv = _concat(pld, 'TidVol'); mv = _concat(pld, 'MinVent')

    def pct(a, q): return float(np.percentile(a, q)) if a.size else float('nan')
    def med(a):    return float(np.median(a)) if a.size else float('nan')

    # Event-pressure alignment: pressure at the moment of each obstructive event
    ep = align_events_pressure(day_dir)
    oa_p = np.array([e[1] for e in ep])
    p90 = pct(press, 90)
    oa_press_med = float(np.median(oa_p)) if oa_p.size else float('nan')
    oa_press_hi_frac = float((oa_p >= p90).mean()) if (oa_p.size and not math.isnan(p90)) else float('nan')
    n_oa_high = int((oa_p >= p90).sum()) if (oa_p.size and not math.isnan(p90)) else 0
    n_press_high = int((press >= p90).sum()) if (press.size and not math.isnan(p90)) else 0

    # Event thirds over the therapy record: elapsed exposure across the union of
    # valid intervals, not envelope start-to-end
    ev_t = [float('nan')] * 3
    ev_t_counts = [0, 0, 0]
    if therapy_ivs and ev_abs:
        total_exposure = _interval_duration(therapy_ivs)
        if total_exposure > 0:
            def _elapsed(t_):
                # therapy seconds accumulated up to time t_
                acc = 0.0
                for a, b in therapy_ivs:
                    if t_ <= a:
                        break
                    acc += min(t_, b) - a
                return acc
            fracs = np.array([_elapsed(t_) / total_exposure for t_ in ev_abs])
            fracs = fracs[(fracs >= 0) & (fracs <= 1.001)]
            if fracs.size:
                cnt = np.bincount(np.clip((fracs * 3).astype(int), 0, 2), minlength=3).astype(float)
                ev_t_counts = [int(x) for x in cnt]
                ev_t = [float(x) for x in cnt / cnt.sum()]

    leak_95 = pct(leak, 95)
    quality_reasons = []
    if usage_h < MIN_ANALYZE_H:
        quality_reasons.append(QR_SHORT_USE)
    if not eve_available:
        quality_reasons.append(QR_NO_EVE)
    if not leak.size:
        quality_reasons.append(QR_NO_LEAK)
    elif leak_95 > LEAK_95_MAX:
        quality_reasons.append(QR_HIGH_LEAK)
    analyzable = not quality_reasons

    # SAD SpO2: only used for continuous hypoxia metrics when coverage passes the
    # gate; otherwise explicitly marked undeterminable
    sad_cq = _channel_quality(sad, 'SpO2', therapy_ivs, low=50.0)
    sad_spo2_continuous = sad_cq['usable']   # coverage >= MIN_SIGNAL_COVERAGE

    spo2_raw = _concat(sad, 'SpO2')
    spo2 = spo2_raw[spo2_raw > 50] if spo2_raw.size else spo2_raw

    if sad_spo2_continuous and spo2.size:
        spo2_t90_pct = float((spo2 < 90).mean() * 100)
        spo2_below88_min = 0.0
        for p in sad:
            raw, fs = read_signal_fs(p, 'SpO2')
            if raw is not None and fs:
                valid = raw[raw > 50]
                spo2_below88_min += float((valid < 88).sum() / float(fs) / 60.0)
    else:
        # Coverage too low: T90/hypoxia time stays incalculable rather than being
        # faked from sparse samples
        spo2_t90_pct = float('nan')
        spo2_below88_min = float('nan')

    night_date = os.path.basename(day_dir)

    # SpO2 min/avg come from SAD when usable (coverage-gated above)
    if spo2.size:
        spo2_min_out = float(spo2.min())
        spo2_avg_out = float(spo2.mean())
        spo2_src = 'SAD'
    else:
        spo2_min_out = spo2_avg_out = float('nan')
        spo2_src = None

    return {
        'date': night_date,
        # usage_h kept for backward compatibility with old snapshots/CSV; value is now
        # the deduplicated BRP union duration, with raw metadata attached
        'usage_h': usage_h,
        'therapy_meta': therapy_meta,
        # ahi kept for backward compatibility; meaning: device-estimated residual event
        # index (denominator is therapy usage time, not PSG sleep time)
        # when ahi_available=False, ahi/residual_rei are nan and must not enter trend stats
        'ahi': ahi, 'residual_rei': ahi, 'ahi_available': rei_available,
        'oai': oa / usage_h if (usage_h and rei_available) else float('nan'),
        'cai': ca / usage_h if (usage_h and rei_available) else float('nan'),
        'hi':  hyp / usage_h if (usage_h and rei_available) else float('nan'),
        'uai': ua / usage_h if (usage_h and rei_available) else float('nan'),
        'n_oa': oa, 'n_ca': ca, 'n_hyp': hyp, 'n_ua': ua, 'n_ev': events,
        'ev_quality': ev_meta,
        'press_med': med(press), 'press_95': pct(press, 95),
        'press_max': float(press.max()) if press.size else float('nan'),
        'leak_med': med(leak), 'leak_95': leak_95,
        'flowlim_med': med(flowlim), 'flowlim_95': pct(flowlim, 95),
        'snore_med': med(snore), 'snore_95': pct(snore, 95),
        'resprate_med': med(rr), 'tidvol_med': med(tv), 'minvent_med': med(mv),
        'spo2_min': spo2_min_out,
        'spo2_avg': spo2_avg_out,
        'spo2_src': spo2_src,
        'spo2_continuous': sad_spo2_continuous,
        'sad_coverage': sad_cq['coverage'],
        # T90/hypoxia time: valid only when SAD coverage passes the gate; nan otherwise,
        # and the report explicitly marks it undeterminable
        'spo2_t90_pct': spo2_t90_pct,
        'spo2_below88_min': spo2_below88_min,
        'oa_press_med': oa_press_med, 'oa_press_hi_frac': oa_press_hi_frac,
        'n_oa_aligned': int(oa_p.size), 'n_oa_high': n_oa_high,
        'n_press_samples': int(press.size), 'n_press_high': n_press_high,
        'oa_alignment_coverage': float(oa_p.size / oa) if oa else float('nan'),
        'ev_t1': ev_t[0], 'ev_t2': ev_t[1], 'ev_t3': ev_t[2],
        'n_ev_t1': ev_t_counts[0], 'n_ev_t2': ev_t_counts[1], 'n_ev_t3': ev_t_counts[2],
        'short_night': bool(usage_h < COMPLIANCE_H), 'analyzable': analyzable,
        'quality_reasons': quality_reasons,
    }


def mann_whitney(a, b):
    """Mann-Whitney U + two-sided p (scipy standard: exact for small samples,
    normal approximation with tie correction for large ones) + rank-biserial |r|
    effect size. An earlier version used a hand-rolled normal approximation;
    p-values differed slightly."""
    from scipy import stats as _st
    a = np.asarray(a, float); a = a[~np.isnan(a)]
    b = np.asarray(b, float); b = b[~np.isnan(b)]
    n1, n2 = len(a), len(b)
    if n1 == 0 or n2 == 0:
        return {'p': None, 'U': None, 'r': None, 'n1': n1, 'n2': n2}
    U1, p = _st.mannwhitneyu(a, b, alternative='two-sided')
    U1, p = float(U1), float(p)
    r = abs(2 * U1 / (n1 * n2) - 1)                       # rank-biserial magnitude
    return {'p': min(p, 1.0), 'U': min(U1, n1 * n2 - U1), 'r': r, 'n1': n1, 'n2': n2}


def spearman(x, y):
    """Spearman rank correlation rho + two-sided p (scipy standard, exact t
    distribution; an earlier version used a hand-rolled normal approximation)."""
    from scipy import stats as _st
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = ~(np.isnan(x) | np.isnan(y))
    x, y = x[m], y[m]
    n = len(x)
    if n < 3 or np.unique(x).size < 2 or np.unique(y).size < 2:
        return {'rho': None, 'p': None, 'n': n}
    rho, p = _st.spearmanr(x, y)
    if np.isnan(rho):
        return {'rho': None, 'p': None, 'n': n}                # all-equal/zero-variance → meaningless
    return {'rho': float(rho), 'p': float(p), 'n': n}


def _hodges_lehmann(a, b, seed=42):
    """Hodges–Lehmann two-sample location shift (Walsh averages) with bootstrap 95% CI.
    Robust point estimate of the median difference b - a."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    a = a[~np.isnan(a)]; b = b[~np.isnan(b)]
    if not (len(a) and len(b)):
        return {'hl': float('nan'), 'ci95_lo': float('nan'), 'ci95_hi': float('nan')}
    diffs = (b[:, None] - a[None, :]).ravel()
    hl = float(np.median(diffs))
    rng = np.random.default_rng(seed)
    boot = [float(np.median((rng.choice(b, len(b))[:, None] - rng.choice(a, len(a))[None, :]).ravel()))
            for _ in range(1000)]
    lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
    return {'hl': hl, 'ci95_lo': lo, 'ci95_hi': hi}


def seg_verdict(seg_a, seg_b, key='ahi'):
    """Distribution comparison of one metric across two segments: MWU + Hodges–Lehmann
    robust location shift (exploratory; no causal reading)."""
    a = [r[key] for r in seg_a if not _nan(r.get(key, float('nan')))]
    b = [r[key] for r in seg_b if not _nan(r.get(key, float('nan')))]
    mw = mann_whitney(a, b)
    ma = float(np.nanmedian(a)) if a else float('nan')
    mb = float(np.nanmedian(b)) if b else float('nan')
    delta = mb - ma
    hl = _hodges_lehmann(a, b)
    if mw['p'] is None or mw['n1'] < 3 or mw['n2'] < 3:
        verdict = t('verdict_insufficient_n')
    elif mw['p'] < 0.05:
        verdict = t('verdict_decrease') if delta < 0 else t('verdict_increase')
    else:
        # p>=0.05 proves neither equivalence nor "no difference within noise"
        verdict = t('verdict_no_clear_diff')
    return {'key': key, 'med_a': ma, 'med_b': mb, 'delta': delta,
            'hl': hl['hl'], 'hl_ci95_lo': hl['ci95_lo'], 'hl_ci95_hi': hl['ci95_hi'],
            'p': mw['p'], 'r': mw['r'], 'verdict': verdict, 'n1': mw['n1'], 'n2': mw['n2']}


def pressure_response(rows):
    """Describe the co-occurrence of obstructive events and pressure; never use this
    to judge cause or adjust prescriptions on your own.

    High-pressure bins naturally occupy only ~10% of therapy time, so besides the
    share of events we compute an event-rate ratio (event rate in high-pressure
    bins / event rate elsewhere). But APAP raises pressure in *response* to events,
    so even that cannot serve as causal evidence that "pressure does not help" or
    "pressure causes events".
    """
    sp = spearman([r['press_95'] for r in rows], [r['oai'] for r in rows])
    epmed = [r['oa_press_med'] for r in rows if not _nan(r.get('oa_press_med'))]
    tpmed = [r['press_med'] for r in rows if not _nan(r.get('press_med'))]
    n_aligned = sum(int(r.get('n_oa_aligned', 0)) for r in rows)
    n_high = sum(int(r.get('n_oa_high', 0)) for r in rows)
    samples = sum(int(r.get('n_press_samples', 0)) for r in rows)
    high_samples = sum(int(r.get('n_press_high', 0)) for r in rows)
    pooled_hi = n_high / n_aligned if n_aligned else None
    high_exposure = high_samples / samples if samples else None
    high_rate = n_high / high_samples if high_samples else None
    other_events, other_samples = n_aligned - n_high, samples - high_samples
    other_rate = other_events / other_samples if other_samples else None
    rate_ratio = high_rate / other_rate if (high_rate is not None and other_rate and other_rate > 0) else None
    ev_p = float(np.median(epmed)) if epmed else None
    th_p = float(np.median(tpmed)) if tpmed else None
    if n_aligned < MIN_PATTERN_EVENTS or len(rows) < MIN_PATTERN_NIGHTS:
        verdict = t('pr_insufficient')
        why = t('pr_insufficient_why', n=n_aligned, min_events=MIN_PATTERN_EVENTS,
                min_nights=MIN_PATTERN_NIGHTS)
    else:
        verdict = t('pr_cooccurrence')
        ratio_text = (t('pr_ratio_tail', rr=_fmt(rate_ratio, "{:.2f}"))
                      if rate_ratio is not None else '')
        why = t('pr_cooccurrence_why', n=n_aligned, pct=f'{pooled_hi*100:.0f}',
                exposure=f'{high_exposure*100:.0f}', ratio=ratio_text)
    return {'spearman': sp, 'pooled_hi': pooled_hi, 'ev_press_med': ev_p,
            'therapy_press_med': th_p, 'n_aligned_events': n_aligned,
            'n_high_events': n_high, 'high_pressure_exposure': high_exposure,
            'high_pressure_rate_ratio': rate_ratio, 'verdict': verdict, 'why': why}


def timing_verdict(rows):
    """Describe where events fall within the therapy record; without PSG no REM or
    positional cause can be claimed."""
    counts = [sum(int(r.get(f'n_ev_t{i}', 0)) for r in rows) for i in (1, 2, 3)]
    total = sum(counts)
    if total < MIN_PATTERN_EVENTS:
        return None
    a, b, c = (x / total for x in counts)
    if c >= 0.45 and c > a:
        v = t('timing_late_heavy')
    elif max(a, b, c) - min(a, b, c) < 0.12:
        v = t('timing_uniform')
    else:
        v = t('timing_uneven')
    return {'t1': a, 't2': b, 't3': c, 'n_events': total, 'verdict': v}


# ── Respiratory waveform analysis (flow curve: per-breath features / event
#    clustering / periodicity / pressure exposure) ────────────────────────────
#
# The sections above use device-computed 0.5 Hz summary channels and event
# annotations; this section goes back to the 25 Hz BRP flow waveform and
# reconstructs breathing breath by breath. The value: answering what summary
# channels cannot — whether residual obstruction is "not enough pressure" or
# "enough pressure but the wrong mechanism (clusters/REM/position)", and
# ventilatory instability at the loop-gain level (periodic breathing).
#
# Scope boundary: the device flow signal is not PSG nasal pressure/thermistry —
# no EEG arousals, no body position, no thoracoabdominal effort. FI (flattening
# index), per AASM v3's wording for RERAs, means "inspiratory flattening compared
# to baseline breathing" — a self-controlled comparison, not an absolute
# threshold; hence every threshold here is a within-night/within-segment
# quantile of the night itself, never literature absolute values, and none of
# this diagnoses RERAs or hypopneas. Curves are relative device trends and do
# not replace manual waveform review.

WAVE_SMOOTH_S = 0.30        # flow smoothing window (s): kills cardiogenic oscillations
                            # and quantization noise, keeps the breathing waveform
WAVE_PEAK_DIST_S = 1.20     # minimum spacing of inspiratory peaks: up to 50 breaths/min,
                            # blocks double detection
WAVE_PROM_FLOOR = 0.04      # minimum peak prominence (L/s); below this = invalid/no breath
WAVE_PROM_PCT = 0.12        # prominence threshold relative to the night's 99th percentile
WAVE_FI_A, WAVE_FI_B = 0.25, 0.85   # FI sampling window: 25%~85% of inspiration onset→peak
WAVE_PERIOD_LO_S = 20.0     # periodic-breathing search lower bound (s)
WAVE_PERIOD_HI_S = 90.0     # upper bound: oscillations >90 s look more like postural/
                            # post-arousal drift, not periodicity
WAVE_PERIOD_CORR2 = 0.10    # fit strength threshold for "periodic"
                            # (synthetic calibration: ≈0.12 at modulation depth 0.5)
WAVE_PERIOD_WEAK = 0.04     # weak-signal floor; below this, no periodicity is reported
WAVE_PERIOD_MIN_S = 300.0   # segments shorter than this are never judged periodic
                            # (too-short samples are false-positive machines)
WAVE_DETREND_S = 180.0      # detrend window: drift >90 s stays out of the frequency band
WAVE_CLUSTER_GAP_S = 120.0  # maximum adjacent spacing for events in one cluster
WAVE_CLUSTER_MIN = 3        # minimum events to form a cluster
WAVE_SIGH_RATIO = 1.6       # sigh-like breathing: tidal volume > night median × this
WAVE_PRESSURE_BIN = 0.5     # bin width of the pressure-event joint distribution (cmH2O)
WAVE_BIN_MIN_FRAC = 0.03    # minimum exposure share per pressure bin; below this it is
                            # Ramp drive-by, excluded from curve comparison
WAVE_CEILING_FRAC = 0.03    # dwell share near the ceiling to count as "clipped";
                            # below this is transient touch, not truncation
WAVE_REPORT_NIGHTS = 14     # nights feeding the waveform layer in --report
                            # (per-breath analysis is slow; capped)


def _smooth_signal(x, fs, win_s=WAVE_SMOOTH_S):
    """Hann-window moving average (zero phase, half-window transient at the front).
    Returns a float array the same length as the input."""
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x
    n = int(max(1, round(win_s * fs)))
    if n <= 1 or n > x.size:
        return x.copy()
    k = np.hanning(n)
    k = k / k.sum()
    return np.convolve(x, k, mode='same')


def _baseline(x, fs, win_s=60.0):
    """Slowly varying baseline (long-window moving average) preserving the DC
    component of the breathing waveform."""
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x
    n = int(max(1, round(win_s * fs)))
    if n <= 1 or n > x.size:
        return np.full_like(x, float(np.nanmean(x)) if x.size else 0.0)
    return np.convolve(x, np.ones(n) / n, mode='same')


def _flattening_index(insp):
    """Inspiratory flattening index FI: mid-segment max deviation from the
    start-end chord, relative to the peak.

    Over the "inspiration onset → peak" segment, fit the chord through the
    first and last points of the middle stretch (WAVE_FI_A~WAVE_FI_B) and
    measure the waveform's largest relative deviation from it. Rounded normal
    inspiratory peaks deviate a lot (high FI); plateau-like flow-limited
    waveforms hug the line (low FI). **High/low only means something compared
    within the same night/segment** — absolute values depend on signal
    bandwidth, smoothing window and mask type; never use as a cross-device
    threshold.
    """
    seg = np.asarray(insp, dtype=float)
    peak = float(seg.max()) if seg.size else 0.0
    if seg.size < 4 or not np.isfinite(peak) or peak <= 0:
        return float('nan')
    n = seg.size
    a = int(n * WAVE_FI_A)
    b = int(n * WAVE_FI_B)
    if b - a + 1 < 3:
        a, b = 0, n - 1
    mid = seg[a:b + 1]
    line = np.linspace(float(mid[0]), float(mid[-1]), mid.size)
    return float(np.max(np.abs(mid - line)) / peak)


def find_breaths(flow, fs):
    """Cut the flow curve into individual breaths; returns index arrays (peaks, troughs).

    Peaks = inspiratory peaks. Troughs = the most negative point between
    adjacent peaks (expiratory trough); if more than half a breath cycle of
    data remains after the last peak, one extra trough is appended so the last
    breath has an endpoint.
    """
    x = np.nan_to_num(np.asarray(flow, dtype=float), nan=0.0)
    if x.size < int(2 * fs):
        return np.array([], dtype=int), np.array([], dtype=int)
    xc = _smooth_signal(x - _baseline(x, fs), fs)
    p99 = float(np.percentile(xc, 99))
    prom = max(WAVE_PROM_FLOOR, WAVE_PROM_PCT * p99)
    peaks, _ = find_peaks(xc, distance=int(max(1, round(WAVE_PEAK_DIST_S * fs))), prominence=prom)
    troughs = []
    for k in range(peaks.size - 1):
        a, b = peaks[k], peaks[k + 1]
        troughs.append(a + int(np.argmin(xc[a:b + 1])))
    if peaks.size:
        mid = int(round(2.5 * fs))
        if peaks[-1] + mid < xc.size:
            troughs.append(peaks[-1] + int(np.argmin(xc[peaks[-1]:peaks[-1] + mid + 1])))
    return peaks, np.asarray(troughs, dtype=int)


def _breath_slice(flow):
    """Cut one breath from the flow: (inspiratory segment, full cycle, peak index).
    (None, None, -1) when out of bounds or too short."""
    x = flow
    pk = int(x.size) - 1
    if pk < 3:
        return None, None, -1
    i = pk
    while i > 0 and x[i] > 0:
        i -= 1
    insp = x[i:pk + 1]
    if insp.size < 3:
        return None, None, -1
    return insp, x, pk


def breathe(flow, fs=25.0):
    """Per-breath feature sequence.

    Each entry is a dict: time t (s, relative to the input array start),
    inspiratory time ti, expiratory time te, period T, tidal volume tv (positive
    integral, L), peak inspiratory flow pif, relative peak amplitude peaki,
    flattening index fi, plus the slice indices i0/ipk/i1. Tidal volume matches
    the device TidVol convention (see _volumes).
    """
    x = np.nan_to_num(np.asarray(flow, dtype=float), nan=0.0)
    peaks, troughs = find_breaths(x, fs)
    if peaks.size < 2:
        return []
    xc = _smooth_signal(x - _baseline(x, fs), fs)
    # trough → peak one-to-one: one fewer trough than peaks (last peak may lack one)
    out = []
    for k in range(peaks.size - 1):
        pk = peaks[k]
        nxt = peaks[k + 1]
        T = (nxt - pk) / fs
        if not (2.0 <= T <= 10.0):
            continue
        trough = pk
        while trough > 0 and xc[trough] > 0:
            trough -= 1
        insp = xc[trough:pk + 1]
        if insp.size < int(0.4 * fs):
            continue
        peak_val = float(insp.max())
        tv = float(np.trapezoid(np.clip(xc[pk:nxt], 0.0, None), dx=1.0 / fs))
        out.append({
            't': float(pk) / fs,
            'ti': (pk - trough) / fs,
            'te': (nxt - pk) / fs,
            'T': T,
            'tv': tv,
            'pif': peak_val,
            'fi': _flattening_index(insp),
            'i0': int(trough), 'ipk': int(pk), 'i1': int(nxt),
        })
    return out


def _volumes(flow, fs=25.0):
    """Per-breath tidal volume sequence (same convention as breathe), for tests
    and quick calls."""
    return [b['tv'] for b in breathe(flow, fs)]


def _sample_at(times, values, t_, mode='prev'):
    """Value at t_ on monotonic times. prev=nearest before, next=nearest after.
    NaN when out of range."""
    times = np.asarray(times, dtype=float)
    if times.size == 0 or not np.isfinite(t_):
        return float('nan')
    if mode == 'next':
        i = int(np.searchsorted(times, t_, side='left'))
    else:
        i = int(np.searchsorted(times, t_, side='right')) - 1
    if i < 0 or i >= times.size:
        return float('nan')
    return float(values[i])


def periodicity_fit(times, values, lo=WAVE_PERIOD_LO_S, hi=WAVE_PERIOD_HI_S, step=1.0):
    """Periodicity test of a tidal-volume series: per-period sinusoid fit, strongest period wins.

    Returns {corr2, period_s, mod_amp, n_cycles, n_breaths}. corr2 is the
    squared correlation of projecting the detrended tidal-volume series onto
    that period's sine/cosine basis (equivalent to least-squares R², but robust
    to uneven per-breath sampling).

    Why not autocorrelation/spectral peak share: real breath-to-breath
    variability is broadband (measured CV 30–40%), so autocorrelation at short
    20 s lags hits false peaks of 0.25–0.37, and spectral peak share gets
    diluted by slow drift (measured: an obviously periodic signal reported as
    0.6%). Sinusoid fitting is insensitive to both — synthetic calibration:
    no modulation ≈ 0.000, modulation depth (peak-trough/median) 0.5 ≈ 0.12,
    0.7 ≈ 0.21; measured real non-periodic nights ≈ 0.000–0.001.
    """
    times = np.asarray(times, dtype=float)
    values = np.asarray(values, dtype=float)
    m = np.isfinite(times) & np.isfinite(values)
    times, values = times[m], values[m]
    n = int(times.size)
    if n < 20 or (times[-1] - times[0]) < WAVE_PERIOD_MIN_S:
        return {'corr2': None, 'period_s': None, 'mod_amp': None,
                'n_cycles': None, 'n_breaths': n}
    dur = float(times[-1] - times[0])
    grid = np.arange(times[0], times[-1], 1.0)
    y = np.interp(grid, times, values)
    win = int(round(WAVE_DETREND_S))
    if win >= y.size:
        win = max(3, y.size // 2)
    trend = np.convolve(y, np.ones(win) / win, mode='same')
    y = y - trend
    y = y - float(np.median(values))
    ss = float(np.dot(y, y))
    if ss <= 0:
        return {'corr2': None, 'period_s': None, 'mod_amp': None,
                'n_cycles': None, 'n_breaths': n}
    tv_med = float(np.median(values))
    best = {'corr2': 0.0, 'period_s': None, 'mod_amp': None, 'n_cycles': None, 'n_breaths': n}
    for period in np.arange(lo, hi + step / 2, step):
        if dur / period < 5:            # fewer than 5 cycles cannot establish periodicity
            continue
        s = np.sin(2 * np.pi * grid / period)
        c = np.cos(2 * np.pi * grid / period)
        ds = math.sqrt(float(np.dot(s, s)) * ss)
        dc = math.sqrt(float(np.dot(c, c)) * ss)
        if ds <= 0 or dc <= 0:
            continue
        r2 = (float(np.dot(s, y)) / ds) ** 2 + (float(np.dot(c, y)) / dc) ** 2
        if r2 > best['corr2']:
            amp = None
            if tv_med > 0:
                coef, *_ = np.linalg.lstsq(np.vstack([s, c]).T, y, rcond=None)
                amp = float(2 * np.hypot(coef[0], coef[1]) / tv_med)
            best = {'corr2': float(r2), 'period_s': float(period), 'mod_amp': amp,
                    'n_cycles': float(dur / period), 'n_breaths': n}
    return best


def periodicity_verdict(corr2, period_s, covered_s,
                        min_corr2=WAVE_PERIOD_CORR2, weak_corr2=WAVE_PERIOD_WEAK):
    """Translate a periodicity fit into a verdict tier. covered_s is the therapy
    seconds covered by the series.

    Periods <40 s and >=40 s are reported separately: short-period oscillation
    is closer to treatment-emergent central events (TECSA) / high loop gain,
    long-period closer to classic Cheyne-Stokes respiration (heart failure
    related). **Neither is a diagnosis** — the device has no EEG, no
    thoracoabdominal effort, no position; formally declaring Cheyne-Stokes
    requires PSG with respiratory effort channels. All this tool can say is
    "the waveform layer shows periodic ventilatory instability; manual review
    is warranted".
    """
    if corr2 is None or period_s is None or covered_s < WAVE_PERIOD_MIN_S:
        return 'cover_too_short'
    if corr2 < weak_corr2:
        return 'no_periodic'
    tier = 'periodic_short_cycle' if period_s < 40.0 else 'periodic_long_cycle'
    return tier if corr2 >= min_corr2 else 'weak_' + tier


def cluster_events(event_times, gap_s=WAVE_CLUSTER_GAP_S, min_events=WAVE_CLUSTER_MIN):
    """Event clustering: consecutive groups with adjacent gaps <= gap_s form a cluster
    when they reach min_events.

    Clustering is the classic positional / REM-related OSA cue (single events
    interrupted by discrete arousals vs one sustained collapse). Only the
    temporal structure of clusters is reported; positions are never inferred
    from clusters — the device does not record position.
    """
    ts = sorted(float(x) for x in event_times if np.isfinite(x))
    clusters = []
    for x in ts:
        if clusters and x - clusters[-1][-1] <= gap_s:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    real = [c for c in clusters if len(c) >= min_events]
    return {
        'n_events': len(ts),
        'n_clusters': len(real),
        'n_events_in_clusters': int(sum(len(c) for c in real)),
        'cluster_frac': (sum(len(c) for c in real) / len(ts)) if ts else None,
        'longest': max((len(c) for c in real), default=0),
        'longest_span_s': max((c[-1] - c[0] for c in real), default=0.0),
        'clusters': real,
    }


def pressure_exposure(press, event_press, bin_w=WAVE_PRESSURE_BIN, ceiling=None):
    """Pressure–exposure–event joint distribution, in **breaths** as the exposure unit.

    Bin by bin_w how many inspiratory breaths dwell in each pressure bin and
    how many events fall in each bin, to inform pressure decisions: events
    piling up in low bins with high bins nearly clean = pressure headroom
    remains; events not decreasing in high bins = further increases have
    diminishing returns. Exposure counts breaths, not seconds — per-breath
    pressure comes from sampling the PLD pressure time axis, and converting to
    seconds assumes a constant sampling interval, which does not hold across
    concatenated segments.

    **APAP selection bias**: pressure is raised reactively to events/flow
    limitation, so dwelling in high bins is inherently correlated with events
    in the preceding minute; the "rates" here describe co-occurrence only, not
    a dose–response relationship.
    """
    press = np.asarray(press, dtype=float)
    press = press[np.isfinite(press)]
    if press.size == 0:
        return {'bins': [], 'n_breaths': 0, 'n_events': 0, 'delivered_p90': None}
    ev = np.asarray([p for p in np.asarray(event_press, dtype=float) if np.isfinite(p)])
    lo = math.floor(float(np.min(press)) / bin_w) * bin_w
    hi = math.ceil(float(np.max(press)) / bin_w) * bin_w
    edges = np.arange(lo, hi + bin_w / 2, bin_w)
    counts, _ = np.histogram(press, bins=edges)
    ev_counts, _ = np.histogram(ev, bins=edges) if ev.size else (np.zeros(len(edges) - 1), None)
    bins = []
    for b in range(len(edges) - 1):
        n_br = int(counts[b])
        n_ev = int(ev_counts[b])
        bins.append({
            'lo': float(edges[b]), 'hi': float(edges[b + 1]),
            'breaths': n_br,
            'frac': float(n_br / counts.sum()) if counts.sum() else None,
            'events': n_ev,
            'event_per_100_breaths': (100.0 * n_ev / n_br) if n_br else None,
        })
    press_max = float(np.max(press))
    # "dwelling at the ceiling" is judged against the device-set ceiling (not the
    # pooled peak): the set ceiling is the control boundary; the pooled peak is just
    # the highest single moment across nights. ceiling defaults to the pooled peak.
    ref = float(ceiling) if ceiling is not None else press_max
    return {'bins': bins, 'n_breaths': int(counts.sum()), 'n_events': int(ev.size),
            'press_median': float(np.median(press)), 'press_p95': float(np.percentile(press, 95)),
            'press_max': press_max, 'delivered_p90': float(np.percentile(press, 90)),
            'ceiling_ref': ref,
            'frac_at_ceiling': float((press >= ref - 0.5).mean())}


def summarize_breaths(breaths, press_times=None, press_vals=None, flow_t0=None):
    """Per-breath sequence → nightly waveform summary (resp rate / tidal volume /
    flattening-index quantiles / sigh-like breaths).

    FI is binned by the night's own quantiles (not literature absolute
    thresholds; see _flattening_index for why). Given the pressure time axis and
    flow_t0 (epoch seconds of the flow array start), each breath's pressure is
    also captured for the pressure–flatness curve.
    """
    if not breaths:
        return None
    t_ = np.array([b['t'] for b in breaths], dtype=float)
    tv = np.array([b['tv'] for b in breaths], dtype=float)
    fi = np.array([b['fi'] for b in breaths], dtype=float)
    T = np.array([b['T'] for b in breaths], dtype=float)
    ti = np.array([b['ti'] for b in breaths], dtype=float)
    fin = fi[np.isfinite(fi)]
    q10 = float(np.percentile(fin, 10)) if fin.size else float('nan')
    q25 = float(np.percentile(fin, 25)) if fin.size else float('nan')
    tv_med = float(np.median(tv)) if tv.size else float('nan')
    out = {
        'n_breaths': int(len(breaths)),
        'span_h': float(t_[-1] / 3600.0) if t_.size else 0.0,
        'rr_med': float(60.0 / np.median(T)) if T.size else float('nan'),
        'tv_med': tv_med,
        'tv_cv': float(np.std(tv) / np.mean(tv)) if tv.size and np.mean(tv) > 0 else float('nan'),
        'pif_med': float(np.median([b['pif'] for b in breaths])),
        'ti_med': float(np.median(ti)) if ti.size else float('nan'),
        'fi_med': float(np.median(fin)) if fin.size else float('nan'),
        'fi_p10': q10, 'fi_p25': q25,
        'frac_below_p10': float((fin < q10).mean()) if fin.size else float('nan'),
        'frac_below_p25': float((fin < q25).mean()) if fin.size else float('nan'),
        'n_sigh': int((tv > tv_med * WAVE_SIGH_RATIO).sum()) if tv.size and tv_med > 0 else 0,
        'sigh_per_h': None,
    }
    if out['span_h'] > 0:
        out['sigh_per_h'] = out['n_sigh'] / out['span_h']
    if press_times is not None and press_vals is not None and len(press_times) and flow_t0 is not None:
        # per-breath times are "relative to flow start"; the pressure time axis is
        # absolute epoch — convert first, then align
        pt = np.searchsorted(np.asarray(press_times, dtype=float),
                             t_ + float(flow_t0), side='right') - 1
        ok = (pt >= 0) & (pt < len(press_vals))
        out['breath_press'] = np.asarray(press_vals, dtype=float)[pt[ok]]
        out['breath_fi'] = fi[ok]
    else:
        out['breath_press'] = None
        out['breath_fi'] = None
    return out


def wave_features(breaths, press=None, press_fs=None, press_t0=None, event_records=None,
                  flow_t0=None):
    """Pack one night's per-breath series, pressure time axis and event table into
    waveform-layer metrics.

    ``breaths`` comes from ``breathe()`` with times relative to the flow array
    start; ``flow_t0`` is that start in epoch seconds — without it breath times
    cannot be mapped to absolute time and aligned with pressure (the two come
    from independent files of the same night with different start/end times).
    Pressure and events are optional: missing inputs leave the corresponding
    fields None without raising — the caller still gets a report, just one
    section shorter.
    """
    if not breaths:
        return None
    press_arr = np.asarray(press, dtype=float) if press is not None and len(press) else None
    press_times = None
    if press_arr is not None and press_fs and press_t0 is not None:
        press_times = float(press_t0) + np.arange(press_arr.size, dtype=float) / float(press_fs)
    agg = summarize_breaths(breaths, press_times, press_arr, flow_t0=flow_t0)
    if agg is None:
        return None
    tv_times = np.array([b['t'] for b in breaths], dtype=float)
    tv_series = np.array([b['tv'] for b in breaths], dtype=float)
    period = periodicity_fit(tv_times, tv_series)
    cl = cluster_events([r['time'] for r in (event_records or [])])
    agg.update({
        'period_s': period['period_s'], 'period_corr2': period['corr2'],
        'period_mod_amp': period['mod_amp'], 'period_n_cycles': period['n_cycles'],
        'period_verdict': periodicity_verdict(period['corr2'], period['period_s'],
                                              float(tv_times[-1] - tv_times[0])),
        'event_clusters': cl,
    })
    return agg


def night_wave(day_dir):
    """Read one night's BRP/PLD/EVE into waveform-layer metrics; None when data is
    insufficient."""
    brp = sorted(glob.glob(f"{day_dir}/*_BRP.edf"))
    if not brp:
        return None
    flow = _concat(brp, 'Flow')
    if flow.size < 60 * 25:
        return None
    fs = read_signal_fs(brp[0], 'Flow')[1] or 25.0
    breaths = breathe(flow, fs)
    if not breaths:
        return None
    pt = pf = None
    press = _concat(sorted(glob.glob(f"{day_dir}/*_PLD.edf")), 'Press')
    pfiles = sorted(glob.glob(f"{day_dir}/*_PLD.edf"))
    if press.size and pfiles:
        st = edf_start(pfiles[0])
        pf = read_signal_fs(pfiles[0], 'Press')[1]
        if st is not None and pf:
            pt = st.timestamp()
    fst = edf_start(brp[0])
    flow_t0 = fst.timestamp() if fst is not None else None
    ivs, _ = _therapy_intervals(day_dir)
    ev, _ = _event_records(day_dir, ivs)
    return wave_features(breaths, press, pf, pt, ev, flow_t0=flow_t0)


def pressure_vs_fi(wave, bin_w=WAVE_PRESSURE_BIN):
    """Bin per-breath (pressure, flattening index) into a pressure–flatness curve for
    reading pressure headroom.

    Reading: if FI clearly recovers as pressure rises (less limitation) → the
    airway responds to pressure; raising the floor/ceiling may help. If FI is
    basically flat across bins → the mechanism does not respond to pressure;
    more pressure has diminishing returns. Compare only within the same
    night/segment; APAP selection bias (pressure is raised in reaction to
    events) means this curve is not a dose–response experiment.
    """
    if not wave or wave.get('breath_press') is None or wave.get('breath_fi') is None:
        return None
    p = np.asarray(wave['breath_press'], dtype=float)
    f = np.asarray(wave['breath_fi'], dtype=float)
    m = np.isfinite(p) & np.isfinite(f)
    p, f = p[m], f[m]
    if p.size < 50:
        return None
    lo = math.floor(float(p.min()) / bin_w) * bin_w
    hi = math.ceil(float(p.max()) / bin_w) * bin_w
    edges = np.arange(lo, hi + bin_w / 2, bin_w)
    idx = np.clip(np.digitize(p, edges) - 1, 0, len(edges) - 2)
    bins = []
    for b in range(len(edges) - 1):
        sel = f[idx == b]
        if sel.size < 20:
            continue
        bins.append({'lo': float(edges[b]), 'hi': float(edges[b + 1]), 'n': int(sel.size),
                     'fi_med': float(np.median(sel)), 'fi_p25': float(np.percentile(sel, 25))})
    if len(bins) < 2:
        return None
    xs = np.array([b['lo'] + bin_w / 2 for b in bins])
    ys = np.array([b['fi_med'] for b in bins])
    ws = np.array([b['n'] for b in bins], dtype=float)
    slope = float(np.polyfit(xs, ys, 1, w=np.sqrt(ws))[0]) if len(bins) >= 2 else float('nan')
    return {'bins': bins, 'slope_per_cmH2O': slope}


def _load_nights(days):
    """Night directory list → [(date, night_summary, wave)]; wave is None when the
    waveform layer lacks data."""
    out = []
    for d in days:
        date = os.path.basename(d)
        if not os.path.isdir(d):
            continue
        row = night_summary(d)
        if row['usage_h'] <= 0.01:
            continue
        try:
            wave = night_wave(d)
        except (OSError, ValueError, IndexError, KeyError, np.linalg.LinAlgError):
            wave = None
        out.append((date, row, wave))
    return out


def _wave_pool(nights):
    """Pool multiple nights' (pressure, FI) pairs and event pressures into a
    cross-night combined curve."""
    press, fi, ev_press = [], [], []
    for _date, row, wave in nights:
        if not wave:
            continue
        if wave.get('breath_press') is not None and wave.get('breath_fi') is not None:
            press.append(np.asarray(wave['breath_press'], dtype=float))
            fi.append(np.asarray(wave['breath_fi'], dtype=float))
        ev_press += [p for _t, p, _lab in align_events_pressure(f"{ROOT}/{_date}")]
    if not press:
        return None
    return {'press': np.concatenate(press), 'fi': np.concatenate(fi),
            'event_press': np.asarray(ev_press, dtype=float) if ev_press else np.array([])}


def _pressure_fi_bins(press, fi, bin_w=WAVE_PRESSURE_BIN, min_frac=WAVE_BIN_MIN_FRAC):
    """(pressure, FI) per-breath samples → binned median curve + weighted slope.

    Only bins with sufficient exposure (>= min_frac of all breaths) participate.
    Reason: on its way from a start pressure of 5 up to therapeutic pressure,
    AutoSet leaves hundreds of "Ramp drive-by" breaths in low bins; comparing
    them as "low-pressure therapy" against fully loaded high bins measures
    "ramp vs therapy", not a pressure dose effect.
    """
    press = np.asarray(press, dtype=float)
    fi = np.asarray(fi, dtype=float)
    m = np.isfinite(press) & np.isfinite(fi)
    press, fi = press[m], fi[m]
    if press.size < 50:
        return None
    total = int(press.size)
    lo = math.floor(float(press.min()) / bin_w) * bin_w
    hi = math.ceil(float(press.max()) / bin_w) * bin_w
    edges = np.arange(lo, hi + bin_w / 2, bin_w)
    idx = np.clip(np.digitize(press, edges) - 1, 0, len(edges) - 2)
    bins = []
    for b in range(len(edges) - 1):
        sel = fi[idx == b]
        if sel.size < max(20, min_frac * total):
            continue
        bins.append({'lo': float(edges[b]), 'hi': float(edges[b + 1]), 'n': int(sel.size),
                     'fi_med': float(np.median(sel)), 'fi_p25': float(np.percentile(sel, 25))})
    if len(bins) < 2:
        return None
    xs = np.array([b['lo'] + bin_w / 2 for b in bins])
    ys = np.array([b['fi_med'] for b in bins])
    ws = np.array([b['n'] for b in bins], dtype=float)
    slope = float(np.polyfit(xs, ys, 1, w=np.sqrt(ws))[0])
    # Remaining headroom: median FI difference between the lowest three and the
    # highest three bins. A single whole-range linear slope averages "steep low
    # segment + flat high segment" into one positive slope that reads as
    # "responsive throughout", when the actual question is **how much is still
    # gainable above the current prescription range**.
    k = 3
    gain = None
    if len(bins) >= 2 * k:
        lo_top = float(np.median([b['fi_med'] for b in bins[:k]]))
        hi_top = float(np.median([b['fi_med'] for b in bins[-k:]]))
        gain = hi_top - lo_top
    return {'bins': bins, 'slope_per_cmH2O': slope, 'gain_lo_to_hi': gain,
            'gain_span_cmH2O': (float(bins[-1]['lo'] + bin_w - bins[0]['lo'])) if len(bins) >= 2 * k else None,
            'therapy_lo': float(bins[0]['lo']), 'therapy_hi': float(bins[-1]['hi'])}


def wave_verdict(nights, pool):
    """Translate waveform-layer metrics into auditable reading points (no diagnoses,
    no pressure values)."""
    out = {'points': [], 'flags': []}
    if not nights:
        return out
    # Flattening-index overview
    fis = [w['fi_med'] for _d, _r, w in nights if w and w.get('fi_med') is not None
           and np.isfinite(w['fi_med'])]
    if fis:
        out['points'].append(
            t('wv_fi_summary', med=f'{float(np.median(fis)):.3f}', n=len(fis)))
    # Clusters
    cl_frac, cl_n, cl_nights = [], 0, 0
    for _d, _r, w in nights:
        if not w:
            continue
        c = w['event_clusters']
        cl_n += c['n_clusters']
        if c['n_events']:
            cl_nights += 1
            cl_frac.append(c['cluster_frac'])
    if cl_frac:
        out['points'].append(
            t('wv_cluster', nights=cl_nights, clusters=cl_n, min_ev=WAVE_CLUSTER_MIN,
              gap_min=f'{WAVE_CLUSTER_GAP_S/60:.0f}', pct=f'{float(np.median(cl_frac))*100:.0f}'))
        if float(np.median(cl_frac)) >= 0.30:
            out['flags'].append('cluster')
    # Periodicity
    per = [w for _d, _r, w in nights if w and w.get('period_verdict') not in (None, 'cover_too_short')]
    flagged = [w for w in per if w['period_verdict'].startswith('periodic_')]
    weak = [w for w in per if w['period_verdict'].startswith('weak_')]
    if per and not flagged:
        note = t('wv_period_none', n=len(per))
        if weak:
            note += t('wv_period_weak_tail', n=len(weak))
        out['points'].append(note + t('wv_period_none_tail'))
    elif flagged:
        wk = [w for w in flagged if w['period_verdict'].startswith('periodic_short_cycle')]
        out['points'].append(
            t('wv_period_flagged', flagged=len(flagged), total=len(per),
              corr2=WAVE_PERIOD_CORR2, period=f'{float(np.median([w["period_s"] for w in flagged])):.0f}',
              n_short=len(wk)))
        out['flags'].append('periodic')
    # Pressure–flatness
    if pool is not None:
        curve = _pressure_fi_bins(pool['press'], pool['fi'])
        if curve:
            slope, bins = curve['slope_per_cmH2O'], curve['bins']
            lo_bin, hi_bin = bins[0], bins[-1]
            out['points'].append(
                t('wv_curve_base', t_lo=f'{curve["therapy_lo"]:.1f}', t_hi=f'{curve["therapy_hi"]:.1f}',
                  n_bins=len(bins), lo_p=f'{lo_bin["lo"]:.1f}', lo_fi=f'{lo_bin["fi_med"]:.3f}',
                  hi_p=f'{hi_bin["lo"]:.1f}', hi_fi=f'{hi_bin["fi_med"]:.3f}',
                  slope=f'{slope:+.4f}'))
            out['slope'] = slope
            out['gain'] = curve.get('gain_lo_to_hi')
            gain = curve.get('gain_lo_to_hi')
            span = curve.get('gain_span_cmH2O')
            gain_txt = (t('wv_gain_txt', span=f'{span:.1f}', gain=f'{gain:+.3f}')
                        if gain is not None and span else '')
            if slope < -0.002:
                out['points'].append(t('wv_curve_negative'))
                out['flags'].append('pressure_adverse')
            elif gain is not None and gain < 0.02:
                out['points'].append(t('wv_curve_gain_flat', gain_txt=gain_txt))
                out['flags'].append('pressure_flat')
            else:
                # Three further shapes: flat middle (gain exhausted), recovering high
                # segment (still wants more pressure), monotonic rise throughout
                k = 3
                mid = curve['bins'][k:-k] if len(curve['bins']) >= 2 * k else []
                tail_gain = None
                if mid:
                    mid_lo = float(np.median([b['fi_med'] for b in mid[:k]] or [np.nan]))
                    mid_hi = float(np.median([b['fi_med'] for b in mid[-k:]] or [np.nan]))
                    tail_gain = mid_hi - mid_lo
                ys_all = [b['fi_med'] for b in bins]
                lo_i = int(np.argmin(ys_all))
                turn_up = (lo_i < len(bins) - 2
                           and ys_all[-1] - ys_all[lo_i] > 0.015)
                if turn_up:
                    out['points'].append(
                        t('wv_curve_ushape', gain_txt=gain_txt,
                          p_min=f'{bins[lo_i]["lo"] + WAVE_PRESSURE_BIN/2:.1f}',
                          rise=f'{ys_all[-1] - ys_all[lo_i]:+.3f}'))
                    out['flags'].append('pressure_still_climbing')
                elif tail_gain is not None and tail_gain < 0.02:
                    out['points'].append(
                        t('wv_curve_plateau', gain_txt=gain_txt, tail_gain=f'{tail_gain:+.3f}'))
                    out['flags'].append('pressure_plateau')
                else:
                    out['points'].append(t('wv_curve_responsive', gain_txt=gain_txt))
                    out['flags'].append('pressure_responsive')
            if pool['event_press'].size:
                ep = pool['event_press']
                out['points'].append(
                    t('wv_event_press', med=f'{float(np.median(ep)):.1f}',
                      p14=f'{float((ep >= 14).mean())*100:.0f}',
                      p15=f'{float((ep >= 15).mean())*100:.0f}'))
    return out


def pressure_exposure_verdict(bins, delivered_p90, press_max, ceiling_frac,
                              set_max=None, min_breaths=200):
    """Pressure-exposure–event joint distribution → reading of pressure headroom.

    The split uses the **actually delivered** high segment (above P90), not the
    ceiling in settings — AutoSet often runs far below the ceiling, and cutting
    at the ceiling would leave the high segment with only a few hundred breaths,
    all ratios drowned in noise.

    APAP selection bias: the device adjusts pressure reactively to events/flow
    limitation, so "few events in high bins" may mean pressure works — or that
    the device simply never dwelt there (insufficient exposure). Only bins with
    sufficient exposure participate, and the two kinds of evidence are reported
    separately.
    """
    out = {'points': []}
    if delivered_p90 is None:
        return out
    valid = [b for b in bins if b['breaths'] >= min_breaths]
    if not valid:
        return out
    hi_bins = [b for b in valid if b['lo'] + WAVE_PRESSURE_BIN / 2 >= delivered_p90]
    lo_bins = [b for b in valid if b['lo'] + WAVE_PRESSURE_BIN / 2 < delivered_p90]
    hi_br = sum(b['breaths'] for b in hi_bins)
    lo_br = sum(b['breaths'] for b in lo_bins)
    hi_ev = sum(b['events'] for b in hi_bins)
    lo_ev = sum(b['events'] for b in lo_bins)
    if hi_br and lo_br:
        hi_rate = 100.0 * hi_ev / hi_br
        lo_rate = 100.0 * lo_ev / lo_br
        out['points'].append(
            t('pev_split', p90=f'{delivered_p90:.1f}', lo_rate=f'{lo_rate:.1f}',
              hi_rate=f'{hi_rate:.1f}', lo_br=lo_br, hi_br=hi_br))
        out['lo_rate'] = lo_rate
        out['hi_rate'] = hi_rate
        out['flag'] = 'confounded'
    out['points'].append(
        t('pev_delivered', med=f'{np.median([b["lo"] for b in valid]):.1f}',
          p90=f'{delivered_p90:.1f}', mx=f'{press_max:.1f}',
          frac=f'{ceiling_frac*100:.1f}'))
    if set_max is not None:
        set_max = float(set_max)
        # Peak touching the ceiling != the ceiling binding: look at how long it
        # **dwelt** there. Transient touches are normal control behavior, not
        # "clipped"; sustained dwell is the ceiling limiting therapy.
        if press_max < set_max - 0.5:
            out['points'].append(t('pev_not_binding', set_max=f'{set_max:.1f}',
                                   press_max=f'{press_max:.1f}'))
            out['flag_ceiling'] = 'not_binding'
        elif ceiling_frac >= WAVE_CEILING_FRAC:
            out['points'].append(t('pev_binding', set_max=f'{set_max:.1f}',
                                   frac=f'{ceiling_frac*100:.1f}'))
            out['flag_ceiling'] = 'binding'
        else:
            out['points'].append(t('pev_touch_only', set_max=f'{set_max:.1f}',
                                   frac=f'{ceiling_frac*100:.1f}'))
            out['flag_ceiling'] = 'touch_only'
    return out


def chart_wave_pressure(day_dir, path, plt):
    """One night: pressure curve + inspiratory peaks (colored by FI). Limited breaths
    render cooler."""
    times, press, pfs = _pld_pressure_timeline(day_dir)
    if times is None:
        return None
    brp = sorted(glob.glob(f"{day_dir}/*_BRP.edf"))
    flow = _concat(brp, 'Flow')
    ffs = read_signal_fs(brp[0], 'Flow')[1] or 25.0
    breaths = breathe(flow, ffs)
    if not breaths:
        return None
    st = edf_start(brp[0])
    t0 = st.timestamp() if st else times[0]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 5.4), sharex=True, height_ratios=[3, 1.6])
    ax1.plot((times - t0) / 3600.0, press, color='#4c72b0', lw=0.8)
    for tb, _p, _lab in align_events_pressure(day_dir):
        ax1.axvline((tb - t0) / 3600.0, color='#c44e52', alpha=0.35, lw=0.8)
    ax1.set_ylabel(t('axis_press_cmh2o'))
    ax1.set_title(t('chart_wp_title', date=os.path.basename(day_dir)))
    bt = np.array([(b['ipk'] / ffs) / 3600.0 for b in breaths])
    bfi = np.array([b['fi'] for b in breaths], dtype=float)
    ok = np.isfinite(bfi)
    if ok.any():
        sc = ax2.scatter(bt[ok], bfi[ok], s=4, c=bfi[ok], cmap='RdYlBu', vmin=0, vmax=0.35)
        fig.colorbar(sc, ax=ax2, label=t('label_fi'))
    if ok.any() and ok.sum() >= 20:
        q10 = float(np.percentile(bfi[ok], 10))
        ax2.axhline(q10, ls='--', color='#4c72b0', lw=1,
                    label=t('chart_wp_p10_legend', q10=f'{q10:.3f}'))
        ax2.legend(fontsize=8, loc='lower right')
    ax2.set_ylabel(t('axis_fi')); ax2.set_xlabel(t('axis_hours_since_start'))
    ax2.set_title(t('chart_wp_fi_title'), fontsize=9.5)
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
    return path


def chart_pressure_fi_curve(pool, path, plt, event_press=None):
    """Cross-night pooled: pressure bins vs median FI + event-pressure distribution."""
    curve = _pressure_fi_bins(pool['press'], pool['fi'])
    if not curve:
        return None
    bins = curve['bins']
    fig, ax = plt.subplots(figsize=(8, 4.4))
    xs = [b['lo'] + WAVE_PRESSURE_BIN / 2 for b in bins]
    ys = [b['fi_med'] for b in bins]
    y25 = [b['fi_p25'] for b in bins]
    ax.plot(xs, ys, 'o-', color='#4c72b0', label=t('legend_fi_med'))
    ax.fill_between(xs, y25, ys, color='#4c72b0', alpha=0.16, label=t('legend_p25_med'))
    ax.set_xlabel(t('axis_insp_press')); ax.set_ylabel(t('axis_fi_limited'))
    ax.set_xlim(min(xs) - 1.0, max(xs) + 1.0)
    title = t('chart_pf_title', n=sum(b["n"] for b in bins))
    sl = curve['slope_per_cmH2O']
    ax.set_title(title + '\n' + t('chart_pf_slope', slope=f'{sl:+.4f}')
                 + t('chart_pf_bias_note'), fontsize=9.5)
    if event_press is not None and np.size(event_press):
        ax2 = ax.twinx()
        ax2.hist(event_press, bins=np.arange(4, 20.5, 0.5), color='#c44e52', alpha=0.28)
        ax2.set_ylabel(t('axis_event_count'), color='#c44e52')
        ax2.tick_params(axis='y', colors='#c44e52')
    ax.legend(fontsize=8, loc='lower right'); fig.tight_layout()
    fig.savefig(path, dpi=110); plt.close(fig)
    return path


def chart_cluster_timeline(nights, path, plt):
    """Event–time map: one row per night, x = hours since therapy start, red = in-cluster."""
    rows = []
    for date, _row, wave in nights:
        day_dir = f"{ROOT}/{date}"
        s0, _ = _session_span(day_dir)
        if s0 is None:
            continue
        ivs, _meta = _therapy_intervals(day_dir)
        ev, _ = _event_records(day_dir, ivs)
        if not ev:
            continue
        cl = cluster_events([e['time'] for e in ev])
        in_cl = set()
        for c in cl['clusters']:
            in_cl.update(round(x) for x in c)
        rows.append((date, [[(e['time'] - s0) / 3600.0, e['kind'], round(e['time']) in in_cl]
                            for e in ev]))
    if not rows:
        return None
    fig, ax = plt.subplots(figsize=(10, max(2.4, 0.42 * len(rows) + 1.2)))
    for i, (_date, evs) in enumerate(rows):
        for h, kind, incl in evs:
            if h < 0 or h > 12:
                continue
            color = '#c44e52' if incl else '#8c8c8c'
            marker = {'oa': 'o', 'ca': '^', 'hyp': 's', 'ua': 'x'}.get(kind, '.')
            ax.scatter(h, i, s=26, c=color, marker=marker, alpha=0.85, zorder=3)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([d[4:] for d, _ in rows], fontsize=8)
    ax.set_xlabel(t('axis_hours_since_first'))
    # x axis clipped to the P99 of event times (some nights have multiple therapy
    # segments; tail-segment events would stretch the axis to 12h and squash the body)
    hs = [h for _d, e in rows for h, _k, _c in e if 0 <= h <= 12]
    if hs:
        ax.set_xlim(0, max(6.0, min(12.0, float(np.percentile(hs, 99)) + 0.5)))
    ax.axvline(6.0, color='#999999', ls=':', lw=1)
    ax.text(6.05, len(rows) - 0.5, '6h', color='#999999', fontsize=7, va='top')
    ax.set_title(t('chart_ct_title'), fontsize=9.5)
    ax.grid(axis='x', alpha=0.25)
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
    return path


def cmd_wave(days=None, n_nights=14):
    """Breath-by-breath flow waveform analysis: event clustering / periodic breathing /
    pressure-flatness curve."""
    if days is None:
        all_days = sorted(d for d in glob.glob(f"{ROOT}/*") if os.path.isdir(d))
        days = all_days[-n_nights:]
    nights = _load_nights(days)
    if not nights:
        print(t('wave_no_nights', root=ROOT))
        return
    print(t('wave_header', n=len(nights)))
    print(t('wave_range', d0=nights[0][0], d1=nights[-1][0]) + '\n')
    print(t('wave_table_header'))
    print("-" * 95)
    for date, _row, wave in nights:
        if not wave:
            print(t('wave_row_skip', date=date, dash='—'))
            continue
        c = wave['event_clusters']
        per = wave['period_s'] or 0
        c2 = wave['period_corr2'] if wave['period_corr2'] is not None else 0
        print(t('wave_table_row', date=date, breaths=wave['n_breaths'],
                rr=f"{wave['rr_med']:.1f}", tv=f"{wave['tv_med']:.3f}",
                cv=f"{wave['tv_cv']*100:.0f}", fi=f"{wave['fi_med']:.3f}",
                ev=c['n_events'], cl=c['n_clusters'],
                clpct=f"{(c['cluster_frac'] or 0)*100:.0f}",
                per=f"{per:.0f}", c2=f"{c2:.3f}", sigh=f"{wave['sigh_per_h'] or 0:.1f}"))
    pool = _wave_pool(nights)
    print('\n' + t('wave_verdict_header'))
    # The feedback check comes before all pressure metrics: the event-rate ratios
    # below can only be read correctly once it is on the table
    resp = event_pressure_response([f"{ROOT}/{d}" for d, _r, _w in nights])
    if resp:
        tail = (t('wave_feedback_confirmed')
                if resp['ev_rise_frac'] > resp['ctrl_rise_frac'] + 0.1 else
                t('wave_feedback_not_confirmed'))
        print('· ' + t('wave_feedback', n=resp['n_events'], med=f"{resp['ev_median']:+.2f}",
                       rise=f"{resp['ev_rise_frac']*100:.0f}", fall=f"{resp['ev_fall_frac']*100:.0f}",
                       ctrl_med=f"{resp['ctrl_median']:+.2f}",
                       ctrl_rise=f"{resp['ctrl_rise_frac']*100:.0f}") + tail)
    verdict = wave_verdict(nights, pool)
    for p in verdict['points']:
        print(f"· {p}")
    # Exposure and event distribution near the device ceiling (bounded by the recorded setting)
    pe = _pressure_exposure_for(pool, configured_max_press())
    if pe:
        print()
        for p in pe['points']:
            print(f"· {p}")
        # Only one piece of pressure evidence is clean: the FI curve (background
        # limitation compared across pressures). Event-rate ratios are contaminated
        # by APAP's pressurization feedback and take no part in conclusions.
        #
        # The curve shape decides "which end to raise": a U/J shape (bottom mid-range,
        # right end still climbing) says more pressure is gainable and the low segment
        # is already near the optimum — raise the ceiling, not the floor. Monotonic or
        # flat curves are when the floor comes into play. Conflating them gives
        # opposite advice.
        gain = verdict.get('gain')
        flags = verdict.get('flags', [])
        ceiling_binding = (pe.get('flag_ceiling') == 'binding')
        if gain is not None:
            if 'pressure_still_climbing' in flags:
                tail = (t('wave_merge_tail_binding') if ceiling_binding
                        else t('wave_merge_tail_not_binding'))
                print('· ' + t('wave_merge_climbing', gain=f'{gain:+.3f}') + tail
                      + t('wave_merge_disclaimer'))
            elif gain < 0.02:
                print('· ' + t('wave_merge_flat'))
            else:
                print('· ' + t('wave_merge_responsive', gain=f'{gain:+.3f}'))
    plt = _try_mpl()
    if plt:
        os.makedirs(REPORT_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = []
        for tag, fn in [('pressure_fi', lambda p: chart_pressure_fi_curve(pool, p, plt, pool['event_press'])),
                        ('cluster_timeline', lambda p: chart_cluster_timeline(nights, p, plt))]:
            pth = f"{REPORT_DIR}/{stamp}_{tag}.png"
            try:
                if fn(pth):
                    out.append(os.path.basename(pth))
            except Exception as e:
                print(t('msg_chart_fail', tag=tag, err=e))
        if out:
            print('\n' + t('msg_charts_saved', names='  '.join(out), dir=REPORT_DIR))
    return verdict


def _wave_snapshot(nights):
    """Waveform-layer snapshot: drops the long per-breath arrays (breath_press/
    breath_fi can reach tens of thousands of points), keeps summaries only."""
    out = []
    for date, _row, wave in nights:
        if not wave:
            continue
        item = {'date': date}
        for k, v in wave.items():
            if k in ('breath_press', 'breath_fi'):
                continue
            if k == 'event_clusters':
                item['event_clusters'] = {kk: vv for kk, vv in v.items() if kk != 'clusters'}
            else:
                item[k] = v
        out.append(item)
    return out


def event_pressure_response(day_dirs, lookahead_s=120.0, control_per_night=30, seed=0):
    """Does the device raise pressure after events — verifying APAP reactive
    pressurization (the precondition for reading every other pressure metric).

    For each event take the pressure at onset minus the pressure lookahead_s
    later; then sample the same number of random time points across the same
    nights as controls. If post-event pressurization clearly exceeds random
    points, the device does react to events — and then **any "high pressure <->
    many events" correlation is the echo of this feedback loop**, never readable
    as "pressure does not help" or "pressure causes events".

    Returns {n_events, ev_median, ev_rise_frac, n_control, ctrl_median, ctrl_rise_frac}.
    """
    rng = np.random.default_rng(seed)
    ev_d, ctrl_d = [], []
    for day_dir in day_dirs:
        times, press, _fs = _pld_pressure_timeline(day_dir)
        if times is None or times.size < 10:
            continue
        ivs, _m = _therapy_intervals(day_dir)
        ev, _m2 = _event_records(day_dir, ivs)
        for e in ev:
            before = _sample_at(times, press, e['time'])
            after = _sample_at(times, press, e['time'] + lookahead_s)
            if np.isfinite(before) and np.isfinite(after):
                ev_d.append(after - before)
        for _ in range(control_per_night):
            x = float(rng.uniform(times[0], times[-1] - lookahead_s))
            before = _sample_at(times, press, x)
            after = _sample_at(times, press, x + lookahead_s)
            if np.isfinite(before) and np.isfinite(after):
                ctrl_d.append(after - before)
    if not ev_d:
        return None
    ev_d = np.asarray(ev_d); ctrl_d = np.asarray(ctrl_d)
    return {
        'n_events': int(ev_d.size), 'ev_median': float(np.median(ev_d)),
        'ev_rise_frac': float((ev_d > 0.5).mean()), 'ev_fall_frac': float((ev_d < -0.5).mean()),
        'n_control': int(ctrl_d.size),
        'ctrl_median': float(np.median(ctrl_d)) if ctrl_d.size else None,
        'ctrl_rise_frac': float((ctrl_d > 0.5).mean()) if ctrl_d.size else None,
    }


def configured_max_press():
    """The device ceiling recorded in the tuning log (last entry); None when unreadable.

    The ceiling-truncation reading (peak vs set ceiling, dwell share) depends on
    it; passing None silently skips that section — report and --wave must both
    take it from here, never keep private copies."""
    logobj = load_tuning_log()
    if not logobj:
        return None
    entries = sorted(logobj.get('log', []), key=lambda e: e.get('since', ''))
    if not entries:
        return None
    return entries[-1].get('max_press')


def _pressure_exposure_for(pool, max_press):
    """Pressure-exposure–event joint distribution from the pooled pool."""
    if pool is None or pool['press'].size == 0:
        return None
    if max_press is None:
        max_press = configured_max_press()
    ex = pressure_exposure(pool['press'], pool['event_press'], ceiling=max_press)
    if not ex['bins'] or ex['delivered_p90'] is None:
        return None
    return pressure_exposure_verdict(ex['bins'], ex['delivered_p90'], ex['press_max'],
                                     ex['frac_at_ceiling'], set_max=max_press)


def clinical_assessment(rows):
    """Turn analyzable therapy records into auditable screening conclusions and
    escalate-to-clinic cues.

    Deliberately outputs no disease diagnosis and no pressure advice: device
    events are not PSG annotations and usage time is not sleep time. Every
    conclusion carries traceable numbers for the sleep specialist to review.
    """
    if not rows:
        return {'level': t('assess_level_insufficient'),
                'summary': t('assess_summary_insufficient'),
                'findings': [], 'review_actions': []}
    n = len(rows)
    rrei = np.asarray([r['residual_rei'] for r in rows], float)
    oai = np.asarray([r['oai'] for r in rows], float)
    cai = np.asarray([r['cai'] for r in rows], float)
    usage = np.asarray([r['usage_h'] for r in rows], float)
    med_rei = float(np.nanmedian(rrei)); med_oai = float(np.nanmedian(oai)); med_cai = float(np.nanmedian(cai))
    adequate_pct = float((usage >= COMPLIANCE_H).mean() * 100)
    high_rei_pct = float((rrei >= RESIDUAL_REI_REVIEW).mean() * 100)
    central_dominant_pct = float(((cai >= CENTRAL_REVIEW_CAI) & (cai >= oai)).mean() * 100)
    findings = [
        {'name': t('assess_finding_rei_name'), 'value': med_rei,
         'text': t('assess_finding_rei_text', n=n, med=f'{med_rei:.1f}')},
        {'name': t('assess_finding_exposure_name'), 'value': adequate_pct,
         'text': t('assess_finding_exposure_text', h=f'{COMPLIANCE_H:.0f}',
                   pct=f'{adequate_pct:.0f}', k=int((usage >= COMPLIANCE_H).sum()), n=n)},
    ]
    actions = []
    if med_rei >= RESIDUAL_REI_REVIEW or high_rei_pct >= 30:
        level = t('assess_level_specialist')
        actions.append(t('assess_action_rei_high'))
    elif med_rei >= RESIDUAL_REI_TARGET:
        level = t('assess_level_followup')
        actions.append(t('assess_action_rei_target'))
    else:
        level = t('assess_level_near_target')
        actions.append(t('assess_action_near_target'))
    if med_cai >= CENTRAL_REVIEW_CAI or central_dominant_pct >= 20:
        findings.append({'name': t('assess_finding_central_name'), 'value': med_cai,
                         'text': t('assess_finding_central_high', med=f'{med_cai:.1f}',
                                   pct=f'{central_dominant_pct:.0f}',
                                   c=f'{CENTRAL_REVIEW_CAI:.0f}')})
        actions.append(t('assess_action_central'))
    else:
        findings.append({'name': t('assess_finding_central_name'), 'value': med_cai,
                         'text': t('assess_finding_central_low', med=f'{med_cai:.1f}',
                                   c=f'{CENTRAL_REVIEW_CAI:.0f}')})
    sad_rows = [r for r in rows if r.get('spo2_src') == 'SAD' and not _nan(r.get('spo2_t90_pct'))]
    if sad_rows:
        t90 = float(np.nanmedian([r['spo2_t90_pct'] for r in sad_rows]))
        below88 = float(np.nanmedian([r['spo2_below88_min'] for r in sad_rows]))
        findings.append({'name': t('assess_finding_spo2_name'), 'value': t90,
                         'text': t('assess_finding_spo2_text', n=len(sad_rows),
                                   t90=f'{t90:.1f}', b88=f'{below88:.1f}')})
        if t90 >= 5 or below88 >= 5:
            actions.append(t('assess_action_spo2'))
    else:
        findings.append({'name': t('assess_finding_spo2_name'), 'value': None,
                         'text': t('assess_finding_spo2_none')})
    return {'level': level, 'summary': t('assess_summary_normal'),
            'findings': findings, 'review_actions': actions,
            'metrics': {'nights': n, 'residual_rei_med': med_rei, 'oai_med': med_oai,
                        'cai_med': med_cai, 'adequate_use_pct': adequate_pct,
                        'residual_rei_ge10_pct': high_rei_pct,
                        'central_dominant_pct': central_dominant_pct}}


def _agg(seg, k):
    """mean/median/IQR/CV%/min/max of one metric within a segment."""
    v = np.array([r[k] for r in seg], float); v = v[~np.isnan(v)]
    if not len(v):
        return {'mean': None, 'med': None, 'iqr': None, 'cv': None, 'min': None, 'max': None, 'n': 0}
    mean = float(v.mean())
    return {'mean': mean, 'med': float(np.median(v)),
                'iqr': float(np.percentile(v, 75) - np.percentile(v, 25)),
                'cv': float(v.std(ddof=0) / mean * 100) if mean else None,
                'min': float(v.min()), 'max': float(v.max()), 'n': len(v)}


_STAT_KEYS = ['usage_h', 'ahi', 'oai', 'cai', 'hi', 'press_med', 'press_95',
              'leak_95', 'flowlim_95', 'snore_95', 'resprate_med', 'tidvol_med', 'minvent_med']


def seg_stats(seg):
    st = {k: _agg(seg, k) for k in _STAT_KEYS}
    st['n'] = len(seg)
    st['n_analyzable'] = sum(1 for r in seg if r.get('analyzable'))
    return st


def _clean(o):
    """NaN -> None so JSON stays valid and cross-tool readable."""
    if isinstance(o, float) and math.isnan(o): return None
    if isinstance(o, dict): return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list): return [_clean(x) for x in o]
    return o


def load_tuning_log():
    if not os.path.exists(TUNING_LOG):
        return None
    return json.load(open(TUNING_LOG, encoding="utf-8"))


def segment_nights(rows, log):
    """Segment rows by tuning-log `since` dates → [(entry, [rows...]), ...]; segments
    without data are skipped."""
    log_sorted = sorted(log, key=lambda e: e["since"])
    segs = []
    for i, e in enumerate(log_sorted):
        start = e["since"]
        end = log_sorted[i + 1]["since"] if i + 1 < len(log_sorted) else "99999999"
        seg = [r for r in rows if start <= r["date"] < end]
        if seg:
            segs.append((e, seg))
    return segs


def _assign_segments(rows, log):
    """Per-night segment label (used for chart coloring)."""
    ls = sorted(log, key=lambda e: e["since"])
    def seg_of(d):
        lab = '?'
        for e in ls:
            if d >= e["since"]:
                lab = e.get("label", e["since"])
        return lab
    return [seg_of(r["date"]) for r in rows]


def _try_mpl():
    """Configured pyplot with CJK-capable fonts; None when unavailable."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        matplotlib.rcParams['font.sans-serif'] = [
            'PingFang SC',          # macOS PingFang (default 10.11+; covers kana)
            'Hiragino Sans',        # macOS Japanese
            'Microsoft YaHei',      # Windows
            'Heiti SC',             # macOS Heiti fallback
            'SimHei',               # Windows SimHei fallback
            'Yu Gothic',            # Windows Japanese
            'Arial Unicode MS',     # macOS universal (incl. CJK)
            'WenQuanYi Micro Hei',  # Linux WenQuanYi
            'Noto Sans CJK SC',     # Linux Source Han Sans (SC)
            'Noto Sans CJK JP',     # Linux Source Han Sans (JP)
        ]
        matplotlib.rcParams['axes.unicode_minus'] = False
        return plt
    except Exception as e:
        print(t('msg_mpl_missing', err=e))
        return None


def _seg_colors(rows, log, plt):
    seg = _assign_segments(rows, log)
    uniq = list(dict.fromkeys(seg))
    cmap = plt.get_cmap('tab10')
    return seg, uniq, {s: cmap(i % 10) for i, s in enumerate(uniq)}


def chart_ahi_trend(rows, log, path, plt):
    """Per-night device residual event index + 5-night rolling median + segment bands."""
    dates = [r['date'] for r in rows]; x = np.arange(len(rows))
    ahi = np.array([r['ahi'] for r in rows])
    seg, _uniq, color = _seg_colors(rows, log, plt)
    fig, ax = plt.subplots(figsize=(11, 4.3))
    top = max(15.0, float(np.nanmax(ahi)) * 1.08)
    start = 0
    for i in range(1, len(seg) + 1):
        if i == len(seg) or seg[i] != seg[start]:
            ax.axvspan(start - 0.5, i - 0.5, color=color[seg[start]], alpha=0.09)
            ax.text((start + i - 1) / 2, top, seg[start], ha='center', va='top',
                    fontsize=9, color=color[seg[start]])
            start = i
    ax.scatter(x, ahi, s=24, c=[color[s] for s in seg], zorder=3)
    if len(ahi) >= 3:
        rm = np.array([np.nanmedian(ahi[max(0, i - 4):i + 1]) for i in range(len(ahi))])
        ax.plot(x, rm, '-', color='#333', lw=1.6, label=t('legend_rolling5'))
    ax.axhline(RESIDUAL_REI_TARGET, ls='--', color='green', lw=1,
               label=t('legend_target', v=f'{RESIDUAL_REI_TARGET:g}'))
    ax.axhline(RESIDUAL_REI_REVIEW, ls='--', color='orange', lw=1,
               label=t('legend_review', v=f'{RESIDUAL_REI_REVIEW:g}'))
    step = max(1, len(x) // 16)
    ax.set_xticks(x[::step]); ax.set_xticklabels([dates[i][4:] for i in range(0, len(dates), step)],
                                                 rotation=45, fontsize=8)
    ax.set_ylabel(t('axis_rei')); ax.set_ylim(0, top)
    ax.set_title(t('chart_at_title')); ax.legend(fontsize=8, loc='upper right')
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
    return path


def chart_pressure_oai(rows, log, path, plt):
    """Pressure P95 vs OAI scatter (titration view). Note: under APAP pressure and
    events are positively coupled; reference only."""
    p = np.array([r['press_95'] for r in rows]); o = np.array([r['oai'] for r in rows])
    seg, uniq, color = _seg_colors(rows, log, plt)
    fig, ax = plt.subplots(figsize=(6.6, 5))
    for s in uniq:
        m = [i for i, ss in enumerate(seg) if ss == s]
        ax.scatter(p[m], o[m], label=s, color=color[s], s=32, alpha=0.85)
    sp = spearman(p, o)
    good = ~(np.isnan(p) | np.isnan(o))
    if good.sum() >= 2:
        z = np.polyfit(p[good], o[good], 1)
        xs = np.linspace(np.nanmin(p), np.nanmax(p), 50)
        ax.plot(xs, np.polyval(z, xs), '--', color='gray')
    title = t('chart_po_title')
    if sp['rho'] is not None:
        title += f'   Spearman ρ={sp["rho"]:+.2f}'
    ax.set_title(title + '\n' + t('chart_po_subtitle'), fontsize=9.5)
    ax.set_xlabel(t('axis_press95')); ax.set_ylabel(t('axis_oai'))
    ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
    return path


def _all_event_hours(days):
    """Across nights: each event's hours since first-segment therapy start + type."""
    out = []
    for d in days:
        s0, _ = _session_span(d)
        if not s0:
            continue
        for p in sorted(glob.glob(f"{d}/*_EVE.edf")):
            st = edf_start(p)
            if not st:
                continue
            base = st.timestamp()
            for onset, _dur, lab in parse_annotations(p):
                typ = classify_event_label(lab)
                if typ is None:
                    continue
                h = (base + onset - s0) / 3600.0
                if 0 <= h <= 12:
                    out.append((h, typ))
    return out


def chart_event_hours(days, path, plt):
    """Stacked histogram of events by hours since therapy start."""
    ev = _all_event_hours(days)
    if not ev:
        return None
    bins = np.arange(0, math.ceil(max(h for h, _ in ev)) + 1, 1)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    data = {k: [h for h, tt in ev if tt == k] for k in ('oa', 'ca', 'hyp', 'ua')}
    ax.hist([data['oa'], data['ca'], data['hyp'], data['ua']], bins=bins, stacked=True,
            label=[t('ev_oa'), t('ev_ca'), t('ev_hyp'), t('ev_ua')],
            color=['#c44e52', '#4c72b0', '#dd8452', '#999999'])
    ax.set_xlabel(t('axis_hours_since_first')); ax.set_ylabel(t('axis_events_cumulative'))
    ax.set_title(t('chart_eh_title'))
    ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
    return path


def chart_pressure_hist(days, path, plt, title):
    """Cumulative dwell time per pressure bin (classic titration view). Weights convert
    each segment to minutes by its actual sampling rate."""
    segs = []
    for d in days:
        for p in sorted(glob.glob(f"{d}/*_PLD.edf")):
            arr, fs = read_signal_fs(p, 'Press')
            if arr is not None and fs and fs > 0:
                segs.append((arr, float(fs)))
    if not segs:
        return None
    fig, ax = plt.subplots(figsize=(7.5, 4))
    for arr, fs in segs:
        weight_per_sample = 1.0 / fs / 60.0   # minutes represented by one sample
        ax.hist(arr, bins=np.arange(4, 20.5, 0.5),
                weights=np.full(len(arr), weight_per_sample),
                color='#4c72b0', alpha=0.7)
    ax.set_xlabel(t('axis_press')); ax.set_ylabel(t('axis_minutes')); ax.set_title(title)
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
    return path


def chart_spo2_trend(rows, log, path, plt):
    """Nightly minimum SpO2 trend (SAD source)."""
    dates = [r['date'] for r in rows]
    x = np.arange(len(rows))
    spo2 = np.array([r.get('spo2_min', float('nan')) for r in rows], dtype=float)
    src   = [r.get('spo2_src') for r in rows]
    if np.all(np.isnan(spo2)):
        return None
    _seg, _uniq, _color = _seg_colors(rows, log, plt)
    fig, ax = plt.subplots(figsize=(11, 4))
    # color by source: SAD = blue circles
    m_sad = np.array([s == 'SAD' for s in src])
    if m_sad.any():
        ax.scatter(x[m_sad], spo2[m_sad], s=26, c='#4c72b0', marker='o', label='ResMed SAD', zorder=3)
    valid = ~np.isnan(spo2)
    if valid.sum() >= 3:
        rm = np.array([np.nanmedian(spo2[max(0, i-4):i+1]) for i in range(len(spo2))])
        ax.plot(x, rm, '-', color='#333', lw=1.4, label=t('legend_rolling5'))
    ax.axhline(90, ls='--', color='red',    lw=1, label=t('legend_spo2_90'))
    ax.axhline(94, ls='--', color='orange', lw=1, label=t('legend_spo2_94'))
    step = max(1, len(x) // 16)
    ax.set_xticks(x[::step]); ax.set_xticklabels([dates[i][4:] for i in range(0, len(dates), step)],
                                                  rotation=45, fontsize=8)
    ax.set_ylabel(t('axis_spo2_min'))
    ax.set_title(t('chart_st_title') + '\n' + t('chart_st_note'))
    ax.set_ylim(max(70, np.nanmin(spo2) - 3), 101)
    ax.legend(fontsize=8, loc='lower right')
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
    return path


def chart_event_pressure_hist(days, path, plt):
    """Descriptive distribution of pressure at the moment of clearly-labelled
    obstructive events."""
    ps = [e[1] for d in days for e in align_events_pressure(d)]
    if not ps:
        return None
    ps = np.array(ps)
    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.hist(ps, bins=np.arange(4, 20.5, 0.5), color='#c44e52')
    ax.axvline(float(np.median(ps)), ls='--', color='k', label=t('legend_median', m=f'{np.median(ps):.1f}'))
    ax.set_xlabel(t('axis_oa_press')); ax.set_ylabel(t('axis_event_count'))
    ax.set_title(t('chart_ep_title'))
    ax.legend(); fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
    return path


def chart_night_detail(day_dir, path, plt):
    """One night: pressure curve + obstructive-event lines + flow limitation (mini
    hypnogram)."""
    times, press, _ = _pld_pressure_timeline(day_dir)
    if times is None:
        return None
    t0 = times[0]; th = (times - t0) / 3600.0
    fl = _concat(sorted(glob.glob(f"{day_dir}/*_PLD.edf")), 'FlowLim')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 5), sharex=True,
                                   height_ratios=[3, 1])
    ax1.plot(th, press, color='#4c72b0', lw=0.8)
    for tb, _pa, _lab in align_events_pressure(day_dir):
        ax1.axvline((tb - t0) / 3600.0, color='#c44e52', alpha=0.35, lw=0.8)
    ax1.set_ylabel(t('axis_press_cmh2o'))
    ax1.set_title(t('chart_nd_title', date=os.path.basename(day_dir)))
    if fl.size:
        ax2.plot(np.arange(len(fl)) * 2 / 3600.0, fl, color='#dd8452', lw=0.8)
    ax2.set_ylabel(t('axis_flowlim')); ax2.set_xlabel(t('axis_hours_since_start'))
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
    return path


_MODE_KEYS = {0: 'mode_cpap', 1: 'mode_apap', 2: 'mode_bilevel'}
_MASK_KEYS = {0: 'mask_pillow', 1: 'mask_nasal', 2: 'mask_nasal2', 3: 'mask_full'}
_EPRTYPE_KEYS = {0: 'epr_off', 1: 'epr_full', 2: 'epr_ramp'}
_ONOFF_KEYS = {0: 'onoff_off', 1: 'onoff_on', 2: 'onoff_auto'}


def cmd_settings():
    """Parse the current device prescription from <data-dir>/STR.edf (STR is a
    non-standard EDF that read_edf cannot open; parsed by hand)."""
    if not STR_EDF.exists():
        print(t('settings_no_file', path=STR_EDF))
        return
    b = open(STR_EDF, 'rb').read()
    nsig = int(b[252:256]); ndr = int(b[236:244]); H = 256
    def fld(s, w, n): return [b[s + i*w:s + (i+1)*w].decode('latin-1').strip() for i in range(n)]
    def ff(s):
        try: return float(s)
        except Exception: return None
    labels = fld(H, 16, nsig)
    pmax = [ff(x) for x in fld(H + 104*nsig, 8, nsig)]
    dmax = [ff(x) for x in fld(H + 120*nsig, 8, nsig)]
    nsamp = [int(x) for x in fld(H + 216*nsig, 8, nsig)]
    data_off = H + 256*nsig; recsz = sum(nsamp)*2
    idx = {lab: i for i, lab in enumerate(labels)}
    def raw(name, day):
        i = idx[name]
        rec = b[data_off + day*recsz:data_off + (day+1)*recsz]; o = sum(nsamp[:i])*2
        return struct.unpack(f'<{nsamp[i]}h', rec[o:o+nsamp[i]*2])[0]
    # The last STR day is often an empty shell (Mode=-1); fall back to the last valid day
    vday = ndr - 1
    while vday > 0 and raw('Mode', vday) not in (0, 1, 2):
        vday -= 1
    def press(name):
        i = idx[name]; g = pmax[i]/dmax[i] if dmax[i] else 0.02
        return raw(name, vday) * g

    mode = raw('Mode', vday)
    print(t('settings_header', day=vday + 1, total=ndr))
    print(t('settings_mode', v=t(_MODE_KEYS.get(mode, mode))))
    if mode == 1:
        print(t('settings_range', lo=f"{press('S.AS.MinPress'):.1f}", hi=f"{press('S.AS.MaxPress'):.1f}"))
        print(t('settings_start', v=f"{press('S.AS.StartPress'):.1f}"))
    else:
        print(t('settings_fixed', v=f"{press('S.C.Press'):.1f}"))
    epr_on = raw('S.EPR.EPREnable', vday)
    lvl = raw('S.EPR.Level', vday); g = pmax[idx['S.EPR.Level']]/dmax[idx['S.EPR.Level']]
    print(t('settings_epr', onoff=t(_ONOFF_KEYS.get(epr_on, epr_on)), lvl=f"{lvl*g:.0f}",
            eprtype=t(_EPRTYPE_KEYS.get(raw('S.EPR.EPRType', vday), ''))))
    print(t('settings_ramp', onoff=t(_ONOFF_KEYS.get(raw('S.RampEnable', vday), raw('S.RampEnable', vday))),
            n=raw('S.RampTime', vday)))
    print(t('settings_smartstart', onoff=t(_ONOFF_KEYS.get(raw('S.SmartStart', vday), raw('S.SmartStart', vday)))))
    print(t('settings_mask', v=t(_MASK_KEYS.get(raw('S.Mask', vday), raw('S.Mask', vday)))))
    print(t('settings_humid', onoff=t(_ONOFF_KEYS.get(raw('S.HumEnable', vday), raw('S.HumEnable', vday))),
            lvl=raw('S.HumLevel', vday),
            tube=t(_ONOFF_KEYS.get(raw('HeatedTube', vday), raw('HeatedTube', vday))),
            temp=f"{raw('S.Temp', vday)/10:.0f}"))


def _load_rows():
    days = sorted(d for d in glob.glob(f"{ROOT}/*") if os.path.isdir(d))
    return [r for r in (night_summary(d) for d in days) if r["usage_h"] > 0.01]


def _fmt(v, f="{:.1f}"):
    return f.format(v) if not _nan(v) else "—"


def cmd_report():
    """Generate the PAP therapy monitoring report; clinical conclusions stay as
    auditable screening / review cues."""
    rows = _load_rows()
    if not rows:
        print(t('report_no_data', root=ROOT))
        return
    logobj = load_tuning_log(); log = logobj["log"] if logobj else []
    an = [r for r in rows if r["analyzable"]]
    segs = segment_nights(rows, log) if log else [({'label': t('seg_all_label'), 'since': ""}, rows)]
    segs_an = segment_nights(an, log) if log else ([({'label': t('seg_all_label'), 'since': ""}, an)] if an else [])
    stats_an = [(e, seg_stats(s)) for e, s in segs_an]
    # "Current segment" follows the latest recorded settings; when that segment
    # entirely fails the quality gates it must show insufficient data — never
    # quietly fall back to nights under older settings pretending that is the
    # current efficacy.
    current_dates = {r['date'] for r in segs[-1][1]} if segs else set()
    current_an = [r for r in an if r['date'] in current_dates]
    current_stats = seg_stats(current_an) if current_an else None
    n_total = {e.get('label'): len(s) for e, s in segs}
    comparisons = [seg_verdict(segs_an[i - 1][1], segs_an[i][1], k)
                   for i in range(1, len(segs_an)) for k in ("ahi", "oai")]
    pr = pressure_response(current_an)
    tv = timing_verdict(current_an)
    assessment = clinical_assessment(current_an)
    # Waveform layer: rebuild breathing breath-by-breath for the latest nights of
    # the current segment (clusters / periodicity / pressure-flatness); roughly
    # 0.1 s per night, capped at the last WAVE_REPORT_NIGHTS nights.
    wave_nights = _load_nights([f"{ROOT}/{r['date']}" for r in current_an[-WAVE_REPORT_NIGHTS:]])
    wave_pool = _wave_pool(wave_nights)
    wave_v = wave_verdict(wave_nights, wave_pool)
    reason_counts = {}
    for row in rows:
        for reason in row.get('quality_reasons', []):
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    os.makedirs(REPORT_DIR, exist_ok=True)
    now = datetime.now(); stamp = now.strftime("%Y%m%d_%H%M%S")

    plt = _try_mpl(); charts = []
    if plt:
        cur_days = [f"{ROOT}/{r['date']}" for r in current_an]
        specs = [("residual_rei", lambda p: chart_ahi_trend(rows, log, p, plt)),
                 ("spo2", lambda p: chart_spo2_trend(rows, log, p, plt)),
                 ("pressure_oai", lambda p: chart_pressure_oai(current_an, log, p, plt)),
                 ("event_hours", lambda p: chart_event_hours(cur_days, p, plt)),
                 ("event_pressure", lambda p: chart_event_pressure_hist(cur_days, p, plt)),
                 ("pressure_hist", lambda p: chart_pressure_hist(cur_days, p, plt, t('chart_ph_title')))]
        if wave_pool is not None:
            specs.append(("pressure_fi", lambda p: chart_pressure_fi_curve(
                wave_pool, p, plt, wave_pool['event_press'])))
            specs.append(("cluster_timeline", lambda p: chart_cluster_timeline(wave_nights, p, plt)))
        for tag, fn in specs:
            pth = f"{REPORT_DIR}/{stamp}_{tag}.png"
            try:
                if fn(pth): charts.append((tag, pth))
            except Exception as e:
                print(t('msg_chart_fail', tag=tag, err=e))

    snap = {
        "generated_at": now.isoformat(timespec="seconds"),
        "report_type": "PAP treatment monitoring / clinical decision support; not a PSG diagnosis",
        "device": (logobj or {}).get("device", ""),
        "quality": {'nights': len(rows), 'analyzable': len(an),
                    'short_treatment_nights': sum(1 for r in rows if r["short_night"]),
                    'reasons_excluded': reason_counts,
                    'leak95_med': float(np.nanmedian([r["leak_95"] for r in rows])) if rows else None},
        "nights": rows,
        "segments": [{"label": e.get("label"), "since": e.get("since"),
                      "settings": {k: e.get(k) for k in ("min_press", "max_press", "epr")},
                      "stats": st} for e, st in stats_an],
        "clinical_assessment": assessment,
        "pressure_response": pr, "timing": tv, "comparisons": comparisons,
        "waveform": {"nights": _wave_snapshot(wave_nights), "verdict": wave_v},
    }
    json_path = f"{REPORT_DIR}/{stamp}_snapshot.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(_clean(snap), f, ensure_ascii=False, indent=2)

    md = [t('report_title', ts=now.strftime('%Y-%m-%d %H:%M'))]
    md.append(t('report_disclaimer'))
    md.append('\n' + t('report_device', device=(logobj or {}).get('device', ''),
                       mask=(logobj or {}).get('mask', '')))
    if segs:
        e = segs[-1][0]
        md.append(t('report_current_settings', label=e.get('label'), since=e.get('since'),
                    pmin=e.get('min_press'), pmax=e.get('max_press'), epr=e.get('epr')))

    md.append('\n' + t('report_s1_title'))
    md.append(t('report_s1_coverage', n=len(rows), d0=rows[0]['date'], d1=rows[-1]['date'],
                an=len(an), h=f'{MIN_ANALYZE_H:.0f}', leak=f'{LEAK_95_MAX:.0f}'))
    md.append(t('report_s1_short', h=f'{COMPLIANCE_H:.0f}',
                k=sum(1 for r in rows if r['short_night'])))
    lk = float(np.nanmedian([r['leak_95'] for r in rows])) if rows else float('nan')
    md.append(t('report_s1_leak', v=_fmt(lk, '{:.2f}'), mx=f'{LEAK_95_MAX:.0f}'))
    if reason_counts:
        items = "; ".join(t('report_s1_reason_item', reason=quality_reason_text(code), n=count)
                          for code, count in sorted(reason_counts.items()))
        md.append(t('report_s1_reasons', items=items))
    md.append(t('report_s1_scope'))

    md.append('\n' + t('report_s2_title', level=assessment['level']))
    md.append(assessment['summary'])
    for finding in assessment['findings']:
        md.append(f"- {finding['text']}")
    md.append('\n' + t('report_s2_actions_head'))
    for action in assessment['review_actions']:
        md.append(f"- {action}")

    md.append('\n' + t('report_s3_title'))
    if stats_an:
        md.append(t('report_s3_table_header'))
        md.append("|---|---|---|---|---|---|---|---|---|---|")
        for seg_idx, (e, st) in enumerate(stats_an):
            ss = (f"{e.get('min_press')}–{e.get('max_press')} EPR{e.get('epr')}"
                  if e.get("min_press") is not None else "—")
            a = st['ahi']; uai = _agg(segs_an[seg_idx][1], 'uai')
            md.append(f"| {e.get('label','')} | {ss} | {st['n']}/{n_total.get(e.get('label'), st['n'])} | "
                      f"{_fmt(st['usage_h']['mean'])} | {_fmt(a['med'])}[{_fmt(a['iqr'])}] | "
                      f"{_fmt(st['oai']['med'])} | {_fmt(st['cai']['med'])} | {_fmt(uai['med'])} | "
                      f"{_fmt(st['press_95']['med'])} | {_fmt(st['flowlim_95']['med'],'{:.2f}')} |")
        for ci in range(0, len(comparisons), 2):
            va, vo = comparisons[ci], comparisons[ci + 1]
            la = segs_an[ci // 2][0].get('label'); lb = segs_an[ci // 2 + 1][0].get('label')
            md.append('\n' + t('report_s3_comparison', la=la, lb=lb,
                               rei_a=_fmt(va['med_a']), rei_b=_fmt(va['med_b']),
                               p1=_fmt(va['p'], '{:.3f}'), v1=va['verdict'],
                               oai_a=_fmt(vo['med_a']), oai_b=_fmt(vo['med_b']),
                               p2=_fmt(vo['p'], '{:.3f}'), v2=vo['verdict']))
        md.append('\n' + t('report_s3_mwu_note'))
    else:
        md.append(t('report_s3_skip'))

    md.append('\n' + t('report_s4_title'))
    md.append(t('report_s4_meds', ev=_fmt(pr['ev_press_med']), th=_fmt(pr['therapy_press_med'])))
    if pr['pooled_hi'] is not None:
        md.append(t('report_s4_aligned', n=pr['n_aligned_events'], m=pr['n_high_events'],
                    pct=f"{pr['pooled_hi']*100:.0f}", e=f"{pr['high_pressure_exposure']*100:.0f}"))
        if pr['high_pressure_rate_ratio'] is not None:
            md.append(t('report_s4_ratio', rr=_fmt(pr['high_pressure_rate_ratio'], '{:.2f}')))
    sp = pr['spearman']
    if sp['rho'] is not None:
        md.append(t('report_s4_spearman', rho=f"{sp['rho']:+.2f}", n=sp['n']))
    md.append(t('report_s4_verdict', v=pr['verdict'], why=pr['why']))
    if tv:
        md.append(t('report_s4_timing', n=tv['n_events'], t1=f"{tv['t1']*100:.0f}",
                    t2=f"{tv['t2']*100:.0f}", t3=f"{tv['t3']*100:.0f}", v=tv['verdict']))

    md.append('\n' + t('report_s4b_title',
                       n=len([w for _d, _r, w in wave_nights if w])))
    if wave_v['points']:
        md.append(t('report_s4b_preamble'))
        resp = event_pressure_response([f"{ROOT}/{r['date']}" for r in current_an[-WAVE_REPORT_NIGHTS:]])
        if resp:
            md.append(t('report_s4b_feedback', n=resp['n_events'],
                        med=f"{resp['ev_median']:+.2f}",
                        rise=f"{resp['ev_rise_frac']*100:.0f}",
                        fall=f"{resp['ev_fall_frac']*100:.0f}",
                        ctrl_n=resp['n_control'], ctrl_med=f"{resp['ctrl_median']:+.2f}",
                        ctrl_rise=f"{resp['ctrl_rise_frac']*100:.0f}"))
        for point in wave_v['points']:
            md.append(f"- {point}")
        pe = _pressure_exposure_for(wave_pool, configured_max_press())
        if pe:
            for point in pe['points']:
                md.append(f"- {point}")
    else:
        md.append(t('report_s4b_skip'))

    md.append('\n' + t('report_s5_title'))
    if current_stats:
        md.append(t('report_s5_flowlim',
                    fl=_fmt(current_stats['flowlim_95']['med'], '{:.2f}'),
                    snore=_fmt(current_stats['snore_95']['med'], '{:.2f}')))
        md.append(t('report_s5_vent',
                    rr=_fmt(current_stats['resprate_med']['med']),
                    tv=_fmt(current_stats['tidvol_med']['med'], '{:.2f}'),
                    mv=_fmt(current_stats['minvent_med']['med'])))
    cur_rows = current_an
    def _med_of(k):
        values = [r[k] for r in cur_rows if not _nan(r.get(k, float('nan')))]
        return float(np.nanmedian(values)) if values else float('nan')

    spo2_min_med = _med_of('spo2_min')
    spo2_src_set = {r.get('spo2_src') for r in cur_rows if r.get('spo2_src')}
    if not _nan(spo2_min_med):
        src_note = (t('report_s5_src', src=", ".join(sorted(spo2_src_set)))
                    if spo2_src_set else "")
        md.append(t('report_s5_spo2', v=_fmt(spo2_min_med), avg=_fmt(_med_of('spo2_avg')),
                    src=src_note))

    md.append('\n' + t('report_s6_title'))
    has_spo2 = any(not _nan(r.get('spo2_min', float('nan'))) for r in rows[-7:])
    header = t('report_s6_header') if has_spo2 else t('report_s6_header_nospo2')
    md.extend([header, "|---|---|---|---|---|---|---|---|" + ("---|" if has_spo2 else "")])
    for row in rows[-7:]:
        line = (f"| {row['date']} | {_fmt(row['usage_h'])} | {_fmt(row['residual_rei'])} | {_fmt(row['oai'])} | "
                f"{_fmt(row['cai'])} | {_fmt(row['uai'])} | {_fmt(row['press_95'])} | {_fmt(row['leak_95'],'{:.2f}')} |")
        if has_spo2:
            line += f" {_fmt(row.get('spo2_min', float('nan')))} |"
        md.append(line)

    if charts:
        md.append('\n' + t('report_charts_title'))
        for tag, pth in charts:
            md.append(f"![{tag}]({os.path.basename(pth)})")
    md.append('\n' + t('report_handoff_title'))
    md.append(t('report_handoff_emergency'))
    md.append(t('report_handoff_medical'))

    md_path = f"{REPORT_DIR}/{stamp}_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))
    print('\n' + t('msg_report_saved', md=md_path, json=json_path))
    if charts:
        print(t('msg_chart_list', names="  ".join(os.path.basename(p) for _, p in charts)))


def cmd_pressure():
    """Descriptive event-pressure association for clinical review; never an automatic
    cause or pressure-decision."""
    rows = _load_rows()
    an = [r for r in rows if r["analyzable"]]
    if not an:
        print(t('pressure_no_data', h=f'{MIN_ANALYZE_H:.0f}'))
        return
    pr = pressure_response(an)
    tv = timing_verdict(an)
    print(t('pressure_header'))
    print(t('pressure_nights', n=len(an), h=f'{MIN_ANALYZE_H:.0f}') + '\n')
    print(t('pressure_meds', ev=_fmt(pr['ev_press_med']), th=_fmt(pr['therapy_press_med'])))
    if pr['pooled_hi'] is not None:
        print(t('pressure_above90', pct=f"{pr['pooled_hi']*100:.0f}"))
    sp = pr['spearman']
    if sp['rho'] is not None:
        print(t('pressure_spearman', rho=f"{sp['rho']:+.2f}", n=sp['n']))
        print(t('pressure_spearman_note'))
    if pr.get('high_pressure_exposure') is not None:
        print(t('pressure_exposure', pct=f"{pr['high_pressure_exposure']*100:.0f}"))
    if pr.get('high_pressure_rate_ratio') is not None:
        print(t('pressure_ratio', v=_fmt(pr['high_pressure_rate_ratio'], '{:.2f}')))
    print('\n' + t('pressure_verdict', v=pr['verdict']))
    print(t('pressure_why', w=pr['why']))
    if tv:
        print('\n' + t('pressure_timing', t1=f"{tv['t1']*100:.0f}", t2=f"{tv['t2']*100:.0f}",
                       t3=f"{tv['t3']*100:.0f}", v=tv['verdict']))
    plt = _try_mpl()
    if plt:
        os.makedirs(REPORT_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logobj = load_tuning_log(); log = logobj["log"] if logobj else []
        days = [f"{ROOT}/{r['date']}" for r in an]
        out = []
        for tag, fn in [("pressure_oai", lambda p: chart_pressure_oai(an, log, p, plt)),
                        ("event_pressure", lambda p: chart_event_pressure_hist(days, p, plt))]:
            pth = f"{REPORT_DIR}/{stamp}_{tag}.png"
            try:
                if fn(pth): out.append(os.path.basename(pth))
            except Exception as e:
                print(t('msg_chart_fail', tag=tag, err=e))
        if out:
            print('\n' + t('msg_charts_saved', names="  ".join(out), dir=REPORT_DIR))


def cmd_summary(as_csv=False):
    """Print the all-nights summary table; as_csv=True emits CSV to stdout instead.

    The CSV keeps the legacy `ahi` column for downstream compatibility and adds
    residual_rei / uai — the device event index is not PSG-AHI, and separate
    column names keep downstream tools from reading it as a diagnostic grade.
    """
    rows = _load_rows()
    if as_csv:
        # legacy `ahi` kept for downstream compatibility; residual_rei/uai added
        # explicitly so the device index is not misread as PSG-AHI.
        cols = ['date', 'usage_h', 'ahi', 'residual_rei', 'oai', 'cai', 'hi', 'uai', 'n_ua',
                'press_med', 'press_95',
                'leak_95', 'flowlim_95', 'snore_95', 'resprate_med', 'tidvol_med', 'minvent_med',
                'oa_press_med', 'oa_press_hi_frac', 'oa_alignment_coverage', 'analyzable']
        print(','.join(cols))
        for r in rows:
            def cell(value):
                if _nan(value):
                    return ''
                if isinstance(value, (float, np.floating)):
                    return f"{float(value):.3f}"
                return str(value)
            print(','.join(cell(r[c]) for c in cols))
        return
    print(t('summary_header'))
    print("-" * 84)
    for r in rows:
        flag = "" if r['analyzable'] else " *"
        print(f"{r['date']:<10} {r['usage_h']:>5.1f} {r['ahi']:>5.1f} {r['oai']:>5.1f} "
              f"{r['cai']:>5.1f} {r['hi']:>5.1f} "
              f"{r['press_med']:>4.1f}/{r['press_95']:<5.1f} {_fmt(r['flowlim_95'],'{:.2f}'):>5} "
              f"{_fmt(r['leak_95'],'{:.2f}'):>6} {_fmt(r['oa_press_med']):>7}{flag}")
    if rows:
        def avg(k):
            return np.nanmean([r[k] for r in rows])
        print("-" * 84)
        print(t('summary_avg_row', usage=f"{avg('usage_h'):.1f}", ahi=f"{avg('ahi'):.1f}",
                oai=f"{avg('oai'):.1f}", cai=f"{avg('cai'):.1f}", hi=f"{avg('hi'):.1f}"))
        print('\n' + t('summary_legend', h=f'{MIN_ANALYZE_H:.0f}'))


def cmd_detail(date):
    """Print one night's detail: therapy record + event list (with pressure at onset).

    With matplotlib, additionally saves a nightly chart to
    <data-dir>/reports/<date>_night.png; without it (or on chart errors) only a
    hint is printed and the text output is unaffected.
    """
    day_dir = f"{ROOT}/{date}"
    if not os.path.isdir(day_dir):
        print(t('detail_no_dir', path=day_dir)); return
    r = night_summary(day_dir)
    print(t('detail_header', date=date))
    print(t('detail_summary', h=f"{r['usage_h']:.2f}", rei=f"{r['residual_rei']:.1f}",
            oa=r['n_oa'], ca=r['n_ca'], hyp=r['n_hyp'], ua=r['n_ua'])
          + ('' if r['analyzable'] else t('detail_not_analyzable')))
    print(t('detail_pressure', med=f"{r['press_med']:.1f}", p95=f"{r['press_95']:.1f}",
            mx=_fmt(r['press_max'])))
    if not _nan(r['oa_press_hi_frac']):
        print(t('detail_oa_press', med=_fmt(r['oa_press_med']),
                pct=f"{r['oa_press_hi_frac']*100:.0f}"))
    else:
        print(t('detail_oa_press_none'))
    print(t('detail_flowlim', fl_med=_fmt(r['flowlim_med'], '{:.2f}'),
            fl95=_fmt(r['flowlim_95'], '{:.2f}'), snore95=_fmt(r['snore_95'], '{:.2f}')))
    print(t('detail_vent', rr=_fmt(r['resprate_med']), tv=_fmt(r['tidvol_med'], '{:.2f}'),
            mv=_fmt(r['minvent_med'])))
    print(t('detail_leak', med=_fmt(r['leak_med'], '{:.2f}'), p95=_fmt(r['leak_95'], '{:.2f}')))
    if not _nan(r['ev_t1']):
        print(t('detail_thirds', t1=f"{r['ev_t1']*100:.0f}", t2=f"{r['ev_t2']*100:.0f}",
                t3=f"{r['ev_t3']*100:.0f}"))
    if not _nan(r.get('spo2_min', float('nan'))):
        src = r.get('spo2_src', '')
        src_tag = t('detail_src_tag', src=src) if src else ""
        print(t('detail_spo2', v=_fmt(r['spo2_min']), avg=_fmt(r.get('spo2_avg', float('nan'))),
                src=src_tag))
    print('\n' + t('detail_event_list_head'))
    ep = {round(x): p for x, p, _ in align_events_pressure(day_dir)}
    eve = sorted(glob.glob(f"{day_dir}/*_EVE.edf"))
    allev = []
    for p in eve:
        s = edf_start(p); b = s.timestamp() if s else 0
        for onset, dur, lab in parse_annotations(p):
            # display the real clock time (epoch → local), not the offset from
            # the first segment's start
            allev.append((b + onset, dur, lab, ep.get(round(b + onset))))
    allev.sort()
    for t_abs, dur, lab, pa in allev[:40]:
        hh, mm, ss = datetime.fromtimestamp(t_abs).strftime('%H:%M:%S').split(':')
        pstr = f"  {pa:.1f}cmH2O" if pa is not None else ""
        print(f"  {hh}:{mm}:{ss}  {dur:4.0f}s  {lab}{pstr}")
    if len(allev) > 40:
        print(t('detail_event_more', n=len(allev)))
    plt = _try_mpl()
    if plt:
        os.makedirs(REPORT_DIR, exist_ok=True)
        pth = f"{REPORT_DIR}/{date}_night.png"
        try:
            if chart_night_detail(day_dir, pth, plt):
                print('\n' + t('msg_night_chart', path=pth))
        except Exception as e:
            print(t('msg_night_chart_fail', err=e))


def _opt_int(flag, default, argv=None):
    """Integer option in `--flag N` form; default when missing or invalid."""
    argv = sys.argv if argv is None else argv
    if flag not in argv:
        return default
    i = argv.index(flag)
    if i + 1 < len(argv):
        try:
            return int(argv[i + 1])
        except ValueError:
            pass
    return default


def main(argv=None):
    """CLI entry point (also installed as the `resmed-sd-monitor` console script)."""
    args = list(sys.argv[1:] if argv is None else argv)
    data_dir = None
    lang = None
    rest = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ('-h', '--help'):
            print(__doc__)
            return 0
        elif a == '--data-dir' and i + 1 < len(args):
            data_dir = args[i + 1]; i += 2
        elif a.startswith('--data-dir='):
            data_dir = a.split('=', 1)[1]; i += 1
        elif a == '--lang' and i + 1 < len(args):
            lang = args[i + 1]; i += 2
        elif a.startswith('--lang='):
            lang = a.split('=', 1)[1]; i += 1
        else:
            rest.append(a); i += 1
    if lang:
        set_lang(lang)
    if data_dir:
        set_data_dir(data_dir)
    positional = [a for a in rest if not a.startswith('--')]
    if '--settings' in rest:
        cmd_settings()
    elif '--report' in rest:
        cmd_report()
    elif '--wave' in rest:
        # --wave [N]: analyze the last N treatment dates (default 14); a date
        # analyzes only that night. Positional args may carry --wave's numeric
        # parameter, so only 8-digit date-like directory names count as dates.
        day_args = [a for a in positional
                    if len(a) == 8 and a.isdigit() and os.path.isdir(f"{ROOT}/{a}")]
        if day_args:
            cmd_wave([f"{ROOT}/{a}" for a in day_args])
        else:
            cmd_wave(n_nights=_opt_int('--wave', 14, rest))
    elif '--pressure' in rest:
        cmd_pressure()
    elif positional:
        cmd_detail(positional[0])
    else:
        cmd_summary(as_csv='--csv' in rest)
    return 0


if __name__ == '__main__':
    sys.exit(main())
