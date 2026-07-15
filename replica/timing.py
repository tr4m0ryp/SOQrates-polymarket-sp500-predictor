"""Per-stock print-timing model: when does each stock's opening print land?

p_live is the CDF of the print-delay distribution evaluated at the photo
moment. Until LSEG print timestamps exist, venue priors apply (Nasdaq cross
fires at 9:30:00; NYSE straggles). fit_from_prints() replaces the priors
with per-stock empirical delay distributions, and condition_not_printed()
gives the Bayes update for the filtering step ("silent this late -> slower
than usual today").
"""
import json

from config import CACHE

_STORE = CACHE / "print_delays.json"
VENUE_PRIOR = {"NASDAQ": 0.97, "NYSE": 0.15}   # P(printed by first tick)


class TimingModel:
    def __init__(self, delays: dict[str, list[float]] | None = None,
                 venues: dict[str, str] | None = None):
        self.delays = delays or {}          # ticker -> print delays (s after 9:30)
        self.venues = venues or {}

    @classmethod
    def load(cls, venues: dict[str, str] | None = None) -> "TimingModel":
        delays = {}
        if _STORE.exists():
            delays = json.loads(_STORE.read_text())
        return cls(delays, venues)

    def fit_from_prints(self, prints_by_day: dict[str, dict[str, float]]):
        """prints_by_day: {date: {ticker: delay_seconds_after_930}} from the
        LSEG cross-trade timestamps. Persists per-ticker delay samples."""
        acc: dict[str, list[float]] = {}
        for day in prints_by_day.values():
            for ticker, delay in day.items():
                acc.setdefault(ticker, []).append(float(delay))
        self.delays = {t: sorted(v) for t, v in acc.items()}
        _STORE.write_text(json.dumps(self.delays))
        return self

    def p_live(self, ticker: str, photo_s: float = 1.0) -> float:
        d = self.delays.get(ticker)
        if d:
            hit = sum(1 for x in d if x <= photo_s)
            return (hit + 0.5) / (len(d) + 1)          # Laplace-smoothed
        return VENUE_PRIOR.get(self.venues.get(ticker, "NYSE"), 0.15)

    def condition_not_printed(self, ticker: str, elapsed_s: float,
                              photo_s: float = 1.0) -> float:
        """P(prints by photo | hasn't printed after elapsed_s). Only
        meaningful pre-photo when the photo moment itself is later than
        `elapsed_s` (e.g. index calc interval jitter)."""
        d = self.delays.get(ticker)
        if not d:
            base = self.p_live(ticker, photo_s)
            return base * 0.3                          # crude prior decay
        later = [x for x in d if x > elapsed_s]
        if not later:
            return 0.05
        hit = sum(1 for x in later if x <= photo_s)
        return (hit + 0.5) / (len(later) + 1)
