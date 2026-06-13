# RR-Y1-022 — Multiple-Testing Harness (MTH) — minimal core (altyapı; promosyon-kapısı)

**Sınıf:** doğrulama-altyapısı (validation infrastructure). **Stage-0-DEĞİL**, ölçüm-DEĞİL,
herhangi bir gerçek araştırma-adayı üzerinde hüküm-DEĞİL; hiçbir getiri ölçülmedi, hiçbir
frozen-pencere/X₂ tüketilmedi. Yeni, **eklenti (additive)** bir modül — committed Mod-A/B/C
motoru ve mevcut hiçbir test değiştirilmedi (strangler). Yalnız **sentetik fixture'larla**
doğrulanır.

**Ne çözer:** Bir geliştirme örnekleminde (X₁) **K** aday strateji arandığında, en iyi
performans gösteren strateji **arandığı için** seçilir → görünen üstünlüğü aramanın kendisi
(data-snooping) tarafından şişirilir. MTH bu aramayı düzeltir ve en-iyi adayın BIST100
**toplam-getiri** (temettü-reyatırımlı, sermaye-aksiyonu düzeltilmiş) benchmark'ı üzerindeki
fazla-getirisinin arama-şansından ayırt edilebilir olup olmadığına dair üç-dallı bir hüküm
verir. Tek-atışlık doğrulama testini (X₂) **korur**; X₂'ye dokunmaz.

---

## A. Tasarım (audit-hardened; istatistik doğaçlanmadı)

**Benchmark.** Performans her zaman benchmark üzerindeki **fazla-getiri** olarak ölçülür;
benchmark = BIST100 **toplam-getiri** (fiyat-yalnız endeks adil-olmayan-kolay null'dır ve
asla benchmark değildir). Beslenen getiriler, çağıranın yüklemek istediği maliyetlerden
zaten net kabul edilir (harness yeniden maliyetlendirmez).

**İki tamamlayıcı null — İKİSİ de zorunlu, ikisi de raporlanır (F1 güvencesi):**

| Null | Ne | Nasıl |
|---|---|---|
| (1) Reality Check / SPA | evren-genelinde data-snooping düzeltmesi | `arch.bootstrap.SPA` **sarmalanır** (Hansen 2005; White 2000 özel-hâl) — istatistik elde-yazılmaz. Benchmark-kaybı = sıfır taban, model-kaybı = `-fazla-getiri` (kayıp=negatif-fazla-getiri, arch'ın küçük-iyidir kuralı). Kilitli config: `bootstrap='stationary'`, `studentize=True`, sabit `reps` + sabit `seed`; stationary blok-uzunluğu `optimal_block_length` ile diferansiyel matris üzerinde **bir kez** (stratejilerin stationary-optimumlarının ortalaması, alt-sınır 1). Raporlanan p = SPA `consistent` (SPA_c); `lower`/`upper` detayda. |
| (2) Eşleşmiş permütasyon | durağan-olmayana-dayanıklı çapraz-kontrol | doğrudan burada (shuffle→yeniden-hesapla→say). **Cross-sectional:** her zaman-adımında tek bir varlık-ekseni permütasyonu tüm stratejilerin sinyaline uygulanır (hangi varlık hangi sinyal-değerini alır rastgelelenir), her varlığın kendi getiri-serisi sabit. **Timing:** fazla-getiri serisinin blok işaret-çevirmesi (aynı işaret-vektörü tüm stratejilerde, çapraz-strateji bağımlılığı korunur), benchmark yolu sabit. Çağıran strateji-tipini bildirir; harness eşleşen null'ı seçer. Her iki null da strateji-başına ortalamayı studentize edip evren üzerinden max alır. |

**Agreement (F1 hüküm tablosu):** her iki p ≤ kilitli α **VE** ekonomik-boyut pozitif →
`PROMOTE-CANDIDATE`; ikisi de anlamsız → `REJECT`; **ayrışma** (biri anlamlı biri değil) ya
da ikisi-anlamlı-ama-ekonomik-boyut≤0 → `FLAG-INCONCLUSIVE` (söyleyemiyoruz — hata değil,
geçerli çıktı). α = 0.05 spec'te **kilitli**, çalıştırma-başına ayarlanamaz.

**Evren-dürüstlüğü (F2):** harness, ön-kayıtlı (pre-registered), kod-bakımından-tüketici
strateji-ailesini tüketir. Hesaplamadan önce ilan edilmiş **frozen manifest**'i alır ve
sunulan evrenin manifest'e **eşit** olduğunu (ekleme/çıkarma yok) doğrular; uyumsuzlukta
`MTHManifestError` fırlatır. Bu, dürüst-dâhil-etmeyi güvene değil mekaniğe bağlar. **Gerekli
ama yeterli-değil:** aileler-arası meta-arama ayrı loglanır; X₂ son-mercidir.

**Raporlama (F7):** her zaman birlikte — RC p-değeri, permütasyon p-değeri, agreement hükmü
**VE** ekonomik-boyut (en-iyi stratejinin yıllıklandırılmış maliyet-sonrası fazla-getiri
büyüklüğü). Asla tek başına bir p-değeri yok.

**Genel arayüz (saf / seed-verili-deterministik):** `run_mth(...) -> MTHReport`;
`decide_verdict(...)` (F1 kuralı, public→doğrudan test edilebilir); `MTHConfig`
(`LOCKED_MTH_CONFIG`); `StrategyType`; `CrossSectionalPanel`; `MTHVerdict`; `MTHManifestError`.
Dosya: `src/engine/multiple_testing.py`.

---

## B. Doğrulama (ölçüm-doğrulaması — C12 statüsünde HARD-GATE golden fixture)

Harness bir hüküm-vericidir; kalibrasyonu zorunlu sert-kapıdır (regresyon build'i düşürür).
Tümü sentetik + seed-sabitli; `tests/test_engine_multiple_testing.py`.

| Fixture | Ne ölçer | Gözlenen | Eşik (assert) |
|---|---|---|---|
| **SIZE — timing** | saf-gürültü evreni ~α'da reddetmeli | rc=0.06, perm=0.07 (M=100) | ≤ 0.15 (aşırı-red = FAIL) |
| **SIZE — cross-sectional** | aynısı, XS null | rc=0.05, perm=0.05 (M=60) | ≤ 0.15 |
| **POWER — timing** | ekilmiş kenar saptanmalı | promote=0.95 (M=100) | ≥ 0.6 |
| **POWER — cross-sectional** | ekilmiş kenar saptanmalı | promote=1.00 (M=60) | ≥ 0.8 |
| **Differential ref** | sarmalayıcı = doğrudan arch SPA | birebir eşit | == (byte) |
| **Determinizm çıpası** | aynı veri+seed → birebir tekrar | rc/perm tekrarlanır; econ=sürüm-kararlı | tam eşit + reprodüksiyon |

**Yorum:** aşırı-red yok (her iki null da ~α; RC hafif-muhafazakâr) → yanlış-pozitif-fabrikası
değil. Permütasyon yolu RC ile aynı size+power fixture'larını **bağımsız** geçer (madde d).
Ekonomik-boyut saf veri-aritmetiğidir (sürüm/kütüphane-bağımsız) → byte-kararlı çıpa.

---

## C. Sınır koşulları (modül docstring + burada — hüküm değil, dürüstlük)

1. **Guard, generator değil.** Harness ÇOĞUNLUKLA reddeden bir korumadır; titiz bir HAYIR
   onun normal, doğru çıktısıdır — makinenin başarısızlığı değil.
2. **Timing düşük güçlü.** Kısa BIST örneklerinde timing stratejilerinin gücü düşüktür; oradaki
   bir red-edememe zayıf kanıttır, temiz bir "hayır" değil.
3. **Durağanlık ön-koşulu.** Sinyaller test öncesi durağanlık/dönüşüm açısından kontrol
   edilmeli — null'lar diferansiyel-serinin iyi-davranışlı olduğunu varsayar.
4. **Çok-az strateji.** Az sayıda strateji max-dağılımını anlamsızlaştırır (`_MIN_STRATEGIES`
   altında guard mesajı).
5. **Ayrışma = INCONCLUSIVE.** RC/permütasyon ayrışması sessizce çözülmez; "söyleyemiyoruz"
   olarak raporlanır.

---

## D. Kapsam sınırı (bilinçli; bu görevde YAPILMADI)

Minimal çekirdek **yalnız**: StepM, FDR, MCS, DSR, MinTRL bu görevde uygulanmadı (ayrı
genişleme). Harness hiçbir gerçek araştırma-adayı üzerinde **çalıştırılmadı**; hiçbir Stage-0
açılmadı; X₂'ye dokunulmadı. Bağımlılık: `arch>=6.3` (requirements.txt).

---

## Caveat'lar
- **Bu modül hiçbir gerçek BIST adayını değerlendirmez** — yalnız sentetik fixture kalibrasyonu.
  Bir gerçek aday üzerinde kullanımı ayrı, soğuk bir karar gerektirir (maintainer'a ait).
- **`reps` bir compute-bütçesidir, karar-düğmesi değil:** kilitli üretim değeri 10000; kalibrasyon
  fixture'ları yalnız çalışma-süresi için düşürür (α/bootstrap/studentize sabit kalır).
- **Asla tek p-değeri** raporlanmaz (F7); ayrışma bir hata değil geçerli "cannot tell" çıktısıdır.
- Gerekli-ama-yeterli-değil (F2): aileler-arası meta-arama ayrı loglanmalı; X₂ son-mercidir.

Kaynaklar: White (2000) "A Reality Check for Data Snooping" · Hansen (2005) "A Test for Superior
Predictive Ability" (SPA) · Politis-Romano (1994) stationary bootstrap · Politis-White (2004)
otomatik blok-uzunluğu · `arch` (Kevin Sheppard) `arch.bootstrap.SPA`/`optimal_block_length` ·
Bailey-López de Prado (2014) deflated-Sharpe (gelecek genişleme bağlamı).
