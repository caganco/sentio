# 🔴 ORCHESTRATOR — KRİTİK DURUM DEĞERLENDİRMESİ

---

## SORUN #1: SİSTEM KIRIK — VERİ ÇEKMİYOR

Rapor **tamamen NaN**. 23 hisseden sadece **ENERY.IS** veri getirmiş. Bu demek ki:

- Yahoo Finance API bağlantısı 22/23 hisse için **fail ediyor**
- Rapor üretiyor ama **boş veriyle** — yani sana yanlış güven veriyor
- Günlük otomasyon çalışıyor gibi görünüp **hiçbir iş yapmıyor**

> **Bu 1 numaralı öncelik. Veri yoksa hiçbir şey yok.**

---

## SORUN #2: BUILDER OUTPUT KAOS

"Code'un verdiği output çok fazla alternatif yol indike ediyor" diyorsun. Bu klasik bir problem: Builder Agent direktif bekliyor ama **net spec almıyor**, o da her olasılığı sıralıyor.

**Çözüm:** Her task için tek sayfalık, net SPEC vermek. Bunu ben yazacağım.

---

## SORUN #3: USAGE LİMİT → WORKFLOW KOPUK

Desktop Orchestrator'a sonuç atamadan limit bitmiş. Yani **karar zinciri kırık**. Agent'lar arası iletişim manuel ve fragile.

---

## ACİL AKSİYON PLANI

### 🔴 P0 — BUGÜN (Veri Düzelt)

**Builder'a ver bu SPEC'i:**

```
TASK: Yahoo Finance NaN Bug Fix
PRIORITY: BLOCKING — hiçbir şey bundan önce gelmez

PROBLEM:
- daily_update.py çalışıyor ama 22/23 hisse NaN döndürüyor
- Sadece ENERY.IS veri geliyor
- Rapor tarihi 13.05.2026 01:38 (gece yarısı — piyasa kapalı)

ARAŞTIR:
1. fetcher.py'de Yahoo Finance API call'ını debug et
2. Tek bir hisse ile test et: THYAO.IS
3. Hata yfinance rate limit mi, format mı, timeout mı?
4. yfinance kütüphanesini güncelle: pip install --upgrade yfinance

TEST:
python -c "import yfinance as yf; print(yf.download('THYAO.IS', period='5d'))"

ÇIKTI: Çalışan fetcher + 23 hissenin tamamı veri çeken rapor

ALTERNATİF YOL SUNMA. TEK ÇÖZÜM BUL, IMPLEMENT ET, TEST ET.
```

### 🟡 P1 — YARIN (Rapor Doğrulandıktan Sonra)

Builder'a ikinci task:

```
TASK: Intelligence Klasör Yapısı
PRIORITY: P1

OLUŞTUR:
C:\Users\cagan\bist-trading-system\agents\intelligence\
├── daily_briefing_YYYY-MM-DD.json  (daily_update.py otomatik üretsin)
├── decisions\                       (orchestrator kararları)
└── README.md                        (format açıklaması)

daily_briefing JSON format:
{
  "date": "2026-05-13",
  "portfolio": [...güncel pozisyonlar + P&L...],
  "scanner_top10": [...momentum skorları...],
  "alerts": [...stop-loss, RSI uyarıları...],
  "data_quality": {"total": 23, "success": X, "failed": [...]}
}

data_quality alanı ZORUNLU — kaç hisse veri çektiğini her gün göreceğiz.
```

### 🟢 P2 — BU HAFTA (Veri Çalışınca)

TAVHL ve diğer pozisyon kararlarını güncel veriyle revize et.

---

## PORTFÖY KARARLARI — ASKIDA

Veri NaN olduğu için karar veremiyorum. Ama **mevcut kurallar geçerli:**

| Pozisyon | Kural | Kontrol Edilecek |
|----------|-------|-----------------|
| TAVHL | SELL tetiklenmişti | **Fiyat ₺263.58 altında mı?** Piyasa açılınca kontrol et |
| AKSEN | ₺82 altı → KES | **Güncel fiyat lazım** |
| ENERY | ₺8.98 (tek çalışan veri) | RSI 49, maliyet ₺9.07, **-%1 zararda**. ₺8.50 yakın — DİKKAT |
| KCHOL | RSI 62 — sağlıklı | Veri gelince teyit |
| TTKOM | RSI 62 — sağlıklı | Veri gelince teyit |

**ENERY için anlık karar:**
> RSI 49, fiyat ₺8.98, maliyet ₺9.07. Nötr bölgede ama stop ₺8.34'e yaklaşıyor. **HOLD ama ₺8.50 altı günlük kapanışta KES.** Conviction: **MED**

---

## WORKFLOW DÜZELTMESİ

Mevcut sorun: Usage limit bitince zincir kopuyor.

**Geçici çözüm (bugünden itibaren):**

```
Sen (insan) → Builder'a SPEC ver (VS Code'da)
                ↓
Builder çalışır, output üretir
                ↓
Sen output'u bana yapıştır (bu chat)
                ↓
Ben karar + yeni direktif veririm
                ↓
Sen Builder'a iletir
```

**Kalıcı çözüm:** orchestrator.py + API key. Ama önce **veri düzelmeli**.

---

## ÖZET — 3 CÜMLE

1. **Sistem kırık** — 22/23 hisse NaN, veri çekilmiyor, rapor anlamsız
2. **P0: fetcher.py'yi bugün düzelt** — yukarıdaki SPEC'i Builder'a ver
3. **Portföy kararları askıda** — veri gelince TAVHL SELL'i teyit edeceğiz, ENERY ₺8.50 kritik

**Builder'a SPEC'i ver, output'u bana getir. Hareket edelim.**

[tokens: 17513 in / 1780 out]