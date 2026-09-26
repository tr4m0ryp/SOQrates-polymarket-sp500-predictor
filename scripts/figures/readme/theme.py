"""Shared theme palette, output settings, and drawing primitives for the README visuals."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[3] / "docs" / "research" / "figures" / "readme"
DPI = 200
THEMES: dict[str, dict[str, str]] = {
    "light": {"bg": "#ffffff", "fg": "#1f2328", "muted": "#59636e", "box": "#f6f8fa",
              "edge": "#d1d9e0", "grid": "#e6e9ec", "blue": "#0969da",
              "orange": "#bc4c00", "green": "#1a7f37", "green_fill": "#dafbe1"},
    "dark": {"bg": "#0d1117", "fg": "#e6edf3", "muted": "#9198a1", "box": "#161b22",
             "edge": "#3d444d", "grid": "#262c36", "blue": "#4c9be8",
             "orange": "#f0883e", "green": "#3fb950", "green_fill": "#12261e"},
}


def new_canvas(theme: str, size: tuple[float, float]) -> tuple[Figure, Axes, dict[str, str]]:
    """Create a themed figure with one axes; returns (fig, ax, colors)."""
    c = THEMES[theme]
    fig, ax = plt.subplots(figsize=size)
    fig.patch.set_facecolor(c["bg"])
    ax.set_facecolor(c["bg"])
    return fig, ax, c


def save(fig: Figure, path: Path, bg: str) -> None:
    """Save at the shared DPI with a tight bounding box, then close."""
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=bg)
    plt.close(fig)


def draw_box(ax: Axes, cx: float, cy: float, w: float, h: float, text: str,
             face: str, edge: str, color: str, size: float = 13, weight: str = "normal",
             linestyle: str | tuple = "solid") -> None:
    """Draw a rounded box centred on (cx, cy) with centred text."""
    box = FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.18",
                         facecolor=face, edgecolor=edge, linewidth=1.6, linestyle=linestyle)
    ax.add_patch(box)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=size, color=color,
            weight=weight, linespacing=1.5)


def draw_arrow(ax: Axes, start: tuple[float, float], end: tuple[float, float], color: str) -> None:
    """Draw a solid arrow between two points."""
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=20,
                                 color=color, linewidth=1.8, shrinkA=0, shrinkB=0))
