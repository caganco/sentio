"""Standalone CLI: Fintables takas/MKK custody scraper (D-116).

Kullanım:
    python scripts/scrape_takas.py                    # Bugün tüm BIST50
    python scripts/scrape_takas.py AKSEN THYAO AEFES  # Belirli ticker'lar (bugün)
    python scripts/scrape_takas.py --date 2026-05-20  # Belirli gün, tüm BIST50
    python scripts/scrape_takas.py --backfill         # 90 günlük tarihsel
    python scripts/scrape_takas.py --check            # DB durumu özeti

NOT: playwright opsiyonel. Kurulu değilse scrape/backfill komutları net bir
mesajla çıkar (--check playwright gerektirmez).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.fintables_scraper import FintablesScraperConnector
from src.signals.thresholds import CUSTODY_DB_PATH
from src.utils.logger import setup_logger

logger = setup_logger("scrape_takas")


def _connector(tickers: tuple[str, ...] | None = None) -> FintablesScraperConnector:
    return FintablesScraperConnector(tickers=tickers)


def cmd_scrape(args: argparse.Namespace) -> int:
    """Günlük çekim (varsayılan komut)."""
    tickers = tuple(t.upper() for t in args.tickers) if args.tickers else None
    conn = _connector(tickers=tickers)
    results = conn.scrape_all(date_str=args.date)
    ok = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Takas scrape tamamlandı: {ok}/{total} ticker başarılı")
    return 0 if ok > 0 else 1


def cmd_backfill(args: argparse.Namespace) -> int:
    conn = _connector()
    conn.backfill(days=args.days, force=args.force)
    print("Backfill tamamlandı.")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """DB durumu: ticker başına distinct gün sayısı ve son tarih."""
    db_path = Path(CUSTODY_DB_PATH)
    if not db_path.exists():
        print(f"Custody DB bulunamadı: {db_path}")
        return 1
    from src.data.fintables_scraper import CustodyDBWriter

    writer = CustodyDBWriter(db_path)
    counts = writer.ticker_counts()
    if not counts:
        print(f"Custody DB boş: {db_path}")
        return 0
    print(f"Custody DB: {db_path}  ({len(counts)} ticker)")
    print(f"{'TICKER':<10}{'GÜN':>6}  SON TARİH")
    for ticker, n in counts.items():
        print(f"{ticker:<10}{n:>6}  {writer.get_latest_date(ticker)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fintables Takas/MKK Custody Scraper (D-116)")
    parser.add_argument(
        "tickers", nargs="*",
        help="İsteğe bağlı ticker listesi (ör. AKSEN THYAO). Boşsa BIST50.",
    )
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (varsayılan: bugün)")
    parser.add_argument("--backfill", action="store_true", help="Tarihsel backfill çalıştır")
    parser.add_argument("--days", type=int, default=None, help="Backfill gün sayısı")
    parser.add_argument("--force", action="store_true", help="Backfill: mevcut veriye rağmen yeniden çek")
    parser.add_argument("--check", action="store_true", help="DB durumu özeti (playwright gerekmez)")
    return parser


def main(args: argparse.Namespace) -> int:
    if args.check:
        return cmd_check(args)
    try:
        if args.backfill:
            return cmd_backfill(args)
        return cmd_scrape(args)
    except ImportError as exc:
        print(f"playwright kurulu değil — scrape/backfill çalıştırılamaz: {exc}")
        print("Kurulum: pip install playwright && playwright install chromium")
        return 1
    except ValueError as exc:
        print(f"Yapılandırma hatası: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main(build_parser().parse_args()))
