"""Historical auction pulls -> normalized records (pure stdlib HTTP+JSON).

Wraps client.get_range for each of the four auction data types and pushes
every record through schemas.py so the output matches the live path:

  #1 nasdaq_noii   XNAS.ITCH  'imbalance'  -> normalize_imbalance (NASDAQ)
  #2 nyse_imbalance XNYS.PILLAR 'imbalance' -> normalize_imbalance (NYSE)
  #3 cross_prints  <dataset>   'trades'     -> normalize_trade
  #4 nbbo_quotes   <dataset>   'mbp-1'      -> normalize_quote

Plus two stage-3 adapters that mirror replica/lseg/parse:
  snapshots()      -> {ticker: [snapshot dicts with 'pred_open'], ...}
  cross_print_map()-> {ticker: (cross_price, ts_ns)} for the timing model.
"""
from collections import defaultdict

from replica.databento.client import get_range
from replica.databento.schemas import (normalize_imbalance, normalize_quote,
                                        normalize_trade)

NASDAQ_DATASET = "XNAS.ITCH"
NYSE_DATASET = "XNYS.PILLAR"


def nasdaq_noii(symbols: list[str], start: str, end: str) -> list[dict]:
    """#1 Opening-cross NOII (near/far/ref, paired/imbalance qty), normalized."""
    return [normalize_imbalance(r, venue="NASDAQ")
            for r in get_range(NASDAQ_DATASET, "imbalance", symbols, start, end)]


def nyse_imbalance(symbols: list[str], start: str, end: str) -> list[dict]:
    """#2 NYSE auction imbalance (indicative match price, qtys), normalized."""
    return [normalize_imbalance(r, venue="NYSE")
            for r in get_range(NYSE_DATASET, "imbalance", symbols, start, end)]


def cross_prints(symbols: list[str], start: str, end: str,
                 dataset: str = NASDAQ_DATASET) -> list[dict]:
    """#3 Realized cross prints + timestamps (trades schema), normalized."""
    return [normalize_trade(r, venue=_venue(dataset))
            for r in get_range(dataset, "trades", symbols, start, end)]


def nbbo_quotes(symbols: list[str], start: str, end: str,
                dataset: str = NASDAQ_DATASET, schema: str = "mbp-1") -> list[dict]:
    """#4 Pre-open top-of-book NBBO (mbp-1/tbbo schema), normalized."""
    return [normalize_quote(r, venue=_venue(dataset))
            for r in get_range(dataset, schema, symbols, start, end)]


def _venue(dataset: str) -> str:
    return "NASDAQ" if dataset == NASDAQ_DATASET else "NYSE"


def snapshots(records) -> dict[str, list[dict]]:
    """Group normalized imbalance records into stage-3's snapshot shape.

    Mirrors replica/lseg/parse.snapshots: {ticker: [snap, ...]} time-ordered,
    each snap carrying 'pred_open'. Feed it nasdaq_noii()+nyse_imbalance()
    output; stage3 then takes the LAST snapshot with a non-null 'pred_open',
    identical to the LSEG path. Records lacking pred_open are dropped so the
    shape stays clean.
    """
    out: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        t = r.get("ticker")
        if not t or r.get("pred_open") is None:
            continue
        out[t].append(r)
    for t in out:
        out[t].sort(key=lambda s: (s.get("ts_ns") is None, s.get("ts_ns") or 0))
    return dict(out)


def cross_print_map(records) -> dict[str, tuple[float, int]]:
    """Normalized trade records -> {ticker: (cross_price, ts_ns)}.

    Feeds timing.fit_from_prints and montecarlo.apply_prints (the caller
    splits into {ticker: price} for apply_prints and hands ts_ns to timing).
    The opening cross is taken as the EARLIEST priced trade per ticker in the
    requested window - confirm the exact cross flag on the first keyed pull.
    """
    best: dict[str, tuple[float, int]] = {}
    for r in records:
        t = r.get("ticker")
        px = r.get("cross_price")
        ts = r.get("ts_ns")
        if not t or px is None or ts is None:
            continue
        cur = best.get(t)
        if cur is None or ts < cur[1]:
            best[t] = (px, ts)
    return best
