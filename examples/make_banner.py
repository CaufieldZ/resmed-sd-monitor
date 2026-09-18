#!/usr/bin/env python3
"""Render the README hero banner from the synthetic demo data.

The banner is not decoration: it is one real night of therapy, drawn by the same
parsing code the tool ships. Top strip = the 25 Hz airflow envelope for the whole
night (each vertical line is one breath; the gaps are where breathing stopped).
Middle ticks = the events the tool detected. Bottom = mask pressure, where the
reactive bumps after each cluster are the APAP feedback loop the report audits.

Usage:
  python examples/generate_demo_data.py          # once, to create the data
  python examples/make_banner.py                 # → docs/assets/banner.png
"""

import argparse
import glob
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from resmed_sd_monitor import monitor as M  # noqa: E402

NIGHT = "20240306"      # clustered + late-heavy: two clean clusters, visible pressure response
COLS = 4000             # envelope columns (breaths per column ~ 1.4)
W, H, DPI = 2000, 667, 100
BG = "#0b1220"
FLOW = "#54c8f2"
PRESS = "#a78bfa"
INK = "#5c6b80"
KIND_COLOR = {"oa": "#ff5c6c", "ca": "#5c9dff", "hyp": "#ffab4a", "ua": "#9aa4b2"}
KIND_LABEL = [("oa", "obstructive"), ("hyp", "hypopnea"), ("ca", "central")]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=str(ROOT / "examples" / "demo" / "data"))
    ap.add_argument("--night", default=NIGHT)
    ap.add_argument("--out", default=str(ROOT / "docs" / "assets" / "banner.png"))
    args = ap.parse_args(argv)

    M.set_data_dir(args.data_dir)
    day = f"{args.data_dir}/DATALOG/{args.night}"
    brp = sorted(glob.glob(f"{day}/*_BRP.edf"))
    if not brp:
        sys.exit(f"no data for {args.night} under {args.data_dir} — run generate_demo_data.py first")

    flow = M._concat(brp, "Flow")
    hours = flow.size / 25.0 / 3600.0
    ivs, _ = M._therapy_intervals(day)
    events, _ = M._event_records(day, ivs)
    t0 = M.edf_start(brp[0]).timestamp()
    press = M._concat(sorted(glob.glob(f"{day}/*_PLD.edf")), "Press")
    ph = np.arange(press.size) / 0.5 / 3600.0

    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    fig.patch.set_facecolor(BG)

    L, R = 0.145, 0.995          # plot area; the left gutter holds the labels
    ax_flow = fig.add_axes([L, 0.400, R - L, 0.550])
    ax_ev = fig.add_axes([L, 0.318, R - L, 0.046], sharex=ax_flow)
    ax_pr = fig.add_axes([L, 0.115, R - L, 0.150], sharex=ax_flow)
    for ax in (ax_flow, ax_ev, ax_pr):
        ax.set_facecolor(BG)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_xlim(0, hours)

    # flow envelope: min/max per column = one breath per vertical stroke
    n = flow.size // COLS * COLS
    env = flow[:n].reshape(COLS, -1)
    x = np.linspace(0, hours, COLS)
    lo, hi = env.min(axis=1), env.max(axis=1)
    ax_flow.fill_between(x, lo, hi, color=FLOW, lw=0)
    reach = max(abs(float(lo.min())), abs(float(hi.max())), 1e-6) * 1.10
    ax_flow.set_ylim(-reach, reach)          # tight: the envelope fills its band

    # events, one tick per event in the middle band
    for e in events:
        h = (e["time"] - t0) / 3600.0
        if 0 <= h <= hours:
            ax_ev.axvline(h, color=KIND_COLOR[e["kind"]], lw=1.0, alpha=0.9)
    ax_ev.set_ylim(0, 1)

    # pressure trace
    ax_pr.plot(ph, press, color=PRESS, lw=0.8, alpha=0.92)
    pad = (float(press.max()) - float(press.min())) * 0.18 + 0.1
    ax_pr.set_ylim(float(press.min()) - pad, float(press.max()) + pad)

    # instrument labels, sitting in the left gutter
    fig.text(0.012, 0.918, "AIRFLOW", color=INK, fontsize=10.5, family="monospace", weight="bold")
    fig.text(0.012, 0.888, "25 Hz", color=INK, fontsize=8.5, family="monospace")
    fig.text(0.012, 0.865, "one night", color=INK, fontsize=8.5, family="monospace")
    fig.text(0.012, 0.340, "EVENTS", color=INK, fontsize=9.5, family="monospace", weight="bold")
    fig.text(0.012, 0.293, "detected", color=INK, fontsize=8.5, family="monospace")
    fig.text(0.012, 0.240, "MASK", color=INK, fontsize=9.5, family="monospace", weight="bold")
    fig.text(0.012, 0.216, "PRESSURE", color=INK, fontsize=9.5, family="monospace", weight="bold")
    fig.text(0.012, 0.176, "rises after", color=INK, fontsize=8.5, family="monospace")
    fig.text(0.012, 0.152, "events", color=INK, fontsize=8.5, family="monospace")

    # hour ruler along the bottom of the pressure panel
    for h in range(1, int(hours) + 1):
        fig.add_artist(plt.Line2D([L + (R - L) * h / hours, L + (R - L) * h / hours],
                                  [0.062, 0.073], color=INK, lw=0.6, alpha=0.75,
                                  transform=fig.transFigure))
    fig.text(R, 0.030, f"{hours:.1f} h of therapy", color=INK, fontsize=8.5,
             family="monospace", ha="right")

    # event-type legend along the bottom left
    lx = L
    for kind, label in KIND_LABEL:
        fig.add_artist(plt.Line2D([lx, lx + 0.009], [0.040, 0.040],
                                  color=KIND_COLOR[kind], lw=2.4, transform=fig.transFigure))
        fig.text(lx + 0.014, 0.030, label, color=INK, fontsize=8.5, family="monospace")
        lx += 0.016 + 0.0075 * len(label)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, facecolor=BG)
    print(f"banner → {args.out}  ({W}x{H}, night {args.night}, {len(events)} events)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
