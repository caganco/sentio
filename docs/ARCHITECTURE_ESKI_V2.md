# BIST OS — ARCHITECTURE v2.0 (Trend/Swing-Öncelikli Quantamental)

**Versiyon:** 2.0 (Paradigma düzeltmesi — Katman A motoru: cross-sectional faktör → trend/swing)
**Tarih:** 30 Mayıs 2026 — Session #8+
**Status:** Hedef mimari — trend-motor TEST sonrası inşa (ÖNCE edge kanıtla, SONRA kur)
**Kaynak (v2.0):** DEC-043 + Faz 0 IC harness (D-177/178/183/184 — cross-sectional zayıf) + Critic CB-017 + RR-UST (taksonomi) + RR-038 (modern BIST) + ARCH_V2_PARADIGM_DECISION.md
**Kaynak (v1.2 — korunan iskelet):** CB-016 + 4 değerlendirme + NRR-001/002/003 + PIVOT_ARCHITECTURE_AUDIT + D-176

> Bu dosya, BIST OS'un mimarisinin **tek kaynak gerçeğidir**. İKİ EVRİM: (1) 5-katman composite → tarama-öncelikli quantamental (v1.x); (2) cross-sectional faktör motoru → trend/swing (v2.0). Geçmiş mimariler SİLİNMEZ — OS_STATE + Faz 0 sonuçları (docs/factor_ic/) tarihsel kanıt olarak korunur (pivot felsefesi: evrim, başarısızlık değil).

---

## 0. NEDEN PİVOT — İKİ EVRİM

### EVRİM 1 (v1.x) — Composite → Tarama
Linear-additive composite (`w1·L1+...+w5·L5 → conviction → sinyal`) iki yapısal kusur taşıyordu: **(1) ortalamaya regresyon** (ağırlıklı toplam güçlü sinyali dilüe ediyor) ve **(2) ölü ağırlık cash drag** (L4/L5=50 stub, composite'in %22.68'i, eşiği yapay yükseltiyor). Backtest kanıtı: reel -42% sistem vs reel +1.09% benchmark.

**D-176 teşhisi (ampirik):** "win rate korunurken return çöktü" = **konuşlanma (cash drag)**. Sistem trade açtığında **doğru seçiyor** (expectancy +5.3%/trade, win 58.7%, PF 2.19), ama **sermayenin %87'si atıl**. Çözüm: composite'i terk et → **tarama → yargı → icra** pipeline'ı.

### EVRİM 2 (v2.0) — Cross-Sectional Faktör → Trend/Swing
v1.x'in Katman A motoru (eşit-ağırlık cross-sectional faktör rank composite: RS+low-vol+value), Faz 0 IC harness'te (D-177→184) **BIST'te ampirik olarak zayıf çıktı.** Üç bağımsız kanıt yakınsadı:
- **Faz 0 ölçümü:** rs6/rs12/value honest_t<2 (geçmedi); sadece lowvol60 marjinal
- **Critic CB-017 + D-184:** lowvol60 ≈ Katman D rejim-gölgesi (D-koşullu IC %90.5, T1 FAIL) — bağımsız alpha yok
- **RR-UST + RR-038 (literatür):** Cross-sectional faktör = **kurumsal teknoloji** (büyük-N 50+, long-short, breadth gerektirir; Grinold IR≈IC×√breadth). Küçük-sermaye-bireysel-sadece-long-BIST için yapısal uygunsuz. **Modern BIST reversal-baskın** (Ünal 2021/2024, %1 anlamlı — kazananlar sonra ortalama-altı).

**Çözüm:** Katman A motorunu değiştir — cross-sectional faktör sıralama → **trend-başı yakalama + parabolik-kaçınma + kalite-süzgeç + yabancı-rejim-teyidi.** Dört-katman iskeleti + tüm disiplinler KORUNUR. (Yön belgesi: ARCH_V2_PARADIGM_DECISION.md)

**Kritik açık nokta:** Yeni motor (zaman-serisi trend) BIST için akademik TEST EDİLMEMİŞ (RR-038 boşluğu). ÖNCE kendi backtest'imizle test, SONRA inşa (Faz 0 dersi: paradigma varsayma).

---

## 1. TASARIM FELSEFESİ

**Sorumlulukların ayrılması (dört kaynak da onayladı):**

| Karar tipi | Sahip | Gerekçe |
|------------|-------|---------|
| Sert kısıtlar (risk, sizing, likidite, stop) | **Deterministik (KANUN)** | Stokastik sisteme asla bırakılmaz; edge disiplinden gelir |
| Tarama, sıralama, faktör, rejim tespiti | **Kantitatif (matematik)** | İstatistik, el-kuralı değil |
| Yapısal-olmayan veri sentezi (KAP/haber → hipotez) | **LLM (asistan)** | Kodlanamayan sentez; ama karar değil |
| Nihai pozisyon kararı | **Kullanıcı (Cagan)** | LLM contamination'a yenilir; insan yargısı + deterministik kapı |

**Çekirdek ilke:** LLM çıktısı hiçbir zaman doğrudan tetiğe bağlı bir aktüatör değildir. Ya bir insana ya da deterministik bir kapıya **öneri** olarak girer. LLM tek başına para kaybettirebilecek konumda olamaz.

**Hedef:** "Piyasayı yenmek" DEĞİL. Reel getiri > **max(TÜFE, para piyasası fonu)**. Edge'in %80'i hata yapmamaktan gelir.

---

## 2. DÖRT KATMAN

```
┌─────────────────────────────────────────────────────────┐
│ KATMAN D — MAKRO ŞALTER (portföy beta exposure)          │
│   Girdi: XU100 vs 200-MA + breadth + yabancı akış + CDS   │
│   Çıktı: equity exposure ON / tighten / cash              │
│   ⚠️ Hisse filtresi DEĞİL — portföy seviyesi risk aç/kapa  │
└────────────────────────┬────────────────────────────────┘
                         ↓ (rejim ON ise tara)
┌─────────────────────────────────────────────────────────┐
│ KATMAN A — TARAMA (deterministik, v2.0 trend/swing motoru)│
│   ★ PROJENİN ASIL EDGE'İ ★                                │
│                                                           │
│   1. SERT KAPILAR (ardışık AND, sıra-duyarsız):           │
│      ADV tabanı → rejim → tradeable-next-open → tazelik    │
│   2. KALİTE-SÜZGEÇ (getiri motoru DEĞİL, liste daraltıcı): │
│      iyi finansal + makul değerleme + aşağıda-kalmış       │
│   3. TREND-BAŞI YAKALAMA (ANA MOTOR):                      │
│      destek-direnç flip + konsolidasyon-retest +          │
│      zaman-serisi trend (kendi trendinde mi)              │
│      ⚠️ "EN ÇOK YÜKSELENİ AL" YASAK (BIST reversal)        │
│   4. PARABOLİK-KAÇINMA: aşırı-uzamış/hype hisse ELE        │
│   5. REJİM TEYİDİ (Katman D ile): yabancı/kurumsal akış    │
│      ENDEKS-seviye (tek-hisse sinyal DEĞİL)               │
│   → CONFLUENCE: süzgeç+teknik+rejim hizalı = yüksek konv.  │
│   → ÇIKTI: eşik-kapılı aday liste; zayıf rejimde az        │
└────────────────────────┬────────────────────────────────┘
                         ↓ (kısa liste: 5-10 hisse)
┌─────────────────────────────────────────────────────────┐
│ KATMAN B — LLM ASİSTAN (bağlayıcı değil)                  │
│   Girdi: kısa liste + ham veri + matematiksel sonuçlar     │
│   Çıktı: KAP özeti + bağlam + ayı senaryosu + hipotez      │
│   ⚠️ ASLA sizing/tetik. Çıktı = çürütülecek hipotez.       │
│   ⚠️ Grounding zorunlu — LLM sayı üretmez, verilen sayı     │
│      üzerinde akıl yürütür.                                │
└────────────────────────┬────────────────────────────────┘
                         ↓ (dosya: yorumlu kısa liste)
┌─────────────────────────────────────────────────────────┐
│ KULLANICI (Cagan) — NİHAİ KARAR                           │
│   LLM dosyasını okur, kendi kararını verir.               │
└────────────────────────┬────────────────────────────────┘
                         ↓ ("al" kararı)
┌─────────────────────────────────────────────────────────┐
│ KATMAN C — İCRA (deterministik KANUN)                     │
│   Kelly + ADV cap + stop + net EV                         │
│   Maliyet: komisyon + %5 BSMV + spread                    │
│   ⚠️ Yargı yok, disiplin var. Tartışılmaz.                 │
└─────────────────────────────────────────────────────────┘
```

---

## 3. KATMAN A — TARAMA (v2.0 trend/swing motoru)

**Projenin asıl değeri burada.** "100 hisseden Cagan'ın masasına hangi dosyalar gelir" sorusu. Cagan'ın tek başına yapamadığı iş (toplu finansal tarama) + doğal olarak iyi yaptığı iş (teknik destek-direnç) birleşir.

**v2.0 paradigma:** Cross-sectional faktör sıralama DEĞİL (Faz 0'da yanlışlandı). Bunun yerine **kalite-süzgeç → trend-başı zamanlama → parabolik-kaçınma → rejim teyidi** (CAN SLIM mantığı: fundamental tarama + teknik kurulum). Detaylı gerekçe: ARCH_V2_PARADIGM_DECISION.md.

### 3.1 Funnel (v2.0)

```
SERT KAPILAR (ardışık AND — geçemeyenler elenir):
  1. ADV tabanı     → TL ortalama günlük hacim eşiği (likit BIST30/50/100)
  2. Rejim          → Katman D ON mu? (XU100>200-MA + breadth + yabancı akış)
  3. Tradeable      → tavan-kilitli DEĞİL (next-open girilebilir)
  4. Veri tazeliği  → point-in-time, lag-respecting takas+KAP+MaliTablo
        ↓ (hayatta kalanlar)
KALİTE-SÜZGEÇ (getiri motoru DEĞİL — izleme listesi daraltıcı):
  - İyi finansal: MaliTablo'dan kalite (kârlılık, borç, nakit) — Cagan'ın
    zayıf olduğu finansal analizi sistem otomatikler
  - Makul değerleme + "aşağıda kalmış" (henüz uçmamış)
  - lowvol60 burada SÜZGEÇ bileşeni olabilir (ana sinyal değil →
    CB-017 rejim-gölgesi sorunu süzgeçte sorun değil)
  ⚠️ Bu katman SIRALAMA/getiri üretmez — sadece "hangi hisselere bak"
        ↓ (kaliteli + aşağıda kalmış aday havuzu)
TREND-BAŞI YAKALAMA (ANA MOTOR — getiri buradan):
  - Zaman-serisi trend: hisse kendi sağlıklı yükseliş yapısında mı
    (MA üstü, yükselen dip-zirve)
  - Düşük-riskli giriş kurulumu: geçmiş direnç → destek dönüşümü
    (support/resistance flip), konsolidasyon-retest (Cagan tarzı)
  - YENİ trend başlangıcı / tabandan (tepeden DEĞİL)
  ⚠️ KESİTSEL "EN ÇOK YÜKSELENİ AL" YASAK (BIST reversal — §3.4)
        ↓
PARABOLİK-KAÇINMA FİLTRESİ (reversal riski):
  - Aşırı-uzamış / kısa sürede aşırı sapmış / hype hisseleri ELE
  - (modern BIST: hızlı kazananlar sonradan ortalama-altı — Ünal 2021/24)
        ↓
REJİM TEYİDİ (Katman D ile birlikte — tek-hisse DEĞİL):
  - Yabancı + yerli kurumsal net akış ENDEKS/rejim seviyesinde
  - Yabancı alım rejimi → long-bias; satış rejimi → temkin/nakit
  ⚠️ Yabancı akış TEK-HİSSE al-sinyali DEĞİL (RR-038: tekil öngörü zayıf,
     yabancı payı %16 dibe, yerli bireysel %37 baskın)
        ↓
ÇIKTI: confluence-skorlu aday liste; zayıf rejimde daha az/yok
```

### 3.2 CONFLUENCE — sinyal hizalanması (Cagan içgüdüsü)

İki+ bağımsız sinyal HİZALI ise konviksiyon yüksek:
```
Kalite-süzgeç GEÇTİ + Teknik kurulum OLGUN (flip/retest, parabolik DEĞİL)
  + Rejim TEYİT (yabancı/kurumsal + XU100 trend pozitif)
  → yüksek konviksiyon → Kelly-ölçekli pozisyon (Katman C)
Biri var diğeri yoksa → düşük konviksiyon → küçük/yok
```
Bu, Cagan'ın "iki yönden tümdengelim" içgüdüsünün sistemsel karşılığı (teknik beğendiğine yabancı akışı da varsa öncelik / yabancı akışı olana teknik bakış — kesişimi ara). Signal confirmation; konviksiyon→pozisyon ilişkisi = Kelly (Katman C).

### 3.3 Neden RS değil zaman-serisi trend, ve enflasyon-dayanıklılık

v1.x'te cross-sectional RS-vs-XU100 vardı (hisseleri birbirine göre sırala). v2.0'da **zaman-serisi trend** (her hisse kendi geçmişine göre) — çünkü modern BIST'te cross-sectional momentum reversal'a dönüyor (§3.4), ama zaman-serisi trend farklı bir şey (RR-038: BIST'te test edilmemiş, kendi backtest'imizle ölçülecek). Enflasyon-dayanıklılık için: getiriler reel/USD bazlı veya endeks-göreli değerlendirilir (yüksek enflasyon ortak drift'i fark-alınır). D-169 TÜFE deflate'in mimari karşılığı korunur.

### 3.4 BIST reversal gerçeği (RR-038 — ÜÇ KEZ vurgulanan)

Modern BIST'te (2020-2024 veri, Ünal 2021/2024 %1 anlamlı) **kesitsel kazananlar sonradan ortalama-altı** kalıyor (reversal/aşırı-tepki baskın). Bildik-Gülay (2007) geçerliliğini koruyor. Kısa-vade (1-4 hafta) reversal kanıtlı (Çelik-Ülkü 2017). **Sonuç:** "en çok yükseleni al" YASAK; "trend başını yakala, parabolikten kaç" doğru yön. Çok-kısa-vade YASAK (reversal + maliyet).

### 3.5 Mevcut primitive'ler (audit §2.2.1 — green-field DEĞİL)

| İhtiyaç | Mevcut araç | Dosya | v2.0 statü |
|---------|-------------|-------|-----------|
| Cross-sectional rank | `compute_universe_percentiles` | `data/short_interest_normalizer.py` | süzgeçte kullanılabilir |
| Rolling percentile | `SmartMoneyNormalizer._rolling_percentile` | `signals/layers/smart_money_layer.py` | rejim/akış için |
| ADV boolean filtre | `is_adv_eligible` | `smart_money_layer.py` | sert kapı (korunur) |
| Trend ham faktör | `technical.detail[adx, momentum_score, ...]` | `signals/layers/technical_layer.py:196-204` | ⭐ ANA MOTOR primitive |
| Snapshot/IC/look-ahead guard | Faz 0 harness (D-177→184) | `docs/factor_ic/`, ilgili src | ⭐ trend-test'te reusable |

**Kritik:** Trend-motor inşası, Faz 0'ın look-ahead/snapshot/IC altyapısını yeniden kullanır (cross-sectional faktör mantığı pasif kalır, silinmez — strangler). Codebase envanteri (Builder) hangi parçaların reusable olduğunu netleştirecek.

---

## 4. KATMAN B — LLM ASİSTAN (detay)

### 4.1 Rol

LLM = çok iyi junior analist + geniş bilgi tabanı. **20 yıllık BIST CEO'su DEĞİL.** Genel finansal muhakemede güçlü, BIST'e özel güncel kurumsal hafızası zayıf.

**Yapar:** KAP/haber → yapısal özet; bağlam sentezi; ayı senaryosu (red-team); "X+Y → N olabilir" hipotezi.
**ASLA yapmaz:** nihai al/sat, pozisyon boyutu, hedef fiyat, sayısal temel veri üretimi.

### 4.2 Neden karar verici değil (4 kaynak)

- **Yapısal (Mimar):** LLM konsensüs makinesi — ortalama üretir. Piyasa konsensüsün yanıldığı yerde öder. LLM'in gücü (bilineni sentezlemek) ile edge (yanlış fiyatlananı görmek) **dik**.
- **Ampirik (Research):** StockBench/LiveTradeBench — LLM ajanları buy-and-hold'u yenemiyor, düşüşte hepsi geri kalıyor. Statik benchmark'ta parlayan canlıda daha kötü.
- **Otorite:** Greg Jensen (Bridgewater AIA mimarı): naif LLM stock-picking "hopeless path". AIA bile %11.9 < endeks %16.97 < insan-fonu ~%33.
- **Türkçe NLP:** Dedicated FinBERT yok; Tilburg 2025 tezi BIST sentiment'i terk etti. → güçlü genel model + retrieval, özel Türkçe model değil.

### 4.3 Disiplin kuralları

1. **Grounding zorunlu:** LLM sayı üretmez — borç/hedef/çarpan verilir, üzerinde akıl yürütür.
2. **Hipotez, sonuç değil:** her çıktı çürütülecek; ayı senaryosu/red-team zorunlu.
3. **Tetiğe bağlı değil:** çıktı insana veya deterministik kapıya öneri.
4. **Baseline disiplini:** deterministik sistem tek başına aynı işi yapıyorsa, LLM katmanı öldürülür (ablation karar verir, ego değil).

---

## 5. KATMAN C — İCRA (detay)

**Deterministik KANUN.** Yargı yok. KOVA 1'de zaten mevcut (audit Q3 — conviction'ı parametre alır, engine import etmez).

| Bileşen | Durum | Dosya |
|---------|-------|-------|
| Kelly (quarter-Kelly) | ✅ | `risk/kelly.py` |
| ADV cap (min Kelly, %5×ADV_20d) | ✅ D-145 | `risk/position_sizer_v2.py` |
| Net EV (gross - round_trip_cost) | ✅ D-146 | `risk/position_sizer_v2.py` |
| Stop (vol-aware, floor -%20) | ✅ | `risk/stop_calculator.py` |
| Staged exit (TP1/2/3) | ✅ | `order_engine/staged_exit_manager.py` |
| BIST trend scalar (sizing) | ✅ D-163 | `signals/layers/bist_trend_scalar.py` |

**Maliyet modeli (NRR-001):** komisyon (~%0.1-0.3/side) + **%5 BSMV** (komisyon üzerine) + spread. Round-trip ~%1.5 yüksek-turnover stratejiyi eritir → düşük-turnover sinyaller (low-vol, 6-12ay RS), uzun rebalance.

**Değişecek:** `kelly_win_prob(composite)` → composite yerine EV/rank tabanlı win-prob (Katman C'de yeniden türetilecek).

**Çıkış profili — D-176 ile KARARA BAĞLANDI (ampirik):** Bağımsız kritik "sabit +20% profit_target upside'ı kesiyor, konveks çıkış (runner + trailing) ekle" önerdi. D-176 runner counterfactual'ı (downside sabit, upside açık — en iyi senaryo) bunu **veriyle reddetti:** trailing 8%/10%'da net negatif (-6242/-4249 TL), sadece 15%'te marjinal pozitif (+121 TL). +20% cap önemli sağ-kuyruk bırakmıyor; trailing whipsaw'a yeniliyor. **Karar: mevcut profit_target/stop çıkış yapısı KORUNUR. Runner/trailing eklenmez.** (Çıkış sorun değil — sorun konuşlanmaydı, §0.) Skewness +0.10 (hafif pozitif) bunu doğruluyor: negatif çarpıklık/çıkış problemi YOK.

**Konuşlanma — D-176 ile yeni Katman C gereksinimi:** avg_exposure %13 (sermayenin %87'si atıl) cash drag'in kaynağıydı. Katman C, Katman A'nın ürettiği sinyalleri sermayeyi konuşlandıracak şekilde boyutlandırmalı (atıl nakit minimize). DİKKAT: bu, BUY eşiğini körü körüne düşürmek DEĞİL (kalite düşürür); Katman A'nın yapısal "her zaman top-5/10 seçili" mantığıyla doğal çözülür.

---

## 6. KATMAN D — MAKRO ŞALTER (detay)

**Portföy beta exposure — hisse filtresi DEĞİL.** Research'ün en güçlü mimari önerisi: makro/akış hisse seviyesinde değil, portföy seviyesinde risk aç/kapa.

```
Girdi:
  - XU100 vs 200-MA (primary rejim switch)
  - breadth (% constituents > 50-MA)
  - trend-strength (50- vs 200-MA slope, ADX)
  - yabancı akış yönü (Ülkü-İkizlerli: agregat öngörür)
  - CDS rejimi
Çıktı:
  - equity exposure: full / tighten (N azalt, eşik yükselt) / cash
```

**Mevcut çekirdek (audit):** `macro_regime_gate.py` (`classify_regime`) zaten ayrı ve temiz; `backtest/engine.py:344-361` `_is_entry_gated_by_macro` (VIX>35 / USDTRY+%3) zaten Katman-D tipi şalter. Bu genişletilecek.

**Not:** HMM rejim tespiti (RR-017) Katman D'ye taşınabilir — ama "ağırlık override" amacı (AG-001) iptal (composite öldü).

---

## 7. DOĞRULAMA PROTOKOLÜ

### 7.1 Çekirdek (tarama + icra) — backtest EDİLEBİLİR

Deterministik olduğu için contamination yok.

**⚠️ v2.0 ÖLÇÜM PARADİGMASI DEĞİŞTİ:** v1.x cross-sectional rank-IC ile ölçüyordu (binlerce hisse-ay). v2.0 trend/swing motoru **olay-bazlı** (her trend-başı sinyali bir işlem) → birincil kanıt **per-trade expectancy + event-study**, cross-sectional IC değil. Ama az sayıda örtüşen trade Sharpe'ı anlamsız kılar (NRR-003) → istatistiksel güç için yeterli sinyal sayısı (100+ trade) ve maliyet-sonrası ölçüm şart.

#### ÖN-KAYIT ZORUNLU (Stage 0 — backtest'ten ÖNCE)
Backtest koşmadan ÖNCE yazılır, timestamp'lenir, dondurulur (dated git commit): gating + failure eşikleri, trend/kurulum tanımları (destek-direnç flip, konsolidasyon, parabolik eşiği), maliyet modeli, benchmark, **maksimum konfigürasyon N ≤ 3 (ideal N=1)**. MinBTL: az veriyle çok varyant = garantili overfitting (López de Prado). Önceden-kayıtlı tek tasarım.

#### v2.0 GATING KRİTERLERİ (trend-motor — hepsi sağlanmalı, AND)
```
1. PER-TRADE EXPECTANCY pozitif VE maliyet-sonrası anlamlı
   - Tüm trade'lerin (kazanan+kaybeden) ortalama net getirisi > 0
   - Round-trip maliyet (komisyon + BSMV + spread) düşülmüş
   - Cagan hedefi referans: süreye-oranlı, tuttuğu süre faizini yensin
   ⚠️ BİRİNCİL KANIT bu (event-study, tüm sinyaller)
   ⚠️ Survivorship-in-memory'ye karşı: TÜM sinyaller, seçilmiş değil

2. RANDOM-SELECTION BENCHMARK'ı geçer
   - Aynı dönem/sayıda RASTGELE hisse aynı süre tutulsa ne kazanırdı?
   - Sistem rastgeleden ANLAMLI iyi olmalı (yoksa edge yok, piyasa betası)
   ⚠️ En kritik test — "sinyal mi piyasa mı" ayrımı

3. REJİM-AYRIŞTIRILMIŞ tutarlılık
   - Sinyaller D=ON ve D=OFF'ta ayrı ölçülür
   - Sadece yükselen rejimde mi kazanıyor (lowvol60 dersi — rejim-gölgesi)?
   - Tek balon dönemine (2021-22) bağımlı mı?

4. Net-of-cost REEL getiri benchmark'ı geçer
   - benchmark = max(TÜFE, TLREF ~%40); fırsat-maliyeti dahil
   - per-trade getiri × fırsat sıklığı (nakit beklerken faiz kaybı)
   ⚠️ Gerçek rakip: risksiz mevduat ~%40 — çıta yüksek
```

#### FAILURE EŞİKLERİ (herhangi biri → "premise'i yeniden düşün")
```
- Per-trade expectancy ≤ 0 (maliyet sonrası)        → hard fail
- Random benchmark'ı geçemiyor                        → edge yok
- Sadece tek rejimde/balon döneminde kazanıyor        → rejim-bağımlı
- Net-of-cost reel getiri ≤ 0                         → mevduata kaybediyor
- Trend sinyalleri reversal'a yakalanıyor (parabolik) → filtre çalışmıyor
- Max drawdown > ~%25-35                              → risk kontrolü zayıf
```

**Absence of evidence ≠ evidence of absence (NRR-003):** Yetersiz trade'de "kanıt yokluğu." Expectancy ~0 + dar CI → kanıt yok → öldür. Pozitif ama anlamsız + geniş CI → belirsiz → sermaye verme, veri topla (deploy ETME).

#### CPCV / OOS mekaniği
Trend kurallarını farklı dönem-dilimlerinde test (purge: holding overlap; embargo: leak engelle). Çıktı: OOS expectancy dağılımı (tek nokta değil). 2019-2026 dönem-ayrıştırma.

#### D-176 BASELINE (referans)
Eski composite seçim mekanizması: expectancy +5.3%/trade, win %58.7, PF 2.19. v2.0 trend-motoru bu per-trade kalitesini en azından KORUMALI (tercihen artırmalı) VE daha fazla sinyal/konuşlanma sağlamalı (eski sorun: avg_exposure %13).

#### Geçer kriter
4 gating'in HEPSİ (AND) → trend edge'i kanıtlandı → LLM katmanına geç. Herhangi biri başarısız → premise yeniden düşün (patch'leyip yeniden koşma — ön-kayıt post-hoc rasyonalizasyonu engeller).

**Gerçekçi hedef:** Cagan içgüdüsü (~%10-15/birkaç hafta) ideal ama OOS'ta abartıdan kaçın. ~5500 USD'de birincil amaç beceri+süreç validasyonu. **Quarter-to-half Kelly ZORUNLU** (tam-Kelly aşırı agresif).

#### Trend BIST'te test-edilmemiş (RR-038 — ÜÇ KEZ tekrar)
Zaman-serisi trend-takibinin modern BIST kârlılığı akademik olarak TEST EDİLMEMİŞ. Kesitsel reversal kanıtlı (o farklı şey). **Trend kuralı backtest'te per-trade pozitif çıkmazsa veya reversal baskınsa → sistemi mean-reversion'a ayarla** (yine "fırsat" içgüdüsü, ters yön). En olası tek-nokta-başarısızlık bu.

### 7.2 LLM asistanı — backtest EDİLEMEZ (contamination)

```
- 6-12 ay paper-trade, post-training-cutoff veri (doğal OOS)
- Ablation: rules-only vs rules+LLM vs buy-and-hold
- Hepsi reel (TÜFE-ayarlı) bazda
- LLM katkı kanıtlamazsa → öldür
```

**ASLA LLM-in-the-loop backtest** (Lopez-Lira-Tang-Zhu 2025 memorization — yapısal duvar).

### 7.3 Look-ahead tuzakları (NRR-001 — BIST-spesifik)

- **Takas:** post-close yayım + T+2 → ≥1 gün lag (≥2 güvenli pre-T+1); MKK ücretsiz feed ~10 iş günü gecikme (backtest lag'i gerçek feed'e eşitle)
- **KAP:** period-end DEĞİL, gerçek disclosure tarihi (FY2025 non-consol 2 Mart, consol 11 Mart 2026)
- **Survivorship:** tarihsel constituent + halt/delist dahil (KOZAA/KOZAL/IPEKE/TRALT class)
- **T+1 geçişi:** end-2026 → takas lag ~1 gün (yeniden baseline)

---

## 8. CODEBASE STRATEJİSİ (PIVOT_ARCHITECTURE_AUDIT)

**IN-PLACE REFACTOR (strangler pattern). Sıfırdan repo DEĞİL.**

Gerekçe: KOVA 1 (data/risk/icra/backtest-infra) ölü çekirdekten temiz ayrılıyor; composite yüzeyi 3 production dosyada dar; harness composite'ten bağımsız; 0 döngüsel bağımlılık; cross-sectional primitive'ler mevcut.

### Strangler yol haritası

```
1. screening/ (Katman A) + execution/ (Katman C) modüllerini
   mevcut yapının YANINA kur; KOVA 1 faktör kaynaklarını tüket
2. backtest/engine.py sinyal aşamasını yönlendir
   (_compute_composite → Katman A, kelly_win_prob → Katman C)
   HARNESS'A DOKUNMA (~490 satır korunur)
3. signals/engine.py'yi aynı desenle yönlendir
   conviction üretimini Katman C'ye taşı (downstream imza koru)
4. Katman D'yi macro_regime_gate + _is_entry_gated_by_macro
   üzerinden portföy-beta şalterine genişlet
5. EN SON: calculator.py, conviction_validator.py,
   MASTER_WEIGHTS/SIGNAL_THRESHOLDS/CONVICTION_* buda; ölü test temizle
```

### Sessiz kırılma riski

`conviction_score`/`conviction_tier` default'lu (`models.py:53-54,64-65` → 0.0/"WATCH"). Composite koparılıp Katman C bağlanmazsa pozisyon **sessizce sıfırlanır**. Bu alanlara yeni anlam ZORUNLU.

---

## 9. NEYE DOKUNMA (refactor invariant'ları)

1. **KOVA 1 korunur** — veri/risk/icra/backtest-infra/kantitatif faktörler; regresyon riski
2. **Harness korunur** — backtest engine loop/portföy/exit/execution (~490 satır)
3. **Strangler sırası** — yeni yanına, eski EN SON (eski çalışırken). Faz 0 cross-sectional kodları + eski composite SİLİNMEZ (pasif kalır)
4. **(v2.0) Trend-motor parametreleri ön-kayıtlı + minimal** — aşırı parametre/optimize YASAK (overfitting; az veri). Birkaç makul değer dondur, post-hoc seçme yok
5. **(v2.0) Reel/endeks-göreli ölçüm** — yüksek enflasyon ortak drift'i fark-alınır (mutlak nominal getiri yanıltıcı)
6. **LLM tetiğe bağlanmaz** — Katman B çıktısı öneri, aktüatör değil
7. **ASLA LLM-in-the-loop backtest** — contamination
8. **Maliyet-sonrası ölçüm** — per-trade net (komisyon+BSMV+spread); BSMV komisyon-üzerinden (düşük)
9. **Survivorship** — halt/delist dahil (KOZAA/KOZAL/IPEKE); expectancy TÜM trade'ler (seçilmiş değil)
10. **Runner/trailing EKLENMEZ** — D-176 reddetti; mevcut profit_target/stop korunur
11. **(v2.0) Parabolik-kaçınma ZORUNLU** — "en çok yükseleni al" YASAK (BIST reversal); trend-başı yakala
12. **(v2.0) Yabancı akış = rejim teyidi** — tek-hisse al-sinyali DEĞİL (RR-038)
13. **Random-benchmark + rejim-ayrıştırma** — "sinyal mi piyasa/rejim mi" ayrımı zorunlu (lowvol60 dersi)

---

## 10. KARARA BAĞLANAN SORULAR (v1.x'te 5/5 kapandı; v2.0'da güncellendi)

> Bu sorular v1.x'te kapatıldı. v2.0 paradigma düzeltmesiyle S2/S4/S5/EK-1 trend/swing motoruna göre revize edildi (cross-sectional faktör varsayımları kaldırıldı). Architect/Builder bunları KARAR olarak alır.

**S1 — Benchmark serisi (NRR-002):** ✅ **max(TÜFE, TLREF)**
- TÜFE: `TP.FG.J0` (EVDS, zaten var — D-151); TLREF: `TP.BISTTLREF.KAPANIS` (EVDS, ücretsiz, günlük, 2019+, resmi gecelik risksiz faiz)
- **Para piyasası fonu kategori ortalaması hazır seri olarak YOK** (TEFAS/KYD); fon NAV (GTL/ALE) sadece robustluk kontrolü (TEFAS API, kırılgan)
- Risk-free = MMF/repo rate; Sharpe REEL veya USD bazlı (nominal TRY Sharpe ~%37-50 cash rate'le anlamsız)

**S2 — Validasyon eşiği (v2.0 — trend-motor):** ✅ **4 gating: per-trade expectancy / random-benchmark / rejim-ayrıştırma / net-of-cost reel (§7.1)**
- v1.x cross-sectional rank-IC idi; v2.0 trend/swing olay-bazlı → birincil kanıt **per-trade expectancy + event-study**
- Random-selection benchmark zorunlu ("sinyal mi piyasa betası mı")
- Rejim-ayrıştırma zorunlu (lowvol60 rejim-gölgesi dersi)
- N≤3 konfigürasyon; ön-kayıt zorunlu; Cagan hedefi (~%10-15/birkaç hafta) referans ama OOS abartıdan kaçın

**S3 — Evren (Cagan kararı):** ✅ **BIST100** (ADV kapısı likit alt-kümeye daraltır; survivorship: halt/delist dahil)

**S4 — Value faktörü (v2.0 — SÜZGEÇ rolü):** ✅ **USD-bazlı F/DD + EV/EBITDA — KALİTE SÜZGECİ (getiri motoru değil)**
- v2.0'da value/kalite = "iyi finansal + aşağıda kalmış" izleme-listesi daraltıcı (Cagan'ın zayıf olduğu finansal analizi otomatikler), getiri motoru DEĞİL
- Nominal F/K YASAK (TMS 29 net kârı çarpıtıyor); **UFRS/TMS 29 finansalları ZORUNLU**
- MaliTablo veri kaynağı (DEC-041) korunur; ⚠️ 2022-2024 yapısal kırılma (TMS 29)

**S5 — Rebalance/tarama frekansı (Orchestrator):** ✅ **Haftalık tarama; pozisyon birkaç hafta-ay (swing)** — fırsat bazlı, sürekli-pozisyon değil (Cagan: fırsat varsa gir, yoksa nakit). Çok-kısa-vade YASAK (reversal+maliyet).

**EK KARAR 1 — (v2.0) Trend validasyonu ZORUNLU:** Zaman-serisi trend BIST'te test edilmemiş (RR-038). Trend kuralı backtest'te per-trade pozitif çıkmazsa veya reversal baskınsa → mean-reversion'a ayarla. En olası tek-nokta-başarısızlık. ÖNCE test, SONRA inşa.

**EK KARAR 2 — Çıkış profili (D-176 ampirik):** ✅ **Mevcut profit_target/stop KORUNUR, runner/trailing EKLENMEZ.** Runner counterfactual veriyle reddetti (trailing 8/10%'da net negatif). Çıkış sorun değil.

**EK KARAR 3 — Birincil problem (D-176 ampirik):** ✅ **Cash drag (avg_exposure %13).** Seçim çalışıyor (+5.3%/trade), konuşlanma çalışmıyor. Katman A bu seçim kalitesini KORUYUP konuşlanmayı yükseltmeli. NAİF eşik-düşürme YASAK (kalite düşürür).

---

## 11. KAYNAK REFERANSLARI

**v2.0 (paradigma düzeltmesi):**
- **DEC-043 + ARCH_V2_PARADIGM_DECISION.md** — Katman A motoru değişimi (yön kararı)
- **Faz 0 IC harness (D-177→184)** — cross-sectional faktör BIST'te zayıf (ampirik yanlışlama)
- **Critic CB-017 + D-184** — lowvol60 rejim-gölgesi (T1 FAIL %90.5)
- **RR-UST** — sistem taksonomisi: trend(4/5)+olay(4/5); cross-sectional(2/5) bizim profil için değil
- **RR-038** — modern BIST reversal-baskın; yabancı endeks-öncü/tek-hisse-zayıf; trend test-edilmemiş; BSMV komisyon-üzerinden

**v1.x (korunan iskelet):**
- **CB-016** — pivot kararı (composite→tarama)
- **Critic/Mimar/RR-MOBILE-001/002** — teşhis, sorumluluk ayrımı, rejim, LLM
- **NRR-001/002/003** — tarama metodolojisi, benchmark(TLREF), validasyon iskeleti
- **PIVOT_ARCHITECTURE_AUDIT** — codebase denetimi, in-place strangler, KOVA
- **D-176** — cash drag teşhisi (+5.3%/trade seçim çalışıyor, konuşlanma değil)

---

## 12. FAZ HARİTASI (v2.0)

```
✅ Faz 0 (cross-sectional IC harness, D-177→184) — BİTTİ → YANLIŞLANDI
✅ ARCHITECTURE v2.0 paradigma kararı (DEC-043)
⏭️ Codebase envanteri (Builder hafif) — Faz 0 ne ekledi, reusable ayrımı
⏭️ Trend-motor TEST (yeni Stage 0) — destek-direnç-flip + trend-başı +
   parabolik-kaçınma, BIST 2019-2026, per-trade expectancy + maliyet
   → ÖN-KOŞUL: edge kanıtlanmadan inşa YOK (Faz 0 dersi)
⏸️ [test geçerse] Katman A inşası (strangler) + bu ARCHITECTURE'ın
   build-detayı
⏸️ Katman C (icra) bağlama — Kelly + stop + net EV
⏸️ Katman B (LLM asistan) — EN SON
⏸️ [opsiyonel] Olay-güdümlü katman (PEAD/endeks) — ana motor sonrası
```

**Eğer trend-test BAŞARISIZ:** mean-reversion'a ayarla (yine Cagan "fırsat" içgüdüsü, ters yön) VEYA premise yeniden (ama literatür yön verdi, daha az olası).

*ARCHITECTURE v1.2 — 29 Mayıs 2026 Session #8. 5 açık soru karara bağlandı (S1-S5) + D-176 ampirik teşhis işlendi (cash drag birincil problem, çıkış profili korunur). Bu doküman Architect SPEC_PIVOT_ARCHITECTURE_1'in temelidir — varsayım yok, kararlar veriyle desteklendi. Eski linear-additive mimari OS_STATE'de tarihsel referans olarak korunur.*
