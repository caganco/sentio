# RR-Y1-005B — MATEMATİKSEL SPEC (Faz-1.5)
## Konjuge-Motorun Formel Çekirdeği: ψ + Konjuge-Uyum + Faktör-Nötrleme

**Statü:** FORMEL-SPEC — DONMUŞ. Tasarım v0.2'nin üç-boşluğunu (a/b/c) kapatır; Faz-2 build bunu girdi-alır.
**Sürüm:** v1.1 — 4 Haziran 2026 (v1.0→v1.1: Çatal-1 — Mod-A çekirdeği gerçek-CSCV-PBO; mevcut compute_pbo proxy, Mod-B-only).
**Çelişki-önceliği:** TASARIM v0.2 > bu-spec > build-direktifi > Builder.
**İlke:** her formül yerleşik-literatüre dayanır (sezgi-değil). Kaynaklar §9.
**Builder-notu:** "düz-uygula (yerleşik)" ve "DONMUŞ-default (bizim-kararımız)" ayrımı her bölümde işaretli. DONMUŞ-default'lar Stage-0'da pinlenir; sonuca-bakıp-değiştirme guard-RAISE.

> Her bölüm: **(plain)** = Çağan-için-ne-yapıyor · **(formel)** = Builder-için-tanım · **(donmuş)** = pinli-parametreler.

---

## 1. NOTASYON (ortak)

Panel: gün `t`, isim `i ∈ N_t`. Look-ahead-safe getiri (total-return, `tr_index`): `r_{i,t}` = `t`'den `t+1` rebal'a knowable-getiri. Sinyal `s_{i,t}` = `t`'de **knowable** (lag-uygulanmış) skor. Piyasa getirisi `r_mkt,t` (XU100, `exposure_d187_xu100`).

---

## 2. BOŞLUK (a) — ψ: rank-IC ve kararlılık

**(plain)** ψ, "sinyalin bir günde isimleri ne kadar doğru-sıraladığını" ölçen sayıdır. Her gün bir skor üretir; bu skorların zaman-içindeki ortalaması ve istikrarı sinyalin gücüdür. Kaynak: Grinold-Kahn "fundamental law" (IR ≈ IC·√breadth) — endüstri-standardı.

**(formel)**
- **Günlük rank-IC** (cross-sectional Spearman): `IC_t = Spearman( s_{·,t} , r_{·,t→t+h} )`, isim-kesiti üzerinde. `h` = rebal-ufku (günlük testte h=1 rebal-adımı, aylıkta h=1 ay).
- **Gerçekleşen IR** (kararlılık): `IR = mean_t(IC_t) / std_t(IC_t)`. (Grinold-Kahn: bu sinyalin realize-skill/breadth bileşimi.)
- **Anlamlılık** (IC serisi otokoreledir → HAC zorunlu): `t_IC = mean(IC_t) / NW_SE(IC_t)`, Newey-West/Bartlett-kernel, lag `m`. Repo'da hazır: `c9._nw_t`, `src/backtest...sharpe_newey_west` (§5, yeniden-kullan).
- **İşaret-tutarlılığı** (yardımcı): `hit = frac_t( sign(IC_t) = sign(mean IC) )`.

**Çerçeve-kilidi:** ψ "sürekli-forward" çerçevesinde ölçülür (N≈gün/ay). ψ bir **kabul-kapısı-DEĞİL** (rejim düşürüldü, tasarım §4.3); ψ, konjuge-uyumun (boşluk-b) ölçtüğü büyüklüktür. Yani "edge gerçek mi" kararı ψ-eşiğiyle-değil, ψ'nin-konjuge-tutarlılığıyla verilir.

**(donmuş-default)**
- Spearman-rank-IC (Pearson-değil → aykırı-dayanıklı).
- Cross-section min-isim: **≥30** (altında o-gün IC NaN, breadth-yetersiz; recon B7 likit ~38-77/arm ile uyumlu).
- Forward-getiri: total-return (`tr_index`), knowable-lag, look-ahead-safe.
- NW-lag `m`: günlük `m = 5` (haftalık-otokorelasyon); aylık `m = 3`. (Stock-Watson default-mertebesi; sinyal-otokorelasyonu uzunsa h-window'a yükselt — bkz boşluk-c/embargo.)
- Winsorize sinyal: cross-section %1/%99 (aşırı-uç sırayı-bozmasın).

---

## 3. BOŞLUK (c) — Faktör-nötrleme (önce-bu; çünkü uyum nötrlenmiş-getiride ölçülür)

**(plain)** İki isim-yarısının "aynı edge'i göstermesi" ya gerçek-seçim-becerisindendir ya da ikisinin-de-aynı-piyasaya-binmesinden. İkincisini elemek için, getirilerden piyasa-etkisini söküp **artık-getiri** ile çalışırız. Sektör-sökmesi long-only'de genelde zararlı (kaynak FAJ 2023) → default-kapalı.

**(formel) — Piyasa-betası nötrlemesi (Mod-A için ZORUNLU)**
- Zaman-serisi rolling-beta: her isim için trailing-pencerede `r_{i,τ} = α_i + β_i·r_mkt,τ + ε`, `τ ∈ [t−W, t−1]` (yalnız-geçmiş → look-ahead-safe).
- Artık-getiri: `r̃_{i,t} = r_{i,t} − β̂_{i,t}·r_mkt,t`. ψ ve uyum `r̃` üzerinde hesaplanır.
- Kaynak-zemini: residual-momentum literatürü (faktör-modeli-residual'i ile sistematik-bağımlılığı söker, Quantpedia/Blitz).

**(formel) — Karma-frekans kuralı**
- Piyasa-beta: GÜNLÜK (`exposure_d187_xu100` mevcut, recon B8).
- Size/value (aylık karakteristikler): nötrleme rebal-frekansında **cross-sectional rank-orthogonalizasyon** — sinyali o-ayki size/value-rank'ına regresle, residual'i al (zaman-serisi-beta-değil; aylık-veriyle uyumlu).
- **Sektör: opsiyonel dial, default KAPALI.** Long-only'de sektör-nötrleme across-component değerini-siler (FAJ 2023). Açılırsa: sektör-içi-demean (`sector_map.py`, PIT, 2019-07+; effective-start-uyarısı tasarım §3.5).

**(formel) — Konjuge OOS-temizliği**
- İsim-bölmesinde iki-arm aynı-zaman-dilimi → β trailing-pencerede tahmin (look-ahead-safe), **arm-bağımsız** (her ismin β'sı kendi-geçmişinden; bölmeden-etkilenmez). Cross-sectional-orthogonalizasyon ise **arm-içinde** yapılır (X_1 ve X_2 ayrı demean) → bir-armın bilgisi diğerine-sızmaz.

**(donmuş-default)**
- Beta-pencere `W = 126 gün` (≈6 ay; recon-duyarlılık 30/60/90/120 ile test-edilir, plato-ilkesi §tasarım-5). Min-gözlem `0.8·W`.
- Beta-tahmin: basit-OLS trailing (EWM opsiyonel-dial).
- Nötrleme-derinliği default: **market-only**. +size/+value opsiyonel-dial. Sektör default-OFF (long-only).
- `getiri_tabani = total_return` (tr_index, fiyat-only-değil; tasarım C5).

---

## 4. BOŞLUK (b) — Konjuge-uyum istatistiği (motorun ÇEKİRDEĞİ)

**(plain)** "X_1'de iyi-çalışan sinyal, X_2'de de iyi-çalışıyor mu?" sorusunu sayıya çeviriyoruz. Builder haklı-uyardı: burada **iki ayrı ve TERS-yönlü** büyüklük var, karıştırmak sessiz-hata olur. Birincisi (uyum) yüksek-olsun-isteriz; ikincisi (kalıntı-korelasyon) düşük-olsun-isteriz. İkisini ayrı-formülize ediyoruz.

### 4.1 UYUM — asset-space out-of-sample (istenir: GÜÇLÜ)
**(formel)** Yerleşik-yöntem: faktörü bir-arm'da seç/sırala, **diğer-arm'da değerlendir** (Roussanov; higher-order-factors OOS-in-asset-space). Simetrik:
- X_1'de sinyali kur → X_2'de gerçekleşen `r̃`-aktif-getiri ve `IC^{X1→X2}_t` serisi → `t_IC^{X1→X2}` (NW).
- X_2'de kur → X_1'de değerlendir → `t_IC^{X2→X1}`.
- **Çoklu-rastgele-bölme:** R bağımsız seed-sabit bölme (recon: rastgele-yarı veya likidite-eşleştirilmiş). Her bölme bir cross-arm-OOS-IC dağılımı verir (CPCV-path mantığının cross-sectional-eşi).
- **PBO-analoğu:** in-arm-en-iyi-konfig cross-arm'da medyan-altına-düşüyor mu → repo `compute_pbo` (CSCV) yeniden-kullan (§5).

**(donmuş-default) PASS-bar (Stage-0'da, sonuç-ÖNCESİ donar):**
1. `median_R( t_IC^{cross} ) > 2.0` (her-iki-yön), VE
2. işaret-tutarlılığı: `frac_R( sign(IC^{X1→X2}) = sign(IC^{X2→X1}) ) ≥ 0.90`, VE
3. `PBO < 0.50` (**gerçek CSCV median-rank PBO** — best-IS'in OOS-medyan-altına-düşme oranı; basit `P(OOS Sharpe<0)` proxy-DEĞİL, §5).
Üçü-birden geçmezse → uyum-YOK. (Eşikler keep-bar; sonuca-bakıp-gevşetme guard-RAISE.)

### 4.2 KALINTI-KORELASYON — paylaşılan-faktör-kontrolü (istenir: DÜŞÜK)
**(formel)** İki-arm'ın **nötrleme-sonrası** aktif-getiri zaman-serileri arasındaki korelasyon `ρ_arms = corr( a^{X1}_t , a^{X2}_t )`. Yüksekse: uyum gerçek-idiyosenkratik-edge-değil, ortak-artık-faktör (nötrleme-eksik) demek.
- **Eşik keyfi-değil, NULL'dan:** permütasyon-null — isimleri rastgele-yeniden-böl, R_null kez `ρ_arms` dağılımı; gözlenen-ρ null-%95'in üstündeyse kırmızı-bayrak (adil-null dersi). Sabit-0.3-gibi-keyfi-eşik YASAK.

### 4.3 KARIŞTIRMA-YASAĞI (Builder-flag, sessiz-hata-önleme)
Uyum (4.1) **cross-arm-tahmin-performansıyla** ölçülür; kalıntı-korelasyon (4.2) **arm-getiri-eş-hareketiyle**. İkisi ayrı-fonksiyon, ayrı-rapor-alanı. Uyumu-korelasyonla-ölçmek (veya tersi) = SESSİZ-HATA → kod-incelemesinde ayrı-test.

---

## 5. MEVCUT-KODLA UZLAŞTIRMA (recon §3 — sıfırdan-yazma-YOK)

Repo'da hazır (Builder-buldu): `src/backtest/statistical_validation.py` (`compute_dsr`, `compute_pbo`, `sharpe_newey_west`, `min_btl_days`) + `src/backtest/cross_validation.py` (`PurgedKFold`, `CombinatorialPurgedCV`) + `c9._nw_t`, `c9._exact_binom_one_sided`.
- **PBO/DSR/NW-t/CPCV:** yeniden-kullan, yeniden-yazma — AMA bir-istisna (Builder-bulgusu, S#14): mevcut `compute_pbo` aslında basit `P(OOS Sharpe<0)` proxy'sidir, gerçek-CSCV-DEĞİL. Konjuge-uyum (§4.1) motorun merkez-iddiası → **Mod-A çekirdeği için gerçek CSCV median-rank PBO kur** (best-IS'in OOS-medyan-altı-oranı, Bailey–López de Prado); basit `compute_pbo`'yu yalnız **Mod-B convenience-bacağında, etiketli** kullan. Bu "yeniden-yazma-yasağı"nı çiğnemez — proxy'yi-CSCV-diye-etiketlememe (sessiz-mis-attribution-önleme) gereğidir. Gerçek-CSCV-PBO'yu §7 fixture'ları doğrular (saf-gürültü→yüksek-PBO, gömülü-gerçek-faktör→düşük-PBO) → yeni-kod silent-error-riski kapanır.
- **Default-uzlaştırma (DONMUŞ):** mevcut CPCV `N=6,k=2,purge=10,embargo=5` → tasarım-hedefi `N=10` (günlük, ~184g/blok), `k=2` (45-path), `purge=h`, **`embargo = sinyal-construction-window`** (boşluk-c, S4). Aylık: temporal-CPCV-YASAK (güç-fakiri, S6) → Mod-A.
- DSR `denenen_konfig_sayisi` Stage-0'dan-beslenir (dürüst-sayım).

---

## 6. BENCHMARK / TLREF VERİ-DUVARI (recon §4)

**(plain)** Reel-hedef `> max(TÜFE, TLREF)`. Ama TLREF temiz-serisi 2022-07'den başlıyor; öncesi NaN. Sessiz-NaN tuzağına düşmemek için kuralı açık-pinliyoruz.

**(donmuş-default)**
- Reel-deflate: **TÜFE her-zaman** (TP.FG.J0, 2019+).
- Benchmark-floor: `2022-07-öncesi = TÜFE-only`; `2022-07+ = max(TÜFE, TLREF)`. Sessiz-NaN → guard-RAISE (d213-precedent: "silent-NaN until 2022-07" kayıtlı).

---

## 7. YENİ KABUL-FIXTURE'LARI (Mod-A doğruluğu — golden-fixture'ın KAPATMADIĞI boşluk)

**(plain)** Golden-fixture (C12) walk-forward'ı (Mod-B) sınar; ama isim-bölmesi+uyum-istatistiği (Mod-A) **tamamen-yeni** ve onu hiçbir bilinen-sonuç denetlemiyordu. Sessiz-hata-riski tam-orada. Üç sentetik-fixture bu boşluğu kapatır (bilinen-cevap):

1. **Saf-gürültü (false-positive kontrolü):** iki-arm bağımsız-rastgele-getiri, sinyal=gürültü → §4.1 PASS-bar FIRE-ETMEMELİ (uyum-yok çıkmalı). Fire-ederse motor-bozuk.
2. **Gömülü-gerçek-cross-sectional-faktör:** her-iki-arm'da aynı idiyosenkratik-tahmin-edici (market-nötr) → §4.1 PASS-ETMELİ, §4.2 kalıntı-korelasyon DÜŞÜK kalmalı (gerçek-edge, paylaşılan-faktör-değil).
3. **Saf-paylaşılan-piyasa-faktörü:** sinyal sadece market-betaya-biniyor → nötrleme-sonrası §4.1 PASS-ETMEMELİ VE/VEYA §4.2 kalıntı-korelasyon YÜKSEK kırmızı-bayrak (paylaşılan-faktör yakalanmalı).

Üçü pytest; build bunlarsız tamamlanmaz. (Golden-fixture §8.1 + synthetic-null §8.2 + bu-üçü = tam anti-slop kapısı.)

---

## 8. DONMUŞ-PARAMETRE TABLOSU (tek-yerde — Stage-0'a pinlenir)

| Parametre | Değer | Kaynak/gerekçe |
|-----------|-------|----------------|
| IC-tipi | Spearman rank-IC | aykırı-dayanıklı (Grinold-Kahn) |
| min-isim/kesit | 30 | breadth; recon B7 |
| forward-getiri | total-return (tr_index), knowable-lag | tasarım C5 |
| NW-lag m | günlük 5 / aylık 3 | Stock-Watson; sinyal-OK uzunsa h'a yükselt |
| sinyal-winsorize | %1/%99 | sıra-bozulmasın |
| beta-pencere W | 126 gün (min 0.8W) | 30-120-256 plato-test; residual-momentum |
| nötrleme-derinliği | market-only (default) | FAJ: sektör long-only-zararlı → default-OFF |
| split R (rastgele-bölme) | ≥50 | dağılım-stabilitesi |
| uyum PASS: cross-IC-t | >2.0 (çift-yön) | NW-anlamlılık |
| uyum PASS: işaret-tutarlılık | ≥0.90 | — |
| uyum PASS: PBO | <0.50 | gerçek CSCV median-rank (López de Prado); proxy-değil (§5) |
| kalıntı-korelasyon eşik | permütasyon-null %95 | adil-null (keyfi-sabit-YASAK) |
| CPCV (günlük) | N=10, k=2, purge=h, embargo=construction-window | recon B9; mevcut-koddan-uzlaştır |
| aylık temporal-CPCV | YASAK → Mod-A | güç-fakiri (S6) |
| benchmark-floor | TÜFE-always; +TLREF 2022-07'den | d213-NaN-tuzağı |

---

## 9. KAYNAKLAR (sezgi-değil dayanak)

- **IC/IR/breadth, ψ:** Grinold & Kahn, *Active Portfolio Management* (fundamental law IR≈IC·√BR); Goodwin, *The Information Ratio*; Fundamental-Law-Redux (cross-section IC formel).
- **NW/HAC anlamlılık:** Newey-West (1987), Bartlett-kernel HAC; IC-serisi otokoreli → zorunlu.
- **Faktör-nötrleme/residual:** residual-momentum (FF-residual ile sistematik-söküm); sektör-nötrleme long-only-zararlı (Financial Analysts Journal 2023); beta-pencere-duyarlılığı (rolling 30-120g).
- **Konjuge-uyum (asset-space OOS):** Roussanov ("OOS measure in asset space"); higher-order-factors ("out-of-sample test in asset space: select train-assets, evaluate remaining").
- **PBO/CPCV/DSR:** López de Prado (CPCV, purge/embargo); Bailey & López de Prado (PBO/CSCV, deflated-Sharpe). Repo'da implementli (§5).

---

*RR-Y1-005B-MATEMATİKSEL-SPEC v1.1 — 4 Haziran 2026, DONMUŞ. Üç-boşluk (ψ / konjuge-uyum / nötrleme) yerleşik-literatürle formel-kapatıldı; uyum-ve-kalıntı-korelasyon AYRI-formülize (karıştırma-yasağı); Mod-A çekirdeği GERÇEK-CSCV-PBO (proxy-değil, Çatal-1), §7-fixture'larıyla-doğrulanır; DSR/NW-t mevcut-koddan; Mod-A doğruluğu üç-sentetik-fixture ile bilinen-cevaba-bağlandı; sektör-nötrleme long-only-default-OFF; benchmark-TLREF-NaN açık-pinlendi. Sezgi-değil, dayanak-§9.*
