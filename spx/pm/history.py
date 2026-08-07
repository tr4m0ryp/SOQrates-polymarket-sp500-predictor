"""Historical SPX-open daily markets: gamma enumeration + minute price curves."""
import datetime as dt
import json
import re
import time
import urllib.request

from spx.config import CACHE, NY

SERIES_ID = 10945
HIST_DIR = CACHE / "pm_history"
_UA = {"User-Agent": "Mozilla/5.0"}
_SLUG_RE = re.compile(r"spx-opens-up-or-down-on-(\w+)-(\d+)-(\d+)")
_MONTHS = ["", "january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december"]
_CHUNK = 20 * 3600          # prices-history returns empty beyond ~1 day spans


def _get(url: str):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _slug_date(slug: str) -> str | None:
    m = _SLUG_RE.match(slug)
    if not m:
        return None
    month, day, year = m.groups()
    if month not in _MONTHS:
        return None
    return f"{int(year):04d}-{_MONTHS.index(month):02d}-{int(day):02d}"


def list_markets() -> list[dict]:
    """All closed daily markets of the series, sorted by date."""
    out, offset = [], 0
    while True:
        events = _get("https://gamma-api.polymarket.com/events"
                      f"?series_id={SERIES_ID}&closed=true&limit=100&offset={offset}")
        if not events:
            break
        offset += len(events)
        for e in events:
            date = _slug_date(e.get("slug", ""))
            m = (e.get("markets") or [{}])[0]
            if not date or not m.get("clobTokenIds"):
                continue
            prices = json.loads(m.get("outcomePrices") or "[]")
            if len(prices) != 2 or float(prices[0]) not in (0.0, 1.0):
                continue                       # unresolved / voided
            out.append({
                "date": date,
                "slug": e["slug"],
                "token_up": json.loads(m["clobTokenIds"])[0],
                "outcome_up": float(prices[0]) == 1.0,
                "volume": float(e.get("volume") or 0),
                "liquidity": float(e.get("liquidity") or 0),
                "start_iso": e.get("startDate"),
            })
    out.sort(key=lambda r: r["date"])
    return out


def _window(meta: dict) -> tuple[int, int]:
    d = dt.date(*map(int, meta["date"].split("-")))
    end = int(dt.datetime(d.year, d.month, d.day, 9, 35, tzinfo=NY).timestamp())
    start = end - 48 * 3600
    if meta.get("start_iso"):
        iso = meta["start_iso"].replace("Z", "+00:00")
        start = max(start, int(dt.datetime.fromisoformat(iso).timestamp()))
    return start, end


def _price_history(token: str, start: int, end: int) -> list[dict]:
    pts, t = [], start
    while t < end:
        hi = min(t + _CHUNK, end)
        d = _get("https://clob.polymarket.com/prices-history"
                 f"?market={token}&startTs={t}&endTs={hi}&fidelity=1")
        pts.extend(d.get("history") or [])
        t = hi
        time.sleep(0.2)
    seen, out = set(), []
    for p in pts:
        if p["t"] not in seen:
            seen.add(p["t"])
            out.append({"t": p["t"], "p": p["p"]})
    return out


def fetch_all(refresh: bool = False, log=print) -> int:
    """Cache every day's UP-token minute curve under .cache/pm_history/."""
    HIST_DIR.mkdir(parents=True, exist_ok=True)
    markets = list_markets()
    n_new = 0
    for meta in markets:
        f = HIST_DIR / f"{meta['date']}.json"
        if f.exists() and not refresh:
            continue
        start, end = _window(meta)
        hist = _price_history(meta["token_up"], start, end)
        f.write_text(json.dumps({"meta": meta, "history": hist}))
        n_new += 1
        log(f"{meta['date']}: {len(hist)} pts  vol ${meta['volume']:,.0f}")
    log(f"{len(markets)} resolved markets, {n_new} fetched this run")
    return n_new


def load_all() -> dict[str, dict]:
    """date -> {meta, history} for every cached day (may be empty curves)."""
    out = {}
    for f in sorted(HIST_DIR.glob("*.json")):
        d = json.loads(f.read_text())
        if d.get("history"):
            out[d["meta"]["date"]] = d
    return out
