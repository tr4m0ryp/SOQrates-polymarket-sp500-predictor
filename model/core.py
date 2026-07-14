"""Model cores: baseline, v1.2 (ES-only), v1.3 (VIX1D sigma + NQ spread)."""
import math

from config import (A0, K_DEFAULT, SMALL_GAP, SMALL_GAP_HOURS,
                      NFP_SIGMA_MULT)
from model.regime import RegimeScaler, terciles, tercile_of

HOURS = range(10)


def phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def ols_slope(pairs: list[tuple[float, float]], default: float = K_DEFAULT) -> float:
    n = len(pairs)
    if n < 8:
        return default
    sx = sum(p[0] for p in pairs)
    sy = sum(p[1] for p in pairs)
    sxx = sum(p[0] ** 2 for p in pairs)
    sxy = sum(p[0] * p[1] for p in pairs)
    denom = n * sxx - sx * sx
    return (n * sxy - sx * sy) / denom if denom else default


def _sigma_by_hour(train, mu_fn, mult_fn):
    out = {}
    for h in HOURS:
        res = [(r["off"] - mu_fn(r, h)) / mult_fn(r)
               for r in train if h in r["es"]]
        m = sum(res) / len(res)
        out[h] = math.sqrt(sum((e - m) ** 2 for e in res) / (len(res) - 1))
    return out


class Baseline:
    """Static sigma, pooled k — the original frozen model."""
    name = "baseline"

    def fit(self, train):
        self.sigma = _sigma_by_hour(train, lambda r, h: A0 + K_DEFAULT * r["es"][h],
                                    lambda r: 1.0)
        return self

    def predict(self, row, h):
        mu = A0 + K_DEFAULT * row["es"][h]
        sig = self.sigma[h]
        return mu, sig, phi(mu / sig)


class ModelV12:
    """Tercile-k + small-gap k (early hours) + HL regime sigma + NFP widening."""
    name = "v1.2"
    use_vix = False
    use_nq = False

    def fit(self, train):
        self.scaler = RegimeScaler(use_vix=self.use_vix).fit(train)
        self.bounds = terciles(train, self.scaler)
        self.k_terc = {
            tc: ols_slope([(r["es"][9], r["off"]) for r in train
                           if tercile_of(r, self.scaler, self.bounds) == tc
                           and 9 in r["es"]])
            for tc in range(3)}
        self.k_small = {
            h: ols_slope([(r["es"][h], r["off"]) for r in train
                          if h in r["es"] and abs(r["es"][h]) < SMALL_GAP])
            for h in SMALL_GAP_HOURS}
        if self.use_nq:
            self.c_nq = {
                h: ols_slope([(r["nq"][h] - r["es"][h],
                               r["off"] - self._mu_es(r, h))
                              for r in train if h in r["es"] and h in r["nq"]],
                             default=0.0)
                for h in HOURS}
        self.sigma = _sigma_by_hour(train, self._mu, lambda r: self.scaler.mult(r))
        return self

    def _k(self, row, h):
        if h in SMALL_GAP_HOURS and abs(row["es"][h]) < SMALL_GAP:
            return self.k_small[h]
        return self.k_terc[tercile_of(row, self.scaler, self.bounds)]

    def _mu_es(self, row, h):
        return A0 + self._k(row, h) * row["es"][h]

    def _mu(self, row, h):
        mu = self._mu_es(row, h)
        if self.use_nq and h in row.get("nq", {}):
            mu += self.c_nq[h] * (row["nq"][h] - row["es"][h])
        return mu

    def predict(self, row, h):
        mult = self.scaler.mult(row)
        if row.get("release_morning") and h < 8.5:
            mult *= NFP_SIGMA_MULT
        mu = self._mu(row, h)
        sig = self.sigma[h] * mult
        return mu, sig, phi(mu / sig)


class ModelV13(ModelV12):
    """v1.2 + VIX1D in the regime blend + NQ-ES spread term."""
    name = "v1.3"
    use_vix = True
    use_nq = True


class ModelProd:
    """Production model: v1.3 early (h<=4, where VIX1D+NQ sharpen the call),
    v1.2 late (h>=5, where the plain ES view is better calibrated)."""
    name = "prod"
    SWITCH_HOUR = 5

    def fit(self, train):
        self.early = ModelV13().fit(train)
        self.late = ModelV12().fit(train)
        return self

    def predict(self, row, h):
        model = self.early if h < self.SWITCH_HOUR else self.late
        return model.predict(row, h)
