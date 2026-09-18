"""Mask-off timing audit: was "couldn't keep the mask on" an event-driven arousal
or something else?

Usage:
  resmed-sd-monitor-maskoff [--data-dir DIR] [--lang en|zh|ja]

Classifies each night by the gap between therapy end and the last event:
- cluster  : dense events within the final 10 min (>=2) -> arousal then unconscious mask-off
- lone     : exactly 1 event within the final 30 min -> possibly woken by that single event
- clean    : no events in the final 30 min -> mask-off unrelated to events
             (sufficient duration / gave up subjectively / leak)
- no_events: whole night without events yet ended early -> fully unrelated; look elsewhere
"""

import glob
import os
import sys
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from . import monitor as R
from .i18n import set_lang, t


def night_events(day_dir):
    """All events (including central) with absolute timestamps + labels."""
    out = []
    for p in sorted(glob.glob(f"{day_dir}/*_EVE.edf")):
        st = R.edf_start(p)
        if st is None:
            continue
        base = st.timestamp()
        for onset, dur, lab in R.parse_annotations(p):
            out.append((base + onset, dur, lab))
    return sorted(out)


def classify_night(day_dir):
    """One night -> (date, hours, end_hhmm, gap_s, n_last30, kind, last_labels)."""
    start, end = R.session_span(day_dir)
    if start is None:
        return None
    evs = night_events(day_dir)
    end_dt = datetime.fromtimestamp(end)
    in_last30 = [e for e in evs if end - e[0] <= 1800]
    in_last10 = [e for e in evs if end - e[0] <= 600]
    gap = None
    if evs:
        # last event -> mask-off gap in seconds (negative = event after span end, clamp to 0)
        gap = max(0, end - evs[-1][0])
    kind = 'clean'
    if len(in_last10) >= 2:
        kind = 'cluster'
    elif in_last30:
        kind = 'lone'
    elif not evs:
        kind = 'no_events'
    return (os.path.basename(day_dir), (end - start) / 3600.0,
            end_dt.strftime('%H:%M'), gap, len(in_last30), kind,
            ', '.join(lab.split()[0] for _t, _d, lab in in_last30[-4:]))


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    data_dir = lang = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == '--data-dir' and i + 1 < len(args):
            data_dir = args[i + 1]; i += 2
        elif a.startswith('--data-dir='):
            data_dir = a.split('=', 1)[1]; i += 1
        elif a == '--lang' and i + 1 < len(args):
            lang = args[i + 1]; i += 2
        elif a.startswith('--lang='):
            lang = a.split('=', 1)[1]; i += 1
        else:
            i += 1
    if lang:
        set_lang(lang)
    if data_dir:
        R.set_data_dir(data_dir)

    rows = []
    for day_dir in sorted(glob.glob(f"{R.ROOT}/*")):
        if not os.path.isdir(day_dir):
            continue
        row = classify_night(day_dir)
        if row is not None:
            rows.append(row)

    print(t('maskoff_header'))
    cnt = {}
    for day, hrs, end_t, gap, n30, kind, labs in rows:
        if gap is None:
            gap_s = "-"
        elif gap < 60:
            gap_s = f"{int(gap)}s"
        else:
            gap_s = f"{int(gap // 60)}min"
        flag = '*' if kind != 'clean' else ''
        print(f"{day:<10}{hrs:>6.1f}{end_t:>8}{gap_s:>12}{n30:>8}  {kind:<11}{labs} {flag}")
        cnt[kind] = cnt.get(kind, 0) + 1
    print('\n' + t('maskoff_counts', counts=", ".join(f"{k}={v}" for k, v in sorted(cnt.items()))))
    # End-time distribution: how many nights ended in each window
    ends = [r[2] for r in rows]
    hm = [datetime.strptime(e, '%H:%M') for e in ends]
    early = sum(1 for x in hm if x <= datetime(1900, 1, 1, 1, 0))
    mid = sum(1 for x in hm if datetime(1900, 1, 1, 1, 0) < x <= datetime(1900, 1, 1, 3, 30))
    late = sum(1 for x in hm if x > datetime(1900, 1, 1, 3, 30))
    print(t('maskoff_end_dist', early=early, mid=mid, late=late))
    return 0


if __name__ == '__main__':
    sys.exit(main())
