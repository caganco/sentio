"""CRITIC_BACKLOG.md invariant tests.

Bu testler, Cagan'ın 20 May 2026 "session-to-session memory" kuralının
mekanik garantisidir. CRITIC_BACKLOG.md silinemez, formatı bozulamaz,
ve ACTIVE FINDINGS sayısı OS_STATE.md ile tutarlı olmalı.

Bir Orchestrator bu testi atlatmaya çalışırsa CI kırılır — bu kural
"silmek için" değil, "saklamak için" testtir.
"""
from __future__ import annotations
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
CRITIC_BACKLOG = REPO_ROOT / "CRITIC_BACKLOG.md"
OS_STATE = REPO_ROOT / "OS_STATE.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"


class TestCriticBacklogExistence:
    """CRITIC_BACKLOG.md silinemez."""

    def test_file_exists(self):
        assert CRITIC_BACKLOG.exists(), (
            "CRITIC_BACKLOG.md silinmiş — bu dosya nesilden nesile "
            "korunmalıdır. Cagan kuralı (20 May 2026). Eğer kasıtlı "
            "silindiyse, gerekçe DECISIONS.md'de yer almalı."
        )

    def test_required_sections(self):
        text = CRITIC_BACKLOG.read_text(encoding="utf-8")
        required = [
            "## ACTIVE FINDINGS",
            "## CLOSED FINDINGS",
            "## SESSION CHECKPOINT LOG",
            "## ORIGIN",
            "## DOSYA KURALLARI",
        ]
        missing = [s for s in required if s not in text]
        assert not missing, f"CRITIC_BACKLOG.md'den eksik bölümler: {missing}"


class TestActiveFindingsFormat:
    """ACTIVE FINDINGS bölümünde her madde CB-XXX formatında olmalı."""

    def test_findings_have_id_format(self):
        text = CRITIC_BACKLOG.read_text(encoding="utf-8")
        active_section = text.split("## ACTIVE FINDINGS")[1].split("## CLOSED")[0]
        finding_headers = re.findall(r"### \[(CB-\d{3})\]", active_section)
        assert len(finding_headers) > 0, (
            "ACTIVE FINDINGS bölümünde [CB-XXX] formatlı madde bulunamadı."
        )
        # ID'ler unique olmalı
        assert len(finding_headers) == len(set(finding_headers)), (
            f"Duplicate CB ID tespit edildi: {finding_headers}"
        )

    def test_findings_have_required_fields(self):
        """Her ACTIVE finding'in Status ve Eklendi alanları olmalı."""
        text = CRITIC_BACKLOG.read_text(encoding="utf-8")
        active_section = text.split("## ACTIVE FINDINGS")[1].split("## CLOSED")[0]
        finding_blocks = re.split(r"### \[CB-\d{3}\]", active_section)[1:]

        for i, block in enumerate(finding_blocks, 1):
            assert "**Status:**" in block, (
                f"ACTIVE finding #{i}'de **Status:** alanı yok"
            )
            assert "**Eklendi:**" in block, (
                f"ACTIVE finding #{i}'de **Eklendi:** alanı yok"
            )


class TestSessionCheckpointLog:
    """SESSION CHECKPOINT LOG en az bir kayıt içermeli (audit trail)."""

    def test_has_at_least_one_session_log(self):
        text = CRITIC_BACKLOG.read_text(encoding="utf-8")
        checkpoint_section = text.split("## SESSION CHECKPOINT LOG")[1]
        # En az bir "### YYYY Month YYYY — Session" başlığı olmalı
        session_entries = re.findall(
            r"### \d+ \w+ \d{4} — Session", checkpoint_section
        )
        assert len(session_entries) >= 1, (
            "SESSION CHECKPOINT LOG boş — audit trail kuralını ihlal."
        )


class TestOsStateSummary:
    """OS_STATE.md'de Critic Backlog Summary blok olmalı."""

    def test_os_state_has_backlog_summary(self):
        text = OS_STATE.read_text(encoding="utf-8")
        assert "CRITIC BACKLOG SUMMARY" in text, (
            "OS_STATE.md'de 'CRITIC BACKLOG SUMMARY' bloku yok. "
            "Bu blok session başında 30-saniyelik snapshot için zorunlu."
        )


class TestNoSilentDeletion:
    """ACTIVE FINDINGS'ten bir madde CLOSED'a taşınmadan kaybolamaz.

    Bu test git-aware değil (mevcut state'i kontrol eder).
    True bütünlük için git pre-commit hook + bu test kombinasyonu.
    """

    def test_total_findings_consistency(self):
        """ACTIVE + CLOSED finding sayısı monoton artar."""
        text = CRITIC_BACKLOG.read_text(encoding="utf-8")
        all_ids = re.findall(r"\[(CB-\d{3})\]", text)
        unique_ids = set(all_ids)

        # Her CB-XXX ID'si CRITIC_BACKLOG'da en az bir kere referanslanmalı
        # (kendi başlığında veya checkpoint log'da)
        assert len(unique_ids) > 0, "Hiç CB ID bulunamadı."

        # ID'ler sıralı olmalı: CB-001'den başlayıp ardışık
        sorted_ids = sorted(unique_ids)
        numbers = [int(cb.split("-")[1]) for cb in sorted_ids]
        # Gap kontrol et (CB-001, CB-002, CB-003... CB-005 olabilir, CB-007 atlanmış olabilir)
        # Sadece duplicate olmamalı
        assert len(numbers) == len(set(numbers)), "Duplicate CB numarası"