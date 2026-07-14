"""Group-B (continuous news) mathematical weight - fitted, not guessed.

Publication == market effect (measured: GDELT indexed the Iran story the
same hour ES swung 2%), so after a shock the futures gap already contains
the move and a naive directional voice would double-count. Two effects
remain that the gap does NOT carry, both fittable from history:

  1. post-shock sigma: after a >= SHOCK_PCT one-hour gap move, is the
     official-open residual wider than sigma(tau) says? -> m_shock
  2. conflicted-day direction: shock happened but |gap| ended small -
     does the shock's SIGN still predict the official direction?
     -> lambda (gap-equivalent size of a full-strength news voice)
"""
import math

SHOCK_PCT = 0.35        # one-hour |gap move| that counts as a shock
CONFLICT_GAP = 0.15     # |gap at 9:00| below this = conflicted day
RECENT_HOURS = 2        # shock counts as "recent" this many hours


def shock_hour(gaps: dict[int, float]) -> int | None:
    hs = sorted(gaps)
    for prev, h in zip(hs, hs[1:]):
        if abs(gaps[h] - gaps[prev]) >= SHOCK_PCT:
            return h
    return None


def last_shock(gaps: dict[int, float]) -> tuple[int | None, float]:
    hs = sorted(gaps)
    best_h, delta = None, 0.0
    for prev, h in zip(hs, hs[1:]):
        d = gaps[h] - gaps[prev]
        if abs(d) >= SHOCK_PCT:
            best_h, delta = h, d
    return best_h, delta


def fit_shock_sigma(rows: list[dict], model, at_hour: int = 9) -> dict:
    """Ratio of |official residual| std: recent-shock days vs quiet days."""
    shocked, quiet = [], []
    for r in rows:
        if at_hour not in r["es"]:
            continue
        mu, sig, _ = model.predict(r, at_hour)
        e = (r["off"] - mu) / sig
        h, _ = last_shock(r["es"])
        (shocked if h is not None and at_hour - h <= RECENT_HOURS
         else quiet).append(e * e)
    ratio = math.sqrt((sum(shocked) / len(shocked)) /
                      (sum(quiet) / len(quiet))) if shocked and quiet else 1.0
    return {"m_shock": min(max(ratio, 1.0), 2.5),
            "n_shocked": len(shocked), "n_quiet": len(quiet)}


def fit_conflicted_direction(rows: list[dict], at_hour: int = 9) -> dict:
    """On conflicted days, hit-rate of the shock's sign vs the official open.

    lambda is backed out so the implied probability matches the empirical
    hit-rate: mu_B = z(hit) * sigma_model(at_hour); caller multiplies by
    the LLM's direction*confidence in [-1, 1].
    """
    hits = n = 0
    for r in rows:
        if at_hour not in r["es"] or abs(r["es"][at_hour]) >= CONFLICT_GAP:
            continue
        h, delta = last_shock(r["es"])
        if h is None:
            continue
        n += 1
        hits += (delta > 0) == (r["off"] > 0)
    if n == 0:
        return {"hit_rate": None, "n": 0, "z": 0.0}
    hit = hits / n
    # inverse normal via bisection (stdlib-only)
    lo, hi = -3.0, 3.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if 0.5 * (1 + math.erf(mid / math.sqrt(2))) < hit:
            lo = mid
        else:
            hi = mid
    return {"hit_rate": hit, "n": n, "z": (lo + hi) / 2}
