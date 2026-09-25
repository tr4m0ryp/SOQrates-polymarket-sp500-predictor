"""Baseline comparison table for the SOQrates paper (crowd / k=1 / logistic).

Evaluates every method on the paper's validated test window: the second
half of the 200-trading-day dataset window ending 2026-07-13 (the "200-day
numbers remain the validated reference" of the paper), i.e. the 100 days
2026-02-12..2026-07-13, split chronologically, nothing fitted on the test
half. Methods:

  crowd     Polymarket UP-token book midpoint at the decision minute, from
            the cached minute curves under .cache/pm_history/ (no fetching).
  k=1       naive full-gap carryover: call = sign of the overnight ES gap
            at the decision hour, probability hard 0/1 (Brier = miss rate).
  logistic  P(up) = sigmoid(b0 + b1 g) on the ES gap alone, one fit per
            decision hour, Newton-Raphson on the train half only (stdlib).
  SOQrates  the production hand-off (v1.3 before 5:00 ET, v1.2 after),
            fitted on the train half only.

Metrics per decision time: direction accuracy (with n) and Brier score,
under the run.py convention that p > 0.5 calls UP. A paired block repeats
model rows on the exact crowd-covered subset so crowd-vs-model cells are
apples-to-apples. Run from the repo root:  python3 -m open_predictor.evaluation.backtest.baselines
"""
import datetime as dt
import json
import math

from open_predictor.config import NY
from open_predictor.evaluation.backtest import dataset
from open_predictor.forecast.model.core import ModelProd
from open_predictor.trading.polymarket.history import HIST_DIR

PAPER_END = "2026-07-13"    # last dataset day when the paper numbers were run
WINDOW = 200                # the paper's validated dataset window, days
HOURS = (0, 4, 9)           # decision times 00:00 / 04:00 / 09:00 ET
MINUTES = {0: 0, 4: 240, 9: 540}
LAST_MINUTE = 9 * 60 + 29   # 9:29 ET, crowd-only extra decision time


def paper_window(rows: list[dict]) -> list[dict]:
    upto = [r for r in rows if r["date"] <= PAPER_END]
    if len(upto) < WINDOW:
        raise SystemExit(f"dataset has {len(upto)} days <= {PAPER_END}, "
                         f"need {WINDOW}; rebuild with --rebuild")
    return upto[-WINDOW:]


def crowd_curves(dates: set[str]) -> dict[str, list[list]]:
    """date -> sorted [(minute_of_day_ET, p_up)], market date only.

    Same construction as strategy.data._minute_curve, applied straight to
    the pm_history cache so no strategy-side filtering (>= 60 points) hides
    days from the baseline.
    """
    out = {}
    for f in sorted(HIST_DIR.glob("*.json")):
        if f.stem not in dates:
            continue
        rec = json.loads(f.read_text())
        if not rec.get("history"):
            continue
        d = dt.date(*map(int, f.stem.split("-")))
        dedup = {}
        for pt in rec["history"]:
            ts = dt.datetime.fromtimestamp(pt["t"], dt.timezone.utc).astimezone(NY)
            m = ts.hour * 60 + ts.minute
            if ts.date() == d and m <= LAST_MINUTE:
                dedup[m] = pt["p"]      # last quote wins within a minute
        if dedup:
            out[f.stem] = sorted([m, p] for m, p in dedup.items())
    return out


def crowd_p(curve: list[list], minute: int) -> float | None:
    best = None
    for m, p in curve:
        if m <= minute:
            best = p
        else:
            break
    return best


def fit_logistic(pairs: list[tuple[float, int]], iters: int = 50) -> tuple[float, float]:
    """Newton-Raphson logistic fit of y on [1, g]; tiny ridge for stability."""
    b0 = b1 = 0.0
    lam = 1e-6
    for _ in range(iters):
        g0 = g1 = h00 = h01 = h11 = 0.0
        for g, y in pairs:
            p = 1 / (1 + math.exp(-max(-35.0, min(35.0, b0 + b1 * g))))
            w = p * (1 - p)
            g0 += y - p
            g1 += (y - p) * g
            h00 += w
            h01 += w * g
            h11 += w * g * g
        h00 += lam
        h11 += lam
        det = h00 * h11 - h01 * h01
        if not det:
            break
        d0 = (h11 * g0 - h01 * g1) / det
        d1 = (h00 * g1 - h01 * g0) / det
        b0, b1 = b0 + d0, b1 + d1
        if abs(d0) + abs(d1) < 1e-12:
            break
    return b0, b1


def score(preds: list[tuple[float, bool]]) -> dict:
    """Direction accuracy + Brier under the run.py convention (p>0.5 = UP)."""
    n = len(preds)
    if not n:
        return {"n": 0, "acc": float("nan"), "brier": float("nan")}
    hit = sum((p > 0.5) == o for p, o in preds)
    br = sum((p - (1.0 if o else 0.0)) ** 2 for p, o in preds)
    return {"n": n, "acc": hit / n, "brier": br / n}


def build_table() -> dict:
    rows = dataset.load()
    window = paper_window(rows)
    half = len(window) // 2
    train, test = window[:half], window[half:]
    curves = crowd_curves({r["date"] for r in test})
    model = ModelProd().fit(train)
    logits = {h: fit_logistic([(r["es"][h], int(r["off"] > 0))
                               for r in train if h in r["es"]])
              for h in HOURS}

    out = {"window": (window[0]["date"], window[-1]["date"]),
           "test": (test[0]["date"], test[-1]["date"], len(test)),
           "logits": logits, "cells": {}, "paired": {}, "crowd_929": None}
    for h in HOURS:
        days = [r for r in test if h in r["es"]]
        b0, b1 = logits[h]
        sq = [(model.predict(r, h)[2], r["off"] > 0) for r in days]
        k1 = [(1.0 if r["es"][h] > 0 else 0.0, r["off"] > 0) for r in days]
        lg = [(1 / (1 + math.exp(-(b0 + b1 * r["es"][h]))), r["off"] > 0)
              for r in days]
        cw, sq_sub = [], []
        for r in days:
            p = crowd_p(curves.get(r["date"], []), MINUTES[h])
            if p is not None:
                cw.append((p, r["off"] > 0))
                sq_sub.append((model.predict(r, h)[2], r["off"] > 0))
        out["cells"][h] = {"crowd": score(cw), "k1": score(k1),
                           "logistic": score(lg), "soqrates": score(sq)}
        out["paired"][h] = score(sq_sub)
    c929 = [(p, r["off"] > 0) for r in test
            if (p := crowd_p(curves.get(r["date"], []), LAST_MINUTE)) is not None]
    out["crowd_929"] = score(c929)
    return out


def main():
    t = build_table()
    print(f"paper window: {t['window'][0]}..{t['window'][1]} ({WINDOW} days), "
          f"test half {t['test'][0]}..{t['test'][1]} (n={t['test'][2]})")
    print(f"\n{'time (ET)':10}{'method':10}{'n':>4} {'acc':>7} {'Brier':>8}")
    for h in HOURS:
        label = f"{h:02d}:00"
        for name in ("crowd", "k1", "logistic", "soqrates"):
            s = t["cells"][h][name]
            print(f"{label:10}{name:10}{s['n']:>4} {s['acc']*100:6.1f}% "
                  f"{s['brier']:8.4f}")
            label = ""
    s = t["crowd_929"]
    print(f"{'09:29':10}{'crowd':10}{s['n']:>4} {s['acc']*100:6.1f}% "
          f"{s['brier']:8.4f}   (model/gap rows need minute futures: none cached)")
    print("\nSOQrates on the crowd-covered subset (paired cells):")
    for h in HOURS:
        s, c = t["paired"][h], t["cells"][h]["crowd"]
        print(f"  {h:02d}:00  n={s['n']}  model {s['acc']*100:.1f}% / "
              f"{s['brier']:.4f}   crowd {c['acc']*100:.1f}% / {c['brier']:.4f}")
    print("\nlogistic fits (train half only): " +
          ", ".join(f"h{h}: b0={b[0]:+.4f} b1={b[1]:+.4f}"
                    for h, b in t["logits"].items()))


if __name__ == "__main__":
    main()
