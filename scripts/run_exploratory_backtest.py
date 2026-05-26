"""Exploratory backtest script — BIST50 universe, 2025-09 to 2026-02.

EXPLORATORY RUN -- 6 ay < MinBTL 553 gun.
L3/L4/L5 stub (neutral 50.0). CB-014 kapsamaz. DSR/PBO hesaplanmaz.

Cikti dizini: reports/backtest/exploratory/bist50_2025h2/
  summary.json      -- Sharpe, total_return_pct, n_trades, ticker bazli
  run_metadata.json -- tarih, universe, EXPLORATORY notu
  trades.csv        -- tum islemler

Kullanim:
  python scripts/run_exploratory_backtest.py
  python scripts/run_exploratory_backtest.py --start 2025-09-01 --end 2026-02-28
  python scripts/run_exploratory_backtest.py --output-dir reports/backtest/exploratory/custom
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
from src.backtest.reporter import save_summary_json, save_trades_csv
from src.utils.logger import setup_logger

logger = setup_logger("run_exploratory_backtest")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EXPLORATORY_WARNING = (
    "EXPLORATORY RUN -- 6 ay < MinBTL 553 gun. "
    "L3/L4/L5 stub. CB-014 kapsamaz."
)

_DEFAULT_START = "2025-09-01"
_DEFAULT_END = "2026-02-28"
_DEFAULT_OUTPUT = "reports/backtest/exploratory/bist50_2025h2"

# 50 tickers — .IS suffix load_price_data() tarafindan eklenir
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
# Helpers
# ---------------------------------------------------------------------------

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
    # Alfabetik siralama
    return dict(sorted(per_ticker.items()))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=_EXPLORATORY_WARNING,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--start", default=_DEFAULT_START,
                        help=f"Baslangic tarihi (default: {_DEFAULT_START})")
    parser.add_argument("--end", default=_DEFAULT_END,
                        help=f"Bitis tarihi (default: {_DEFAULT_END})")
    parser.add_argument("--output-dir", default=_DEFAULT_OUTPUT,
                        help=f"Cikti dizini (default: {_DEFAULT_OUTPUT})")
    args = parser.parse_args()

    sep = "=" * 65
    print(f"\n{sep}")
    print(f"  *** {_EXPLORATORY_WARNING} ***")
    print(f"  Donem   : {args.start} --> {args.end}")
    print(f"  Universe: {len(_BIST50)} ticker (BIST50)")
    print(f"  Cikti   : {args.output_dir}")
    print(f"{sep}\n")

    # --- 1. Fiyat verisi -------------------------------------------------------
    print("  [1/4] BIST50 fiyat verisi indiriliyor...")
    price_data = load_price_data(_BIST50, args.start, args.end)
    n_loaded = len(price_data)
    print(f"        {n_loaded}/{len(_BIST50)} ticker yuklendi")
    if not price_data:
        print("\n  HATA: Fiyat verisi alinamadi. Ag baglantisini kontrol edin.")
        sys.exit(1)

    # --- 2. Makro verisi -------------------------------------------------------
    print("  [2/4] Makro veri indiriliyor (USDTRY, VIX, Brent, SP500, BIST100)...")
    macro_ts = load_macro_series(args.start, args.end)
    print(f"        {len(macro_ts)} gun, kolonlar: {list(macro_ts.columns)}")
    benchmark_series = macro_ts["BIST100"] if "BIST100" in macro_ts.columns else None

    # --- 3. Backtest simülasyonu -----------------------------------------------
    print("  [3/4] Backtest simulasyonu calistiriliyor...")
    engine = BacktestEngine(
        start_date=args.start,
        end_date=args.end,
        quiet_warnings=True,
    )
    engine.run(price_data, macro_ts, benchmark_series)

    # --- 4. Metrikler ve cikti ------------------------------------------------
    print("  [4/4] Metrikler hesaplaniyor, dosyalar yaziliyor...")
    metrics = summarize(engine, benchmark_series)

    # Exploratory marker ve ticker breakdown ekle
    metrics["exploratory_warning"] = _EXPLORATORY_WARNING
    metrics["ticker_summary"] = _ticker_summary(engine.trades)

    # Cikti dizini olustur
    out_path = Path(args.output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # summary.json
    save_summary_json(metrics, args.output_dir)

    # trades.csv
    save_trades_csv(engine.trades, args.output_dir)

    # run_metadata.json
    metadata = {
        "run_type": "EXPLORATORY",
        "warning": _EXPLORATORY_WARNING,
        "run_date_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "period_start": args.start,
        "period_end": args.end,
        "universe": "BIST50",
        "n_universe": len(_BIST50),
        "n_loaded": n_loaded,
        "tickers": _BIST50,
        "cb014_validation": False,
        "dsr_pbo_computed": False,
        "l3_l4_l5_stub": True,
        "stub_note": "KAP/sentiment/smart_money=50.0 (neutral) — tarihsel veri yok",
        "minbtl_note": "6 ay (~126 gun) < MinBTL 553 gun — istatistiksel guven dusuk",
    }
    meta_path = out_path / "run_metadata.json"
    meta_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # --- Sonuc ozeti ----------------------------------------------------------
    print(f"\n{sep}")
    print("  SONUCLAR (beklenti yonetimi: L3/L4/L5=50 stub, 6 ay pencere)")
    print(f"{sep}")
    print(f"  Donem      : {metrics['period']}")
    print(f"  Islem gunu : {metrics['trading_days']}")
    print(f"  Trade      : {metrics['total_trades']} toplam"
          f" ({metrics['completed_trades']} kapandi)")
    print(f"  Getiri     : {metrics['total_return_pct']:+.2f}%"
          f"  vs  {metrics['benchmark_return_pct']:+.2f}% (BIST100)")
    print(f"  Sharpe     : {metrics['sharpe_ratio']:.3f}"
          f"  (conservative — L3/L4/L5=50)")
    print(f"  Max DD     : {metrics['max_drawdown_pct']:.2f}%")
    print(f"  Alpha      : {metrics['alpha_pct']:+.2f}%")
    print(f"  Win Rate   : {metrics['win_rate_pct']:.1f}%")
    print(f"{sep}")
    print(f"\n  summary.json      --> {args.output_dir}/summary.json")
    print(f"  run_metadata.json --> {args.output_dir}/run_metadata.json")
    print(f"  trades.csv        --> {args.output_dir}/trades.csv")
    print()


if __name__ == "__main__":
    main()
