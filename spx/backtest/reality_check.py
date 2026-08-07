"""White's reality check for the strategy-lab selection (multiple testing).

The paper reports the best of 15 verified strategy candidates on the 58-day
test half. Selecting the best of a family and quoting its unadjusted
performance overstates significance; this script corrects for that with
White's reality check (White 2000, Econometrica): the test statistic is the
maximum, over the candidate family, of sqrt(n) times mean daily flat-stake
PnL, and its null distribution comes from a stationary bootstrap
(Politis-Romano 1994) of the test-half day-PnL panel, resampled jointly
across candidates so cross-candidate correlation is preserved.

Candidate provenance: the 28-agent verification workflow (session 380c3a0d,
run wf_89eb270d) recorded 16 submissions that dedupe to the 15 unique
parameterizations below -- the "15 verified strategy candidates" of the
paper. Two takeprofit entries differ only by an explicit maker=0 (the
engine default) and are behaviorally identical; duplicates do not change a
max statistic. EXTENDED adds the two later survivors selected after the
workflow (first_signal and the full_strategy composite), since selection in
fact continued past the recorded 15.

All candidates run in flat-stake mode ($100 research stakes; bet_frac /
stake_abs stripped) so mean daily PnL is in common units. Days the volume
gate skips count as $0 days: the 58-day test grid is fixed.

Run from the repo root:  python3 -m backtest.reality_check
"""
import math
import random

MEAN_BLOCK = 5.0        # stationary-bootstrap mean block length, days
DRAWS = 10000
SEED = 20260719

_EXEC = {"signal": "model", "half_spread": 0.01, "impact_per_100": 0.001}

CANDIDATES = [
    ("hold", {"hour": 5, "edge": 0.06, "gate": 0.6, "maker": 0,
              "bet_frac": 0.15, **_EXEC}),
    ("hold", {"hour": 4, "edge": 0.08, "gate": 0.6, "maker": 0,
              "bet_frac": 0.1, **_EXEC}),
    ("flow_flip", {"h0": 1, "agree_min": 0.55, "min_lean": 0.02,
                   "flip_from": 8, "flip_edge": 0.15, "bet_frac": 0.1,
                   "sizing": "fixed", **_EXEC}),
    ("flow_flip", {"h0": 1, "agree_min": 0.55, "min_lean": 0.02,
                   "flip_from": 8, "flip_edge": 0.1, "bet_frac": 0.05,
                   "sizing": "fixed", **_EXEC}),
    ("convergence", {"hour": 5, "edge": 0.05, "gate": 0.6, "exit_h": 9,
                     "min_move": 0.05, "margin": 0.01, "hold_ok": 0,
                     "sizing": "fixed", "bet_frac": 0.15, **_EXEC}),
    ("takeprofit", {"hour": 5, "edge": 0.05, "gate": 0.6, "tp": 0.95,
                    "sizing": "fixed", "bet_frac": 0.15, **_EXEC}),
    ("flow_flip", {"h0": 1, "flip_from": 8, "flip_edge": 0.15,
                   "bet_frac": 0.1, **_EXEC}),
    ("hold", {"hour": 4, "edge": 0.05, "gate": 0.6,
              "bet_frac": 0.1, **_EXEC}),                  # the survivor
    ("longshot", {"px_max": 0.25, "p_min": 0.25, "h_min": 0,
                  "sizing": "optimal", "max_stake": 20,
                  "bet_frac": 0.1, **_EXEC}),
    ("longshot", {"px_max": 0.12, "p_min": 0.3, "h_min": 0,
                  "sizing": "optimal", "max_stake": 10,
                  "bet_frac": 0.1, **_EXEC}),
    ("takeprofit", {"hour": 4, "edge": 0.07, "gate": 0.6, "tp": 0.97,
                    "sizing": "fixed", "bet_frac": 0.15, **_EXEC}),
    ("convergence", {"hour": 4, "edge": 0.08, "gate": 0.6, "exit_h": 9,
                     "min_move": 0.05, "margin": 0, "hold_ok": 1,
                     "sizing": "fixed", "bet_frac": 0.15, **_EXEC}),
    ("takeprofit", {"hour": 5, "edge": 0.05, "gate": 0.6, "tp": 0.95,
                    "maker": 0, "sizing": "fixed", "bet_frac": 0.15,
                    **_EXEC}),
    ("hold", {"hour": 7, "edge": 0.04, "gate": 0.65, "maker": 1,
              "maker_disc": 0.03, "sizing": "fixed", "bet_frac": 0.15,
              **_EXEC}),
    ("hold", {"hour": 5, "edge": 0.05, "gate": 0.6, "maker": 0,
              "sizing": "fixed", "bet_frac": 0.2, **_EXEC}),
]

EXTENDED = [
    ("first_signal", {"h_start": 4, "h_end": 9, "edge": 0.05, "gate": 0.7,
                      "stake_abs": 50, **_EXEC}),
    ("full_strategy", {"h_start": 4, "h_end": 9, "edge": 0.05, "gate": 0.7,
                       "px_max": 0.95, "exit_thr": 0.5, "flip": 1,
                       "stake_abs": 50, **_EXEC}),
]


def _flat(prm: dict) -> dict:
    """Non-compounding $100 research stakes: comparable units across
    candidates. sizing='optimal' keeps its own stake rule (part of the
    strategy definition)."""
    d = dict(prm)
    d.pop("bet_frac", None)
    d.pop("stake_abs", None)
    return d


def _label(fam: str, prm: dict) -> str:
    skip = set(_EXEC) | {"bet_frac", "stake_abs", "sizing"}
    core = {k: v for k, v in prm.items() if k not in skip}
    if prm.get("sizing") == "optimal":
        core["sizing"] = "optimal"
    return fam + " " + ",".join(f"{k}={v}" for k, v in sorted(core.items()))


def day_series(fam: str, prm: dict, days: list[dict]) -> list[float]:
    from spx.strategy.engine import sim
    res = sim.run(fam, days, _flat(prm))
    by_date = {d["date"]: d["pnl"] for d in res["days"]}
    return [float(by_date.get(day["date"], 0.0)) for day in days]


def _stationary_idx(n: int, rng: random.Random) -> list[int]:
    """One stationary-bootstrap draw of day indices (wrap-around;
    geometric block lengths with mean MEAN_BLOCK)."""
    out = []
    t = rng.randrange(n)
    for i in range(n):
        if i and rng.random() < 1.0 / MEAN_BLOCK:
            t = rng.randrange(n)
        out.append(t)
        t = (t + 1) % n
    return out


def reality_check(series: list[list[float]], draws: int = DRAWS,
                  seed: int = SEED) -> dict:
    """White's RC p for max_k sqrt(n)*mean(f_k) vs 0, plus the naive
    (single-hypothesis) bootstrap p for the best candidate alone."""
    n = len(series[0])
    rn = math.sqrt(n)
    means = [sum(s) / n for s in series]
    best = max(range(len(series)), key=lambda k: means[k])
    v_obs = rn * means[best]
    rng = random.Random(seed)
    exceed = exceed_naive = 0
    for _ in range(draws):
        idx = _stationary_idx(n, rng)
        v_star = -math.inf
        for k, s in enumerate(series):
            b = rn * (sum(s[i] for i in idx) / n - means[k])
            if b > v_star:
                v_star = b
            if k == best and b >= v_obs:
                exceed_naive += 1
        if v_star >= v_obs:
            exceed += 1
    return {"n": n, "best": best, "means": means, "v_obs": v_obs,
            "p_rc": exceed / draws, "p_naive": exceed_naive / draws}


def main() -> None:
    from spx.strategy import data
    days = data.build()
    _, test = data.split(days)
    print(f"test half: {len(test)} days {test[0]['date']}..{test[-1]['date']}"
          f"  |  flat $100 stakes  |  B={DRAWS} stationary bootstrap "
          f"(mean block {MEAN_BLOCK:g}d, seed {SEED})")

    fams = [("recorded family (paper's 15)", CANDIDATES),
            ("extended family (15 + later survivors)", CANDIDATES + EXTENDED)]
    series_cache: dict[str, list[float]] = {}
    for title, cands in fams:
        series, labels = [], []
        for fam, prm in cands:
            lab = _label(fam, prm)
            if lab not in series_cache:
                series_cache[lab] = day_series(fam, prm, test)
            series.append(series_cache[lab])
            labels.append(lab)
        rc = reality_check(series)
        print(f"\n== {title}: {len(cands)} candidates ==")
        print(f"{'mean$/d':>8} {'total$':>8}  candidate")
        for lab, s, m in sorted(zip(labels, series, rc["means"]),
                                key=lambda r: -r[2]):
            print(f"{m:8.2f} {sum(s):8.2f}  {lab}")
        best = labels[rc["best"]]
        print(f"best: {best}")
        print(f"  V = sqrt({rc['n']}) * mean = {rc['v_obs']:.2f}")
        print(f"  naive (unadjusted) bootstrap p = {rc['p_naive']:.4f}")
        print(f"  White reality-check adjusted p = {rc['p_rc']:.4f}")


if __name__ == "__main__":
    main()
