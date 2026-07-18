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


_VOICES = None                      # date -> {"04:00": voice, ...}
_CP_MIN = {"04:00": 240, "07:00": 420, "08:35": 515}


def _llm_voices() -> dict:
    global _VOICES
    if _VOICES is None:
        f = CACHE / "news_voice.json"
        _VOICES = json.loads(f.read_text()) if f.exists() else {}
    return _VOICES


def _llm_p(day: dict, minute: int) -> float | None:
    """Fuse the replayed LLM voice (latest checkpoint <= minute) with the
    model at the in-force hour, using the production groupb.voice() math.
    Falls back to the plain model P when no voice exists."""
    from math import erf, sqrt
    from news import groupb
    voices = _llm_voices().get(day["date"])
    base = model_p_at(day, minute, "model")
    if not voices or base is None:
        return base
    live_cp = [cp for cp, m in sorted(_CP_MIN.items(), key=lambda x: x[1])
               if m <= minute and cp in voices]
    if not live_cp:
        return base
    v = voices[live_cp[-1]]
    hours = sorted(int(h) for h in day["model_mu"] if int(h) * 60 <= minute)
    if not hours:
        return base
    h = hours[-1]
    mu = day["model_mu"][str(h)] if str(h) in day["model_mu"] else day["model_mu"][h]
    sig = day["model_sigma"][str(h)] if str(h) in day["model_sigma"] else day["model_sigma"][h]
    gap = day["es"].get(str(h), day["es"].get(h))
    if gap is None:
        return base
    recent = bool(v.get("shock")) or float(v.get("sigma_mult", 1.0)) > 1.0
    mu_b, sig_b, s_mult = groupb.voice(float(v["direction"]),
                                       float(v["confidence"]),
                                       gap, sig, recent)
    sig_eff = sig * max(s_mult, float(v.get("sigma_mult", 1.0)))
    w = 1 / sig_eff ** 2
    wb = 0.0 if sig_b == float("inf") else 1 / sig_b ** 2
    mu_f = (mu * w + mu_b * wb) / (w + wb)
    sig_f = (1 / (w + wb)) ** 0.5
    return 0.5 * (1 + erf(mu_f / sig_f / sqrt(2)))


def model_p_at(day: dict, minute: int, signal: str = "model") -> float | None:
    """Signal P(up) in force at a minute (hourly refresh, hold last).
    signal='model' = futures model alone; 'news' = + deterministic Group-B
    overlay; 'llm' = + replayed LLM voice (needs .cache/news_voice.json)."""
    if signal == "llm":
        return _llm_p(day, minute)
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
