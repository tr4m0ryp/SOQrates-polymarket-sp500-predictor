"""S&P 500 constituent weights + listing venue.

Primary: Slickcharts weight table (plain HTML, reliable).
Venue:   Nasdaq's official symbol directory (nasdaqlisted.txt) - a ticker
         present there is Nasdaq-listed (prints at 9:30:00 sharp), else NYSE.
Fallback: iShares IVV holdings CSV (endpoint currently serves a bot-wall;
         kept for when it recovers).
"""
import csv
import io
import json
import re
import time
import urllib.request

from open_predictor.config import CACHE

_CACHE_FILE = CACHE / "weights.json"
_MAX_AGE = 5 * 86400
# Slickcharts 403s a bare "Mozilla/5.0" (verified 2026-08-09); nasdaqtrader
# 406s an html-only Accept. A full browser UA with a wildcard Accept is the
# one header set both hosts serve.
_UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
       "Accept": "*/*",
       "Accept-Language": "en-US,en;q=0.9"}

_SLICKCHARTS = "https://www.slickcharts.com/sp500"
_NASDAQ_DIR = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
_ISHARES = ("https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf/"
            "1467271812596.ajax?fileType=csv&fileName=IVV_holdings&dataType=fund")


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8-sig", errors="replace")


def _nasdaq_symbols() -> set[str]:
    syms = set()
    for line in _get(_NASDAQ_DIR).splitlines()[1:]:
        parts = line.split("|")
        if len(parts) > 3 and parts[3] == "N":     # exclude test issues
            syms.add(parts[0])
    return syms


def _from_slickcharts() -> list[dict]:
    html = _get(_SLICKCHARTS)
    # rows carry /symbol/XXX links followed by the weight percentage cell
    pat = re.compile(r'href="/symbol/([A-Z.\-]+)".*?</td>\s*<td[^>]*>([\d.]+)%',
                     re.S)
    rows, seen = [], set()
    for sym, w in pat.findall(html):
        if sym in seen:
            continue
        seen.add(sym)
        rows.append({"ticker": sym, "weight": float(w)})
    if len(rows) < 400:
        raise RuntimeError(f"slickcharts parse got only {len(rows)} rows")
    return rows


def _from_ishares() -> list[dict]:
    text = _get(_ISHARES)
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("Ticker"))
    rows = []
    for row in csv.DictReader(io.StringIO("\n".join(lines[start:]))):
        try:
            w = float(row.get("Weight (%)", "").replace(",", ""))
        except ValueError:
            continue
        if row.get("Asset Class", "") == "Equity" and w > 0:
            rows.append({"ticker": row["Ticker"].strip(), "weight": w})
    if len(rows) < 400:
        raise RuntimeError("ishares CSV parse failed")
    return rows


def fetch() -> list[dict]:
    try:
        rows = _from_slickcharts()
    except Exception:
        rows = _from_ishares()
    nasdaq = _nasdaq_symbols()
    for r in rows:
        base = r["ticker"].replace(".", "-").split("-")[0]
        r["exchange"] = "NASDAQ" if (r["ticker"] in nasdaq or base in nasdaq) \
            else "NYSE"
    return rows


def load(refresh: bool = False) -> list[dict]:
    if not refresh and _CACHE_FILE.exists():
        blob = json.loads(_CACHE_FILE.read_text())
        if time.time() - blob["fetched"] < _MAX_AGE and blob["rows"]:
            return blob["rows"]
    rows = fetch()
    _CACHE_FILE.write_text(json.dumps({"fetched": time.time(), "rows": rows}))
    return rows


def nasdaq_share(rows: list[dict]) -> float:
    total = sum(r["weight"] for r in rows)
    nas = sum(r["weight"] for r in rows if r["exchange"] == "NASDAQ")
    return nas / total if total else 0.0
