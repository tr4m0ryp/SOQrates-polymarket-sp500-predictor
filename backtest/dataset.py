"""Build and cache the daily backtest dataset (gap paths + regressors)."""
import datetime as dt
import json

from config import CACHE, DATASET_DAYS
from data import futures, yahoo
from macro import releases
from model.regime import annotate_ewma

_CACHE_FILE = CACHE / "dataset.json"


def build() -> list[dict]:
    feeds = futures.load_feeds()
    spx = yahoo.daily_open_close("^GSPC", 330)
    try:
        vix = yahoo.daily_open_close("^VIX1D", 330)
    except Exception:
        vix = {}
    days = sorted(spx)

    rows = []
    for i in range(1, len(days)):
        d, p = days[i], days[i - 1]
        es = futures.gap_path(feeds["ES=F"], d, p)
        nq = futures.gap_path(feeds["NQ=F"], d, p)
        ym = futures.gap_path(feeds["YM=F"], d, p)
        if not es or len(es) < 9 or 0 not in es:
            continue
        rows.append({
            "date": d,
            "off": (spx[d][0] / spx[p][1] - 1) * 100,
            "es": es, "nq": nq or {}, "ym": ym or {},
            "rv_prev": futures.prior_day_rv(feeds["ES=F"], p),
            "vix1d_prev": (vix.get(p) or (None,))[-1],
            "release_morning": releases.is_release_morning(
                dt.date(*map(int, d.split("-")))),
        })
    rows = annotate_ewma(rows)[-DATASET_DAYS:]
    return rows


def _intify(rows):
    for r in rows:
        for k in ("es", "nq", "ym"):
            r[k] = {int(h): v for h, v in r[k].items()}
    return rows


def load(rebuild: bool = False) -> list[dict]:
    if not rebuild and _CACHE_FILE.exists():
        return _intify(json.loads(_CACHE_FILE.read_text()))
    rows = build()
    _CACHE_FILE.write_text(json.dumps(rows))
    return rows


def split(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    half = len(rows) // 2
    return rows[:half], rows[half:]
