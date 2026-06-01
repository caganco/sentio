"""D-189 — SAF Per-Trade Edge İzolasyonu (D-186 disiplini).

Mevcut 348-trade bist50_2yr_v2 verisine D-186 lensini uygular:
  - Per-trade REEL getiri (TÜFE deflasyonu)
  - Per-trade XU100-GÖRELI getiri
  - ADİL-NULL testi (random giriş, aynı SL/TP/max-hold kuralları)
  - ATRİBÜSYON (kapalı işlem P&L vs portföy kazancı)
  - FROZEN VERDICT (§4 karar kuralı)

Veri kaynakları (offline snapshot, ağ bağlantısı gerekmez):
  data/snapshots/exposure_d187_xu100.parquet    — XU100 günlük kapanış
  data/snapshots/exposure_d187_tufe.parquet     — TÜFE kümülatif endeks (base=1.0)
  data/snapshots/faz0_v2_prices_2024-01-01_2026-04-30.parquet  — hisse fiyatları

BKSI.: src/ dosyalarına DOKUNULMAZ. Sadece TUFE_UNAVAILABLE + eşik sabitleri import edilir.

Kullanım:
  python scripts/d189_edge_isolation.py
  python scripts/d189_edge_isolation.py --null-iters 200  # hızlı test
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtest.metrics import TUFE_UNAVAILABLE  # noqa: E402
from src.signals.thresholds import EXIT_PROFIT_TARGET, EXIT_STOP_LOSS  # noqa: E402

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
TRADES_CSV = Path("reports/backtest/exploratory/bist50_2yr_v2/trades.csv")
SUMMARY_JSON = Path("reports/backtest/exploratory/bist50_2yr_v2/summary.json")
OUTPUT_DIR = Path("reports/backtest/d189_edge_analysis")

SNAP_XU100 = Path("data/snapshots/exposure_d187_xu100.parquet")
SNAP_TUFE = Path("data/snapshots/exposure_d187_tufe.parquet")
SNAP_PRICES = Path("data/snapshots/faz0_v2_prices_2024-01-01_2026-04-30.parquet")

SL_FACTOR: float = EXIT_STOP_LOSS      # 0.92 = -8% stop
TP_FACTOR: float = EXIT_PROFIT_TARGET  # 1.20 = +20% profit
COMMISSION: float = 0.001              # %0.1 round-trip (adil-null için)
NULL_MAX_HOLD_DAYS: int = 30           # adil-null max tutma süresi
NULL_ENTRY_CUTOFF: str = "2026-03-01"  # 60 gün buffer (çıkış simülasyonu için)
RANDOM_SEED: int = 42

DECISION_PCTILE_MIN: float = 0.95  # §4 frozen: >%95 dilim gerekli


# ---------------------------------------------------------------------------
# Veri yükleme
# ---------------------------------------------------------------------------

def load_trades() -> pd.DataFrame:
    df = pd.read_csv(TRADES_CSV, parse_dates=["date", "entry_date"])
    df = df[df["type"] == "SELL"].copy()
    df = df.rename(columns={"date": "exit_date", "price": "exit_price"})
    df["holding_days"] = (df["exit_date"] - df["entry_date"]).dt.days
    assert len(df) > 0, "trades.csv boş"
    return df.reset_index(drop=True)


def load_xu100() -> pd.Series:
    df = pd.read_parquet(SNAP_XU100)
    s = pd.to_datetime(df["date"])
    vals = df["value"].values
    return pd.Series(vals, index=s, name="xu100").sort_index()


def load_tufe() -> pd.Series | None:
    if not SNAP_TUFE.exists():
        return None
    df = pd.read_parquet(SNAP_TUFE)
    s = pd.to_datetime(df["date"])
    return pd.Series(df["value"].values, index=s, name="tufe").sort_index()


def load_prices() -> dict[str, pd.Series]:
    """Hisse fiyatlarını yükle: {SYMBOL: daily_close_series}"""
    if not SNAP_PRICES.exists():
        return {}
    df = pd.read_parquet(SNAP_PRICES)
    df["date"] = pd.to_datetime(df["date"])
    result = {}
    for sym, grp in df.groupby("symbol"):
        s = grp.set_index("date")["close"].sort_index()
        result[str(sym)] = s
    return result


def load_summary() -> dict:
    with open(SUMMARY_JSON, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Per-trade hesaplamaları
# ---------------------------------------------------------------------------

def _ret_over(series: pd.Series, entry_date, exit_date) -> float:
    """İki tarih arasındaki geometrik getiri (asof lookup)."""
    e = float(series.asof(pd.Timestamp(entry_date)))
    x = float(series.asof(pd.Timestamp(exit_date)))
    if not (math.isfinite(e) and math.isfinite(x)) or e <= 0:
        return float("nan")
    return x / e - 1.0


def compute_per_trade_metrics(
    trades: pd.DataFrame,
    tufe: pd.Series | None,
    xu100: pd.Series,
) -> pd.DataFrame:
    df = trades.copy()
    reel_vals, cum_infs, xu100_rets, rel_vals = [], [], [], []

    for _, row in df.iterrows():
        # XU100-relative (geometrik excess)
        xu = _ret_over(xu100, row["entry_date"], row["exit_date"])
        if math.isfinite(xu):
            xu100_rets.append(round(xu, 6))
            # D-186 formülü: (1 + nominal) / (1 + xu100_ret) - 1
            rel_vals.append(round((1.0 + row["pnl_pct"]) / (1.0 + xu) - 1.0, 6))
        else:
            xu100_rets.append(float("nan"))
            rel_vals.append(float("nan"))

        # TÜFE reel getiri
        if tufe is not None:
            t_e = float(tufe.asof(pd.Timestamp(row["entry_date"])))
            t_x = float(tufe.asof(pd.Timestamp(row["exit_date"])))
            if math.isfinite(t_e) and math.isfinite(t_x) and t_e > 0:
                cum_inf = t_x / t_e - 1.0
                reel = (1.0 + row["pnl_pct"]) / (1.0 + cum_inf) - 1.0
                cum_infs.append(round(cum_inf, 6))
                reel_vals.append(round(reel, 6))
            else:
                cum_infs.append(float("nan"))
                reel_vals.append(TUFE_UNAVAILABLE)
        else:
            cum_infs.append(float("nan"))
            reel_vals.append(TUFE_UNAVAILABLE)

    df["xu100_ret"] = xu100_rets
    df["rel_pnl_pct"] = rel_vals
    df["cum_inf"] = cum_infs
    df["reel_pnl_pct"] = reel_vals
    return df


def compute_expectancy(df: pd.DataFrame) -> dict:
    # Nominal (komisyon dahil, zaten trades.csv'de)
    pnl = df["pnl_pct"].values
    win_rate = float((pnl > 0).mean())
    avg_nom = float(np.mean(pnl))
    avg_win_nom = float(np.mean(pnl[pnl > 0])) if (pnl > 0).any() else 0.0
    avg_loss_nom = float(np.mean(pnl[pnl < 0])) if (pnl < 0).any() else 0.0

    # XU100-relative
    rel = df["rel_pnl_pct"].dropna().values
    avg_rel = float(np.mean(rel)) if len(rel) > 0 else float("nan")
    rel_win_rate = float((rel > 0).mean()) if len(rel) > 0 else float("nan")

    # Reel (TÜFE deflasyonlu)
    reel_raw = df["reel_pnl_pct"]
    reel_numeric = pd.to_numeric(reel_raw, errors="coerce").dropna().values
    n_reel = len(reel_numeric)
    if n_reel > 0:
        avg_reel = float(np.mean(reel_numeric))
        reel_win_rate = float((reel_numeric > 0).mean())
        avg_win_reel = float(np.mean(reel_numeric[reel_numeric > 0])) if (reel_numeric > 0).any() else 0.0
        avg_loss_reel = float(np.mean(reel_numeric[reel_numeric < 0])) if (reel_numeric < 0).any() else 0.0
        wins_sum = float(reel_numeric[reel_numeric > 0].sum())
        loss_sum = abs(float(reel_numeric[reel_numeric < 0].sum()))
        pf_reel = round(wins_sum / loss_sum, 3) if loss_sum > 0 else float("inf")
    else:
        avg_reel = TUFE_UNAVAILABLE
        reel_win_rate = TUFE_UNAVAILABLE
        avg_win_reel = TUFE_UNAVAILABLE
        avg_loss_reel = TUFE_UNAVAILABLE
        pf_reel = TUFE_UNAVAILABLE

    return {
        "n_trades": len(df),
        "n_reel_available": n_reel,
        "win_rate_nominal": round(win_rate, 4),
        "avg_nominal_expectancy": round(avg_nom, 4),
        "avg_win_nominal": round(avg_win_nom, 4),
        "avg_loss_nominal": round(avg_loss_nom, 4),
        "avg_relative_expectancy": round(avg_rel, 4) if math.isfinite(avg_rel) else float("nan"),
        "relative_win_rate": round(rel_win_rate, 4) if math.isfinite(rel_win_rate) else float("nan"),
        "avg_reel_expectancy": round(avg_reel, 4) if isinstance(avg_reel, float) else avg_reel,
        "reel_win_rate": round(reel_win_rate, 4) if isinstance(reel_win_rate, float) else reel_win_rate,
        "avg_win_reel": round(avg_win_reel, 4) if isinstance(avg_win_reel, float) else avg_win_reel,
        "avg_loss_reel": round(avg_loss_reel, 4) if isinstance(avg_loss_reel, float) else avg_loss_reel,
        "profit_factor_reel": pf_reel,
    }


# ---------------------------------------------------------------------------
# Adil-null simülasyonu
# ---------------------------------------------------------------------------

def _simulate_exit(
    prices_arr: np.ndarray,  # close prices (chrono)
    dates_arr: np.ndarray,   # datetime64 dates
    entry_date: pd.Timestamp,
    sl_factor: float = SL_FACTOR,
    tp_factor: float = TP_FACTOR,
    max_hold: int = NULL_MAX_HOLD_DAYS,
) -> float | None:
    """SL/TP/max-hold çıkış simülasyonu. pnl_pct (pre-commission) döner."""
    idx = np.searchsorted(dates_arr, entry_date.to_datetime64(), side="left")
    if idx >= len(dates_arr):
        return None
    entry_px = float(prices_arr[idx])
    if not math.isfinite(entry_px) or entry_px <= 0:
        return None
    sl_px = entry_px * sl_factor
    tp_px = entry_px * tp_factor
    end_idx = min(idx + max_hold + 1, len(dates_arr))
    for j in range(idx + 1, end_idx):
        close = float(prices_arr[j])
        if not math.isfinite(close):
            continue
        if close <= sl_px:
            return (sl_px - entry_px) / entry_px  # SL hit (approximate)
        if close >= tp_px:
            return (tp_px - entry_px) / entry_px  # TP hit
    # Max hold
    last = float(prices_arr[end_idx - 1])
    if not math.isfinite(last):
        return None
    return (last - entry_px) / entry_px


def run_fair_null(
    trades: pd.DataFrame,
    symbol_prices: dict[str, pd.Series],
    xu100: pd.Series,
    n_iter: int = 1000,
    seed: int = RANDOM_SEED,
) -> dict:
    """1000-iterasyon adil-null: random giriş, aynı SL/TP/max-hold.

    §4 testi: giriş-zamanlaması edge'i mi, yoksa çıkış mekanik kazancı mı?
    """
    rng = random.Random(seed)

    # Giriş havuzu: snapshot'taki tüm iş günleri (entry cutoff kadar)
    all_dates_raw: set[pd.Timestamp] = set()
    for s in symbol_prices.values():
        mask = s.index <= pd.Timestamp(NULL_ENTRY_CUTOFF)
        all_dates_raw.update(s.index[mask])
    entry_pool = sorted(all_dates_raw)
    if len(entry_pool) < 50:
        return {"error": "Yeterli giriş tarihi yok", "n_iterations": 0}

    # Symbol → (prices_array, dates_array) cache
    cache: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for sym, s in symbol_prices.items():
        cache[sym] = (s.values.astype(float), s.index.values)

    xu100_arr = xu100.values.astype(float)
    xu100_dates = xu100.index.values

    null_win_rates: list[float] = []
    null_expectancies: list[float] = []

    for _ in range(n_iter):
        iter_pnls: list[float] = []
        for _, row in trades.iterrows():
            sym = row["symbol"]
            prices_arr, dates_arr = cache.get(sym, (None, None))
            if prices_arr is None:
                # KORDS veya eksik → XU100 proxy
                prices_arr, dates_arr = xu100_arr, xu100_dates

            random_entry = rng.choice(entry_pool)
            pnl = _simulate_exit(prices_arr, dates_arr, random_entry)
            if pnl is not None:
                iter_pnls.append(pnl - COMMISSION)

        if iter_pnls:
            arr = np.array(iter_pnls)
            null_win_rates.append(float((arr > 0).mean()))
            null_expectancies.append(float(arr.mean()))

    if not null_win_rates:
        return {"error": "Simülasyon sonuç üretemedi", "n_iterations": n_iter}

    wr_arr = np.array(null_win_rates)
    exp_arr = np.array(null_expectancies)
    return {
        "n_iterations": len(null_win_rates),
        "null_win_rate_p50": round(float(np.percentile(wr_arr, 50)), 4),
        "null_win_rate_p95": round(float(np.percentile(wr_arr, 95)), 4),
        "null_expectancy_p50": round(float(np.percentile(exp_arr, 50)), 4),
        "null_expectancy_p95": round(float(np.percentile(exp_arr, 95)), 4),
        "null_win_rate_mean": round(float(wr_arr.mean()), 4),
        "null_expectancy_mean": round(float(exp_arr.mean()), 4),
    }


# ---------------------------------------------------------------------------
# Attribution (S2)
# ---------------------------------------------------------------------------

def compute_attribution(
    trades: pd.DataFrame,
    enriched: pd.DataFrame,
    summary: dict,
) -> dict:
    """Kapalı işlem P&L vs portföy kazancı farkını göster (conviction/cash-drag atfı)."""
    initial_cap = float(summary.get("initial_capital_tl", 120000.0))
    final_port = float(summary.get("final_portfolio_tl", 167401.06))
    total_commission = float(summary.get("total_commission_tl", 2924.08))

    closed_pnl_tl = float(trades["pnl"].sum())
    actual_gain_tl = final_port - initial_cap
    open_pos_contribution = actual_gain_tl - closed_pnl_tl

    # Reel P&L tahmini (reel_pnl_pct × invested_capital)
    reel_col = pd.to_numeric(enriched["reel_pnl_pct"], errors="coerce")
    invested = enriched["entry_price"] * enriched["shares"]
    reel_pnl_tl_series = reel_col * invested
    reel_closed_pnl_tl = float(reel_pnl_tl_series.dropna().sum())
    n_reel = int(reel_col.notna().sum())
    inflation_erased_tl = (
        closed_pnl_tl - reel_closed_pnl_tl
        if n_reel == len(trades)
        else float("nan")
    )

    avg_invested_per_trade = float(invested.mean())

    return {
        "initial_capital_tl": initial_cap,
        "final_portfolio_tl": final_port,
        "actual_gain_tl": round(actual_gain_tl, 2),
        "closed_trades_pnl_tl": round(closed_pnl_tl, 2),
        "open_positions_contribution_tl": round(open_pos_contribution, 2),
        "total_commission_tl": round(total_commission, 2),
        "reel_closed_pnl_tl": round(reel_closed_pnl_tl, 2) if n_reel > 0 else TUFE_UNAVAILABLE,
        "inflation_erased_tl": round(inflation_erased_tl, 2) if math.isfinite(inflation_erased_tl) else TUFE_UNAVAILABLE,
        "avg_invested_per_trade_tl": round(avg_invested_per_trade, 2),
        "n_closed_trades": len(trades),
        "n_total_trades_all": int(summary.get("total_trades", 0)),
        "attribution_note": (
            "open_positions_contribution = portföy kazancındaki kapalı-işlem tarafından "
            "açıklanamayan kısım (açık pozisyon MTM + cash-drag etkisi). "
            "Büyükse: conviction/cash-drag/sizing etkili. Küçükse: edge'in kendisi kısıtlayıcı."
        ),
    }


# ---------------------------------------------------------------------------
# Frozen Verdict (§4)
# ---------------------------------------------------------------------------

def compute_verdict(
    expectancy: dict,
    null_results: dict,
    tufe_available: bool,
) -> dict:
    """§4 dondurulmuş karar kuralı — sonuç görülmeden eşik gevşetme YASAK."""
    if "error" in null_results:
        return {
            "verdict": "BELIRSIZ",
            "reason": f"Adil-null hata: {null_results['error']}",
        }

    actual_wr = expectancy["win_rate_nominal"]
    null_p95_wr = null_results["null_win_rate_p95"]
    null_p95_exp = null_results["null_expectancy_p95"]

    beats_null_wr = bool(actual_wr > null_p95_wr)

    avg_reel = expectancy["avg_reel_expectancy"]
    if tufe_available and isinstance(avg_reel, float):
        reel_positive = bool(avg_reel > 0)
        beats_null_exp = bool(avg_reel > null_p95_exp)
        tüfe_note = None
    else:
        # TÜFE yok → nominal proxy (flaglenir)
        nom_exp = expectancy["avg_nominal_expectancy"]
        reel_positive = None
        beats_null_exp = bool(isinstance(nom_exp, float) and nom_exp > null_p95_exp)
        tüfe_note = "TÜFE_UNAVAILABLE: reel_positive kontrolü atlandı, nominal proxy kullanıldı"

    # §4 frozen: TÜM ÜÇÜ zorunlu (reel_positive AND beats_null_wr AND beats_null_exp)
    if reel_positive is None:
        # TÜFE yok → reel gate atlanır, sadece null testleri
        edge_var = beats_null_wr and beats_null_exp
    else:
        edge_var = reel_positive and beats_null_wr and beats_null_exp

    # D-186 dersi: survivorship bias → iyimser yönde baskı
    survivorship_caveat = (
        "Survivorship bias (orta risk) sonuçları iyimser yönde etkiler. "
        "EDGE_YOK çıktıysa gerçekte kesinlikle yok."
    )

    # H2-2024 salience-bias önleme notu
    h2_note = (
        "DİKKAT: H2-2024 alt-dönem winrate (%67.1, 85 trade) istatistiksel olarak zayıftır. "
        "Bu analiz full-2yr verisi (348 trade, %52.87) kullanır."
    )

    return {
        "verdict": "EDGE_VAR" if edge_var else "EDGE_YOK",
        "gate_results": {
            "reel_positive": reel_positive,
            "beats_null_winrate_p95": beats_null_wr,
            "beats_null_expectancy_p95": beats_null_exp,
        },
        "actual_win_rate": actual_wr,
        "null_win_rate_p95": null_p95_wr,
        "avg_reel_expectancy": avg_reel,
        "null_expectancy_p95": null_p95_exp,
        "tufe_note": tüfe_note,
        "survivorship_caveat": survivorship_caveat,
        "h2_alt_donem_notu": h2_note,
        "frozen_rule": (
            "EDGE_VAR ← reel_positive AND win_rate>null_p95 AND reel_expectancy>null_p95_expectancy. "
            "Tüm koşullar zorunlu. Eşik gevşetme YASAK."
        ),
    }


# ---------------------------------------------------------------------------
# Konsol raporu
# ---------------------------------------------------------------------------

def _print_report(
    exp: dict, null: dict, attr: dict, verdict: dict, n_trades: int
) -> None:
    def fmt(v, pct: bool = True) -> str:
        if isinstance(v, str):
            return v
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "N/A"
        if pct:
            return f"{v*100:+.2f}%"
        return f"{v:.4f}"

    print("\n" + "=" * 68)
    print("  D-189 SAF EDGE ANALİZİ — BIST50 2YR STUB-FREE (L1+L2)")
    print("=" * 68)
    print(f"  DATASET : {n_trades} tamamlanan işlem, 2024-01-01 – 2026-04-30")
    print(f"  KONFİG  : fundamentals-kapalı (L1+L2 only, stub-free)")
    tufe_s = "MEVCUT" if verdict.get("tufe_note") is None else "EKSİK (SENTINEL)"
    print(f"  TÜFE    : {tufe_s}")
    print()
    print("  NOMINAL BEKLENTİ      :", fmt(exp["avg_nominal_expectancy"]))
    print("  REEL BEKLENTİ         :", fmt(exp["avg_reel_expectancy"]))
    print("  XU100-GÖRELİ BEKLENTİ:", fmt(exp["avg_relative_expectancy"]))
    print()
    print(f"  WİNRATE NOMİNAL : {exp['win_rate_nominal']*100:.1f}%")
    print(f"  WİNRATE REEL    : {fmt(exp['reel_win_rate'], pct=False)}")
    print(f"  WİNRATE GÖRELİ  : {exp['relative_win_rate']*100:.1f}%" if isinstance(exp.get("relative_win_rate"), float) else "  WİNRATE GÖRELİ : N/A")
    print(f"  PF REEL         : {exp['profit_factor_reel']}")
    print()
    if "error" not in null:
        beats_wr = verdict["gate_results"]["beats_null_winrate_p95"]
        beats_exp = verdict["gate_results"]["beats_null_expectancy_p95"]
        print(f"  ADİL-NULL ({null['n_iterations']} iter):")
        print(f"    Null WR P95     : {null['null_win_rate_p95']*100:.1f}%  | Sinyal: {exp['win_rate_nominal']*100:.1f}%  -> {'GECIYOR [OK]' if beats_wr else 'GECEMLYOR [!!]'}")
        print(f"    Null Exp P95    : {fmt(null['null_expectancy_p95'])} | Sinyal: {fmt(exp['avg_reel_expectancy'])} -> {'GECIYOR [OK]' if beats_exp else 'GECEMLYOR [!!]'}")
    print()
    print(f"  ATRİBÜSYON:")
    print(f"    Kapalı işlem P&L   : +{attr['closed_trades_pnl_tl']:,.0f} TL")
    print(f"    Portföy kazancı    : +{attr['actual_gain_tl']:,.0f} TL")
    print(f"    Açık poz + nakit   : +{attr['open_positions_contribution_tl']:,.0f} TL")
    infl = attr.get("inflation_erased_tl")
    if isinstance(infl, (int, float)) and math.isfinite(infl):
        print(f"    Enflasyonun yediği : {infl:,.0f} TL")
    print()
    print("=" * 68)
    print(f"  KARAR: {verdict['verdict']}")
    for gate, result in verdict["gate_results"].items():
        status = "[OK]" if result is True else ("[!!]" if result is False else "[?]")
        print(f"    {gate}: {result} {status}")
    if verdict.get("tufe_note"):
        print(f"  [!!] {verdict['tufe_note']}")
    print(f"\n  {verdict['survivorship_caveat']}")
    print(f"\n  {verdict['h2_alt_donem_notu']}")
    print("=" * 68 + "\n")


# ---------------------------------------------------------------------------
# Ana fonksiyon
# ---------------------------------------------------------------------------

def main(null_iters: int = 1000) -> None:
    print("[D-189] Veri yükleniyor...")
    trades = load_trades()
    xu100 = load_xu100()
    tufe = load_tufe()
    symbol_prices = load_prices()
    summary = load_summary()

    tufe_available = tufe is not None
    print(f"  -> {len(trades)} trade, XU100 {len(xu100)} gun, "
          f"TÜFE {'mevcut' if tufe_available else 'EKSİK'}, "
          f"{len(symbol_prices)} hisse snapshot")

    print("[D-189] Per-trade metrikler hesaplanıyor...")
    enriched = compute_per_trade_metrics(trades, tufe, xu100)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(OUTPUT_DIR / "per_trade_table.csv", index=False, encoding="utf-8")
    print(f"  -> {OUTPUT_DIR / 'per_trade_table.csv'}")

    expectancy = compute_expectancy(enriched)

    print(f"[D-189] Adil-null simülasyonu ({null_iters} iterasyon × {len(trades)} trade)...")
    null_results = run_fair_null(trades, symbol_prices, xu100, n_iter=null_iters)
    (OUTPUT_DIR / "fair_null_results.json").write_text(
        json.dumps(null_results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  -> {OUTPUT_DIR / 'fair_null_results.json'}")

    attribution = compute_attribution(trades, enriched, summary)
    (OUTPUT_DIR / "attribution_results.json").write_text(
        json.dumps(attribution, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  -> {OUTPUT_DIR / 'attribution_results.json'}")

    verdict = compute_verdict(expectancy, null_results, tufe_available)
    full_results = {
        "expectancy": expectancy,
        "null_results": null_results,
        "attribution": attribution,
        "verdict": verdict,
        "config": {
            "dataset": str(TRADES_CSV),
            "n_trades": len(trades),
            "null_iters": null_iters,
            "sl_factor": SL_FACTOR,
            "tp_factor": TP_FACTOR,
            "random_seed": RANDOM_SEED,
        },
    }
    (OUTPUT_DIR / "verdict.json").write_text(
        json.dumps(full_results, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"  -> {OUTPUT_DIR / 'verdict.json'}")

    _print_report(expectancy, null_results, attribution, verdict, len(trades))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="D-189 SAF edge izolasyonu")
    parser.add_argument(
        "--null-iters", type=int, default=1000,
        help="Adil-null iterasyon sayısı (varsayılan: 1000, hızlı test: 100)",
    )
    args = parser.parse_args()
    main(null_iters=args.null_iters)
