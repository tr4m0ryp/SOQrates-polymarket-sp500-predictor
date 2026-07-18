"""Execution realism: fees (Fee Structure V2), spread, impact, maker fills.

Prices in the curve are for the UP token; DOWN trades use 1-p. All entries
model verified facts from the 2026-07-18 microstructure research: taker fee
C*rate*p*(1-p) since 2026-03-30 (Finance rate 0.04), makers pay zero, market
orders walk the book (impact grows with stake on a thin ladder).
"""
FEE_START = "2026-03-30"
FEE_RATE = 0.04


def taker_fee(date: str, price: float, shares: float) -> float:
    if date < FEE_START:
        return 0.0
    return shares * FEE_RATE * price * (1 - price)


class ExecModel:
    """half_spread and impact_per_100 (price impact per $100 stake) are the
    stress knobs; defaults are deliberately pessimistic for a thin book."""

    def __init__(self, half_spread=0.01, impact_per_100=0.005, maker_eps=0.01):
        self.half_spread = half_spread
        self.impact_per_100 = impact_per_100
        self.maker_eps = maker_eps

    def _buy_px(self, p: float, stake: float) -> float:
        return min(0.999, p + self.half_spread + self.impact_per_100 * stake / 100)

    def _sell_px(self, p: float, stake: float) -> float:
        return max(0.001, p - self.half_spread - self.impact_per_100 * stake / 100)

    def buy_taker(self, date: str, p_token: float, stake: float) -> dict:
        """Spend `stake` USDC crossing the spread; returns shares + cost."""
        px = self._buy_px(p_token, stake)
        shares = stake / px
        return {"shares": shares, "px": px,
                "cost": stake + taker_fee(date, px, shares)}

    def sell_taker(self, date: str, p_token: float, shares: float) -> float:
        """Proceeds of selling `shares` crossing the spread."""
        px = self._sell_px(p_token, shares * p_token)
        return shares * px - taker_fee(date, px, shares)

    def maker_fill(self, curve: list, minute: int, limit: float,
                   side: str = "up") -> int | None:
        """First minute >= `minute` where a resting buy of `side`'s token at
        `limit` fills: the print must trade through the limit by maker_eps.
        Curve prices are UP-token; a DOWN buy at L needs p_up >= 1-L+eps."""
        for m, p in curve:
            p_tok = p if side == "up" else 1 - p
            if m >= minute and p_tok <= limit - self.maker_eps:
                return m
        return None
