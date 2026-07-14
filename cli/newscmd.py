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
