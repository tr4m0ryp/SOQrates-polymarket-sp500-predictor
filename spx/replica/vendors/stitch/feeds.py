"""Vendor-stitch auction feeds (fallback when Databento is unavailable).

Nasdaq leg : NCDS / Nasdaq Data Link (official TotalView incl. NOII) - needs a
             signed Nasdaq agreement; stub below documents the interface.
NYSE leg   : Massive (ex-Polygon.io) "Imbalances Expansion" websocket - LIVE
             ONLY, no history; NYSE-listed names only; $49/mo add-on plan.
             Fields per massive.com/docs/websocket/stocks/imbalances:
               o  = imbalance qty (shares)
               p  = paired qty (shares)
               b  = book clearing / indicative match price
               a  = auction type (M core-opening, C closing, H halt/resume)
               at = planned auction time (epoch ms)

Both normalize into the same dicts replica/core/assembly.py consumes
(ticker / pred_open / paired / imbalance / venue / ts), so swapping back to
Databento later is a one-line change in the caller.

Public surface: MassiveNYSEImbalance, NCDSNasdaqNOII, FeedError.
Env: MASSIVE_API_KEY (Massive), NCDS_CLIENT_ID / NCDS_CLIENT_SECRET (Nasdaq).
"""
import json
import os
from datetime import datetime, timezone

from spx.config import NY


class FeedError(RuntimeError):
    pass


def _env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        raise FeedError(f"{name} not set")
    return val


def _as_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _as_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _epoch_to_et(v):
    """Unix epoch timestamp -> aware ET datetime; magnitude-detected units.

    Massive/Polygon feeds mix seconds, milliseconds, micro-, and nanoseconds
    depending on the channel, so scale off the integer's digit count rather
    than assume one unit. Returns None on non-numeric input.
    """
    n = _as_float(v)
    if n is None:
        return None
    a = abs(n)
    if a >= 1e17:        # nanoseconds
        n /= 1e9
    elif a >= 1e14:      # microseconds
        n /= 1e6
    elif a >= 1e11:      # milliseconds
        n /= 1e3
    return datetime.fromtimestamp(n, timezone.utc).astimezone(NY)


class MassiveNYSEImbalance:
    """Live NYSE opening-auction imbalance via the Massive websocket (wss).

    Massive is the ex-Polygon.io tape; NYSE imbalances need the $49/mo
    "Imbalances Expansion" add-on. Coverage caveats before trusting output:
      * NYSE-listed names ONLY (the primary-listing opening auction).
      * REAL-TIME ONLY - Massive serves no imbalance history; backtests must
        use the LSEG/Databento paths instead.
      * A message stream, not a snapshot: the last core-opening (a=='M') event
        before 9:30:00 carries the freshest indicative clearing price.

    stdlib has no websocket client; the live path (`stream_opening`) needs
    `pip install websockets`, imported lazily so the dependency stays optional.
    auth/subscribe/normalize are pure and unit-testable without the dep.
    """
    WS_URL = "wss://socket.massive.com/stocks"
    CHANNEL = "NOI"                 # subscription prefix, per-symbol: NOI.<sym>
    OPENING_AUCTION = "M"           # `a` code for the core opening cross

    def __init__(self):
        self.key = _env("MASSIVE_API_KEY")

    def auth_message(self) -> str:
        return json.dumps({"action": "auth", "params": self.key})

    def subscribe_message(self, tickers: list[str]) -> str:
        params = ",".join(f"{self.CHANNEL}.{t}" for t in tickers)
        return json.dumps({"action": "subscribe", "params": params})

    @staticmethod
    def normalize(msg: dict) -> dict:
        """Massive imbalance event -> assembly-ready dict.

        Field map (massive.com/docs/websocket/stocks/imbalances):
          o  -> imbalance             (imbalance quantity, shares)
          p  -> paired                (paired quantity, shares)
          b  -> pred_open             (book clearing / indicative match price)
          a  -> auction_type          (M core-opening, C closing, H halt)
          at -> planned_auction_time  (epoch -> ET datetime)
        Symbol arrives as `sym` (Polygon/Massive convention); `T`/`symbol`
        are accepted as fallbacks. Event ts is `t`, falling back to `at`.
        """
        ticker = next((str(msg[k]) for k in ("sym", "T", "symbol")
                       if msg.get(k)), None)
        at = msg.get("at")
        return {
            "ticker": ticker,
            "pred_open": _as_float(msg.get("b")),
            "paired": _as_int(msg.get("p")),
            "imbalance": _as_int(msg.get("o")),
            "auction_type": msg.get("a"),
            "planned_auction_time": _epoch_to_et(at),
            "venue": "NYSE",
            "ts": _epoch_to_et(msg.get("t", at)),
        }

    async def stream_opening(self, symbols: list[str], on_imbalance):
        """Connect, auth, subscribe; deliver normalized opening imbalances.

        Filters to core-opening events (a == 'M'); closing (C) and
        halt/resume (H) messages are skipped. Calls `on_imbalance(dict)` per
        opening imbalance, each a normalize() dict. Messages arrive batched in
        JSON arrays (Polygon/Massive convention). Real-time only - no history.
        Needs the optional `pip install websockets`. Blocks until cancelled.
        """
        try:
            import websockets       # optional dep; imported lazily
        except ImportError as e:
            raise FeedError(
                "live NYSE imbalances need `pip install websockets`") from e
        async with websockets.connect(self.WS_URL) as ws:
            await ws.send(self.auth_message())
            await ws.send(self.subscribe_message(symbols))
            async for raw in ws:
                payload = json.loads(raw)
                batch = payload if isinstance(payload, list) else [payload]
                for msg in batch:
                    if msg.get("a") == self.OPENING_AUCTION:
                        on_imbalance(self.normalize(msg))


class NCDSNasdaqNOII:
    """Nasdaq Cloud Data Service TotalView/NOII - official Nasdaq leg.

    Requires an NCDS agreement + credentials (client id/secret, Kafka-style
    streaming; SDKs at github.com/Nasdaq). Interface kept identical to the
    Databento path: fetch/stream NOII near prices per ticker.
    """

    def __init__(self):
        self.client_id = _env("NCDS_CLIENT_ID")
        self.client_secret = _env("NCDS_CLIENT_SECRET")
        raise FeedError("NCDS streaming not implemented - sign Nasdaq "
                        "agreement first, then wire the official SDK here.")

    @staticmethod
    def normalize(msg: dict) -> dict:
        return {"ticker": msg.get("symbol"), "pred_open": msg.get("nearPrice"),
                "paired": msg.get("pairedShares"),
                "imbalance": msg.get("imbalanceShares"),
                "venue": "NASDAQ", "ts": msg.get("timestamp")}
