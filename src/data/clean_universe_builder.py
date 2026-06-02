"""D-200: Survivorship-clean adjusted price panel builder.

Parse 3196 official price CSVs + 100460/461/471 corp-action ZIPs,
compute back-adjusted close + total-return index, extract PIT membership.
Pure helper -- no HTTP, no CLI. Called by scripts/build_clean_universe.py.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from src.signals.thresholds import (
    CLEAN_UNIVERSE_ADJ_PRICES,
    CLEAN_UNIVERSE_DIVIDEND_WITHHOLDING,
    CLEAN_UNIVERSE_META,
    CLEAN_UNIVERSE_PIT_MEMBERSHIP,
    COL_3196_BIST100,
    COL_3196_BIST30,
    COL_3196_CA_CODE,
    COL_3196_CLOSE,
    COL_3196_DATE,
    COL_3196_EXPECTED_COUNT,
    COL_3196_TICKER,
    COL_3196_VALUE_TL,
    COL_3196_VOLUME,
    COL_3196_VWAP,
)

_EPOCH = date(1900, 1, 1)

_SYMBOL_CANDS = ["KOD", "HISSE KODU", "HISSE", "SEMBOL", "TICKER", "MENKUL KIYMET KODU", "STOCK CODE"]
_DATE_CANDS = ["TARIH", "HAK KULLANIM TARIHI", "TEMETTÜ TARIHI", "EX DATE", "DATE", "EX-DATE"]
_RATIO_CANDS = ["ORAN", "ARTIS ORANI", "BEDELSIZ ORAN", "BEDELLI ORAN", "RATIO", "ORANI"]
_SUBPRICE_CANDS = ["HAK KULLANIM FIYATI", "ITIBARI DEGER", "NOMINAL", "SUB PRICE", "BEDELLI FIYAT", "HAK FIYATI"]
_DIVAMT_CANDS = ["NET TEMETTÜ", "BRÜT TEMETTÜ", "TEMETTÜ TUTARI", "DIVIDEND", "AMOUNT", "TUTAR", "NET TEMETTU", "BRUT TEMETTU"]
_ACTIONTYPE_CANDS = ["TIP", "ARTIS TURU", "ISLEM TURU", "TYPE", "ORAN TIPI"]


def _find_col(df_cols: list[str], candidates: list[str]) -> str | None:
    for cand in candidates:
        if cand in df_cols:
            return cand
    for col in df_cols:
        for cand in candidates:
            if cand in col:
                return col
    return None


def _to_float(val: str) -> float | None:
    s = str(val).strip().replace(",", ".")
    if not s or s.lower() in ("nan", "none", "-", ""):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_date(val: str) -> date | None:
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", ""):
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_3196_monthly(path: Path) -> pd.DataFrame:
    """Parse a single PP_GUNSONUFIYATHACIM.M.YYYYMM.csv file.

    Returns df: [date, symbol, close, vwap, value_tl, volume, bist100, bist30, ca_code].
    """
    for enc in ("utf-8", "utf-8-sig", "cp1254"):
        try:
            raw = pd.read_csv(
                path, sep=";", header=None, skiprows=2,
                dtype=str, encoding=enc, on_bad_lines="skip",
            )
            break
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError:
            raise ValueError(f"3196 CSV {path.name}: veri satiri bulunamadi (skiprows=2 sonrasi bos)")
    else:
        raise ValueError(f"3196 CSV kodlama hatasi: {path.name}")

    if raw.empty or raw.shape[1] < COL_3196_EXPECTED_COUNT:
        raise ValueError(
            f"3196 CSV {path.name}: {raw.shape[1]} sutun, beklenen >= {COL_3196_EXPECTED_COUNT}"
        )

    col_map = {
        "date": COL_3196_DATE,
        "symbol": COL_3196_TICKER,
        "bist100": COL_3196_BIST100,
        "bist30": COL_3196_BIST30,
        "ca_code": COL_3196_CA_CODE,
        "close": COL_3196_CLOSE,
        "vwap": COL_3196_VWAP,
        "value_tl": COL_3196_VALUE_TL,
        "volume": COL_3196_VOLUME,
    }
    subset = raw.iloc[:, list(col_map.values())].copy()
    subset.columns = list(col_map.keys())

    parsed = []
    bad = 0
    for _, row in subset.iterrows():
        try:
            d = _to_date(str(row["date"]))
            if d is None:
                bad += 1
                continue
            sym_raw = str(row["symbol"]).strip()
            if not sym_raw.endswith(".E"):
                continue  # only equities; skip warrants (.V), bonds, sukuk, etc.
            sym = sym_raw[:-2]
            close = _to_float(row["close"])
            if close is None:
                bad += 1
                continue
            b100_s = str(row["bist100"]).strip()
            b30_s = str(row["bist30"]).strip()
            b100 = int(b100_s) if b100_s not in ("", "nan") else 0
            b30 = int(b30_s) if b30_s not in ("", "nan") else 0
            ca_s = str(row["ca_code"]).strip()
            ca = None if ca_s in ("", "nan") else ca_s
            parsed.append({
                "date": d, "symbol": sym,
                "close": close,
                "vwap": _to_float(row["vwap"]),
                "value_tl": _to_float(row["value_tl"]),
                "volume": _to_float(row["volume"]),
                "bist100": b100, "bist30": b30, "ca_code": ca,
            })
        except (ValueError, TypeError):
            bad += 1
    if bad > 0:
        print(f"[clean-universe] {path.name}: {bad} gecersiz satir atildi")
    return pd.DataFrame(parsed)


def build_raw_price_panel(
    prices_dir: Path,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Concat all 3196 monthly CSVs in prices_dir whose month falls in [start_date, end_date]."""
    from src.data.bist_datastore_client import _extract_date_from_name

    csv_files = sorted(prices_dir.glob("*.csv"))
    if not csv_files:
        raise RuntimeError(
            f"HATA: {prices_dir} dizininde CSV bulunamadi. "
            f"3196 indirildi mi? (archive_datastore.py --type 3196)"
        )

    chunks = []
    included = 0
    for f in csv_files:
        fd = _extract_date_from_name(f.name)
        if fd is None:
            continue
        if fd < start_date or fd > end_date:
            continue
        df = parse_3196_monthly(f)
        if not df.empty:
            chunks.append(df)
            included += 1

    if not chunks:
        raise RuntimeError(
            f"HATA: {start_date}..{end_date} araliginda indirilmis CSV yok. "
            f"archive_datastore.py --type 3196 calistirin."
        )

    print(f"[clean-universe] 3196: {included} dosya okundu ({start_date}..{end_date})")
    panel = pd.concat(chunks, ignore_index=True)
    panel = panel[(panel["date"] >= start_date) & (panel["date"] <= end_date)]
    return panel.reset_index(drop=True)


def _parse_price_action_df(df: pd.DataFrame, filename: str) -> list[dict]:
    cols = list(df.columns)
    sym_col = _find_col(cols, _SYMBOL_CANDS)
    date_col = _find_col(cols, _DATE_CANDS)
    ratio_col = _find_col(cols, _RATIO_CANDS)
    if not (sym_col and date_col and ratio_col):
        raise ValueError(
            f"{filename}: kolon eslesemedi. Mevcut: {cols}\n"
            f"  Beklenen: sembol({_SYMBOL_CANDS[:3]}), tarih({_DATE_CANDS[:3]}), oran({_RATIO_CANDS[:3]})"
        )
    subprice_col = _find_col(cols, _SUBPRICE_CANDS)
    atype_col = _find_col(cols, _ACTIONTYPE_CANDS)

    rows = []
    for _, row in df.iterrows():
        sym = str(row[sym_col]).strip()
        if not sym or sym.lower() in ("nan", "none"):
            continue
        ex_date = _to_date(str(row[date_col]))
        if ex_date is None:
            continue
        ratio = _to_float(str(row[ratio_col]))
        if ratio is None:
            continue
        sub_price = _to_float(str(row[subprice_col])) if subprice_col else None
        action_type = "BEDELSIZ"
        if atype_col:
            at = str(row[atype_col]).strip().upper()
            if "BEDELLI" in at or "RIGHTS" in at or "PAID" in at:
                action_type = "BEDELLI"
        elif subprice_col and sub_price is not None:
            action_type = "BEDELLI"
        rows.append({
            "ex_date": ex_date, "symbol": sym, "action_type": action_type,
            "ratio": ratio, "sub_price": sub_price,
        })
    return rows


def _parse_dividend_df(df: pd.DataFrame, filename: str) -> list[dict]:
    cols = list(df.columns)
    sym_col = _find_col(cols, _SYMBOL_CANDS)
    date_col = _find_col(cols, _DATE_CANDS)
    amt_col = _find_col(cols, _DIVAMT_CANDS)
    if not (sym_col and date_col and amt_col):
        raise ValueError(
            f"{filename}: temettü kolon eslesemedi. Mevcut: {cols}\n"
            f"  Beklenen: sembol({_SYMBOL_CANDS[:3]}), tarih({_DATE_CANDS[:3]}), tutar({_DIVAMT_CANDS[:3]})"
        )
    rows = []
    for _, row in df.iterrows():
        sym = str(row[sym_col]).strip()
        if not sym or sym.lower() in ("nan", "none"):
            continue
        ex_date = _to_date(str(row[date_col]))
        if ex_date is None:
            continue
        amount = _to_float(str(row[amt_col]))
        if amount is None or amount <= 0:
            continue
        rows.append({"ex_date": ex_date, "symbol": sym, "amount_per_share": amount})
    return rows


def parse_corp_actions(ca_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse corp-action zip files in ca_dir.

    Returns: (price_actions, dividends) where:
      price_actions: [ex_date, symbol, action_type, ratio, sub_price]
      dividends: [ex_date, symbol, amount_per_share]
    """
    if not ca_dir.exists():
        raise RuntimeError(
            f"HATA: Corp-action dizini bulunamadi: {ca_dir}\n"
            f"  Cozum: python scripts/archive_datastore.py --phase 3 --proceed-faz3"
        )

    zip_files = sorted(ca_dir.glob("*.zip"))
    if not zip_files:
        raise RuntimeError(
            f"HATA: {ca_dir} icinde zip dosyasi yok. FAZ-3 tamamlandi mi?"
        )

    price_rows: list[dict] = []
    div_rows: list[dict] = []

    for zf_path in zip_files:
        is_div = "100471" in zf_path.name

        try:
            with zipfile.ZipFile(zf_path, "r") as zf:
                inner = next(
                    (n for n in zf.namelist()
                     if n.lower().endswith((".xlsx", ".xls", ".csv"))),
                    None,
                )
                if inner is None:
                    print(f"[clean-universe] {zf_path.name}: veri dosyasi yok → atlandi")
                    continue
                with zf.open(inner) as fh:
                    if inner.lower().endswith(".csv"):
                        df = pd.read_csv(fh, sep=None, engine="python", dtype=str)
                    else:
                        df = pd.read_excel(fh, dtype=str)
        except Exception as exc:
            print(f"[clean-universe] {zf_path.name}: okuma hatasi ({exc}) → atlandi")
            continue

        df.columns = [str(c).strip().upper() for c in df.columns]

        try:
            if is_div:
                rows = _parse_dividend_df(df, zf_path.name)
                div_rows.extend(rows)
            else:
                rows = _parse_price_action_df(df, zf_path.name)
                price_rows.extend(rows)
        except ValueError as exc:
            print(f"[clean-universe] {zf_path.name}: {exc}")

    price_actions = (
        pd.DataFrame(price_rows)
        if price_rows
        else pd.DataFrame(columns=["ex_date", "symbol", "action_type", "ratio", "sub_price"])
    )
    dividends = (
        pd.DataFrame(div_rows)
        if div_rows
        else pd.DataFrame(columns=["ex_date", "symbol", "amount_per_share"])
    )
    return price_actions, dividends


def compute_adjustment_factors(
    price_actions: pd.DataFrame,
    raw_panel: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, set[str]]:
    """Compute backward-cumulative adjustment factor breakpoints.

    Returns: (breakpoints_df[symbol, date, adj_factor], excluded_symbols).
    adj_factor for data row at date t = product of all event factors where ex_date > t.
    merge_asof(direction='backward') against breakpoints gives per-row factor.
    """
    excluded: set[str] = set()
    all_bp: list[dict] = []

    if price_actions.empty:
        return pd.DataFrame(columns=["symbol", "date", "adj_factor"]), excluded

    for symbol, grp in price_actions.groupby("symbol"):
        grp = grp.sort_values("ex_date").reset_index(drop=True)
        event_factors: list[tuple[date, float]] = []
        skip = False

        for _, row in grp.iterrows():
            atype = str(row["action_type"]).upper()
            ratio = float(row["ratio"])

            if atype == "BEDELSIZ":
                factor = 1.0 / (1.0 + ratio)
                event_factors.append((row["ex_date"], factor))

            elif atype == "BEDELLI":
                sub_price = row.get("sub_price", None)
                if pd.isna(sub_price) if sub_price is not None else True:
                    print(f"[clean-universe] {symbol}: bedelli sub_price yok -> DISLANIR")
                    excluded.add(symbol)
                    skip = True
                    break
                if raw_panel is None:
                    print(f"[clean-universe] {symbol}: bedelli icin raw_panel gerekli -> DISLANIR")
                    excluded.add(symbol)
                    skip = True
                    break
                ex_dt = row["ex_date"]
                sym_prices = raw_panel[raw_panel["symbol"] == symbol]
                prev = sym_prices[sym_prices["date"] < ex_dt]
                if prev.empty:
                    print(f"[clean-universe] {symbol}: bedelli oncesi fiyat yok -> DISLANIR")
                    excluded.add(symbol)
                    skip = True
                    break
                p_prev = float(prev.loc[prev["date"].idxmax(), "close"])
                if p_prev <= 0:
                    excluded.add(symbol)
                    skip = True
                    break
                n, m = 1.0, ratio
                terp = (n * p_prev + m * float(sub_price)) / (n + m)
                factor = terp / p_prev
                event_factors.append((ex_dt, factor))

        if skip or not event_factors:
            continue

        dates = [d for d, _ in event_factors]
        factors = [f for _, f in event_factors]
        n = len(factors)

        suffix = [1.0] * (n + 1)
        for i in range(n - 1, -1, -1):
            suffix[i] = factors[i] * suffix[i + 1]

        all_bp.append({"symbol": symbol, "date": _EPOCH, "adj_factor": suffix[0]})
        for i in range(n):
            all_bp.append({"symbol": symbol, "date": dates[i], "adj_factor": suffix[i + 1]})

    bp_df = (
        pd.DataFrame(all_bp)
        if all_bp
        else pd.DataFrame(columns=["symbol", "date", "adj_factor"])
    )
    return bp_df, excluded


def apply_back_adjustment(
    raw_panel: pd.DataFrame,
    adj_factors: pd.DataFrame,
    excluded_symbols: set[str],
) -> pd.DataFrame:
    """Merge adjustment breakpoints into raw_panel and compute adjusted_close/vwap.

    Processes per-symbol to avoid merge_asof global sort constraint.
    """
    panel = raw_panel[~raw_panel["symbol"].isin(excluded_symbols)].copy()

    if adj_factors.empty:
        panel["adj_factor"] = 1.0
        panel["adjusted_close"] = panel["close"]
        panel["adjusted_vwap"] = panel["vwap"]
        return panel.reset_index(drop=True)

    bp_by_sym = {sym: grp for sym, grp in adj_factors.groupby("symbol")}
    results = []

    for sym, sym_panel in panel.groupby("symbol", sort=False):
        sym_panel = sym_panel.copy()
        sym_panel["_date_ord"] = pd.to_datetime(sym_panel["date"]).astype("int64")
        sym_panel = sym_panel.sort_values("_date_ord").reset_index(drop=True)

        if sym in bp_by_sym:
            sym_bp = bp_by_sym[sym].copy()
            sym_bp["_date_ord"] = pd.to_datetime(sym_bp["date"]).astype("int64")
            sym_bp = sym_bp.sort_values("_date_ord").reset_index(drop=True)
            sym_panel = pd.merge_asof(
                sym_panel, sym_bp[["_date_ord", "adj_factor"]],
                on="_date_ord", direction="backward",
            )
        else:
            sym_panel["adj_factor"] = 1.0

        sym_panel.drop(columns=["_date_ord"], inplace=True)
        results.append(sym_panel)

    merged = pd.concat(results, ignore_index=True) if results else panel.iloc[:0].copy()
    merged["adj_factor"] = merged["adj_factor"].fillna(1.0)
    merged["adjusted_close"] = merged["close"] * merged["adj_factor"]
    merged["adjusted_vwap"] = merged["vwap"] * merged["adj_factor"]
    return merged


def compute_total_return_index(
    adj_panel: pd.DataFrame,
    dividends: pd.DataFrame,
    withholding: float = CLEAN_UNIVERSE_DIVIDEND_WITHHOLDING,
) -> pd.DataFrame:
    """Compute total-return index (gross and net) for each symbol.

    TR_t = TR_{t-1} * (P_t + D_t) / P_{t-1}.
    D is the actual dividend; both P values are adjusted_close (price-return basis).
    Returns [date, symbol, tr_index_gross, tr_index_net].
    """
    if adj_panel.empty:
        return pd.DataFrame(columns=["date", "symbol", "tr_index_gross", "tr_index_net"])

    panel = adj_panel[["date", "symbol", "adjusted_close"]].copy()
    panel = panel.sort_values(["symbol", "date"]).reset_index(drop=True)

    if not dividends.empty:
        div = dividends.rename(columns={"ex_date": "date"}).copy()
        panel = panel.merge(
            div[["date", "symbol", "amount_per_share"]],
            on=["date", "symbol"], how="left",
        )
    else:
        panel["amount_per_share"] = 0.0

    panel["amount_per_share"] = panel["amount_per_share"].fillna(0.0)
    panel["div_net"] = panel["amount_per_share"] * (1.0 - withholding)

    tr_rows = []
    for symbol, grp in panel.groupby("symbol"):
        grp = grp.sort_values("date").reset_index(drop=True)
        prices = grp["adjusted_close"].to_numpy(dtype=float)
        divs_gross = grp["amount_per_share"].to_numpy(dtype=float)
        divs_net = grp["div_net"].to_numpy(dtype=float)
        k = len(grp)
        tr_g = [1.0] * k
        tr_n = [1.0] * k
        for i in range(1, k):
            if prices[i - 1] > 0:
                tr_g[i] = tr_g[i - 1] * (prices[i] + divs_gross[i]) / prices[i - 1]
                tr_n[i] = tr_n[i - 1] * (prices[i] + divs_net[i]) / prices[i - 1]
            else:
                tr_g[i] = tr_g[i - 1]
                tr_n[i] = tr_n[i - 1]
        for i, d in enumerate(grp["date"]):
            tr_rows.append({
                "date": d, "symbol": symbol,
                "tr_index_gross": tr_g[i], "tr_index_net": tr_n[i],
            })

    return pd.DataFrame(tr_rows)


def extract_pit_membership(raw_panel: pd.DataFrame) -> pd.DataFrame:
    """Extract PIT BIST100/30 membership from raw panel col-11/12 flags."""
    mem = raw_panel[["date", "symbol", "bist100", "bist30"]].copy()
    mem = mem.rename(columns={"bist100": "in_bist100", "bist30": "in_bist30"})
    mem["in_bist100"] = mem["in_bist100"].astype(bool)
    mem["in_bist30"] = mem["in_bist30"].astype(bool)
    return mem.reset_index(drop=True)


def content_hash(df: pd.DataFrame) -> str:
    """Deterministic SHA256, sort by [symbol, date]. Mirrors snapshot.py pattern."""
    canon = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    csv_bytes = canon.to_csv(index=False, float_format="%.10g").encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def build_and_freeze_adjusted_panel(
    prices_dir: Path,
    ca_dir: Path,
    output_root: Path,
    start_date: date,
    end_date: date,
    force_rebuild: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """Idempotent: if meta hash matches existing parquet, loads and returns.

    Returns: (adj_panel_df, meta_dict).
    adj_panel has: [date, symbol, close, adjusted_close, adjusted_vwap, adj_factor, bist100, bist30, ...]
    Also saves pit_membership parquet and _meta.json.
    """
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    meta_path = output_root / CLEAN_UNIVERSE_META
    prices_path = output_root / CLEAN_UNIVERSE_ADJ_PRICES
    membership_path = output_root / CLEAN_UNIVERSE_PIT_MEMBERSHIP

    if not force_rebuild and meta_path.exists() and prices_path.exists():
        existing_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        existing_df = pd.read_parquet(prices_path)
        if content_hash(existing_df) == existing_meta.get("content_hash_prices"):
            print(f"[clean-universe] Meta hash eslesiyor -> yukle, yeniden kurma yok")
            return existing_df, existing_meta

    raw_panel = build_raw_price_panel(prices_dir, start_date, end_date)
    price_actions, dividends = parse_corp_actions(ca_dir)

    adj_factors, excluded = compute_adjustment_factors(price_actions, raw_panel)
    if excluded:
        print(f"[clean-universe] DISLANAN semboller ({len(excluded)}): {sorted(excluded)}")

    adj_panel = apply_back_adjustment(raw_panel, adj_factors, excluded)
    tr_panel = compute_total_return_index(adj_panel, dividends)
    membership = extract_pit_membership(raw_panel)

    if not tr_panel.empty:
        adj_panel = adj_panel.merge(
            tr_panel[["date", "symbol", "tr_index_gross", "tr_index_net"]],
            on=["date", "symbol"], how="left",
        )

    _run_d185_checks(adj_panel)

    adj_panel.to_parquet(prices_path, index=False)
    membership.to_parquet(membership_path, index=False)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {
        "schema_version": 1,
        "directive": "D-200",
        "timestamp_utc": ts,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "n_symbols": int(adj_panel["symbol"].nunique()),
        "n_dates": int(adj_panel["date"].nunique()),
        "content_hash_prices": content_hash(adj_panel),
        "content_hash_membership": content_hash(membership),
        "excluded_symbols_count": len(excluded),
        "excluded_symbols": sorted(excluded),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"[clean-universe] Meta -> {meta_path}")
    return adj_panel, meta


def _run_d185_checks(adj_panel: pd.DataFrame) -> None:
    """D-185 validation: survivorship, BIST100 count, zero-price."""
    syms = set(adj_panel["symbol"].unique())
    for s in ("KOZAA", "IPEKE"):
        if s in syms:
            print(f"[clean-universe] D185-OK: {s} panelde mevcut (survivorship-clean)")
        else:
            print(f"[clean-universe] D185-UYARI: {s} panelde YOK")

    if "adjusted_close" in adj_panel.columns:
        zeros = (adj_panel["adjusted_close"] <= 0).sum()
        if zeros > 0:
            print(f"[clean-universe] D185-UYARI: adjusted_close <= 0 olan {zeros} satir")

    if "in_bist100" in adj_panel.columns or "bist100" in adj_panel.columns:
        b100_col = "in_bist100" if "in_bist100" in adj_panel.columns else "bist100"
        daily_count = adj_panel.groupby("date")[b100_col].sum()
        out_of_range = ((daily_count < 80) | (daily_count > 120)).sum()
        if out_of_range > 0:
            print(f"[clean-universe] D185-UYARI: {out_of_range} gunde BIST100 uye sayisi 80-120 disinda")
        else:
            print(f"[clean-universe] D185-OK: BIST100 uye sayisi tutarli (80-120 araliginda)")
