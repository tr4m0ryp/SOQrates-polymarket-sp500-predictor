"""8:30 ET macro-release calendar: NFP computed, CPI/PPI fetched from BLS."""
import datetime as dt
import json
import re
import urllib.request

from ..config import CACHE

_CACHE_FILE = CACHE / "releases.json"
_BLS_PAGES = {
    "CPI": "https://www.bls.gov/schedule/news_release/cpi.htm",
    "PPI": "https://www.bls.gov/schedule/news_release/ppi.htm",
    "NFP": "https://www.bls.gov/schedule/news_release/empsit.htm",
}
_DATE_RE = re.compile(r"([A-Z][a-z]+)\.?\s+(\d{1,2}),\s+(\d{4})")
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def is_nfp_friday(date: dt.date) -> bool:
    """Employment Situation is (almost always) the first Friday of the month."""
    return date.weekday() == 4 and date.day <= 7


def refresh() -> dict[str, list[str]]:
    """Fetch BLS schedule pages; best-effort — sites may block or change."""
    out: dict[str, list[str]] = {}
    for name, url in _BLS_PAGES.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                html = r.read().decode(errors="replace")
            dates = []
            for mon, day, year in _DATE_RE.findall(html):
                m = _MONTHS.get(mon[:3])
                if m:
                    dates.append(f"{year}-{m:02d}-{int(day):02d}")
            out[name] = sorted(set(dates))
        except Exception:
            out[name] = []
    _CACHE_FILE.write_text(json.dumps(out, indent=1))
    return out


def _load() -> dict[str, list[str]]:
    if _CACHE_FILE.exists():
        return json.loads(_CACHE_FILE.read_text())
    return {}


def release_names(date: dt.date) -> list[str]:
    """Which 8:30 releases hit this morning (calendar cache + NFP rule)."""
    ds = str(date)
    names = [k for k, v in _load().items() if ds in v]
    if not names and is_nfp_friday(date):
        names = ["NFP"]
    return names


def is_release_morning(date: dt.date) -> bool:
    return bool(release_names(date))
