# BIST Hedge Fund OS — Master Plan
*Last updated: 13 Mayıs 2026*

---

## Vision
Retail seviye değil, kurumsal (hedge fund) kalitesinde BIST trading infrastructure.
Druckenmiller metodolojisi: Makro → Sektör → Hisse → Timing.
Hedef: Minimum insan müdahalesi, maksimum getiri, sistematik karar mekanizması.

---

## Kullanıcı Profili
- **Portföy:** 100-500K TL
- **Stil:** Hibrit (momentum + fundamentals)
- **Vade:** Fırsata göre (1 hafta - 3 ay)
- **Mevcut pozisyonlar:**
  - AKSEN: 591 lot @ ₺87.59
  - TTKOM: 329 lot @ ₺60.65
  - TAVHL: 68 lot @ ₺286.50 ⚠️
  - KCHOL: 81 lot @ ₺188.83
  - ENERY: 1543 lot @ ₺9.07 ⚠️
- **Yatırım fonları:**
  - DVT (Deniz Metaverse): ₺41.688 (+%36.52)
  - DFI (Atlas Serbest): ₺47.672 (+%5.93)
  - PHE (Pusula Hisse): ₺20.673 (+%3.38)
- **US Hisse:** PLTR (şimdilik dışarıda)

---

## Sistem Mimarisi — 6 Agent

### Agent 1: ORCHESTRATOR
- **Platform:** Claude.ai (bu conversation)
- **Rol:** Stratejik beyin, vizyon, koordinasyon, final kararlar
- **Input:** Tüm agent raporları
- **Output:** Direktifler, yatırım kararları, yeni feature talepleri

### Agent 2: ANALYST
- **Platform:** Ayrı Claude.ai conversation
- **Rol:** Piyasa analizi, makro rejim, narrative, sinyal üretimi
- **Metodoloji:** Druckenmiller framework (7 katman)
- **Output:** Structured daily briefing (JSON + MD)
- **System Prompt Özeti:**
  > "Sen deneyimli bir hedge fund analistisin. Druckenmiller metodolojisiyle piyasayı analiz et. Makro → Sektör → Hisse → Timing. Sadece aksiyon odaklı, noise'sız içgörüler. Her analizi BUY/SELL/HOLD/WATCH sinyaliyle bitir."

### Agent 3: AUDITOR
- **Platform:** Ayrı Claude.ai conversation
- **Rol:** Risk denetimi, şeytanın avukatı, worst-case analizi
- **Output:** Risk skorları, karşı argümanlar, audit report
- **System Prompt Özeti:**
  > "Sen risk management direktörüsün. Her yatırım kararını şüpheyle karşıla. Temel soru: Ne ters gidebilir? Worst-case senaryolar. Hiçbir zaman optimist ol."

### Agent 4: ARCHITECT
- **Platform:** Ayrı Claude.ai conversation veya Cowork
- **Rol:** Yazılım mimarisi, yeni feature spec'leri, Claude Code'a teslim
- **Output:** SPEC.md + INSTRUCTIONS.md (Claude Code için)
- **System Prompt Özeti:**
  > "Sen senior software architect'sin. Feature request → Mimari değerlendirme → Implementation spec. Clean, scalable, modular Python."

### Agent 5: BUILDER
- **Platform:** Claude Code (VS Code)
- **Rol:** Kodu yazar, test eder, raporlar
- **Proje dizini:** `C:\Users\cagan\bist-trading-system\`
- **Status:** ✅ Kurulu ve çalışıyor

### Agent 6: EFFICIENCY AGENT
- **Platform:** Ayrı Claude.ai conversation
- **Rol:** Token optimizasyonu, workflow analizi, insan müdahalesini minimize et
- **Output:** Haftalık efficiency report, optimization önerileri
- **System Prompt Özeti:**
  > "Sen AI systems engineer'sın. Sistemin token kullanımı, latency, maliyet ve insan müdahalesini izle. Hedef: Minimum input, maksimum output kalitesi. Her hafta optimization report üret."

---

## Tamamlananlar (13 Mayıs 2026 — güncellendi) ✅

- Macro signal per-symbol volatility scaling (USDTRY scale=0.02, VIX scale=0.15, BRENT/equity scale=0.05) — `src/signals/macro_signals.py`
- Decisions otomasyonu — `decisions/decisions_YYYY-MM-DD.md` orchestrator pipeline sonunda otomatik oluşturuluyor
- KAP source tagging — haber başına `source_type: kap_official / news_media / unknown`, `source_domain` alanları eklendi
- `CLAUDE.md` + auto permission mode kuruldu (`.claude/settings.local.json` → `defaultMode: auto`)
- Test suite: 41/41 geçiyor (SPEC 1 + 2 + 3 testleri dahil)
- Permission mode `bypassPermissions` → `auto` (güvenli mod, güvenlik sınırları korunuyor)
- **60 hisse coverage:** BIST30 tam + BIST100 seçili 30 hisse — `config.yaml` güncellendi
- **Batch fetcher:** 60 hisseyi tek `yf.download()` çağrısında paralel thread ile çekiyor — `src/data/fetcher.py`
- **Pre-filter sistemi:** 60 → 8-10 hisse, lokal hesaplama (zero API token), 6 kriter 6/6 doğru — `scripts/daily_update.py`
- **Orchestrator canlı:** Anthropic API entegre, compact prompt modu aktif, cache + model routing çalışıyor — `agents/orchestrator.py`
- **Token optimization:** Auditor/Efficiency Haiku'ya geçti, MD5 response caching eklendi, max_tokens düşürüldü — tahmini **%60-70 maliyet düşüşü**
- **Signal Engine — Layer 7:** `src/signals/engine.py` + 6 layer (`technical`, `macro`, `kap`, `sentiment`-stub, `smart_money`-stub, `risk`) — deterministik, audit trail dahil, backtest-safe. 86 yeni test. `agents/orchestrator.py`'e entegre: sinyal context analyst prompt'a inject ediliyor
- **KAP bildirimleri Signal Engine'e entegre:** `kap_layer.py` 3 günlük event window, high_priority multiplier, category impact tablosu
- **`thresholds.py`:** Tüm eşik sabitleri tek dosyada — magic number sıfır

---

## Kalan Görevler (Backlog)

### Öncelik: YÜKSEK
- [ ] **KAP WAF sorunu** → `fintables.com` alternatifini araştır ve entegre et (mevcut KAP API WAF tarafından sıkça engelleniyor)
- [x] **Signal Engine — Layer 7:** Multi-layer weighted scoring sistemi, BUY-STRONG/SELL-STRONG output formatı ✅ (13 Mayıs 2026)
- [ ] **Layer 2 genişletme — Lokal makro:** TCMB faiz yönü (sayısal delta), CDS primi seviyesi, yabancı takas oranı → `macro_layer.py`'e entegre *(Signal Engine bittikten sonra)*
- [ ] **Layer 5 Smart Money:** Borsa İstanbul günlük takas raporu scraper → kurumsal net alım/satım → Bull Trap flag (teknik BUY + kurumsal net satış → HOLD override) *(Signal Engine bittikten sonra)*

### Öncelik: ORTA
- [ ] **Analyst Agent prompt güncelle:** "Lokal makro rejim bu hissenin hikayesini destekliyor mu?" narrative perspektifi ekle — Engine'e değil, prompt'a *(Gemini Stratejik Raporu kararı)*
- [ ] **KAP → Macro → Teknik sinyal entegrasyonu** — üç katman tek bir sinyal skoruna birleştirilecek *(kısmen tamamlandı: Signal Engine bu entegrasyonu sağlıyor)*
- [ ] Backtest'e makro regime filtresi ekle (RISK_ON → uzun, RISK_OFF → nakit/kısa)
- [ ] Analyst system prompt'una `source_type` bilgisini ekle (`kap_official` haberlere daha yüksek güven ağırlığı)

### Öncelik: DÜŞÜK
- [ ] `server.py` path traversal güvenlik açığını kapat (`_safe_resolve` `/file` endpoint dışında kullanılmıyor)

---

## Mevcut Sistem Durumu (Phase 4 Başlıyor 🚀)

### Kurulu Bileşenler
```
C:\Users\cagan\bist-trading-system\
├── src/
│   ├── data/
│   │   ├── fetcher.py          ✅ Yahoo Finance (.IS format)
│   │   └── database.py         ✅ SQLite CRUD
│   ├── analysis/
│   │   ├── momentum.py         ✅ Volume surge, 52w high, scoring
│   │   ├── technicals.py       ✅ RSI, MA20/50/200, VWAP
│   │   └── portfolio.py        ✅ P&L, stop-loss alerts
│   ├── reports/
│   │   └── daily_report.py     ✅ Markdown + HTML output
│   └── utils/
│       ├── config.py           ✅ YAML config management
│       └── logger.py           ✅ File + console logging
├── scripts/
│   ├── daily_update.py         ✅ Ana entry point
│   └── setup_scheduler.py      ✅ Windows Task Scheduler
├── data/
│   └── bist_data.db            ✅ SQLite (23 ticker, 5819 rows)
├── reports/                    ✅ MD + HTML raporlar
├── config.yaml                 ✅ Portföy + scanner settings
└── logs/                       ✅ Error + info logs
```

### Günlük Otomasyon
- **09:00:** Task Scheduler → `daily_update.py --scan --generate-report`
- **Output:** `reports/report_YYYY-MM-DD.md` + `.html`
- **Coverage:** 23 BIST hissesi (KOZAL/KOZAA çıkarıldı)

### Takip Edilen Hisseler (config.yaml)
THYAO, AKBNK, EREGL, KCHOL, TUPRS, SAHOL, GARAN, ISCTR, VAKBN,
SISE, TTKOM, PETKM, BIMAS, ASELS, FROTO, TAVHL, AKSEN, ENERY,
TCELL, HALKB, EKGYO, KRDMD, SOKM

---

## 7-Layer Intelligence Stack (Roadmap)

### Layer 1: Market Data ✅ (Aktif)
- Yahoo Finance → OHLCV, volume
- 60 hisse, batch download, SQLite storage

### Layer 2: Macro Intelligence ✅ (Aktif)
- Crude oil, USD/TRY, Gold, S&P500, VIX — macro.py
- Per-symbol volatility scaling aktif
- Rejim sınıflandırması (RISK_ON/RISK_OFF/TRANSITION)

### Layer 3: Corporate Intelligence ❌ (Phase 4 — AKTİF GELIŞTIRME)
- **KAP scraper** → Finansal tablolar, özel durumlar, temettü
- **Earnings surprise model** → Beklenti vs gerçek EPS
- **Insider transaction tracker** → CEO/CFO alım-satımları
- Fintables entegrasyonu (analist hedefleri)

### Layer 4: Sentiment & Narrative ❌ (Phase 4 — SIRADAKI)
- Bloomberg HT, Investing.com TR, Hürriyet Finans scraping
- NLP sentiment scoring (-1 to +1)
- Sektör bazlı narrative momentum tracker
- Sosyal medya (opsiyonel — düşük öncelik)

### Layer 5: Smart Money Tracking ❌ (Phase 4)
- BofA institutional flow (günlük)
- Yabancı yatırımcı net akımı (KAP)
- Block trade detector
- Fon akımları

### Layer 6: Risk Management ❌ (Phase 5)
- Kelly criterion position sizing
- Korelasyon matrisi (hidden concentration risk)
- Drawdown management (-10% → risk off, -15% → flatten)
- Max 2 hisse aynı sektörden, sektör max %30

### Layer 7: Signal Engine ✅ (Aktif — Phase 4 tamamlandı)
- Multi-layer weighted scoring:
  - Technical: %15
  - Macro: %25
  - Earnings/KAP: %20
  - Sentiment: %15
  - Smart money: %10
  - Risk: %05
- Output: BUY-STRONG / BUY-WEAK / HOLD / SELL-WEAK / SELL-STRONG

---

## Python Bridge — Agent Orchestration

```python
# orchestrator.py (Claude Code'da inşa edilecek)
import anthropic, json

client = anthropic.Anthropic()  # API key .env'den

def run_analyst_agent(daily_briefing: dict) -> str:
    response = client.messages.create(
        model="claude-opus-4-6",
        system=ANALYST_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(daily_briefing)}]
    )
    return response.content[0].text

def run_auditor_agent(analyst_report: str) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        system=AUDITOR_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": analyst_report}]
    )
    return response.content[0].text

def run_efficiency_agent(system_metrics: dict) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        system=EFFICIENCY_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(system_metrics)}]
    )
    return response.content[0].text
```

**Günlük Çalışma Sırası:**
1. 06:00 → Builder: Veri çek, ham rapor üret
2. 08:00 → Analyst: Ham raporu analiz et, sinyal üret
3. 08:30 → Auditor: Sinyalleri denetle, risk score ekle
4. 09:00 → Orchestrator (Sen): Final briefing oku, karar ver
5. 10:00 → Piyasa açılır, kararlar execute edilir
6. 18:30 → Efficiency: Günlük metrikler topla

---

## Shared Intelligence Folder
```
C:\Users\cagan\bist-trading-system\intelligence\
├── daily_briefing_YYYY-MM-DD.json    ← Builder üretir
├── analyst_report_YYYY-MM-DD.md      ← Analyst Agent
├── audit_report_YYYY-MM-DD.md        ← Auditor Agent
├── decisions_YYYY-MM-DD.md           ← Orchestrator (Sen) yazar
└── efficiency_report_YYYY-MM-WW.md   ← Haftalık, Efficiency Agent
```

---

## Druckenmiller Framework — Karar Kuralları

### Narrative & Engine Dengesi:

- Layer 7 tamamen sayısal ve deterministik kalır — narrative score'a girmez
- Analyst Agent narrative yorum yazar (audit trail'e), Layer 7 score'una dokunmaz
- Orchestrator her ikisini okur, final kararı verir

### Takas Veri Stratejisi:

- Şu an: Borsa İstanbul gün sonu takas bülteni (ücretsiz, gecikmeli) — yeterli
- Geçiş koşulu: Portföy 1M TL+ olduğunda veya vade 1 haftanın altına indiğinde gerçek zamanlı sağlayıcıya (Matriks/Foreks) geç

### Bull Trap Kuralı (kesinleşti):

- Koşul: 3 gün üst üste kurumsal net satış ≥ -500K lot → BULL_TRAP flag
- KAP eventi YOK: Mutlak veto → BUY durdur
- KAP eventi VAR (kap_official, temettü/sözleşme): Veto → downgrade (BUY-STRONG → BUY-WEAK), audit trail'e "KAP event kurumsal satışı override etti" yaz, final karar Orchestrator'a gelir

### Giriş Koşulları (BUY)
- RSI 50-65 (ne aşırı alım ne aşırı satım)
- Fiyat > MA20
- Volume surge > 1.5x (20-day avg)
- 1 aylık momentum > %5
- Makro rejim sektörü destekliyor
- Kurumsal akış pozitif veya nötr

### Çıkış Koşulları (SELL)
- RSI > 80 (aşırı alım, kurumlar çıkıyor)
- RSI < 35 (momentum kaybı)
- Fiyat < MA20 ve düşüş trendi
- Stop-loss seviyesi tetiklendi
- Kurumsal distribution sinyali (hacim yüksek, fiyat düz/düşüş)
- Makro rejim sektöre karşı döndü

### Pozisyon Büyüklüğü
- High conviction: %15-20 portföy
- Medium conviction: %5-10 portföy
- Low conviction: Çık

### Küçük Yatırımcı Tuzakları (Kaçınılacaklar)
- RSI 80+ hisseye "tren kaçıyor" diye binmek
- Haberden sonra almak (fiyata zaten yansımış)
- Stop-loss koymamak ("döner" umududuyla beklemek)
- Aynı sektörden çok hisse (hidden correlation)
- Kurumlar saterken retail alıyor (distribution tuzağı)

---

## Mevcut Pozisyon Kararları (12 Mayıs 2026)

| Ticker | Durum | Karar | Seviyeler |
|--------|-------|-------|-----------|
| KCHOL | ✅ Güçlü (+%10.6, RSI 57) | TUT | Hedef ₺225, Stop ₺195 |
| TTKOM | ✅ İyi (+%7.3, RSI 55) | TUT | Hedef ₺70, Stop ₺62 |
| AKSEN | ⚠️ Zayıf (-%3.8, RSI 54) | İZLE | ₺82 altı → KES |
| ENERY | ⚠️ Nötr (-%0.7, RSI 51) | İZLE | ₺9.50 üstü → TUT, ₺8.50 altı → KES |
| TAVHL | ❌ Çok Zayıf (-%4.5, RSI 36) | SAT | Stop ₺263.58 → Tetiklendi |

**Momentum Watchlist:**
- KRDMD: RSI 83 → BEKLE, RSI 60 altı → AL
- PETKM: RSI 77 → BEKLE
- EREGL: RSI 77, BofA satıyor → UZAK DUR
- AKBNK: BofA alıyor → RSI kontrol et, ₺10-12K pozisyon değerlendir
- BIMAS: BofA SATIYOR → UZAK DUR

---

## Öncelikli Sonraki Adımlar

### Hemen (Bu Hafta)
1. Anthropic API key al
2. `orchestrator.py` Python bridge inşa et (Claude Code)
3. Analyst + Auditor + Efficiency agent system prompt'larını yaz
4. Intelligence klasör yapısını kur

### Kısa Vade (2 Hafta)
5. KAP scraper implement et
6. Earnings calendar entegrasyonu
7. Makro data (petrol, USD/TRY, VIX) feed ekle

### Orta Vade (1 Ay)
8. News sentiment NLP pipeline
9. Institutional flow tracker (BofA + yabancı akım)
10. Multi-layer signal engine

### Uzun Vade (3 Ay)
11. ML pattern recognition
12. Backtesting framework
13. Tam otomasyon (sıfır insan müdahalesi rutin işlerde)

---

## Önemli Notlar
- Narrative zekası Engine'e girmez, Analyst Agent promptunda kalır — backtest bütünlüğü korunur
- Bull Trap istisnası: kap_official kaynaklı pozitif event varsa mutlak veto → downgrade'e dönüşür
- **Smart Money kaynağı:** Borsa İstanbul takas raporu (günlük, ücretsiz) — format araştırılacak, `smartmoney_layer.py` stub olarak bekliyor
- **Narrative zekası Engine'e girmez:** Analyst Agent prompt'unda kalır — "Lokal makro rejim bu hissenin hikayesini destekliyor mu?" perspektifi
- **Bull Trap mantığı:** Teknik BUY-STRONG + 3 gün üst üste kurumsal net satış → HOLD override (henüz implement edilmedi, Layer 5 planı)
- Sistem her sabah 09:00'da otomatik çalışıyor
- Manuel çalıştırma: `python scripts/daily_update.py --scan --generate-report`
- Raporlar: `C:\Users\cagan\bist-trading-system\reports\`
- Config: `C:\Users\cagan\bist-trading-system\config.yaml`
- Bu dosya her büyük karar değişikliğinde güncellenecek
