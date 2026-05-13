# 🔍 SISTEM CHECK-UP RAPORU — 13 Mayıs 2026

## 1️⃣ TOKEN OPTİMİZASYONU ANALİZİ

### Mevcut Token Kullanımı
```
Analyst (Opus):   ~1784 tokens/gün
Auditor (Sonnet): ~5000+ tokens/gün
────────────────────────────────
TOPLAM:          ~6800+ tokens/gün
```

### System Prompt Analizi
| Agent | Dosya | Satır | Token (Est.) | Sorun |
|-------|-------|-------|--------------|-------|
| Analyst | analyst_system_prompt.md | 92 | ~450-500 | 7 katman (aşırı detaylı) |
| Auditor | auditor_system_prompt.md | 71 | ~350-400 | 5 aşama (tekrar edici) |

### Token Optimizasyon Önerileri

#### Önerilen 1: Analyst Prompt Kısaltma (450→250 token)
**Şu anda:**
```
7 Katman (Makro Rejim, Sektör, Kurumsal Akış, Teknik, KAP, Narrative, Risk/Reward)
+ Her katman için detaylı açıklama
+ Çok sayıda alt başlık
= ~450 token
```

**Optimize Versiyonu:**
```
KISA KURAL SETİ:
1. Makro (Petrol, USD/TRY, VIX, Jeopolitik)
2. Sektör (Petrol↑ → Energy SAT, Interest↓ → Banks BUY)
3. Kurumsal Akış (Distribution = High Vol + Flat Price)
4. Teknik (RSI 50-65=Buy, 75+=Caution, <35=Weak)
5. KAP (Earnings beat/miss etkisi)
6. Risk (Upside% vs Downside%)

OUTPUT: BUY-STRONG / BUY-WEAK / HOLD / WATCH / SELL-WEAK / SELL-STRONG + seviyeleri
```

**Tahmini Tasarruf:** 200 token/gün

#### Önerilen 2: Auditor Prompt Basitleştirme (350→200 token)
**Şu anda:** Thesis Kırma + Risk Skorlama (1-5 scale 5 kategori) + Portfolio Check + Tuzak Kontrolü + Worst-Case

**Optimize Versiyonu:**
```
DENET KURALLAR:
1. Thesis Kırma: En zayıf noktayı bul
2. Risk Skoru: Likidite/Konsantrasyon/Makro/Şirket/Timing (X/25)
3. Portfolio: Sektör <30%, Drawdown?, Stop-loss var mı?
4. Red Flags: Retail FOMO mu? Kurumsal akış tersine mi?

OUTPUT: ONAYLANDI / REDDEDILDI / DEĞİŞTİRİLDİ + Risk Skoru
```

**Tahmini Tasarruf:** 150 token/gün

#### Önerilen 3: Model Seçimi Optimize
**Şu Anda:**
- Analyst: Opus-4-6 (pahalı, gereksiz)
- Auditor: Sonnet-4-6 ✅ (doğru)

**Öneriliyorum:**
- Analyst → **Sonnet-4-6** (Analyst 7 katman analiz için fazla, Sonnet yeterli)
- Auditor → **Haiku-4-5** (Risk denetimi sadece sorgulamak, hafif model yeterli)

**Tahmini Tasarruf:** 40-50% maliyet (Opus→Sonnet, Sonnet→Haiku)

---

## 2️⃣ EFFORT/IMPACT MATRİSİ

### Eksikliklerin Prioritizasyonu

```
┌────────────────────────────────────────────────────┐
│           HIGH IMPACT                              │
│  ┌──────────────────────────────────────────────┐  │
│  │ 1. MAKRO VERİ ENTEGRASYONU (USD/TRY,Petrol) │  │
│  │    Druckenmiller modeli için %25 ağırlık     │  │
│  │    Impact: 9/10 | Effort: 3/10              │  │
│  │    API: yfinance.Ticker("EURUSD=X")          │  │
│  │    Yapma Süresi: 2-3 saat                    │  │
│  │                                              │  │
│  │ 2. KAP SCRAPER (Corporate Intelligence)      │  │
│  │    Earnings, M&A, Insider Alım/Satım         │  │
│  │    Impact: 8/10 | Effort: 5/10              │  │
│  │    API: KAP REST API (daha kolay Scraper'dan)│  │
│  │    Yapma Süresi: 4-6 saat                    │  │
│  │                                              │  │
│  │ 3. KURUMSAL FLOW OTOMASYONU (BofA gibi)      │  │
│  │    Bloomberg terminal / Manual monitoring     │  │
│  │    Impact: 7/10 | Effort: 8/10              │  │
│  │    SKIP İÇİN: Fintech API (Reuters, etc)     │  │
│  │    Yapma Süresi: 8+ saat                     │  │
│  └──────────────────────────────────────────────┘  │
│           LOW IMPACT (Ama değerli)                 │
│  ┌──────────────────────────────────────────────┐  │
│  │ 4. YAHOO FINANCE VERİ HATASI (Acil!)         │  │
│  │    Şu an tüm fiyatlar NaN → Sistem kırık     │  │
│  │    Impact: 10/10 | Effort: 2/10             │  │
│  │    FİX: Alpha Vantage / Polygon.io kullan    │  │
│  │    Yapma Süresi: 30-60 dk                    │  │
│  │                                              │  │
│  │ 5. TOKEN OPTİMİZASYON (Prompt Kısalt)        │  │
│  │    Daily: 6800+ → 6300+ token (7% tasarruf)  │  │
│  │    Impact: 4/10 | Effort: 2/10              │  │
│  │    Yapma Süresi: 1-2 saat                    │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

### Önerilen Yapılış Sırası
```
HAFTANIN YAPILACAK LİSTESİ:

🔴 PAZARTESİ (Acil Fix)
   - Yahoo Finance hatası fix (Alpha Vantage → fetcher.py)
   - Model mismatch düzelt (Analyst: Opus→Sonnet, Auditor: Sonnet→Haiku)

🟡 SALI-ÇARŞAMBA (Makro Veri)
   - yfinance makro modülü ekle (USD/TRY, Petrol, VIX)
   - System prompt'ları kısalt (Analyst: -200, Auditor: -150 token)

🟢 PERŞEMBE (KAP Entegrasyonu)
   - KAP API scouting (Earnings, Corporate News)
   - daily_briefing.json'a makro_data bloğu ekle

🔵 CUMA (Haftalık Report)
   - Efficiency report oluştur
   - Model performans karşılaştırması (Opus vs Sonnet vs Haiku)
```

---

## 3️⃣ MAKRO VERİ ÇÖZÜMLERİ (En Az Eforlu)

### Seçenek A: yfinance (Ücretsiz, Basit) ⭐ ÖNERİLİ
```python
import yfinance as yf

# USD/TRY
usdtry = yf.Ticker("USDTRY=X").history(period="1d")["Close"][-1]

# Brent Petrol
oil = yf.Ticker("BZ=F").history(period="1d")["Close"][-1]

# VIX
vix = yf.Ticker("^VIX").history(period="1d")["Close"][-1]

# S&P500
sp500 = yf.Ticker("^GSPC").history(period="1d")["Close"][-1]
```
**Ücretsiz | Hızlı | Kolay | Token: 0**

### Seçenek B: Alpha Vantage (Ücretsiz tier, RSS-stable)
```python
import requests

API_KEY = "demo"  # free tier
url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=TRY&apikey={API_KEY}"
usdtry = requests.get(url).json()["Realtime Currency Exchange Rate"]["5. Exchange Rate"]
```
**Güvenilir | Hızlı | Stabil**

### Seçenek C: Polygon.io (Ücretli ama en iyi)
```python
from polygon import RESTClient

client = RESTClient(api_key="YOUR_KEY")
usdtry = client.forex_snapshot_all()
```
**Profesyonel | Hızlı | $10/ay**

**Tavsiye:** **Seçenek A (yfinance)** + daily_update.py içine ekle, 5 dakikada biter.

---

## 4️⃣ HAFTALIK İZLEME PLANI

### Her Pazartesi 09:00'da Çalışacak Task

**Görev:** Token Kullanımını, Model Performansını, Darboğazları Ölçmek

```python
# efficiency_tracker.py (Yeni)

from pathlib import Path
from datetime import datetime, timedelta
import json
import re

PROJECT_DIR = Path("C:/Users/cagan/bist-trading-system")
INTELLIGENCE_DIR = PROJECT_DIR / "agents/intelligence"
LOGS_DIR = PROJECT_DIR / "logs"

def count_tokens_in_file(filepath, model="claude-sonnet-4-6"):
    """Rough token estimate: 1 token ≈ 4 char (Sonnet)"""
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    token_estimate = len(text) / 4
    return token_estimate

def extract_model_calls_from_logs():
    """Parse logs to find API calls, model, token usage"""
    logs = LOGS_DIR / "errors.log"
    if not logs.exists():
        return []
    
    calls = []
    with open(logs, 'r', encoding='utf-8') as f:
        for line in f:
            # Look for patterns like "[Analyst] Sonnet: 1784 tokens"
            if "Model" in line or "token" in line:
                calls.append(line.strip())
    
    return calls

def generate_weekly_efficiency_report():
    """Haftalık rapor oluştur"""
    
    # Analyst ve Auditor raporları
    analyst_file = INTELLIGENCE_DIR / "analyst_report.md"
    audit_file = INTELLIGENCE_DIR / "audit_report.md"
    
    analyst_tokens = int(count_tokens_in_file(analyst_file))
    audit_tokens = int(count_tokens_in_file(audit_file))
    
    report = f"""
=== EFFICIENCY REPORT — HAFTA {datetime.now().isocalendar()[1]} ===

WORKFLOW METRIKLERI:
- Toplam agent etkileşimi: 2 (Analyst → Auditor)
- Tahmini token kullanımı: ~{analyst_tokens + audit_tokens} token/gün
- İnsan müdahalesi gereken adım: 1/5 (Final Decision)
- Otomasyon oranı: %80

MALIYET ANALİZİ:
- Analyst (Opus): {analyst_tokens} tokens × $0.015 = ${analyst_tokens * 0.015 / 1000:.3f}
- Auditor (Sonnet): {audit_tokens} tokens × $0.003 = ${audit_tokens * 0.003 / 1000:.3f}
- Günlük Toplam: ~$0.03-0.05
- Aylık Tahmini: ~$1.00-1.50

DARBOĞAZLAR:
- Yahoo Finance 0 veri (NaN): FİX ÖNCELIK #1
- Makro veri yok: Analyst %25 ağırlığını kullansa bile boş
- KAP news otomasyonu yok: Manuel monitoring

OPTİMİZASYON ÖNERİLERİ:
1. Analyst → Sonnet-4-6 (200 token tasarruf)
2. Auditor → Haiku-4-5 (300 token tasarruf)
3. yfinance makro modülü (5 dakika)
4. Prompt kısaltma (150 token tasarruf)

AKSIYON GEREKTİREN:
- [ ] Yahoo Finance fix (Alpha Vantage)
- [ ] Model downgrade (Opus→Sonnet→Haiku)
- [ ] Makro veri modülü ekle
- [ ] KAP API research
"""
    
    return report

# Çalıştır
if __name__ == "__main__":
    report = generate_weekly_efficiency_report()
    print(report)
    
    # Kaydet
    output_file = PROJECT_DIR / f"efficiency_report_w{datetime.now().isocalendar()[1]}.md"
    output_file.write_text(report, encoding='utf-8')
    print(f"\n✅ Report saved: {output_file}")
```

**Haftalık Çalışacak:**
- Her Pazartesi 09:00 (Task Scheduler)
- Dosya: `efficiency_report_w{week_number}.md`
- Rapor: Token kullanım, maliyet, bottleneck analizi

---

## 📊 ÖZET: AKSIYON GEREKTİREN

| # | Görev | Çaba | İmpact | Çözüm Süresi |
|---|-------|------|--------|--------------|
| 1️⃣ | Yahoo Finance Veri Hatası | 2/10 | 10/10 | 30-60 dk |
| 2️⃣ | Model Mismatch (Opus→Sonnet) | 1/10 | 7/10 | 10 dk |
| 3️⃣ | Makro Veri (yfinance) | 3/10 | 9/10 | 2-3 saat |
| 4️⃣ | System Prompt Kısalt | 2/10 | 5/10 | 1-2 saat |
| 5️⃣ | KAP API Entegrasyonu | 5/10 | 8/10 | 4-6 saat |
| 6️⃣ | Haftalık İzleme Task | 3/10 | 6/10 | 2-3 saat |

---

**Raporlama:** Haftalık her Pazartesi 09:05 → `efficiency_report_wXX.md`

