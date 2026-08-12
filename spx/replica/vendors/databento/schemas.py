"""DBN field maps + record normalization (the heart of the adapter).

Historical JSON records and live DBN objects both flow through the SAME
normalize_* functions here, so hist and live yield byte-identical dicts.
Prices arrive as fixed-point integers scaled 1e-9 (nanodollars); timestamps
as nanoseconds since the UNIX epoch. We emit float dollars + an ET datetime,
and keep raw `ts_ns` (epoch nanoseconds) for the timing model.

The indicative-clearing selection (`pred_open`) lives in exactly ONE place
(`_indicative`) so it is finalized on the first keyed pull, exactly like
replica/vendors/lseg/parse. Run `discover(records)` on that first pull to dump the
observed field names + counts and confirm the maps below.
"""
from datetime import datetime, timezone

from spx.config import NY

# Databento sentinels for "undefined".
UNDEF_PRICE = 9223372036854775807          # INT64_MAX
UNDEF_QTY = 2147483647                       # INT32_MAX
_SCALE = 1e9

# ---- 'imbalance' schema (Nasdaq NOII / NYSE imbalance) -----------------
# DBN field name -> normalized output key. See discover() to confirm.
IMBALANCE_FIELDS = {
    "ref_price": "ref_price",
    "cont_book_clr_price": "near",          # Nasdaq "near" indicative
    "auct_interest_clr_price": "far",       # Nasdaq "far" (cross-only)
    "ind_match_price": "ind_match",         # NYSE indicative match
    "paired_qty": "paired_qty",
    "total_imbalance_qty": "imbalance_qty",
    "market_imbalance_qty": "market_imbalance_qty",
    "side": "side",
    "auction_type": "auction_type",
    "auction_time": "auction_time",
    "upper_collar": "upper_collar",
    "lower_collar": "lower_collar",
}
_IMB_PRICE = {"ref_price", "cont_book_clr_price", "auct_interest_clr_price",
              "ind_match_price", "upper_collar", "lower_collar"}
_IMB_QTY = {"paired_qty", "total_imbalance_qty", "market_imbalance_qty"}

# indicative-clearing preference order -> pred_open (single source of truth).
_INDICATIVE_ORDER = ("ind_match_price", "cont_book_clr_price", "ref_price")

# ---- 'trades' schema (realized opening cross) --------------------------
TRADE_FIELDS = {"price": "cross_price", "size": "size", "side": "side",
                "action": "action"}

# ---- 'mbp-1' / 'tbbo' schema (pre-open NBBO) ---------------------------
QUOTE_LEVEL_FIELDS = {"bid_px": "bid", "ask_px": "ask",
                      "bid_sz": "bid_size", "ask_sz": "ask_size"}


def _field(rec, key):
    """Read `key` from a JSON dict (checking the nested `hd` header) or a
    live DBN object (attribute, falling back to the `hd` header object where
    the bindings keep ts_event/instrument_id). One accessor => one path."""
    if isinstance(rec, dict):
        if key in rec:
            return rec[key]
        hd = rec.get("hd")
        if isinstance(hd, dict) and key in hd:
            return hd[key]
        return None
    v = getattr(rec, key, None)
    if v is None:
        hd = getattr(rec, "hd", None)
        if hd is not None:
            return getattr(hd, key, None)
    return v


def _px(v):
    """Price -> float dollars. Raw fixed-point nanodollar ints (the JSON/DBN
    default) scale by 1e-9; decimal strings (pretty_px, contain '.') are
    already dollars and pass through. Sentinel/None -> None."""
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        if "." in s or "e" in s.lower():         # pretty_px decimal dollars
            try:
                return float(s)
            except ValueError:
                return None
        try:
            n = int(s)
        except ValueError:
            return None
    elif isinstance(v, float):
        if not v.is_integer():
            return v                             # already decimal dollars
        n = int(v)
    elif isinstance(v, int):
        n = v
    else:
        return None
    if abs(n) >= UNDEF_PRICE:
        return None
    return n / _SCALE


def _qty(v):
    if v is None:
        return None
    try:
        n = int(v)
    except (TypeError, ValueError):
        try:
            n = int(float(v))
        except (TypeError, ValueError):
            return None
    if abs(n) >= UNDEF_QTY:
        return None
    return n


def _to_ns(v):
    """Timestamp field -> epoch nanoseconds int. Accepts an integer/str of
    nanoseconds, or an ISO-8601 string (fractional secs truncated to us)."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip()
    if not s:
        return None
    if s.lstrip("-").isdigit():
        return int(s)
    iso = s.replace("Z", "+00:00")
    if "." in iso:                           # trim ns fraction to us, keep tz
        dot = iso.index(".")
        j = dot + 1
        while j < len(iso) and iso[j].isdigit():
            j += 1
        iso = iso[:dot + 1] + iso[dot + 1:j][:6] + iso[j:]
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return None
    return int(dt.timestamp() * 1e9)


def _ts_et(ns):
    if ns is None:
        return None
    return datetime.fromtimestamp(ns / 1e9, timezone.utc).astimezone(NY)


def _symbol(rec, override=None):
    if override:
        return override
    for k in ("symbol", "raw_symbol", "ticker"):
        v = _field(rec, k)
        if v:
            return str(v)
    iid = _field(rec, "instrument_id")
    return str(iid) if iid is not None else None


def _indicative(rec):
    """pred_open = the auction's indicative clearing price. ONE place only.

    Zero means "this venue does not populate this field", not "this stock
    clears at $0.00": NYSE Pillar leaves ind_match_price at 0 and carries the
    indicative in cont_book_clr_price, so accepting 0 here silently blanked
    every NYSE constituent (verified against the 2026-07-10 pull, where it
    cost the replica 345 of 506 names and 43% of index weight).
    """
    for k in _INDICATIVE_ORDER:
        px = _px(_field(rec, k))
        if px is not None and px > 0:
            return px
    return None


def normalize_imbalance(rec, venue=None, symbol=None) -> dict:
    """Auction imbalance record -> assembly-ready dict.

    `pred_open` is the indicative clearing price (NOT the realized print):
    ind_match_price else cont_book_clr_price else ref_price. Shape mirrors
    replica/vendors/lseg/parse snapshots (ticker/pred_open/near/far/ref/paired/...).
    """
    ts_ns = _to_ns(_field(rec, "ts_event"))
    sym = _symbol(rec, symbol)
    return {
        "symbol": sym,
        "ticker": sym,
        "pred_open": _indicative(rec),
        "ref_price": _px(_field(rec, "ref_price")),
        "near": _px(_field(rec, "cont_book_clr_price")),
        "far": _px(_field(rec, "auct_interest_clr_price")),
        "ind_match": _px(_field(rec, "ind_match_price")),
        "paired_qty": _qty(_field(rec, "paired_qty")),
        "imbalance_qty": _qty(_field(rec, "total_imbalance_qty")),
        "market_imbalance_qty": _qty(_field(rec, "market_imbalance_qty")),
        "side": _field(rec, "side"),
        "auction_type": _field(rec, "auction_type"),
        "ts_ns": ts_ns,
        "ts": _ts_et(ts_ns),
        "venue": venue,
    }


def normalize_trade(rec, venue=None, symbol=None) -> dict:
    """Realized cross print (#3). `cross_price` + `ts_ns` feed the timing
    model's {ticker: (price, ts_ns)}."""
    ts_ns = _to_ns(_field(rec, "ts_event"))
    sym = _symbol(rec, symbol)
    return {
        "symbol": sym,
        "ticker": sym,
        "cross_price": _px(_field(rec, "price")),
        "size": _qty(_field(rec, "size")),
        "side": _field(rec, "side"),
        "action": _field(rec, "action"),
        "ts_ns": ts_ns,
        "ts": _ts_et(ts_ns),
        "venue": venue,
    }


def _bidask(rec):
    """Top-of-book prices from either nested `levels[0]` (JSON / DBN object)
    or flattened `bid_px_00`/`ask_px_00` fields."""
    lv = _field(rec, "levels")
    level0 = None
    if isinstance(lv, (list, tuple)) and lv:
        level0 = lv[0]
    elif lv is not None:                     # single object, not a list
        level0 = lv

    def g(base):
        if level0 is not None:
            v = level0.get(base) if isinstance(level0, dict) \
                else getattr(level0, base, None)
            if v is not None:
                return v
        return _field(rec, f"{base}_00")
    return g("bid_px"), g("ask_px"), g("bid_sz"), g("ask_sz")


def normalize_quote(rec, venue=None, symbol=None) -> dict:
    """Pre-open NBBO top-of-book (#4) -> bid/ask/mid for quote midpoints."""
    ts_ns = _to_ns(_field(rec, "ts_event"))
    sym = _symbol(rec, symbol)
    bid, ask, bsz, asz = _bidask(rec)
    bid, ask = _px(bid), _px(ask)
    mid = (bid + ask) / 2 if (bid is not None and ask is not None) else None
    return {
        "symbol": sym,
        "ticker": sym,
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "bid_size": _qty(bsz),
        "ask_size": _qty(asz),
        "ts_ns": ts_ns,
        "ts": _ts_et(ts_ns),
        "venue": venue,
    }


def discover(records) -> dict[str, int]:
    """Count distinct DBN field names across JSON records - run on the FIRST
    keyed pull to confirm the maps above (mirrors lseg_parse.discover).

    Flattens the nested `hd` header and `levels[0]` so imbalance, trade, and
    quote fields all surface by their canonical names.
    """
    from collections import defaultdict
    counts: dict[str, int] = defaultdict(int)
    for rec in records:
        if not isinstance(rec, dict):
            continue
        for k, v in rec.items():
            if k == "hd" and isinstance(v, dict):
                for hk in v:
                    counts[f"hd.{hk}"] += 1
            elif k == "levels" and isinstance(v, (list, tuple)) and v \
                    and isinstance(v[0], dict):
                for lk in v[0]:
                    counts[f"levels.0.{lk}"] += 1
            else:
                counts[k] += 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))
