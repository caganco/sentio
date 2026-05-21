# CRITIC BACKLOG — Persistent Findings

> **Bu dosya nesilden nesile (session-to-session) taşınır. Her Orchestrator session başında okunmak ZORUNLUDUR. Hiçbir kapanmamış madde sessizce unutulamaz.**

---

## ORIGIN

Bu backlog, dış kritikler ve araştırma raporlarından çıkan **stratejik bulguları** kalıcılaştırmak için tutulur. Klasik LLM context decay sorununa karşı koruma katmanı.

**Kaynak olaylar:**
- Critic raporu (20 May 2026) — dış göz, sistemin alpha üretmeme nedenleri
- RESEARCH-013/014/016 (20 May 2026) — BIST-spesifik akademik bulgular
- Alpha Attribution akademik raporu (20 May 2026) — IC metodolojisi

**Kural:** Hiçbir Orchestrator session bu dosyayı okumadan başlamaz. Hiçbir session ACTIVE FINDINGS'i güncellemeden kapanmaz.

---

## ACTIVE FINDINGS (6 ACTIVE)

### [CB-002] Static weights, regime-blind
- **Tahmini alpha kaybı:** 8-10 puan/yıl
- **Kök neden:** L1=0.25, L2=0.20, L3=0.27 sabit. Rejim sadece gate, modülatör değil.
- **Önerilen düzeltme:** Regime-conditional weights — BULL'da L1 0.40-0.50, BEAR'da L1 contrarian
- **Akademik referans:** Asness, Moskowitz, Pedersen (2013) J. Finance doi:10.1111/jofi.12021
- **İç araştırma:** RR-003 §3 — bootstrap stratejisi + BIST empirik kanıt (Şenol 2020, Doğan&Bilge 2022)
- **Tahmini alpha:** Sharpe +0.29 (Northern Trust) / +%80 göreceli (Neuhierl et al. 2024)
- **Status:** Faz 3 (IC datası sonrası, ~Aug 2026) → D-123 HMM SPEC sonraki session
- **Etkilenen:** `src/signals/engine.py`, `src/signals/thresholds.py`
- **Eklendi:** 20 May 2026

### [CB-004] L3 KAP overweight — %27 continuous
- **Tahmini alpha kaybı:** 3-5 puan/yıl
- **Kök neden:** KAP filings episodik ve genelde nötr/teknik. Continuous %27 yanlış.
- **Önerilen düzeltme:** Event-triggered weight boost
- **Status:** Faz 3 (IC datası sonrası)
- **Etkilenen:** `src/signals/engine.py`, `src/signals/layers/kap_layer.py`
- **Eklendi:** 20 May 2026

### [CB-005] Conviction threshold ≥0.68 çok yüksek
- **Tahmini alpha kaybı:** 3-5 puan/yıl
- **Kök neden:** Aktif weight 0.78 iken 0.68 eşik = ortalama skor 87. Nadiren tetikleniyor.
- **Önerilen düzeltme:** Empirical kalibrasyon — IC datasına dayalı eşik
- **Status:** Faz 3 (IC datası sonrası)
- **Etkilenen:** `src/signals/conviction_validator.py`, `src/signals/thresholds.py`
- **Eklendi:** 20 May 2026

### [CB-007] Foreign flow yanlış katmanda
- **Bulgu:** Ülkü & İkizlerli (2012) — foreign flows piyasa-seviyesi sinyal, hisse-spesifik değil
- **Kök neden:** L5'te foreign_ratio hisse-spesifik — akademik olarak yanlış
- **Önerilen düzeltme:** ownership L5'te kalır, net_foreign_flow L2'ye migrate
- **Önerilen yol:** RR-001 §4
- **Status:** D-111 (sıraya alınacak)
- **Etkilenen:** `src/signals/layers/smart_money_layer.py`, `src/data/local_macro_signals.py`
- **Eklendi:** 20 May 2026

### [CB-008] VIOP eşikleri akademik kaynaksız
- **Bulgu:** Türkiye'ye özel Put/Call eşiği literatürde YOK. CBOE referansı BIST için geçersiz olabilir.
- **Önerilen düzeltme:** IC t-stat ≥ 2.0 sonrası kalibrasyon
- **Status:** Faz 1 IC datası bekler
- **Etkilenen:** `src/signals/thresholds.py`, `src/signals/layers/viop_layer.py`
- **Eklendi:** 20 May 2026

### [CB-010] Linear additive mimari insan kararını simüle etmiyor
- **Bulgu:** w1×L1+...linear composite; layer bağımsızlık varsayımı muhtemelen yanlış,
  episodik sinyal sorunu (L3), non-stationarity, interaksiyon kayıpları.
- **Önerilen araştırma:** Attention-weighted composite, multi-LLM jüri, conviction×context
- **İç araştırma:** RR-003 §1-4 — 4 aşamalı yol haritası (HMM → XGBoost → 2-LLM → Transformer)
- **Status:** RESEARCH tamamlandı — D-123 HMM Aşama 1 SPEC sonraki session önceliği
- **Eklendi:** 21 May 2026

---

## TOTAL ALPHA AT STAKE

| Kategori | Tahmini Kayıp |
|----------|--------------|
| ~~HEMEN (CB-001, CB-003, CB-006)~~ | ~~18-24 puan/yıl~~ ✅ KAPATILDI |
| Faz 3 (CB-002, CB-004, CB-005) | 14-20 puan/yıl |
| Yapısal (CB-007, CB-008, CB-010) | Ölçülmüş değil |
| **TOPLAM açık** | **~14-20+ puan/yıl** |

---

## ACTIVATION GATES — Zaman Kilitli Kararlar

### [AG-001] ENABLE_HMM_WEIGHTS=True aktivasyonu
- **Su an:** False (default) — D-123 implement edildi, 1032 test geciyor
- **Aktivasyon kosulu:**
  - Alpha Attribution IC dashboard'da >=90 gun OOS veri birikmi
  - HMM NEUTRAL rejim → mevcut davranisla identik (architecture test ✅)
  - HMM BULL/BEAR → MASTER_WEIGHTS'e gore Sharpe iyilesmesi gorunur
- **Tahmini tarih:** ~Agustos 2026
- **Aktive eden:** Cagan (manuel, .env'de ENABLE_HMM_WEIGHTS=True)
- **Kontrol sorumlusu:** Her Orchestrator session basinda AG-001 status kontrol
- **Eklendi:** 22 May 2026 — Session #3

---

## CLOSED FINDINGS

### ✅ [CB-001] Over-gating — L2 < 45 → 0.0x scaling
- **Kapatıldı:** 20 May 2026 — D-108, DEC-017
- **Uygulanan:** CDS percentile-conditional overlay. BEAR soft 0.25x, hard 0.0x.
- **Doğrulama:** 874 passed

### ✅ [CB-003] TP1 prematüre — ATR×1.5'te %50 exit
- **Kapatıldı:** 20 May 2026 — D-109
- **Uygulanan:** BULL'da 1.5x→2.5x ATR. Monotonicity guard.
- **Doğrulama:** 874 passed

### ✅ [CB-006] Stop-loss -%8 dar
- **Kapatıldı:** 20 May 2026 — D-110
- **Uygulanan:** Vol-aware tier: -%6/-%8/-%12/-%15, floor -%20
- **Doğrulama:** 874 passed

### ✅ [CB-009] L4 Türkçe NLP yanlış araç
- **Kapatıldı:** 21 May 2026 — D-124
- **Uygulanan:** Hybrid Tier-1 (93-term Türkçe lexicon) + Tier-2 (Claude Haiku 4.5)
  temperature=0.0, structured JSON, prompt caching. ~18 TL/ay maliyet.
- **Akademik referans:** RR-004 §Bölüm 5 (Boztepe Tilburg 2025, Lopez-Lira 2025)
- **Doğrulama:** 999 passed, 46 yeni test

---

## SESSION CHECKPOINT LOG

### 20 May 2026 — Session #1 Açılış
- ACTIVE FINDINGS oluşturuldu: 9 madde
- Üretilmiş SPEC: D-108/109/110

### 20 May 2026 — Session #1 Kapanış
- Kapanan: CB-001, CB-003, CB-006
- Active: 9 → 6 | Test: 824 → 874

### 21 May 2026 — Session #2 Kapanış (D-112..D-124)
- Kapanan: CB-009 (D-124 — L4 Türkçe NLP hybrid)
- Eklenen: CB-010 (linear mimari)
- Active: 6 → 6 (CB-009 kapatıldı, CB-010 eklendi)
- Test count: 874 → 999 passed
- D-112..D-124 tamamlandı (signal logging, KAP, branch workflow, CI/CD,
  ops reliability, mypy, research registry, L4 NLP)
- gh CLI kuruldu — Builder artık PR açabiliyor
- DEC-018 — Multi-instance Builder belgelendi
- CHP krizi: BIST -%6, CDS 250 bps, devre kesici
- Portföy: AKSEN SELL emri aktif (73.50, %-16.38)
- Dependabot: 9 PR açık (pandas #6 hariç merge edilebilir)
- Sonraki session: D-123 HMM SPEC + portföy kararı + Dependabot merge

---

## DOSYA KURALLARI

- **Hiçbir madde silinmez** — kapatılanlar CLOSED FINDINGS'e taşınır
- **Alpha sayıları** ampirik IC datasıyla revize edilir
- **Status değişimleri** SESSION CHECKPOINT LOG'a yazılır
- **Yeni bulgu** kaynak referansıyla eklenir
- **Closed** = commit hash + doğrulama testi şart