"""Thin Databento historical client for auction/imbalance data.

Requires DATABENTO_API_KEY in the environment. UNTESTED until a key exists —
endpoints per https://databento.com/docs (timeseries.get_range, JSON encoding).
Datasets: XNAS.ITCH (Nasdaq NOII, history to 2018), XNYS.PILLAR (NYSE
imbalances, history ~2025+). Schema: "imbalance".
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
    """timeseries.get_range with JSON encoding; returns decoded records."""
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


def nasdaq_noii(symbols: list[str], start: str, end: str) -> list[dict]:
    """Opening-cross NOII records (near/far/ref prices, paired/imbalance qty)."""
    return get_range("XNAS.ITCH", "imbalance", symbols, start, end)


def nyse_imbalance(symbols: list[str], start: str, end: str) -> list[dict]:
    """NYSE auction imbalance records (ref/indicative match prices, qtys)."""
    return get_range("XNYS.PILLAR", "imbalance", symbols, start, end)
