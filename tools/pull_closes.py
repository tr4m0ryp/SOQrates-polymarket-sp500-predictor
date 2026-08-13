"""Split-correct daily closes for every S&P constituent, from Databento.

The replica gap is `pred_open / prior_close - 1`, so the prior close must
share a price basis with the auction prices, which are raw and
contemporaneous. Two wrong denominators have already been used here:

  Yahoo daily history  - SPLIT-ADJUSTED, so wrong by the cumulative split
                         factor for any name that split after the date
                         (NFLX +899%, BKNG +2383% on 2025-09-12)
  auction `ref_price`  - the auction's LIVE reference, which moves during
                         the auction and is not the previous close; it drags
                         an oracle reconstruction from corr +0.981 to +0.415

Databento `ohlcv-1d` gives the raw close as printed on the day, which is the
correct basis. A full year for all ~500 names costs about $0.19.

    python3 tools/pull_closes.py --start 2025-09-01 --end 2026-08-13
"""
import argparse
import json
import sys

sys.path.insert(0, ".")

import spx  # noqa: E402  (loads .env)
from spx.config import CACHE  # noqa: E402
from spx.data import weights as wmod  # noqa: E402
from spx.replica.vendors.databento import budget  # noqa: E402
from spx.replica.vendors.databento.client import get_range  # noqa: E402
from spx.replica.vendors.databento.historical import (NASDAQ_DATASET,  # noqa: E402
                                                      NYSE_DATASET)
from spx.replica.vendors.databento.schemas import _field, _px, _symbol  # noqa: E402

OUT = CACHE / "daily_closes.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-09-01")
    ap.add_argument("--end", default="2026-08-13")
    args = ap.parse_args()

    rows = wmod.load()
    legs = [(NASDAQ_DATASET, [r["ticker"] for r in rows
                              if r["exchange"] == "NASDAQ"], "NASDAQ"),
            (NYSE_DATASET, [r["ticker"] for r in rows
                            if r["exchange"] != "NASDAQ"], "NYSE")]

    start = f"{args.start}T00:00:00Z"
    end = f"{args.end}T00:00:00Z"
    out: dict[str, dict[str, float]] = {}
    for dataset, syms, label in legs:
        cost = budget.check_and_reserve(f"closes/{label}", dataset, "ohlcv-1d",
                                        syms, start, end)
        recs = get_range(dataset, "ohlcv-1d", syms, start, end)
        n = 0
        for r in recs:
            sym = _symbol(r, None)
            close = _px(_field(r, "close"))
            ts = _field(r, "ts_event")
            if not sym or close is None or ts is None:
                continue
            # ohlcv-1d stamps the session; take the UTC date as the key
            import datetime as dt
            day = dt.datetime.fromtimestamp(
                int(ts) / 1e9, tz=dt.timezone.utc).strftime("%Y-%m-%d")
            out.setdefault(sym, {})[day] = close
            n += 1
        print(f"{label}: {len(recs)} records, {n} usable, ${cost:.4f}")

    OUT.write_text(json.dumps(out))
    print(f"\n{len(out)} tickers written to {OUT}")
    print(f"budget: ${budget.spent_usd():.4f} of ${budget.cap_usd():.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
