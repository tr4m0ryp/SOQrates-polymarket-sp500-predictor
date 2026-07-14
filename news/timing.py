"""When does decisive overnight news hit? Timing profile for the LLM layer.

For each news-affected day the decisive hour is the hour-over-hour gap change
with the largest magnitude (the move that made or broke the call). The
cumulative profile answers: "if the LLM last ran at hour H, what share of
decisive moves had already happened?"
"""
import json

from config import CACHE

HOURS = range(1, 10)


def decisive_hour(gaps: dict[int, float]) -> tuple[int, float]:
    best_h, best = None, 0.0
    hs = sorted(gaps)
    for prev, h in zip(hs, hs[1:]):
        d = abs(gaps[h] - gaps[prev])
        if d >= best:
            best, best_h = d, h
    return best_h, best


def profile(rows: list[dict], mistakes: list[dict]) -> dict:
    by_date = {r["date"]: r for r in rows}
    hist = {k: {h: 0 for h in HOURS} for k in
            ("news_miss", "news_swing", "news_survived", "all")}
    for m in mistakes:
        gaps = by_date[m["date"]]["es"]
        h, _ = decisive_hour(gaps)
        if h is None:
            continue
        hist[m["kind"]][h] += 1
        hist["all"][h] += 1
    out = {"hist": hist, "cum": {}}
    for kind, hs in hist.items():
        total = sum(hs.values()) or 1
        run = 0
        out["cum"][kind] = {}
        for h in HOURS:
            run += hs[h]
            out["cum"][kind][h] = run / total
    (CACHE / "news_timing.json").write_text(json.dumps(out, indent=1))
    return out
