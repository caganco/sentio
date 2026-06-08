"""VIOP SSF monthly OI panel builder — DataStore 3208 input.

Reads pre-downloaded DataStore 3208 files from data/viop/ and returns
a ViOpMonthlyPanel with front-month OI aggregated to month-end.
Downloading is out of scope; loader raises DataUnavailableError when files absent.
"""
from __future__ import annotations

import io
import logging
import warnings
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_SSF_CONTRACT_TYPE = "D_EQ_FPD"

# Maps raw CSV column headers (Turkish chars + spaces) to normalized names.
_COL_NORM: dict[str, str] = {
    "TARIH": "TARIH",
    "SÖZLEŞME TİPİ": "SOZLESME_TIPI",
    "SOZLESME TIPI": "SOZLESME_TIPI",
    "SOZLESME_TIPI": "SOZLESME_TIPI",
    "DAYANAK VARLIĞI": "DAYANAK_VARLIK",
    "DAYANAK VARLIK": "DAYANAK_VARLIK",
    "DAYANAK_VARLIK": "DAYANAK_VARLIK",
    "DAYANAK VARLIK KODU": "DAYANAK_VARLIK",
    "VADE TARİHİ": "VADE_TARIHI",
    "VADE TARIHI": "VADE_TARIHI",
    "VADE_TARIHI": "VADE_TARIHI",
    "UZLAŞMA FİYATI": "UZLASMA_FIYATI",
    "UZLASMA FIYATI": "UZLASMA_FIYATI",
    "AĞIRLIKLI ORTALAMA FİYAT": "AGIRLIKLI_ORT_FIYAT",
    "AGIRLIKLI ORTALAMA FIYAT": "AGIRLIKLI_ORT_FIYAT",
    "İŞLEM HACMİ": "ISLEM_HACMI",
    "ISLEM HACMI": "ISLEM_HACMI",
    "İŞLEM MİKTARI": "ISLEM_MIKTARI",
    "ISLEM MIKTARI": "ISLEM_MIKTARI",
    "İŞLEM SAYISI": "ISLEM_SAYISI",
    "ISLEM SAYISI": "ISLEM_SAYISI",
    "AÇIK POZİSYON": "ACIK_POZISYON",
    "ACIK POZISYON": "ACIK_POZISYON",
    "AÇIK POZİSYON DEĞİŞİMİ": "ACIK_POZISYON_DEGISIMI",
    "ACIK POZISYON DEGISIMI": "ACIK_POZISYON_DEGISIMI",
    "PRİM HACMİ": "PRIM_HACMI",
    "PRIM HACMI": "PRIM_HACMI",
}

_SCHEMA_PRE = "pre_redenomination"
_SCHEMA_POST = "post_redenomination"
_SCHEMA_AHT = "aht"

# 2020-07-27: index redenomination (2 zeros dropped from index futures prices).
# SSF (D_EQ_FPD) values unaffected, but column names may shift around this date.
_REDENOMINATION_DATE = pd.Timestamp("2020-07-27")


class DataUnavailableError(FileNotFoundError):
    """No 3208 data files found under the expected directory."""


class EmptyFilterError(ValueError):
    """D_EQ_FPD filter left zero rows; check source CSV content."""


class InsufficientDataError(ValueError):
    """Valid months after breadth exclusion are below the Stage-0 minimum (36)."""


@dataclass
class ViOpMonthlyPanel:
    """Monthly front-month OI panel indexed by (year_month, ticker)."""

    data: pd.DataFrame  # MultiIndex (Period[M], str); cols: OI, ISLEM_HACMI, ISLEM_MIKTARI
    schema_log: list[str] = field(default_factory=list)
    excluded_months: list[str] = field(default_factory=list)
    date_range: tuple[str, str] = ("", "")
    n_tickers: int = 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Map raw header names to normalized underscore names; warn on unknowns."""
    renamed: dict[str, str] = {}
    unknown: list[str] = []
    normalized_values = set(_COL_NORM.values())
    for col in df.columns:
        key = col.strip()
        if key in _COL_NORM:
            renamed[col] = _COL_NORM[key]
        elif key not in normalized_values:
            unknown.append(col)
    if unknown:
        warnings.warn(
            f"viop_loader: unrecognized columns (kept as-is): {unknown}",
            stacklevel=3,
        )
        logger.warning("viop_loader: unrecognized columns: %s", unknown)
    return df.rename(columns=renamed)


def _detect_schema_version(ref_date: pd.Timestamp, cols: list[str]) -> str:
    """Return 'pre_redenomination' | 'post_redenomination' | 'aht'."""
    if "ACIK_POZISYON_DEGISIMI" in cols:
        return _SCHEMA_AHT
    if ref_date < _REDENOMINATION_DATE:
        return _SCHEMA_PRE
    return _SCHEMA_POST


def _parse_csv_bytes(data: bytes) -> pd.DataFrame:
    """Parse one 3208 CSV with BIST standard encoding."""
    return pd.read_csv(
        io.BytesIO(data),
        encoding="windows-1254",
        sep=";",
        thousands=".",
        decimal=",",
        dtype=str,
    )


def _load_file(path: Path) -> pd.DataFrame:
    """Load one CSV or ZIP file, return empty DataFrame on failure."""
    if path.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(path) as zf:
                csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                if not csv_names:
                    logger.warning("viop_loader: zip %s contains no CSV", path.name)
                    return pd.DataFrame()
                frames: list[pd.DataFrame] = [_parse_csv_bytes(zf.read(n)) for n in csv_names]
                return pd.concat(frames, ignore_index=True)
        except Exception as exc:
            logger.error("viop_loader: failed to read zip %s — %s", path.name, exc)
            return pd.DataFrame()
    if path.suffix.lower() in {".csv", ".txt"}:
        try:
            return _parse_csv_bytes(path.read_bytes())
        except Exception as exc:
            logger.error("viop_loader: failed to read csv %s — %s", path.name, exc)
            return pd.DataFrame()
    logger.warning("viop_loader: skipping unsupported file type %s", path.name)
    return pd.DataFrame()


def _discover_files(data_dir: Path) -> list[Path]:
    """Recursively collect CSV and ZIP files under data_dir."""
    return sorted(data_dir.rglob("*.csv")) + sorted(data_dir.rglob("*.zip"))


def _to_float_series(s: pd.Series) -> pd.Series:
    """Convert Turkish-formatted number strings (. thousands, , decimal) to float."""
    return (
        s.astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
    )


def _parse_tarih(s: pd.Series) -> pd.Series:
    """Parse TARIH column; handles DD.MM.YYYY and YYYY-MM-DD."""
    parsed = pd.to_datetime(s, format="%d.%m.%Y", errors="coerce")
    mask = parsed.isna()
    if mask.any():
        fallback = pd.to_datetime(s[mask], format="%Y-%m-%d", errors="coerce")
        parsed = parsed.copy()
        parsed[mask] = fallback
    return parsed


def _parse_vade(s: pd.Series) -> pd.Series:
    """Parse VADE_TARIHI to Period[M]; supports YYYYMM and YYYY-MM."""
    clean = s.astype(str).str.strip()
    # Try YYYYMM (6 chars)
    six_char = clean.str.len() == 6
    result = pd.Series(pd.NaT, index=s.index, dtype="object")
    if six_char.any():
        parsed_6 = pd.to_datetime(
            clean[six_char] + "01", format="%Y%m%d", errors="coerce"
        ).dt.to_period("M")
        result[six_char] = parsed_6
    # Fallback: YYYY-MM
    other = ~six_char
    if other.any():
        parsed_other = pd.to_datetime(
            clean[other], format="%Y-%m", errors="coerce"
        ).dt.to_period("M")
        result[other] = parsed_other
    return result


def _build_monthly_panel(
    df: pd.DataFrame,
    schema_log: list[str],
    excluded_months: list[str],
) -> pd.DataFrame:
    """Core aggregation: daily rows → month-end front-month OI per ticker."""
    df = df.copy()

    df["TARIH"] = _parse_tarih(df["TARIH"])
    df = df.dropna(subset=["TARIH"])
    df["year_month"] = df["TARIH"].dt.to_period("M")

    df["VADE_YM"] = _parse_vade(df["VADE_TARIHI"])
    df = df.dropna(subset=["VADE_YM"])

    for num_col in ("ACIK_POZISYON", "ISLEM_HACMI", "ISLEM_MIKTARI"):
        if num_col in df.columns:
            df[num_col] = _to_float_series(df[num_col])

    # Log schema version changes
    prev_schema: str | None = None
    for ym, grp in df.groupby("year_month", sort=True):
        first_date = pd.Timestamp(grp["TARIH"].min())
        schema = _detect_schema_version(first_date, list(grp.columns))
        if schema != prev_schema:
            entry = f"{ym}: schema={schema}"
            schema_log.append(entry)
            logger.info("viop_loader: %s", entry)
            prev_schema = schema

    result_rows: list[dict[str, object]] = []

    for (ym, ticker), grp in df.groupby(["year_month", "ticker"], sort=True):
        current_period = pd.Period(ym, freq="M")

        # Last trading day in this month for this ticker
        last_date = grp["TARIH"].max()
        last_day = grp[grp["TARIH"] == last_date]

        # Exclude contracts expiring in current month or earlier (roll + expiry exclusion)
        future = last_day[last_day["VADE_YM"] > current_period]
        if future.empty:
            excluded_months.append(f"{ym}-{ticker}")
            continue

        # Front-month = minimum future expiry period
        front_ym = future["VADE_YM"].min()
        front = future[future["VADE_YM"] == front_ym]

        oi = float(front["ACIK_POZISYON"].iloc[0]) if "ACIK_POZISYON" in front.columns else float("nan")
        hacmi = float(front["ISLEM_HACMI"].sum()) if "ISLEM_HACMI" in front.columns else 0.0
        miktari = float(front["ISLEM_MIKTARI"].sum()) if "ISLEM_MIKTARI" in front.columns else 0.0

        result_rows.append({
            "year_month": current_period,
            "ticker": str(ticker),
            "OI": oi,
            "ISLEM_HACMI": hacmi,
            "ISLEM_MIKTARI": miktari,
        })

    if not result_rows:
        return pd.DataFrame(
            columns=["year_month", "ticker", "OI", "ISLEM_HACMI", "ISLEM_MIKTARI"]
        ).set_index(["year_month", "ticker"])

    out = pd.DataFrame(result_rows).set_index(["year_month", "ticker"])
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_viop_monthly_panel(
    data_dir: Path | str,
    start: str = "2016-01",
    end: str | None = None,
) -> ViOpMonthlyPanel:
    """Load 3208 files into a monthly front-month OI panel.

    Args:
        data_dir: Root dir of pre-downloaded 3208 CSV/ZIP files.
        start: First YYYY-MM to include.
        end: Last YYYY-MM to include; None means all available.

    Returns:
        ViOpMonthlyPanel with month-end front-month OI.

    Raises:
        DataUnavailableError: No files found under data_dir.
        EmptyFilterError: No D_EQ_FPD rows in files.
    """
    root = Path(data_dir)
    files = _discover_files(root)
    if not files:
        raise DataUnavailableError(
            f"No CSV/ZIP files found under {root}. "
            "Download DataStore 3208 files before running this loader."
        )

    frames: list[pd.DataFrame] = []
    for f in files:
        raw = _load_file(f)
        if raw.empty:
            continue
        frames.append(_normalize_cols(raw))

    if not frames:
        raise DataUnavailableError(f"All files under {root} parsed to empty DataFrames.")

    df = pd.concat(frames, ignore_index=True)

    required = {"SOZLESME_TIPI", "DAYANAK_VARLIK", "TARIH", "VADE_TARIHI"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise EmptyFilterError(
            f"Required columns missing after normalization: {sorted(missing_cols)}. "
            "Verify source CSV format and column normalization map."
        )

    df = df[df["SOZLESME_TIPI"].astype(str).str.strip() == _SSF_CONTRACT_TYPE].copy()
    if df.empty:
        raise EmptyFilterError(
            f"No rows with SOZLESME_TIPI == '{_SSF_CONTRACT_TYPE}'. "
            "Source files may contain only index/currency futures."
        )

    df["ticker"] = (
        df["DAYANAK_VARLIK"].astype(str).str.strip().str.replace(r"\.E$", "", regex=True)
    )

    schema_log: list[str] = []
    excluded_months: list[str] = []

    monthly = _build_monthly_panel(df, schema_log, excluded_months)

    if not monthly.empty:
        start_period = pd.Period(start, freq="M")
        idx_months = monthly.index.get_level_values("year_month")
        mask = idx_months >= start_period
        if end is not None:
            mask = mask & (idx_months <= pd.Period(end, freq="M"))
        monthly = monthly[mask]

    if not monthly.empty:
        nan_frac = float(monthly["OI"].isna().mean())
        if nan_frac >= 0.15:
            warnings.warn(
                f"viop_loader: OI NaN fraction {nan_frac:.1%} >= 15% — "
                "check for missing monthly files or roll-convention mismatch.",
                stacklevel=2,
            )
            logger.warning("viop_loader: high OI NaN rate %.1f%%", nan_frac * 100)

    idx = monthly.index.get_level_values("year_month") if not monthly.empty else pd.PeriodIndex([], freq="M")
    n_tickers = len(monthly.index.get_level_values("ticker").unique()) if not monthly.empty else 0
    date_range: tuple[str, str] = (
        (str(idx.min()), str(idx.max())) if len(idx) > 0 else ("", "")
    )

    return ViOpMonthlyPanel(
        data=monthly,
        schema_log=schema_log,
        excluded_months=excluded_months,
        date_range=date_range,
        n_tickers=n_tickers,
    )
