"""Databento pipeline adapter: one-day pull + stage-3 / timing feeds.

The CLI-facing bridge between the Databento client and the auction pipeline.
`pull_day` fetches the four auction data types for every S&P constituent over
the pre-open window and caches the raw JSON per date; `snapshots` and `prints`
re-read that cache and hand stage3 / the timing model the SAME shapes the LSEG
path produces (replica/vendors/lseg/parse.snapshots and {ticker: (price, ts_ns)}).

  pull_day(date)      -> {counts, errors, records, dir}   (raw JSON cached)
  snapshots(date)     -> {ticker: [snap w/ pred_open]}     (== lseg_parse)
  prints(date)        -> {ticker: (cross_price, ts_ns)}    (montecarlo/timing)
  print_delays(date)  -> {ticker: seconds_after_930}       (timing.fit_from_prints)
  ping()              -> [dataset codes]                   (status probe)

Historical is pure stdlib HTTP+JSON (via client.get_range). Windows are built
in ET (America/New_York) and sent to Databento as UTC RFC-3339.
"""
import base64
import json
import urllib.parse
import urllib.request
from datetime import datetime, time as dtime, timezone

from open_predictor.config import CACHE, NY
from open_predictor.sources.market import weights as wmod
from open_predictor.forecast.auction.vendors.databento import budget
from open_predictor.forecast.auction.vendors.databento.transport.client import DatabentoError, get_range, _key
from open_predictor.forecast.auction.vendors.databento.feeds.historical import (NASDAQ_DATASET, NYSE_DATASET,
                                           cross_print_map,
                                           snapshots as _group_snapshots)
from open_predictor.forecast.auction.vendors.databento.schemas import normalize_imbalance, normalize_trade

_META = "https://hist.databento.com/v0"

# Pre-open windows (ET). Imbalance carries the running NOII indicative; the
# trades window is tight around the cross so cross_print_map's earliest priced
# trade per ticker is the opening print (NYSE stragglers open late -> 9:34).
IMB_WINDOW = (dtime(9, 20, 0), dtime(9, 33, 0))
TRADE_WINDOW = (dtime(9, 29, 55), dtime(9, 34, 0))
QUOTE_WINDOW = (dtime(9, 29, 0), dtime(9, 30, 0))

# (schema, dataset, venue, window) - the four data types, both venues.
_SLICES = (
    ("imbalance", NASDAQ_DATASET, "NASDAQ", IMB_WINDOW),    # #1 Nasdaq NOII
    ("imbalance", NYSE_DATASET, "NYSE", IMB_WINDOW),        # #2 NYSE imbalance
    ("trades", NASDAQ_DATASET, "NASDAQ", TRADE_WINDOW),     # #3 cross prints
    ("trades", NYSE_DATASET, "NYSE", TRADE_WINDOW),
    ("mbp-1", NASDAQ_DATASET, "NASDAQ", QUOTE_WINDOW),      # #4 pre-open NBBO
    ("mbp-1", NYSE_DATASET, "NYSE", QUOTE_WINDOW),
)


def _daydir(date: str):
    return CACHE / "databento" / date


def _iso(date: str, t: dtime) -> str:
    y, m, d = (int(x) for x in date.split("-"))
    et = datetime(y, m, d, t.hour, t.minute, t.second, tzinfo=NY)
    return et.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _symbols():
    rows = wmod.load()
    nas = [r["ticker"] for r in rows if r["exchange"] == "NASDAQ"]
    nyse = [r["ticker"] for r in rows if r["exchange"] != "NASDAQ"]
    return nas, nyse


def pull_day(date: str, cache: bool = True) -> dict:
    """Fetch all four auction data types for both venues and cache raw JSON.

    Splits constituents Nasdaq/NYSE (mirrors cli lseg-pull), pulls each
    (schema, venue) slice over its pre-open window, and writes the raw records
    to config.CACHE/databento/<date>/<schema>_<venue>.json. A missing key
    raises DatabentoError up front; a per-slice failure (e.g. NYSE PILLAR
    entitlement) is recorded in `errors` without killing the other slices.
    """
    _key()                                   # fail fast, clear message
    nas, nyse = _symbols()
    syms = {"NASDAQ": nas, "NYSE": nyse}
    d = _daydir(date)
    if cache:
        d.mkdir(parents=True, exist_ok=True)
    counts, errors, records, cost = {}, {}, [], 0.0
    for schema, dataset, venue, window in _SLICES:
        name = f"{schema}_{venue}"
        start, end = _iso(date, window[0]), _iso(date, window[1])
        try:
            # priced call: quote + reserve against the cap BEFORE fetching
            cost += budget.check_and_reserve(f"{date}/{name}", dataset, schema,
                                             syms[venue], start, end)
            recs = get_range(dataset, schema, syms[venue], start, end)
        except budget.BudgetError as e:
            errors[name] = f"BUDGET: {e}"
            recs = []
        except DatabentoError as e:
            errors[name] = str(e)
            recs = []
        counts[name] = len(recs)
        records.extend(recs)
        if cache:
            (d / f"{name}.json").write_text(json.dumps(recs))
    return {"date": date, "dir": str(d), "counts": counts, "errors": errors,
            "records": records, "cost_usd": cost,
            "spent_usd": budget.spent_usd(), "cap_usd": budget.cap_usd()}


def cached(date: str) -> bool:
    """True if an imbalance pull for `date` is on disk (stage3 gate)."""
    d = _daydir(date)
    return (d / "imbalance_NASDAQ.json").exists() \
        or (d / "imbalance_NYSE.json").exists()


def _read(date: str, name: str):
    p = _daydir(date) / f"{name}.json"
    if not p.exists():
        return []
    return json.loads(p.read_text())


def snapshots(date: str) -> dict[str, list[dict]]:
    """Cached imbalance records -> stage-3 snapshot shape (== lseg_parse).

    Normalizes both venues' cached imbalance records and groups them into
    {ticker: [snap, ...]} time-ordered, each carrying 'pred_open' (the
    indicative clearing price). stage3 takes the LAST snap with pred_open,
    identical to the LSEG path.
    """
    recs = [normalize_imbalance(r, venue="NASDAQ")
            for r in _read(date, "imbalance_NASDAQ")]
    recs += [normalize_imbalance(r, venue="NYSE")
             for r in _read(date, "imbalance_NYSE")]
    return _group_snapshots(recs)


def prints(date: str) -> dict[str, tuple[float, int]]:
    """Cached trade records -> {ticker: (cross_price, ts_ns)} realized opens.

    Feeds montecarlo.apply_prints (split the price element) and, via
    print_delays(), timing.fit_from_prints.
    """
    recs = [normalize_trade(r, venue="NASDAQ")
            for r in _read(date, "trades_NASDAQ")]
    recs += [normalize_trade(r, venue="NYSE")
             for r in _read(date, "trades_NYSE")]
    return cross_print_map(recs)


def print_delays(date: str) -> dict[str, float]:
    """{ticker: seconds_after_0930} for timing.fit_from_prints({date: ...}).

    timing.fit_from_prints wants per-ticker print DELAYS (seconds after
    09:30:00 ET), not (price, ts_ns); this converts the prints() timestamps.
    """
    y, m, d = (int(x) for x in date.split("-"))
    open_ns = int(datetime(y, m, d, 9, 30, 0, tzinfo=NY).timestamp() * 1e9)
    return {t: (ts - open_ns) / 1e9 for t, (_px, ts) in prints(date).items()}


def ping() -> list[str]:
    """Tiny metadata call (metadata.list_datasets) to verify the key works."""
    auth = base64.b64encode(f"{_key()}:".encode()).decode()
    req = urllib.request.Request(
        f"{_META}/metadata.list_datasets",
        headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    return data if isinstance(data, list) else list(data)
