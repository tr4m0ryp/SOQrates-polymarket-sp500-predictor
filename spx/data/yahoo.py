"""Yahoo v8 chart API fetchers (stdlib only)."""
import json
import time
import urllib.parse
import urllib.request
import datetime as dt

from config import NY

_UA = {"User-Agent": "Mozilla/5.0"}


def _get(url: str, retries: int = 4):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=_UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(1 + 2 * i)


def chart(symbol: str, interval: str, days_back: int, prepost: bool = False):
    """Return (timestamps, closes, result) for a symbol/interval window."""
    now = int(time.time())
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.parse.quote(symbol)}?period1={now - days_back * 86400}"
        f"&period2={now}&interval={interval}"
        + ("&includePrePost=true" if prepost else "")
    )
    res = _get(url)["chart"]["result"][0]
    closes = res["indicators"]["quote"][0]["close"]
    ts = res["timestamp"]
    return ts, closes, res


def hourly_closes(symbol: str, days_back: int) -> dict[int, float]:
    """utc_ts_of_bar_END -> close. Bar end = bar start + 3600."""
    ts, closes, _ = chart(symbol, "60m", days_back)
    return {t + 3600: c for t, c in zip(ts, closes) if c is not None}


def daily_open_close(symbol: str, days_back: int) -> dict[str, tuple[float, float]]:
    """ET-date string -> (open, close)."""
    ts, _, res = chart(symbol, "1d", days_back)
    q = res["indicators"]["quote"][0]
    out = {}
    for i, t in enumerate(ts):
        if q["open"][i] is None:
            continue
        d = dt.datetime.fromtimestamp(t, dt.timezone.utc).astimezone(NY).date()
        out[str(d)] = (q["open"][i], q["close"][i])
    return out
