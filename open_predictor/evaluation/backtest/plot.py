"""Reliability diagram for the production model (matplotlib lives only here).

Computed on the validated 200-day window (2025-09-09..2026-07-13): ModelProd
is fitted on the first 100 days and evaluated on the held-out 100, at the
9:00 ET prediction time (the latest hour present in the hourly dataset;
9:29 exists only as an unretained 18-day minute-level sample). Bins are
deciles of predicted P(up); whiskers are 95% Wilson intervals.
"""
import math

from open_predictor.evaluation.backtest import dataset
from open_predictor.forecast.model.core import ModelProd

WINDOW = ("2025-09-09", "2026-07-13")   # the paper's validated 200-day window
HOUR = 9
N_BINS = 10

INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"
BASE = "#c3c2b7"
SURFACE = "#fcfcfb"
BLUE = "#2a78d6"


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


def _test_predictions():
    rows = dataset.load()
    dates = [r["date"] for r in rows]
    w = rows[dates.index(WINDOW[0]):dates.index(WINDOW[1]) + 1]
    model = ModelProd().fit(w[:len(w) // 2])
    preds = [(model.predict(r, HOUR)[2], r["off"] > 0)
             for r in w[len(w) // 2:] if HOUR in r["es"]]
    brier = sum((p - o) ** 2 for p, o in preds) / len(preds)
    return preds, brier


def reliability_diagram(out_path="docs/research/plots/reliability_diagram.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    preds, brier = _test_predictions()
    bins = [[0, 0] for _ in range(N_BINS)]        # [n, n_up]
    for p, o in preds:
        b = min(int(p * N_BINS), N_BINS - 1)
        bins[b][0] += 1
        bins[b][1] += o

    fig, (ax, axc) = plt.subplots(
        2, 1, figsize=(7.2, 7.6), dpi=150, sharex=True,
        gridspec_kw={"height_ratios": [4, 1], "hspace": 0.06})
    fig.patch.set_facecolor(SURFACE)
    for a in (ax, axc):
        a.set_facecolor(SURFACE)
        for sp in ("top", "right", "left"):
            a.spines[sp].set_visible(False)
        a.spines["bottom"].set_color(BASE)
        a.tick_params(colors=MUTED, labelsize=9)

    ax.plot([0, 1], [0, 1], color=BASE, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.annotate("perfect calibration", (0.60, 0.575), color=MUTED,
                fontsize=8.5, rotation=38, rotation_mode="anchor")
    centers, freqs = [], []
    for i, (n, up) in enumerate(bins):
        if not n:
            continue
        x = (i + 0.5) / N_BINS
        f = up / n
        lo, hi = wilson(up, n)
        ax.plot([x, x], [lo, hi], color=BLUE, lw=1.2, alpha=0.55, zorder=3)
        centers.append(x)
        freqs.append(f)
    ax.plot(centers, freqs, color=BLUE, lw=2, zorder=4)
    ax.scatter(centers, freqs, s=42, color=BLUE, edgecolors=SURFACE,
               linewidths=1.5, zorder=5)
    ax.grid(color=GRID, lw=0.75, zorder=0)
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.02, 1.02)
    ax.set_ylabel("observed frequency of UP", color=MUTED, fontsize=10)
    ax.set_title(f"Reliability at 9:00 ET - test half (n={len(preds)} days), "
                 f"Brier {brier:.4f}",
                 color=INK, fontsize=11.5, loc="left", pad=12)

    xs = [(i + 0.5) / N_BINS for i in range(N_BINS)]
    axc.bar(xs, [n for n, _ in bins], width=1 / N_BINS - 0.012, color=BASE,
            zorder=2)
    for x, (n, _) in zip(xs, bins):
        if n:
            axc.annotate(str(n), (x, n), xytext=(0, 2),
                         textcoords="offset points", ha="center",
                         color=MUTED, fontsize=8)
    axc.grid(axis="y", color=GRID, lw=0.75, zorder=0)
    axc.set_ylabel("days", color=MUTED, fontsize=9)
    axc.set_xlabel("predicted P(up)", color=MUTED, fontsize=10)

    fig.subplots_adjust(left=0.11, right=0.96, top=0.94, bottom=0.075)
    for path in (out_path, out_path.replace(".png", ".pdf")):
        fig.savefig(path, facecolor=SURFACE)
    return out_path, brier, len(preds)
