"""Results charts: the out-of-sample accuracy ladder and the midnight-miss breakdown."""

from __future__ import annotations

from pathlib import Path

from .theme import new_canvas, save

ACCURACY: list[tuple[str, float, float, float, float, int]] = [
    ("00:00", 0.0, 72.5, 65.9, 78.2, 200),
    ("04:00", 4.0, 77.0, 70.7, 82.3, 200),
    ("06:00", 6.0, 82.0, 75.5, 86.3, 200),
    ("07:00", 7.0, 85.0, 78.3, 88.4, 200),
    ("09:00", 9.0, 90.0, 83.9, 92.6, 200),
    ("09:29", 9.483, 94.0, 74.2, 99.0, 18),
]
CEILING = 96.3
MISSES: list[tuple[int, str, str, bool]] = [
    (33, "Coin tosses", "model near 50/50,\nno signal", False),
    (51, "Overnight news reversals", "information after midnight\nflipped the gap", True),
    (16, "Auction quirks", "futures held, official\nprint landed opposite", False),
]


def render_accuracy(theme: str, path: Path) -> None:
    """Render the out-of-sample accuracy ladder for one theme."""
    fig, ax, c = new_canvas(theme, (9, 5.6))
    xs = [row[1] for row in ACCURACY]
    ys = [row[2] for row in ACCURACY]
    ax.axhline(CEILING, color=c["green"], linestyle="--", linewidth=1.4, zorder=1)
    ax.text(0.0, CEILING + 0.9, f"Ceiling with perfect 9:30 futures data: {CEILING}%",
            color=c["green"], fontsize=11, ha="left", va="bottom")
    ax.axhline(50, color=c["muted"], linestyle=":", linewidth=1.6, zorder=1)
    ax.text(0.0, 51.0, "Coin flip", color=c["muted"], fontsize=11, ha="left", va="bottom")
    ax.plot(xs, ys, color=c["blue"], linewidth=2.0, zorder=2)
    for label, x, y, lo, hi, n in ACCURACY:
        hollow = n < 200
        ax.errorbar(x, y, yerr=[[y - lo], [hi - y]], fmt="none", ecolor=c["blue"],
                    elinewidth=1.6, capsize=5, capthick=1.6, zorder=3,
                    alpha=0.6 if hollow else 1.0)
        ax.plot(x, y, marker="D" if hollow else "o", markersize=9 if hollow else 8,
                markerfacecolor=c["bg"] if hollow else c["blue"], markeredgecolor=c["blue"],
                markeredgewidth=2.0, zorder=4, linestyle="none")
        text = f"~{y:.0f}%" if hollow else f"{y:g}%"
        if hollow:
            ax.annotate(f"{text}\nn = 18", (x, y), xytext=(14, -4), textcoords="offset points",
                        ha="left", va="center", fontsize=12, color=c["fg"], weight="bold")
        else:
            ax.annotate(text, (x, y), xytext=(-10, 10), textcoords="offset points",
                        ha="right", va="bottom", fontsize=12, color=c["fg"], weight="bold")
    ax.set_xticks(xs, [row[0] for row in ACCURACY])
    ticks = ax.get_xticklabels()
    ticks[-2].set_horizontalalignment("right")
    ticks[-1].set_horizontalalignment("left")
    ax.set_xlim(-0.6, 10.6)
    ax.set_ylim(45, 100)
    ax.set_xlabel("Prediction time (ET)", fontsize=13, color=c["fg"])
    ax.set_ylabel("Direction accuracy (%)", fontsize=13, color=c["fg"])
    ax.tick_params(colors=c["fg"], labelsize=12)
    ax.grid(True, color=c["grid"], linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(c["edge"])
    fig.suptitle("Out-of-sample accuracy climbs toward the open", fontsize=16,
                 color=c["fg"], weight="bold", x=0.08, ha="left", y=0.99)
    ax.set_title("200 trading days, Sep 2025 to Jul 2026; bars are 95% CIs",
                 fontsize=11.5, color=c["muted"], loc="left", pad=10)
    fig.tight_layout()
    save(fig, path, c["bg"])


def render_misses(theme: str, path: Path) -> None:
    """Render the stacked breakdown of the 55 wrong midnight calls for one theme."""
    fig, ax, c = new_canvas(theme, (9, 3.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(-3.1, 1.6)
    ax.axis("off")
    left = 0.0
    for pct, label, detail, accent in MISSES:
        face = c["blue"] if accent else c["box"]
        ax.barh(0.6, pct, left=left, height=1.3, color=face, edgecolor=c["bg"] if accent else c["edge"],
                linewidth=1.6)
        mid = left + pct / 2
        ax.text(mid, 0.6, f"{pct}%", ha="center", va="center", fontsize=17, weight="bold",
                color=c["bg"] if accent else c["fg"])
        ax.text(mid, -0.35, label, ha="center", va="top", fontsize=12, weight="bold",
                color=c["blue"] if accent else c["fg"])
        ax.text(mid, -0.95, detail, ha="center", va="top", fontsize=11, color=c["muted"],
                linespacing=1.4)
        left += pct
    ax.text(0, -2.75, "55 midnight misses over 200 trading days; zero unexplained",
            ha="left", va="top", fontsize=11, color=c["muted"], style="italic")
    fig.suptitle("Why the midnight call misses", fontsize=16, color=c["fg"], weight="bold",
                 x=0.125, ha="left", y=0.98)
    save(fig, path, c["bg"])
