# AUDIT_REPORT_001 — Backtest Engine Divergence Audit

**Audit Tarihi:** 2026-05-25
**Direktif:** D-061 (audit), D-149a–e (closure)
**Referans:** RR-018 §8 (C-1 closure roadmap), SPEC_BACKTEST_FRAMEWORK_1
**Durum:** Faz 1 ✅ KAPANDI (D-149e, 2026-05-25)

---

## C-1: backtest/engine.py — Production'dan Diverge Formül

**Bulgu:** `src/backtest/engine.py` composite hesaplamasinda
L3 (KAP), L4 (Sentiment), L5 (SmartMoney) katmanlari daima 50.0
(neutral stub) kullaniyordu. Bu katmanlarin toplam MASTER_WEIGHTS
agirligi %52 oldugundan backtest sinyallerinin %52'si her zaman
sabit (neutral) kaliyordu. Production engine ayni gunlerde gercek KAP/
sentiment/smart_money skorlari kullandigindan divergence maksimum
26 composite puan ulasabiliyordu (BUY-STRONG → HOLD sessiz regresyon).

**Ek divergence kaynaklari:**
- Stop-loss (0.92), profit-target (1.20), circuit-breaker (-0.15)
  ve VIX haircut (0.75 / 25.0) thresholds.py'den degil, hardcoded
- `src/signals/calculator.py` shared module yoktu
- Kelly formulu (0.50 + (c-50)/200.0) thresholds sabitleri kullanmiyordu

**Kapatma Adimlari (D-149 serisi):**

| Direktif | Is | PR |
|----------|----|----|
| D-149a | Parity test yazimi (divergence belgeleme) | #66 |
| D-149b | Drift olcumu + eski rapor RETRACT | #68 |
| D-149c | `src/signals/calculator.py` shared module | #70 |
| D-149d | backtest/engine.py hardcode temizleme | #71 |
| D-149e | Architecture test finalize + C-1 closure | bu PR |

> ✅ CLOSED — D-149a/b/c/d/e (2026-05-25)
> backtest/engine.py thresholds.py'den okur.
> calculator.py shared module production + backtest'i birlestirdi.
> Kalan: 50.0 neutral stub (intentional, Faz 2 D-150 kapsami — veri kisiti).

---

## C-2: reports/ Eski Backtest Raporlari RETRACT Edilmedi

**Bulgu:** D-038, D-046, D-047, D-048, D-049, D-050 raporlari
diverge engine ile uretilmisti, RETRACT isaretlenmemisti.

> ✅ CLOSED — D-149b (2026-05-25)
> scripts/retract_old_backtest_reports.py calistirildi.
> Hedef raporlar RETRACT NOTICE header aldi.
> reports/ gitignored oldugundan cogu dosya yok (non-fatal, warning+skip).
