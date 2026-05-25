"""Backtest-production parity tests (D-149a, RR-018 §8.4 Faz 1a).

Bu dosya iki amaca hizmet eder:
1. Mevcut divergence miktarını matematiksel olarak belgeler (kanıt + log).
2. Gelecek fix testlerini skip işaretli yer tutar (D-149c / D-149d aktive eder).

Mevcut durum (D-149a):
- L3/L4/L5 neutral stub: 50.0 (veri kısıtı — intentional)
- Toplam divergence kapsamı: %52 (MASTER_WEIGHTS["kap"]+["sentiment"]+["smart_money"])
- Hardcoded değerler: 0.92 / 1.20 / -0.15 (D-149d'de kaldırılacak)

Test sınıfları:
  TestBacktestNeutralStubMath  (6): neutral stub matematiği
  TestDivergenceLog            (1): 5 senaryo için divergence log
  TestSignalThresholdConsistency (3): SIGNAL_THRESHOLDS import kontrolü
  TestParityFutureChecks       (3): D-149c/D-149d için skip-marked yer tutucular
Toplam: 13 test (10 PASS + 3 SKIP)
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest

from src.signals.thresholds import MASTER_WEIGHTS, SIGNAL_THRESHOLDS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pure-math helper fonksiyonlar — engine instantiation gerektirmez
# ---------------------------------------------------------------------------

def _bt_composite(tech: float, macro: float, risk: float) -> float:
    """Backtest composite formula: L3/L4/L5 = 50.0 neutral stub.

    backtest/engine.py _compute_composite() satır 217-226 ile özdeş.
    """
    return max(0.0, min(100.0,
        tech * MASTER_WEIGHTS["technical"]
        + macro * MASTER_WEIGHTS["macro"]
        + risk * MASTER_WEIGHTS["risk"]
        + 50.0 * (
            MASTER_WEIGHTS["kap"]
            + MASTER_WEIGHTS["sentiment"]
            + MASTER_WEIGHTS["smart_money"]
        )
    ))


def _prod_composite(
    tech: float,
    macro: float,
    kap: float,
    sentiment: float,
    smart_money: float,
    risk: float,
) -> float:
    """Production composite formula: full 6-layer weighted sum.

    src/signals/engine.py _compute_weighted_sum() ile özdeş yapı.
    """
    return max(0.0, min(100.0,
        tech * MASTER_WEIGHTS["technical"]
        + macro * MASTER_WEIGHTS["macro"]
        + kap * MASTER_WEIGHTS["kap"]
        + sentiment * MASTER_WEIGHTS["sentiment"]
        + smart_money * MASTER_WEIGHTS["smart_money"]
        + risk * MASTER_WEIGHTS["risk"]
    ))


# ---------------------------------------------------------------------------
# TestBacktestNeutralStubMath (6 test — tümü PASSING)
# ---------------------------------------------------------------------------

class TestBacktestNeutralStubMath:
    """L3/L4/L5 neutral stub'ının matematiksel özelliklerini doğrular (D-149a)."""

    def test_neutral_stub_weight_fraction(self):
        """L3/L4/L5 toplam ağırlığı %52 — mevcut divergence kapsamı.

        MASTER_WEIGHTS["kap"]=0.30 + ["sentiment"]=0.12 + ["smart_money"]=0.10 = 0.52
        Bu, toplam sinyalin %52'sinin backtest'te daima sabit kaldığı anlamına gelir.
        """
        neutral_weight = (
            MASTER_WEIGHTS["kap"]
            + MASTER_WEIGHTS["sentiment"]
            + MASTER_WEIGHTS["smart_money"]
        )
        assert neutral_weight == pytest.approx(0.52, abs=0.001)

    def test_neutral_stub_contribution_at_50(self):
        """50.0 neutral stub → composite'e 26.0 puan sabit katkı.

        50.0 × 0.52 = 26.0 puan — backtest'te L3/L4/L5 daima bu değeri katkılar.
        """
        contribution = 50.0 * (
            MASTER_WEIGHTS["kap"]
            + MASTER_WEIGHTS["sentiment"]
            + MASTER_WEIGHTS["smart_money"]
        )
        assert contribution == pytest.approx(26.0, abs=0.001)

    def test_max_positive_divergence(self):
        """L3/L4/L5 = 100 iken production - backtest maksimum fark = 26.0 puan.

        (100 - 50) × 0.52 = 26.0 puan maksimum divergence.
        Örnek: production BUY-STRONG (≥72) iken backtest HOLD üretebilir.
        """
        max_div = (100.0 - 50.0) * (
            MASTER_WEIGHTS["kap"]
            + MASTER_WEIGHTS["sentiment"]
            + MASTER_WEIGHTS["smart_money"]
        )
        assert max_div == pytest.approx(26.0, abs=0.001)

    def test_zero_divergence_when_l3_l4_l5_neutral(self):
        """L3/L4/L5 = 50.0 iken backtest composite = production composite."""
        tech, macro, risk = 65.0, 55.0, 52.0
        bt = _bt_composite(tech, macro, risk)
        prod = _prod_composite(tech, macro, 50.0, 50.0, 50.0, risk)
        assert bt == pytest.approx(prod, rel=1e-6)

    def test_divergence_positive_for_strong_l3_l4_l5(self):
        """Güçlü KAP/Sentiment/SmartMoney: production composite > backtest composite."""
        tech, macro, risk = 65.0, 55.0, 52.0
        bt = _bt_composite(tech, macro, risk)
        prod = _prod_composite(
            tech, macro, kap=80.0, sentiment=72.0, smart_money=75.0, risk=risk
        )
        assert prod > bt, (
            f"Güçlü L3/L4/L5: production ({prod:.2f}) > backtest ({bt:.2f}) bekleniyor"
        )

    def test_divergence_negative_for_weak_l3_l4_l5(self):
        """Zayıf KAP/Sentiment/SmartMoney: production composite < backtest composite."""
        tech, macro, risk = 65.0, 55.0, 52.0
        bt = _bt_composite(tech, macro, risk)
        prod = _prod_composite(
            tech, macro, kap=25.0, sentiment=30.0, smart_money=20.0, risk=risk
        )
        assert prod < bt, (
            f"Zayıf L3/L4/L5: production ({prod:.2f}) < backtest ({bt:.2f}) bekleniyor"
        )


# ---------------------------------------------------------------------------
# TestDivergenceLog (1 test — PASSING)
# ---------------------------------------------------------------------------

class TestDivergenceLog:
    """§8.4 Faz 1a: 5 senaryo için backtest-production divergence tablosu loglanır."""

    def test_divergence_scenarios_logged(self):
        """5 piyasa senaryosunda backtest-production delta'yı INFO log olarak yaz.

        Bu test her zaman geçer; amacı divergence miktarını ölçmek ve belgelemektir.
        Çalıştır: pytest tests/test_backtest_production_parity.py -s --log-cli-level=INFO
        """
        SCENARIOS = [
            ("S1: Güçlü KAP+Sentiment", 80.0, 72.0, 75.0),
            ("S2: Negatif Sentiment",     50.0, 30.0, 45.0),
            ("S3: Neutral Baseline",      50.0, 50.0, 50.0),
            ("S4: BUY-STRONG Pattern",    85.0, 78.0, 80.0),
            ("S5: SELL Pattern",          20.0, 25.0, 30.0),
        ]
        tech_fixed, macro_fixed, risk_fixed = 65.0, 55.0, 52.0

        for name, l3, l4, l5 in SCENARIOS:
            bt = _bt_composite(tech_fixed, macro_fixed, risk_fixed)
            prod = _prod_composite(tech_fixed, macro_fixed, l3, l4, l5, risk_fixed)
            delta = prod - bt
            logger.info(
                "[PARITY][%s] prod=%.2f bt=%.2f delta=%+.2f (L3=%s L4=%s L5=%s)",
                name, prod, bt, delta, l3, l4, l5,
            )

        # Invariant: S3 Neutral senaryosunda delta = 0 olmalı
        bt_n = _bt_composite(tech_fixed, macro_fixed, risk_fixed)
        prod_n = _prod_composite(tech_fixed, macro_fixed, 50.0, 50.0, 50.0, risk_fixed)
        assert abs(bt_n - prod_n) < 0.001, (
            "Neutral senaryo (L3=L4=L5=50): backtest-production delta 0 olmalı"
        )


# ---------------------------------------------------------------------------
# TestSignalThresholdConsistency (3 test — tümü PASSING)
# ---------------------------------------------------------------------------

class TestSignalThresholdConsistency:
    """Her iki engine aynı SIGNAL_THRESHOLDS'u import etmeli (architecture check)."""

    def test_signal_thresholds_has_buy_strong_key(self):
        """SIGNAL_THRESHOLDS 'buy_strong' anahtarını içermeli."""
        assert "buy_strong" in SIGNAL_THRESHOLDS, (
            "SIGNAL_THRESHOLDS['buy_strong'] eksik — thresholds.py kontrolü gerekli."
        )

    def test_backtest_engine_imports_signal_thresholds(self):
        """backtest/engine.py SIGNAL_THRESHOLDS'u thresholds.py'den import etmeli."""
        source = (
            Path(__file__).parent.parent / "src" / "backtest" / "engine.py"
        ).read_text(encoding="utf-8")
        assert "SIGNAL_THRESHOLDS" in source, (
            "backtest/engine.py SIGNAL_THRESHOLDS import etmiyor. "
            "from src.signals.thresholds import SIGNAL_THRESHOLDS satırı gerekli."
        )

    def test_production_engine_imports_signal_thresholds(self):
        """src/signals/engine.py SIGNAL_THRESHOLDS'u thresholds.py'den import etmeli."""
        source = (
            Path(__file__).parent.parent / "src" / "signals" / "engine.py"
        ).read_text(encoding="utf-8")
        assert "SIGNAL_THRESHOLDS" in source, (
            "src/signals/engine.py SIGNAL_THRESHOLDS import etmiyor."
        )


# ---------------------------------------------------------------------------
# TestParityFutureChecks (3 test — tümü SKIP)
# ---------------------------------------------------------------------------

class TestParityFutureChecks:
    """D-149c / D-149d sonrası aktive edilecek parity testleri.

    D-149a: Tüm testler skip işaretli.
    D-149c: test_composite_calculation_parity_requires_calculator ve
            test_signal_from_composite_consistent_via_calculator skip kaldırılır.
    D-149d / Faz 2: test_no_l3_l4_l5_neutral_stub_in_backtest_post_faz2 skip kaldırılır.
    """

    def test_composite_calculation_parity_requires_calculator(self):
        """Production/backtest composite parity — calculator.py paylasimli modul (D-149c)."""
        from src.signals.calculator import compute_composite_score

        # Neutral giris -> her iki engine ayni sonucu uretmeli
        scores = {layer: 50.0 for layer in MASTER_WEIGHTS}
        result = compute_composite_score(scores, MASTER_WEIGHTS)
        assert result == pytest.approx(50.0, abs=0.01)

    def test_signal_from_composite_consistent_via_calculator(self):
        """signal_from_composite() SIGNAL_THRESHOLDS sinirlarini dogru uygular (D-149c)."""
        from src.signals.calculator import signal_from_composite

        assert signal_from_composite(75.0) == "BUY-STRONG"   # >= 72
        assert signal_from_composite(65.0) == "BUY-WEAK"     # >= 60, < 72
        assert signal_from_composite(50.0) == "HOLD"         # >= 48, < 60
        assert signal_from_composite(40.0) == "SELL-WEAK"    # >= 32, < 48
        assert signal_from_composite(20.0) == "SELL-STRONG"  # < 32

    def test_no_l3_l4_l5_neutral_stub_in_backtest_post_faz2(self):
        """backtest L3/L4/L5 neutral stub kaldırıldı mı? — D-149d / Faz 2."""
        pytest.skip(
            "D-149d / Faz 2 bekliyor: "
            "L3/L4/L5 historical veri pipeline hazır olduğunda skip kaldır. "
            "Mevcut: 50.0 neutral stub (intentional — veri kısıtı)."
        )
