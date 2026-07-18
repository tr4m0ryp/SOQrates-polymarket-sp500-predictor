"""Databento transport: historical HTTP+JSON (stdlib) + live entrypoint.

Historical is pure stdlib (urllib/json/base64) against the timeseries
REST endpoint. Live is the one allowed exception: the DBN binary protocol
over TCP is impractical in stdlib, so `live_client()` lazily imports the
official `databento` package (`pip install databento`).

Datasets: XNAS.ITCH (Nasdaq NOII/imbalance, history to 2018),
XNYS.PILLAR (NYSE imbalance, history ~2025+). Env: DATABENTO_API_KEY.
"""
import base64
import json
import os
import urllib.parse
import urllib.request

_BASE = "https://hist.databento.com/v0"


class DatabentoError(RuntimeError):
    pass


def _key() -> str:
    key = os.environ.get("DATABENTO_API_KEY", "")
    if not key:
        raise DatabentoError(
            "DATABENTO_API_KEY not set - the auction replica needs it. "
            "Export the key and rerun.")
    return key


def get_range(dataset: str, schema: str, symbols: list[str],
              start: str, end: str) -> list[dict]:
    """timeseries.get_range with JSON encoding; returns decoded records.

    Newline-delimited JSON; each line is one DBN record. Behaviour preserved
    from the original single-file client - normalization happens downstream
    in schemas.py, not here.
    """
    params = urllib.parse.urlencode({
        "dataset": dataset, "schema": schema, "symbols": ",".join(symbols),
        "start": start, "end": end, "encoding": "json",
    })
    auth = base64.b64encode(f"{_key()}:".encode()).decode()
    req = urllib.request.Request(
        f"{_BASE}/timeseries.get_range?{params}",
        headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        text = r.read().decode()
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def live_client():
    """Authenticated `databento.Live` client (lazy import).

    stdlib has no DBN/TCP client, so the live leg needs the optional
    `pip install databento`. Imported here so the historical path and every
    module import stay dependency-free.
    """
    try:
        import databento
    except ImportError as e:
        raise DatabentoError(
            "live Databento needs `pip install databento`") from e
    return databento.Live(key=_key())
