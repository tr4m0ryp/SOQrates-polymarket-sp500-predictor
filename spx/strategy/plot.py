"""Plotting helpers for strategy-lab results (matplotlib lives only here)."""

INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"
BASE = "#c3c2b7"
SURFACE = "#fcfcfb"
BLUE = "#2a78d6"      # series 1: raw $50/day
GREEN = "#008300"     # series 2: guarded min($50, 20% bankroll)


def bankroll_band(out_path="research/plots/strategy_bankroll_50_band.png"):
    """Bootstrap-band version of the bankroll figure: the two headline
    records (first-signal flat $50; hour-4 hold at 10% of bankroll) with
    their 5-95% day-resampled bootstrap bands from strategy/bootstrap.py."""
    import json
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import datetime as dt

    from spx.strategy import bootstrap
    if not bootstrap.OUT_FILE.exists():
        bootstrap.run()
    bb = json.loads(bootstrap.OUT_FILE.read_text())
    xs = [dt.date(*map(int, d.split("-"))) for d in bb["dates"]]
    series = [
        ("First signal, flat $50", BLUE, bb["strategies"]["first_signal_flat50"]),
        ("Hour-4 hold, 10% of bankroll", GREEN, bb["strategies"]["hold_h4_frac10"]),
    ]

    fig, ax = plt.subplots(figsize=(10, 5.4), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    for label, color, s in series:
        ax.fill_between(xs, s["band"]["p5"], s["band"]["p95"], color=color,
                        alpha=0.14, lw=0, zorder=2)
        ax.plot(xs, s["band"]["p50"], color=color, lw=1, ls=(0, (2, 3)),
                alpha=0.8, zorder=3)
        ax.plot(xs, s["actual_path"], color=color, lw=2, label=label, zorder=4)
        ax.annotate(f"${s['actual_end']:,.2f}", (xs[-1], s["actual_path"][-1]),
                    xytext=(8, 0), textcoords="offset points", color=INK,
                    fontsize=10, fontweight="bold", va="center")
        e = s["end"]
        ax.annotate(f"5-95%: \\${e['p5']:,.0f}-\\${e['p95']:,.0f}",
                    (xs[-1], e["p95"]), xytext=(8, 0),
                    textcoords="offset points", color=MUTED, fontsize=8.5,
                    va="center")

    ax.axhline(100, color=BASE, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.annotate("start $100", (mdates.date2num(xs[0]), 100), xytext=(0, -12),
                textcoords="offset points", color=MUTED, fontsize=9)
    ax.grid(axis="y", color=GRID, lw=0.75, zorder=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASE)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.set_ylabel("bankroll (USDC)", color=MUTED, fontsize=10)
    ax.set_title("SPX-open daily - test half (Apr 16 - Jul 14, 2026), shaded: "
                 f"5-95% band over {bb['B']:,} day-resampled bootstraps",
                 color=INK, fontsize=11.5, loc="left", pad=12)
    ax.legend(loc="upper left", frameon=False, fontsize=9.5, labelcolor=INK)
    fig.tight_layout()
    for path in (out_path, out_path.replace(".png", ".pdf")):
        fig.savefig(path, facecolor=SURFACE)
    return out_path


def bankroll_trajectories(out_path="research/plots/strategy_bankroll_50.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import datetime as dt

    from spx.strategy import data, sim
    days = data.build()
    _, te = data.split(days)
    ex = {"half_spread": 0.01, "impact_per_100": 0.001}
    core = {"hour": 4, "edge": 0.05, "gate": 0.6, "signal": "model", **ex}
    runs = [
        ("Raw $50/day", BLUE, {**core, "stake_abs": 50}),
        ("Guarded min($50, 20%)", GREEN, {**core, "stake_abs": 50, "bet_frac": 0.20}),
    ]

    fig, ax = plt.subplots(figsize=(10, 5.4), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    for label, color, prm in runs:
        r = sim.run("hold", te, prm)
        xs = [dt.date(*map(int, d["date"].split("-"))) for d in r["days"]]
        ys = [d["bankroll"] for d in r["days"]]
        ax.plot(xs, ys, color=color, lw=2, label=label, zorder=3)
        ax.annotate(f"${ys[-1]:,.0f}", (xs[-1], ys[-1]), xytext=(8, 0),
                    textcoords="offset points", color=INK, fontsize=10,
                    fontweight="bold", va="center")
        losses = [(x, y) for x, y, d in zip(xs, ys, r["days"])
                  if d["n"] and d["pnl"] < 0]
        ax.scatter(*zip(*losses), s=64, color=color, edgecolors=SURFACE,
                   linewidths=2, zorder=4)

    for x, txt in ((dt.date(2026, 7, 2), "Jul 2\nnews reversal"),
                   (dt.date(2026, 7, 10), "Jul 10\nquirk day")):
        ax.annotate(txt, (x, 292), color=MUTED, fontsize=8.5,
                    ha="center", va="top")

    ax.axhline(100, color=BASE, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.annotate("start $100", (mdates.date2num(dt.date(2026, 4, 16)), 100),
                xytext=(0, -12), textcoords="offset points",
                color=MUTED, fontsize=9)
    ax.grid(axis="y", color=GRID, lw=0.75, zorder=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASE)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.set_ylabel("bankroll (USDC)", color=MUTED, fontsize=10)
    ax.set_title("SPX-open daily, $50 stakes - hour-4 hold, test half "
                 "(Apr 16 - Jul 14, 2026) - 21 trades, 19W-2L",
                 color=INK, fontsize=11.5, loc="left", pad=12)
    ax.legend(loc="upper left", frameon=False, fontsize=9.5, labelcolor=INK)
    fig.tight_layout()
    fig.savefig(out_path, facecolor=SURFACE)
    return out_path
