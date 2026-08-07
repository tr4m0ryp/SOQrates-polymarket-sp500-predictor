"""Run a strategy over day records and score it.

Two modes: flat $100 research stakes (default), or bankroll compounding when
params carry bet_frac — the engine then starts at start_bankroll (default
$100), stakes bet_frac of the live bankroll per day (never leveraged), and
reports terminal wealth over the period.

Liquidity realism: the price curve is CLOB midpoints, not prints, so days
where the market barely traded would give purely fictional fills. Days with
meta volume below params['min_volume'] (default MIN_VOLUME) are skipped, and
the per-day stake is capped at params['liq_frac'] (default LIQ_FRAC) of the
day's real traded volume.
"""
import math

from spx.strategy.execution import ExecModel
from spx.strategy.rules import STRATEGIES

START_BANKROLL = 100.0
MIN_VOLUME = 1000.0     # USDC; below this the market never really traded and
                        # midpoint quotes have no prints behind them
LIQ_FRAC = 0.01         # per-day stake cap as a fraction of real traded volume


def run(family: str, days: list[dict], params: dict, em: ExecModel | None = None):
    em = em or ExecModel(**{k: params[k] for k in
                            ("half_spread", "impact_per_100", "maker_eps")
                            if k in params})
    fn = STRATEGIES[family]
    compound = bool(params.get("bet_frac") or params.get("stake_abs"))
    bankroll = params.get("start_bankroll", START_BANKROLL)
    min_vol = params.get("min_volume", MIN_VOLUME)
    liq_frac = params.get("liq_frac", LIQ_FRAC)
    day_pnl, all_trades = [], []
    for day in days:
        vol = day.get("volume") or 0.0
        if vol < min_vol:
            continue                    # fills on no-volume days are fiction
        prm = dict(params)
        prm["_avail"] = vol * liq_frac                  # liquidity stake cap
        if compound:
            if bankroll < 1.0:
                break                                   # ruin
            prm["_bankroll"] = bankroll
            prm["_avail"] = min(prm["_avail"], bankroll)
        trades = fn(day, em, prm)
        pnl = sum(t["proceeds"] - t["stake"] for t in trades)
        staked = sum(t["stake"] for t in trades)
        if compound:
            bankroll += pnl
        day_pnl.append({"date": day["date"], "pnl": round(pnl, 2),
                        "staked": round(staked, 2), "n": len(trades),
                        **({"bankroll": round(bankroll, 2)} if compound else {})})
        for t in trades:
            all_trades.append({**t, "date": day["date"],
                               "pnl": round(t["proceeds"] - t["stake"], 2)})
    m = _metrics(day_pnl, all_trades)
    if compound:
        m["final_bankroll"] = round(bankroll, 2)
        m["min_bankroll"] = round(min((d["bankroll"] for d in day_pnl
                                       if "bankroll" in d), default=bankroll), 2)
    return {"family": family, "params": params, "metrics": m,
            "days": day_pnl, "trades": all_trades}


def _metrics(day_pnl, trades):
    pnls = [d["pnl"] for d in day_pnl if d["n"]]
    total = sum(pnls)
    staked = sum(d["staked"] for d in day_pnl)
    wins = sum(1 for t in trades if t["pnl"] > 0)
    cum = peak = 0.0
    max_dd = 0.0
    for d in day_pnl:
        cum += d["pnl"]
        peak = max(peak, cum)
        max_dd = max(max_dd, peak - cum)
    n = len(pnls)
    mean = total / n if n else 0.0
    sd = math.sqrt(sum((p - mean) ** 2 for p in pnls) / n) if n > 1 else 0.0
    mults = [t["shares"] / t["stake"] for t in trades if t["stake"]]
    return {
        "n_days_traded": n, "n_trades": len(trades),
        "total_pnl": round(total, 2),
        "roi": round(total / staked, 4) if staked else 0.0,
        "win_rate": round(wins / len(trades), 3) if trades else 0.0,
        "avg_multiplier": round(sum(mults) / len(mults), 2) if mults else 0.0,
        "avg_day_pnl": round(mean, 2),
        "sharpe_day": round(mean / sd, 3) if sd else 0.0,
        "max_drawdown": round(max_dd, 2),
    }
