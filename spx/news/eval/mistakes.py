"""Historical news-mistake inventory - the eval set for the LLM news layer.

A "news mistake" is a day where information arriving AFTER the prediction
hour moved the overnight gap enough to matter:
  news_miss     - committed call (conf >= CONF_COMMIT) that lost because the
                  gap flipped sign after the prediction hour
  news_swing    - coin-flip day where the gap later swung >= SWING_PCT
                  (a news signal could have added conviction either way)
  news_survived - committed call that won despite a >= SWING_PCT swing
                  (negative examples: big news, direction held)
Quirk days (gap held, official printed opposite) are excluded - they are
auction mechanics, not news.
"""
import datetime as dt
import json

from spx.config import CACHE, CONF_COMMIT
from spx.macro import releases

SWING_PCT = 0.35
PRED_HOUR = 0

_WINDOWS = ((2, "late-Asia (00-02)"), (5, "Europe open (02-05)"),
            (8, "US pre-market (05-08)"), (10, "8:30-9:30 data window"))


def _window(hour: int) -> str:
    return next(label for bound, label in _WINDOWS if hour <= bound)


def _swing(gaps: dict[int, float], h0: int) -> tuple[float, int]:
    base = gaps[h0]
    hour, best = h0, 0.0
    for h, g in gaps.items():
        if h > h0 and abs(g - base) > best:
            best, hour = abs(g - base), h
    return best, hour


def build(rows: list[dict], model) -> list[dict]:
    out = []
    for r in rows:
        gaps = r["es"]
        if PRED_HOUR not in gaps:
            continue
        _, _, p = model.predict(r, PRED_HOUR)
        call_up = p > 0.5
        conf = max(p, 1 - p)
        won = call_up == (r["off"] > 0)
        swing, swing_h = _swing(gaps, PRED_HOUR)
        flips = [h for h in sorted(gaps) if h > PRED_HOUR
                 and (gaps[h] > 0) != call_up]
        g_last = gaps[max(gaps)]
        date = dt.date(*map(int, r["date"].split("-")))

        if conf >= CONF_COMMIT and not won:
            if not flips and abs(g_last) >= 0.05:
                continue                      # quirk, not news
            kind, hour = "news_miss", (flips[-1] if flips else max(gaps))
        elif conf < CONF_COMMIT and swing >= SWING_PCT:
            kind, hour = "news_swing", swing_h
        elif conf >= CONF_COMMIT and won and swing >= SWING_PCT:
            kind, hour = "news_survived", swing_h
        else:
            continue
        out.append({
            "date": r["date"], "kind": kind, "conf": round(conf, 2),
            "call": "UP" if call_up else "DOWN", "won": won,
            "official_pct": round(r["off"], 3),
            "swing_pct": round(swing, 2), "event_hour": hour,
            "window": _window(hour),
            "releases": releases.release_names(date),
        })
    out.sort(key=lambda m: (m["kind"] != "news_miss", -m["swing_pct"]))
    (CACHE / "news_mistakes.json").write_text(json.dumps(out, indent=1))
    return out
