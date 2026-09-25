"""Regenerate the README diagrams (pipeline flow and accuracy ladder), light and dark."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "research" / "figures" / "readme"
DPI = 200
THEMES: dict[str, dict[str, str]] = {
    "light": {"bg": "#ffffff", "fg": "#1f2328", "muted": "#59636e", "box": "#f6f8fa",
              "edge": "#d1d9e0", "grid": "#e6e9ec", "blue": "#0969da",
              "orange": "#bc4c00", "green": "#1a7f37", "green_fill": "#dafbe1"},
    "dark": {"bg": "#0d1117", "fg": "#e6edf3", "muted": "#9198a1", "box": "#161b22",
             "edge": "#3d444d", "grid": "#262c36", "blue": "#4c9be8",
             "orange": "#f0883e", "green": "#3fb950", "green_fill": "#12261e"},
}
MAIN_X = 3.2
BOX_W = 5.0
BOX_H = 1.15
MAIN_STEPS: list[tuple[float, str]] = [
    (10.6, "Overnight futures gap $g$\n(E-mini S&P)"),
    (8.2, "Predicted official gap\n$a_0 + k\\,g$"),
    (5.8, "P(official open is UP)\n$= \\Phi$(predicted gap / $\\sigma$)"),
    (3.4, "Compare with\nPolymarket price $q$"),
    (1.0, "Trade only if confident\nAND edge $\\geq$ 5 cents"),
]
ACCURACY: list[tuple[str, float, float, float, float, int]] = [
    ("00:00", 0.0, 72.5, 65.9, 78.2, 200),
    ("04:00", 4.0, 77.0, 70.7, 82.3, 200),
    ("06:00", 6.0, 82.0, 75.5, 86.3, 200),
    ("07:00", 7.0, 85.0, 78.3, 88.4, 200),
    ("09:00", 9.0, 90.0, 83.9, 92.6, 200),
    ("09:29", 9.483, 94.0, 74.2, 99.0, 18),
]
CEILING = 96.3


def draw_box(ax: Axes, cx: float, cy: float, w: float, h: float, text: str,
             face: str, edge: str, color: str, size: float = 13, weight: str = "normal") -> None:
    """Draw a rounded box centred on (cx, cy) with centred text."""
    box = FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.18",
                         facecolor=face, edgecolor=edge, linewidth=1.6)
    ax.add_patch(box)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=size, color=color,
            weight=weight, linespacing=1.5)


def draw_arrow(ax: Axes, start: tuple[float, float], end: tuple[float, float], color: str) -> None:
    """Draw a solid arrow between two points."""
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=20,
                                 color=color, linewidth=1.8, shrinkA=0, shrinkB=0))


def render_pipeline(theme: str, path: Path) -> None:
    """Render the gap-to-trade pipeline diagram for one theme."""
    c = THEMES[theme]
    fig, ax = plt.subplots(figsize=(10, 9.2))
    fig.patch.set_facecolor(c["bg"])
    ax.set_facecolor(c["bg"])
    ax.set_xlim(0, 10)
    ax.set_ylim(0.2, 12.0)
    ax.axis("off")
    ax.set_title("How SOQrates turns the overnight gap into a trade", fontsize=16,
                 color=c["fg"], weight="bold", pad=10)
    for i, (cy, label) in enumerate(MAIN_STEPS):
        final = i == len(MAIN_STEPS) - 1
        draw_box(ax, MAIN_X, cy, BOX_W, BOX_H, label,
                 face=c["green_fill"] if final else c["box"],
                 edge=c["green"] if final else c["edge"], color=c["fg"],
                 weight="bold" if final else "normal")
        if not final:
            nxt = MAIN_STEPS[i + 1][0]
            draw_arrow(ax, (MAIN_X, cy - BOX_H / 2 - 0.05), (MAIN_X, nxt + BOX_H / 2 + 0.08), c["muted"])
    mid1 = (MAIN_STEPS[0][0] + MAIN_STEPS[1][0]) / 2
    ax.text(MAIN_X + 0.25, mid1, "$\\times\\,k \\approx 0.8$", ha="left", va="center",
            fontsize=13, color=c["blue"], weight="bold")
    note_x = 7.9
    draw_box(ax, note_x, mid1, 3.4, 1.35,
             "The crowd assumes $k = 1$.\nMeasured: $k \\approx$ 0.77-0.80",
             face=c["bg"], edge=c["orange"], color=c["fg"], size=12)
    ax.plot([MAIN_X + 1.75, note_x - 1.72], [mid1, mid1], color=c["orange"],
            linewidth=1.3, linestyle=(0, (3, 3)))
    sig_y = MAIN_STEPS[2][0]
    draw_box(ax, note_x, sig_y, 3.4, 1.35, "Uncertainty $\\sigma(\\tau)$\nshrinks toward 9:30",
             face=c["box"], edge=c["blue"], color=c["fg"], size=12)
    draw_arrow(ax, (note_x - 1.72, sig_y), (MAIN_X + BOX_W / 2 + 0.06, sig_y), c["blue"])
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=c["bg"])
    plt.close(fig)


def render_accuracy(theme: str, path: Path) -> None:
    """Render the out-of-sample accuracy ladder for one theme."""
    c = THEMES[theme]
    fig, ax = plt.subplots(figsize=(9, 5.6))
    fig.patch.set_facecolor(c["bg"])
    ax.set_facecolor(c["bg"])
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
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=c["bg"])
    plt.close(fig)


def main() -> None:
    """Write all four README PNGs."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for theme in THEMES:
        for name, fn in (("pipeline", render_pipeline), ("accuracy", render_accuracy)):
            path = OUT_DIR / f"{name}-{theme}.png"
            fn(theme, path)
            written.append(path)
    print(f"Wrote {len(written)} figures to {OUT_DIR}")


if __name__ == "__main__":
    main()
