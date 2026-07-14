"""8:30 ET macro-release calendar.

Primary: FRED release-dates API (free key: fred.stlouisfed.org/docs/api/api_key.html,
env FRED_API_KEY). Release ids: CPI=10, PPI=46, Employment Situation (NFP)=50,
GDP=53. Covers past AND scheduled future dates.
Fallbacks: manual dates merged from .cache/releases_manual.json, and the
first-Friday NFP rule (works with no key at all).
BLS schedule pages 403 scripted fetches - do not re-add them.
"""
import datetime as dt
import json
import os
import urllib.request

from config import CACHE

_CACHE_FILE = CACHE / "releases.json"
_MANUAL_FILE = CACHE / "releases_manual.json"
_FRED = "https://api.stlouisfed.org/fred/release/dates"
_RELEASE_IDS = {"CPI": 10, "PPI": 46, "NFP": 50, "GDP": 53}


def is_nfp_friday(date: dt.date) -> bool:
    return date.weekday() == 4 and date.day <= 7


def refresh(years_back: int = 2) -> dict[str, list[str]]:
    """Pull release dates from FRED; requires FRED_API_KEY env."""
    key = os.environ.get("FRED_API_KEY", "")
    if not key:
        raise RuntimeError(
            "FRED_API_KEY not set - get a free key at "
            "fred.stlouisfed.org/docs/api/api_key.html, then rerun.")
    start = str(dt.date.today() - dt.timedelta(days=365 * years_back))
    out: dict[str, list[str]] = {}
    for name, rid in _RELEASE_IDS.items():
        url = (f"{_FRED}?release_id={rid}&api_key={key}&file_type=json"
               f"&realtime_start={start}&include_release_dates_with_no_data=true"
               f"&sort_order=asc&limit=1000")
        with urllib.request.urlopen(url, timeout=60) as r:
            data = json.load(r)
        out[name] = sorted({d["date"] for d in data.get("release_dates", [])})
    _CACHE_FILE.write_text(json.dumps(out, indent=1))
    return out


def _load() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if _CACHE_FILE.exists():
        out.update(json.loads(_CACHE_FILE.read_text()))
    if _MANUAL_FILE.exists():                      # user-maintained overrides
        for name, dates in json.loads(_MANUAL_FILE.read_text()).items():
            out[name] = sorted(set(out.get(name, [])) | set(dates))
    return out


def release_names(date: dt.date) -> list[str]:
    ds = str(date)
    names = [k for k, v in _load().items() if ds in v]
    if "NFP" not in names and is_nfp_friday(date):
        names.append("NFP")
    return names


def is_release_morning(date: dt.date) -> bool:
    return bool(release_names(date))
