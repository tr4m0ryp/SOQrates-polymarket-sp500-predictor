"""Measure NOII near-price vs actual opening print deviation.

This is THE number that sets the auction replica's accuracy ceiling: how far
the exchange's own indicative price at 9:28/9:29 sits from the print at
9:30:00. Run on free ITCH sample files (no vendor account needed).
"""
import math

from open_predictor.forecast.auction.vendors.itch.parse import SymbolAuction

_NS_H = 3_600_000_000_000
CHECKPOINTS = {          # ns since midnight ET
    "9:25": 9 * _NS_H + 25 * 60_000_000_000,
    "9:28": 9 * _NS_H + 28 * 60_000_000_000,
    "9:29": 9 * _NS_H + 29 * 60_000_000_000,
    "9:29:50": 9 * _NS_H + 29 * 60_000_000_000 + 50_000_000_000,
}


def near_at(rec: SymbolAuction, ts_ns: int) -> float | None:
    best = None
    for snap in rec.noii:
        if snap.ts_ns <= ts_ns and snap.near > 0:
            best = snap.near
        elif snap.ts_ns > ts_ns:
            break
    return best


def symbol_deviation(rec: SymbolAuction) -> dict | None:
    """bps deviation of the NOII near price vs the actual cross print."""
    if not rec.cross_price or not rec.noii:
        return None
    out = {"ticker": rec.ticker, "cross": rec.cross_price,
           "cross_shares": rec.cross_shares}
    for name, ts in CHECKPOINTS.items():
        near = near_at(rec, ts)
        out[name] = ((near / rec.cross_price - 1) * 1e4) if near else None
    return out


def aggregate(records: dict[str, SymbolAuction],
              weights: dict[str, float] | None = None) -> dict:
    """Per-checkpoint stats across symbols; weighted index-level error too."""
    rows = [d for d in (symbol_deviation(r) for r in records.values()) if d]
    stats = {}
    for cp in CHECKPOINTS:
        devs = [r[cp] for r in rows if r[cp] is not None]
        if not devs:
            continue
        adevs = sorted(abs(d) for d in devs)
        stats[cp] = {
            "n": len(devs),
            "median_abs_bps": adevs[len(adevs) // 2],
            "mean_abs_bps": sum(adevs) / len(adevs),
            "p90_abs_bps": adevs[int(0.9 * len(adevs))],
        }
        if weights:
            wsum = werr = 0.0
            for r in rows:
                w = weights.get(r["ticker"])
                if w and r[cp] is not None:
                    wsum += w
                    werr += w * r[cp]          # signed -> index-level error
            if wsum:
                stats[cp]["index_signed_bps"] = werr / 100  # per 100% weight
                stats[cp]["covered_weight_pct"] = wsum
    return {"per_symbol": rows, "stats": stats}
