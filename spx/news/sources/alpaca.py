"""Alpaca news wire - Group-B real-time headline stream + historical REST.

Feeds the 'real-time news wire stream' row of the Group-B registry
(news/prefetch.py STREAM_FEEDS["alpaca_news_ws"]). Both the historical REST
endpoint and the live websocket normalise into the news-layer headline dict
the LLM prompt consumes:

    {id, headline, summary, symbols, created_at, url}

where created_at is an ISO-8601 string in America/New_York (config.NY).

Public surface
--------------
- normalize(raw)                 -> one Alpaca record (REST *or* ws) -> dict
- fetch_range(start, end, syms)  -> historical headlines, stdlib-only, paged
- NewsStream                     -> live wss client (auth/subscribe/run)
- run_stream(on_headline, syms)  -> blocking convenience wrapper

Auth: free API key, env ALPACA_API_KEY / ALPACA_API_SECRET (APCA headers).
Historical archive reaches back to ~2015. The REST path is pure urllib; the
websocket loop lazily imports `websockets` (like replica/stitch/feeds.py) so the
dependency stays optional until the stream is actually run.
"""
import datetime as dt
import json
import os
import urllib.parse
import urllib.request

from spx.config import NY

_REST_URL = "https://data.alpaca.markets/v1beta1/news"
_WS_URL = "wss://stream.data.alpaca.markets/v1beta1/news"


class AlpacaNewsError(RuntimeError):
    pass


def _env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        raise AlpacaNewsError(
            f"{name} not set - get a free key at alpaca.markets and export "
            "ALPACA_API_KEY / ALPACA_API_SECRET.")
    return val


def _headers() -> dict:
    return {"APCA-API-KEY-ID": _env("ALPACA_API_KEY"),
            "APCA-API-SECRET-KEY": _env("ALPACA_API_SECRET"),
            "Accept": "application/json"}


# ---------------------------------------------------------------- normalise

def _to_et(ts) -> str:
    """RFC-3339 / datetime -> ISO-8601 string in America/New_York."""
    if isinstance(ts, dt.datetime):
        d = ts
    else:
        s = str(ts).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        if "." in s:                       # clamp fractional secs to micros
            head, frac = s.split(".", 1)
            i = 0
            while i < len(frac) and frac[i].isdigit():
                i += 1
            digits = (frac[:i] + "000000")[:6]
            s = f"{head}.{digits}{frac[i:]}"
        d = dt.datetime.fromisoformat(s)
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(NY).isoformat()


def normalize(raw: dict) -> dict:
    """Alpaca news record (REST item or ws 'n' message) -> headline dict.

    Extra Alpaca fields (author, content, updated_at, source, images) are
    dropped; the LLM layer only reads id/headline/summary/symbols/ts/url.
    """
    syms = raw.get("symbols") or []
    if isinstance(syms, str):
        syms = [s.strip() for s in syms.split(",") if s.strip()]
    return {"id": str(raw.get("id", "")),
            "headline": raw.get("headline") or "",
            "summary": raw.get("summary") or "",
            "symbols": list(syms),
            "created_at": _to_et(raw.get("created_at") or raw.get("updated_at")),
            "url": raw.get("url") or ""}


# ----------------------------------------------------------- historical REST

def _fmt_time(x) -> str | None:
    if x is None:
        return None
    if isinstance(x, dt.datetime):
        return x.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(x, dt.date):
        return x.isoformat()
    return str(x)


def build_request(start=None, end=None, symbols=None, limit: int = 50,
                  page_token: str | None = None,
                  sort: str = "desc") -> urllib.request.Request:
    """The signed GET for one page (exposed for testing without a live key)."""
    params: dict[str, str] = {"limit": str(min(max(int(limit), 1), 50)),
                              "sort": sort}
    if symbols:
        params["symbols"] = ",".join(symbols)
    for key, val in (("start", _fmt_time(start)), ("end", _fmt_time(end))):
        if val:
            params[key] = val
    if page_token:
        params["page_token"] = page_token
    url = f"{_REST_URL}?{urllib.parse.urlencode(params)}"
    return urllib.request.Request(url, headers=_headers(), method="GET")


def fetch_range(start=None, end=None, symbols=None, limit: int = 50,
                max_results: int = 500, sort: str = "desc") -> list[dict]:
    """Historical headlines in [start, end], paginated, normalised to ET.

    start/end accept RFC-3339 strings, date, or datetime (None = open-ended).
    symbols is a list of tickers (None/empty = all wire news). Follows
    next_page_token until exhausted or max_results reached.
    """
    out: list[dict] = []
    token: str | None = None
    while len(out) < max_results:
        req = build_request(start, end, symbols, limit, token, sort)
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.load(r)
        for item in body.get("news", []):
            out.append(normalize(item))
        token = body.get("next_page_token")
        if not token:
            break
    return out[:max_results]


# --------------------------------------------------------------- live stream

class NewsStream:
    """Live Alpaca news websocket (wss).

    stdlib ships no websocket client, so run() lazily imports `websockets`
    (pip install websockets); auth/subscribe payloads are built eagerly so
    the message contract is testable without the dependency or a live key.
    """
    WS_URL = _WS_URL

    def __init__(self, symbols=("*",)):
        self.key = _env("ALPACA_API_KEY")
        self.secret = _env("ALPACA_API_SECRET")
        self.symbols = list(symbols) or ["*"]

    def auth_message(self) -> str:
        return json.dumps({"action": "auth", "key": self.key,
                           "secret": self.secret})

    def subscribe_message(self) -> str:
        return json.dumps({"action": "subscribe", "news": self.symbols})

    @staticmethod
    def _dispatch(payload):
        """Parse one ws frame into (headlines, control_messages)."""
        msgs = json.loads(payload)
        if isinstance(msgs, dict):
            msgs = [msgs]
        heads, control = [], []
        for m in msgs:
            if m.get("T") == "n":
                heads.append(normalize(m))
            elif m.get("T") == "error":
                raise AlpacaNewsError(f"stream error: {m.get('msg')}")
            else:
                control.append(m)
        return heads, control

    async def run(self, on_headline, *, reconnect: bool = True,
                  max_backoff: float = 30.0) -> None:
        """Connect, authenticate, subscribe, then push normalised headlines.

        on_headline may be sync or async and is awaited if it returns a
        coroutine. Reconnects with exponential backoff on connection loss.
        """
        import asyncio
        import websockets                      # lazy optional dep

        backoff = 1.0
        while True:
            try:
                async with websockets.connect(self.WS_URL,
                                              max_size=None) as ws:
                    await ws.recv()            # [{"T":"success","msg":"connected"}]
                    await ws.send(self.auth_message())
                    await ws.recv()            # auth ack (raises via _dispatch on error)
                    await ws.send(self.subscribe_message())
                    backoff = 1.0
                    async for frame in ws:
                        heads, _ = self._dispatch(frame)
                        for h in heads:
                            res = on_headline(h)
                            if asyncio.iscoroutine(res):
                                await res
            except AlpacaNewsError:
                raise
            except Exception:
                if not reconnect:
                    raise
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)


def run_stream(on_headline, symbols=("*",), *, reconnect: bool = True) -> None:
    """Blocking helper: run the stream on the current thread until killed."""
    import asyncio
    asyncio.run(NewsStream(symbols).run(on_headline, reconnect=reconnect))
