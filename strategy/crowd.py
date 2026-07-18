"""Crowd model: predict what the futures-following market will do.

The crowd prices P(up) ~= Phi(gap / sigma_crowd(h)) off the live ES gap with
k=1. Fitting sigma_crowd per hour on the train half gives a forecast of the
market's own future price path (the gap is ~martingale), which lets rules
trade CONVERGENCE — sell into the crowd's predictable repricing instead of
carrying binary resolution risk.
"""
import json
from statistics import NormalDist

from config import CACHE
from strategy.data import market_p_at

_N = NormalDist()
_CACHE_FILE = CACHE / "crowd_fit.json"


def _hour_val(d: dict, h: int):
    return d.get(h, d.get(str(h)))


def fit(train_days: list[dict]) -> dict:
    """Median implied sigma_crowd per ET hour, train half only."""
    sig = {}
    for h in range(10):
        vals = []
        for day in train_days:
            gap = _hour_val(day["es"], h)
            p = market_p_at(day, h * 60)
            if gap is None or p is None or not 0.03 <= p <= 0.97:
                continue
            z = _N.inv_cdf(p)
            if abs(z) >= 0.05 and abs(gap) >= 0.03 and gap / z > 0:
                vals.append(gap / z)
        if len(vals) >= 8:
            vals.sort()
            sig[h] = round(vals[len(vals) // 2], 4)
    _CACHE_FILE.write_text(json.dumps(sig))
    return sig


def load() -> dict:
    if _CACHE_FILE.exists():
        return {int(h): s for h, s in json.loads(_CACHE_FILE.read_text()).items()}
    return {}


def _sigma_at(fitted: dict, h: int) -> float | None:
    live = [s for hh, s in sorted(fitted.items()) if hh <= h]
    return live[-1] if live else None


def crowd_p(gap: float, h: int, fitted: dict) -> float | None:
    """Predicted crowd price at hour h given a live ES gap."""
    s = _sigma_at(fitted, h)
    return _N.cdf(gap / s) if s else None


def forecast(day: dict, minute_now: int, h_exit: int, fitted: dict) -> float | None:
    """Expected market P(up) at h_exit given the gap known at minute_now."""
    hours = sorted(int(h) for h in day["es"]
                   if _hour_val(day["es"], int(h)) is not None)
    known = [h for h in hours if h * 60 <= minute_now]
    if not known:
        return None
    gap_now = _hour_val(day["es"], known[-1])
    return crowd_p(gap_now, h_exit, fitted)
