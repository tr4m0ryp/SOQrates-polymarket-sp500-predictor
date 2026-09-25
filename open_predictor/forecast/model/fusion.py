"""Inverse-variance fusion of (mu, sigma) estimates from pipeline stages."""
import math

from open_predictor.forecast.model.core import phi


def combine(estimates: list[tuple[float, float]]) -> tuple[float, float]:
    """Kalman-style pooling: weight each estimate by 1/sigma^2."""
    weights = [1.0 / (s * s) for _, s in estimates if s > 0]
    mus = [m for m, s in estimates if s > 0]
    total = sum(weights)
    mu = sum(w * m for w, m in zip(weights, mus)) / total
    return mu, math.sqrt(1.0 / total)


def prob_up(mu: float, sigma: float) -> float:
    return phi(mu / sigma)
