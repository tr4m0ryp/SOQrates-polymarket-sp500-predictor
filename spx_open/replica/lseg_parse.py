"""Parse LSEG Tick History raw extractions into auction snapshots.

TickHistoryRaw CSV is LONG format: one field (FID) per row -
  #RIC, Domain, Date-Time, GMT Offset, Type, MsgClass, ..., Name, Value
Exact auction FID names vary by venue; candidates below cover the usual
Nasdaq NOII and NYSE imbalance fields. Run `discover()` on the first real
extraction and extend the maps before trusting `snapshots()`.
"""
import csv
import gzip
import io
from collections import defaultdict

# candidate FID name -> normalized key
FID_MAP = {
    # indicative / clearing prices
    "IND_AUC": "pred_open", "IND_AUCVOL": "paired",
    "OPN_AUC": "open_print", "OPN_AUCVOL": "open_vol",
    "NR_PRC": "pred_open", "NEAR_PRICE": "pred_open",
    "FAR_PRC": "far", "FAR_PRICE": "far",
    "CROSS_TYPE": "cross_type",
    # imbalance quantities / side
    "IMB_SH": "imbalance", "IMB_SIDE": "side", "IMB_ACT_TP": "imb_type",
    "PR_IMB_SH": "paired", "MTCH_QTY": "paired",
    # reference
    "REF_PRC": "ref", "HST_CLOSE": "prior_close",
}


def _rows(path_or_bytes):
    if isinstance(path_or_bytes, (bytes, bytearray)):
        raw = bytes(path_or_bytes)
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        fh = io.StringIO(raw.decode(errors="replace"))
    else:
        opener = gzip.open if str(path_or_bytes).endswith(".gz") else open
        fh = opener(path_or_bytes, "rt", errors="replace")
    return csv.DictReader(fh)


def discover(path_or_bytes, limit: int = 500_000) -> dict[str, int]:
    """Count distinct FID names seen - run this on the FIRST real pull."""
    counts: dict[str, int] = defaultdict(int)
    for i, row in enumerate(_rows(path_or_bytes)):
        name = row.get("Name") or row.get("FID Name") or ""
        if name:
            counts[name] += 1
        if i >= limit:
            break
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def snapshots(path_or_bytes) -> dict[str, list[dict]]:
    """ticker -> chronological auction snapshots with normalized keys."""
    out: dict[str, list[dict]] = defaultdict(list)
    current: dict[tuple[str, str], dict] = {}
    for row in _rows(path_or_bytes):
        ric = row.get("#RIC") or row.get("RIC") or ""
        name = row.get("Name") or row.get("FID Name") or ""
        key = FID_MAP.get(name)
        if not ric or not key:
            continue
        ts = row.get("Date-Time") or ""
        ticker = ric.split(".")[0]
        bucket = current.setdefault((ticker, ts), {"ts": ts})
        val = row.get("Value") or ""
        try:
            bucket[key] = float(val)
        except ValueError:
            bucket[key] = val
        if key in ("pred_open", "open_print"):
            out[ticker].append(dict(bucket))
    return dict(out)
