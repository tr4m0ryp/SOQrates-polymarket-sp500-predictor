"""Fetcher for NYSE's free public Daily TAQ Order Imbalance sample files.

NYSE hosts a handful of full-day order-imbalance captures in an open directory
(no login, no key):

    https://ftp.nyse.com/Historical%20Data%20Samples/TAQ%20NYSE%20ORDER%20IMBALANCES/

This module lists what is published, streams a chosen day into ``CACHE/nyse_taq/``,
and hands the local file to the EXISTING CSV parser in ``replica.taq.parse``
(``parse_opening``) to recover the opening-auction (0930) indicative clearing
price stream + imbalance quantities for chosen symbols. That NYSE leg is the
replica's estimate of the official opening print for NYSE-listed names.

Caveats (real, load-bearing):
  * ONLY the specific published sample dates are free - NOT arbitrary dates.
    A date lookup that is not on the server raises ``NyseTaqSampleError``; this
    source will not cover an arbitrary quirk day. As of writing the directory
    holds two 2026 ``EQY_US_NYSE_REF_IMBALANCES_YYYYMMDD.gz`` files and one
    older uncompressed ``NYSE_IMBALANCES_20200909``.
  * Two file shapes coexist: gzipped ``*.gz`` and older uncompressed CSV with no
    extension. ``replica.taq.parse.parse_opening`` opens with ``gzip``, so an
    uncompressed download is gzip-normalised on the way into the cache; every
    cached file therefore ends in ``.gz`` and feeds the parser unchanged.
  * These are daily files (tens of MB). ``download`` streams to disk and skips
    if cached; ``imbalance_for_date`` then parses (the parser stops shortly
    after 09:30 ET, but the whole day must be on disk first).

Public surface: ``list_available``, ``download``, ``imbalance_for_date``,
``NyseTaqSampleError``, ``BASE_URL``.
"""
import gzip
import re
import shutil
import urllib.request

from spx.config import CACHE
from spx.replica.vendors.taq import parse as nyse_taq

BASE_URL = ("https://ftp.nyse.com/Historical%20Data%20Samples/"
            "TAQ%20NYSE%20ORDER%20IMBALANCES/")
_UA = {"User-Agent": "Mozilla/5.0"}
_DIR = CACHE / "nyse_taq"
_PREFIXES = ("EQY_US_NYSE_REF_IMBALANCES_", "NYSE_IMBALANCES_")

# nginx autoindex row:
#   <a href="NAME">NAME</a>   01-Jul-2026 00:09   18349213
# The DD-Mon-YYYY HH:MM date anchor keeps a match on its own row (so the
# "../" parent link and any line cannot bleed into the next).
_ROW = re.compile(
    r'<a href="([^"]+)">[^<]*</a>\s+\d{2}-[A-Za-z]{3}-\d{4}\s+\d{2}:\d{2}\s+(\d+)')


class NyseTaqSampleError(RuntimeError):
    pass


def _get(url: str, timeout: int = 90):
    req = urllib.request.Request(url, headers=_UA)
    return urllib.request.urlopen(req, timeout=timeout)


def _date_from_filename(name: str) -> str | None:
    """``EQY_US_NYSE_REF_IMBALANCES_20260401.gz`` -> ``2026-04-01`` (trailing
    ``YYYYMMDD`` before an optional ``.gz``; ``None`` if not that form)."""
    stem = name[:-3] if name.endswith(".gz") else name
    digits = stem[-8:]
    if len(digits) == 8 and digits.isdigit():
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
    return None


def _to_iso(s: str) -> str | None:
    """Normalise ``YYYY-MM-DD`` or bare ``YYYYMMDD`` to ISO; else ``None``."""
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return "-".join(m.groups())
    if len(s) == 8 and s.isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    return None


def list_available() -> list[dict]:
    """List the imbalance sample files published on the NYSE server.

    Returns dicts sorted by date: ``{filename, date, size_bytes, url}``. Every
    listed file exists (plain nginx directory listing, no purged siblings).
    ``date`` is the trailing ``YYYYMMDD`` parsed from the filename.
    """
    try:
        with _get(BASE_URL) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception as e:                               # noqa: BLE001
        raise NyseTaqSampleError(f"directory listing failed: {e}") from e

    out: list[dict] = []
    for name, size in _ROW.findall(html):
        if not name.startswith(_PREFIXES):
            continue
        out.append({
            "filename": name,
            "date": _date_from_filename(name),
            "size_bytes": int(size),
            "url": BASE_URL + name,
        })
    out.sort(key=lambda d: (d["date"] or "", d["filename"]))
    return out


def _resolve(date_or_filename: str) -> dict:
    """Map a date or filename to a published ``list_available`` entry.

    Accepts a raw sample filename / URL (used directly, no network), or a
    ``YYYY-MM-DD`` / ``YYYYMMDD`` date (looked up against the live listing).
    """
    s = date_or_filename.strip().rstrip("/")
    base = s.rsplit("/", 1)[-1]
    if base.startswith(_PREFIXES):
        return {"filename": base, "url": BASE_URL + base,
                "date": _date_from_filename(base)}
    iso = _to_iso(s)
    if iso:
        for entry in list_available():
            if entry["date"] == iso:
                return entry
        raise NyseTaqSampleError(
            f"no published NYSE TAQ imbalance sample for {iso} - only the "
            f"specific free sample dates are available, not arbitrary days")
    raise NyseTaqSampleError(
        f"cannot interpret {date_or_filename!r} as a date (YYYY-MM-DD / "
        f"YYYYMMDD) or a known sample filename")


def download(date_or_filename: str) -> str:
    """Stream one sample file into ``CACHE/nyse_taq/`` and return its local path.

    Skips the transfer if already cached. The cached file is always gzip so the
    parser (which uses ``gzip.open``) can consume it: an uncompressed source is
    recompressed on the way in, and its cache name gains a ``.gz`` suffix.
    """
    entry = _resolve(date_or_filename)
    src_name = entry["filename"]
    is_gz = src_name.endswith(".gz")
    cache_name = src_name if is_gz else src_name + ".gz"
    _DIR.mkdir(parents=True, exist_ok=True)
    dest = _DIR / cache_name
    if dest.exists():
        return str(dest)

    part = dest.with_suffix(dest.suffix + ".part")
    try:
        with _get(entry["url"], timeout=600) as r:
            if is_gz:
                with open(part, "wb") as fh:              # already gzip on wire
                    shutil.copyfileobj(r, fh, length=8 << 20)
            else:
                with gzip.open(part, "wb") as fh:         # normalise to gzip
                    shutil.copyfileobj(r, fh, length=8 << 20)
    except Exception as e:                                # noqa: BLE001
        part.unlink(missing_ok=True)
        raise NyseTaqSampleError(
            f"download of {src_name} failed: {e}") from e
    part.replace(dest)
    return str(dest)


def imbalance_for_date(date_or_filename: str, symbols,
                       until: str = "09:30:10") -> dict:
    """Download the day's sample then parse it with ``replica.taq.parse``.

    ``symbols`` is any iterable of tickers (e.g. ``["ELV", "USB"]``, matched
    case-insensitively) or ``None`` to keep every symbol. ``until`` bounds the
    source-time scan (default just past the 09:30 open). Returns the
    ``parse_opening`` mapping ``{symbol: NyseAuction}`` carrying the 0930
    opening-auction reference price and indicative clearing-price snapshots.
    """
    syms = None if symbols is None else {s.upper() for s in symbols}
    path = download(date_or_filename)
    return nyse_taq.parse_opening(path, symbols=syms, until=until)
