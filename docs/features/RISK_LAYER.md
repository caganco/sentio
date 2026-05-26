# Feature Guide: Risk Layer (Vol Targeting + Net EV + ADV Cap)
**Son güncelleme:** 26 Mayıs 2026 — D-154
**Durum:** Vol targeting gözlem modu ✅ | Net EV check aktif ✅ | ADV cap aktif ✅
**Sorumlu direktifler:** D-145 (ADV), D-146 (Net EV), D-147 (Vol), D-154 (composite removal)

> **D-154 Notu (2026-05-26):** `score_risk()` (L6) composite formülünden **çıkarıldı**.
> Gerekçe: MASTER_WEIGHTS["risk"] = 0.03 → maksimum composite katkısı 2.1 puan (gürültü seviyesi).
> `score_risk()` yalnızca **pozisyon boyutlandırma** tarafında (Kelly / ADV cap / Net EV / Vol scalar)
> kullanılmaya devam ediyor — bu taraf değişmedi. MASTER_WEIGHTS'te "risk" anahtarı artık yok;
> kalan 5 katman 0.97'ye bölünerek renormalize edildi (toplam = 1.000). Bkz. RR-022 §1.3.

---

## Ne Yapar

Pozisyon büyüklüğünü 3 katmanlı risk filtresiyle kısıtlar:

```
size_position(conviction, macro_scaling, equity)
    ↓
apply_adv_cap(ticker, decision)        ← D-145: likidite kısıtı
    ↓
net_expected_value_check(ticker, expected_return, decision)  ← D-146: maliyet filtresi
    ↓
[Daily Report'ta vol_scalar + ENERY flag]  ← D-147: gözlem
```

---

## Katman 1: ADV Cap (D-145)

`max_position = min(Kelly, POSITION_MAX_ADV_PCT × ADV_20d)`

**Amaç:** Thin market'te piyasayı sarsmamak (Almgren 2005).
**Değer:** `POSITION_MAX_ADV_PCT = 0.05` (günlük ortalama hacmin %5'i)
**Non-fatal:** yfinance başarısız → cap uygulanmaz, Kelly değeri kullanılır.

---

## Katman 2: Net EV Check (D-146)

`net_ev = gross_ev - round_trip_cost; gir sadece net_ev ≥ 0.005`

**Broker:** `BROKER_TIER = "A"` (Garanti BBVA, %1.05 round-trip) — **Cagan kararı (DEC-025)**

| Ticker | Cost | Neden |
|--------|------|-------|
| ENERY, AYGAZ, GUBRF | %1.3 | `HIGH_COST_TICKERS` — mikro-cap |
| Diğerleri | %1.05 | Tier A |

**Dikkat:** BUY-MEDIUM sinyali (gross ~%1.1-1.5) Net EV check'te NO-TRADE dönebilir. Bu kasıtlı — zayıf sinyal maliyet karşılayamıyor.

Broker değişirse: `thresholds.py`'de `BROKER_TIER` güncelle, `_TIER_COSTS` dict'ine ekle.

---

## Katman 3: Vol Targeting — GÖZLEM MODU (D-147)

**Şu an pozisyon kararına ETKİSİ YOK** — sadece daily report'ta görünür.

| Sabit | Değer | Anlam |
|-------|-------|-------|
| `PORTFOLIO_TARGET_VOL_ANNUAL` | 0.15 | Bridgewater hedef volatilite |
| `VOL_SCALAR_CAP` | 1.50 | Maximum kaldıraç önerisi |
| `VOL_SCALAR_FLOOR` | 0.20 | COVID seviyesi vol için minimum |
| `MAX_SINGLE_VOL_CONTRIB` | 0.40 | Tek hisse vol dominance eşiği |

**ENERY flag:** vol_contribution = 0.40 (eşikte) — σ %60'a çıkınca daily report'ta kırmızı uyarı tetiklenir.

**Faz 2 (D-150 sonrası):** vol_scalar aktive edilir, pozisyon kararına etki başlar.

---

## Execution Timing Notu

Ekinci (2003) BIST intraday pattern: sabah "inverse J" + öğleden sonra "U".
`EXECUTION_WINDOW_MORNING_START = "10:30"`, `END = "11:30"`
`EXECUTION_WINDOW_AFTERNOON_START = "14:00"`, `END = "15:30"`

**Bu sadece rapor notu — otomatik emir değil.**

---

## Risk Metrikleri (daily_report'ta)

D-147 ile eklenenler:
- **Ulcer Index** (Peter Martin 1987) — süre × derinlik cezalı DD
- **Calmar Ratio** — yıllık getiri / MDD
- **Sortino Ratio** — downside volatiliteye göre risk-adjusted getiri
- **Current Drawdown** — mevcut tepe'den düşüş

---

## Neye Dokunma

| Yasak | Neden |
|-------|-------|
| Vol_scalar'ı aktive etme (Faz 2 olmadan) | Gözlem verisi yetersiz, yanlış scalar üretir |
| `BROKER_TIER`'ı kod içinde override | DEC-025 — sadece thresholds.py'den |
| HIGH_COST_TICKERS'tan ENERY çıkarma | %1.3 round-trip gerçek maliyet |
| `apply_adv_cap` ve `net_expected_value_check` sırasını değiştirme | ADV önce, cost sonra — sıra kasıtlı |
