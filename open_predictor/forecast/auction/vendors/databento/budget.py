"""Hard spend cap for metered Databento pulls.

Databento bills per byte delivered, so an unattended backfill needs a
governor. Every priced request asks `metadata.get_cost` first (that call is
free), adds the quote to a running total kept in `.cache/databento_spend.json`,
and refuses the request when the total would cross the cap.

The cap comes from DATABENTO_SPEND_CAP_USD (default 50.00, the value agreed
for the 2026-08 backfill run). Set DATABENTO_SPEND_CAP_USD=0 to make every
priced call refuse, which turns a run into a dry run.

The ledger is advisory in one direction only: it can refuse a pull that would
exceed the cap, but it cannot refund one already made, so `reserve()` records
the quote BEFORE the data request is issued.
"""
import base64
import json
import os
import urllib.parse
import urllib.request

from open_predictor.config import CACHE

_META = "https://hist.databento.com/v0"
_LEDGER = CACHE / "databento_spend.json"
DEFAULT_CAP_USD = 50.00


class BudgetError(RuntimeError):
    """Raised when a request would exceed the configured spend cap."""


def cap_usd() -> float:
    raw = os.environ.get("DATABENTO_SPEND_CAP_USD")
    if raw is None or raw == "":
        return DEFAULT_CAP_USD
    return float(raw)


def _read() -> dict:
    try:
        return json.loads(_LEDGER.read_text())
    except (OSError, ValueError):
        return {"spent_usd": 0.0, "entries": []}


def spent_usd() -> float:
    return float(_read().get("spent_usd", 0.0))


def remaining_usd() -> float:
    return max(0.0, cap_usd() - spent_usd())


def quote(dataset: str, schema: str, symbols: list[str],
          start: str, end: str, stype_in: str = "raw_symbol") -> float:
    """Cost in USD of a would-be request. Free metadata call."""
    key = os.environ.get("DATABENTO_API_KEY", "")
    if not key:
        raise BudgetError("DATABENTO_API_KEY is not set")
    auth = base64.b64encode(f"{key}:".encode()).decode()
    body = urllib.parse.urlencode({
        "dataset": dataset, "schema": schema, "start": start, "end": end,
        "symbols": ",".join(symbols), "stype_in": stype_in,
        "mode": "historical-streaming",
    }).encode()
    req = urllib.request.Request(
        f"{_META}/metadata.get_cost", data=body,
        headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return float(json.loads(r.read()))


def reserve(label: str, cost: float) -> None:
    """Record `cost` against the cap, or refuse if it would cross it.

    Call this immediately BEFORE issuing the priced request, so a crash
    mid-pull leaves the ledger pessimistic rather than optimistic.
    """
    led = _read()
    new_total = float(led.get("spent_usd", 0.0)) + cost
    if new_total > cap_usd():
        raise BudgetError(
            f"refused {label}: ${cost:.4f} would take spend to "
            f"${new_total:.2f}, over the ${cap_usd():.2f} cap "
            f"(${remaining_usd():.2f} left)")
    led["spent_usd"] = new_total
    led.setdefault("entries", []).append({"label": label, "usd": cost})
    _LEDGER.parent.mkdir(exist_ok=True)
    _LEDGER.write_text(json.dumps(led, indent=1))


def check_and_reserve(label: str, dataset: str, schema: str,
                      symbols: list[str], start: str, end: str) -> float:
    """Quote a request, reserve it against the cap, and return the cost."""
    cost = quote(dataset, schema, symbols, start, end)
    reserve(label, cost)
    return cost
