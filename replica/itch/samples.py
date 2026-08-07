"""Fetcher for Nasdaq's free public TotalView-ITCH 5.0 sample files.

Nasdaq hosts full-day ITCH captures in an open directory (no login, no key):

    https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/

Files are named ``MMDDYYYY.NASDAQ_ITCH50.gz`` (e.g. ``01302019.NASDAQ_ITCH50.gz``)
with a sibling ``.md5sum``. This module lists what is currently available,
streams a chosen day into ``CACHE/itch/``, and hands the local ``.gz`` to the
EXISTING binary parser in ``replica.itch`` (``parse_opening``) to recover NOII
snapshots + the opening-cross print for chosen symbols.

Caveats (real, load-bearing):
  * Sample dates are FIXED and SCATTERED (mostly month-end 2019, a little 2018 /
    2020) and Nasdaq ROTATES them - many listed dates keep only the ``.md5sum``
    after the ``.gz`` is purged. ``list_available`` returns only dates whose
    ``.gz`` still exists. This source will NOT cover arbitrary quirk days.
  * Each full-day file is 3.5-5.5 GB gzipped. ``download`` streams to disk and
    skips if cached; ``noii_for_date`` then parses (the parser itself stops at
    09:45 ET, but the whole file must be on disk first). Budget the transfer.
  * The ``NOII`` subfolder holds a delimited TEXT dump
    (``S######-v50-NOII.txt.gz``), NOT binary ITCH - it is listed by
    ``list_available(noii=True)`` for discovery but is NOT parseable by
    ``replica.itch`` and is not used by ``noii_for_date``.

Public surface: ``list_available``, ``download``, ``noii_for_date``,
``ItchSampleError``, ``BASE_URL``.
"""
import re
import shutil
import urllib.request

from config import CACHE
from replica.itch import parse as itch

BASE_URL = "https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/"
NOII_URL = BASE_URL + "NOII/"
_UA = {"User-Agent": "Mozilla/5.0"}
_ITCH_SUFFIX = ".NASDAQ_ITCH50.gz"
_ITCH_DIR = CACHE / "itch"

# " ... 4764426091 <A HREF="/ITCH/.../01302019.NASDAQ_ITCH50.gz">name</A>"
_ROW = re.compile(r'(\d+)\s+<A HREF="[^"]*/([^"/]+\.gz)"')


class ItchSampleError(RuntimeError):
    pass


def _get(url: str, timeout: int = 90):
    req = urllib.request.Request(url, headers=_UA)
    return urllib.request.urlopen(req, timeout=timeout)


def _date_from_filename(name: str) -> str | None:
    """``01302019.NASDAQ_ITCH50.gz`` -> ``2019-01-30`` (None if not that form)."""
    if not name.endswith(_ITCH_SUFFIX):
        return None
    stem = name[: -len(_ITCH_SUFFIX)]
    if len(stem) != 8 or not stem.isdigit():
        return None
    mm, dd, yyyy = stem[0:2], stem[2:4], stem[4:8]
    return f"{yyyy}-{mm}-{dd}"


def _filename_for(date_or_filename: str) -> str:
    """Normalise a date or filename to a canonical sample filename.

    Accepts ``YYYY-MM-DD``, bare ``MMDDYYYY``, or any ``*.gz`` filename
    (returned unchanged so a known NOII/text file can be fetched too).
    """
    s = date_or_filename.strip()
    if s.endswith(".gz"):
        return s.rsplit("/", 1)[-1]
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        yyyy, mm, dd = m.groups()
        return f"{mm}{dd}{yyyy}{_ITCH_SUFFIX}"
    if len(s) == 8 and s.isdigit():
        return f"{s}{_ITCH_SUFFIX}"
    raise ItchSampleError(
        f"cannot interpret {date_or_filename!r} as a date (YYYY-MM-DD / "
        f"MMDDYYYY) or a *.gz sample filename")


def _url_for(filename: str) -> str:
    return (NOII_URL if "-NOII." in filename else BASE_URL) + filename


def list_available(noii: bool = False) -> list[dict]:
    """List sample files whose payload actually exists on Nasdaq's server.

    Returns dicts sorted by date: ``{filename, date, size_bytes, url}``.
    ``date`` is ``None`` for the NOII text dumps (they carry no ISO date).
    Set ``noii=True`` to list the ``NOII/`` text subfolder instead of the
    binary full-day files. Entries left as ``.md5sum`` only are omitted.
    """
    url = NOII_URL if noii else BASE_URL
    try:
        with _get(url) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception as e:                               # noqa: BLE001
        raise ItchSampleError(f"directory listing failed: {e}") from e

    out: list[dict] = []
    for size, name in _ROW.findall(html):
        if name.endswith(".md5sum"):
            continue
        if noii:
            if "-NOII." not in name:
                continue
        # Binary listing: only the canonical `.NASDAQ_ITCH50.gz` files are
        # guaranteed ITCH-5.0 binary + date-parseable. The same folder also
        # carries other historical dumps (`S*-v50.txt.gz`, `itch50_*.gz`,
        # `tvagg.gz`) of unverified format - fetch those by exact filename
        # via `download(filename)` if you know one is binary ITCH.
        elif not name.endswith(_ITCH_SUFFIX):
            continue
        out.append({
            "filename": name,
            "date": _date_from_filename(name),
            "size_bytes": int(size),
            "url": _url_for(name),
        })
    out.sort(key=lambda d: (d["date"] or "", d["filename"]))
    return out


def download(date_or_filename: str, max_bytes: int | None = None) -> str:
    """Stream one sample file into ``CACHE/itch/`` and return its local path.

    Skips the transfer if the file is already fully cached. ``max_bytes`` caps
    the download for a connectivity smoke-test, leaving a ``.part`` file that is
    a TRUNCATED gzip (leading messages decompress, the tail does not) - do not
    feed a ``.part`` to the full-day parser.
    """
    filename = _filename_for(date_or_filename)
    _ITCH_DIR.mkdir(parents=True, exist_ok=True)
    dest = _ITCH_DIR / filename
    if dest.exists() and max_bytes is None:
        return str(dest)

    part = dest.with_suffix(dest.suffix + ".part")
    url = _url_for(filename)
    try:
        with _get(url, timeout=600) as r, open(part, "wb") as fh:
            if max_bytes is None:
                shutil.copyfileobj(r, fh, length=8 << 20)
            else:
                remaining = max_bytes
                while remaining > 0:
                    chunk = r.read(min(remaining, 8 << 20))
                    if not chunk:
                        break
                    fh.write(chunk)
                    remaining -= len(chunk)
    except Exception as e:                               # noqa: BLE001
        part.unlink(missing_ok=True)
        raise ItchSampleError(f"download of {filename} failed: {e}") from e

    if max_bytes is not None:
        return str(part)                                 # intentionally partial
    part.replace(dest)
    return str(dest)


def noii_for_date(date: str, symbols) -> dict:
    """Download the day's sample then parse it with ``replica.itch``.

    ``symbols`` is any iterable of tickers (e.g. ``["AAPL", "MSFT"]``) or
    ``None`` to keep every symbol. Returns the ``parse_opening`` mapping
    ``{ticker: SymbolAuction}`` carrying NOII snapshots + the opening cross.
    Raises ``ItchSampleError`` if the day's ``.gz`` is not published.
    """
    tickers = None if symbols is None else {s.upper() for s in symbols}
    path = download(date)
    return itch.parse_opening(path, tickers=tickers)
