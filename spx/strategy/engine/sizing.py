"""Stake selection: chase the highest realizable multiplier.

On a thin ladder the payout multiplier decays with stake (impact walks the
book), so there is an optimal stake where marginal edge = marginal impact.
optimal_stake() maximizes expected profit E = p_true*shares - cost under the
execution model; rules use it via params {"sizing":"optimal"}.
"""
from spx.strategy.execution import ExecModel


def optimal_stake(p_true: float, p_tok: float, em: ExecModel, date: str,
                  lo: float = 10, hi: float = 500, step: float = 10) -> dict | None:
    """Best stake in [lo, hi], or None if no stake has positive EV."""
    best = None
    s = lo
    while s <= hi:
        f = em.buy_taker(date, p_tok, s)
        ev = p_true * f["shares"] - f["cost"]
        if best is None or ev > best["ev"]:
            best = {"stake": s, "ev": ev,
                    "multiplier": f["shares"] / f["cost"]}
        s += step
    return best if best and best["ev"] > 0 else None
