"""DB & log backup + retention (D-120).

- custody DB    → data/backups/custody_YYYY-MM-DD.db
- signal_logs/  → data/backups/signal_logs_YYYY-MM-DD/  (kopya ağaç)
- 30 günden eski backup'lar silinir
- Kaynak veri yoksa graceful (sessizce atlar, hata vermez)

Kullanım:
    python scripts/backup_db.py
"""
from __future__ import annotations

import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.signals.thresholds import CUSTODY_DB_PATH, SIGNAL_LOG_BASE_PATH
from src.utils.logger import setup_logger

logger = setup_logger("backup_db")

ROOT_DIR = Path(__file__).parent.parent
_CUSTODY_DB = ROOT_DIR / CUSTODY_DB_PATH
_SIGNAL_LOGS_DIR = ROOT_DIR / SIGNAL_LOG_BASE_PATH
_BACKUP_DIR = ROOT_DIR / "data" / "backups"

BACKUP_RETENTION_DAYS = 30
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def backup_custody(
    src: str | Path = _CUSTODY_DB,
    backup_dir: str | Path = _BACKUP_DIR,
    today: date | None = None,
) -> Path | None:
    """custody DB'yi data/backups/custody_YYYY-MM-DD.db'ye kopyala. Yoksa None."""
    today = today or date.today()
    src = Path(src)
    if not src.exists():
        logger.info("custody DB yok, backup atlandı: %s", src)
        return None
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest = backup_dir / f"custody_{today.isoformat()}.db"
    shutil.copy2(src, dest)
    logger.info("custody DB backup -> %s", dest)
    return dest


def backup_signal_logs(
    src: str | Path = _SIGNAL_LOGS_DIR,
    backup_dir: str | Path = _BACKUP_DIR,
    today: date | None = None,
) -> Path | None:
    """signal_logs/ ağacını data/backups/signal_logs_YYYY-MM-DD/'ye kopyala. Yok/boşsa None."""
    today = today or date.today()
    src = Path(src)
    if not src.exists() or not any(src.iterdir()):
        logger.info("signal_logs yok/boş, backup atlandı: %s", src)
        return None
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest = backup_dir / f"signal_logs_{today.isoformat()}"
    shutil.copytree(src, dest, dirs_exist_ok=True)
    logger.info("signal_logs backup -> %s", dest)
    return dest


def _parse_backup_date(name: str) -> date | None:
    m = _DATE_RE.search(name)
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:
        return None


def prune_old_backups(
    backup_dir: str | Path = _BACKUP_DIR,
    keep_days: int = BACKUP_RETENTION_DAYS,
    now: datetime | None = None,
) -> list[Path]:
    """keep_days'ten eski backup'ları sil. Silinen path'leri döner."""
    now = now or datetime.now()
    backup_dir = Path(backup_dir)
    if not backup_dir.exists():
        return []
    cutoff = (now - timedelta(days=keep_days)).date()
    deleted: list[Path] = []
    for item in backup_dir.iterdir():
        d = _parse_backup_date(item.name)
        if d is None or d >= cutoff:
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
        deleted.append(item)
        logger.info("eski backup silindi (%s < %s): %s", d, cutoff, item)
    return deleted


def run_backup() -> dict:
    """custody + signal_logs backup + prune. Döner: özet dict."""
    return {
        "custody": backup_custody(),
        "signal_logs": backup_signal_logs(),
        "pruned": prune_old_backups(),
    }


def main() -> int:
    s = run_backup()
    print("Backup tamamlandı:")
    print(f"  custody:     {s['custody'] or 'veri yok (atlandı)'}")
    print(f"  signal_logs: {s['signal_logs'] or 'veri yok (atlandı)'}")
    print(f"  pruned:      {len(s['pruned'])} eski backup silindi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
