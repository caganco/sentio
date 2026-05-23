"""Standalone CLI: İş Yatırım foreign-flow bridge (D-126, §17).

Robots-güvenli `getScreenerDataNEW` üzerinden yabancı oran (foreign_ratio) +
~30g değişim verisini data/foreign_flow/isyatirim.db'ye köprüler. Doğrudan
foreign-flow endpoint'i (robots-yasaklı + 401 + ToS gri zon) KULLANILMAZ.

Kullanım:
    python scripts/fetch_foreign_flow.py                    # Bugün tüm screener ticker'ları
    python scripts/fetch_foreign_flow.py AKSEN THYAO        # Belirli ticker'lar (bugün)
    python scripts/fetch_foreign_flow.py --date 2026-05-20  # Belirli gün
    python scripts/fetch_foreign_flow.py --check            # DB durumu özeti

Gün-1 sentetik seed: geçmişi olmayan ticker için ilk çekimde bugün + bugün-30g
(= foreign_ratio - change_1m_pp) yazılır → change_30d_score ilk günden çalışır.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.isyatirim_scraper import ForeignFlowConnector
from src.utils.logger import setup_logger

logger = setup_logger("fetch_foreign_flow")


def cmd_fetch(args: argparse.Namespace) -> int:
    """Günlük çekim (varsayılan komut)."""
    tickers = tuple(t.upper() for t in args.tickers) if args.tickers else None
    conn = ForeignFlowConnector(tickers=tickers)
    results = conn.fetch_and_store(date_str=args.date)
    ok = sum(1 for v in results.values() if v)
    print(f"Foreign flow çekim: {ok}/{len(results)} ticker yazıldı ({args.date or 'bugün'})")
    if not results:
        print("  UYARI: screener boş döndü (soft-block/network) — veri yazılmadı.")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """DB durumu özeti (network gerektirmez)."""
    conn = ForeignFlowConnector()
    counts = conn.writer.ticker_counts()
    if not counts:
        print("isyatirim.db boş (henüz veri yok).")
        return 0
    print(f"isyatirim.db: {len(counts)} ticker")
    for ticker, n in list(counts.items())[:50]:
        print(f"  {ticker}: {n} gün")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="İş Yatırım foreign-flow bridge (D-126)")
    parser.add_argument("tickers", nargs="*", help="Ticker(lar); boşsa tüm screener ticker'ları")
    parser.add_argument("--date", help="YYYY-MM-DD (varsayılan: bugün)")
    parser.add_argument("--check", action="store_true", help="DB durumu özeti (network yok)")
    args = parser.parse_args()

    if args.check:
        return cmd_check(args)
    return cmd_fetch(args)


if __name__ == "__main__":
    sys.exit(main())
