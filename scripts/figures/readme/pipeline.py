"""Gap-to-trade pipeline diagram."""

from __future__ import annotations

from pathlib import Path

from .theme import draw_arrow, draw_box, new_canvas, save

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


def render_pipeline(theme: str, path: Path) -> None:
    """Render the gap-to-trade pipeline diagram for one theme."""
    fig, ax, c = new_canvas(theme, (10, 9.2))
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
    save(fig, path, c["bg"])
