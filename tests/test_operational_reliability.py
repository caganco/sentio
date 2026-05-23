"""Tests for D-120 operational reliability (health_check, backup_db, failure_notifier).

Tüm testler tmp_path + monkeypatch kullanır — network/gerçek SMTP yok.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta

import pytest

import src.utils.failure_notifier as fn
from scripts.backup_db import (
    backup_custody,
    backup_signal_logs,
    prune_old_backups,
)
from scripts.health_check import (
    check_custody_db,
    check_os_state,
    check_signal_logs,
    run_health_check,
)
from src.data.fintables_scraper import CustodyDailySummary, CustodyDBWriter
from src.utils.failure_notifier import (
    maybe_send_email,
    notify_failure,
    write_failure_file,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_mtime(path, hours_ago: float) -> None:
    ts = (datetime.now() - timedelta(hours=hours_ago)).timestamp()
    os.utime(path, (ts, ts))


def _raise_boom() -> Exception:
    try:
        raise ValueError("boom — pipeline broke")
    except ValueError as exc:
        return exc


# ---------------------------------------------------------------------------
# failure_notifier
# ---------------------------------------------------------------------------

def test_write_failure_file_creates_file_with_traceback(tmp_path):
    exc = _raise_boom()
    fpath = write_failure_file(exc, context="unit test", failure_dir=tmp_path)
    assert fpath.exists()
    assert fpath.name.startswith("failure_") and fpath.suffix == ".txt"
    content = fpath.read_text(encoding="utf-8")
    assert "ValueError: boom" in content
    assert "Traceback" in content
    assert "unit test" in content


def test_maybe_send_email_silent_when_no_alert_email(monkeypatch):
    monkeypatch.delenv("ALERT_EMAIL", raising=False)
    assert maybe_send_email("subj", "body") is False


def test_maybe_send_email_false_when_transport_incomplete(monkeypatch):
    monkeypatch.setenv("ALERT_EMAIL", "ops@example.com")
    for k in ("SMTP_SERVER", "SMTP_PORT", "EMAIL_FROM", "EMAIL_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    # Transport eksik → gönderim denenmez, False döner (raise etmez)
    assert maybe_send_email("subj", "body") is False


def test_notify_failure_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(fn, "FAILURE_LOG_DIR", tmp_path)
    monkeypatch.delenv("ALERT_EMAIL", raising=False)
    exc = _raise_boom()
    fpath = notify_failure(exc, context="daily_update test")
    assert fpath.exists()
    assert fpath.parent == tmp_path
    assert "boom" in fpath.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# health_check — OS_STATE staleness (mtime)
# ---------------------------------------------------------------------------

def test_check_os_state_fresh(tmp_path):
    p = tmp_path / "OS_STATE.md"
    p.write_text("x", encoding="utf-8")
    _set_mtime(p, hours_ago=1)
    r = check_os_state(p)
    assert r["status"] == "OK"
    assert r["age_hours"] < 24


def test_check_os_state_warning(tmp_path):
    p = tmp_path / "OS_STATE.md"
    p.write_text("x", encoding="utf-8")
    _set_mtime(p, hours_ago=30)
    assert check_os_state(p)["status"] == "WARNING"


def test_check_os_state_critical_stale(tmp_path):
    p = tmp_path / "OS_STATE.md"
    p.write_text("x", encoding="utf-8")
    _set_mtime(p, hours_ago=50)
    assert check_os_state(p)["status"] == "CRITICAL"


def test_check_os_state_missing(tmp_path):
    r = check_os_state(tmp_path / "nope.md")
    assert r["status"] == "CRITICAL"
    assert r["age_hours"] is None


# ---------------------------------------------------------------------------
# health_check — signal_logs freshness
# ---------------------------------------------------------------------------

def test_check_signal_logs_today_present(tmp_path):
    today = date(2026, 5, 21)
    (tmp_path / f"{today.isoformat()}.parquet").touch()
    r = check_signal_logs(tmp_path, today=today)
    assert r["status"] == "OK"
    assert r["latest_date"] == "2026-05-21"


def test_check_signal_logs_yesterday_present(tmp_path):
    today = date(2026, 5, 21)
    (tmp_path / "2026-05-20.parquet").touch()
    r = check_signal_logs(tmp_path, today=today)
    assert r["status"] == "OK"
    assert r["latest_date"] == "2026-05-20"


def test_check_signal_logs_hive_present(tmp_path):
    today = date(2026, 5, 21)
    hive = tmp_path / "year=2026" / "month=05" / "day=21"
    hive.mkdir(parents=True)
    (hive / "signals.parquet").touch()
    assert check_signal_logs(tmp_path, today=today)["status"] == "OK"


def test_check_signal_logs_missing(tmp_path):
    r = check_signal_logs(tmp_path, today=date(2026, 5, 21))
    assert r["status"] == "WARNING"


# ---------------------------------------------------------------------------
# health_check — custody DB (optional)
# ---------------------------------------------------------------------------

def test_check_custody_db_missing_graceful(tmp_path):
    r = check_custody_db(tmp_path / "nope.db")
    assert r["status"] == "OK"
    assert r["present"] is False


def test_check_custody_db_with_data(tmp_path):
    db = tmp_path / "custody.db"
    writer = CustodyDBWriter(db)
    writer.upsert_summary(CustodyDailySummary(
        date="2026-05-21", ticker="AKSEN", yabanci_toplam_pct=42.0,
        kurumsal_pct=None, bireysel_pct=None, toplam_yatirimci_sayisi=None,
        scraped_at=datetime.now().isoformat(),
    ))
    r = check_custody_db(db)
    assert r["status"] == "OK"
    assert r["present"] is True
    assert r["rows"] == 1
    assert r["latest_date"] == "2026-05-21"


# ---------------------------------------------------------------------------
# health_check — orchestration & exit codes
# ---------------------------------------------------------------------------

def _fresh_state(tmp_path):
    """OS_STATE fresh + today's signal_logs → healthy fixture."""
    os_state = tmp_path / "OS_STATE.md"
    os_state.write_text("x", encoding="utf-8")
    _set_mtime(os_state, hours_ago=1)
    logs = tmp_path / "signal_logs"
    logs.mkdir()
    today = date(2026, 5, 21)
    (logs / f"{today.isoformat()}.parquet").touch()
    return os_state, logs, today


def test_run_health_check_all_ok_exit_0(tmp_path):
    os_state, logs, today = _fresh_state(tmp_path)
    report, code = run_health_check(
        os_state_path=os_state, signal_logs_base=logs,
        custody_db_path=tmp_path / "nope.db",
        now=datetime(2026, 5, 21, 12, 0), today=today,
    )
    assert code == 0
    assert report["status"] == "OK"


def test_run_health_check_warning_exit_1(tmp_path):
    os_state, _, today = _fresh_state(tmp_path)
    report, code = run_health_check(
        os_state_path=os_state,
        signal_logs_base=tmp_path / "empty_logs",  # yok → WARNING
        custody_db_path=tmp_path / "nope.db",
        now=datetime(2026, 5, 21, 12, 0), today=today,
    )
    assert code == 1
    assert report["status"] == "WARNING"


def test_run_health_check_critical_exit_2(tmp_path):
    _, logs, today = _fresh_state(tmp_path)
    report, code = run_health_check(
        os_state_path=tmp_path / "missing_os_state.md",  # yok → CRITICAL
        signal_logs_base=logs,
        custody_db_path=tmp_path / "nope.db",
        now=datetime(2026, 5, 21, 12, 0), today=today,
    )
    assert code == 2
    assert report["status"] == "CRITICAL"


def test_run_health_check_report_json_serializable(tmp_path):
    os_state, logs, today = _fresh_state(tmp_path)
    report, _ = run_health_check(
        os_state_path=os_state, signal_logs_base=logs,
        custody_db_path=tmp_path / "nope.db",
        now=datetime(2026, 5, 21, 12, 0), today=today,
    )
    # default=str → datetime/Path güvenli
    assert json.dumps(report, default=str)


# ---------------------------------------------------------------------------
# backup_db
# ---------------------------------------------------------------------------

def test_backup_custody_copies(tmp_path):
    src = tmp_path / "custody.db"
    src.write_bytes(b"sqlite-bytes")
    backup_dir = tmp_path / "backups"
    dest = backup_custody(src=src, backup_dir=backup_dir, today=date(2026, 5, 21))
    assert dest is not None
    assert dest.exists()
    assert dest.name == "custody_2026-05-21.db"
    assert dest.read_bytes() == b"sqlite-bytes"


def test_backup_custody_missing_returns_none(tmp_path):
    assert backup_custody(src=tmp_path / "nope.db", backup_dir=tmp_path / "b") is None


def test_backup_signal_logs_copytree(tmp_path):
    src = tmp_path / "signal_logs"
    src.mkdir()
    (src / "2026-05-21.parquet").write_bytes(b"pq")
    backup_dir = tmp_path / "backups"
    dest = backup_signal_logs(src=src, backup_dir=backup_dir, today=date(2026, 5, 21))
    assert dest is not None
    assert (dest / "2026-05-21.parquet").exists()


def test_backup_signal_logs_empty_returns_none(tmp_path):
    empty = tmp_path / "signal_logs"
    empty.mkdir()
    assert backup_signal_logs(src=empty, backup_dir=tmp_path / "b") is None
    assert backup_signal_logs(src=tmp_path / "missing", backup_dir=tmp_path / "b") is None


def test_prune_old_backups_deletes_old_keeps_recent(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    # old (>30d before 2026-05-21): 2026-04-01
    (backup_dir / "custody_2026-04-01.db").write_bytes(b"old")
    old_dir = backup_dir / "signal_logs_2026-04-01"
    old_dir.mkdir()
    (old_dir / "x.parquet").touch()
    # recent: 2026-05-20
    (backup_dir / "custody_2026-05-20.db").write_bytes(b"new")

    deleted = prune_old_backups(backup_dir, keep_days=30, now=datetime(2026, 5, 21, 12, 0))

    deleted_names = {p.name for p in deleted}
    assert "custody_2026-04-01.db" in deleted_names
    assert "signal_logs_2026-04-01" in deleted_names
    assert not (backup_dir / "custody_2026-04-01.db").exists()
    assert not old_dir.exists()
    assert (backup_dir / "custody_2026-05-20.db").exists()  # recent kept


def test_prune_ignores_unparseable_names(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    (backup_dir / "readme.txt").write_text("not a backup", encoding="utf-8")
    deleted = prune_old_backups(backup_dir, keep_days=30, now=datetime(2026, 5, 21))
    assert deleted == []
    assert (backup_dir / "readme.txt").exists()
