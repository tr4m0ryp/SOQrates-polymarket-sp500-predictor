"""Live Nasdaq NOII snapshots via the Webull OpenAPI (stdlib-only client).

The ONLY free live NOII (Net Order Imbalance Indicator) leg in this repo. It
polls Webull's auction-snapshot endpoint every 5s across the 9:28-9:30 ET
opening window and normalizes each snapshot into the same dict the ITCH path
produces (paired_shares / imbalance_shares / imbalance_direction / far_price /
near_price / current_reference_price), so replica/assembly.py and
replica/montecarlo.py consume it unchanged.

Caveats (read before trusting live output):
  * FREE but not tick-continuous - 5-second snapshots, so the 9:29:5x preview
    that best predicts the 9:30:00 cross may be missed by up to ~5s.
  * Needs a FUNDED Webull OpenAPI account (app key/secret + a real-time US
    market-data subscription); Nasdaq-listed names only for NOII.
  * Response field completeness under auction-load is UNVERIFIED - the
    field-name -> canonical-key map (`_ALIASES`) covers the documented and
    common camel/snake variants and must be confirmed against a real payload.

Signing (developer.webull.com "Authentication > Signature"; cross-checked
against webull-inc/openapi-python-sdk default_signature_composer.py, used here
as REFERENCE ONLY - we do not import it):
  1. sign set = {x-app-key, x-timestamp, x-signature-version,
     x-signature-algorithm, x-signature-nonce, host} + all query params,
     keys lowercased.
  2. sort keys A-Z, join `k=v` with `&`  -> str1
  3. string_to_sign = `path&str1`  (+ `&SHA256(body)`.upper() for a body)
  4. percent-encode string_to_sign with NOTHING safe (even `/`, `&`, `=`)
  5. signature = base64( HMAC-SHA256( app_secret + "&", encoded ) )
The SDK's committed default is HMAC-SHA1 + uppercase-MD5 body hash; the current
public docs specify HMAC-SHA256 + uppercase-SHA256 body hash (implemented here).
GET snapshots carry no body, so the hash choice is moot for this leg - but the
HMAC algorithm still MUST be confirmed against a live key.

Public surface: snapshot(), normalize_noii(), poll_opening(), WebullError.
Env: WEBULL_APP_KEY, WEBULL_APP_SECRET (WEBULL_ACCOUNT_ID reserved, unused here).
"""
import base64
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

from config import NY

HOST = "api.webull.com"
PATH = "/openapi/market-data/stock/noii/snapshot"
CATEGORY = "US_STOCK"
SIGN_ALGORITHM = "HMAC-SHA256"     # public-doc default; SDK default = HMAC-SHA1
SIGN_VERSION = "1.0"
API_VERSION = "v2"                  # x-version; excluded from the signature
RATE_LIMIT_PER_MIN = 600

# Canonical NOII key -> candidate source field names (lowercased, symbols
# stripped). Confirm/extend against a real Webull NOII payload.
_ALIASES = {
    "near_price": ("nearprice", "nearclearingprice", "indicativenearprice",
                   "nearindicativeprice", "near"),
    "far_price": ("farprice", "farclearingprice", "indicativefarprice",
                  "farindicativeprice", "far"),
    "current_reference_price": ("referenceprice", "refprice",
                                "currentreferenceprice", "matchprice",
                                "auctionreferenceprice"),
    "paired_shares": ("pairedshares", "pairedqty", "pairedquantity",
                      "matchquantity", "matchqty", "matchedshares"),
    "imbalance_shares": ("imbalanceshares", "imbalanceqty",
                         "imbalancequantity", "imbalancevolume"),
}
_SIDE_KEYS = ("imbalanceside", "imbalancedirection", "imbalancesidename",
              "side", "direction")
_SYMBOL_KEYS = ("symbol", "ticker", "instrument")
_NEST_KEYS = ("noii", "imbalance", "auction", "openimbalance")
_BUY = {"B", "BUY", "BUY_SIDE", "BUYSIDE", "BID"}
_SELL = {"S", "SELL", "SELL_SIDE", "SELLSIDE", "ASK"}


class WebullError(RuntimeError):
    """Auth, signing, transport, or bad-response failure from the Webull leg."""


def _env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        raise WebullError(f"{name} not set - fund a Webull OpenAPI account and "
                          "export WEBULL_APP_KEY / WEBULL_APP_SECRET.")
    return val


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sign_headers(host: str, path: str, query: dict, app_key: str,
                 app_secret: str, *, algorithm: str = SIGN_ALGORITHM,
                 version: str = API_VERSION, body: str | None = None,
                 timestamp: str | None = None,
                 nonce: str | None = None) -> dict:
    """Build the signed request header set (timestamp/nonce injectable for tests)."""
    ts = timestamp or _iso_now()
    non = nonce or uuid.uuid4().hex
    params = {
        "x-app-key": app_key,
        "x-timestamp": ts,
        "x-signature-version": SIGN_VERSION,
        "x-signature-algorithm": algorithm,
        "x-signature-nonce": non,
        "host": host,
    }
    for k, v in (query or {}).items():
        params[k.lower()] = str(v)
    pairs = "&".join(f"{k}={params[k]}" for k in sorted(params))
    string_to_sign = f"{path}&{pairs}" if path else pairs
    if body:
        string_to_sign += "&" + hashlib.sha256(body.encode()).hexdigest().upper()
    encoded = quote(string_to_sign, safe="")
    digest = hmac.new((app_secret + "&").encode(), encoded.encode(),
                      hashlib.sha256).digest()
    return {
        "x-app-key": app_key,
        "x-timestamp": ts,
        "x-signature": base64.b64encode(digest).decode(),
        "x-signature-algorithm": algorithm,
        "x-signature-version": SIGN_VERSION,
        "x-signature-nonce": non,
        "x-version": version,
        "Content-Type": "application/json",
    }


def snapshot(symbols, *, category: str = CATEGORY, host: str = HOST,
             path: str = PATH, timeout: float = 10.0) -> dict:
    """GET the latest NOII snapshot for `symbols` (str or list). Raw JSON back.

    Nasdaq-listed names only carry NOII; pass Nasdaq tickers. Up to ~100
    symbols per call per the snapshot contract.
    """
    app_key = _env("WEBULL_APP_KEY")
    app_secret = _env("WEBULL_APP_SECRET")
    if isinstance(symbols, (list, tuple)):
        symbols = ",".join(symbols)
    query = {"symbols": symbols, "category": category}
    headers = sign_headers(host, path, query, app_key, app_secret)
    url = f"https://{host}{path}?{urlencode(query)}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:300]
        raise WebullError(f"Webull NOII HTTP {exc.code}: {detail!r}") from exc
    except urllib.error.URLError as exc:
        raise WebullError(f"Webull NOII transport error: {exc.reason}") from exc


def _records(payload) -> list[dict]:
    """Pull the list of per-symbol snapshot dicts from an unknown envelope."""
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("data", "snapshots", "result", "results", "items"):
            inner = payload.get(key)
            if isinstance(inner, list):
                return [r for r in inner if isinstance(r, dict)]
        if any(k.lower() in _SYMBOL_KEYS for k in payload):
            return [payload]
    return []


def _nk(key: str) -> str:
    """Compact key: lowercase with separators removed (near_price -> nearprice)."""
    return key.lower().replace("_", "").replace("-", "").replace(" ", "")


def _flatten(raw: dict) -> dict:
    """Compact-key view, merging a nested 'noii'/'imbalance' sub-object if any."""
    flat = {}
    for k, v in raw.items():
        ck = _nk(k)
        if isinstance(v, dict) and ck in _NEST_KEYS:
            for ik, iv in v.items():
                flat.setdefault(_nk(ik), iv)
        else:
            flat.setdefault(ck, v)
    return flat


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


def _direction(v) -> str:
    if v is None:
        return "N"
    s = str(v).strip().upper()
    if s in _BUY:
        return "B"
    if s in _SELL:
        return "S"
    if s in ("N", "NONE", "NO_IMBALANCE", "", "0"):
        return "N"
    return s[:1] or "N"


def normalize_noii(raw: dict) -> dict:
    """Webull NOII snapshot -> canonical dict matching the ITCH NOII shape."""
    flat = _flatten(raw)
    out = {
        "ticker": next((str(flat[k]) for k in _SYMBOL_KEYS if flat.get(k)), None),
        "near_price": None,
        "far_price": None,
        "current_reference_price": None,
        "paired_shares": None,
        "imbalance_shares": None,
        "imbalance_direction": "N",
    }
    for key, cands in _ALIASES.items():
        for c in cands:
            if c in flat and flat[c] is not None:
                val = _as_int(flat[c]) if key.endswith("_shares") else _as_float(flat[c])
                if val is not None:
                    out[key] = val
                    break
    for c in _SIDE_KEYS:
        if c in flat and flat[c] is not None:
            out["imbalance_direction"] = _direction(flat[c])
            break
    return out


def poll_opening(symbols, on_snapshot, *, category: str = CATEGORY,
                 interval_s: int = 5, start=(9, 28), end=(9, 30),
                 now_fn=None, sleep_fn=time.sleep) -> int:
    """Poll NOII every `interval_s` across the ET opening-auction window.

    Fixed cadence on an interval-aligned grid (no wall-clock randomness). Each
    tick calls `on_snapshot(records, ts_et)` where `records` is a list of
    normalize_noii() dicts. `now_fn`/`sleep_fn` are injectable for testing.
    Returns the number of ticks fetched. Nasdaq-listed names only.
    """
    now_fn = now_fn or (lambda: datetime.now(NY))
    now = now_fn()
    start_dt = now.replace(hour=start[0], minute=start[1], second=0, microsecond=0)
    end_dt = now.replace(hour=end[0], minute=end[1], second=0, microsecond=0)
    if now < start_dt:
        sleep_fn((start_dt - now).total_seconds())
    ticks = 0
    while now_fn() < end_dt:
        try:
            records = [normalize_noii(r) for r in
                       _records(snapshot(symbols, category=category))]
            on_snapshot(records, now_fn())
        except WebullError:
            on_snapshot([], now_fn())
        ticks += 1
        nxt = start_dt + timedelta(seconds=ticks * interval_s)
        if nxt >= end_dt:
            break
        sleep_fn(max(0.0, (nxt - now_fn()).total_seconds()))
    return ticks
