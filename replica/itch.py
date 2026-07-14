"""Streaming Nasdaq TotalView-ITCH 5.0 parser for opening-auction messages.

Reads the raw BinaryFILE format (2-byte big-endian length prefix per message)
straight from a .gz stream, extracts only what the auction replica needs, and
stops shortly after the opening cross window to avoid parsing the full day:

  'R' Stock Directory  -> locate id -> ticker
  'I' NOII             -> near/far/ref price, paired/imbalance, 9:25-9:30
  'Q' Cross Trade      -> the actual opening print (cross type 'O')

Prices are uint32 with 4 implied decimals; timestamps are uint48 nanoseconds
since midnight ET. Free full-day samples: https://emi.nasdaq.com/ITCH/
"""
import gzip
import struct
from dataclasses import dataclass, field

_PX = 1e-4
_NS_H = 3_600_000_000_000
STOP_NS = int(9.75 * _NS_H)          # stop parsing at 09:45 ET
_TS_PROBE_EVERY = 1_000_000          # sample a timestamp every N messages

MSG_NOII = 73            # 'I'
MSG_CROSS = 81           # 'Q'
MSG_DIRECTORY = 82       # 'R'

_u16 = struct.Struct(">H")
_noii = struct.Struct(">HH6sQQc8sIIIcc")   # 'I' body after type byte
_cross = struct.Struct(">HH6sQ8sIQc")      # 'Q' body after type byte


def _ns(b: bytes) -> int:
    return int.from_bytes(b, "big")


@dataclass
class NoiiSnap:
    ts_ns: int
    near: float
    far: float
    ref: float
    paired: int
    imbalance: int
    direction: str


@dataclass
class SymbolAuction:
    ticker: str
    noii: list[NoiiSnap] = field(default_factory=list)
    cross_price: float | None = None
    cross_shares: int | None = None
    cross_ts_ns: int | None = None


def parse_opening(path: str, tickers: set[str] | None = None,
                  progress=None) -> dict[str, SymbolAuction]:
    """Return per-ticker auction record. `tickers=None` keeps every symbol."""
    names: dict[int, str] = {}
    out: dict[str, SymbolAuction] = {}
    n_msgs = 0

    with gzip.open(path, "rb") as fh:
        buf = b""
        off = 0
        while True:
            if len(buf) - off < 3:
                chunk = fh.read(8 << 20)
                buf = buf[off:] + chunk
                off = 0
                if len(buf) < 3:
                    break
            ln = _u16.unpack_from(buf, off)[0]
            if len(buf) - off < 2 + ln:
                chunk = fh.read(8 << 20)
                buf = buf[off:] + chunk
                off = 0
                if len(buf) < 2 + ln:
                    break
                continue
            mtype = buf[off + 2]
            body = off + 3
            n_msgs += 1

            if mtype == MSG_DIRECTORY:
                locate = _u16.unpack_from(buf, body)[0]
                names[locate] = buf[body + 10:body + 18].decode().strip()
            elif mtype == MSG_NOII:
                (loc, _, ts, paired, imb, side, stock, far, near, ref,
                 ctype, _) = _noii.unpack_from(buf, body)
                if ctype == b"O":
                    tick = stock.decode().strip() or names.get(loc, "")
                    if not tickers or tick in tickers:
                        rec = out.setdefault(tick, SymbolAuction(tick))
                        rec.noii.append(NoiiSnap(
                            _ns(ts), near * _PX, far * _PX, ref * _PX,
                            paired, imb, side.decode()))
            elif mtype == MSG_CROSS:
                loc, _, ts, shares, stock, px, _, ctype = _cross.unpack_from(buf, body)
                if ctype == b"O":
                    tick = stock.decode().strip() or names.get(loc, "")
                    if not tickers or tick in tickers:
                        rec = out.setdefault(tick, SymbolAuction(tick))
                        rec.cross_price = px * _PX
                        rec.cross_shares = shares
                        rec.cross_ts_ns = _ns(ts)
                        if _ns(ts) > STOP_NS:
                            return out
            elif n_msgs % _TS_PROBE_EVERY == 0:
                ts_ns = _ns(buf[body + 4:body + 10])
                if progress:
                    progress(n_msgs, ts_ns)
                if ts_ns > STOP_NS:
                    return out
            off += 2 + ln
    return out
