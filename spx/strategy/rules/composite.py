"""The full designed strategy on backtest data (docs/approach.tex):
first-signal entry with the price gate, then checkpoint monitors that sell
and optionally FLIP the position when the live signal turns against it.
"""
from spx.strategy.data import LAST_MINUTE, market_p_at
from spx.strategy.rules import _base, _edge_side, _enter_taker, _resolve, _sig, _tok

CHECK_MINUTES = (8 * 60 + 35, 9 * 60)     # 8:35 release check, 9:00 refresh


def full_strategy(day, em, prm):
    """Entry: first hour in [h_start,h_end] the signal clears edge+gate AND
    the token costs <= px_max (expensive certainty is skipped: above ~0.90
    one quirk loss needs ~20 wins to repay). Monitors: at 8:35 and 9:00,
    if the traded side's live signal drops below exit_thr, sell; with
    flip=1 redeploy the proceeds into the other side when it qualifies."""
    h0, h1 = int(prm.get("h_start", 4)), int(prm.get("h_end", 9))
    px_max = prm.get("px_max", 0.90)
    entry = None
    for h in range(h0, h1 + 1):
        m = h * 60
        pm, pk = _sig(day, m, prm), market_p_at(day, m)
        if pm is None or pk is None:
            continue
        side = _edge_side(pm, pk, prm.get("edge", 0.05))
        if not side or _tok(pm, side) < prm.get("gate", 0.70):
            continue
        if _tok(pk, side) > px_max:
            continue
        entry = _enter_taker(day, em, side, m, _base(prm), prm)
        if entry is not None:
            break
    if entry is None:
        return []

    trades = [entry]
    pos = entry
    for m in CHECK_MINUTES:
        if pos is None or m <= pos["entry_min"]:
            continue
        pm, pk = _sig(day, m, prm), market_p_at(day, m)
        if pm is None or pk is None:
            continue
        if _tok(pm, pos["side"]) >= prm.get("exit_thr", 0.5):
            continue
        proceeds = em.sell_taker(day["date"], _tok(pk, pos["side"]),
                                 pos["shares"])
        pos.update(exit_min=m, proceeds=proceeds)
        pos = None
        if prm.get("flip", 1):
            other = _edge_side(pm, pk, prm.get("edge", 0.05))
            if other and _tok(pm, other) >= prm.get("gate", 0.70) \
                    and _tok(pk, other) <= px_max and proceeds >= 1.0:
                fill = em.buy_taker(day["date"], _tok(pk, other), proceeds)
                pos = {"side": other, "entry_min": m, "px": fill["px"],
                       "stake": fill["cost"], "shares": fill["shares"]}
                trades.append(pos)
    if pos is not None:
        pos.update(exit_min=LAST_MINUTE + 1,
                   proceeds=_resolve(day, pos["side"], pos["shares"]))
    return trades
