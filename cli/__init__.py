"""Argument parsing; command bodies live in market / sources / auction."""
import argparse

from cli import auction, market, newscmd, sources


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

    s3 = sub.add_parser("stage3")
    s3.add_argument("--date", required=True,
                    help="YYYY-MM-DD (needs lseg-pull first)")
    s3.set_defaults(fn=auction.cmd_stage3)

    for name, fn in (("predict", market.cmd_predict),
                     ("quirks", market.cmd_quirks),
                     ("ground-truth", sources.cmd_ground_truth),
                     ("weights", sources.cmd_weights),
                     ("lseg-status", auction.cmd_lseg_status),
                     ("calendar-refresh", sources.cmd_calendar_refresh)):
        sub.add_parser(name).set_defaults(fn=fn)

    args = ap.parse_args()
    args.fn(args)
