"""Day-resampled bootstrap for bankroll trajectories (stdlib only).

Extracts stake-independent per-day contracts (entry side, token price,
outcome, volume) from one canonical sim run per strategy config, then
replays the staking rule over day sequences resampled with replacement —
sequence risk and compounding included. Identity replay is asserted against
sim.run to the cent before any resampling. matplotlib stays in plot.py.
"""
import json
import random

from open_predictor.config import CACHE
from open_predictor.trading.strategy import data
from open_predictor.trading.strategy.engine import sim
from open_predictor.trading.strategy.data import market_p_at
from open_predictor.trading.strategy.engine.execution import ExecModel
from open_predictor.trading.strategy.rules.base import _tok

OUT_FILE = CACHE / "bootstrap_bands.json"
B = 10_000
SEED = 20260719
EXEC = {"half_spread": 0.01, "impact_per_100": 0.001}

# (family, rule params, staking rule) — staking: ("flat", $) or ("frac", f).
CONFIGS = {
    "first_signal_flat50": (
        "first_signal",
        {"h_start": 4, "h_end": 9, "edge": 0.05, "gate": 0.7,
         "signal": "model", "stake_abs": 50, **EXEC},
        ("flat", 50.0)),
    "hold_h4_frac10": (
        "hold",
        {"hour": 4, "edge": 0.05, "gate": 0.6, "signal": "model",
         "maker": 0, "bet_frac": 0.1, **EXEC},
        ("frac", 0.10)),
    "hold_h4_flat50": (
        "hold",
        {"hour": 4, "edge": 0.05, "gate": 0.6, "signal": "model",
         "stake_abs": 50, **EXEC},
        ("flat", 50.0)),
}


def _contracts(family: str, params: dict, test: list[dict]) -> list[dict | None]:
    """One entry per test day; None = the rule does not trade that day.
    Entry decisions in `hold`/`first_signal` never depend on the stake, so
    side/minute/price extracted at one stake hold for every staking rule."""
    run = sim.run(family, test, dict(params))
    by_date = {}
    for t in run["trades"]:
        by_date.setdefault(t["date"], t)          # these rules trade <= 1/day
    out = []
    for day in test:
        t = by_date.get(day["date"])
        if t is None:
            out.append(None)
            continue
        p = market_p_at(day, t["entry_min"])
        out.append({"date": day["date"], "volume": day.get("volume") or 0.0,
                    "p_tok": _tok(p, t["side"]),
                    "win": day["outcome_up"] == (t["side"] == "up")})
    return out


def _replay(seq: list[dict | None], stake_rule, em: ExecModel) -> list[float]:
    """Bankroll after each day of `seq`, mirroring sim.run semantics:
    volume gate, liquidity cap, no leverage, ruin below $1."""
    kind, x = stake_rule
    bank = 100.0
    path = []
    for c in seq:
        if c is not None and bank >= 1.0 and c["volume"] >= sim.MIN_VOLUME:
            avail = min(c["volume"] * sim.LIQ_FRAC, bank)
            stake = min(max(1.0, x if kind == "flat" else bank * x), avail)
            if stake >= 1.0:
                fill = em.buy_taker(c["date"], c["p_tok"], stake)
                bank += (fill["shares"] if c["win"] else 0.0) - fill["cost"]
        path.append(bank)
    return path


def _pctl(sorted_vals: list[float], q: float) -> float:
    i = (len(sorted_vals) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (i - lo)


def run(n_resamples: int = B, seed: int = SEED) -> dict:
    days = data.build()
    _, test = data.split(days)
    em = ExecModel(**EXEC)
    rng = random.Random(seed)
    n = len(test)
    out = {"B": n_resamples, "seed": seed, "n_days": n,
           "dates": [d["date"] for d in test], "strategies": {}}

    for name, (family, params, stake_rule) in CONFIGS.items():
        cons = _contracts(family, params, test)
        actual = _replay(cons, stake_rule, em)
        ref = sim.run(family, test, dict(params))["metrics"]["final_bankroll"]
        assert abs(actual[-1] - ref) < 0.01, (name, actual[-1], ref)

        paths = [_replay([cons[rng.randrange(n)] for _ in range(n)],
                         stake_rule, em) for _ in range(n_resamples)]
        ends = sorted(p[-1] for p in paths)
        band = {k: [] for k in ("p5", "p50", "p95")}
        for t in range(n):
            col = sorted(p[t] for p in paths)
            for k, q in (("p5", .05), ("p50", .50), ("p95", .95)):
                band[k].append(round(_pctl(col, q), 2))
        out["strategies"][name] = {
            "family": family, "params": params, "stake_rule": list(stake_rule),
            "actual_end": round(actual[-1], 2),
            "actual_path": [round(v, 2) for v in actual],
            "end": {k: round(_pctl(ends, q), 2)
                    for k, q in (("p5", .05), ("p50", .50), ("p95", .95))},
            "band": band,
        }
    OUT_FILE.write_text(json.dumps(out))
    return out


def main():
    res = run()
    for name, s in res["strategies"].items():
        e = s["end"]
        print(f"{name}: actual ${s['actual_end']:.2f} | bootstrap end "
              f"5th ${e['p5']:.2f} / median ${e['p50']:.2f} / 95th ${e['p95']:.2f}")
    print(f"bands -> {OUT_FILE}")
