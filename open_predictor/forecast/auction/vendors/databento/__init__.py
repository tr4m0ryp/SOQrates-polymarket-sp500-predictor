"""Databento auction-data client (historical stdlib + optional live SDK).

Covers all four auction data types: #1 Nasdaq NOII, #2 NYSE imbalance,
#3 realized cross prints+timestamps, #4 pre-open NBBO. Historical is pure
stdlib HTTP+JSON; live is behind a lazy `import databento`. Hist and live
share the schemas.py normalize_* functions, so both yield identical dicts.

Preserved public names: get_range, nasdaq_noii, nyse_imbalance.
"""
from open_predictor.forecast.auction.vendors.databento.client import (DatabentoError, get_range, live_client,
                                       _key)
from open_predictor.forecast.auction.vendors.databento.historical import (cross_print_map, cross_prints,
                                           nasdaq_noii, nbbo_quotes,
                                           nyse_imbalance, snapshots)
from open_predictor.forecast.auction.vendors.databento.live import stream_imbalance
from open_predictor.forecast.auction.vendors.databento.schemas import (discover, normalize_imbalance,
                                        normalize_quote, normalize_trade)

__all__ = [
    "DatabentoError", "get_range", "live_client", "_key",
    "nasdaq_noii", "nyse_imbalance", "cross_prints", "nbbo_quotes",
    "snapshots", "cross_print_map",
    "normalize_imbalance", "normalize_trade", "normalize_quote", "discover",
    "stream_imbalance",
]
