"""S&P 500 constituent weights from the free IVV holdings file (iShares)."""
import csv
import io
import json
import time
import urllib.request

from ..config import CACHE

_URL = ("https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf/"
        "1467271812596.ajax?fileType=csv&fileName=IVV_holdings&dataType=fund")
_CACHE_FILE = CACHE / "weights.json"
_MAX_AGE = 5 * 86400


def fetch() -> list[dict]:
    req = urllib.request.Request(_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        text = r.read().decode("utf-8-sig", errors="replace")
    # holdings CSV has preamble lines; locate the header row
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("Ticker"))
    rows = []
    for row in csv.DictReader(io.StringIO("\n".join(lines[start:]))):
        try:
            w = float(row.get("Weight (%)", "").replace(",", ""))
        except ValueError:
            continue
        if row.get("Asset Class", "") != "Equity" or w <= 0:
            continue
        rows.append({"ticker": row["Ticker"].strip(),
                     "weight": w,
                     "exchange": row.get("Exchange", "").strip()})
    return rows


def load(refresh: bool = False) -> list[dict]:
    if not refresh and _CACHE_FILE.exists():
        blob = json.loads(_CACHE_FILE.read_text())
        if time.time() - blob["fetched"] < _MAX_AGE:
            return blob["rows"]
    rows = fetch()
    _CACHE_FILE.write_text(json.dumps({"fetched": time.time(), "rows": rows}))
    return rows


def nasdaq_share(rows: list[dict]) -> float:
    """Fraction of total weight listed on Nasdaq (prints at 9:30:00 sharp)."""
    total = sum(r["weight"] for r in rows)
    nas = sum(r["weight"] for r in rows if "NASDAQ" in r["exchange"].upper())
    return nas / total if total else 0.0
