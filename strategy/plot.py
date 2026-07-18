"""Plotting helpers for strategy-lab results (matplotlib lives only here)."""

INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"
BASE = "#c3c2b7"
SURFACE = "#fcfcfb"
BLUE = "#2a78d6"      # series 1: raw $50/day
GREEN = "#008300"     # series 2: guarded min($50, 20% bankroll)


def bankroll_trajectories(out_path="plots/strategy_bankroll_50.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import datetime as dt

    from strategy import data, sim
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
