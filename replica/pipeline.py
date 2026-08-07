"""Stage-3 pipeline: auction snapshots -> first-tick replica -> fused P(up).

One code path for both uses:
  backtest : snapshots from an LSEG Tick History pull (replica.lseg.parse.snapshots)
  live     : snapshots from NCDS/dxFeed + Massive normalize() dicts

Nasdaq names enter at their indicative price (they print at 9:30:00);
NYSE names are carried at prior close unless their imbalance feed shows a
credible instant open - the measured NYSE indicative noise (~29bp at
9:29:50 vs ~0-5bp for Nasdaq NOII) says: trust Nasdaq, default-stale NYSE.
"""
from data import weights as wmod
from model import fusion
from replica.assembly import Constituent, first_tick_gap, replica_sigma
from replica.montecarlo import McConstituent, simulate
from replica.timing import TimingModel

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


PREVIEW_SIGMA = {"NASDAQ": 0.05, "NYSE": 0.30}   # measured NOII / NYSE noise, %


def replica_distribution(pred_opens: dict[str, float],
                         prior_closes: dict[str, float],
                         timing: TimingModel | None = None) -> dict:
    """Distributional assembly: full photo-gap distribution + pivotal names.

    Uses the timing model's per-stock p_live when fitted (LSEG print
    timestamps), venue priors otherwise. Supersedes replica_estimate for
    decision-making; the (mean, sigma, p_up) feed fusion directly.
    """
    rows = wmod.load()
    venues = {r["ticker"]: r["exchange"] for r in rows}
    timing = timing or TimingModel.load(venues)
    timing.venues = timing.venues or venues
    cons = []
    for r in rows:
        t = r["ticker"]
        pc = prior_closes.get(t)
        po = pred_opens.get(t)
        gap = ((po / pc - 1) * 100) if (po and pc) else 0.0
        p = timing.p_live(t) if (po and pc) else 0.0
        cons.append(McConstituent(t, r["weight"], gap, p,
                                  PREVIEW_SIGMA.get(r["exchange"], 0.30)))
    return simulate(cons)
