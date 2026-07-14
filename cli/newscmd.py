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
