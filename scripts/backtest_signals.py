"""Backtest RSI 50-65 + MA20 above + volume surge signals with 8% SL / 20% TP."""
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd

from src.utils.config import get_db_path, get_reports_dir
from src.utils.logger import setup_logger

logger = setup_logger("backtest")

STOP_LOSS_PCT = 0.08
PROFIT_TARGET_PCT = 0.20
VOL_SURGE_THRESHOLD = 1.5
RSI_PERIOD = 14
MA_PERIOD = 20
LOOKBACK_DAYS = 730
SEP = "=" * 65


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def load_all_tickers() -> list[str]:
    with sqlite3.connect(get_db_path()) as conn:
        rows = conn.execute("SELECT DISTINCT ticker FROM prices").fetchall()
    return [r[0] for r in rows]


def load_ticker_data(ticker: str) -> pd.DataFrame:
    query = """
        SELECT date, open, high, low, close, volume
        FROM prices WHERE ticker = ?
        ORDER BY date ASC
    """
    with sqlite3.connect(get_db_path()) as conn:
        df = pd.read_sql_query(query, conn, params=(ticker,))
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    df.columns = [c.capitalize() for c in df.columns]
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=LOOKBACK_DAYS)
    return df[df.index >= cutoff]


def backtest_ticker(ticker: str, df: pd.DataFrame) -> list[dict]:
    if len(df) < MA_PERIOD + RSI_PERIOD + 10:
        return []

    df = df.copy()
    df["rsi"] = _rsi(df["Close"], RSI_PERIOD)
    df["ma20"] = df["Close"].rolling(MA_PERIOD).mean()
    df["vol_avg20"] = df["Volume"].rolling(MA_PERIOD).mean().shift(1)
    df["vol_surge"] = df["Volume"] / df["vol_avg20"].replace(0, float("nan"))

    trades = []
    in_position = False
    entry_price = 0.0
    entry_date = None

    for i in range(MA_PERIOD + RSI_PERIOD, len(df)):
        prev = df.iloc[i - 1]
        row = df.iloc[i]

        if not in_position:
            rsi_val = prev["rsi"]
            ma_val = prev["ma20"]
            vs_val = prev["vol_surge"]
            if (
                pd.notna(rsi_val) and 50 <= rsi_val <= 65
                and pd.notna(ma_val) and prev["Close"] > ma_val
                and pd.notna(vs_val) and vs_val >= VOL_SURGE_THRESHOLD
            ):
                in_position = True
                entry_price = float(row["Open"]) if row["Open"] > 0 else float(prev["Close"])
                entry_date = df.index[i]
        else:
            stop = entry_price * (1 - STOP_LOSS_PCT)
            target = entry_price * (1 + PROFIT_TARGET_PCT)
            low, high = float(row["Low"]), float(row["High"])

            if low <= stop:
                result = (stop - entry_price) / entry_price * 100
                trades.append({
                    "ticker": ticker,
                    "entry_date": str(entry_date.date()),
                    "exit_date": str(df.index[i].date()),
                    "entry_price": round(entry_price, 2),
                    "exit_price": round(stop, 2),
                    "result_pct": round(result, 2),
                    "exit_reason": "SL",
                })
                in_position = False
            elif high >= target:
                result = (target - entry_price) / entry_price * 100
                trades.append({
                    "ticker": ticker,
                    "entry_date": str(entry_date.date()),
                    "exit_date": str(df.index[i].date()),
                    "entry_price": round(entry_price, 2),
                    "exit_price": round(target, 2),
                    "result_pct": round(result, 2),
                    "exit_reason": "TP",
                })
                in_position = False

    return trades


def main() -> None:
    print(SEP)
    print("  BIST BACKTEST — RSI 50-65 + MA20 + Volume Surge")
    print(SEP)
    print(f"  Giriş : RSI {RSI_PERIOD}-period 50–65 + Close > MA20 + VolSurge ≥ {VOL_SURGE_THRESHOLD}x")
    print(f"  Çıkış : Stop-Loss %{STOP_LOSS_PCT*100:.0f}  |  Kar Al %{PROFIT_TARGET_PCT*100:.0f}")
    print(f"  Süre  : Son {LOOKBACK_DAYS} gün (~2 yıl)")
    print(SEP)

    tickers = load_all_tickers()
    print(f"\n[1/3] {len(tickers)} hisse taranıyor...")

    all_trades: list[dict] = []
    ticker_stats: list[dict] = []

    for ticker in tickers:
        df = load_ticker_data(ticker)
        if df.empty:
            continue
        trades = backtest_ticker(ticker, df)
        if not trades:
            continue

        all_trades.extend(trades)
        wins = [t for t in trades if t["result_pct"] > 0]
        win_rate = len(wins) / len(trades) * 100
        avg_ret = sum(t["result_pct"] for t in trades) / len(trades)

        ticker_stats.append({
            "ticker": ticker,
            "trades": len(trades),
            "win_rate_pct": round(win_rate, 1),
            "avg_return_pct": round(avg_ret, 2),
            "total_return_pct": round(sum(t["result_pct"] for t in trades), 2),
        })

    print(f"[2/3] {len(all_trades)} işlem / {len(ticker_stats)} hisse bulundu.")

    ticker_stats.sort(key=lambda x: -x["avg_return_pct"])
    today = str(date.today())

    lines = [
        f"# Backtest Sonuçları — {today}",
        "",
        "## Strateji",
        f"- **Giriş:** RSI({RSI_PERIOD}) 50–65 + Close > MA20 + Volume Surge ≥ {VOL_SURGE_THRESHOLD}x",
        f"- **Stop-Loss:** %{STOP_LOSS_PCT*100:.0f}  |  **Kar Al:** %{PROFIT_TARGET_PCT*100:.0f}",
        f"- **Lookback:** {LOOKBACK_DAYS} gün (~2 yıl)",
        "",
        "## Genel Özet",
    ]

    if all_trades:
        total = len(all_trades)
        wins_all = [t for t in all_trades if t["result_pct"] > 0]
        overall_wr = len(wins_all) / total * 100
        overall_avg = sum(t["result_pct"] for t in all_trades) / total
        tp_count = sum(1 for t in all_trades if t["exit_reason"] == "TP")
        sl_count = total - tp_count

        lines += [
            f"| Metrik | Değer |",
            f"|--------|-------|",
            f"| Toplam İşlem | {total} |",
            f"| Win Rate | %{overall_wr:.1f} |",
            f"| Ortalama Getiri | %{overall_avg:+.2f} |",
            f"| TP Çıkışı | {tp_count} (%{tp_count/total*100:.0f}) |",
            f"| SL Çıkışı | {sl_count} (%{sl_count/total*100:.0f}) |",
            f"| Taranan Hisse | {len(ticker_stats)} |",
            "",
            "## Hisse Bazında Sonuçlar (Ort. Getiriye Göre — İlk 30)",
            "",
            "| Hisse | İşlem | Win% | Ort. Getiri | Toplam |",
            "|-------|-------|------|-------------|--------|",
        ]
        for s in ticker_stats[:30]:
            lines.append(
                f"| {s['ticker']} | {s['trades']} | %{s['win_rate_pct']} | %{s['avg_return_pct']:+.2f} | %{s['total_return_pct']:+.2f} |"
            )

        best = ticker_stats[:5]
        worst = sorted(ticker_stats, key=lambda x: x["avg_return_pct"])[:5]

        lines += ["", "## En İyi 5 Hisse", ""]
        for s in best:
            lines.append(
                f"- **{s['ticker']}**: {s['trades']} işlem | Win %{s['win_rate_pct']} | Ort. %{s['avg_return_pct']:+.2f}"
            )

        lines += ["", "## En Kötü 5 Hisse", ""]
        for s in worst:
            lines.append(
                f"- **{s['ticker']}**: {s['trades']} işlem | Win %{s['win_rate_pct']} | Ort. %{s['avg_return_pct']:+.2f}"
            )
    else:
        lines += [
            "Sinyal bulunamadı. Olası nedenler:",
            "- Veritabanında yeterli veri yok (daily_update.py çalıştırıldı mı?)",
            "- Lookback periyodunda eşzamanlı koşullar oluşmadı.",
        ]

    lines += ["", f"---", f"*Oluşturuldu: {today}*"]
    report_text = "\n".join(lines)

    out_path = get_reports_dir() / "backtest_results.md"
    out_path.write_text(report_text, encoding="utf-8")

    print(f"[3/3] Rapor yazıldı: {out_path}")
    print()
    print(report_text)
    print(f"\n{SEP}")


if __name__ == "__main__":
    main()
