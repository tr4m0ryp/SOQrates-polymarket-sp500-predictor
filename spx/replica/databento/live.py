"""Live opening-auction imbalance stream (9:28-9:30 ET, one prediction/day).

Databento live sessions are single-dataset, so each dataset (XNAS.ITCH
Nasdaq NOII, XNYS.PILLAR NYSE) gets its OWN `databento.Live` client, pumped
on a daemon thread into one queue. Every record is normalized by the SAME
schemas.normalize_imbalance the historical path uses, so live and backtest
yield identical dicts. Live DBN records are objects, not dicts;
normalize_imbalance reads them via attribute access (with an `hd` header
fallback), and each pump tracks its feed's instrument_id -> symbol mapping
from SymbolMappingMsg records so every imbalance carries its ticker.
"""
import queue
import threading
from datetime import time as dtime

from config import NY
from replica.databento.client import DatabentoError, live_client
from replica.databento.schemas import normalize_imbalance

WINDOW_START = dtime(9, 28)
WINDOW_END = dtime(9, 30)
# dataset -> venue tag threaded into every normalized record.
DATASETS = {"XNAS.ITCH": "NASDAQ", "XNYS.PILLAR": "NYSE"}


def stream_imbalance(symbols: list[str], on_record,
                     datasets: dict[str, str] = DATASETS,
                     start: dtime = WINDOW_START, end: dtime = WINDOW_END,
                     stype_in: str = "raw_symbol") -> None:
    """Stream normalized imbalance dicts over the pre-open window.

    Calls `on_record(dict)` for every imbalance whose ET timestamp falls in
    [start, end]. Records before the window only keep the symbol map warm;
    a record past `end` closes that feed (one prediction/day). Blocks until
    every feed's window closes or its stream ends; a feed ErrorMsg or pump
    crash re-raises here. Needs the optional `pip install databento`
    (raised by live_client()).
    """
    q: queue.Queue = queue.Queue()
    clients = []
    for dataset, venue in datasets.items():
        client = live_client()               # one client per dataset
        client.subscribe(dataset=dataset, schema="imbalance",
                         symbols=symbols, stype_in=stype_in)
        clients.append(client)
        threading.Thread(target=_pump, args=(client, venue, q, start, end),
                         daemon=True).start()
    try:
        open_feeds = len(clients)
        while open_feeds:
            kind, payload = q.get()
            if kind == "rec":
                on_record(payload)
            elif kind == "err":
                raise payload
            else:                            # "done"
                open_feeds -= 1
    finally:
        for client in clients:
            try:
                client.stop()
            except Exception:
                pass


def _pump(client, venue: str, q: queue.Queue,
          start: dtime, end: dtime) -> None:
    """One dataset's feed: iterate, map symbols, normalize, filter window."""
    symbol_map: dict[int, str] = {}
    try:
        for record in client:
            rtype = type(record).__name__
            if rtype == "ErrorMsg":
                q.put(("err", DatabentoError(
                    f"{venue} live: {getattr(record, 'err', record)}")))
                return
            if rtype == "SymbolMappingMsg":
                iid = _instrument_id(record)
                sym = (getattr(record, "stype_out_symbol", None)
                       or getattr(record, "raw_symbol", None))
                if iid is not None and sym:
                    symbol_map[iid] = str(sym)
                continue
            if rtype != "ImbalanceMsg":
                continue
            rec = normalize_imbalance(
                record, venue=venue,
                symbol=symbol_map.get(_instrument_id(record)))
            ts = rec.get("ts")
            if ts is not None:
                local = ts.astimezone(NY).time()
                if local < start:
                    continue
                if local > end:
                    break
            q.put(("rec", rec))
    except Exception as e:                   # surfaced in the caller's thread
        q.put(("err", e))
        return
    q.put(("done", None))


def _instrument_id(record):
    iid = getattr(record, "instrument_id", None)
    if iid is None:
        hd = getattr(record, "hd", None)
        if hd is not None:
            iid = getattr(hd, "instrument_id", None)
    return iid
