"""Parser for NYSE TAQ Order Imbalances daily files (CSV .gz).

Free samples: ftp.nyse.com/Historical Data Samples/TAQ NYSE ORDER IMBALANCES/
Paid: $1,000/mo subscription includes 12 months back history (nyse.com).

Message type 105 = auction imbalance:
  105, seq, source_time, symbol, msg_num, reference_price, paired_qty,
  total_imbalance_qty, market_imbalance_qty, auction_time (e.g. 0930),
  auction_type, imbalance_side, continuous_book_clearing_price, ...
The clearing price stream from 8:00 to 9:30 is the NYSE leg's predicted
opening print; unopened names carry prior close in the first index tick.
"""
import gzip
from dataclasses import dataclass, field


@dataclass
class NyseAuction:
    symbol: str
    ref_price: float | None = None
    snaps: list[tuple[str, float, int, int]] = field(default_factory=list)
    # (source_time, clearing_price, paired_qty, imbalance_qty)


def parse_opening(path: str, symbols: set[str] | None = None,
                  until: str = "09:30:10") -> dict[str, NyseAuction]:
    out: dict[str, NyseAuction] = {}
    with gzip.open(path, "rt", errors="replace") as fh:
        for line in fh:
            if not line.startswith("105,"):
                continue
            f = line.rstrip("\n").split(",")
            if len(f) < 13 or f[9] != "0930":
                continue    # opening auction records only
            ts, sym = f[2], f[3]
            if symbols and sym not in symbols:
                continue
            if ts > until:
                break
            rec = out.setdefault(sym, NyseAuction(sym))
            try:
                rec.ref_price = float(f[5])
                clearing = float(f[12])
            except ValueError:
                continue
            if clearing > 0:
                rec.snaps.append((ts, clearing, int(f[6] or 0), int(f[7] or 0)))
    return out


def clearing_at(rec: NyseAuction, ts: str) -> float | None:
    best = None
    for t, px, _, _ in rec.snaps:
        if t <= ts:
            best = px
        else:
            break
    return best


def deviation_vs_open(records: dict[str, NyseAuction],
                      opens: dict[str, float],
                      checkpoints=("09:00:00", "09:25:00", "09:29:00",
                                   "09:29:50")) -> list[dict]:
    """bps deviation of the indicative clearing price vs the official open."""
    rows = []
    for sym, rec in records.items():
        actual = opens.get(sym)
        if not actual or not rec.snaps:
            continue
        row = {"symbol": sym, "open": actual, "ref": rec.ref_price}
        for cp in checkpoints:
            px = clearing_at(rec, cp)
            row[cp] = ((px / actual - 1) * 1e4) if px else None
        rows.append(row)
    return rows
