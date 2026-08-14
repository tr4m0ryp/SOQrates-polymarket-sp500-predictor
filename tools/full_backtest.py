"""Full-sequence Polymarket backtest: every tradeable day, no day selection.

Every previous evaluation in this project chose its days using the realised
outcome, twice, and both headline results were artifacts of that choice. This
runs the opposite way: the universe is every day with a resolved Polymarket
market, in date order, and the strategy decides for itself whether to act. A
day is never excluded, so there is nothing left to condition on the answer.

Emits one ledger row per day, traded or not:

    date, official gap, model p(up) per arm, fused p, market price,
    edge, decision, suppressing rule, stake, realised PnL, and the
    counterfactual PnL of the road not taken.

The counterfactual column is the point. A skipped day that would have lost is
the abstention rule earning its keep; a skipped day that would have won is
what the rule costs. Neither is visible in an equity curve, and scoring an
abstention as neutral makes the rule look free when it is not.

    python3 tools/full_backtest.py                 # both arms, full window
    python3 tools/full_backtest.py --arm futures   # futures only
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys

sys.path.insert(0, ".")

import spx  # noqa: E402  (loads .env)
from spx.config import CACHE, CONF_COMMIT, NY  # noqa: E402
from spx.backtest import dataset  # noqa: E402
from spx.data import weights as wmod, yahoo  # noqa: E402
from spx.model.core import ModelProd  # noqa: E402
from spx.pm.history import HIST_DIR  # noqa: E402

DECISION_HOUR = 9          # ET hour the FUTURES model is scored at
# The market price must be taken at the same moment as the newest information
# used. The replica reads auction snapshots up to 09:29:59, so quoting the
# 09:00 price against it is a 30-minute lookahead: we would be trading on
# information the book had not yet seen. Both arms therefore price at 09:29.
DECISION_MINUTE = 9 * 60 + 29
LIQ_FRAC = 0.01            # matches spx/strategy/engine/sim.py
HALF_SPREAD = 0.01         # matches spx/strategy/engine/execution.py
FEE = 0.04                 # taker fee

# Directional accuracy of the production model at the decision hour, measured
# on the TRAIN half only (2024-08..2025-08), which ends before this backtest
# window opens. Caps the optimism any single day's probability may express.
TRAIN_ACC = 0.94


def market_days() -> list[str]:
    """Every day with a resolved Polymarket market, in order. The universe."""
    return sorted(os.path.splitext(os.path.basename(p))[0]
                  for p in glob.glob(str(HIST_DIR) + "/*.json"))


def replica_p(date: str, closes: dict, W: dict, idx: list, spx_hist: dict):
    """Pre-open replica probability, or None when the day has no auction data.

    Hard 09:29:59 cutoff: a snapshot stamped at or after the bell cannot enter
    a prediction. That rule is what the 2026-08-13 lookahead defect required,
    and it is enforced here rather than trusted to the request window.
    """
    dpath = CACHE / "databento" / date / "preopen.json"
    if not dpath.exists() or date not in spx_hist:
        return None
    dg = json.loads(dpath.read_text())
    prev = idx[idx.index(date) - 1]
    num = cov = 0.0
    for t, px in dg.get("pred_preopen", {}).items():
        w = W.get(t)
        h = closes.get(t) or {}
        ks = [k for k in h if k <= prev]
        if not w or not ks:
            continue
        num += w * (px / h[max(ks)] - 1) * 100
        cov += w
    if cov <= 0:
        return None
    gap = num / cov
    # sigma from the measured pre-open reconstruction error, not the MC
    # posterior: 12.9 bp, the only figure that does not depend on day choice.
    import math
    return 0.5 * (1 + math.erf((gap / 0.129) / math.sqrt(2))), gap


def market_at(date: str, minute: int):
    """UP-token price at `minute` of the day, from the archived curve."""
    p = HIST_DIR / f"{date}.json"
    try:
        curve = json.loads(p.read_text())
    except (OSError, ValueError):
        return None, None
    meta = curve.get("meta") or {}
    vol = meta.get("volume")
    best = None
    for row in curve.get("history") or []:
        t, v = row.get("t"), row.get("p")
        if t is None or v is None:
            continue
        et = dt.datetime.fromtimestamp(int(t), tz=dt.timezone.utc).astimezone(NY)
        # the curve spans the prior noon to resolution; only same-day points
        # at or before the decision minute are knowable at decision time
        if et.strftime("%Y-%m-%d") != date:
            continue
        mm = et.hour * 60 + et.minute
        if mm <= minute and (best is None or mm > best[0]):
            best = (mm, float(v))
    return (best[1] if best else None), vol


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="both",
                    choices=("futures", "both"))
    ap.add_argument("--stake", type=float, default=50.0)
    args = ap.parse_args()

    days = market_days()
    print(f"universe: {len(days)} tradeable days, {days[0]} .. {days[-1]}")

    rows = dataset.load()
    train, _ = dataset.split(rows)
    model = ModelProd().fit(train)
    by_date = {r["date"]: r for r in rows}

    wrows = wmod.load()
    W = {r["ticker"]: r["weight"] for r in wrows}
    closes = json.loads((CACHE / "daily_closes.json").read_text())
    spx_hist = yahoo.daily_open_close("^GSPC", 400)
    idx = sorted(spx_hist)

    ledger, bank = [], 100.0
    for date in days:
        r = by_date.get(date)
        if r is None or DECISION_HOUR not in (r.get("es") or {}):
            ledger.append({"date": date, "decision": "no_model_data"})
            continue
        _mu, _s, p_fut = model.predict(r, DECISION_HOUR)
        rep = replica_p(date, closes, W, idx, spx_hist) if args.arm == "both" else None
        p_rep, gap = (rep if rep else (None, None))
        # equal-variance blend when both arms exist; no fitted weights
        p = p_fut if p_rep is None else 0.5 * (p_fut + p_rep)

        price, vol = market_at(date, DECISION_MINUTE)
        up = r["off"] > 0
        conf = max(p, 1 - p)
        row = {"date": date, "official_pct": r["off"], "up": up,
               "p_futures": p_fut, "p_replica": p_rep, "replica_gap": gap,
               "p_fused": p, "market": price, "volume": vol, "conf": conf}

        if price is None:
            row["decision"] = "no_market_price"
            ledger.append(row)
            continue

        side = "UP" if p > 0.5 else "DOWN"
        mkt_p = price if side == "UP" else 1 - price
        edge = (p if side == "UP" else 1 - p) - mkt_p
        row.update({"side": side, "edge": edge})

        # what a trade WOULD have returned, whether or not we take it
        cap = max(1.0, (vol or 0) * LIQ_FRAC)
        stake = min(args.stake, cap)
        fill = min(0.99, mkt_p + HALF_SPREAD)
        won = (side == "UP") == up
        gross = stake / fill if won else 0.0
        pnl_if_traded = (gross - stake) * (1 - FEE) if won else -stake
        row["counterfactual_pnl"] = pnl_if_traded
        row["liquidity_cap"] = cap

        # Expected value at the ACTUAL fill, not probability edge. A binary
        # bought at fill f pays (1/f - 1) per unit staked on a win and loses
        # the whole stake otherwise, so break-even accuracy is f + fee terms,
        # not the market's implied probability. At the median fill of 0.99
        # break-even is 99.0%, above any accuracy this model has ever
        # measured, so `edge > 0` waves through trades that are negative-EV
        # by arithmetic. This is derived from the payoff, not fitted to
        # results, so it is a mechanism fix under C9.
        # Use the model's TRAIN-half measured accuracy, not the live fused
        # probability, to decide whether the payoff can support a bet. The
        # fused p is uncalibrated (one arm is ~3x overconfident), and an EV
        # gate fed a miscalibrated p underperformed a cruder rule. Train-half
        # accuracy is a fixed number known before this window begins, so
        # using it introduces no dependence on the outcomes being scored.
        p_win = min(p if side == "UP" else 1 - p, TRAIN_ACC)
        ev = p_win * (1.0 / fill - 1.0) * (1 - FEE) - (1 - p_win)
        row["ev_per_unit"] = ev
        row["breakeven_p"] = 1.0 / (1.0 + (1.0 / fill - 1.0) * (1 - FEE))

        if conf < CONF_COMMIT:
            row.update({"decision": "abstain", "suppressed_by": "CONF_COMMIT",
                        "pnl": 0.0})
        elif edge <= 0:
            row.update({"decision": "abstain", "suppressed_by": "no_edge",
                        "pnl": 0.0})
        elif ev <= 0:
            row.update({"decision": "abstain", "suppressed_by": "negative_ev",
                        "pnl": 0.0})
        else:
            bank += pnl_if_traded
            row.update({"decision": "trade", "stake": stake,
                        "fill": fill, "won": won, "pnl": pnl_if_traded,
                        "bankroll": bank})
        ledger.append(row)

    traded = [r for r in ledger if r.get("decision") == "trade"]
    absts = [r for r in ledger if r.get("decision") == "abstain"]
    good_abst = [r for r in absts if r.get("counterfactual_pnl", 0) < 0]
    bad_abst = [r for r in absts if r.get("counterfactual_pnl", 0) > 0]

    print(f"\ndays in ledger      {len(ledger)}")
    print(f"  traded            {len(traded)}  "
          f"({sum(1 for r in traded if r['won'])}W-"
          f"{sum(1 for r in traded if not r['won'])}L)")
    print(f"  abstained         {len(absts)}")
    print(f"    correctly       {len(good_abst)}  "
          f"(loss avoided ${-sum(r['counterfactual_pnl'] for r in good_abst):,.2f})")
    print(f"    wrongly         {len(bad_abst)}  "
          f"(profit foregone ${sum(r['counterfactual_pnl'] for r in bad_abst):,.2f})")
    print(f"  no market/model   "
          f"{sum(1 for r in ledger if r.get('decision','').startswith('no_'))}")
    print(f"\nterminal bankroll   ${bank:,.2f} from $100.00")
    print(f"net abstention value ${-sum(r['counterfactual_pnl'] for r in good_abst) - sum(r['counterfactual_pnl'] for r in bad_abst):,.2f}")

    out = CACHE / f"full_backtest_{args.arm}.json"
    out.write_text(json.dumps(ledger, indent=1))
    print(f"artifact: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
