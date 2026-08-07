"""Group A - midnight prefetch: slow-moving context, fetched once per night.

Everything here is stable enough to fetch at ~00:05 ET and reuse in every
LLM run until the open. The LLM never sees our own market data (ES gap,
cross-asset moves) - that evidence already lives in the quant model and
would only anchor the LLM; market moves act as run TRIGGERS only.

Group B (continuous, in news/stream registry below): wire headlines,
Truth Social / key accounts, GDELT sweeps, EDGAR post-close filings, and
the 8:30 release endpoints - unpredictable arrival, streamed or polled.
Prediction-market odds sit in BOTH: tonight's level is prefetched as the
baseline prior; a large overnight delta (>5 pts) is a Group-B wake event,
injected as text ("Hormuz-normal odds fell 62->48 overnight").
"""
import datetime as dt
import json
import urllib.request

from spx.config import CACHE, NY
from spx.macro import releases

_UA = {"User-Agent": "Mozilla/5.0"}
_GAMMA = "https://gamma-api.polymarket.com/events"

# Polymarket structural markets watched as regime dials
PREDICTION_TAGS = ("economy", "geopolitics")

# Group B registry - continuous feeds (implemented as each key arrives)
STREAM_FEEDS = {
    "alpaca_news_ws": "wss://stream.data.alpaca.markets/v1beta1/news",
    "truth_social": "apify/scrapecreators poller, 1-5 min cadence",
    "gdelt_sweep": "news.gdelt.window_snapshot at each checkpoint",
    "edgar_8k": "SEC EDGAR real-time filings (evening: mega-cap earnings)",
    "release_endpoints": "bls.gov/bea.gov machine-readable at 08:30:00",
}


def _get(url: str):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def prediction_odds(limit: int = 8) -> list[dict]:
    """Baseline odds snapshot of the big structural markets."""
    out = []
    for tag in PREDICTION_TAGS:
        try:
            evs = _get(f"{_GAMMA}?closed=false&limit={limit}&order=volume"
                       f"&ascending=false&tag_slug={tag}")
        except Exception:
            continue
        for e in evs:
            m = (e.get("markets") or [{}])[0]
            prices = json.loads(m.get("outcomePrices") or "[]")
            outcomes = json.loads(m.get("outcomes") or "[]")
            out.append({
                "tag": tag, "title": e["title"],
                "volume": round(float(e.get("volume") or 0)),
                "odds": dict(zip(outcomes, prices)),
            })
    return out


def build(date: dt.date | None = None) -> dict:
    """The static context block for every LLM run tonight."""
    date = date or dt.datetime.now(NY).date()
    ctx = {
        "date": str(date),
        "releases_0830": releases.release_names(date),
        "is_nfp_friday": releases.is_nfp_friday(date),
        "prediction_baseline": prediction_odds(),
        # slots to fill as sources come online:
        "nowcast_cpi": None,          # Cleveland Fed daily nowcast
        "consensus": None,            # release consensus estimates
        "earnings_after_close": None, # index heavyweights reporting tonight
    }
    (CACHE / "news_prefetch.json").write_text(json.dumps(ctx, indent=1))
    return ctx
