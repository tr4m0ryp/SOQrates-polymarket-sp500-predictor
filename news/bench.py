"""Model bench for the Group-B classifier: labeled cases from real history.

Each case is a headline scenario from our 465-day inventory with the
expected classification. Scoring: schema validity, direction sign,
shock flag, event type, plus latency. Run against any OpenAI-compatible
provider with `python3 . news-llm-bench --models a,b,c`.
"""
import json
import time

from news import llm, prompt

SHORTLIST = (
    "deepseek-ai/deepseek-v4-pro",
    "deepseek-ai/deepseek-v4-flash",
    "qwen/qwen3.5-397b-a17b",
    "moonshotai/kimi-k2.6",
    "mistralai/mistral-large-3-675b-instruct-2512",
    "z-ai/glm-5.2",
    "nvidia/nemotron-3-super-120b-a12b",
    "openai/gpt-oss-120b",
    "meta/llama-3.3-70b-instruct",
)

_BASELINE = {"releases_0830": [], "is_nfp_friday": False,
             "prediction_baseline": [
                 {"title": "US x Iran military escalation in 2026?",
                  "odds": {"Yes": "0.20", "No": "0.80"}}]}


def _case(name, headlines, expect, group_a=None, odds_deltas=None):
    return {"name": name, "expect": expect,
            "payload": {"group_a_block": group_a or _BASELINE,
                        "headlines_since_last_run": headlines,
                        "odds_deltas": odds_deltas or {}, "seen_ids": []}}


CASES = [
    _case("iran-deescalation (Mar23)",
          [{"id": "a1", "ts": "2026-03-23T12:02:00Z", "source": "wire",
            "title": "Trump: halting strikes on Iranian energy assets after "
                     "'very productive' talks with Tehran"}],
          {"dir": +1, "shock": True, "type": "geopolitical"}),
    _case("cpi-hot (release morning)",
          [{"id": "b1", "ts": "2026-07-15T12:31:00Z", "source": "bls.gov",
            "title": "CPI June: +0.5% m/m vs +0.2% consensus; core +0.4%"}],
          {"dir": -1, "shock": True, "type": "release"},
          group_a={**_BASELINE, "releases_0830": ["CPI"],
                   "consensus": {"CPI m/m": "+0.2%"}}),
    _case("cpi-cool (release morning)",
          [{"id": "c1", "ts": "2026-07-15T12:31:00Z", "source": "bls.gov",
            "title": "CPI June: 0.0% m/m vs +0.2% consensus"}],
          {"dir": +1, "shock": True, "type": "release"},
          group_a={**_BASELINE, "releases_0830": ["CPI"],
                   "consensus": {"CPI m/m": "+0.2%"}}),
    _case("megacap-earnings-miss (Oct30)",
          [{"id": "d1", "ts": "2026-07-15T01:05:00Z", "source": "wire",
            "title": "Meta plunges 11% after hours on soaring AI capex "
                     "guidance; Microsoft -3%"}],
          {"dir": -1, "shock": True, "type": "earnings"}),
    _case("recap-noise",
          [{"id": "e1", "ts": "2026-07-15T09:00:00Z", "source": "blog",
            "title": "Stocks poised for a mixed open as investors weigh "
                     "earnings season and await Fed clarity"}],
          {"dir": 0, "shock": False, "type": "none"}),
    _case("conditional-fedspeak",
          [{"id": "f1", "ts": "2026-07-15T06:12:00Z", "source": "wire",
            "title": "Fed's Waller says he favors a July cut if inflation "
                     "stays soft"}],
          {"dir": 0, "shock": False, "type": None}),   # type not scored
    _case("odds-shock-no-headline", [],
          {"dir": -1, "shock": True, "type": "geopolitical"},
          odds_deltas={"US x Iran military escalation in 2026?":
                       {"Yes": "+0.09 (0.20 -> 0.29)"}}),
    _case("russia-doctrine (Nov19)",
          [{"id": "g1", "ts": "2026-07-15T02:40:00Z", "source": "wire",
            "title": "Kremlin lowers threshold for nuclear weapons use after "
                     "ATACMS strikes inside Russia"}],
          {"dir": -1, "shock": True, "type": "geopolitical"}),
]


def score_case(out: dict, expect: dict) -> tuple[float, str]:
    pts, notes = 0.0, []
    d, want = out["direction"], expect["dir"]
    if want == 0:
        ok = abs(d) <= 0.2 and not out["shock"]
        pts += 2.0 if ok else 0.0
        notes.append("calm-ok" if ok else f"false-alarm d={d:+.1f}")
    else:
        if d * want > 0 and abs(d) >= 0.3:
            pts += 2.0
        elif d * want > 0:
            pts += 1.0
            notes.append("right-sign-weak")
        else:
            notes.append(f"WRONG-SIGN d={d:+.1f}")
        pts += 0.5 if out["shock"] == expect["shock"] else 0.0
    if expect["type"] and out["event_type"] == expect["type"]:
        pts += 0.5
    return pts, ",".join(notes) or "ok"


def run_bench(models: list[str], base: str, key: str) -> list[dict]:
    results = []
    for model in models:
        provider = {"base": base.rstrip("/"), "key": key, "model": model}
        total, valid, lat, details = 0.0, 0, [], []
        for case in CASES:
            t0 = time.time()
            try:
                raw = llm._call(provider, prompt.GROUP_B_PROMPT,
                                case["payload"])
                out = prompt.validate_b(raw)
                valid += 1
            except Exception as e:
                details.append(f"  {case['name']}: INVALID ({str(e)[:60]})")
                continue
            lat.append(time.time() - t0)
            pts, note = score_case(out, case["expect"])
            total += pts
            details.append(f"  {case['name']}: {pts:.1f} ({note})")
        results.append({"model": model, "score": total, "valid": valid,
                        "n": len(CASES),
                        "median_latency": sorted(lat)[len(lat) // 2] if lat else None,
                        "details": details})
    results.sort(key=lambda r: -r["score"])
    return results
