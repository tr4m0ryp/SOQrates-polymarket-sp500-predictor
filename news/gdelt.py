"""GDELT DOC 2.0 fetcher - the archive that covers every inventory day.

Keyless, timestamped (15-min index cycle, `seendate` UTC), full archive back
past 2015. Hard rate limit: space requests >= 5s and expect occasional 429s
(retry with backoff). Verified against labeled days: first Iran-strikes-halt
article 2026-03-23 12:00 UTC = 08:00 ET, the same hour ES swung +2% - i.e.
publication-to-effect is near-simultaneous; the LLM layer must poll, it
cannot rely on reading tomorrow's news early.
"""
import json
import time
import urllib.parse
import urllib.request

_API = "https://api.gdeltproject.org/api/v2/doc/doc"
_UA = {"User-Agent": "Mozilla/5.0"}

MARKET_QUERY = ('(tariff OR fed OR inflation OR strikes OR war OR sanctions '
                'OR opec OR earnings) (market OR futures OR stocks OR economy)')


def _fmt(ts: str) -> str:
    return ts.replace("-", "").replace(":", "").replace("T", "").replace("Z", "")


def query(q: str, start: str, end: str, max_records: int = 30,
          retries: int = 4, sort: str = "datedesc") -> list[dict]:
    """start/end like '20260323T0400Z' or plain YYYYMMDDHHMMSS."""
    params = urllib.parse.urlencode({
        "query": q, "mode": "artlist", "format": "json",
        "startdatetime": _fmt(start).ljust(14, "0"),
        "enddatetime": _fmt(end).ljust(14, "0"),
        "maxrecords": max_records, "sort": sort})
    for i in range(retries):
        try:
            req = urllib.request.Request(f"{_API}?{params}", headers=_UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                arts = json.load(r).get("articles", [])
            return [{"ts": a.get("seendate"), "domain": a.get("domain"),
                     "title": a.get("title"), "url": a.get("url")}
                    for a in arts]
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(8 * (i + 1))
    return []


def window_snapshot(end_utc: str, hours_back: float = 3.0,
                    q: str = MARKET_QUERY) -> list[dict]:
    """Headlines from the trailing window before an LLM checkpoint run."""
    import datetime as dt
    end = dt.datetime.strptime(_fmt(end_utc).ljust(14, "0"), "%Y%m%d%H%M%S")
    start = end - dt.timedelta(hours=hours_back)
    return query(q, start.strftime("%Y%m%d%H%M%S"), end.strftime("%Y%m%d%H%M%S"))
