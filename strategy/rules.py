"""Strategy families. Each takes (day, em, params) and returns a list of
closed trades: {side, entry_min, px, stake, shares, exit_min, proceeds}.
Curve prices are UP-token; DOWN token trades at 1-p. Stakes in USDC.
"""
from strategy.data import LAST_MINUTE, market_p_at, model_p_at

STAKE = 100.0


def _tok(p_up: float, side: str) -> float:
    return p_up if side == "up" else 1 - p_up


def _resolve(day: dict, side: str, shares: float) -> float:
    won = day["outcome_up"] == (side == "up")
    return shares if won else 0.0


def _enter_taker(day, em, side, minute, stake):
    p = market_p_at(day, minute)
    if p is None:
        return None
    fill = em.buy_taker(day["date"], _tok(p, side), stake)
    return {"side": side, "entry_min": minute, "px": fill["px"],
            "stake": fill["cost"], "shares": fill["shares"]}


def _edge_side(p_model, p_mkt, thr):
    if p_model - p_mkt >= thr:
        return "up"
    if p_mkt - p_model >= thr:
        return "down"
    return None


def hold(day, em, prm):
    """Enter once at hour `hour` on |model-market| >= edge with conf >= gate;
    hold to resolution. maker=1 posts a resting limit `maker_disc` inside."""
    h = int(prm.get("hour", 7))
    minute = h * 60
    p_model, p_mkt = model_p_at(day, minute), market_p_at(day, minute)
    if p_model is None or p_mkt is None:
        return []
    if max(p_model, 1 - p_model) < prm.get("gate", 0.65):
        return []
    side = _edge_side(p_model, p_mkt, prm.get("edge", 0.05))
    if side is None:
        return []
    if prm.get("maker"):
        limit = _tok(p_mkt, side) - prm.get("maker_disc", 0.01)
        fm = em.maker_fill(day["curve"], minute, limit, side)
        if fm is None:
            return []
        shares = STAKE / limit
        t = {"side": side, "entry_min": fm, "px": limit,
             "stake": STAKE, "shares": shares}
    else:
        t = _enter_taker(day, em, side, minute, STAKE)
        if t is None:
            return []
    t.update(exit_min=LAST_MINUTE + 1, proceeds=_resolve(day, t["side"], t["shares"]))
    return [t]


def flow_flip(day, em, prm):
    """Ride the market favourite when the model agrees; from `flip_from` on,
    if the model diverges by >= flip_edge against the market, reverse."""
    m0 = int(prm.get("h0", 1)) * 60
    p_model, p_mkt = model_p_at(day, m0), market_p_at(day, m0)
    if p_model is None or p_mkt is None:
        return []
    trades = []
    pos = None
    fav = "up" if p_mkt >= 0.5 else "down"
    agree = (p_model >= prm.get("agree_min", 0.55)) == (fav == "up")
    if agree and abs(p_mkt - 0.5) >= prm.get("min_lean", 0.05):
        pos = _enter_taker(day, em, fav, m0, STAKE)
    for minute in range(int(prm.get("flip_from", 7)) * 60, LAST_MINUTE + 1, 5):
        p_model, p_mkt = model_p_at(day, minute), market_p_at(day, minute)
        if p_model is None or p_mkt is None:
            continue
        side = _edge_side(p_model, p_mkt, prm.get("flip_edge", 0.25))
        if side and (pos is None or side != pos["side"]):
            if pos is not None:
                pos.update(exit_min=minute, proceeds=em.sell_taker(
                    day["date"], _tok(p_mkt, pos["side"]), pos["shares"]))
                trades.append(pos)
            pos = _enter_taker(day, em, side, minute, STAKE)
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
        p_model, p_mkt = model_p_at(day, minute), market_p_at(day, minute)
        if p_model is None or p_mkt is None:
            continue
        for side in ("up", "down"):
            p_tok = _tok(p_mkt, side)
            p_mod = p_model if side == "up" else 1 - p_model
            if p_tok <= prm.get("px_max", 0.15) and p_mod >= prm.get("p_min", 0.30):
                t = _enter_taker(day, em, side, minute, STAKE)
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
        p_model, p_mkt = model_p_at(day, minute), market_p_at(day, minute)
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
            t = _enter_taker(day, em, s, minute, STAKE / len(hours))
            if t:
                side = s
                trades.append(t)
    for t in trades:
        t.update(exit_min=LAST_MINUTE + 1,
                 proceeds=_resolve(day, t["side"], t["shares"]))
    return trades


STRATEGIES = {"hold": hold, "flow_flip": flow_flip, "takeprofit": takeprofit,
              "longshot": longshot, "scale_in": scale_in}
