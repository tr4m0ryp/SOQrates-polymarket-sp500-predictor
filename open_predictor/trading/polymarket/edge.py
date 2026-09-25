"""Model-vs-market edge calculation for the Polymarket SPX-open market."""
from open_predictor.config import CONF_COMMIT

EDGE_THRESHOLD = 0.05   # minimum price divergence worth trading


def assess(p_model: float, p_market: float | None) -> dict:
    conf = max(p_model, 1 - p_model)
    out = {"p_model": round(p_model, 3), "p_market": p_market,
           "confidence": round(conf, 3), "action": "no-bet", "edge": None}
    if p_market is None:
        out["action"] = "no market price"
        return out
    edge_up = p_model - p_market
    edge_dn = p_market - p_model
    if conf < CONF_COMMIT:
        out["action"] = "coin-flip zone - stand down (or quote both sides)"
    elif edge_up >= EDGE_THRESHOLD:
        out.update(action=f"BUY UP @ {p_market:.2f}", edge=round(edge_up, 3))
    elif edge_dn >= EDGE_THRESHOLD:
        out.update(action=f"BUY DOWN @ {1 - p_market:.2f}", edge=round(edge_dn, 3))
    else:
        out["action"] = "priced fairly - no edge"
    return out
