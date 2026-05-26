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
from src.backtest.reporter import save_summary_json, save_trades_csv
from src.signals.calculator import compute_composite_score, kelly_win_prob
from src.signals.layers.risk_layer import score_risk
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
    "L3/L4/L5 DISLANMIS. Sadece L1+L2+L6. CB-014 kapsamaz."
)

_DEFAULT_START  = "2025-09-01"
_DEFAULT_END    = "2026-02-28"
_DEFAULT_OUTPUT = "reports/backtest/exploratory/bist50_2025h2"
_STUBFREE_OUTPUT = "reports/backtest/exploratory/bist50_2025h2_stubfree"

# Stub-free mod: sadece bu 3 layer kullanilir, L3/L4/L5 normalizer'a girmez
_STUB_FREE_WEIGHTS = {
    "technical": MASTER_WEIGHTS["technical"],  # 0.25
    "macro":     MASTER_WEIGHTS["macro"],       # 0.20
    "risk":      MASTER_WEIGHTS["risk"],        # 0.03
    # kap / sentiment / smart_money: dahil degil
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
    """BacktestEngine subclass: L3/L4/L5 dislanir, sadece L1+L2+L6 kullanilir.

    Normalizer = 0.25+0.20+0.03 = 0.48
    BUY sinyali uretebilir (production-equivalent modda composite maks ~58).

    src/backtest/engine.py degistirilmez -- sadece _compute_composite override.
    """

    def _compute_composite(
        self,
        technical_data: dict,
        macro_data: dict,
        symbol: str,
    ) -> tuple[float, float]:
        """L1+L2+L6 composite -- L3/L4/L5 dislanmis."""
        try:
            tech_score = score_technical(technical_data).score
        except Exception:
            tech_score = 50.0
        try:
            macro_score = self._global_macro_score(macro_data)
        except Exception:
            macro_score = 50.0
        try:
            risk_score = score_risk(symbol, technical_data, macro_data).score
        except Exception:
            risk_score = 50.0

        composite = compute_composite_score(
            {
                "technical": tech_score,
                "macro":     macro_score,
                "risk":      risk_score,
                # kap / sentiment / smart_money: kasitli olarak dahil edilmedi
            },
            weights=_STUB_FREE_WEIGHTS,
        )
        return composite, macro_score


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

    # --- 3. Backtest -------------------------------------------------------
    print(f"  [3/4] Backtest simulasyonu ({args.mode} modu)...")
    EngineClass = StubFreeBacktestEngine if stub_free else BacktestEngine
    engine = EngineClass(
        start_date=args.start,
        end_date=args.end,
        quiet_warnings=True,
    )
    engine.run(price_data, macro_ts, benchmark_series)

    # --- 4. Metrikler ve cikti -------------------------------------------
    print("  [4/4] Metrikler hesaplaniyor, dosyalar yaziliyor...")
    metrics = summarize(engine, benchmark_series)
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
            "L3/L4/L5 dislanmis; normalizer=0.48 (L1+L2+L6)"
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
    mode_label = "STUB-FREE (L1+L2+L6)" if stub_free else "PROD-EQUIV (L3/L4/L5=50)"
    print(f"  SONUCLAR [{mode_label}]")
    print(f"  (L3/L4/L5=50 stub, 6 ay pencere -- beklenti yonetimi)")
    print(f"{sep}")
    print(f"  Donem      : {metrics['period']}")
    print(f"  Islem gunu : {metrics['trading_days']}")
    print(f"  Trade      : {metrics['total_trades']} toplam"
          f" ({metrics['completed_trades']} kapandi)")
    print(f"  Getiri     : {metrics['total_return_pct']:+.2f}%"
          f"  vs  {metrics['benchmark_return_pct']:+.2f}% (BIST100)")
    print(f"  Sharpe     : {metrics['sharpe_ratio']:.3f}")
    print(f"  Max DD     : {metrics['max_drawdown_pct']:.2f}%")
    print(f"  Alpha      : {metrics['alpha_pct']:+.2f}%")
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
    parser.add_argument("--start",      default=_DEFAULT_START)
    parser.add_argument("--end",        default=_DEFAULT_END)
    parser.add_argument("--output-dir", default=None,
                        help="Cikti dizini (varsayilan moda gore belirlenir)")
    parser.add_argument(
        "--mode",
        default="production-equivalent",
        choices=["production-equivalent", "stub-free"],
        help=(
            "production-equivalent: L3/L4/L5=50 stub, production paritesi. "
            "stub-free: L3/L4/L5 dislanir, sadece L1+L2+L6."
        ),
    )
    args = parser.parse_args()
    _run(args)


if __name__ == "__main__":
    main()
