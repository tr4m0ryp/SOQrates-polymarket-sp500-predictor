"""Strategy families. Each takes (day, em, params) and returns a list of
closed trades: {side, entry_min, px, stake, shares, exit_min, proceeds}.
Curve prices are UP-token; DOWN token trades at 1-p. Stakes in USDC.
"""
from strategy.data import LAST_MINUTE, market_p_at, model_p_at
from strategy.sizing import optimal_stake

STAKE = 100.0


def _tok(p_up: float, side: str) -> float:
    return p_up if side == "up" else 1 - p_up


def _sig(day, minute, prm):
    return model_p_at(day, minute, prm.get("signal", "model"))


def _base(prm) -> float:
    """Per-trade stake: a bankroll fraction when compounding (bet_frac set
    and the engine injected _bankroll), else the flat $100 research stake."""
    if prm.get("bet_frac") and "_bankroll" in prm:
        return max(1.0, prm["_bankroll"] * prm["bet_frac"])
    return STAKE


def _resolve(day: dict, side: str, shares: float) -> float:
    won = day["outcome_up"] == (side == "up")
    return shares if won else 0.0


def _enter_taker(day, em, side, minute, stake, prm=None):
    """sizing='optimal' in prm overrides `stake` with the EV-maximizing
    (highest realizable multiplier) stake; skips the trade if no stake
    has positive EV under the execution model."""
    p = market_p_at(day, minute)
    if p is None:
        return None
    if prm and prm.get("sizing") == "optimal":
        p_sig = _sig(day, minute, prm)
        if p_sig is None:
            return None
        p_true = p_sig if side == "up" else 1 - p_sig
        best = optimal_stake(p_true, _tok(p, side), em, day["date"],
                             hi=min(prm.get("max_stake", 500),
                                    prm.get("_avail", 500)))
        if best is None:
            return None
        stake = best["stake"]
    if prm is not None and "_avail" in prm:       # no leverage
        stake = min(stake, prm["_avail"])
        if stake < 1.0:
            return None
    fill = em.buy_taker(day["date"], _tok(p, side), stake)
    if prm is not None and "_avail" in prm:
        prm["_avail"] -= fill["cost"]
    return {"side": side, "entry_min": minute, "px": fill["px"],
            "stake": fill["cost"], "shares": fill["shares"]}


def _edge_side(p_model, p_mkt, thr):
    if p_model - p_mkt >= thr:
        return "up"
    if p_mkt - p_model >= thr:
        return "down"
    return None


def hold(day, em, prm):
    """Enter once at hour `hour` on |model-market| >= edge, requiring the
    model's probability ON THE TRADED SIDE >= gate (an either-direction gate
    let anti-model longshots through); hold to resolution. maker=1 posts a
    resting limit `maker_disc` inside."""
    h = int(prm.get("hour", 7))
    minute = h * 60
    p_model, p_mkt = _sig(day, minute, prm), market_p_at(day, minute)
    if p_model is None or p_mkt is None:
        return []
    side = _edge_side(p_model, p_mkt, prm.get("edge", 0.05))
    if side is None:
        return []
    if _tok(p_model, side) < prm.get("gate", 0.65):
        return []
    if prm.get("maker"):
        limit = _tok(p_mkt, side) - prm.get("maker_disc", 0.01)
        fm = em.maker_fill(day["curve"], minute, limit, side,
                           volume=day.get("volume"))
        if fm is None:
            return []
        stake = min(_base(prm), prm.get("_avail", _base(prm)))
        shares = stake / limit
        t = {"side": side, "entry_min": fm, "px": limit,
             "stake": stake, "shares": shares}
    else:
        t = _enter_taker(day, em, side, minute, _base(prm), prm)
        if t is None:
            return []
    t.update(exit_min=LAST_MINUTE + 1, proceeds=_resolve(day, t["side"], t["shares"]))
    return [t]


def flow_flip(day, em, prm):
    """Ride the market favourite when the model agrees; from `flip_from` on,
    if the model diverges by >= flip_edge against the market, reverse."""
    m0 = int(prm.get("h0", 1)) * 60
    p_model, p_mkt = _sig(day, m0, prm), market_p_at(day, m0)
    if p_model is None or p_mkt is None:
        return []
    trades = []
    pos = None
    fav = "up" if p_mkt >= 0.5 else "down"
    agree = (p_model >= prm.get("agree_min", 0.55)) == (fav == "up")
    if agree and abs(p_mkt - 0.5) >= prm.get("min_lean", 0.05):
        pos = _enter_taker(day, em, fav, m0, _base(prm), prm)
    for minute in range(int(prm.get("flip_from", 7)) * 60, LAST_MINUTE + 1, 5):
        p_model, p_mkt = _sig(day, minute, prm), market_p_at(day, minute)
        if p_model is None or p_mkt is None:
            continue
        side = _edge_side(p_model, p_mkt, prm.get("flip_edge", 0.25))
        if side and (pos is None or side != pos["side"]):
            if pos is not None:
                pos.update(exit_min=minute, proceeds=em.sell_taker(
                    day["date"], _tok(p_mkt, pos["side"]), pos["shares"]))
                trades.append(pos)
            pos = _enter_taker(day, em, side, minute, _base(prm), prm)
            break
    if pos is not None:
        pos.update(exit_min=LAST_MINUTE + 1,
                   proceeds=_resolve(day, pos["side"], pos["shares"]))
        trades.append(pos)
    return trades


def takeprofit(day, em, prm):
    """`hold`, but sell into strength once the token trades >= tp."""
    trades = hold(day, em, {**prm, "maker": prm.get("maker", 0)})
    if not trades:
        return []
    t = trades[0]
    for minute in range(t["entry_min"] + 1, LAST_MINUTE + 1):
        p = market_p_at(day, minute)
        if p is None:
            continue
        if _tok(p, t["side"]) >= prm.get("tp", 0.95):
            t.update(exit_min=minute, proceeds=em.sell_taker(
                day["date"], _tok(p, t["side"]), t["shares"]))
            break
    return [t]


def longshot(day, em, prm):
    """Buy the cheap side when the model says it is not that unlikely."""
    for minute in range(int(prm.get("h_min", 0)) * 60, LAST_MINUTE + 1, 5):
        p_model, p_mkt = _sig(day, minute, prm), market_p_at(day, minute)
        if p_model is None or p_mkt is None:
            continue
        for side in ("up", "down"):
            p_tok = _tok(p_mkt, side)
            p_mod = p_model if side == "up" else 1 - p_model
            if p_tok <= prm.get("px_max", 0.15) and p_mod >= prm.get("p_min", 0.30):
                t = _enter_taker(day, em, side, minute, _base(prm), prm)
                if t is None:
                    return []
                t.update(exit_min=LAST_MINUTE + 1,
                         proceeds=_resolve(day, side, t["shares"]))
                return [t]
    return []


def scale_in(day, em, prm):
    """Clip in at each hour the edge persists; bail if the model flips."""
    hours = [int(h) for h in prm.get("hours", [0, 4, 7, 9])]
    trades, side = [], None
    for h in hours:
        minute = h * 60
        p_model, p_mkt = _sig(day, minute, prm), market_p_at(day, minute)
        if p_model is None or p_mkt is None:
            continue
        s = _edge_side(p_model, p_mkt, prm.get("edge", 0.05))
        if side and ((p_model >= 0.5) != (side == "up")):
            for t in trades:                    # model flipped: dump all
                t.update(exit_min=minute, proceeds=em.sell_taker(
                    day["date"], _tok(p_mkt, side), t["shares"]))
            return trades
        if s and (side is None or s == side) \
                and max(p_model, 1 - p_model) >= prm.get("gate", 0.65):
            t = _enter_taker(day, em, s, minute, _base(prm) / len(hours), prm)
            if t:
                side = s
                trades.append(t)
    for t in trades:
        t.update(exit_min=LAST_MINUTE + 1,
                 proceeds=_resolve(day, t["side"], t["shares"]))
    return trades


def convergence(day, em, prm):
    """Two-legged: our model finds the mispricing, the CROWD model predicts
    the market's own repricing path. Enter on edge at `hour`; exit into the
    forecast convergence instead of carrying resolution risk (hold_ok=1
    keeps the position when the target never prints)."""
    from strategy import crowd
    fitted = crowd.load()
    if not fitted:
        return []
    minute = int(prm.get("hour", 4)) * 60
    p_model, p_mkt = _sig(day, minute, prm), market_p_at(day, minute)
    if p_model is None or p_mkt is None:
        return []
    side = _edge_side(p_model, p_mkt, prm.get("edge", 0.05))
    if side is None or max(p_model, 1 - p_model) < prm.get("gate", 0.60):
        return []
    target_up = crowd.forecast(day, minute, int(prm.get("exit_h", 9)), fitted)
    if target_up is None:
        return []
    tok_target = _tok(target_up, side)
    if tok_target - _tok(p_mkt, side) < prm.get("min_move", 0.05):
        return []                       # forecast convergence won't pay costs
    t = _enter_taker(day, em, side, minute, _base(prm), prm)
    if t is None:
        return []
    margin = prm.get("margin", 0.02)
    for m in range(t["entry_min"] + 1, LAST_MINUTE + 1):
        p = market_p_at(day, m)
        if p is not None and _tok(p, side) >= tok_target - margin:
            t.update(exit_min=m, proceeds=em.sell_taker(
                day["date"], _tok(p, side), t["shares"]))
            return [t]
    if prm.get("hold_ok", 1):
        t.update(exit_min=LAST_MINUTE + 1,
                 proceeds=_resolve(day, side, t["shares"]))
    else:
        p = market_p_at(day, LAST_MINUTE)
        t.update(exit_min=LAST_MINUTE, proceeds=em.sell_taker(
            day["date"], _tok(p, side), t["shares"]) if p is not None else 0.0)
    return [t]


STRATEGIES = {"hold": hold, "flow_flip": flow_flip, "takeprofit": takeprofit,
              "longshot": longshot, "scale_in": scale_in,
              "convergence": convergence}
