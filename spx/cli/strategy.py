"""Strategy-lab commands: history fetch, dataset build, run, coarse search."""
import json


def cmd_pm_history(args):
    from pm import history
    history.fetch_all(refresh=args.refresh)


def cmd_strategy_data(args):
    from strategy import data
    days = data.build(rebuild=args.rebuild)
    tr, te = data.split(days)
    up = sum(1 for d in days if d["outcome_up"])
    print(f"{len(days)} joined days ({days[0]['date']} .. {days[-1]['date']}), "
          f"{up} up / {len(days) - up} down")
    print(f"train {len(tr)} (.. {tr[-1]['date']})   test {len(te)} "
          f"({te[0]['date']} ..)")


def _half(days, which):
    from strategy import data
    tr, te = data.split(days)
    return {"train": tr, "test": te, "all": days}[which]


def cmd_strategy_run(args):
    from strategy import data, sim
    days = _half(data.build(), args.half)
    res = sim.run(args.family, days, json.loads(args.params))
    if args.json:
        print(json.dumps({k: res[k] for k in ("family", "params", "metrics",
                                              "days" if args.days else "metrics")}))
        return
    print(f"{args.family} {args.params} [{args.half}]")
    for k, v in res["metrics"].items():
        print(f"  {k:>14} {v}")


def cmd_strategy_search(args):
    from strategy import data, sim
    days = _half(data.build(), args.half)
    grids = {
        "hold": [{"hour": h, "edge": e, "gate": g, "maker": mk}
                 for h in (0, 4, 7, 9) for e in (0.05, 0.10, 0.15)
                 for g in (0.60, 0.65, 0.75) for mk in (0, 1)],
        "takeprofit": [{"hour": h, "edge": 0.05, "gate": 0.65, "tp": tp}
                       for h in (0, 4, 7) for tp in (0.90, 0.95, 0.99)],
        "flow_flip": [{"h0": 1, "flip_from": f, "flip_edge": fe}
                      for f in (7, 8, 9) for fe in (0.15, 0.25, 0.35)],
        "longshot": [{"px_max": px, "p_min": pm, "h_min": 0}
                     for px in (0.10, 0.15, 0.25) for pm in (0.25, 0.35, 0.50)],
        "scale_in": [{"hours": hs, "edge": 0.05, "gate": g}
                     for hs in ([0, 4, 7], [0, 4, 7, 9], [4, 7, 9])
                     for g in (0.60, 0.65)],
    }
    rows = []
    for fam, grid in grids.items():
        for prm in grid:
            m = sim.run(fam, days, prm)["metrics"]
            if m["n_trades"]:
                rows.append((fam, prm, m))
    rows.sort(key=lambda r: r[2]["total_pnl"], reverse=True)
    print(f"{'family':<11} {'pnl':>8} {'roi':>7} {'win%':>6} {'days':>5} "
          f"{'shrp':>6} {'dd':>7}  params")
    for fam, prm, m in rows[:args.top]:
        print(f"{fam:<11} {m['total_pnl']:>8} {m['roi']:>7} "
              f"{m['win_rate']:>6} {m['n_days_traded']:>5} "
              f"{m['sharpe_day']:>6} {m['max_drawdown']:>7}  {json.dumps(prm)}")
