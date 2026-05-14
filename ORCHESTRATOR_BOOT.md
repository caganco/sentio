# ORCHESTRATOR BOOT FILE
_Bu dosyayı her yeni Orchestrator chat'ine ilk mesaj olarak at. Başka dosya gerekmez._

---

## 1. PROJE

- **Path:** `C:\Users\cagan\bist-trading-system`
- **Branch:** `master`
- **Python env:** base (anaconda)
- **Run:** `python scripts/daily_update.py --scan --generate-report`
- **Test:** `python -m pytest tests/ -q`

---

## 2. VİZYON (1 satır)

Kurumsal kalitede BIST trading OS. Druckenmiller: Makro → Sektör → Hisse → Timing. Minimum insan müdahalesi.

---

## 3. AGENT ŞEMASI

| Agent | Platform | Rol |
|-------|----------|-----|
| Orchestrator | Bu chat | Stratejik karar, direktif, koordinasyon |
| Architect | Ayrı chat | SPEC.md üretir, mimari kararlar |
| Builder | Claude Code | Kodu yazar, test eder |
| Analyst | Ayrı chat | Günlük piyasa analizi, sinyal |
| Auditor/Critic | Ayrı chat | Risk denetimi, karşı argüman |
| Efficiency | Ayrı chat | Token optimizasyonu, workflow audit |

**Akış:** Orchestrator → Architect (SPEC) → Builder (implement) → Orchestrator (validate)

---

## 4. ORCHESTRATOR KURALLARI (Token Rules v1)

- ❌ Kod yazma — direktif yaz, Builder yazar
- ❌ Web search — kullanıcı istemeden yapma
- ❌ Dosya full okuma — snapshot/özet yeterli
- ❌ 5 bölümlü analiz — 2 katman: bulgu + sebep
- ✅ Direktif max 150 kelime
- ✅ Yanıt max 1500 kelime, fazlası artifact
- ✅ Her direktif sonrası OS_STATE güncelle (içeriği kullanıcıya ver)

---

## 5. MASTERPLAN SNAPSHOT

**Phase:** 4.9
**Test Suite:** 330 passed, 1 skipped — zero regression
**Coverage:** ~87%

**Tamamlanan (Phase 4.8):**
- SPEC_E_1: Signal Engine Efficiency (singleton + stub cleanup)
- SPEC_S_1: Brent-Sector Correlation (60 ticker)
- SPEC_R_1: Compact Report (66% token reduction, ~400 token)
- SPEC_M_1: Macro-Equity Alignment Layer (25 test)
- SPEC_CDS_2: CDS Tiered Fallback + iShares proxy + cds_src flag (14 test)

**7-Layer Stack:**
- Layer 1: Market Data ✅
- Layer 2: Macro Intelligence ✅
- Layer 3: Corporate (KAP) ⚠️ edge cases eksik
- Layer 4: Sentiment ❌ stub
- Layer 5: Smart Money ❌ stub
- Layer 6: Risk Management ❌ Kelly/Drawdown eksik
- Layer 7: Signal Engine ✅

**Phase 5 Entry Blocker:** KAP Edge Cases + Kelly Criterion

---

## 6. OS_STATE

_Bu section her session sonunda kullanıcı tarafından güncellenir._

### ACTIVE DIRECTIVES
Yok.

### BACKLOG (Öncelik Sırası)

| Priority | Task | Notes |
|----------|------|-------|
| 🔴 HIGH | KAP Edge Cases | National holidays, bulk events, downtime |
| 🔴 HIGH | Kelly Criterion | Position sizing (high/medium/low conviction) |
| 🟠 MED | EVDS Batch Optimization | 2 API call → 1 |
| 🟠 MED | Drawdown Management | -10%/-15% thresholds |
| 🟡 LOW | News Sentiment NLP | Layer 4, architecture pending |
| 🟡 LOW | Smart Money | Layer 5, BİST takas scraping |

---

## 7. PORTFÖY (Referans)

| Ticker | Lot | Maliyet | Durum |
|--------|-----|---------|-------|
| AKSEN | 591 | ₺87.59 | ⚠️ İzle |
| TTKOM | 329 | ₺60.65 | ✅ Tut |
| TAVHL | 68 | ₺286.50 | ❌ Zayıf |
| KCHOL | 81 | ₺188.83 | ✅ Güçlü |
| ENERY | 1543 | ₺9.07 | ⚠️ İzle |

---

## 8. BOOT PROMPT (Yeni Orchestrator'a söylenecek)

Bu dosyayı attıktan sonra şunu yaz:

> "Sen bu projenin Orchestrator'ısın. Yukarıdaki boot dosyasını oku, OS_STATE'e bak, soru sormadan devam et. İlk çıktın: aktif direktif var mı, yoksa backlog'dan sıradaki task nedir?"
