"""Argument parsing; command bodies live in market / sources / auction."""
import argparse

from spx.cli import auction, market, newscmd, sources, strategy


def main():
    ap = argparse.ArgumentParser(prog="spx-open")
    sub = ap.add_subparsers(dest="cmd", required=True)

    nm = sub.add_parser("news-mistakes")
    nm.add_argument("--rebuild", action="store_true")
    nm.set_defaults(fn=newscmd.cmd_news_mistakes)

    nt = sub.add_parser("news-timing")
    nt.set_defaults(fn=newscmd.cmd_news_timing)

    np_ = sub.add_parser("news-prefetch")
    np_.set_defaults(fn=newscmd.cmd_news_prefetch)

    gb = sub.add_parser("news-groupb-fit")
    gb.set_defaults(fn=newscmd.cmd_news_groupb_fit)

    lt = sub.add_parser("news-llm-test")
    lt.set_defaults(fn=newscmd.cmd_news_llm_test)

    lb = sub.add_parser("news-llm-bench")
    lb.add_argument("--models", default="", help="comma list; default = NVIDIA shortlist")
    lb.add_argument("--verbose", action="store_true")
    lb.set_defaults(fn=newscmd.cmd_news_llm_bench)

    rp = sub.add_parser("news-replay")
    rp.set_defaults(fn=newscmd.cmd_news_replay)

    bt = sub.add_parser("backtest")
    bt.add_argument("--rebuild", action="store_true")
    bt.set_defaults(fn=market.cmd_backtest)

    nd = sub.add_parser("noii-deviation")
    nd.add_argument("--file", required=True,
                    help="path to a NASDAQ_ITCH50.gz full-day file")
    nd.set_defaults(fn=auction.cmd_noii_deviation)

    lp = sub.add_parser("lseg-pull")
    lp.add_argument("--date", required=True, help="YYYY-MM-DD quirk day")
    lp.set_defaults(fn=auction.cmd_lseg_pull)

    rs = sub.add_parser("replica-sim")
    rs.set_defaults(fn=auction.cmd_replica_sim)

    dp = sub.add_parser("databento-pull")
    dp.add_argument("--date", required=True, help="YYYY-MM-DD to pull + cache")
    dp.set_defaults(fn=auction.cmd_databento_pull)

    s3 = sub.add_parser("stage3")
    s3.add_argument("--date", required=True,
                    help="YYYY-MM-DD (needs databento-pull or lseg-pull first)")
    s3.add_argument("--source", choices=["lseg", "databento"], default=None,
                    help="auction source (default: databento if "
                         "DATABENTO_API_KEY set, else lseg)")
    s3.set_defaults(fn=auction.cmd_stage3)

    ph = sub.add_parser("pm-history")
    ph.add_argument("--refresh", action="store_true")
    ph.set_defaults(fn=strategy.cmd_pm_history)

    sd = sub.add_parser("strategy-data")
    sd.add_argument("--rebuild", action="store_true")
    sd.set_defaults(fn=strategy.cmd_strategy_data)

    sr = sub.add_parser("strategy-run")
    sr.add_argument("--family", required=True)
    sr.add_argument("--params", default="{}")
    sr.add_argument("--half", default="train",
                    choices=("train", "test", "all"))
    sr.add_argument("--json", action="store_true")
    sr.add_argument("--days", action="store_true")
    sr.set_defaults(fn=strategy.cmd_strategy_run)

    ss = sub.add_parser("strategy-search")
    ss.add_argument("--half", default="train",
                    choices=("train", "test", "all"))
    ss.add_argument("--top", type=int, default=25)
    ss.set_defaults(fn=strategy.cmd_strategy_search)

    for name, fn in (("predict", market.cmd_predict),
                     ("quirks", market.cmd_quirks),
                     ("ground-truth", sources.cmd_ground_truth),
                     ("weights", sources.cmd_weights),
                     ("lseg-status", auction.cmd_lseg_status),
                     ("databento-status", auction.cmd_databento_status),
                     ("calendar-refresh", sources.cmd_calendar_refresh)):
        sub.add_parser(name).set_defaults(fn=fn)

    args = ap.parse_args()
    args.fn(args)
