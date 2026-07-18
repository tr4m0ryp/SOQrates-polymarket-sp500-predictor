"""Run a strategy over day records and score it."""
import math

from strategy.execution import ExecModel
from strategy.rules import STRATEGIES


def run(family: str, days: list[dict], params: dict, em: ExecModel | None = None):
    em = em or ExecModel(**{k: params[k] for k in
                            ("half_spread", "impact_per_100", "maker_eps")
                            if k in params})
    fn = STRATEGIES[family]
    day_pnl, all_trades = [], []
    for day in days:
        trades = fn(day, em, params)
        pnl = sum(t["proceeds"] - t["stake"] for t in trades)
        staked = sum(t["stake"] for t in trades)
        day_pnl.append({"date": day["date"], "pnl": round(pnl, 2),
                        "staked": round(staked, 2), "n": len(trades)})
        for t in trades:
            all_trades.append({**t, "date": day["date"],
                               "pnl": round(t["proceeds"] - t["stake"], 2)})
    return {"family": family, "params": params,
            "metrics": _metrics(day_pnl, all_trades),
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
    return {
        "n_days_traded": n, "n_trades": len(trades),
        "total_pnl": round(total, 2),
        "roi": round(total / staked, 4) if staked else 0.0,
        "win_rate": round(wins / len(trades), 3) if trades else 0.0,
        "avg_day_pnl": round(mean, 2),
        "sharpe_day": round(mean / sd, 3) if sd else 0.0,
        "max_drawdown": round(max_dd, 2),
    }
