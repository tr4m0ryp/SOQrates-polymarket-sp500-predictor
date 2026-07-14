"""Stage-3: reconstruct the official first index tick from auction data.

The official open is a continuous calculation where each constituent enters at
its last price — its opening auction print if it has crossed, else its prior
close (S&P DJI Equity Indices Policies & Practices). In weighted-gap space the
divisor cancels, so:

    replica_gap% = sum_i  w_i * gap_i * in_first_tick_i

where gap_i = (predicted_open_i / prior_close_i - 1) * 100 and
in_first_tick_i = 1 if the stock's auction prints at 9:30:00 (Nasdaq cross;
NYSE names only when the imbalance feed implies an instant open), else 0.
"""
from dataclasses import dataclass


@dataclass
class Constituent:
    ticker: str
    weight: float            # index weight, %
    prior_close: float
    pred_open: float | None  # NOII near price / NYSE indicative match price
    in_first_tick: bool      # will it print at 9:30:00?


def first_tick_gap(constituents: list[Constituent]) -> dict:
    """Predicted official-open gap (%) plus coverage diagnostics."""
    total_w = sum(c.weight for c in constituents)
    live_w = 0.0
    gap = 0.0
    for c in constituents:
        if not (c.in_first_tick and c.pred_open and c.prior_close):
            continue    # stale names contribute exactly 0 to the gap
        live_w += c.weight
        gap += c.weight * (c.pred_open / c.prior_close - 1) * 100
    return {
        "replica_gap_pct": gap / total_w * 100 / 100 if total_w else 0.0,
        "live_weight_pct": live_w / total_w * 100 if total_w else 0.0,
        "n_live": sum(1 for c in constituents if c.in_first_tick),
        "n_total": len(constituents),
    }


def replica_sigma(live_weight_pct: float, per_name_sigma: float = 0.05) -> float:
    """Crude uncertainty: stale weight contributes zero-variance (it IS prior
    close); live names carry NOII-vs-print deviation, to be measured from
    Databento history. Until measured, per_name_sigma is a placeholder prior."""
    return per_name_sigma * (live_weight_pct / 100) ** 0.5
