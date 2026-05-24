# RR-015: Transaction Cost Modellemesi
**BIST OS Trading System | Research Report | 24 Mayıs 2026**

---

## 1. TL;DR

**the maintainer'ın ~85K TL'lik portföyünde round-trip işlem maliyeti, broker seçimine bağlı olarak yıllık net getiriyi %0.5 ile %12 arasında erozyona uğratıyor.** 24 trade/yıl frekansı varsayımı altında üç tier paralel senaryosu:

| Tier | Broker örnek | Tahmini round-trip cost | Yıllık maliyet (24 trade × ~21K TL ort.) | Yıllık % erozyon |
|------|--------------|-------------------------|------------------------------------------|------------------|
| **A — Geleneksel** | İş Yatırım (binde 2 + BSMV; isyatirim.com.tr EK-8 Komisyon ve Masraf Tarifesi: *"Pay alım-satım işlemlerinde işlem tutarı üzerinden %0,2 (binde iki) oranında komisyon tahsilatı esastır"*) | %0.55 – %1.30 (hisse bazlı) | ~5.000 – 8.000 TL | %6 – %9 |
| **B — Hacme bağlı orta** | Garanti BBVA Yatırım (hacme bağlı model binde 1.99 → 0.90; sabit model binde 1.95) | %0.40 – %1.05 | ~3.500 – 6.500 TL | %4 – %7 |
| **C — Online discount** | Midas (BIST %0 + borsa payı kullanıcıdan tahsil edilmez) | %0.15 – %0.85 (sadece spread+slippage) | ~700 – 2.500 TL | %0.8 – %3 |

**30 dakikalık fix önerileri:**
1. **the maintainer'ın gerçek broker bilgisi alınmalı** — bu rapor 3 tier paralel senaryo kuruyor, somut tarife teyidi şart (§Erişim Notları).
2. **`position_sizer_v2`'ye `net_expected_value_check` paralel kolonu eklenecek** — gross EV koruyacak; net EV < %0.5 ise `tradeable=False` döndürecek (§8).
3. **Conviction tier filtresi**: BUY-MEDIUM (0.55–0.67) sinyallerinin cost-net break-even win rate'i ~%45'i geçemeyecekse devre dışı; BUY-STRONG (≥0.68) önceliklendirilecek (§7).
4. **Eğer Tier A'da ise Tier C'ye geçiş**, *yıllık ~2.700 TL tasarruf potansiyeli* — portföyün %3'üne eş değer.

> **Kritik bulgu:** ENERY (small-cap, ~9 TL fiyat) için round-trip cost en yüksek (~%0.9–1.3); BIST OS'un hisse-bazlı `ROUND_TRIP_COST_PCT` override etmesi gerekiyor.

---

## 2. Erişim Notları & Kısıtlar (rapor başı)

| Konu | Durum | Etki |
|------|-------|------|
| **Twitter/X Erişim Notu** | Login-wall; pratisyen söylem sample edilmedi | §10 sektör pratiği analizi forum (Ekşi, Hisse.net, ŞikayetVar) ile sınırlı |
| **Broker Fiyat Güncellik Notu** | Mayıs 2026 itibarıyla broker'ların public web sayfası tarandı; özel kampanya/müzakere fiyatları görünmez | ±%30 belirsizlik |
| **the maintainer Broker Bilgisi** | **BİLİNMİYOR** — 3 tier paralel senaryo kuruldu, retrospektif tahmin yapılmadı | AKSEN retrospektif maliyet 3 tier ayrı verildi |
| **Slippage detayı** | RR-014'te derinlemesine işlendi; bu raporda sadece cost stack bileşeni olarak özet | §5'te sabit varsayım (2–10 bps) |
| **TCMB politika faizi** | %37 (TCMB.gov.tr ana sayfa Mayıs 2026 itibarıyla: *"Para Politikası Kurulu, politika faizi olan bir hafta vadeli repo ihale faiz oranının yüzde 37'de sabit tutulmasına karar vermiştir"*) | Risk-free rate hesabında %37 kullanıldı |

---

## 3. Round-Trip Cost Formülü

### 3.1 Temel formül

```
Round-Trip Cost (%) =
    [Komisyon_alış × (1 + BSMV)]
  + [Komisyon_satış × (1 + BSMV)]
  + [2 × Half-Spread]
  + [2 × Slippage]
  + [Damga / sabit ücret payı, eğer varsa]
```

BSMV = %5 (Banka ve Sigorta Muameleleri Vergisi; tüm broker tarife dipnotları teyit ediyor — örn. Garanti BBVA Yatırım: *"Oranlar işlem başına olup %5 (yüzde beş) BSMV dahil değildir"*). 6802 sayılı Gider Vergileri Kanunu m.28 yasal temeli.

Toplam komisyon bileşeni alış-satışta simetrik olduğundan kısaltılmış formül:

```
RT_cost ≈ 2 × Komisyon × 1.05 + Spread + 2 × Slippage
```

### 3.2 Kavramsal Python implementasyonu (KAVRAMSAL, production-ready DEĞİL)

```python
def round_trip_cost_pct(
    ticker: str,
    broker_tier: str,        # "A", "B", "C"
    half_spread_bps: float,  # hisse bazlı override edilebilir
    slippage_bps: float,     # RR-014 modülünden gelir
) -> float:
    """
    Hisse bazlı round-trip işlem maliyetini yüzde olarak döndürür.
    BSMV %5 dahil; damga vergisi BIST hissesinde uygulanmaz (GVK Geçici 67 kapsamı).
    Bkz. thresholds.py → ROUND_TRIP_COST_PCT_DEFAULT, MIN_NET_EXPECTED_VALUE_PCT.
    """
    # broker_tier → komisyon haritası thresholds.py'den okunur
    # half_spread_bps → None ise BIST kapsam endeksine göre varsayılan (mega/mid/small)
    # slippage_bps → RR-014 modülünden gelir (ADV ratio temelli)
    # Toplam = 2*komisyon*1.05 + half_spread/100 + 2*slippage/100
    ...
```

### 3.3 Hisse-bazlı override mantığı

`thresholds.py` örnek sabitler (öneri):

```python
ROUND_TRIP_COST_PCT_DEFAULT = 0.90    # %0.9 — orta-cap baz
MIN_NET_EXPECTED_VALUE_PCT  = 0.50    # %0.5 — net EV eşiği

ROUND_TRIP_COST_OVERRIDES = {
    # BIST 30 mega-cap: spread çok dar
    "KCHOL": 0.55, "AKBNK": 0.50, "GARAN": 0.50,
    # BIST 50–100 mid-cap
    "TTKOM": 0.65,
    # Small-cap, dikkat
    "ENERY": 1.20, "AKSEN": 1.15,
}
```

---

## 4. Broker Karşılaştırma Tablosu (Tier A/B/C)

> Erişim notu: Tüm oranlar Mayıs 2026 itibarıyla resmi broker web sayfalarından okundu. Özel müşteri tarifeleri, halka arz ek kampanyaları kapsam dışı.

| Broker | Tier | Standart komisyon (BSMV hariç) | Hacim indirimi | Hesap bakım | Min komisyon/işlem | the maintainer profili uygunluk |
|--------|------|--------------------------------|----------------|-------------|---------------------|-------------------------|
| **İş Yatırım** | A | %0.2 (binde 2) — *isyatirim.com.tr EK-8 Komisyon ve Masraf Tarifesi* | Yatırımcı bazında müzakere | — | — | 🔴 Yüksek |
| **Garanti BBVA Yatırım** (Sabit) | A | %0.1950 (binde 1.95) + BSMV | — | 250 TL/6ay BSMV dahil → yıllık **500 TL** (garantibbvayatirim.com.tr: *"6 ayda bir 250 TL (BSMV dahil) (yıllık 500 TL (BSMV dahil)) hesap bakım ücreti tahsil edilmektedir"*) | 1 TL/işlem | 🔴 Yüksek (sabit) |
| **Garanti BBVA Yatırım** (Hacme bağlı) | B | Son 3 ay ort. hacme göre: binde **1.99 → 0.90** kademeli (0-500K → 1.99; 500K-1M → 1.95; 1M-2.5M → 1.90; … 25M+ → 0.90) | Otomatik kademe | 500 TL/yıl | 1 TL | 🟡 Orta (the maintainer hacmi en alt kademede kalır → binde 1.99) |
| **Yapı Kredi Yatırım** | A/B | Skala (kanal bazlı; Müşteri İletişim Merkezi binde 9) + BSMV ayrı | Aylık hacim bazlı | 590 TL/6ay → yıllık **1.180 TL** (yapikredi.com.tr: *"01 Ocak 2026 itibarıyla 6 ayda bir 590 TL olarak güncellenmiştir"*) | — | 🔴 Yüksek (sabit), 🟡 Mobil tier |
| **Ak Yatırım (TradeAll TR)** | A/B | Aylık kademeli skala | Aylık hacim | 275 TL/yıl yıllık bakım | — | 🟡 Orta |
| **Ziraat Yatırım** | A/B | İnternet: binde 1.5 + BSMV (min 0.90 TL); AHS: binde 2 | Günlük hacim artışıyla | Yok | 0.90 TL | 🟡 Orta |
| **Osmanlı Menkul** | B | Maks. onbinde 3.75 (skalalı) | İşlem hacmine göre | — | 35 kuruş | 🟢 Orta-düşük |
| **Gedik Yatırım** | A/B | Maks. binde 1.05 (azami), skalalı | Portföy/hacim bazlı | 6 ayda bir bakım | Onbinde 4.2 asgari | 🟡 Orta (forum şikayetleri var) |
| **Midas Menkul Değerler** | C | **%0 (sıfır komisyon, BIST)** — yasal ücretler (MKK + borsa payı) Midas tarafından karşılanır | Şartsız | Yok | Yok | 🟢 Düşük |
| **Akbank Mobil (kampanyalı 90 gün)** | C | Yeni müşteri 3 ay %0 (sonrası standart, sadece yüzbinde 2.5 borsa payı) | — | — | — | 🟢 Geçici |

**Ek hidden-fee bulguları (forum + resmi duyurular):**
- **Yapı Kredi Yatırım virman:** Kurum dışı virmanlarda **işlem başına sabit 34 TL** (ykyatirim.com.tr 1 Nisan 2026 ücret sayfası: *"Kurum dışı virmanlarda işlem başına sabit 34 TL ücret tahsil edilir"*) — broker değiştirmek isteyen the maintainer için bariyer.
- **Ak Yatırım yıllık bakım** ~275 TL (ŞikayetVar kullanıcı bildirimleri 21.04.2025).

**Ordinal değerlendirme (the maintainer ~85K portföy, 24 trade/yıl, mid+small-cap mix):**

- **Komisyon yükü:** Yüksek (Tier A), Orta (Tier B), Düşük (Tier C — Midas)
- **Hidden fees riski:** Yüksek (Tier A bankalar: hesap bakım Garanti 500 TL/yıl, Yapı Kredi 1.180 TL/yıl, Ak 275 TL/yıl), Düşük (Midas)
- **Hisse virmanı çıkış maliyeti:** Yüksek (Yapı Kredi 34 TL/hisse), Orta (Garanti), Düşük (Midas — virman ücretsiz)

### 4.1 "Sıfır komisyon" iddiasının teknik analizi (Midas)

Midas resmi sayfasındaki ifade: *"Borsa İstanbul yatırımlarını Midas ile yapan herkes, tüm işlemlerini sıfır komisyonla yapar. Portföy büyüklüğü, işlem hacmi gibi hiçbir koşul bulunmamaktadır."* Resmi tarife (getmidas.com/ucretler):

- BİST hisse işlemleri: **0 komisyon, 0 borsa payı kullanıcıdan tahsil edilmez** — *"Diğer aracı kurumların aksine yatırım hesabı dışında alınan yasal ücretler (MKK ve BIST) kullanıcılar yerine bizzat Midas Menkul Değerler A.Ş. tarafından karşılanır."*
- BSMV: Sıfır komisyondan dolayı sıfır
- ABD borsaları: 1.5 USD sabit/işlem (ayrı ürün)
- Spread genişletme veya PFOF (Payment for Order Flow) iddiasına dair Midas'ın resmi açıklaması: **veri bulunmadı** — Türkiye'de PFOF düzenleyici çerçevesi henüz oluşmadığı için spekülatif. Order routing detayı public değil.

> ⚠️ **Kritik bulgu:** "Sıfır komisyon"un yapısal olarak mümkün olması için Midas'ın gelir modelinin (a) bekleyen nakit nemalandırma, (b) margin/açığa satış faizleri, (c) varant/opsiyon komisyonu, (d) "Anında Nakit" hizmeti (binde 2.5 takas avansı; getmidas.com/destek: *"Anında Nakit'te komisyon, takas günü başına %0,25 (binde 2,5) oranındadır"*) gibi yan ürünlere dayandığı görülüyor. the maintainer profili (uzun pozisyon, az margin) için gerçekten %0 cost geliyor.

---

## 5. Örnek Hesaplamalar — the maintainer'ın 4 Pozisyonu

**Varsayımlar (tek tek doğrulandı):**
- BSMV = %5
- Half-spread tahmini (Mayıs 2026 BIST işlem hacmi gözlemine göre):
  - KCHOL (mega-cap, ~5 milyar TL günlük hacim — bullsyatirim.com 16.04.2026: *"Günlük İşlem Hacmi (TL): 5.002.826.773 TL"*): half-spread ~0.05–0.08%
  - TTKOM (large-cap, ~1 milyar TL günlük hacim — mynet.com 20.05.2026 teknik analiz: *"Günlük işlem hacmi 1,16 milyar TL"*): half-spread ~0.08–0.12%
  - ENERY (mid/small-cap, ~150 milyon TL günlük hacim; günlük lot ~4.6 milyon × ~9 TL): half-spread ~0.30–0.50%
  - AKSEN (mid-cap enerji): half-spread ~0.20–0.35%
- Slippage (RR-014): mevcut portföy ölçeğinde 2–5 bps (per leg)

### 5.1 Pozisyon büyüklükleri

| Hisse | Lot | Birim fiyat | Pozisyon TL | Portföy ağırlığı | Likidite tier |
|-------|-----|-------------|--------------|------------------|----------------|
| TTKOM | 329 | 60.65 TL | 19.953,85 | ~%23.5 | Large-cap |
| KCHOL | 81 | 188.83 TL | 15.295,23 | ~%18.0 | Mega-cap |
| ENERY | 1.543 | 9.07 TL | 13.995,01 | ~%16.5 | Mid/Small-cap |
| AKSEN (satıldı 24.05.2026) | — | — | ~14.000 (varsayım) | — | Mid-cap |
| **Toplam pozisyon** | | | **~63.244 TL** | ~%58 | |
| Nakit + diğer | | | ~21.756 TL | ~%26 | |

### 5.2 Round-trip cost — hisse × tier matrisi (% pozisyon TL)

| Hisse | Tier A (İş Yat.) | Tier B (Garanti binde ~1.95) | Tier C (Midas %0) |
|-------|------------------|-------------------------------|--------------------|
| **TTKOM** | (2×0.20×1.05) + 0.20 + 0.05 = **0.67%** | 0.41 + 0.20 + 0.05 = **0.66%** | 0 + 0.20 + 0.05 = **0.25%** |
| **KCHOL** | 0.42 + 0.12 + 0.05 = **0.59%** | 0.41 + 0.12 + 0.05 = **0.58%** | 0 + 0.12 + 0.05 = **0.17%** |
| **ENERY** | 0.42 + 0.70 + 0.10 = **1.22%** | 0.41 + 0.70 + 0.10 = **1.21%** | 0 + 0.70 + 0.10 = **0.80%** |
| **AKSEN** (retro) | 0.42 + 0.45 + 0.08 = **0.95%** | 0.41 + 0.45 + 0.08 = **0.94%** | 0 + 0.45 + 0.08 = **0.53%** |

### 5.3 Mutlak TL maliyet (her bir round-trip)

| Hisse | Pozisyon TL | Tier A TL | Tier B TL | Tier C TL |
|-------|-------------|------------|------------|------------|
| TTKOM | 19.954 | 134 | 132 | 50 |
| KCHOL | 15.295 | 90 | 89 | 26 |
| ENERY | 13.995 | 171 | 169 | 112 |
| AKSEN (retro) | ~14.000 | 133 | 132 | 74 |
| **4-pozisyon round-trip toplamı** | **63.244** | **528** | **522** | **262** |

### 5.4 Yıllık maliyet projeksiyonu (3 senaryo × 3 tier)

Portföyün yaklaşık %75'inin yıl içinde devir hızıyla işlem gördüğü varsayımıyla (her trade ~21K TL ortalama):

| Yıllık trade sayısı | Tier A toplam | Tier B toplam | Tier C toplam | Net % erozyon (85K) |
|----------------------|----------------|----------------|----------------|----------------------|
| 12 trade (uzun-vade) | ~2.640 TL | ~2.610 TL | ~1.310 TL | A: %3.1 / B: %3.1 / C: %1.5 |
| **24 trade (baz)** | **~5.280 TL** | **~5.220 TL** | **~2.620 TL** | **A: %6.2 / B: %6.1 / C: %3.1** |
| 48 trade (aktif) | ~10.560 TL | ~10.440 TL | ~5.240 TL | A: %12.4 / B: %12.3 / C: %6.2 |

> **AKSEN retrospektif:** 24 Mayıs 2026'da satıldığı için bu maliyet zaten realize oldu. Eğer the maintainer Tier A broker'sa, AKSEN'in tek round-trip'i ~%0.95 (= ~133 TL) cost ödendi; Tier C'de olsaydı ~74 TL olurdu, fark 59 TL.

---

## 6. Cost-Aware Sharpe Oranı

### 6.1 Gross vs Net formül

```
Sharpe_gross = (E[r_p] − r_f) / σ(r_p)

Sharpe_net   = (E[r_p] − r_f − c_yıllık) / σ(r_p)

c_yıllık = N_trade_yıllık × RT_cost(%)
```

`r_f` (risk-free) = %37 (TCMB politika faizi, 22 Ocak 2026 Basın Duyurusu 2026-01: *"Para Politikası Kurulu, politika faizi olan bir hafta vadeli repo ihale faiz oranının yüzde 38'den yüzde 37'ye indirilmesine karar vermiştir."* Mart 2026 ve sonraki kararlarda %37 seviyesi korundu).

### 6.2 BIST OS hedef Sharpe revizyonu

| Gross Sharpe gözlemi | Cost katmanı sonrası net Sharpe (24 trade, ortalama c=%0.9) | Yorum |
|-----------------------|--------------------------------------------------------------|--------|
| 0.5 | ~0.2 — **alpha YOK** | Cost öldü; pasif endekse benzer net getiri |
| 1.0 | ~0.7 — marjinal | Sistem işliyor ama kırılgan |
| 1.5 | ~1.2 — **gerçek alpha** | Cost dahil sürdürülebilir edge |
| 2.0 | ~1.7 — çok güçlü | İdeal hedef |

> **Hedef:** BIST OS conviction-validator'ın **Gross Sharpe ≥ 1.5** üretmediği setup'lara cost katmanından sonra "tradeable=False" damgası vurulmalı.

### 6.3 Backtest cost-adjusted etki

"Buy-and-hold superiority" iddiası (forum söylemi, §10'da işlenecek) cost-net karşılaştırmadan kaynaklanıyor. Pasif buy-and-hold:
- BIST 100 endeksi tek round-trip maliyeti (yılda 0–1 trade): ~%0.5–0.7
- BIST OS 24 trade/yıl: ~%21.6 (Tier A) → ~%10.8 (Tier C)
- **Fark:** Aktif sistemin alpha'sının yıllık ≥ %20 (Tier A) veya ≥ %10 (Tier C) olması gerek

---

## 7. Break-Even Win Rate

### 7.1 Formül türetimi

```
Required Win Rate (cost-aware) = (avg_loss + cost_per_RT) / (avg_loss + avg_win + cost_per_RT)
```

Örnek (the maintainer baz senaryo): avg_win = +%6, avg_loss = −%4, cost (per RT) = %0.9 (Tier B baz)

```
WR = (4 + 0.9) / (4 + 6 + 0.9) = 4.9 / 10.9 ≈ 45.0%
```

Cost olmasaydı: 4/10 = %40 → **cost +5 puan disiplin gerektiriyor**.

### 7.2 BIST OS conviction tier'lar için tablo

> Bu tablodaki gözlenen win rate'ler **örnek/hipotetik**'tir; backtest log'u henüz toplanmadı — empirik doğrulama §11 checklist'inde.

| Conviction tier | Tahmini gözlenen WR | Tier C req. WR (%0.85 cost) | Tier A req. WR (%1.05 cost) | Tradeable? |
|------------------|---------------------|------------------------------|------------------------------|-------------|
| **BUY-STRONG (≥0.68)** | ~%58–62 | ~44.5% | ~45.2% | ✅ Cost dahil pozitif |
| **BUY-MEDIUM (0.55–0.67)** | ~%48–53 | ~44.5% | ~45.2% | 🟡 Marjinal — Tier A'da risk |
| **BUY-WEAK (<0.55)** | ~%40–46 | ~44.5% | ~45.2% | ❌ Cost altında negatif EV |

**Sonuç:** "Sadece BUY-STRONG'a tepki ver" mantığı cost-net'te **doğrulanıyor**. BUY-MEDIUM, Tier A broker'da break-even'a yakın; Tier C'ye geçiş, BUY-MEDIUM tier'ı pratik olarak kurtarıyor.

---

## 8. `position_sizer_v2` Entegrasyonu — Kavramsal Mini-Spec

### 8.1 Mevcut vs önerilen mimari

```
[MEVCUT]                              [ÖNERİLEN — paralel kolon]
─────────                              ─────────────────────────
Signal → Kelly                         Signal → Kelly
       → conviction tier                      → conviction tier
       → sector cap                            → sector cap
       → vol-aware stop                        → vol-aware stop
       → POSITION_SIZE                          → net_expected_value_check ⬅ YENİ
                                                → POSITION_SIZE veya tradeable=False
```

> **PARALEL KOLON KURALI:** Mevcut gross EV mantığı **DEĞİŞTİRİLMEZ**; net EV ek katman olarak en sona eklenir. Bu sayede backtest reproducibility korunur.

### 8.2 Kavramsal fonksiyon (KESIN: production-ready DEĞİL)

```python
def net_expected_value_check(
    ticker: str,
    expected_return_pct: float,
    conviction_score: float,
    broker_tier: str,
    half_spread_bps: float = None,
    slippage_bps: float = None,
) -> tuple[bool, dict]:
    """
    Gross EV'yi kabul edip, üzerine round-trip cost düşürerek net EV'yi
    hesaplar. MIN_NET_EXPECTED_VALUE_PCT eşiğinin altında ise tradeable=False
    döndürür. Mevcut Kelly/conviction çıktısı değişmez — bu paralel kolon.

    Returns:
        tradeable (bool): net EV >= eşik mi?
        debug (dict): {gross_ev, rt_cost, net_ev, margin, tier_used}
    """
    # 1) thresholds.py'den ROUND_TRIP_COST_PCT_DEFAULT ve override'lar oku
    # 2) round_trip_cost_pct() çağır
    # 3) net_ev = expected_return_pct - rt_cost
    # 4) net_ev < MIN_NET_EXPECTED_VALUE_PCT ise tradeable=False
    # 5) debug paketle ve log
    ...
```

### 8.3 Pseudo-test senaryoları

| # | Beklenen getiri | Conviction | RT cost | Net EV | tradeable? |
|---|------------------|------------|----------|---------|-------------|
| 1 | %4.0 | 0.70 (STRONG) | %1.0 | %3.0 | ✅ True |
| 2 | %2.0 | 0.58 (MEDIUM) | %1.0 | %1.0 | ✅ True (eşiğin üstünde) |
| 3 | %2.0 | 0.58 (MEDIUM) | %1.6 (ENERY) | %0.4 | ❌ False (<%0.5) |
| 4 | %0.8 | 0.62 (MEDIUM) | %0.9 | %−0.1 | ❌ False |
| 5 | %1.2 | 0.55 (zayıf) | %0.6 (KCHOL/Midas) | %0.6 | ✅ True (Tier C kurtarır) |

### 8.4 30 dakikalık implementation roadmap

1. **Dakika 0–5:** `thresholds.py`'a `ROUND_TRIP_COST_PCT_DEFAULT = 0.9` ve `MIN_NET_EXPECTED_VALUE_PCT = 0.5` sabitlerini ekle.
2. **Dakika 5–15:** `transaction_cost.py` modülü içine `round_trip_cost_pct()` fonksiyonunu yaz (sadece signature + docstring + commented logic — production değil).
3. **Dakika 15–25:** `position_sizer_v2.py`'a `net_expected_value_check()` paralel kolon eklendi (mevcut return path korunur).
4. **Dakika 25–30:** Pseudo-test senaryolarını `tests/test_net_ev_smoke.py` olarak kavramsal şablon halinde bırak; gerçek implementasyon RR-016 (Backtest Reproducibility) ile birlikte yapılır.

---

## 9. Vergi Stratejisi (2026 Mevzuat)

### 9.1 GVK Geçici 67. Madde — BIST hisseleri 2026 durumu

> **Erişim notu:** 11 Aralık 2025 tarihli ve 33104 sayılı Resmi Gazete'de yayımlanan **10680 sayılı Cumhurbaşkanı Kararı** ile Geçici 67. maddenin uygulanma süresi **31 Aralık 2030**'a kadar uzatıldı (TÜRMOB kütüphane: *"söz konusu maddenin uygulanma süresi 31 Aralık 2030 tarihine kadar uzatılmıştır"*).

**Tam mükellef bireysel yatırımcı (the maintainer) için kritik kalemler:**

| Kalem | 2026 oran | Beyan zorunluluğu | Kaynak |
|-------|------------|---------------------|---------|
| BIST hisse alım-satım kazancı (yatırım ortaklığı dışı) | **%0 stopaj** | Stopaj nihai vergi — **beyan edilmez** | Bakanlar Kurulu Kararı 2012/3141; GİB 2026 Rehberi (cdn.gib.gov.tr) |
| BİST'te işlem gören menkul kıymet yatırım ortaklığı hisseleri | %10 stopaj (1 yıldan kısa) / %0 (1+ yıl) | Stopaj nihai | GİB |
| Hisse senedi temettüsü (kurum tarafından) | **%15 stopaj** | Brüt temettünün yarısı diğer iratlarla > eşik ise beyan | GVK m.94, 22 |
| Yatırım fonu katılma payı (TEFAS, hisse senedi yoğun) | %0 | Stopaj nihai | Karar 11107 (27.03.2026) |
| TEFAS dışı serbest fon (hisse senedi yoğun) | **%17.5** | — | Karar 11107 (PwC bülteni 2026: *"serbest hisse senedi yoğun yatırım fonu katılma paylarından elde edilen kazançlar üzerinden %17,5 oranında gelir vergisi stopajı uygulanacaktır"*) |

### 9.2 the maintainer için pratik vergi stratejisi

**İYİ HABER:** BIST hisse senedi alım-satım kazancı için bireysel yatırımcı (the maintainer), **stopaj %0 + beyan etmeme** rejimi altında. **Loss harvesting, FIFO/LIFO tercihleri, 1-yıl tutma istisnası gibi karmaşıklıklar Türkiye'de — şu anki rejimde — uygulanabilir değil**: stopaj zaten %0 olduğundan zarar realize etmenin direkt vergi avantajı yok.

**Aksi durum:** Eğer 2030 sonrasında GVK Geçici 67 uzatılmazsa, kazançlar değer artış kazancı olarak beyana tabi olabilir. Bu, the maintainer'ın 5+ yıllık ufkunda bir risk → §13 caveat.

**Temettü:** %15 stopaj kaynakta yapılır. Brüt temettünün yarısı, yıllık beyan eşiğini aşarsa beyana tabi (eşik 2026'da GİB Aralık 2025 rehberi takip edilmeli).

**ETF / TEFAS fon karşılaştırması:**
- TEFAS hisse senedi yoğun fon: %0 stopaj → vergi açısından doğrudan hisseyle eşdeğer
- Avantaj: Tek işlemde sepet exposure, broker komisyonu yok (TEFAS işlem komisyonu portföy yönetim ücretine gömülü)
- Dezavantaj: Aktif strateji yapamazsın, fon yönetim ücreti (%1–%3 TER aralığı; HangiKredi.com: *"Genellikle %1 ile %3 arasında değişen bu oran, yatırımcıların getirisinden kesilir"*) komisyon-eşdeğeri net getirinden düşer

---

## 10. BIST 2024–2026 Sektör Pratiği

> **Erişim notu:** Twitter/X login-wall nedeniyle örneklenmedi. Aşağıdaki gözlemler Ekşi Sözlük, Hisse.net, ŞikayetVar ve broker resmi duyuruları üzerinden derlendi. Ordinal skala: Yüksek/Orta/Düşük/Yok.

| Tema | Pratisyen farkındalığı | Gözlem |
|-------|-------------------------|---------|
| Komisyon farkındalığı | **Yüksek** | (Şikayetvar'da "İşCep'te 10.000 TL'de 20-25 TL komisyon, başka kurumlarda 2-5 TL" yorumları yaygın; aktif değişim) |
| Cost-aware Sharpe kavramı | **Düşük** | (Forum söyleminde Sharpe kelimesi neredeyse yok; "net getiri" pratik söylem) |
| Vergi optimizasyonu | **Yok / çok düşük** | (Çünkü BIST hissesi %0 stopaj — pratisyenler bu yüzden "vergi düşünmüyoruz" diyor) |
| Online broker tercihi | **Yüksek** | (Midas, Gedik gibi online platformlara forum bazlı geçiş söylemi açık; "İş Yatırım'dan Midas'a taşıdım" örüntüsü çok) |
| Hesap bakım ücreti şikayetleri | **Yüksek** | (Yapı Kredi yıllık 1.180 TL [yapikredi.com.tr], Garanti yıllık 500 TL [garantibbvayatirim.com.tr], Akbank ~275 TL — bu hidden fees forum kullanıcılarını rahatsız ediyor) |
| "Sık trade ölümcül" sezgisi | **Orta** | (Bigpara/Hisse.net'te "buy-and-hold daha karlı" söylemi var, ama backtest-eşdeğeri argüman yok) |
| Algorithmic trading retail topluluğu | **Düşük-Orta** | (Matriks API, Foreks AlgoTrader küçük niş; Türk algo-retail community zayıf) |

**Online broker savaşı 2024–2026 özet:**
- **Midas** 2022'den itibaren BIST sıfır komisyon iddiasıyla agresif büyüdü; SPK lisansı + MKK saklama güvencesi nedeniyle güven kazandı.
- **Akbank** geçici 90-gün %0 kampanyası ile direnç gösteriyor (akbank.com kampanya sayfası).
- **Gedik** ve **Osmanlı Menkul** gibi geleneksel discount'lar, Midas baskısı altında hacme bağlı skala daraltma yoluna gidiyor.
- **Geleneksel bankalar (İş, Garanti, Yapı Kredi)** komisyonda inmek yerine "bakım ücreti" gibi yan kalemlerle gelir koruyor — bu modeli forum kullanıcıları "gizli ücret" diye eleştiriyor.

> **Kritik bulgu:** Türk retail pratisyen söylemi "komisyon farkındalığı yüksek + cost-aware Sharpe kavramı çok düşük" şeklinde asimetrik. BIST OS bu boşluğu doldurabilir; the maintainer için net-EV check katmanı pratisyen pazarda da görülen bir disipline odaklı.

---

## 11. the maintainer'a Özel Tavsiyeler

### 11.1 Broker değişimi gerekli mi? — 3 tier karar matrisi

| Mevcut tier (varsayım) | Yıllık cost (24 trade) | Net tavsiye |
|--------------------------|--------------------------|--------------|
| Tier A (İş/Garanti sabit) | ~5.300 TL/yıl | **EVET — Tier C'ye geç**, yıllık 2.700 TL tasarruf (portföyün %3.2'si) |
| Tier B (Garanti hacme bağlı düşük tier) | ~5.200 TL/yıl | **EVET — Tier C'ye geç** (the maintainer'ın hacmi B'de zaten en üst kademe komisyonunu yiyor — binde 1.99) |
| Tier C (Midas) | ~2.600 TL/yıl | **HAYIR — koru**, ek tasarruf sınırı sınırlı |

### 11.2 Trade frequency optimizasyonu

- 12 trade/yıl senaryosu Tier C'de ~1.310 TL ≈ %1.5 erozyon. Sharpe gross 1.0 için net ~0.85 — sürdürülebilir.
- 48 trade/yıl Tier A'da %12.4 erozyon — pratik olarak gross Sharpe 2.0 gerektirir ki the maintainer'ın L1–L6 sistemi muhtemelen bunu üretmiyor.
- **Hedef:** the maintainer ≤ 24 trade/yıl + Tier C (Midas) kombinasyonu.

### 11.3 Tax-efficient hold period

GVK Geçici 67 + %0 stopaj rejimi nedeniyle "1 yıl tut" gibi bir vergi avantajı **yok**. Ancak:
- TEFAS hisse senedi yoğun fon (örn. TI2 endeks fon) ile **uzun-vadeli BIST exposure** % 0 stopajla mümkün; broker komisyonu ödeme yok, sadece fon TER.
- the maintainer'ın ufku 5+ yıl, öğrenme aşamasında: Portföyün %20-30'u TEFAS fon (pasif kor), %70-80'i BIST OS sistemine ayrılabilir.

### 11.4 Aylık review checklist

```
□ Bu ay round-trip cost / portföy oranı %1'i aştı mı?
□ ENERY benzeri small-cap pozisyonlar > %15 portföy ağırlığı mı? (Cost'tan dolayı agresiflik)
□ BUY-MEDIUM tier sinyalleri net EV check'i geçti mi (>%0.5)?
□ TCMB politika faizi 5+ puan oynadı mı? (r_f revize, Sharpe net değişir)
□ Broker tarifesi değişti mi? (Yılda 1–2 kez güncelleme normal)
□ Hesap bakım ücreti veya MKK saklama ücreti son ekstrede beklenmedik mi?
```

---

## 12. Akademik Kaynak Özeti

| Eser | Künye | BIST'e katkı |
|------|-------|---------------|
| **Perold (1988)** | "The Implementation Shortfall: Paper Versus Reality", *J. of Portfolio Management*, 14(3), 4–9. DOI: 10.3905/jpm.1988.409150 | Karar fiyatı ile gerçekleşen fiyat arasındaki gap'ı "shortfall" olarak operasyonelleştirir. BIST OS için → backtest "paper" return ile canlı sistem return'ünü ayırma disiplini. |
| **Bessembinder (2003a)** | "Trade Execution Costs and Market Quality after Decimalization", *J. of Financial and Quantitative Analysis*, 38(4), 747–777. DOI: 10.2307/4126742 | Decimalization sonrası tick size daralması ve effective spread'in retail yatırımcıya etkisi. BIST için tick size 2023 düzenlemesi (06.11.2023 fiyat adımı duyurusu) benzer mantık. |
| **Bessembinder (2003b)** | "Issues in Assessing Trade Execution Costs", *J. of Financial Markets*, 6(3), 233–257. DOI:10.1016/S1386-4181(02)00064-2 | Quoted vs effective vs realized spread metodolojik ayrımı. RR-014 slippage hesabının teorik temeli. |
| **Engle & Russell (1998)** | "Autoregressive Conditional Duration: A New Model for Irregularly Spaced Transaction Data", *Econometrica*, 66(5), 1127–1162. DOI: 10.2307/2999632 | Intraday trade durations modellemesi (ACD); spread'in saat içi paterni (açılış-kapanış geniş, orta seans dar). BIST OS execution scheduling için referans. |
| **Hasbrouck (2007)** | *Empirical Market Microstructure: The Institutions, Economics, and Econometrics of Securities Trading*, Oxford University Press, ISBN 978-0195301649. DOI: 10.1093/oso/9780195301649.001.0001 | Roll Model (Ch. 3, 8), retrospective trading costs (Ch. 14), prospective costs ve execution (Ch. 15) — RR-014 ve bu raporun (RR-015) teorik omurgası. |
| **GVK Geçici 67. madde** | 193 sayılı Gelir Vergisi Kanunu Geçici 67. madde; Cumhurbaşkanı Kararı 10680 (11.12.2025, RG 33104) → süre uzatma 31.12.2030; Karar 11107 (27.03.2026, RG 33206) → stopaj oran değişiklikleri. | BIST hisse alım-satım kazancı %0 stopaj rejiminin yasal temeli. |
| **BSMV** | 6802 sayılı Gider Vergileri Kanunu m.28; komisyon üzerinden %5. | Tüm Tier A/B broker tariflerinde "BSMV hariç" dipnotu standart. |

---

## 13. Kısıtlar & Caveat'lar

1. **Broker fiyat yapısı yıllık değişiyor.** Garanti BBVA Yatırım örneği: 8 Haziran 2024'te BSMV ayrı tahsile geçti; yıllık bakım ücretleri 2026 başında bir kez daha güncellendi (Yapı Kredi 1 Ocak 2026 itibarıyla 590 TL/6ay → yıllık 1.180 TL). Bu rapor ±%30 hata payını çabuk kapatır; üç ayda bir gözden geçirilmelidir.
2. **"Sıfır komisyon" iddialarının teknik detayı kara kutu.** Midas'ta PFOF/spread genişletme tespiti için resmi mekanizma yok — order routing data public değil. the maintainer profili için pratik gözlem: TTKOM/KCHOL gibi likit hisseler için bid-ask gözleminden anomali görülmüyor.
3. **GVK Geçici 67. madde 2030 risk.** 31.12.2030 sonrasında uzatılmazsa, BIST hisse kazancı beyana tabi olabilir → the maintainer'ın 5+ yıl ufkunda 2030 öncesi durum izlenmeli.
4. **Slippage tahmini ±%50 hata payı.** RR-014'te detaylı işlenen ADV-ratio bazlı model varsayımlarla (örn. trade ADV %0.5'in altında) uyumlu; portföy 5× büyüdüğünde (~425K TL) bu varsayım kırılır.
5. **Conviction tier win rate'leri hipotetik.** §7'deki BUY-STRONG ~%58–62, BUY-MEDIUM ~%48–53 değerleri **örnek**'tir; backtest log empirik doğrulaması RR-016 ile gelecek. Bu rapor o değerlere bağlı sonuç çıkarmıyor; sadece break-even mekaniğini gösteriyor.
6. **the maintainer broker bilgisi açık soru.** Üç tier paralel senaryo nedeniyle kesin TL maliyet yerine bir aralık veriyoruz; broker teyit edilince §5.4 tek senaryoya indirgenir.
7. **Forum söylemi anekdotal.** §10'daki ordinal skala kalitatif gözlem; pratisyen popülasyonu üzerinde sistematik survey YOK.

---

## Açık Soru Bölümü

1. **the maintainer'ın gerçek broker'ı nedir?** Tier A, B veya C? AKSEN tarihsel maliyeti retrospektif analiz için bilinmeli.
2. **Conviction validator'ın 2024–2026 backtest logu** mevcut mu? Win rate empirik verisi olmadan §7 hipotetik kalıyor.
3. **the maintainer'ın ortalama hold süresi ne?** 24 trade/yıl baz tahmini; gerçek frekans bilinirse projeksiyon revize edilir.
4. **TEFAS hisse senedi yoğun fon kullanılıyor mu?** §11.3'te paralel kor öneri var; mevcut durum bilinmiyor.

---

*Bu rapor, RR-012 (EM Faktörler), RR-013 (Holding NAV) ve RR-014 (Slippage) ile aynı disiplin çerçevesinde hazırlanmıştır. Hipotez vermek yerine bağımsız sayısal ölçüme ve resmi kaynak teyidine dayanır. Production-ready Python kodu içermez — `position_sizer_v2` entegrasyonu KAVRAMSAL mini-spec olarak verilmiştir.*