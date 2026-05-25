#!/usr/bin/env python3
"""RETRACT eski backtest raporları + drift raporu üret (D-149b, RR-018 §8.4 Faz 1b).
C-1 CLOSED: D-149e merge (2026-05-25) — AUDIT_REPORT_001 referans.

Bu script iki iş yapar:
1. Eski backtest raporlarının başına RETRACT NOTICE ekler
   (backtest/engine.py L3/L4/L5 = 50.0 neutral stub divergence).
2. data/analytics/drift_report_<tarih>.json üretir
   (sinyal verisi yoksa boş rapor, non-fatal).

Idempotent: "RETRACT NOTICE" / "retract_notice" zaten varsa dosyayı atlar.
Kayıp dosyalar için warning log yazıp devam eder (reports/ gitignored).

Dayanak: SPEC_BACKTEST_FRAMEWORK_1 §B1-S2, §B1-S5; RR-018 §8.4 Faz 1b

Kullanım:
    python scripts/retract_old_backtest_reports.py
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent

RETRACT_HEADER = """> ⚠️ RETRACT NOTICE — Bu rapor backtest/engine.py'nin
> L3/L4/L5 = 50.0 (neutral, %52 ağırlık) hardcode versiyonuyla
> üretildi. Production engine davranışını yansıtmıyor.
> Geçerli rapor: D-149d tamamlandıktan sonra reports/backtest/v2/'de.
> İşaretleyen: SPEC_BACKTEST_FRAMEWORK_1, 2026-05-25

---

"""

RETRACT_NOTICE_JSON = (
    "Bu rapor backtest/engine.py L3/L4/L5=50.0 (neutral, %52 ağırlık) "
    "versiyonuyla üretildi. Production engine davranışını yansıtmıyor. "
    "Geçerli rapor: D-149d sonrası reports/backtest/v2/."
)

RETRACT_REASON = "L3/L4/L5 neutral stub 50.0 — prod diverge"

# Hedef Markdown raporları (içerik DEĞİŞMEZ — sadece başa header eklenir)
RETRACT_MD_FILES: list[str] = [
    "reports/D-038_SHARPE_RECALIBRATION.md",
    "reports/D-046_MACRO_GATED_BACKTEST_REPORT.md",
    "reports/D-046_ORCHESTRATOR_SUMMARY.md",
    "reports/D-047_AUDIT_TRAIL_ANALYSIS.md",
    "reports/D-047_FINAL_AUDIT_ANALYSIS.md",
    "reports/D-048_ALPHA_ANALYSIS.md",
    "reports/D-049_BASELINES.md",
    "reports/D-050_BEAR_TEST.md",
    "reports/backtest_results.md",
]

# JSON raporları — retract_notice dict alanı eklenir (Markdown header geçersiz JSON üretir)
RETRACT_JSON_FILES: list[str] = [
    "reports/D-048_REAL_ALPHA.json",
    "reports/backtest/backtest_with_sentiment_2024_2026.json",
]

SUMMARY_JSON = "reports/backtest/summary.json"


# ---------------------------------------------------------------------------
# RETRACT işlemleri
# ---------------------------------------------------------------------------

def retract_markdown(path: Path) -> None:
    """Markdown dosyasının başına RETRACT NOTICE header ekle (idempotent)."""
    if not path.exists():
        logger.warning("Dosya yok, atlanıyor: %s", path.relative_to(REPO_ROOT))
        return
    content = path.read_text(encoding="utf-8")
    if "RETRACT NOTICE" in content:
        logger.info("Zaten işaretli, atlanıyor: %s", path.relative_to(REPO_ROOT))
        return
    path.write_text(RETRACT_HEADER + content, encoding="utf-8")
    logger.info("✓ RETRACT eklendi: %s", path.relative_to(REPO_ROOT))


def retract_json(path: Path) -> None:
    """JSON dosyasına retract_notice alanı ekle (idempotent).

    Geçerli JSON'da satır başı yorum desteklenmez; retract_notice dict alanı
    kullanılır. Liste ise wrapper dict'e sarılır.
    """
    if not path.exists():
        logger.warning("Dosya yok, atlanıyor: %s", path.relative_to(REPO_ROOT))
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("JSON parse hatası (%s): %s — atlanıyor", path.name, exc)
        return
    if isinstance(data, dict):
        if "retract_notice" in data:
            logger.info("Zaten işaretli, atlanıyor: %s", path.relative_to(REPO_ROOT))
            return
        new_data = {"retract_notice": RETRACT_NOTICE_JSON, **data}
    elif isinstance(data, list):
        # Liste başı dict kontrolü
        if data and isinstance(data[0], dict) and "retract_notice" in data[0]:
            logger.info("Zaten işaretli, atlanıyor: %s", path.relative_to(REPO_ROOT))
            return
        new_data = {"retract_notice": RETRACT_NOTICE_JSON, "data": data}
    else:
        logger.warning(
            "Beklenmeyen JSON tipi (%s): %s — atlanıyor",
            type(data).__name__,
            path.name,
        )
        return
    path.write_text(json.dumps(new_data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("✓ RETRACT (JSON) eklendi: %s", path.relative_to(REPO_ROOT))


def update_summary_json(path: Path) -> None:
    """summary.json'a retract_reason alanı ekle; dosya yoksa oluştur."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            data = {}
    else:
        data = {}
    if data.get("retract_reason") == RETRACT_REASON:
        logger.info("retract_reason zaten var: %s", path.relative_to(REPO_ROOT))
        return
    data["retract_reason"] = RETRACT_REASON
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("✓ retract_reason eklendi: %s", path.relative_to(REPO_ROOT))


# ---------------------------------------------------------------------------
# Drift raporu
# ---------------------------------------------------------------------------

def generate_drift_report() -> None:
    """data/analytics/drift_report_<tarih>.json üret.

    Signal logs mevcut değilse boş rapor üretilir (non-fatal, SPEC §B1-S2).
    D-149c tamamlandıktan sonra sinyal pipeline'ı aktive edilecek.
    """
    analytics_dir = REPO_ROOT / "data" / "analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    out_path = analytics_dir / f"drift_report_{today}.json"

    signal_logs_dir = REPO_ROOT / "data" / "signal_logs"
    entries_available = signal_logs_dir.exists() and any(signal_logs_dir.glob("*.json"))

    if not entries_available:
        report = {
            "generated_at": today,
            "period_days": 30,
            "note": (
                "data/signal_logs/ mevcut değil veya boş — sinyal verisi yok. "
                "Boş rapor (SPEC_BACKTEST_FRAMEWORK_1 §B1-S2 non-fatal). "
                "D-149c sonrası sinyal pipeline aktive edilecek."
            ),
            "total_days": 0,
            "mismatch_count": 0,
            "avg_delta": None,
            "max_delta_ticker": None,
            "max_delta_day": None,
            "entries": [],
        }
    else:
        # TODO: D-149c sonrası implement edilecek (sinyal log parse + delta hesap)
        report = {
            "generated_at": today,
            "period_days": 30,
            "note": "Sinyal log parse pipeline D-149c'de implement edilecek.",
            "total_days": 0,
            "mismatch_count": 0,
            "avg_delta": None,
            "max_delta_ticker": None,
            "max_delta_day": None,
            "entries": [],
        }

    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("✓ Drift raporu üretildi: %s", out_path.relative_to(REPO_ROOT))


# ---------------------------------------------------------------------------
# Giriş noktası
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=== D-149b RETRACT + Drift raporu başlıyor ===")
    logger.info("Not: reports/ gitignored — kayıp dosyalar warning ile geçilir.")

    # 1. Markdown dosyaları RETRACT
    for rel in RETRACT_MD_FILES:
        retract_markdown(REPO_ROOT / rel)

    # 2. JSON dosyaları RETRACT (retract_notice field)
    for rel in RETRACT_JSON_FILES:
        retract_json(REPO_ROOT / rel)

    # 3. summary.json retract_reason
    update_summary_json(REPO_ROOT / SUMMARY_JSON)

    # 4. Drift raporu
    generate_drift_report()

    logger.info("=== D-149b tamamlandı ===")


if __name__ == "__main__":
    main()
