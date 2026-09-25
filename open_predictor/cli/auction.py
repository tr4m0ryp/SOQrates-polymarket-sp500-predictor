"""Auction-replica commands: noii-deviation, lseg-*, stage3."""


def cmd_noii_deviation(args):
    from open_predictor.forecast.auction.core import deviation
    from open_predictor.forecast.auction.vendors.itch import parse as itch
    from open_predictor.sources.market import weights as wmod
    try:
        w = {r["ticker"]: r["weight"] for r in wmod.load()}
    except Exception:
        w = {}

    def progress(n, ts_ns):
        h = ts_ns / 3_600_000_000_000
        print(f"  ...{n/1e6:.0f}M msgs, stream at {int(h):02d}:{int(h%1*60):02d} ET")

    print(f"parsing {args.file} (stops after opening cross window)")
    records = itch.parse_opening(args.file, progress=progress)
    agg = deviation.aggregate(records, weights=w)
    print(f"\nsymbols with opening cross + NOII: "
          f"{sum(1 for r in agg['per_symbol'] if r)}")
    print(f"\n{'checkpoint':>9} {'n':>6} {'median|dev|':>11} {'mean|dev|':>10} "
          f"{'p90|dev|':>9} {'idx signed':>10} {'cover%':>7}")
    for cp, s in agg["stats"].items():
        print(f"{cp:>9} {s['n']:>6} {s['median_abs_bps']:>9.1f}bp "
              f"{s['mean_abs_bps']:>8.1f}bp {s['p90_abs_bps']:>7.1f}bp "
              f"{s.get('index_signed_bps', float('nan')):>8.2f}bp "
              f"{s.get('covered_weight_pct', 0):>6.1f}%")
    megas = [r for r in agg["per_symbol"]
             if r["ticker"] in ("AAPL", "MSFT", "AMZN", "GOOGL", "FB", "META",
                                "NVDA", "TSLA", "INTC", "CSCO")]
    if megas:
        print("\nmega-caps, near-price deviation vs print (bps):")
        for r in sorted(megas, key=lambda x: x["ticker"]):
            vals = " ".join(f"{cp}:{r[cp]:+.1f}" if r[cp] is not None else f"{cp}:-"
                            for cp in ("9:25", "9:28", "9:29", "9:29:50"))
            print(f"  {r['ticker']:6} cross {r['cross']:>9.2f}  {vals}")


def cmd_lseg_status(_args):
    from open_predictor.forecast.auction.vendors.lseg import tick_history as lseg
    try:
        lseg.auth_token()
        print("DataScope Select credentials OK - token issued.")
    except lseg.LsegError as e:
        print(f"not ready: {e}")
    except Exception as e:
        print(f"auth failed: {e}")


def cmd_lseg_pull(args):
    from open_predictor.config import CACHE
    from open_predictor.sources.market import weights as wmod
    from open_predictor.forecast.auction.vendors.lseg import parse as lseg_parse, tick_history as lseg

    rows = wmod.load()
    nas = [r["ticker"] for r in rows if r["exchange"] == "NASDAQ"]
    nyse = [r["ticker"] for r in rows if r["exchange"] == "NYSE"]
    print(f"pulling {args.date}: {len(nas)} Nasdaq + {len(nyse)} NYSE RICs")
    payload = lseg.quirk_day_pull(nas, nyse, args.date)
    out = CACHE / "lseg"
    out.mkdir(exist_ok=True)
    path = out / f"{args.date}.csv"
    path.write_bytes(payload)
    print(f"saved {path} ({len(payload)/1e6:.1f} MB)")
    print("\ntop FIDs seen (extend replica/vendors/lseg/parse.py FID_MAP with auction fields):")
    for name, n in list(lseg_parse.discover(payload).items())[:25]:
        print(f"  {name}: {n}")


def cmd_databento_status(_args):
    from open_predictor.forecast.auction.vendors.databento import source
    from open_predictor.forecast.auction.vendors.databento.client import DatabentoError
    try:
        datasets = source.ping()
    except DatabentoError as e:
        print(f"not ready: {e}")
        return
    except Exception as e:
        print(f"ping failed: {e}")
        return
    print(f"DATABENTO_API_KEY OK - {len(datasets)} datasets visible "
          f"(XNAS.ITCH: {'XNAS.ITCH' in datasets}, "
          f"XNYS.PILLAR: {'XNYS.PILLAR' in datasets}).")


def cmd_databento_pull(args):
    from open_predictor.forecast.auction.vendors.databento import source, schemas
    from open_predictor.forecast.auction.vendors.databento.client import DatabentoError
    try:
        res = source.pull_day(args.date)
    except DatabentoError as e:
        print(f"not ready: {e}")
        return
    print(f"cached raw JSON under {res['dir']}")
    for name, n in res["counts"].items():
        print(f"  {name}: {n} records")
    for name, err in res["errors"].items():
        print(f"  {name}: ERROR {err}")
    print("\nobserved DBN fields (extend schemas maps if any auction "
          "field is missing):")
    for name, n in list(schemas.discover(res["records"]).items())[:25]:
        print(f"  {name}: {n}")


def cmd_stage3(args):
    import os
    from open_predictor.config import CACHE
    from open_predictor.sources.market import yahoo
    from open_predictor.forecast.auction import pipeline
    from open_predictor.forecast.auction.vendors.lseg import parse as lseg_parse

    src = getattr(args, "source", None) or (
        "databento" if os.environ.get("DATABENTO_API_KEY") else "lseg")
    if src == "databento":
        from open_predictor.forecast.auction.vendors.databento import source
        if not source.cached(args.date):
            print(f"no cached databento pull for {args.date} - run: "
                  f"databento-pull --date {args.date}")
            return
        snaps = source.snapshots(args.date)
    else:
        path = CACHE / "lseg" / f"{args.date}.csv"
        if not path.exists():
            print(f"no cached pull for {args.date} - run: "
                  f"lseg-pull --date {args.date}")
            return
        snaps = lseg_parse.snapshots(str(path))
    spx = yahoo.daily_open_close("^GSPC", 400)
    days = sorted(spx)
    if args.date not in spx:
        print(f"{args.date} not a trading day in ^GSPC history")
        return
    prior = days[days.index(args.date) - 1]

    # Reference price comes from the auction record itself: it is
    # contemporaneous and already adjusted for corporate actions. Yahoo
    # history is SPLIT-ADJUSTED while these prices are raw, so pairing the two
    # is wrong by the cumulative split factor for any name that has split
    # since (measured 2025-09-12: NFLX +899%, BKNG +2383%). Yahoo is a
    # per-name fallback only, and is correct only for very recent dates.
    pred, closes, fellback = {}, {}, []
    for t, ss in snaps.items():
        last = next((s for s in reversed(ss) if s.get("pred_open")), None)
        if not last:
            continue
        ref = next((s.get("ref_price") for s in ss if s.get("ref_price")), None)
        if not ref:
            fellback.append(t)
            try:
                hist = yahoo.daily_open_close(t.replace(".", "-"), 35)
                ref = hist.get(prior, (None, None))[1]
            except Exception:
                ref = None
        if ref:
            pred[t] = last["pred_open"]
            closes[t] = ref
    print(f"[{src}] {len(pred)} tickers with indicative prices "
          f"({len(fellback)} needed a Yahoo prior-close fallback)")
    rep = pipeline.replica_estimate(pred, closes)
    dist = pipeline.replica_distribution(pred, closes)
    official = (spx[args.date][0] / spx[prior][1] - 1) * 100
    print(f"replica gap {rep['replica_gap_pct']:+.3f}% "
          f"(live weight {rep['live_weight_pct']:.0f}%)")
    print(f"distribution: mean {dist['mean']:+.3f}% sigma {dist['sigma']:.3f}% "
          f"P(up) {dist['p_up']:.2f} [q05 {dist['q05']:+.3f} q95 {dist['q95']:+.3f}]")
    for pv in dist["pivotal"][:4]:
        print(f"  pivotal: {pv['ticker']} p_live {pv['p_live']} "
              f"swings P(up) {pv['p_up_swing']:+.2f}")
    print(f"official gap {official:+.3f}%  -> direction "
          f"{'MATCH' if (dist['mean'] > 0) == (official > 0) else 'MISS'}")


def cmd_replica_sim(_args):
    """Synthetic self-test: validates the MC assembly today, without data."""
    import math
    from open_predictor.forecast.auction.core.montecarlo import McConstituent, simulate, apply_prints
    from open_predictor.forecast.auction.core.timing import TimingModel

    # independent-case check vs analytic normal approximation
    cons = [McConstituent(f"S{i}", 1.0, 0.5, 0.7, 0.0) for i in range(50)]
    res = simulate(cons)
    mu_a = 0.7 * 0.5
    var_a = sum((1/50)**2 * 0.5**2 * 0.7 * 0.3 for _ in range(50))
    p_a = 0.5 * (1 + math.erf((mu_a / math.sqrt(var_a)) / math.sqrt(2)))
    print(f"independent check: MC mean {res['mean']:.3f} (analytic {mu_a:.3f}), "
          f"MC P(up) {res['p_up']:.3f} (analytic ~{p_a:.3f})")

    # lumpy quirk-day scenario: flat photo, one pivotal fast-NYSE giant
    cons = ([McConstituent("NAS", 55.0, +0.02, 1.0, 0.05)] +
            [McConstituent("JPM", 1.5, -0.90, 0.85, 0.30)] +
            [McConstituent("LLY", 1.2, +0.80, 0.60, 0.30)] +
            [McConstituent(f"NY{i}", 0.8, 0.0, 0.10, 0.30) for i in range(40)])
    res = simulate(cons)
    print(f"\nquirk scenario: mean {res['mean']:+.3f}% sigma {res['sigma']:.3f}% "
          f"P(up) {res['p_up']:.2f} (uncertain names: {res['n_uncertain']})")
    for pv in res["pivotal"]:
        print(f"  pivotal: {pv['ticker']} p_live {pv['p_live']} "
              f"swings P(up) by {pv['p_up_swing']:+.2f}")

    # filtering: JPM prints at -0.9 -> distribution collapses
    res2 = simulate(apply_prints(cons, {"JPM": -0.90}))
    print(f"after JPM prints: P(up) {res['p_up']:.2f} -> {res2['p_up']:.2f}")
