"""LSEG Tick History client (DataScope Select REST API).

For academic access granted via a university library (e.g. UvA). Historical
ONLY (data ~2h after close) - live legs still need NCDS/dxFeed/Massive.
Academic licenses are research-use only: fine for validating the replica,
not for powering live trading.

Flow (documented at developers.lseg.com, RTH REST API):
  1. POST /Authentication/RequestToken  {Credentials:{Username,Password}}
  2. POST /Extractions/ExtractRaw       (TickHistoryRawExtractionRequest)
  3. poll the 202 Location until done
  4. GET  .../ExtractRawResult(...)/$value  -> gzipped CSV

Credentials via env: DSS_USERNAME, DSS_PASSWORD (DataScope Select account).
UNTESTED until credentials exist. RIC conventions: AAPL.OQ (Nasdaq),
IBM.N (NYSE); imbalance/auction fields arrive as MarketPrice FIDs in raw
messages - finalize the field mapping against a first real extraction.
"""
import gzip
import io
import json
import os
import time
import urllib.request

_BASE = "https://selectapi.datascope.refinitiv.com/RestApi/v1"


class LsegError(RuntimeError):
    pass


def _req(url: str, body: dict | None = None, token: str | None = None,
         raw: bool = False):
    headers = {"Content-Type": "application/json", "Prefer": "respond-async"}
    if token:
        headers["Authorization"] = f"Token {token}"
    if raw:
        headers["Accept-Encoding"] = "gzip"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers)
    return urllib.request.urlopen(req, timeout=300)


def auth_token() -> str:
    user = os.environ.get("DSS_USERNAME", "")
    pw = os.environ.get("DSS_PASSWORD", "")
    if not user or not pw:
        raise LsegError("DSS_USERNAME / DSS_PASSWORD not set - request "
                        "DataScope Select credentials from the library first.")
    with _req(f"{_BASE}/Authentication/RequestToken",
              {"Credentials": {"Username": user, "Password": pw}}) as r:
        return json.load(r)["value"]


def raw_extraction(rics: list[str], start_utc: str, end_utc: str,
                   token: str | None = None) -> bytes:
    """Tick History Raw extraction (all venue messages incl. auction FIDs).

    start/end e.g. '2026-06-22T13:20:00.000Z'. Returns decompressed CSV bytes.
    """
    token = token or auth_token()
    body = {"ExtractionRequest": {
        "@odata.type": "#DataScope.Select.Api.Extractions.ExtractionRequests."
                       "TickHistoryRawExtractionRequest",
        "IdentifierList": {
            "@odata.type": "#DataScope.Select.Api.Extractions."
                           "ExtractionRequests.InstrumentIdentifierList",
            "InstrumentIdentifiers": [
                {"Identifier": r, "IdentifierType": "Ric"} for r in rics],
            "ValidationOptions": {"AllowHistoricalInstruments": True},
        },
        "Condition": {
            "MessageTimeStampIn": "GmtUtc",
            "ReportDateRangeType": "Range",
            "QueryStartDate": start_utc,
            "QueryEndDate": end_utc,
            "DisplaySourceRIC": True,
            "DomainCode": "MarketPrice",
        },
    }}
    resp = _req(f"{_BASE}/Extractions/ExtractRaw", body, token)
    if resp.status == 202:                       # async: poll Location
        loc = resp.headers["Location"]
        while True:
            time.sleep(15)
            poll = _req(loc, token=token)
            if poll.status == 200:
                resp = poll
                break
    job = json.load(resp)
    job_id = job["JobId"]
    with _req(f"{_BASE}/Extractions/RawExtractionResults('{job_id}')/$value",
              token=token, raw=True) as r:
        payload = r.read()
        if r.headers.get("Content-Encoding") == "gzip" or payload[:2] == b"\x1f\x8b":
            payload = gzip.decompress(payload)
        return payload


def quirk_day_pull(tickers_nasdaq: list[str], tickers_nyse: list[str],
                   date: str) -> bytes:
    """One quirk day, 9:20-9:35 ET (13:20-13:35 UTC in summer), both venues."""
    rics = [f"{t}.OQ" for t in tickers_nasdaq] + [f"{t}.N" for t in tickers_nyse]
    return raw_extraction(rics, f"{date}T13:15:00.000Z", f"{date}T13:40:00.000Z")
