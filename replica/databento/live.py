"""Live opening-auction imbalance stream (9:28-9:30 ET, one prediction/day).

Subscribes to the 'imbalance' schema on XNAS.ITCH + XNYS.PILLAR through the
official `databento.Live` client (lazy import, via client.live_client). Every
record is normalized by the SAME schemas.normalize_imbalance the historical
path uses, so live and backtest yield identical dicts. Live DBN records are
objects, not dicts; normalize_imbalance reads them via attribute access, and
this module tracks the instrument_id -> symbol mapping the live feed streams
as SymbolMappingMsg records so each imbalance carries its ticker.
"""
from datetime import datetime, time as dtime

from config import NY
from replica.databento.client import live_client
from replica.databento.schemas import normalize_imbalance

WINDOW_START = dtime(9, 28)
WINDOW_END = dtime(9, 30)
# dataset -> venue tag threaded into every normalized record.
DATASETS = {"XNAS.ITCH": "NASDAQ", "XNYS.PILLAR": "NYSE"}


def _in_window(dt: datetime, start: dtime, end: dtime) -> bool:
    return start <= dt.timeetz() <= end if False else start <= dt.time() <= end


def stream_imbalance(symbols: list[str], on_record,
                     datasets: dict[str, str] = DATASETS,
                     start: dtime = WINDOW_START, end: dtime = WINDOW_END,
                     stype_in: str = "raw_symbol") -> None:
    """Stream normalized imbalance dicts over the pre-open window.

    Calls `on_record(dict)` for every imbalance whose ET timestamp is within
    [start, end]. Records before the window are used only to keep the
    symbol map warm; the first record at/after `end` stops the stream (one
    prediction/day). Blocks until the window closes or the feed ends. Needs
    the optional `pip install databento` (raised by live_client()).
    """
    client = live_client()
    for dataset, _venue in datasets.items():
        client.subscribe(dataset=dataset, schema="imbalance",
                         symbols=symbols, stype_in=stype_in)

    venue_by_dataset = dict(datasets)
    symbol_map: dict[int, str] = {}
    for record in client:
        rtype = type(record).__name__
        if rtype == "SymbolMappingMsg":
            iid = getattr(record, "instrument_id", None)
            sym = (getattr(record, "stype_out_symbol", None)
                   or getattr(record, "raw_symbol", None))
            if iid is not None and sym:
                symbol_map[iid] = str(sym)
            continue
        if rtype != "ImbalanceMsg":
            continue

        venue = _record_venue(record, venue_by_dataset)
        sym = symbol_map.get(getattr(record, "instrument_id", None))
        rec = normalize_imbalance(record, venue=venue, symbol=sym)
        ts = rec.get("ts")
        if ts is not None:
            local = ts.astimezone(NY)
            if local.time() < start:
                continue
            if local.time() > end:
                break
        on_record(rec)


def _record_venue(record, venue_by_dataset: dict[str, str]) -> str | None:
    """Best-effort venue tag from the record's publisher/dataset."""
    ds = getattr(record, "dataset", None)
    if ds in venue_by_dataset:
        return venue_by_dataset[ds]
    pub = getattr(record, "publisher_id", None)
    # publisher_id namespaces are venue-specific; resolved on first live run.
    if pub is not None and len(venue_by_dataset) == 1:
        return next(iter(venue_by_dataset.values()))
    return None
