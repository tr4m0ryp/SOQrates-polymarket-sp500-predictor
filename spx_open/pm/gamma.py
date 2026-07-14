"""Polymarket gamma-api client for the daily SPX-open market."""
import datetime as dt
import json
import urllib.request

_UA = {"User-Agent": "Mozilla/5.0"}
_MONTHS = ["", "january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december"]


def _get(url: str):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def open_market(date: dt.date) -> dict | None:
    """The 'SPX Opens Up or Down on <date>' market, or None."""
    slug = f"spx-opens-up-or-down-on-{_MONTHS[date.month]}-{date.day}-{date.year}"
    events = _get(f"https://gamma-api.polymarket.com/events?slug={slug}")
    if not events:
        return None
    e = events[0]
    m = e["markets"][0]
    prices = json.loads(m.get("outcomePrices") or "[null,null]")
    return {
        "slug": slug,
        "event_id": e["id"],
        "closed": e.get("closed"),
        "p_up": float(prices[0]) if prices[0] is not None else None,
        "volume": float(e.get("volume") or 0),
        "liquidity": float(e.get("liquidity") or 0),
        "clob_token_up": json.loads(m["clobTokenIds"])[0],
    }
