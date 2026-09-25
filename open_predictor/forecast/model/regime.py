"""Regime scaling: EWMA of overnight gap^2 + prior-day RV (+ optional VIX1D)."""
import math

from open_predictor.config import EWMA_LAMBDA


def annotate_ewma(rows: list[dict]) -> list[dict]:
    """Attach ewma_prev (no lookahead: uses gaps of PRIOR days only).

    Rows must be chronological with es[9] present. The first row (no prior
    EWMA) is dropped.
    """
    ew = None
    for r in rows:
        g9 = r["es"].get(9) or r["es"][max(r["es"])]
        r["ewma_prev"] = ew
        ew = g9 * g9 if ew is None else EWMA_LAMBDA * ew + (1 - EWMA_LAMBDA) * g9 * g9
    return [r for r in rows if r["ewma_prev"] is not None]


class RegimeScaler:
    """sigma multiplier m(day); normalization means fitted on train only."""

    def __init__(self, use_vix: bool = False):
        self.use_vix = use_vix
        self.means: dict[str, float] = {}

    def fit(self, train: list[dict]) -> "RegimeScaler":
        def mean(key):
            vals = [r[key] for r in train if r.get(key)]
            return sum(vals) / len(vals) if vals else 1.0
        self.means = {"ewma": mean("ewma_prev"), "rv": mean("rv_prev")}
        if self.use_vix:
            self.means["vix"] = mean("vix1d_prev")
        return self

    def mult(self, row: dict) -> float:
        ew = row["ewma_prev"] / self.means["ewma"]
        rv = (row["rv_prev"] / self.means["rv"]) if self.means.get("rv") else 1.0
        if self.use_vix and row.get("vix1d_prev") and self.means.get("vix"):
            vx = (row["vix1d_prev"] / self.means["vix"]) ** 2
            blend = 0.4 * ew + 0.3 * rv + 0.3 * vx
        else:
            blend = 0.5 * ew + 0.5 * rv
        return math.sqrt(max(blend, 0.05))


def terciles(train: list[dict], scaler: RegimeScaler) -> tuple[float, float]:
    ms = sorted(scaler.mult(r) for r in train)
    return ms[len(ms) // 3], ms[2 * len(ms) // 3]


def tercile_of(row: dict, scaler: RegimeScaler, bounds: tuple[float, float]) -> int:
    m = scaler.mult(row)
    return 0 if m <= bounds[0] else (1 if m <= bounds[1] else 2)
