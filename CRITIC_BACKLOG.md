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

## ACTIVE FINDINGS (9 ACTIVE)

### [CB-001] Over-gating — L2 < 45 → 0.0x scaling
- **Tahmini alpha kaybı:** 12-15 puan/yıl (bull regime)
- **Kök neden:** Macro regime gate sert eşikli. CDS spike sırasında out, normalize olduğunda geç in.
- **Önerilen düzeltme:** CDS percentile-conditional gate (Longstaff et al. 2011)
- **Akademik referans:** Longstaff, Pan, Pedersen, Singleton (2011) "How Sovereign is Sovereign Credit Risk?"
- **Status:** D-108 SPEC üretiliyor (Architect)
- **Etkilenen dosyalar:** `src/signals/macro_regime_gate.py`, `src/signals/engine.py`
- **Eklendi:** 20 May 2026

### [CB-002] Static weights, regime-blind
- **Tahmini alpha kaybı:** 8-10 puan/yıl
- **Kök neden:** L1=0.25, L2=0.20, L3=0.27 sabit. Rejim sadece gate, modülatör değil.
- **Önerilen düzeltme:** Regime-conditional weights — BULL'da L1 (momentum) 0.40-0.50, BEAR'da L1 contrarian
- **Akademik referans:** Asness, Moskowitz, Pedersen (2013) "Value and Momentum Everywhere"
- **Status:** Faz 3 (IC datası sonrası, ~Aug 2026)
- **Etkilenen dosyalar:** `src/signals/engine.py`, `src/signals/thresholds.py`
- **Eklendi:** 20 May 2026

### [CB-003] TP1 prematüre — ATR×1.5'te %50 exit
- **Tahmini alpha kaybı:** 4-6 puan/yıl
- **Kök neden:** Bull market'te ilk pivot direnci genelde kırılır. Profit-clipping bias.
- **Önerilen düzeltme:** BULL regime'de TP1 atla veya 2.5x'e yükselt (let winners run)
- **Status:** D-109 SPEC üretiliyor (Architect)
- **Etkilenen dosyalar:** Position sizer, exit logic
- **Eklendi:** 20 May 2026

### [CB-004] L3 KAP overweight — %30 continuous
- **Tahmini alpha kaybı:** 3-5 puan/yıl
- **Kök neden:** KAP filings episodik ve genelde nötr/teknik. Continuous %30 yanlış.
- **Önerilen düzeltme:** Event-triggered weight boost — KAP event tetiklenince geçici weight artışı
- **Status:** Faz 3 (IC datası sonrası)
- **Etkilenen dosyalar:** `src/signals/engine.py`, `src/signals/layers/kap_layer.py`
- **Eklendi:** 20 May 2026

### [CB-005] Conviction threshold ≥0.68 çok yüksek
- **Tahmini alpha kaybı:** 3-5 puan/yıl
- **Kök neden:** Aktif weight 0.78 iken 0.68 eşik = ortalama skor 87. Nadiren tetikleniyor.
- **Önerilen düzeltme:** Empirical kalibrasyon — IC datasına dayalı eşik
- **Status:** Faz 3 (IC datası sonrası)
- **Etkilenen dosyalar:** `src/signals/conviction_validator.py`, `src/signals/thresholds.py`
- **Eklendi:** 20 May 2026

### [CB-006] Stop-loss -%8 dar (BIST volatilitesi için)
- **Tahmini alpha kaybı:** 2-3 puan/yıl
- **Kök neden:** AKSEN/ENERY gibi mikro-cap'lerde haftada -%5 normal noise. Whipsaw.
- **Önerilen düzeltme:** Volatility-aware stop tier (ATR/P bazlı)
- **Status:** D-110 SPEC üretiliyor (Architect)
- **Etkilenen dosyalar:** `src/risk/position_sizer_v2.py`, `src/signals/thresholds.py`
- **Eklendi:** 20 May 2026

### [CB-007] Foreign flow yanlış katmanda
- **Bulgu:** Ülkü & İkizlerli (2012) — foreign flows piyasa-seviyesi sinyal, hisse-spesifik değil
- **Kök neden:** L5'te foreign_ratio hisse-spesifik kullanılıyor — akademik olarak yanlış
- **Önerilen düzeltme:** `foreign_ratio` (ownership) L5'te kalır, `net_foreign_flow` (akış) L2'ye migrate
- **Status:** D-111 (sıraya alınacak)
- **Etkilenen dosyalar:** `src/signals/layers/smart_money_layer.py`, `src/data/local_macro_signals.py`
- **Eklendi:** 20 May 2026

### [CB-008] VIOP eşikleri akademik kaynaksız
- **Bulgu:** RESEARCH-013 — Türkiye'ye özel Put/Call eşiği literatürde YOK. Mevcut VIOP_PC_THRESHOLDS CBOE referansı.
- **Kök neden:** BIST opsiyon hacmi ABD'nin çok altında — CBOE eşikleri geçersiz olabilir
- **Önerilen düzeltme:** Faz 1 IC ölçümü sonrası kalibrasyon. IC t-stat ≥ 2.0 görmeden engine'e bağlama.
- **Status:** Faz 1 IC datası bekler (D-107 ile log alıyor)
- **Etkilenen dosyalar:** `src/signals/thresholds.py` (VIOP_PC_THRESHOLDS), `src/signals/layers/viop_layer.py`
- **Eklendi:** 20 May 2026

### [CB-009] L4 Türkçe NLP yanlış araç
- **Bulgu:** RESEARCH-016 — İngilizce FinBERT (ProsusAI) Türkçe Mynet haberlerine uygulanıyor. Dil mismatch.
- **Kök neden:** Public Türkçe finansal BERT YOK. Mevcut Türkçe sentiment modelleri genel domain (film/ürün).
- **Önerilen düzeltme:** Üç seçenek — (A) BERTurk + KAP fine-tune, (B) Lexicon-based, (C) LSTM + Twitter + suspicious score
- **Status:** Ayrı SPEC (sırası gelmedi)
- **Etkilenen dosyalar:** `src/nlp/finbert_analyzer.py`, `src/signals/sentiment/news_aggregator.py`
- **Eklendi:** 20 May 2026

---

## TOTAL ALPHA AT STAKE

| Kategori | Tahmini Kayıp |
|----------|--------------|
| HEMEN düzeltilebilir (CB-001, CB-003, CB-006) | 18-24 puan/yıl |
| Faz 3 (IC sonrası — CB-002, CB-004, CB-005) | 14-20 puan/yıl |
| Yapısal (CB-007, CB-008, CB-009) | Ölçülmüş değil |
| **TOPLAM açık alpha leak** | **32-44+ puan/yıl** |

---

## CLOSED FINDINGS

*(Kapatılanlar buraya taşınır — tarih + commit hash + doğrulama notu ile)*

(Henüz kapatılmış madde yok.)

---

## SESSION CHECKPOINT LOG

*(Her session sonu burada satır ekler — accountability izi)*

### 20 May 2026 — Session #1 (D-090..D-110)
- ACTIVE FINDINGS oluşturuldu: 9 madde
- Bu session'da kapatılan: yok (henüz)
- Üretilmiş SPEC: D-108 (CB-001), D-109 (CB-003), D-110 (CB-006) — Architect aşamasında
- Sonraki session'ın bakacağı: SPEC'lerin Builder implementasyonu, CB-007 için D-111 SPEC, IC dashboard günlük kontrol

---

## DOSYA KURALLARI

- **Hiçbir madde silinmez** — kapatılanlar CLOSED FINDINGS bölümüne taşınır
- **Tahmini alpha kaybı sayıları** kanıt geldikçe revize edilir (yorumla değil, ampirik IC datasıyla)
- **Status değişimleri** SESSION CHECKPOINT LOG'a yazılır
- **Yeni bulgu eklenirken** kaynak (research raporu, critic, dış göz) açıkça referanslanır
- **Closed işaretlemek için** commit hash + doğrulama testi şart
