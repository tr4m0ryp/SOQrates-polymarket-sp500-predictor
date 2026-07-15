"""Distributional first-tick assembly (Monte Carlo over the live set).

The photo gap is a random variable: sum over stocks of w_i * B_i * g_i,
where B_i ~ Bernoulli(p_live_i) with a common "slow morning" factor
correlating the flips, plus per-stock preview-vs-print noise. Collapsing
to the mean (w*p*g) hides the slot variance, the correlation, and the
lumpiness that decides quirk days - this module keeps the distribution.

Stocks are partitioned for speed: certain-live names collapse into one
deterministic base (their pooled noise is a single Gaussian), certain-stale
names contribute zero, and only the uncertain names are simulated per
scenario (~50-100 of 505).
"""
import math
import random
from dataclasses import dataclass

N_SCENARIOS = 2000
SLOWNESS_BETA = 1.0     # logit shift per unit of the common slowness factor
SEED = 7                # fixed: reproducible runs, no wall-clock dependence


@dataclass
class McConstituent:
    ticker: str
    weight: float        # index weight, %
    gap: float           # predicted gap % if counted live
    p_live: float        # probability the stock makes the first tick
    sigma: float         # preview-vs-print noise, % (0.05 NAS / 0.30 NYSE measured)


def _logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def simulate(cons: list[McConstituent], n: int = N_SCENARIOS,
             slowness_beta: float = SLOWNESS_BETA, seed: int = SEED,
             pivotal_top: int = 6) -> dict:
    rng = random.Random(seed)
    w_total = sum(c.weight for c in cons)

    live = [c for c in cons if c.p_live >= 0.995]
    uncertain = [c for c in cons if 0.005 < c.p_live < 0.995]
    base = sum(c.weight * c.gap for c in live) / w_total
    base_noise = math.sqrt(sum((c.weight * c.sigma) ** 2 for c in live)) / w_total
    logits = [_logit(c.p_live) for c in uncertain]

    watch = sorted(uncertain, key=lambda c: -c.weight * max(abs(c.gap), 0.05))
    watch = [cons.index(c) for c in watch[:pivotal_top]]
    watch_set = {cons.index(c): i for i, c in enumerate(uncertain)
                 if cons.index(c) in watch}

    gaps, states = [], []
    for _ in range(n):
        z = rng.gauss(0, 1)
        total = base + (rng.gauss(0, base_noise) if base_noise else 0.0)
        st = {}
        for c, lo in zip(uncertain, logits):
            p = _sigmoid(lo - slowness_beta * z)
            b = rng.random() < p
            if b:
                g = c.gap + (rng.gauss(0, c.sigma) if c.sigma else 0.0)
                total += c.weight * g / w_total
            idx = cons.index(c)
            if idx in watch_set:
                st[idx] = b
        gaps.append(total)
        states.append(st)

    order = sorted(range(n), key=lambda i: gaps[i])
    sorted_gaps = [gaps[i] for i in order]
    mean = sum(gaps) / n
    var = sum((x - mean) ** 2 for x in gaps) / (n - 1)
    p_up = sum(1 for x in gaps if x > 0) / n

    pivotal = []
    for idx in watch:
        up_in = [gaps[i] > 0 for i in range(n) if states[i].get(idx)]
        up_out = [gaps[i] > 0 for i in range(n) if states[i].get(idx) is False]
        if len(up_in) > 20 and len(up_out) > 20:
            swing = sum(up_in) / len(up_in) - sum(up_out) / len(up_out)
            if abs(swing) > 0.02:
                pivotal.append({"ticker": cons[idx].ticker,
                                "p_live": round(cons[idx].p_live, 2),
                                "p_up_swing": round(swing, 3)})
    pivotal.sort(key=lambda x: -abs(x["p_up_swing"]))

    return {"mean": mean, "sigma": math.sqrt(var), "p_up": p_up,
            "q05": sorted_gaps[int(0.05 * n)], "q50": sorted_gaps[n // 2],
            "q95": sorted_gaps[int(0.95 * n)], "n": n,
            "n_uncertain": len(uncertain), "pivotal": pivotal}


def apply_prints(cons: list[McConstituent], printed: dict[str, float],
                 timing=None, elapsed_s: float = 0.0,
                 photo_s: float = 1.0) -> list[McConstituent]:
    """Filtering step for 9:30:00+: observed prints become facts; silent
    names get their p_live conditioned on 'not printed yet'."""
    out = []
    for c in cons:
        if c.ticker in printed:
            out.append(McConstituent(c.ticker, c.weight,
                                     printed[c.ticker], 1.0, 0.0))
        elif timing is not None and elapsed_s > 0 and 0 < c.p_live < 1:
            p = timing.condition_not_printed(c.ticker, elapsed_s, photo_s)
            out.append(McConstituent(c.ticker, c.weight, c.gap, p, c.sigma))
        else:
            out.append(c)
    return out
