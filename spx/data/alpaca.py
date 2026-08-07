"""Alpaca Market Data client: opening-cross prints (#3) + pre-open NBBO (#4).

REST paths (historical auctions, historical quotes) use stdlib urllib only.
The live IEX quote websocket needs an optional `pip install websockets`; that
logic is kept out of the REST path, same pattern as replica/stitch/feeds.py Massive.

Auth: env ALPACA_API_KEY / ALPACA_API_SECRET -> request headers
APCA-API-KEY-ID / APCA-API-SECRET-KEY.

Public surface
--------------
- auctions(symbols, start, end, feed): historical opening/closing auction
  prints per symbol (paginated, merged).
- official_open(resp, venue_map): the ONE opening print whose exchange code
  matches each symbol's primary listing venue (Q=Nasdaq, N=NYSE), timestamp
  converted to ET.
- quotes(symbols, start, end, feed): historical NBBO quotes per symbol.
- nbbo_at(quote_list, target_et): bid/ask/mid at/nearest an ET timestamp.
- parse_ts(s): RFC3339-nanosecond string -> aware ET datetime.
- LiveIexQuotes: auth/subscribe/normalize (+ optional async stream) for the
  free real-time IEX quote websocket.

Cost / coverage
---------------
- Free / "Basic" ($0): live IEX real-time quotes only (feed="iex"); no SIP
  history.
- Historical auctions/quotes on the full consolidated (SIP) tape (feed="sip")
  need Algo Trader Plus ($99/mo).
- The widely repeated "15-minute delay on the free tier" claim is FALSE
  (refuted): free IEX quotes are real-time. The free-tier limitation is
  IEX-only coverage, not a delay.
"""
import datetime as dt
import json
import os
import urllib.parse
import urllib.request

from spx.config import NY

_BASE = "https://data.alpaca.markets/v2/stocks"

# Alpaca single-char CTA/UTP exchange codes we care about for a primary open.
VENUE_TO_CODE = {
    "NASDAQ": "Q", "NAS": "Q", "UTP": "Q",
    "NYSE": "N",
    "ARCA": "P", "NYSEARCA": "P", "PSE": "P",
    "AMEX": "A", "NYSEAMERICAN": "A", "NYSEMKT": "A",
    "BATS": "Z", "BZX": "Z", "CBOE": "Z",
}


class AlpacaError(RuntimeError):
    pass


def _headers() -> dict:
    key = os.environ.get("ALPACA_API_KEY", "")
    secret = os.environ.get("ALPACA_API_SECRET", "")
    if not key or not secret:
        raise AlpacaError(
            "ALPACA_API_KEY / ALPACA_API_SECRET not set - create free keys at "
            "alpaca.markets and export them (SIP history needs Algo Trader Plus).")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret,
            "Accept": "application/json"}


def _get(path: str, params: dict) -> dict:
    url = f"{_BASE}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def _paged(path: str, key: str, symbols: list[str], start: str, end: str,
           feed: str, limit: int = 10000) -> dict[str, list]:
    """Collect a paginated stocks endpoint into {symbol: [records...]}."""
    out: dict[str, list] = {}
    token = None
    while True:
        params = {"symbols": ",".join(symbols), "start": start, "end": end,
                  "feed": feed, "limit": limit}
        if token:
            params["page_token"] = token
        blob = _get(path, params)
        for sym, recs in (blob.get(key) or {}).items():
            out.setdefault(sym, []).extend(recs or [])
        token = blob.get("next_page_token")
        if not token:
            return out


def parse_ts(s: str) -> dt.datetime | None:
    """RFC3339 (nanosecond) string -> aware datetime in ET.

    datetime tops out at microseconds, so 9-digit fractions are truncated.
    """
    if not s:
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    if "." in s:
        head, frac = s.split(".", 1)
        digits, rest = "", ""
        for i, ch in enumerate(frac):
            if ch.isdigit():
                digits += ch
            else:
                rest = frac[i:]
                break
        s = f"{head}.{digits[:6]}{rest}"
    return dt.datetime.fromisoformat(s).astimezone(NY)


def auctions(symbols: list[str], start: str, end: str,
             feed: str = "sip") -> dict[str, list]:
    """Historical opening/closing auction prints per symbol.

    start/end: date (YYYY-MM-DD) or RFC3339. Each per-symbol record is a day:
    {d: date, o: [opening auctions], c: [closing auctions]}; each auction entry
    is {t: RFC3339-nanos, x: exch-code, p: price, s: size, c: cond}.
    """
    return _paged("auctions", "auctions", symbols, start, end, feed)


def quotes(symbols: list[str], start: str, end: str,
           feed: str = "sip") -> dict[str, list]:
    """Historical NBBO quotes per symbol.

    Each quote: {t, bp: bid px, bs: bid size, ap: ask px, as: ask size, ...}.
    feed="iex" works on the free tier; feed="sip" needs Algo Trader Plus.
    """
    return _paged("quotes", "quotes", symbols, start, end, feed)


def _venue_code(v: str) -> str:
    v = (v or "").strip().upper()
    return v if len(v) == 1 else VENUE_TO_CODE.get(v, v)


def official_open(resp: dict, venue_map: dict[str, str]) -> dict[str, dict]:
    """Extract the official opening print per symbol.

    resp:      an auctions() response ({symbol: [{d, o, c}, ...]}).
    venue_map: symbol -> primary listing venue, either a friendly name
               ("NASDAQ"/"NYSE", as data/weights.py emits) or a raw single-char
               exchange code ("Q"/"N").

    Returns symbol -> {price, ts (ET datetime), exch, size, cond, date} for the
    first opening auction whose exchange code equals the symbol's primary
    venue. Symbols with no matching opening print are omitted. Because the
    predictor queries a single session per run, the first match is the day's
    official open.
    """
    out: dict[str, dict] = {}
    for sym, days in (resp or {}).items():
        want = _venue_code(venue_map.get(sym, ""))
        for day in days or []:
            match = next((a for a in (day.get("o") or []) if a.get("x") == want),
                         None)
            if match:
                out[sym] = {"price": match.get("p"),
                            "ts": parse_ts(match.get("t", "")),
                            "exch": match.get("x"), "size": match.get("s"),
                            "cond": match.get("c"), "date": day.get("d")}
                break
    return out


def nbbo_at(quote_list: list[dict], target_et: dt.datetime) -> dict | None:
    """Bid/ask/mid at/nearest an ET timestamp.

    quote_list: the list quotes() returns for one symbol. target_et: aware ET
    datetime. Returns {bid, ask, mid, spread, bid_size, ask_size, ts, age_s}
    for the quote whose timestamp is closest to target, or None if empty.
    """
    best, best_gap = None, None
    for q in quote_list or []:
        ts = parse_ts(q.get("t", ""))
        if ts is None:
            continue
        gap = abs((ts - target_et).total_seconds())
        if best_gap is None or gap < best_gap:
            best, best_gap = (q, ts), gap
    if best is None:
        return None
    q, ts = best
    bid, ask = q.get("bp"), q.get("ap")
    both = bid is not None and ask is not None
    return {"bid": bid, "ask": ask,
            "mid": (bid + ask) / 2 if both else None,
            "spread": (ask - bid) if both else None,
            "bid_size": q.get("bs"), "ask_size": q.get("as"),
            "ts": ts, "age_s": best_gap}


class LiveIexQuotes:
    """Free real-time IEX quote websocket (wss).

    stdlib has no websocket client; live use needs `pip install websockets`
    (kept optional, same pattern as replica/stitch/feeds.py Massive). This class holds
    the auth/subscribe/normalize logic so the REST paths stay stdlib-only.
    """
    WS_URL = "wss://stream.data.alpaca.markets/v2/iex"

    def __init__(self):
        self.key = os.environ.get("ALPACA_API_KEY", "")
        self.secret = os.environ.get("ALPACA_API_SECRET", "")
        if not self.key or not self.secret:
            raise AlpacaError("ALPACA_API_KEY / ALPACA_API_SECRET not set.")

    def auth_message(self) -> str:
        return json.dumps({"action": "auth", "key": self.key,
                           "secret": self.secret})

    def subscribe_message(self, symbols: list[str]) -> str:
        return json.dumps({"action": "subscribe", "quotes": symbols})

    @staticmethod
    def normalize(msg: dict) -> dict:
        """Alpaca IEX quote event (T=='q') -> bid/ask/mid dict (ET ts)."""
        bid, ask = msg.get("bp"), msg.get("ap")
        both = bid is not None and ask is not None
        return {"symbol": msg.get("S"), "bid": bid, "ask": ask,
                "mid": (bid + ask) / 2 if both else None,
                "bid_size": msg.get("bs"), "ask_size": msg.get("as"),
                "ts": parse_ts(msg.get("t", ""))}

    async def stream(self, symbols: list[str], on_quote):
        """Connect, auth, subscribe; call on_quote(normalize(msg)) per tick.

        Needs `pip install websockets` (optional). Blocks until cancelled.
        """
        try:
            import websockets  # optional dep; imported lazily
        except ImportError as e:
            raise AlpacaError(
                "live IEX quotes need `pip install websockets`") from e
        async with websockets.connect(self.WS_URL) as ws:
            await ws.send(self.auth_message())
            await ws.send(self.subscribe_message(symbols))
            async for raw in ws:
                for msg in json.loads(raw):
                    if msg.get("T") == "q":
                        on_quote(self.normalize(msg))
