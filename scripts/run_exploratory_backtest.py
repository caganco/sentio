"""Exploratory backtest script -- BIST50 universe.

EXPLORATORY RUN -- 6 ay < MinBTL 553 gun.
CB-014 kapsamaz. DSR/PBO hesaplanmaz.

Modlar:
  production-equivalent (varsayilan):
    L3/L4/L5 = 50.0 neutral stub. Production composite ile ayni formul.
    Sonuc: composite maks ~58 -> BUY sinyali olusmuyor (L3 weight=0.30 tavan).
    Amac: production paritesini korumak.

  stub-free:
    L3/L4/L5 DISLANIR. Normalizer sadece L1+L2+L6 (0.48).
    BUY sinyali uretebilir. Gercek hayatta L1+L2+L6 katmanlari
    ne kadar iyi calistigiyla ilgili bir proxy.
    --mode stub-free --output-dir reports/backtest/exploratory/bist50_2025h2_stubfree

Kullanim:
  python scripts/run_exploratory_backtest.py
  python scripts/run_exploratory_backtest.py --mode stub-free
  python scripts/run_exploratory_backtest.py --start 2025-09-01 --end 2026-02-28 --mode stub-free
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtest.data_loader import load_macro_series, load_price_data
from src.backtest.engine import BacktestEngine
from src.backtest.metrics import summarize
from src.data.macro_sources import fetch_tufe_series
from src.backtest.reporter import save_summary_json, save_trades_csv
from src.signals.calculator import compute_composite_score, kelly_win_prob
from src.signals.layers.technical_layer import score_technical
from src.signals.thresholds import MASTER_WEIGHTS
from src.utils.logger import setup_logger

logger = setup_logger("run_exploratory_backtest")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROD_EQUIV_WARNING = (
    "EXPLORATORY RUN -- 6 ay < MinBTL 553 gun. "
    "L3/L4/L5 stub (50.0). CB-014 kapsamaz."
)
_STUB_FREE_WARNING = (
    "EXPLORATORY RUN -- STUB-FREE MODE. "
    "L3/L4/L5 DISLANMIS. Sadece L1+L2. CB-014 kapsamaz."
)

_DEFAULT_START  = "2025-09-01"
_DEFAULT_END    = "2026-02-28"
_DEFAULT_OUTPUT = "reports/backtest/exploratory/bist50_2025h2"
_STUBFREE_OUTPUT = "reports/backtest/exploratory/bist50_2025h2_stubfree"

# Stub-free mod: sadece bu 2 layer kullanilir, L3/L4/L5 normalizer'a girmez
# D-154: L6 (risk) composite'den cikarildi — artik sadece L1+L2.
# Normalizer = tech_weight + macro_weight = 0.2577 + 0.2062 ≈ 0.4639
_STUB_FREE_WEIGHTS = {
    "technical": MASTER_WEIGHTS["technical"],  # 0.2577 (D-154 renorm)
    "macro":     MASTER_WEIGHTS["macro"],       # 0.2062 (D-154 renorm)
    # risk (L6) removed D-154; kap / sentiment / smart_money: kasitli dahil degil
}

_BIST50: list[str] = [
    "AKBNK", "ARCLK", "ASELS", "BIMAS", "DOHOL",
    "EKGYO", "ENKAI", "EREGL", "FROTO", "GARAN",
    "GUBRF", "HEKTS", "ISCTR", "KCHOL", "KORDS",
    "KOZAA", "KOZAL", "KRDMD", "MGROS", "ODAS",
    "PETKM", "PGSUS", "SAHOL", "SASA", "SISE",
    "SOKM",  "TAVHL", "TCELL", "THYAO", "TKFEN",
    "TOASO", "TTKOM", "TTRAK", "TUPRS", "VAKBN",
    "VESTL", "YKBNK", "AKSEN", "ALARK", "CIMSA",
    "CLEBI", "EGEEN", "GESAN", "HALKB", "LOGO",
    "OTKAR", "SKBNK", "ULKER", "ZOREN", "AGHOL",
]


# ---------------------------------------------------------------------------
# Stub-Free Engine (subclass -- src/ dokunulmaz)
# ---------------------------------------------------------------------------

class StubFreeBacktestEngine(BacktestEngine):
    """BacktestEngine subclass: L3/L4/L5 dislanir, sadece L1+L2 kullanilir.

    D-154: L6 (risk) composite'den cikarildi. Normalizer = tech+macro = 0.4639.
    BUY sinyali uretebilir (production-equiv modda composite maks ~73, ama
    kap/sent/sm stub'u %53.6 agirlik ceker -> pratikte <72 kalin sinyaller).

    src/backtest/engine.py degistirilmez -- sadece _compute_composite override.
    """

    def _xbrl_enabled(self) -> bool:
        """Stub-free mod: _compute_composite XBRL kullanmaz, snapshot gerekmez."""
        return False

    def _compute_composite(
        self,
        technical_data: dict,
        macro_data: dict,
        symbol: str,
    ) -> tuple[float, float]:
        """L1+L2 composite -- L3/L4/L5 dislanmis, L6 removed D-154."""
        try:
            tech_score = score_technical(technical_data).score
        except Exception:
            tech_score = 50.0
        try:
            macro_score = self._global_macro_score(macro_data)
        except Exception:
            macro_score = 50.0

        composite = compute_composite_score(
            {
                "technical": tech_score,
                "macro":     macro_score,
                # kap / sentiment / smart_money / risk: kasitli olarak dahil edilmedi
            },
            weights=_STUB_FREE_WEIGHTS,
        )
        return composite, macro_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _debug_macro_analysis(audit_trail: list[dict], engine, out_dir: str) -> None:
    """Print daily L2 macro score time-series and gate stats. Save audit_trail.csv."""
    if not audit_trail:
        print("  [DEBUG] audit_trail bos.")
        return

    # Group by date: macro_score is identical across all symbols per day
    daily: dict[str, dict] = {}
    for entry in audit_trail:
        d = str(entry.get("date", ""))[:10]
        if d not in daily:
            daily[d] = {
                "macro_score": float(entry.get("macro_score") or 0.0),
                "any_gated": bool(entry.get("entry_gated", False)),
                "vix": entry.get("vix_level"),
                "usdtry_chg": entry.get("USDTRY_1d_change"),
            }
        elif entry.get("entry_gated", False):
            daily[d]["any_gated"] = True

    total_days = len(daily)
    below45    = sum(1 for v in daily.values() if v["macro_score"] < 45.0)
    gated_days = sum(1 for v in daily.values() if v["any_gated"])

    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  DEBUG: L2 Makro Skor Analizi — {total_days} islem gunu")
    print(f"  Esik: BACKTEST_MACRO_CRISIS_VIX=35.0 | BACKTEST_MACRO_CRISIS_USDTRY_SPIKE=0.03 (D-166)")
    print(f"{sep}")
    print(f"  {'TARIH':<12} {'L2_SCORE':>10} {'VIX':>6} {'USDTRY_dg':>10} {'GATE':>6}")
    print(f"  {'-'*12} {'-'*10} {'-'*6} {'-'*10} {'-'*6}")
    for date in sorted(daily.keys()):
        v    = daily[date]
        ms   = v["macro_score"]
        vix  = f"{v['vix']:.1f}" if v["vix"] is not None else "  N/A"
        usd  = f"{v['usdtry_chg']:.4f}" if v["usdtry_chg"] is not None else "    N/A"
        gate = "BLOCK" if v["any_gated"] else "OK"
        flag = " <<<" if ms < 45.0 else ""
        print(f"  {date:<12} {ms:>10.2f} {vix:>6} {usd:>10} {gate:>6}{flag}")
    print(f"{sep}")
    print(f"  Toplam islem gunu : {total_days}")
    print(f"  L2 < 45 gun       : {below45}  ({100.0*below45/max(total_days,1):.1f}%)")
    print(f"  Gated gunler      : {gated_days}  ({100.0*gated_days/max(total_days,1):.1f}%)")
    print(f"{sep}\n")

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    audit_csv = str(out_path / "audit_trail.csv")
    engine.export_audit_trail_csv(audit_csv)
    print(f"  audit_trail.csv   --> {audit_csv}")


def _ticker_summary(trades: list[dict]) -> dict[str, dict]:
    """Per-ticker P&L ve trade sayisi (tamamlanan SELL'lerden)."""
    per_ticker: dict[str, dict] = {}
    for t in trades:
        if t.get("type") != "SELL":
            continue
        sym = t["symbol"]
        if sym not in per_ticker:
            per_ticker[sym] = {
                "n_trades": 0,
                "total_pnl_pct": 0.0,
                "wins": 0,
                "losses": 0,
            }
        per_ticker[sym]["n_trades"] += 1
        pnl_pct = t.get("pnl_pct", 0.0) * 100.0
        per_ticker[sym]["total_pnl_pct"] = round(
            per_ticker[sym]["total_pnl_pct"] + pnl_pct, 4
        )
        if t.get("pnl", 0.0) > 0:
            per_ticker[sym]["wins"] += 1
        else:
            per_ticker[sym]["losses"] += 1
    return dict(sorted(per_ticker.items()))


def _run(args: argparse.Namespace) -> None:
    stub_free = (args.mode == "stub-free")
    warning   = _STUB_FREE_WARNING if stub_free else _PROD_EQUIV_WARNING

    # Cikti dizinini moda gore belirle
    if args.output_dir:
        out_dir = args.output_dir
    else:
        out_dir = _STUBFREE_OUTPUT if stub_free else _DEFAULT_OUTPUT

    sep = "=" * 65
    print(f"\n{sep}")
    print(f"  *** {warning} ***")
    print(f"  Donem   : {args.start} -- {args.end}")
    print(f"  Universe: {len(_BIST50)} ticker (BIST50)")
    print(f"  Mod     : {args.mode}")
    print(f"  Cikti   : {out_dir}")
    print(f"{sep}\n")

    # --- 1. Fiyat verisi ---------------------------------------------------
    print("  [1/4] BIST50 fiyat verisi indiriliyor...")
    price_data = load_price_data(_BIST50, args.start, args.end)
    n_loaded = len(price_data)
    print(f"        {n_loaded}/{len(_BIST50)} ticker yuklendi")
    if not price_data:
        print("\n  HATA: Fiyat verisi alinamadi.")
        sys.exit(1)

    # --- 2. Makro verisi ---------------------------------------------------
    print("  [2/4] Makro veri indiriliyor (USDTRY, VIX, Brent, SP500, BIST100)...")
    macro_ts = load_macro_series(args.start, args.end)
    print(f"        {len(macro_ts)} gun, kolonlar: {list(macro_ts.columns)}")
    benchmark_series = (
        macro_ts["BIST100"] if "BIST100" in macro_ts.columns else None
    )

    # --- 2b. TÜFE (reel getiri hesabi icin) ----------------------------------
    print("  [2b/4] TÜFE serisi cekiliyor (EVDS TP.FG.J0)...")
    tufe_series = fetch_tufe_series(args.start, args.end)
    if tufe_series is None:
        print("         UYARI: TÜFE verisi alinamadi — reel getiriler TÜFE_UNAVAILABLE olacak")
    else:
        print(f"         {len(tufe_series)} gunluk TÜFE serisi hazir")

    # --- 3. Backtest -------------------------------------------------------
    print(f"  [3/4] Backtest simulasyonu ({args.mode} modu)...")
    EngineClass = StubFreeBacktestEngine if stub_free else BacktestEngine
    engine = EngineClass(
        start_date=args.start,
        end_date=args.end,
        quiet_warnings=True,
    )
    engine.run(price_data, macro_ts, benchmark_series)

    # --- 3b. Debug macro scores (opsiyonel) --------------------------------
    if getattr(args, "debug_scores", False):
        _debug_macro_analysis(engine.audit_trail, engine, out_dir)

    # --- 4. Metrikler ve cikti -------------------------------------------
    print("  [4/4] Metrikler hesaplaniyor, dosyalar yaziliyor...")
    metrics = summarize(engine, benchmark_series, tufe_series=tufe_series)
    metrics["mode"]              = args.mode
    metrics["exploratory_warning"] = warning
    metrics["ticker_summary"]    = _ticker_summary(engine.trades)

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    save_summary_json(metrics, out_dir)
    save_trades_csv(engine.trades, out_dir)

    metadata = {
        "run_type":        "EXPLORATORY",
        "mode":            args.mode,
        "warning":         warning,
        "run_date_utc":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "period_start":    args.start,
        "period_end":      args.end,
        "universe":        "BIST50",
        "n_universe":      len(_BIST50),
        "n_loaded":        n_loaded,
        "tickers":         _BIST50,
        "cb014_validation":  False,
        "dsr_pbo_computed":  False,
        "l3_l4_l5_included": not stub_free,
        "stub_free_weights": (
            {k: v for k, v in _STUB_FREE_WEIGHTS.items()} if stub_free else None
        ),
        "note": (
            "L3/L4/L5 dislanmis; normalizer=0.4639 (L1+L2, D-154 sonrasi L6 cikarildi)"
            if stub_free else
            "L3/L4/L5=50.0 neutral stub; production composite paritesi"
        ),
    }
    (out_path / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # --- Sonuc ozeti ------------------------------------------------------
    print(f"\n{sep}")
    mode_label = "STUB-FREE (L1+L2)" if stub_free else "PROD-EQUIV (L3/L4/L5=50)"
    print(f"  SONUCLAR [{mode_label}]")
    print(f"  (L3/L4/L5 dislanmis; sadece L1+L2 skorlari etkin)")
    print(f"{sep}")
    print(f"  Donem      : {metrics['period']}")
    print(f"  Islem gunu : {metrics['trading_days']}")
    print(f"  Trade      : {metrics['total_trades']} toplam"
          f" ({metrics['completed_trades']} kapandi)")
    print(f"  Getiri     : {metrics['total_return_pct']:+.2f}%"
          f"  vs  {metrics['benchmark_return_pct']:+.2f}% (BIST100)")
    calmar_val = metrics.get("calmar_ratio")
    calmar_str = f"{calmar_val:.2f}" if calmar_val is not None else "N/A"
    alpha_val = metrics["alpha_pct"]
    alpha_str = f"{alpha_val:+.2f}%" if alpha_val == alpha_val else "N/A (benchmark eksik)"
    print(f"  Sharpe     : {metrics['sharpe_ratio']:.3f} (bilgi; kriter degil)")
    print(f"  Calmar     : {calmar_str}  (getiri/max_dd)")
    print(f"  Max DD     : {metrics['max_drawdown_pct']:.2f}%")
    print(f"  Alpha      : {alpha_str}")
    rr = metrics.get("real_return_pct")
    if rr == "TÜFE_UNAVAILABLE":
        print("  Reel Getiri: TÜFE_UNAVAILABLE (EVDS baglantisi kontrol edin)")
    else:
        print(f"  Reel Getiri: {rr:+.2f}%  (sistem, TRY reel)")
        print(f"  Reel Bench : {metrics['benchmark_real_return_pct']:+.2f}%  (BIST100, TRY reel)")
        print(f"  Reel Alpha : {metrics['real_alpha_pct']:+.2f}%")
        print(f"  Ort.Yil TUFE: {metrics['avg_annual_tufe_pct']:.1f}%")
    print(f"  Win Rate   : {metrics['win_rate_pct']:.1f}%")
    print(f"{sep}")
    print(f"\n  summary.json      --> {out_dir}/summary.json")
    print(f"  run_metadata.json --> {out_dir}/run_metadata.json")
    print(f"  trades.csv        --> {out_dir}/trades.csv")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="BIST50 Exploratory Backtest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--start",        default=_DEFAULT_START)
    parser.add_argument("--end",          default=_DEFAULT_END)
    parser.add_argument("--output-dir",   default=None,
                        help="Cikti dizini (varsayilan moda gore belirlenir)")
    parser.add_argument("--debug-scores", action="store_true",
                        help="Gunluk L2 makro skor time-series + gate stats yazdir, audit_trail.csv kaydet")
    parser.add_argument(
        "--mode",
        default="production-equivalent",
        choices=["production-equivalent", "stub-free"],
        help=(
            "production-equivalent: L3/L4/L5=50 stub, production paritesi. "
            "stub-free: L3/L4/L5 dislanir, sadece L1+L2 (D-154 sonrasi L6 cikarildi)."
        ),
    )
    args = parser.parse_args()
    _run(args)


if __name__ == "__main__":
    main()
