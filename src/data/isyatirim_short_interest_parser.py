"""Is Yatirim aciga satis PDF parser (D-132).

Kaynak: arastirma.isyatirim.com.tr gunluk PDF raporu (robots-safe).
URL format: .../Aciga_Satis_Raporu_DDMMYYYY.pdf

Tasarim:
- IO (_fetch_pdf / _load_cached) saf transform'dan (_parse_table) ayrilir.
- Testler sentetik PDF yerine mock BytesIO ya da onceden olusturulmus JSON
  cache dosyasi kullanir (pdfplumber IO'suz, tam test edilebilir).
- SPK yasagi doneminde sinyal agirligi 0'a yakin kalir; altyapi veri
  toplama icin hazir tutulur.

VERIFY (canli PDF ile): tablo basliginin tam metni, Ticker ve oran kolonlarinin
index'i. Ornek dosya repo'da yok; canli dogrulama execution'da.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import requests

from src.signals.thresholds import (
    SHORT_INTEREST_CACHE_DIR,
    SHORT_INTEREST_CACHE_FILE_TPL,
    SHORT_INTEREST_FETCH_TIMEOUT_SEC,
    SHORT_INTEREST_PDF_BASE_URL,
    SHORT_INTEREST_STALE_DAYS,
)

logger = logging.getLogger(__name__)

# Kolon baslik aday stringleri (VERIFY canli PDF ile)
_TABLE_HEADER_RE = re.compile(r"aciga\s*sati", re.IGNORECASE)
_TICKER_RE = re.compile(r"^[A-Z]{3,6}$")
_NUMBER_RE = re.compile(r"[\d.,]+")

# Tahmin edilen kolon pozisyonlari (VERIFY canli PDF ile)
_COL_TICKER = 0
_COL_SHORT_RATIO = 1   # % serbest dolasim
_COL_AMOUNT_USD = 2    # Tutar (USD milyon)


# ---------------------------------------------------------------------------
# Saf transform (IO yok, tam test edilebilir)
# ---------------------------------------------------------------------------

def _parse_float_tr(val: str | float | None) -> float | None:
    """TR-format ya da numeric string -> float. Ayristirilamazsa None."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        try:
            f = float(val)
        except (TypeError, ValueError):
            return None
        import math
        return None if math.isnan(f) else f
    s = str(val).strip().replace("%", "").strip()
    if not s:
        return None
    # TR format: "1.234,56" -> "1234.56"
    cleaned = re.sub(r"[^0-9,.\-]", "", s)
    if not cleaned or cleaned in {"-", ".", ","}:
        return None
    if "," in cleaned and "." in cleaned:
        # "1.234,56": nokta binlik, virgul ondalik
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_table_rows(
    rows: list[list[str]],
) -> dict[str, dict[str, float]]:
    """Ham satir listesi -> {ticker: {short_ratio, amount_usd}}.

    rows: Her satir bir liste (kolon degerleri string). Header ve bos
    satirlar otomatik atlanir. _TICKER_RE eslesmeyen satirlar elenir.
    """
    result: dict[str, dict[str, float]] = {}
    for row in rows:
        if len(row) <= _COL_TICKER:
            continue
        ticker_raw = str(row[_COL_TICKER]).strip()
        if not _TICKER_RE.match(ticker_raw):
            continue  # header / bos / non-ticker satir

        short_ratio: float | None = None
        amount_usd: float | None = None

        if len(row) > _COL_SHORT_RATIO:
            short_ratio = _parse_float_tr(row[_COL_SHORT_RATIO])
        if len(row) > _COL_AMOUNT_USD:
            amount_usd = _parse_float_tr(row[_COL_AMOUNT_USD])

        if short_ratio is None and amount_usd is None:
            continue  # veri yok, atla

        entry: dict[str, float] = {}
        if short_ratio is not None:
            entry["short_ratio"] = short_ratio
        if amount_usd is not None:
            entry["amount_usd"] = amount_usd
        result[ticker_raw] = entry

    return result


def extract_rows_from_pdf_bytes(pdf_bytes: bytes) -> list[list[str]]:
    """PDF bytes -> ham satir listesi (pdfplumber).

    pdfplumber yuklu degilse ImportError yukseltir (graceful handle ediyor).
    Tablo bulunamazsa bos liste doner.
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber yuklu degil: pip install pdfplumber")

    rows: list[list[str]] = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                # Aciga satis tabelasini bul (baslik kontrolu)
                header_row = table[0] if table else []
                header_text = " ".join(str(c) for c in header_row if c)
                if _TABLE_HEADER_RE.search(header_text) or any(
                    _TICKER_RE.match(str(c).strip()) for c in header_row
                ):
                    rows.extend(table)
                    break  # her sayfada bir tablo yeterli
            if rows:
                break  # ilk tablo sayfasinda bul
    return rows


# ---------------------------------------------------------------------------
# IO katmani
# ---------------------------------------------------------------------------

def _build_url(report_date: date) -> str:
    """PDF URL'ini tarih parametresi ile olustur."""
    return SHORT_INTEREST_PDF_BASE_URL.format(
        YYYY=report_date.strftime("%Y"),
        MM=report_date.strftime("%m"),
        DDMMYYYY=report_date.strftime("%d%m%Y"),
    )


def _cache_path(report_date: date, cache_dir: Path) -> Path:
    fname = SHORT_INTEREST_CACHE_FILE_TPL.format(
        YYYYMMDD=report_date.strftime("%Y%m%d"),
    )
    return cache_dir / fname


def _load_cache(report_date: date, cache_dir: Path) -> dict[str, dict[str, float]] | None:
    """Cache dosyasi varsa yukle. Bulunamazsa None."""
    p = _cache_path(report_date, cache_dir)
    if not p.exists():
        return None
    try:
        with p.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Cache okuma hatasi (%s): %s", p, exc)
        return None


def _save_cache(
    data: dict[str, dict[str, float]],
    report_date: date,
    cache_dir: Path,
) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    p = _cache_path(report_date, cache_dir)
    try:
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug("Cache yazildi: %s (%d ticker)", p, len(data))
    except Exception as exc:
        logger.warning("Cache yazma hatasi (%s): %s", p, exc)


def _fetch_pdf_bytes(url: str) -> bytes | None:
    """HTTP GET -> PDF bytes. Hata durumunda None + log."""
    try:
        resp = requests.get(url, timeout=SHORT_INTEREST_FETCH_TIMEOUT_SEC)
        if resp.status_code == 200 and resp.content[:4] == b"%PDF":
            return resp.content
        logger.warning("PDF fetch basarisiz: %s HTTP %d", url, resp.status_code)
        return None
    except Exception as exc:
        logger.warning("PDF fetch hatasi (%s): %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_short_interest(
    report_date: date | None = None,
    cache_dir: Path | str | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, dict[str, float]]:
    """Belirli gun icin aciga satis verisini cek.

    Oncelik sirasi:
    1. Cache dosyasi (force_refresh=False ise)
    2. PDF HTTP fetch + parse + cache yaz
    3. Hata durumunda: onceki gun dene (hafta sonu / tatil icin 3 gune kadar)
    4. Tum denemeler basarisizsa: {} doner + log

    Donus: {ticker: {"short_ratio": float, "amount_usd": float}}
    """
    if report_date is None:
        report_date = date.today()
    if cache_dir is None:
        cache_dir = Path(__file__).parent.parent.parent / SHORT_INTEREST_CACHE_DIR
    else:
        cache_dir = Path(cache_dir)

    # Takvim toleransi: hafta sonu / tatil -> geri git
    for days_back in range(SHORT_INTEREST_STALE_DAYS + 1):
        target = report_date - timedelta(days=days_back)

        if not force_refresh:
            cached = _load_cache(target, cache_dir)
            if cached is not None:
                logger.debug("Aciga satis cache hit: %s (%d ticker)", target, len(cached))
                return cached

        url = _build_url(target)
        pdf_bytes = _fetch_pdf_bytes(url)
        if pdf_bytes is None:
            logger.debug("PDF bulunamadi %s, bir gun geri deneniyor...", target)
            continue

        try:
            rows = extract_rows_from_pdf_bytes(pdf_bytes)
        except ImportError as exc:
            logger.error("pdfplumber eksik: %s", exc)
            return {}
        except Exception as exc:
            logger.warning("PDF parse hatasi (%s): %s", url, exc)
            continue

        data = parse_table_rows(rows)
        if data:
            _save_cache(data, target, cache_dir)
            logger.info(
                "Aciga satis yuklendi: %s, %d ticker (kaynak: %s)",
                target, len(data), url,
            )
            return data
        logger.warning("PDF parse edildi ama satir bulunamadi: %s", url)

    logger.warning("Aciga satis verisi alinamadi (tum denemeler basarisiz): %s", report_date)
    return {}


class IsyatirimShortInterestConnector:
    """Gunluk 1x fetch + JSON file cache.

    daily_update.py hook pattern: ForeignFlowConnector ile birebir ayni.
    """

    def __init__(
        self,
        cache_dir: Path | str | None = None,
    ) -> None:
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent.parent / SHORT_INTEREST_CACHE_DIR
        self.cache_dir = Path(cache_dir)

    def fetch(
        self,
        report_date: date | None = None,
        *,
        force_refresh: bool = False,
    ) -> dict[str, dict[str, float]]:
        """Aciga satis verisini cek. {ticker: {short_ratio, amount_usd}}."""
        return fetch_short_interest(
            report_date=report_date,
            cache_dir=self.cache_dir,
            force_refresh=force_refresh,
        )

    def get_short_ratios(
        self,
        report_date: date | None = None,
    ) -> dict[str, float]:
        """{ticker: short_ratio} haritasi (daily_update L5 pass icin)."""
        data = self.fetch(report_date=report_date)
        return {
            ticker: entry["short_ratio"]
            for ticker, entry in data.items()
            if "short_ratio" in entry
        }
