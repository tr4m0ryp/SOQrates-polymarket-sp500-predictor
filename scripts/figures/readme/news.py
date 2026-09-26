"""News-layer flow diagram: two bounded input groups fused with the futures model."""

from __future__ import annotations

from pathlib import Path

from .theme import draw_arrow, draw_box, new_canvas, save

COL_A = 3.0
COL_B = 9.0
COL_W = 5.6
FUSE_X = 5.0
NOTE_X = 10.0
Y_HEAD = 18.35
Y_IN, H_IN = 16.4, 1.75
Y_OUT, H_OUT = 13.35, 2.45
Y_FIT, H_FIT = 9.7, 2.55
Y_GUARD, H_GUARD = 7.25, 1.4
Y_FUSE, H_FUSE = 5.25, 1.15
Y_PUP, H_PUP = 3.35, 1.05
TEXT_A_IN = "Inputs: release calendar, earnings,\nnowcast vs consensus,\nprediction-market odds"
TEXT_A_OUT = ("Variance multiplier $m_A \\in [1, 2.5]$\n(anchored at fitted 1.29)\n"
              "Tilt $|d_A| \\leq 0.3$ only on\nnowcast-consensus disagreement")
TEXT_B_IN = "Inputs: GDELT + Alpaca\nheadlines since last run"
TEXT_B_OUT = "LLM output: direction, confidence,\nevent type, shock flag"
TEXT_FIT = ("Post-shock: widen $\\sigma$\n(after a \u2265 0.35% one-hour move)\n"
            "Conflicted day: shock sign,\n$\\mu_B = 0.9\\,d_B\\,c\\,\\sigma_m$ (85.4% hit, n = 41)")


def render_news(theme: str, path: Path) -> None:
    """Render the news-layer flow diagram for one theme."""
    fig, ax, c = new_canvas(theme, (11, 12.4))
    ax.set_xlim(0, 12)
    ax.set_ylim(2.5, 19.2)
    ax.axis("off")
    ax.set_title("The news layer: a bounded second voice", fontsize=16, color=c["fg"],
                 weight="bold", pad=10)
    box = {"face": c["box"], "edge": c["edge"], "color": c["fg"], "size": 12}
    heads = ((COL_A, "Group A: midnight briefing\n(00:05)"),
             (COL_B, "Group B: headline checkpoints\n(02:30 to 09:15 + triggers)"))
    for cx, head in heads:
        ax.text(cx, Y_HEAD, head, ha="center", va="center", fontsize=13, weight="bold",
                color=c["blue"], linespacing=1.4)
    draw_box(ax, COL_A, Y_IN, COL_W, H_IN, TEXT_A_IN, **box)
    draw_box(ax, COL_B, Y_IN, COL_W, H_IN, TEXT_B_IN, **box)
    draw_box(ax, COL_A, Y_OUT, COL_W, H_OUT, TEXT_A_OUT, face=c["box"], edge=c["blue"],
             color=c["fg"], size=12)
    draw_box(ax, COL_B, Y_OUT, COL_W, H_OUT, TEXT_B_OUT, **box)
    draw_box(ax, COL_B, Y_FIT, COL_W, H_FIT, TEXT_FIT, face=c["box"], edge=c["blue"],
             color=c["fg"], size=12)
    ax.text(COL_B, Y_FIT + H_FIT / 2 + 0.12, "Fitted effects, not raw opinions", ha="center",
            va="bottom", fontsize=12, weight="bold", color=c["blue"])
    for cx in (COL_A, COL_B):
        draw_arrow(ax, (cx, Y_IN - H_IN / 2 - 0.05), (cx, Y_OUT + H_OUT / 2 + 0.08), c["muted"])
    draw_arrow(ax, (COL_B, Y_OUT - H_OUT / 2 - 0.05), (COL_B, Y_FIT + H_FIT / 2 + 0.6), c["muted"])
    draw_arrow(ax, (COL_A, Y_OUT - H_OUT / 2 - 0.05), (COL_A, Y_GUARD + H_GUARD / 2 + 0.08), c["muted"])
    draw_arrow(ax, (COL_B, Y_FIT - H_FIT / 2 - 0.05), (COL_B, Y_GUARD + H_GUARD / 2 + 0.08), c["muted"])
    draw_box(ax, 6.0, Y_GUARD, 11.6, H_GUARD,
             "Validators clamp every field; $\\sigma$ floor 0.25%:\nit can nudge and widen, never dominate",
             face=c["bg"], edge=c["orange"], color=c["fg"], size=12.5, weight="bold")
    draw_arrow(ax, (FUSE_X, Y_GUARD - H_GUARD / 2 - 0.05), (FUSE_X, Y_FUSE + H_FUSE / 2 + 0.08), c["muted"])
    draw_box(ax, FUSE_X, Y_FUSE, 5.6, H_FUSE, "Inverse-variance fusion\nwith the futures model", **box)
    draw_arrow(ax, (FUSE_X, Y_FUSE - H_FUSE / 2 - 0.05), (FUSE_X, Y_PUP + H_PUP / 2 + 0.08), c["muted"])
    draw_box(ax, FUSE_X, Y_PUP, 3.2, H_PUP, "P(up)", face=c["green_fill"], edge=c["green"],
             color=c["fg"], size=14, weight="bold")
    draw_box(ax, NOTE_X, (Y_FUSE + Y_PUP) / 2, 3.5, 2.3,
             "Never sees market prices\nor the model's position.\nMarket moves only\ntrigger a run.",
             face=c["bg"], edge=c["muted"], color=c["muted"], size=11.5, linestyle=(0, (4, 3)))
    save(fig, path, c["bg"])
