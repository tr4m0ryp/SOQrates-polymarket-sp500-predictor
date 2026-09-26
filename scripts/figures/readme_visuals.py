"""Regenerate every README diagram (pipeline, accuracy, misses, news), light and dark."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from readme import OUT_DIR, THEMES, render_accuracy, render_misses, render_news, render_pipeline

RENDERERS: dict[str, Callable[[str, Path], None]] = {
    "pipeline": render_pipeline,
    "accuracy": render_accuracy,
    "misses": render_misses,
    "news": render_news,
}


def main() -> None:
    """Write a light and a dark PNG for every README figure."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for theme in THEMES:
        for name, fn in RENDERERS.items():
            path = OUT_DIR / f"{name}-{theme}.png"
            fn(theme, path)
            written.append(path)
    print(f"Wrote {len(written)} figures to {OUT_DIR}")


if __name__ == "__main__":
    main()
