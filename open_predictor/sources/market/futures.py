"""Overnight futures gap paths against the prior-day 16:00 ET reference."""
import bisect
import datetime as dt

from open_predictor.config import NY, LOOKBACK_DAYS
from open_predictor.sources.market import yahoo

SYMBOLS = ("ES=F", "NQ=F", "YM=F")


class HourlyFeed:
    def __init__(self, symbol: str, days_back: int = LOOKBACK_DAYS):
        self.bars = yahoo.hourly_closes(symbol, days_back)
        self.index = sorted(self.bars)

    def price_at(self, utc_ts: int, tolerance: int = 3900):
        i = bisect.bisect_right(self.index, utc_ts) - 1
        if i >= 0 and utc_ts - self.index[i] <= tolerance:
            return self.bars[self.index[i]]
        return None


def _et(date_str: str, hour: int, minute: int = 0) -> int:
    y, m, d = map(int, date_str.split("-"))
    return int(dt.datetime(y, m, d, hour, minute, tzinfo=NY).timestamp())


def load_feeds() -> dict[str, HourlyFeed]:
    return {s: HourlyFeed(s) for s in SYMBOLS}


def gap_path(feed: HourlyFeed, date: str, prior_date: str,
             hours=range(10)) -> dict[int, float] | None:
    """% gap vs prior-day 16:00 ET at each requested hour of `date`."""
    ref = feed.price_at(_et(prior_date, 16))
    if ref is None:
        return None
    path = {}
    for h in hours:
        px = feed.price_at(_et(date, h))
        if px is not None:
            path[h] = (px / ref - 1) * 100
    return path


def prior_day_rv(feed: HourlyFeed, prior_date: str) -> float:
    """Sum of squared hourly returns 10:00-16:00 ET (realized-variance proxy)."""
    rv, prev = 0.0, None
    for h in range(10, 17):
        px = feed.price_at(_et(prior_date, h))
        if px is not None and prev is not None:
            rv += ((px / prev - 1) * 100) ** 2
        if px is not None:
            prev = px
    return rv


def live_gap(feed: HourlyFeed, prior_date: str, now_utc: int) -> float | None:
    ref = feed.price_at(_et(prior_date, 16))
    px = feed.price_at(now_utc)
    if ref is None or px is None:
        return None
    return (px / ref - 1) * 100
