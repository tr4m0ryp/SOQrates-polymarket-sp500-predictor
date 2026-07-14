"""Vendor-stitch auction feeds (fallback when Databento is unavailable).

Nasdaq leg : NCDS / Nasdaq Data Link (official TotalView incl. NOII) - needs a
             signed Nasdaq agreement; stub below documents the interface.
NYSE leg   : Massive (ex-Polygon.io) "Imbalances Expansion" websocket - LIVE
             ONLY, no history. Fields per massive.com/docs: b = book clearing
             price, p = paired qty, o = imbalance qty.

Both normalize into the same dicts replica/assembly.py consumes, so swapping
back to Databento later is a one-line change in the caller.
"""
import json
import os
import urllib.request


class FeedError(RuntimeError):
    pass


def _env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        raise FeedError(f"{name} not set")
    return val


class MassiveNYSEImbalance:
    """Live NYSE opening-auction NOI via Massive websocket (wss).

    stdlib has no websocket client; live use needs `pip install websockets`.
    This class holds auth/subscribe/normalize logic so the dependency stays
    optional until a key exists.
    """
    WS_URL = "wss://socket.massive.com/stocks"

    def __init__(self):
        self.key = _env("MASSIVE_API_KEY")

    def auth_message(self) -> str:
        return json.dumps({"action": "auth", "params": self.key})

    def subscribe_message(self, tickers: list[str]) -> str:
        return json.dumps({"action": "subscribe",
                           "params": ",".join(f"NOI.{t}" for t in tickers)})

    @staticmethod
    def normalize(msg: dict) -> dict:
        """Massive NOI event -> assembly-ready dict."""
        return {"ticker": msg.get("T"), "pred_open": msg.get("b"),
                "paired": msg.get("p"), "imbalance": msg.get("o"),
                "venue": "NYSE", "ts": msg.get("t")}


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
