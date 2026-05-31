# BIST OS — ARCHITECTURE (Tarama-Öncelikli Quantamental)

**Versiyon:** 1.2 (Pivot — S1-S5 kapalı + D-176 teşhis kanıtı işlendi)
**Tarih:** 29 Mayıs 2026 — Session #8
**Status:** Hedef mimari — Architect SPEC + strangler refactor ile inşa edilecek
**Kaynak:** CB-016 + 4 bağımsız değerlendirme (Critic-MOBILE + Mimar-MOBILE + RR-MOBILE-001 + RR-MOBILE-002) + NRR-001/002/003 (tarama+benchmark+validasyon) + PIVOT_ARCHITECTURE_AUDIT (codebase) + D-176 (trade dağılımı teşhisi — ampirik)

> Bu dosya, BIST OS'un yeni mimarisinin **tek kaynak gerçeğidir**. Tüm SPEC'ler, direktifler ve refactor kararları buna referans verir. Eski 5-katman linear-additive composite mimarisi terk edilmiştir (OS_STATE'de tarihsel referans olarak korunur).

---

## 0. NEDEN PİVOT — TEK CÜMLE

Linear-additive composite (`w1·L1+...+w5·L5 → conviction → sinyal`) iki yapısal kusur taşıyordu: **(1) ortalamaya regresyon** (ağırlıklı toplam güçlü sinyali dilüe ediyor) ve **(2) ölü ağırlık cash drag** (L4/L5=50 stub, composite'in %22.68'i, eşiği yapay yükseltiyor). Backtest kanıtı: reel -42% sistem vs reel +1.09% benchmark.

**D-176 teşhisi (ampirik — kanıtı keskinleştirdi):** "win rate korunurken return çöktü" sorunu, **konuşlanma (cash drag)** olarak doğrulandı — ortalama-alma dilüsyonu DEĞİL, çıkış problemi DE DEĞİL. Sistem trade açtığında **doğru seçiyor** (expectancy +5.3%/trade, win 58.7%, PF 2.19), ama **sermayenin %87'si atıl** (avg_exposure %13, günlerin %62'si tam nakit). Mükemmel per-trade ekonomisi, az sinyal yüzünden +7.41%'e sıkışıyor. Kök neden: yüksek conviction eşiği + ölü ağırlık dilüsyonu → az sinyal → atıl sermaye. Bu, tam olarak pivotun hedef aldığı şey: composite yapısı sermayeyi konuşlandıramıyor.

Çözüm: composite'i terk et. Yerine **tarama → yargı → icra** pipeline'ı.

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
│ KATMAN A — TARAMA (deterministik hibrit funnel)           │
│   ★ PROJENİN ASIL EDGE'İ ★                                │
│                                                           │
│   1. SERT KAPILAR (ardışık AND, sıra-duyarsız):           │
│      ADV tabanı → rejim → tradeable-next-open → tazelik    │
│   2. EŞİT-AĞIRLIKLI RANK COMPOSITE (optimize DEĞİL):       │
│      RS-vs-XU100 + low-vol + value                        │
│      (rank'leri ortala, z-score DEĞİL)                    │
│   3. TAKAS TIE-BREAKER (birincil değil)                   │
│   4. ÇIKTI: eşik-kapılı top-5/10 cap; zayıf rejimde az     │
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

## 3. KATMAN A — TARAMA (detay)

**Projenin asıl değeri burada.** "100 hisseden CEO'nun masasına hangi dosyalar gelir" sorusu. Kullanıcının tek başına yapamadığı iş.

### 3.1 Hibrit funnel (NRR-001)

Saf ardışık-filtre de saf ağırlıklı-skor da mükemmel değil. **Hibrit:**

```
SERT KAPILAR (ardışık AND — geçemeyenler elenir):
  1. ADV tabanı     → TL ortalama günlük hacim eşiği (20-60 gün)
  2. Rejim          → Katman D ON mu? (XU100>200-MA + breadth)
  3. Tradeable      → tavan-kilitli DEĞİL (next-open girilebilir)
  4. Veri tazeliği  → point-in-time, lag-respecting takas+KAP
        ↓ (hayatta kalanlar)
EŞİT-AĞIRLIKLI RANK COMPOSITE (optimize/z-score DEĞİL):
  - RS-vs-XU100 (6 & 12 ay, skip 1-ay) ⚠️ standalone valide et (BIST contrarian riski)
  - low-volatility rank
  - value rank: USD-bazlı F/DD + EV/EBITDA (NRR-002; nominal F/K YASAK — TMS 29)
  → rank'leri ortala, eşit ağırlık
  ⚠️ AÇIK KRİTİK UYARISI (test edilecek): rank-ortalama hâlâ bir sıkıştırma
     olabilir (tek-faktör-uç değerleri ortaya çeker); low-vol asimetrik
     hareketlerin zıttını seçebilir. Katman A inşa edilince per-faktör
     rank-IC + composite vs tek-faktör karşılaştırması ile test edilecek.
        ↓
TAKAS TIE-BREAKER:
  - yabancı-custody % düşmüyor → tie-breaker (birincil DEĞİL)
        ↓
ÇIKTI: eşik-kapılı, top-5 → top-10 cap; zayıf rejimde daha az
```

### 3.2 Neden eşit-ağırlık, optimize değil

DeMiguel-Garlappi-Uppal (2009): 7 veri setinde 14 optimize model 1/N'i out-of-sample yenemiyor. EM'de daha keskin: 96 uygulamada optimizasyon EM'de sadece 4/48 kazandı. **Ağırlık optimizasyonu = kaçınılabilir overfitting'in en büyük tek kaynağı.** Rank ortalaması (z-score değil) outlier-dayanıklı.

### 3.3 Neden RS-vs-XU100, mutlak nominal değil

**Bu en kritik BIST tasarım kararı.** Yüksek enflasyonda mutlak nominal getiri ortak bir enflasyon drift'i taşır (tüm hisselerde ~aynı), cross-sectional bilgi katmaz. Endekse göre ölçmek bu ortak bileşeni fark-alır → gerçek sinyal kalır. **RS doğal olarak enflasyon-dayanıklı — CPI deflate'e gerek yok** (endeks aynı drift'i taşır). D-169 TÜFE deflate'in mimari karşılığı.

### 3.4 Momentum uyarısı (NRR-001)

BIST'te momentum **kırılgan**: Fama-MacBeth (2009-2015) momentum/size YOK, book-to-market/temettü kalıcı; başka çalışma winner→negatif, loser→pozitif (reversal). **Momentum tek başına güvenilmez** — low-vol + value ko-çapa, momentum rejim-kapısıyla sınırlı.

### 3.5 Mevcut primitive'ler (audit §2.2.1 — green-field DEĞİL)

| İhtiyaç | Mevcut araç | Dosya |
|---------|-------------|-------|
| Cross-sectional rank | `compute_universe_percentiles` | `data/short_interest_normalizer.py` |
| Rolling percentile | `SmartMoneyNormalizer._rolling_percentile` | `signals/layers/smart_money_layer.py` |
| ADV boolean filtre | `is_adv_eligible` | `smart_money_layer.py` |
| Trend ham faktör | `technical.detail[adx, momentum_score, ...]` | `signals/layers/technical_layer.py:196-204` |
| Cross-sectional surprise ŞABLON | `score_xbrl_surprise` [-40,+40] | `analytics/kap_xbrl_scorer.py:85-132` |

**Kritik (§2.2.1):** Ardışık filtre seçildi → rolled-up 0-100 skoru KULLANMA (içinde gömülü ağırlık var); ham sub-faktörleri tüket.

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

Deterministik olduğu için contamination yok. **KRİTİK (NRR-003):** ~2 yıl veri + 1-2 ay holds = ~12-40 örtüşen trade → **Sharpe'ta istatistiksel anlamlılık İMKANSIZ.** Tek test edilebilir edge = **cross-sectional rank-IC** (~100 hisse × ~24 ay ≈ binlerce hisse-ay havuzlar). Birincil kanıt IC, Sharpe DEĞİL.

#### ÖN-KAYIT ZORUNLU (Stage 0 — backtest'ten ÖNCE)
Backtest koşmadan ÖNCE yazılır, timestamp'lenir, dondurulur (dated git commit): 5 gating + failure eşikleri, faktör tanımları, maliyet modeli, benchmark, **maksimum konfigürasyon N ≤ 3 (ideal N=1)**. MinBTL: <3 yıl veriyle 7 varyant denemek garantili overfitting (López de Prado). Bu, "beating ideas to death"i KISITLAR — önceden-kayıtlı tek tasarım.

#### 5 GATING KRİTER (hepsi sağlanmalı — AND)
```
1. Composite rank-IC ≥ 0.03 (hedef 0.05) VE ICIR ≥ 0.5
   rank-IC = Spearman(signal_rank, fwd_return_rank); IC serisine t-test
   ⚠️ rank-IC > 0.15 → KUTLAMA DEĞİL, overfitting şüphesi
   ⚠️ BİRİNCİL KANIT bu (cross-sectional, binlerce gözlem)

2. PBO < 0.50 (hedef < 0.20) — CSCV/CPCV
   ⚠️ Optimize ağırlık YOK → yapısal düşük olmalı (tasarım avantajı)

3. Net-of-cost REEL getiri pozitif VE benchmark'ı geçer
   benchmark = max(TÜFE, TLREF); hedef +%3-5 reel spread
   ⚠️ +%10 reel spread → overfitting şüphesi
   ⚠️ Sharpe reel/USD bazlı; risk-free = MMF/repo rate

4. Tercile (quintile DEĞİL — 100→5-10 seçimde quintile çok ince)
   top-minus-bottom spread POZİTİF VE istatistiksel anlamlı
   ⚠️ Tam monotonluk (Patton-Timmermann) SUPPORTIVE, gating değil

5. DSR (Deflated Sharpe Ratio) — SUPPORTIVE, gating DEĞİL
   ⚠️ DÜZELTME (bağımsız kritik): NRR-003 hem "Sharpe ölçülemez"
   hem "DSR>0.95 gating" diyordu — çelişki. Az örneklemde DSR gürültülü
   → false-negative riski. Birincil kanıt IC olduğu için DSR supportive'e
   indirildi. Referans olarak izlenir (DSR<0.90 = uyarı), ama tek başına
   reddetmez.
```

#### CPCV mekaniği (NRR-003)
N=6 grup, k=2 → 15 split, **5 backtest path**. **Purge:** 1-2 ay holding label-overlap temizle. **Embargo:** sonrasında leak engelle. Çıktı: OOS Sharpe dağılımı (tek nokta değil).

#### SUPPORTIVE (gating değil)
DSR (yukarıda), walk-forward efficiency ≥ 0.5, tam monotonluk, turnover/maliyet oranı, CPCV path drawdown stabilitesi, **per-faktör IC (ölü faktör tespiti — özellikle momentum)**.

#### FAILURE EŞİKLERİ (herhangi biri → "premise'i yeniden düşün")
```
- Composite rank-IC ≤ 0          → hard fail
- Composite ICIR < 0.3           → çok kararsız
- PBO > 0.50                     → muhtemelen overfit
- Net-of-cost reel getiri ≤ 0    → enflasyona/cash'e kaybediyor
- Tercile spread negatif/anlamsız
- Max drawdown > ~%35-40 VEYA CPCV path'leri arası tutarsız
- Composite'in dayandığı tek faktör negatif standalone IC (özellikle momentum)
```

**Absence of evidence ≠ evidence of absence (NRR-003):** ~24 ayda genelde "kanıt yokluğu." IC ~0 + dar CI → kanıt yok → öldür. IC pozitif ama anlamsız + geniş CI → belirsiz → sermaye verme, veri topla (deploy ETME, başarı İLAN ETME).

#### D-176 BASELINE (yeni tarama bunu GEÇMELİ — ampirik)
Mevcut composite seçim mekanizması (terk edilen) ölçülmüş per-trade ekonomisi: **expectancy +5.3%/trade, win %58.7, PF 2.19, payoff 1.63.** Bu, seçimin çalıştığını gösteriyor — sorun konuşlanmaydı (avg_exposure %13). **Katman A bu seçim kalitesini en azından KORUMALI** (tercihen artırmalı) VE konuşlanmayı yükseltmeli (avg_exposure %13'ten belirgin yukarı). Yeni tarama, eski seçimin +5.3%/trade edge'ini düşürürse → tarama tasarımı başarısız.

#### Geçer kriter
4 gating'in HEPSİ (AND: IC+ICIR / PBO / reel spread / tercile) → çekirdek edge'i kanıtlandı → LLM katmanına geç. Herhangi biri başarısız → çekirdeği yeniden düşün (patch'leyip yeniden koşma — ön-kaydın engellediği post-hoc rasyonalizasyon).

**Gerçekçi hedef (NRR-003):** OOS Sharpe ~0.5-0.8 (1.5-2.0 DEĞİL — o overfit). ~3000 USD'de +%5 reel ≈ 150 USD/yıl → birincil amaç beceri+süreç validasyonu. **Quarter-to-half Kelly ZORUNLU.**

#### Momentum/RS uyarısı (NRR-001 + NRR-003 — ÜÇ KEZ tekrarlandı)
RS/momentum faktörü **composite'e girmeden ÖNCE standalone valide edilmeli.** BIST güçlü contrarian/reversal gösteriyor (Bildik-Gülay 2007: kaybedenler kazananları ~%15/yıl yeniyor). **Standalone IC ≤ 0 ise → at veya kısa-vadeli reversal sinyaliyle değiştir.** En olası tek-nokta-başarısızlık bu.

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
3. **Strangler sırası** — yeni yanına, eski EN SON (eski çalışırken)
4. **Eşit-ağırlık** — Katman A'da z-score/optimize ağırlık YASAK (overfitting)
5. **RS-vs-XU100** — mutlak nominal RS YASAK (enflasyon kirliliği)
6. **LLM tetiğe bağlanmaz** — Katman B çıktısı öneri, aktüatör değil
7. **ASLA LLM-in-the-loop backtest** — contamination
8. **Maliyet-sonrası ölçüm** — quintile spread net (komisyon+BSMV+spread)
9. **Survivorship** — halt/delist dahil (KOZAA/KOZAL/IPEKE)
10. **Runner/trailing EKLENMEZ** — D-176 reddetti; mevcut profit_target/stop korunur
11. **Cash drag çözümü Katman A ile** — naif BUY-eşik-düşürme YASAK (kaliteyi düşürür)
12. **DSR gating DEĞİL** — supportive; birincil kanıt rank-IC

---

## 10. KARARA BAĞLANAN SORULAR (✅ 5/5 KAPANDI — 29 May 2026)

> Bu sorular Architect SPEC'ten ÖNCE kapatıldı (NRR-002 + NRR-003 + Cagan kararı + Orchestrator + D-176 ampirik). Architect bunları varsayım değil, KARAR olarak alır.

**S1 — Benchmark serisi (NRR-002):** ✅ **max(TÜFE, TLREF)**
- TÜFE: `TP.FG.J0` (EVDS, zaten var — D-151); TLREF: `TP.BISTTLREF.KAPANIS` (EVDS, ücretsiz, günlük, 2019+, resmi gecelik risksiz faiz)
- **Para piyasası fonu kategori ortalaması hazır seri olarak YOK** (TEFAS/KYD); fon NAV (GTL/ALE) sadece robustluk kontrolü (TEFAS API, kırılgan)
- Risk-free = MMF/repo rate; Sharpe REEL veya USD bazlı (nominal TRY Sharpe ~%37-50 cash rate'le anlamsız)

**S2 — Validasyon eşiği (NRR-003 + bağımsız kritik düzeltmesi):** ✅ **4 gating + DSR supportive (§7.1)**
- GATING (AND): rank-IC≥0.03+ICIR≥0.5 / PBO<0.5 / reel pozitif +%3-5 spread / tercile pozitif+anlamlı
- DSR **supportive'e indirildi** (gating değil) — az örneklemde Sharpe ölçülemezse DSR de gürültülü, false-negative riski
- Birincil kanıt cross-sectional IC; N≤3 konfigürasyon; ön-kayıt zorunlu; hedef OOS Sharpe 0.5-0.8

**S3 — Evren (Cagan kararı):** ✅ **BIST100** (ADV kapısı likit alt-kümeye daraltır; survivorship: halt/delist dahil)

**S4 — Value faktörü (NRR-002):** ✅ **USD-bazlı F/DD + EV/EBITDA**
- Nominal F/K YASAK (TMS 29 net kârı çarpıtıyor); EV/EBITDA net parasal pozisyona az duyarlı
- NPPKK ek kalite filtresi (OOS test); **UFRS/TMS 29 finansalları ZORUNLU** (VUK 2025-27 ertelendi)
- ⚠️ 2022-2024 yapısal kırılma (TMS 29 ilk 2023 sonu)

**S5 — Rebalance frekansı (Orchestrator):** ✅ **Haftalık tarama, iki-haftalık/aylık rebalance** (düşük-turnover faktörler + maliyet; kesin değer IC decay belirler)

**EK KARAR 1 — Faktör validasyon sırası (NRR-001+003):** RS/momentum composite'e girmeden ÖNCE standalone valide edilmeli. BIST contrarian riski. Standalone IC≤0 → at/reversal.

**EK KARAR 2 — Çıkış profili (D-176 ampirik):** ✅ **Mevcut profit_target/stop KORUNUR, runner/trailing EKLENMEZ.** Runner counterfactual veriyle reddetti (trailing 8/10%'da net negatif). Çıkış sorun değil.

**EK KARAR 3 — Birincil problem (D-176 ampirik):** ✅ **Cash drag (avg_exposure %13).** Seçim çalışıyor (+5.3%/trade), konuşlanma çalışmıyor. Katman A bu seçim kalitesini KORUYUP konuşlanmayı yükseltmeli. NAİF eşik-düşürme YASAK (kalite düşürür).

---

## 11. KAYNAK REFERANSLARI

- **CB-016** — pivot kararı (CRITIC_BACKLOG.md)
- **Critic-MOBILE** — teşhis (reel -42%, ölü ağırlık, null-test)
- **Mimar-MOBILE** — LLM mutfağa al direksiyona değil; sorumluluk ayrımı
- **RR-MOBILE-001** — BIST 2024-2026 rejim; reel benchmark; enflasyon pass-through
- **RR-MOBILE-002** — LLM trading endüstri+akademik; contamination; Türkçe NLP
- **NRR-001** — BIST tarama metodolojisi; ardışık-filtre+rank; RS-vs-XU100; validasyon
- **NRR-002** — Benchmark serisi (TLREF) + enflasyon-düzeltmeli value (USD F/DD + EV/EBITDA); S1+S4
- **NRR-003** — Validasyon eşikleri (4 gating + DSR supportive); az-örneklem; MinBTL; momentum riski; S2
- **PIVOT_ARCHITECTURE_AUDIT** — codebase denetimi; in-place refactor; KOVA haritası
- **D-176** — trade dağılımı teşhisi (AMPİRİK): cash drag (avg_exposure %13), seçim çalışıyor (+5.3%/trade), runner reddedildi, skew +0.10

---

*ARCHITECTURE v1.2 — 29 Mayıs 2026 Session #8. 5 açık soru karara bağlandı (S1-S5) + D-176 ampirik teşhis işlendi (cash drag birincil problem, çıkış profili korunur). Bu doküman Architect SPEC_PIVOT_ARCHITECTURE_1'in temelidir — varsayım yok, kararlar veriyle desteklendi. Eski linear-additive mimari OS_STATE'de tarihsel referans olarak korunur.*
