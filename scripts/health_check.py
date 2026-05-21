"""Operasyonel health check (D-120).

Kontroller:
1. OS_STATE.md staleness  -- dosya mtime (24h WARNING, 48h CRITICAL)
2. signal_logs tazelik     -- bugün veya dünün parquet'i var mı (flat veya Hive)
3. custody DB              -- son güncelleme (opsiyonel; yoksa graceful)

Çıktı: stdout'a JSON + setup_logger ile human-readable.
Exit code: 0=healthy, 1=warning, 2=critical (check'lerin en yüksek severity'si).

Kullanım:
    python scripts/health_check.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.signals.thresholds import CUSTODY_DB_PATH, SIGNAL_LOG_BASE_PATH
from src.utils.logger import setup_logger
from src.utils.os_state_manager import OS_STATE_PATH

logger = setup_logger("health_check")

ROOT_DIR = Path(__file__).parent.parent
_SIGNAL_LOGS_DIR = ROOT_DIR / SIGNAL_LOG_BASE_PATH
_CUSTODY_DB = ROOT_DIR / CUSTODY_DB_PATH

# severity → exit code
_SEVERITY = {"OK": 0, "INFO": 0, "WARNING": 1, "CRITICAL": 2}
_CODE_TO_STATUS = {0: "OK", 1: "WARNING", 2: "CRITICAL"}

OS_STATE_WARNING_HOURS = 24
OS_STATE_CRITICAL_HOURS = 48


def check_os_state(path: str | Path = OS_STATE_PATH, now: datetime | None = None) -> dict:
    """OS_STATE.md dosya mtime tazeliği.

    NOT: OSStateManager.check_staleness() YAML metadata bloğuna bağlı; OS_STATE.md
    artık hand-maintained Markdown olduğundan kullanılamaz. mtime, daily_update'in
    OS_STATE'i her çalışmada yeniden yazmasının doğru proxy'sidir.
    """
    now = now or datetime.now()
    p = Path(path)
    if not p.exists():
        return {"status": "CRITICAL", "detail": f"OS_STATE.md missing: {p}", "age_hours": None}

    mtime = datetime.fromtimestamp(p.stat().st_mtime)
    age_h = (now - mtime).total_seconds() / 3600.0
    if age_h > OS_STATE_CRITICAL_HOURS:
        status = "CRITICAL"
    elif age_h > OS_STATE_WARNING_HOURS:
        status = "WARNING"
    else:
        status = "OK"
    return {
        "status": status,
        "age_hours": round(age_h, 2),
        "last_modified": mtime.isoformat(),
        "path": str(p),
    }


def check_signal_logs(
    base: str | Path = _SIGNAL_LOGS_DIR, today: date | None = None
) -> dict:
    """Bugün veya dün için signal_logs parquet'i var mı (flat VEYA Hive konvansiyonu)."""
    today = today or date.today()
    base = Path(base)
    for d in (today, today - timedelta(days=1)):
        flat = base / f"{d.isoformat()}.parquet"
        hive = base / f"year={d.year}" / f"month={d.month:02d}" / f"day={d.day:02d}" / "signals.parquet"
        if flat.exists():
            return {"status": "OK", "latest_date": d.isoformat(), "path": str(flat)}
        if hive.exists():
            return {"status": "OK", "latest_date": d.isoformat(), "path": str(hive)}
    return {
        "status": "WARNING",
        "detail": f"No signal_logs parquet for {today} or {today - timedelta(days=1)}",
        "base": str(base),
    }


def check_custody_db(
    path: str | Path = _CUSTODY_DB, now: datetime | None = None
) -> dict:
    """Custody DB son güncelleme (opsiyonel infra → asla CRITICAL'a yükseltmez)."""
    p = Path(path)
    if not p.exists():
        return {"status": "OK", "present": False, "detail": "custody DB not present (optional)"}

    try:
        con = sqlite3.connect(str(p))
        latest, count = con.execute(
            "SELECT MAX(date), COUNT(*) FROM custody_daily_summary"
        ).fetchone()
        con.close()
    except Exception as exc:  # noqa: BLE001 - malformed/foreign DB → warning, not crash
        return {"status": "WARNING", "present": True, "detail": f"custody DB read error: {exc}"}

    if not count:
        return {"status": "OK", "present": True, "rows": 0, "detail": "custody DB empty (no data yet)"}
    return {"status": "OK", "present": True, "rows": int(count), "latest_date": latest}


def run_health_check(
    os_state_path: str | Path = OS_STATE_PATH,
    signal_logs_base: str | Path = _SIGNAL_LOGS_DIR,
    custody_db_path: str | Path = _CUSTODY_DB,
    now: datetime | None = None,
    today: date | None = None,
) -> tuple[dict, int]:
    """Tüm check'leri çalıştır. Döner: (rapor dict, exit_code)."""
    now = now or datetime.now()
    today = today or now.date()
    checks = {
        "os_state": check_os_state(os_state_path, now=now),
        "signal_logs": check_signal_logs(signal_logs_base, today=today),
        "custody_db": check_custody_db(custody_db_path, now=now),
    }
    exit_code = max(_SEVERITY.get(c["status"], 0) for c in checks.values())
    report = {
        "status": _CODE_TO_STATUS[exit_code],
        "timestamp": now.isoformat(),
        "checks": checks,
    }
    return report, exit_code


def main() -> int:
    report, exit_code = run_health_check()
    print(json.dumps(report, indent=2, default=str))

    for name, c in report["checks"].items():
        detail = c.get("detail") or {k: v for k, v in c.items() if k != "status"}
        msg = f"[{c['status']}] {name}: {detail}"
        if c["status"] == "CRITICAL":
            logger.error(msg)
        elif c["status"] == "WARNING":
            logger.warning(msg)
        else:
            logger.info(msg)
    logger.info("Health check overall: %s (exit %d)", report["status"], exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
