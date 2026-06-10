"""Failure notification for daily_update (D-120, operational reliability).

İki sorumluluk:
1. write_failure_file -- logs/failures/ altına traceback'li bir .txt yaz (her zaman)
2. maybe_send_email   -- ALERT_EMAIL tanımlıysa smtplib ile mail at (opsiyonel, graceful)

notify_failure() ikisini birleştirir. Email tamamen opsiyoneldir: ALERT_EMAIL yoksa
sessizce yalnızca dosya yazılır. smtplib hatası asla raise etmez (bildirim, pipeline'ı
ikinci kez düşürmemeli).
"""
from __future__ import annotations

import logging
import os
import smtplib
import traceback
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent.parent
FAILURE_LOG_DIR = ROOT_DIR / "logs" / "failures"


def write_failure_file(
    exc: BaseException,
    context: str = "",
    when: datetime | None = None,
    failure_dir: str | Path | None = None,
) -> Path:
    """logs/failures/failure_YYYY-MM-DD_HHMMSS.txt yaz, path döndür.

    Dosya: timestamp, context, exception tipi+mesajı ve tam traceback içerir.
    """
    when = when or datetime.now()
    out_dir = Path(failure_dir) if failure_dir is not None else FAILURE_LOG_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    fpath = out_dir / f"failure_{when:%Y-%m-%d_%H%M%S}.txt"
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    body = (
        "Sentio — daily_update FAILURE\n"
        f"Timestamp: {when.isoformat()}\n"
        f"Context:   {context}\n"
        f"Exception: {type(exc).__name__}: {exc}\n\n"
        f"Traceback:\n{tb}\n"
    )
    fpath.write_text(body, encoding="utf-8")
    return fpath


def maybe_send_email(subject: str, body: str) -> bool:
    """ALERT_EMAIL tanımlıysa failure mail'i at. Döner: gönderildi mi.

    ALERT_EMAIL yok → False (sessiz, email opsiyonel).
    Transport eksik (SMTP_SERVER/SMTP_PORT/EMAIL_FROM/EMAIL_PASSWORD) → warning + False.
    smtplib hatası → warning + False (asla raise etmez).
    """
    recipient = os.getenv("ALERT_EMAIL")
    if not recipient:
        return False

    server = os.getenv("SMTP_SERVER")
    port = os.getenv("SMTP_PORT")
    sender = os.getenv("EMAIL_FROM")
    password = os.getenv("EMAIL_PASSWORD")
    if not all([server, port, sender, password]):
        logger.warning(
            "ALERT_EMAIL set but SMTP transport incomplete "
            "(SMTP_SERVER/SMTP_PORT/EMAIL_FROM/EMAIL_PASSWORD) — file-only"
        )
        return False

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient
        msg.set_content(body)
        with smtplib.SMTP(server, int(port), timeout=30) as smtp:
            smtp.starttls()
            smtp.login(sender, password)
            smtp.send_message(msg)
        logger.info("Failure alert email sent to %s", recipient)
        return True
    except Exception as exc:  # noqa: BLE001 - notification must never re-raise
        logger.warning("Failure alert email failed (non-fatal): %s", exc)
        return False


def notify_failure(exc: BaseException, context: str = "") -> Path:
    """Failure dosyası yaz (her zaman) + opsiyonel email. Failure dosyası path'ini döner."""
    fpath = write_failure_file(exc, context=context)
    try:
        subject = f"[Sentio] daily_update FAILED — {datetime.now():%Y-%m-%d %H:%M}"
        maybe_send_email(subject, fpath.read_text(encoding="utf-8"))
    except Exception as exc2:  # noqa: BLE001 - notification must never re-raise
        logger.warning("notify_failure email step failed (non-fatal): %s", exc2)
    return fpath
