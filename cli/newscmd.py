"""News-layer commands: news-mistakes inventory."""
import json


def cmd_news_mistakes(args):
    from backtest import dataset
    from model.core import ModelProd
    from news import mistakes
    from config import ROOT

    rows = dataset.load(rebuild=args.rebuild)
    train, _ = dataset.split(rows)
    out = mistakes.build(rows, ModelProd().fit(train))

    labels = {}
    lf = ROOT / "news" / "event_labels.json"
    if lf.exists():
        labels = json.loads(lf.read_text())

    counts = {}
    for m in out:
        counts[m["kind"]] = counts.get(m["kind"], 0) + 1
    print(f"{len(out)} news-affected days in {len(rows)}: {counts}\n")
    print(f"{'date':11}{'kind':14}{'conf':>5} {'call':>5} {'won':>4} "
          f"{'off%':>7} {'swing':>6}  window / event")
    for m in out:
        rel = ",".join(m["releases"])
        label = labels.get(m["date"], rel or "")
        print(f"{m['date']} {m['kind']:14}{m['conf']:>5.2f} {m['call']:>5} "
              f"{'W' if m['won'] else 'L':>4} {m['official_pct']:>+7.2f} "
              f"{m['swing_pct']:>5.2f}%  {m['window']}"
              + (f" | {label}" if label else ""))


RUN_SCHEDULE = (          # ET checkpoints derived from the decisive-hour profile
    ("02:30", "post-Asia, pre-Europe"),
    ("04:30", "Europe open digested"),
    ("07:00", "US pre-market ramp"),
    ("08:00", "pre-release check"),
    ("08:35", "MANDATORY - right after 8:30 releases"),
    ("09:15", "final pass before the open"),
)


def cmd_news_timing(_args):
    import json
    from backtest import dataset
    from news import timing
    from config import CACHE

    rows = dataset.load()
    mistakes = json.loads((CACHE / "news_mistakes.json").read_text())
    prof = timing.profile(rows, mistakes)
    print("decisive-move hour (ET, hour ending) across news-affected days:")
    print(f"{'kind':>14}" + "".join(f"{h:>6}" for h in range(1, 10)))
    for kind in ("news_miss", "news_swing", "news_survived", "all"):
        hs = prof["hist"][kind]
        print(f"{kind:>14}" + "".join(f"{hs[h]:>6}" for h in range(1, 10)))
    print("\ncumulative share already happened if last LLM run was at hour H:")
    for kind in ("news_miss", "all"):
        c = prof["cum"][kind]
        print(f"{kind:>14}" + "".join(f"{c[h]*100:>5.0f}%" for h in range(1, 10)))
    print("\nLLM run schedule (ET):")
    for t, why in RUN_SCHEDULE:
        print(f"  {t}  {why}")
    print("  + event trigger: gap moves >0.15% within 15min between checkpoints")


def cmd_news_prefetch(_args):
    from news import prefetch
    ctx = prefetch.build()
    print(f"prefetch for {ctx['date']}: releases {ctx['releases_0830'] or 'none'}, "
          f"NFP-Friday {ctx['is_nfp_friday']}")
    for m in ctx["prediction_baseline"]:
        odds = ", ".join(f"{k} {float(v)*100:.0f}%" for k, v in list(m["odds"].items())[:2])
        print(f"  [{m['tag']}] {m['title'][:58]:58} ${m['volume']:>12,} | {odds}")
    print("cached to .cache/news_prefetch.json - reused by every LLM run tonight")


def cmd_news_groupb_fit(_args):
    from backtest import dataset
    from model.core import ModelProd
    from news import groupb

    rows = dataset.load()
    train, test = dataset.split(rows)
    model = ModelProd().fit(train)
    for name, sub in (("train", train), ("test", test), ("pooled", rows)):
        s = groupb.fit_shock_sigma(sub, model)
        print(f"{name:6} post-shock sigma ratio {s['m_shock']:.2f} "
              f"(shocked {s['n_shocked']} / quiet {s['n_quiet']})")
    hits = n = 0
    for h in (7, 8):
        d = groupb.fit_conflicted_direction(rows, at_hour=h)
        print(f"conflicted h={h}: hit {d['hit_rate']:.2f} n={d['n']}")
        hits += d["hit_rate"] * d["n"]; n += d["n"]
    print(f"pooled conflicted hit-rate {hits/n*100:.1f}% (n={n}) "
          f"-> Z_CONFLICT {groupb.Z_CONFLICT} (conservative)")


def cmd_news_llm_test(_args):
    from news import llm, prompt, prefetch

    ctx = prefetch.build()
    payload = {"group_a_block": ctx, "headlines_since_last_run": [
        {"id": "test-1", "ts": "2026-07-15T06:12:00Z", "source": "wire-test",
         "title": "Fed's Waller says he favors a July cut if inflation stays soft"}],
        "odds_deltas": {}, "seen_ids": []}
    try:
        out = llm.run(prompt.GROUP_B_PROMPT, payload, prompt.validate_b)
    except llm.LlmError as e:
        print(f"not ready: {e}")
        return
    print(f"provider: {out.pop('_provider')}")
    for k, v in out.items():
        print(f"  {k}: {v}")


def cmd_news_llm_bench(args):
    import os
    from news import bench

    base = os.environ.get("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    key = os.environ.get("LLM_API_KEY", "")
    if not key:
        print("set LLM_API_KEY (nvapi-... for NVIDIA) and rerun")
        return
    models = args.models.split(",") if args.models else list(bench.SHORTLIST)
    print(f"benching {len(models)} models on {len(bench.CASES)} labeled cases\n")
    results = bench.run_bench(models, base, key)
    maxpts = 2.5 * len(bench.CASES)
    for r in results:
        lat = f"{r['median_latency']:.1f}s" if r["median_latency"] else "-"
        print(f"{r['model']:48} {r['score']:>5.1f}/{maxpts:.0f}  "
              f"valid {r['valid']}/{r['n']}  median {lat}")
        if args.verbose:
            print("\n".join(r["details"]))
    print("\nwinner ->", results[0]["model"] if results else "none")


def cmd_news_replay(_args):
    from backtest import dataset
    from news import replay

    rows = dataset.load()
    results = replay.replay_labeled(rows)
    ok = [r for r in results if "verdict" in r]
    correct = sum(1 for r in ok if r["verdict"] == "CORRECT")
    weak = sum(1 for r in ok if r["verdict"] == "weak-right")
    wrong = sum(1 for r in ok if r["verdict"] == "WRONG-SIGN")
    missed = sum(1 for r in ok if r["verdict"] == "missed(0)")
    print(f"\nreplayed {len(ok)} labeled days: {correct} correct, "
          f"{weak} weak-right, {missed} missed(0), {wrong} wrong-sign")
