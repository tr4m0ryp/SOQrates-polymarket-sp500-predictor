"""Stage-3 pipeline: auction snapshots -> first-tick replica -> fused P(up).

One code path for both uses:
  backtest : snapshots from an LSEG Tick History pull (lseg_parse.snapshots)
  live     : snapshots from NCDS/dxFeed + Massive normalize() dicts

Nasdaq names enter at their indicative price (they print at 9:30:00);
NYSE names are carried at prior close unless their imbalance feed shows a
credible instant open - the measured NYSE indicative noise (~29bp at
9:29:50 vs ~0-5bp for Nasdaq NOII) says: trust Nasdaq, default-stale NYSE.
"""
from data import weights as wmod
from model import fusion
from replica.assembly import Constituent, first_tick_gap, replica_sigma

NYSE_TRUST_DEFAULT = False       # flip per-name once live data proves timing


def build_constituents(pred_opens: dict[str, float],
                       prior_closes: dict[str, float],
                       trust_nyse: bool = NYSE_TRUST_DEFAULT) -> list[Constituent]:
    out = []
    for w in wmod.load():
        t = w["ticker"]
        pc = prior_closes.get(t)
        is_nas = w["exchange"] == "NASDAQ"
        in_tick = is_nas or trust_nyse
        out.append(Constituent(
            ticker=t, weight=w["weight"], prior_close=pc or 0.0,
            pred_open=pred_opens.get(t) if in_tick else None,
            in_first_tick=in_tick and t in pred_opens and pc is not None))
    return out


def replica_estimate(pred_opens: dict[str, float],
                     prior_closes: dict[str, float]) -> dict:
    cons = build_constituents(pred_opens, prior_closes)
    res = first_tick_gap(cons)
    res["sigma_pct"] = replica_sigma(res["live_weight_pct"])
    return res


def fused_p_up(replica: dict, futures_mu: float, futures_sigma: float) -> dict:
    """Inverse-variance blend of the auction replica with the futures view."""
    mu, sigma = fusion.combine([
        (replica["replica_gap_pct"], max(replica["sigma_pct"], 1e-4)),
        (futures_mu, futures_sigma),
    ])
    return {"mu": mu, "sigma": sigma, "p_up": fusion.prob_up(mu, sigma),
            "replica_weight_pct": replica["live_weight_pct"]}
