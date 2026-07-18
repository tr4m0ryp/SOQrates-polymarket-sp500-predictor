"""Per-day strategy records: market minute curve joined with model P(up).

The curve comes from Polymarket prices-history, which returns CLOB book
MIDPOINTS, not trades — a dense curve exists even on days with $0 traded
volume (e.g. 2026-03-10). Each record carries the day's meta volume so the
simulator can gate out days where fills would be fictional (sim.MIN_VOLUME)
and cap stakes by real liquidity (sim.LIQ_FRAC)."""
import datetime as dt
import json

from config import CACHE, NY
from pm import history

_CACHE_FILE = CACHE / "strategy_days.json"
LAST_MINUTE = 9 * 60 + 29           # 9:29 ET, last tradeable minute


def _minute_curve(day: str, points: list[dict]) -> list[list]:
    """[(minute_of_day_ET, p_up)] for 00:00-9:29 on the market date."""
    d = dt.date(*map(int, day.split("-")))
    out = []
    for pt in points:
        ts = dt.datetime.fromtimestamp(pt["t"], dt.timezone.utc).astimezone(NY)
        if ts.date() != d:
            continue
        m = ts.hour * 60 + ts.minute
        if m <= LAST_MINUTE:
            out.append([m, pt["p"]])
    dedup = {}
    for m, p in out:                # last quote wins within a minute
        dedup[m] = p
    return sorted([m, p] for m, p in dedup.items())


def _news_p(row: dict, h: int, mu: float, sig: float) -> float:
    """Deterministic Group-B overlay: post-shock sigma widening + the fitted
    conflicted-day direction rule, using only gaps known by hour h. The LLM
    retrieval leg is NOT simulated — this is the futures-derived subset.
    groupb constants are fitted on the dataset train half only (disjoint
    from all strategy days), so this signal carries no look-ahead."""
    from math import erf, sqrt
    from news import groupb
    gaps = {k: v for k, v in row["es"].items() if k <= h}
    sh, delta = groupb.last_shock(gaps)
    recent = sh is not None and h - sh <= groupb.RECENT_HOURS
    direction = (1.0 if delta > 0 else -1.0) if recent else 0.0
    mu_b, sig_b, s_mult = groupb.voice(direction, 0.6, gaps[h], sig, recent)
    sig_eff = sig * s_mult
    w = 1 / sig_eff ** 2
    wb = 0.0 if sig_b == float("inf") else 1 / sig_b ** 2
    mu_f = (mu * w + mu_b * wb) / (w + wb)
    sig_f = (1 / (w + wb)) ** 0.5
    return 0.5 * (1 + erf(mu_f / sig_f / sqrt(2)))


def build(rebuild: bool = False) -> list[dict]:
    if not rebuild and _CACHE_FILE.exists():
        return json.loads(_CACHE_FILE.read_text())

    from backtest import dataset
    from model.core import ModelProd
    rows = dataset.load()
    train, _ = dataset.split(rows)
    model = ModelProd().fit(train)
    by_date = {r["date"]: r for r in rows}

    days = []
    for date, rec in history.load_all().items():
        row = by_date.get(date)
        if row is None:
            continue
        curve = _minute_curve(date, rec["history"])
        if len(curve) < 60:
            continue
        model_p, model_p_news, model_mu, model_sig = {}, {}, {}, {}
        for h in range(10):
            if h not in row["es"]:
                continue
            mu, sig, p = model.predict(row, h)
            model_p[h], model_mu[h], model_sig[h] = round(p, 4), mu, sig
            model_p_news[h] = round(_news_p(row, h, mu, sig), 4)
        if not model_p:
            continue
        days.append({
            "date": date,
            "outcome_up": rec["meta"]["outcome_up"],
            "official_gap": row["off"],
            "volume": rec["meta"]["volume"],
            "release_morning": row["release_morning"],
            "es": row["es"],
            "curve": curve,
            "model_p": model_p,
            "model_p_news": model_p_news,
            "model_mu": model_mu,
            "model_sigma": model_sig,
        })
    days.sort(key=lambda r: r["date"])
    _CACHE_FILE.write_text(json.dumps(days))
    return days


def split(days: list[dict]) -> tuple[list[dict], list[dict]]:
    half = len(days) // 2
    return days[:half], days[half:]


def model_p_at(day: dict, minute: int, signal: str = "model") -> float | None:
    """Signal P(up) in force at a minute (hourly refresh, hold last).
    signal='model' = futures model alone; 'news' = + Group-B overlay."""
    key = "model_p_news" if signal == "news" else "model_p"
    hours = sorted((int(h), p) for h, p in day.get(key, day["model_p"]).items())
    live = [p for h, p in hours if h * 60 <= minute]
    return live[-1] if live else None


def market_p_at(day: dict, minute: int) -> float | None:
    """Latest market quote at or before a minute."""
    best = None
    for m, p in day["curve"]:
        if m <= minute:
            best = p
        else:
            break
    return best
