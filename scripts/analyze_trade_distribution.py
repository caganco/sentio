"""D-176: Trade dagilimi + exit/runner teshis analizi.

Backtest'i IN-PROCESS yeniden calistirir (warm cache ~3 dk) -> engine.trades
(reason'li) + price_data elde eder; mevcut trades.csv ile mutabakat yapar.

4 analiz:
  (1) P&L carpikligi (skewness)
  (2) Ort kazanc vs ort kayip + beklenen deger + sermaye konuslanmasi (cash drag)
  (3) Exit nedeni dagilimi (profit_target / stop_loss / signal) — backtest'te TP1/2/3 YOK
  (4) Runner counterfactual: profit_target cikislari trailing-stop ile ne kadar buyurdu

Salt-okunur teshis: engine.py / reporter.py / thresholds.py DOKUNULMAZ; sabitler import edilir.

Kullanim:
  python scripts/analyze_trade_distribution.py --output-dir reports/backtest/session8_d175
  python scripts/analyze_trade_distribution.py --trail-pcts 8,10,15
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
from pathlib import Path
from statistics import mean

import pandas as pd
from scipy.stats import skew

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.backtest.data_loader import load_macro_series, load_price_data
from src.backtest.engine import BacktestEngine
from src.data.macro_sources import fetch_tufe_series
from src.signals.thresholds import EXIT_PROFIT_TARGET, EXIT_STOP_LOSS

logger = logging.getLogger("analyze_trade_distribution")

# _BIST50 listesini run_exploratory_backtest'ten al (drift yok) — importlib ile
# dosya yolundan yukle (paket kurulumundan bagimsiz, side-effect guvenli).
_REB_PATH = Path(__file__).parent / "run_exploratory_backtest.py"
_spec = importlib.util.spec_from_file_location("_reb_module", _REB_PATH)
_reb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_reb)
_BIST50: list[str] = _reb._BIST50

_DEFAULT_START = "2024-01-01"
_DEFAULT_END = "2026-04-30"
_DEFAULT_OUTPUT = "reports/backtest/session8_d175"
_COMMISSION = 0.001


# ---------------------------------------------------------------------------
# Saf yardimcilar (testlenebilir, ag/state yok)
# ---------------------------------------------------------------------------

def compute_skewness(values: list[float]) -> float:
    """Fisher-Pearson duzeltmeli (bias=False) carpiklik. <3 nokta -> nan."""
    arr = pd.Series(values, dtype=float).dropna()
    if len(arr) < 3:
        return float("nan")
    return float(skew(arr, bias=False))


def simulate_trailing_exit(
    forward_closes: "pd.Series",
    entry_price: float,
    trail_pct: float,
    commission: float = _COMMISSION,
) -> dict:
    """entry SONRASI gunluk Close serisinde peak'ten trail_pct geri cekilince cik.

    Hic cekilme olmazsa son Close'da mark-to-end. pnl_pct engine ile ayni:
    exit*(1-comm)/entry - 1 (entry komisyonu pnl_pct'ye girmez, engine.py:447-449).
    """
    if forward_closes is None or len(forward_closes) == 0:
        return {"exit_price": entry_price, "exit_idx": -1,
                "pnl_pct_net": 0.0, "marked_to_end": True}
    peak = entry_price
    closes = [float(p) for p in forward_closes]
    for i, p in enumerate(closes):
        if p > peak:
            peak = p
        if p <= peak * (1.0 - trail_pct):
            return {"exit_price": p, "exit_idx": i,
                    "pnl_pct_net": p * (1.0 - commission) / entry_price - 1.0,
                    "marked_to_end": False}
    last = closes[-1]
    return {"exit_price": last, "exit_idx": len(closes) - 1,
            "pnl_pct_net": last * (1.0 - commission) / entry_price - 1.0,
            "marked_to_end": True}


def build_holding_intervals(trades: list[dict], last_date) -> list[tuple]:
    """BUY/SELL olaylarindan FIFO ile (start, end, entry_cost) araliklari kurar.

    Sonda hala acik pozisyonlar last_date'te kapatilir.
    """
    open_q: dict[str, list[list]] = {}
    intervals: list[tuple] = []
    for t in sorted(trades, key=lambda x: x["date"]):
        sym = t["symbol"]
        if t.get("type") == "BUY":
            cost = float(t["shares"]) * float(t["price"])
            open_q.setdefault(sym, []).append([t["date"], cost])
        elif t.get("type") == "SELL":
            q = open_q.get(sym, [])
            if q:
                start, cost = q.pop(0)
                intervals.append((start, t["date"], cost))
    for sym, q in open_q.items():
        for start, cost in q:
            intervals.append((start, last_date, cost))
    return intervals


def daily_exposure_stats(
    intervals: list[tuple],
    daily_dates: list,
    equity_curve: list[float],
) -> dict:
    """Gunluk acik pozisyon sayisi + yatirili sermaye (entry cost) / equity orani."""
    if not daily_dates:
        return {}
    n_open: list[int] = []
    exposure: list[float] = []
    for i, d in enumerate(daily_dates):
        opens = [c for (s, e, c) in intervals if s <= d <= e]
        n_open.append(len(opens))
        eq = equity_curve[i] if i < len(equity_curve) and equity_curve[i] > 0 else None
        exposure.append((sum(opens) / eq) if eq else 0.0)
    return {
        "avg_open_positions": round(mean(n_open), 2),
        "max_open_positions": max(n_open),
        "pct_days_all_cash": round(100.0 * sum(1 for n in n_open if n == 0) / len(n_open), 1),
        "avg_exposure_pct": round(100.0 * mean(exposure), 1),
    }


def winloss_stats(pnl_pcts: list[float]) -> dict:
    """Ort kazanc/kayip, payoff, beklenen deger (yuzde puan)."""
    wins = [x for x in pnl_pcts if x > 0]
    losses = [abs(x) for x in pnl_pcts if x < 0]
    n = len(pnl_pcts)
    win_rate = len(wins) / n if n else 0.0
    avg_win = mean(wins) if wins else 0.0
    avg_loss = mean(losses) if losses else 0.0
    payoff = (avg_win / avg_loss) if avg_loss > 0 else float("inf")
    expectancy = win_rate * avg_win - (1 - win_rate) * avg_loss
    return {
        "n_closed": n,
        "win_rate_pct": round(100.0 * win_rate, 2),
        "avg_win_pct": round(100.0 * avg_win, 2),
        "avg_loss_pct": round(100.0 * avg_loss, 2),
        "payoff_ratio": round(payoff, 3) if payoff != float("inf") else None,
        "expectancy_pct_per_trade": round(100.0 * expectancy, 2),
    }


# ---------------------------------------------------------------------------
# Re-run + reconciliation
# ---------------------------------------------------------------------------

def rerun_backtest(start: str, end: str) -> "BacktestEngine":
    """production-equivalent BacktestEngine'i in-process calistir (L3 yfinance aktif)."""
    print("  [1/3] Fiyat verisi (yfinance)...")
    price_data = load_price_data(_BIST50, start, end)
    print(f"        {len(price_data)}/{len(_BIST50)} ticker")
    print("  [2/3] Makro + TUFE...")
    macro_ts = load_macro_series(start, end)
    benchmark = macro_ts["BIST100"] if "BIST100" in macro_ts.columns else None
    try:
        tufe = fetch_tufe_series(start, end)
    except Exception:
        tufe = None
    print(f"  [3/3] Backtest simulasyonu ({start} -> {end})...")
    engine = BacktestEngine(start_date=start, end_date=end, quiet_warnings=True)
    engine.run(price_data, macro_ts, benchmark)
    engine._price_data = price_data  # analiz icin sakla (runner fiyat yolu)
    return engine


def reconcile(sell_trades: list[dict], trades_csv: Path) -> dict:
    """Re-run SELL'lerini mevcut trades.csv ile (symbol+entry_date+exit_date+pnl_pct) esle."""
    if not trades_csv.exists():
        return {"csv_found": False, "match_pct": None, "n_csv": 0, "n_rerun": len(sell_trades)}
    csv_df = pd.read_csv(trades_csv)

    def _key(sym, ed, xd, pp):
        return (str(sym), str(ed)[:10], str(xd)[:10], round(float(pp), 4))

    csv_keys = {
        _key(r["symbol"], r["entry_date"], r["date"], r["pnl_pct"])
        for _, r in csv_df.iterrows()
    }
    matched = sum(
        1 for t in sell_trades
        if _key(t["symbol"], t["entry_date"], t["date"], t["pnl_pct"]) in csv_keys
    )
    n = len(sell_trades)
    return {
        "csv_found": True,
        "n_csv": len(csv_df),
        "n_rerun": n,
        "matched": matched,
        "match_pct": round(100.0 * matched / n, 1) if n else 0.0,
    }


# ---------------------------------------------------------------------------
# Runner counterfactual
# ---------------------------------------------------------------------------

def analyze_runners(
    sell_trades: list[dict],
    price_data: dict,
    trail_pcts: list[float],
) -> dict:
    """profit_target cikislari icin trailing-stop alternatifi (entry'den simule)."""
    pt = [t for t in sell_trades if t.get("reason") == "profit_target"]
    out: dict = {"n_profit_target": len(pt), "by_trail": {}}
    for trail in trail_pcts:
        runners = gaveback = same = skipped = 0
        delta_tl = 0.0
        for t in pt:
            df = price_data.get(t["symbol"])
            if df is None:
                skipped += 1
                continue
            fwd = df[df.index > t["entry_date"]]["Close"]
            if fwd.empty:
                skipped += 1
                continue
            sim = simulate_trailing_exit(fwd, float(t["entry_price"]), trail / 100.0)
            alt_pct = sim["pnl_pct_net"]
            actual_pct = float(t["pnl_pct"])
            if alt_pct > actual_pct + 1e-6:
                runners += 1
            elif alt_pct < actual_pct - 1e-6:
                gaveback += 1
            else:
                same += 1
            # TL delta: pnl = pnl_pct * entry_price * shares (engine.py:447-449 ile tutarli)
            base = float(t["entry_price"]) * float(t["shares"])
            delta_tl += (alt_pct - actual_pct) * base
        out["by_trail"][str(trail)] = {
            "runners": runners,
            "gaveback": gaveback,
            "same": same,
            "skipped": skipped,
            "gross_delta_tl": round(delta_tl, 2),
        }
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _run(args: argparse.Namespace) -> None:
    trail_pcts = [float(x) for x in str(args.trail_pcts).split(",") if x.strip()]
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sep = "=" * 68
    print(f"\n{sep}\n  D-176 TRADE DAGILIMI ANALIZI\n{sep}")
    engine = rerun_backtest(args.start, args.end)
    sells = [t for t in engine.trades if t.get("type") == "SELL"]
    price_data = engine._price_data

    rec = reconcile(sells, out_dir / "trades.csv")
    pnl_pcts = [float(t["pnl_pct"]) for t in sells]
    pnl_tls = [float(t["pnl"]) for t in sells]

    # (1) Carpiklik
    skew_pct = compute_skewness(pnl_pcts)
    skew_tl = compute_skewness(pnl_tls)

    # (2) Win/loss + expectancy + konuslanma
    wl = winloss_stats(pnl_pcts)
    last_date = engine.daily_dates[-1] if engine.daily_dates else None
    intervals = build_holding_intervals(engine.trades, last_date)
    exposure = daily_exposure_stats(intervals, engine.daily_dates, engine.equity_curve)

    # (3) Exit nedeni dagilimi
    reasons: dict = {}
    for t in sells:
        r = t.get("reason", "signal")
        d = reasons.setdefault(r, {"count": 0, "pnl_pcts": [], "total_pnl_tl": 0.0})
        d["count"] += 1
        d["pnl_pcts"].append(float(t["pnl_pct"]))
        d["total_pnl_tl"] += float(t["pnl"])
    exit_dist = {
        r: {
            "count": d["count"],
            "pct_of_trades": round(100.0 * d["count"] / len(sells), 1) if sells else 0.0,
            "avg_pnl_pct": round(100.0 * mean(d["pnl_pcts"]), 2) if d["pnl_pcts"] else 0.0,
            "total_pnl_tl": round(d["total_pnl_tl"], 2),
        }
        for r, d in reasons.items()
    }

    # (4) Runner counterfactual
    runners = analyze_runners(sells, price_data, trail_pcts)

    report = {
        "directive": "D-176",
        "period": f"{args.start} -> {args.end}",
        "reconciliation": rec,
        "exit_thresholds": {
            "profit_target": EXIT_PROFIT_TARGET,
            "stop_loss": EXIT_STOP_LOSS,
            "note": "Backtest'te TP1/2/3 staging YOK — tek seferlik +20% profit_target.",
        },
        "1_skewness": {
            "pnl_pct": round(skew_pct, 3),
            "pnl_tl": round(skew_tl, 3),
            "note": "+20% profit_target sag kuyrugu kirpar -> pozitif carpikligi bastirir.",
        },
        "2_winloss_expectancy": wl,
        "2_capital_deployment": exposure,
        "3_exit_distribution": exit_dist,
        "4_runner_counterfactual": runners,
        "4_caveats": [
            "Downside (stop_loss -8%) SABIT tutuldu; yalniz profit_target upside'i acildi.",
            "Olculen: en-iyi-durum konvekslik UST-SINIRI, beklenen deger DEGIL.",
            "Yorum: '+20% cap ne kadar sag-kuyruk birakti' — 'trailing her zaman iyi' DEGIL.",
            "Whipsaw (erken cikip toparlanma) bu izole testte gorunmez; gercekte olur.",
            "Serbest nakit yeniden konuslanmaz; net fayda bu brut ust-sinirdan dusuktur.",
        ],
    }

    (out_dir / "trade_analysis.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- Konsol ozeti ---
    print(f"\n{sep}\n  SONUCLAR\n{sep}")
    mp = rec.get("match_pct")
    print(f"  Reconciliation : {rec.get('matched','?')}/{rec.get('n_rerun','?')} "
          f"({mp}% trades.csv ile esit)" + ("" if rec.get("csv_found") else "  [CSV YOK]"))
    if mp is not None and mp < 95:
        print("  !! UYARI: dusuk eslesme — yfinance fiyat revizyonu, reason etiketleri suheli.")
    print(f"\n  (1) CARPIKLIK   : pnl_pct skew={skew_pct:+.3f} | pnl_TL skew={skew_tl:+.3f}")
    print(f"  (2) WIN/LOSS    : win={wl['win_rate_pct']}% avg_win={wl['avg_win_pct']}% "
          f"avg_loss={wl['avg_loss_pct']}% payoff={wl['payoff_ratio']} "
          f"E[trade]={wl['expectancy_pct_per_trade']:+}%")
    print(f"      KONUSLANMA  : ort_acik_poz={exposure.get('avg_open_positions')} "
          f"max={exposure.get('max_open_positions')} "
          f"nakit_gun={exposure.get('pct_days_all_cash')}% "
          f"ort_exposure={exposure.get('avg_exposure_pct')}%")
    print("  (3) EXIT DAGILIMI:")
    for r, d in sorted(exit_dist.items(), key=lambda kv: -kv[1]["count"]):
        print(f"      {r:<14} {d['count']:>3} ({d['pct_of_trades']}%)  "
              f"avg={d['avg_pnl_pct']:+}%  toplam={d['total_pnl_tl']:+.0f} TL")
    print(f"  (4) RUNNER (profit_target={runners['n_profit_target']} trade):")
    for trail, d in runners["by_trail"].items():
        print(f"      trail {trail}%: runner={d['runners']} geri-verdi={d['gaveback']} "
              f"ayni={d['same']} | brut_delta={d['gross_delta_tl']:+.0f} TL")
    print(f"\n  Caveat: runner = downside-sabit UST-SINIR, EV degil (whipsaw/redeploy haric).")
    print(f"\n  JSON -> {out_dir / 'trade_analysis.json'}\n{sep}\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="D-176 trade dagilimi analizi")
    ap.add_argument("--start", default=_DEFAULT_START)
    ap.add_argument("--end", default=_DEFAULT_END)
    ap.add_argument("--output-dir", default=_DEFAULT_OUTPUT)
    ap.add_argument("--trail-pcts", default="8,10,15")
    _run(ap.parse_args())


if __name__ == "__main__":
    main()
