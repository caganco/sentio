# RR-Y1-005 — TEST MOTORU TASARIM DOKÜMANI
## Konjuge-Evren Doğrulama Çerçevesi + Genel-Amaçlı Test-Harness'i

**Statü:** TASARIM v0.2 — DONMUŞ (Faz-1 recon işlendi; Faz-2 build'e hazır).
**Sürüm:** v0.2 — 4 Haziran 2026 (v0.1 → v0.2: recon S1-S6 + 2 bonus işlendi; §Değişiklik-kaydı).
**Bağlam:** DEC-045 (Yol-1 pivot-v2, altyapı-önce). Bu doküman RR-Y1-005'in *neyi-niçin* kısmıdır; *nasıl-kodlanacağı* Faz-2 build-specindedir.
**Disiplin-çerçeve:** DISC-6 (disiplini koda-göm), PM-1-yasası, strangler, değişmez-test-dersleri.
**Recon-teyidi:** veri-duvarı YOK; tüm dial'lar uygulanabilir (RR-Y1-005-FAZ1-RECON.md, kanıt dosya:satır).

> Bu doküman aynı zamanda hedeflenen akademik/sektörel-eserin iskeletidir. Hiçbir iddia "ezbere" değil; her metodolojik-primitive kaynağa bağlıdır (López de Prado CPCV/PBO, Bailey deflated-Sharpe, asset-space OOS, cross-sectional-dependence literatürü).

---

## 0. ÖZET (bir paragraf)

Bir prototipin "X_1 evreninde başarılı ve X_2 konjuge-evreninde de başarılı" olması, *belli bir* false-positive sınıfını (evrene-özgü/isme-özgü uydurma) eler — bunu yapabilen, ayarlanabilir, sonradan-denetlenebilir, **genel-amaçlı** bir doğrulama-motoru kuruyoruz. Motorun çekirdek-içgörüsü: **konjuge-bölme tek-bir-şey değildir; prototipin tutunduğu veri-boyutunun fonksiyonudur. Bölmeyi her zaman zamanda değil, overfit'in saklandığı boyutta yap.** Motor tek-evren (X) testleri için de, konjuge (X_1/X_2) testleri için de aynı altyapıyla çalışır; konjuge sadece bir *moddur*.

---

## 1. AMAÇ VE KAPSAM

### 1.1 Ne kuruyoruz
Ayarlanabilir-parametreli (config-dosyası, koda-gömülü-değil), esnek (yeni prototip ucuza takılır), endüstri-seviyesi, **sonradan-denetlenebilir** bir test-harness'i. UI sonraki-faz (motor önce, arayüz üstüne).

### 1.2 Genel-amaçlılık (kritik mimari-şart)
Motor, *tüm-veri* için tek bir doğrulama-aracıdır:
- **Tek-evren modu (X):** klasik validation — bir prototipi tüm-evrende, temporal-CPCV ile sına.
- **Konjuge modu (X_1/X_2):** evreni bölüp prototipi bir-yarıda seç, diğer-yarıda doğrula.

İkisi de aynı çekirdeği kullanır: `harness(panel, sinyal, split_spec, dial_config) → çıktı-vektörü`. Fark yalnızca `split_spec`'tedir. **Motor PARALLEL kurulur** (mevcut committed-motorları sarmalamaz; primitiflerini read-only tüketir — §9, S2).

### 1.3 Kapsam-dışı (bilinçli)
- Edge-avı **değil** (DEC-045, C10-yasağı). Bu motor alet; izin-belgesi değil. Mezarlık-ipliği bu motordan geçmek, ipliği AÇMAZ.
- Rejim-tespiti **motorun-işi-değil** (§4.3). Rejim manuel-girdi.

---

## 2. KONJUGE-EVREN NE YAPAR, NE YAPAMAZ (dürüst-sınırlar)

Bu bölüm dokümanın omurgasıdır; abartılı-iddiadan kaçınmak motorun değerini korur.

### 2.1 Yapar
- **İsme-/evrene-özgü uydurmayı eler.** Prototip X_1'deki spesifik tickerlara/gözlemlere uyduruysa, ayrık X_2'de düşer. En sık ve en ucuz-yakalanan false-positive sınıfı → en yüksek pratik-değer.
- **Garden-of-forking-paths'i ölçer.** Çoklu cut/konfig denemesi → PBO ile fiyatlanır (§4).

### 2.2 Yapamaz (ve neden — masada tutuyoruz)
- **Rejim-bağımsızlığı kanıtlayamaz.** BIST 2019-2026 tek-rejime-yakın; "içkin-edge" ile "bu-rejimde-şanslı" tek-rejim-içinde matematiksel-olarak ayrışmaz. **AMA bu artık kusur değil:** rejime-özgü-edge'i meşru sayıyoruz (§4.3). Motor "regime-R'de gerçek" der, "her-zaman gerçek" demez.
- **Cross-sectional-bağımlılığı tek-başına çözemez.** İsim-bölmesinde iki-yarı ortak-faktörlerle (piyasa-betası, sektör-eş-hareketi, rejim-şoku) kuplajlıdır — literatür: hisse-getirilerinde cross-sectional-bağımlılık baskındır. Sonuç: "edge" aslında ortak-faktöre-biniyorsa iki-yarı da gösterir → "konjuge-uyum" gerçek-idiyosenkratik-edge değil paylaşılan-faktör-kanıtı olur. → **Zorunlu önlem: bölmeden-önce faktör-nötrleme** (§3.5).

### 2.3 Çerçeve-kilidi (değişmez)
Sinyal "sürekli-forward-tahmin" (N≈gözlem, test-edilebilir) çerçevesinde test edilir; "rejim/epizod-flip-bahsi" (N≈epizod, ölçülemez) çerçevesinde **değil**. C9-extreme-tail bu yüzden ölçülemez-prior rafında kalır.

---

## 3. SPLIT-TAKSONOMİSİ (çekirdek-katkı)

### 3.1 Temel-ilke
> **Bölmeyi, overfit'in saklandığı boyutta yap.** Varsayılan-olarak-zamanda-değil.

Overfit'in saklandığı boyut, prototipin-neye-tutunduğunun fonksiyonudur. Tek "konjuge evren" yok; prototip-tipine göre split-modu seçilir ve **Stage-0'da önceden-beyan** edilir.

### 3.2 İçsel-gerilim (her tasarımın çözmesi gereken)
**Doku-benzerliği ↔ bağımsızlık çelişir:**
- Bitişik (X_1=gün k, X_2=gün k+1): doku maksimum, bağımsızlık sıfır → olgu sınıra-taşar, otokorelasyon-sızar. **En kötü split.**
- Uzak: bağımsızlık var, doku/rejim farklı → "n=1 rejim" duvarı.

Çözüm split-boyutunu değiştirmek (zaman yerine isim), gerektiğinde embargo, ve bağımsızlığı **ölçmek-varsaymamak** (§4).

### 3.3 MOD A — İsim-bölmesi (cross-sectional prototipler)
**Ne zaman:** prototip isimleri sıralıyor/seçiyorsa (faktör-tilt, rank-IC tabanlı seçim).
**Nasıl:** X_1 = isimlerin yarısı, X_2 = diğer-yarısı, **ikisi de aynı zaman-diliminde**.
**Neyi öldürür:** isme-özgü uydurma, spesifik-ticker data-snooping'i.
**Avantaj:** zaman-sınırı yok → olgu-taşması-problemi *doğmaz*. Doku birebir (aynı rejim, aynı mikroyapı).
**İçkin-zaaf:** cross-sectional-bağımlılık (§2.2) → faktör-nötrleme zorunlu (§3.5).
**Yöntem-zemini:** asset-space out-of-sample (faktörü eğitim-isimlerinde seç, kalan-isimlerde değerlendir) — yerleşik.
**Bölme-kuralı (Stage-0'da donar):** rastgele-yarı (seed-sabit, çok-tekrar) **veya** nötr-kritere-göre-yarı (likidite-eşleştirilmiş çiftler). Alfabetik/sıra-tabanlı bölme YASAK (gizli-yapı sızdırır).
**Fizibilite (recon B7):** likit-floor (trailing-63g median value_tl ≥ 1e7) → ay-başına min=44/median=77 isim; ikiye-bölününce ~38/arm. Tüm-isim → ~236/arm.
**Sort-depth (recon S5 — yeni dial #8):** 1e7-floor'da decile-sortlar gürültülü (~4 isim/decile). **Kural: split-arm-floor + sort-depth Stage-0'da DONAR** — gürültü-azaltmak için tercile/top-N-by-ADV (her-arm ≥50 isim) prototip-tipine-göre **sonuç-öncesi** seçilir, sonuca-bakıp-değil (DISC-3, post-hoc-kilidi).

### 3.4 MOD B — Temporal-bölme + purge/embargo (timing prototipleri)
**Ne zaman:** prototip bir zaman-serisi sinyaliyse ("bu ay re-tilt").
**Nasıl:** CPCV — zamanı N ardışık-bloğa böl, kombinatoryel train/test yolları üret, purge + embargo uygula.
**Neyi öldürür:** zaman-spesifik şans; tek-path-yüksek-varyansı.
**İçkin-zaaf:** olgu-taşması GERÇEK → embargo onu yönetir.
**Embargo-uzunluğu (h) — recon S4 (DOĞRULANDI, tek-sabit-değil):** h := **sinyalin construction-window'u** (h≥1), tek-sayı-değil sinyale-özgü. Ölçüm (60 likit isim, günlük ACF): günlük-clipped-getiri lag1 +0.099 → ~1-2g söner (h≈1); 21g-trailing-momentum → ~21g söner (h≈window). AR(h) altında train↔test kovaryansı→0.
**Sınır:** uzun-rejim-taşması embargo'yla kapanmaz → rejim-içi-kalıcılık test edilir, rejim-bağımsızlık değil (§4.3, meşru).
**Fizibilite (recon B9):** günlük obs=1848 → N=10-12, k=2 → 45-66 path, CPCV/PBO sağlıklı. Aylık: 88 obs → güç-fakiri (§3.6).

### 3.5 Faktör-nötrleme (Mod-A için zorunlu, Mod-B için opsiyonel)
İsim-bölmesi geçerli-olsun diye, bölmeden-önce getiriler bilinen-ortak-faktörlerden arındırılır. Spesifikasyon Stage-0'da donar.
**Fizibilite (recon B8):** market-beta nötrleme (zorunlu-minimum) → `exposure_d187_xu100` ile GÜNLÜK tam-feasible. Size (`fundamentals.mktval`), sektör (degoran arşivi 2019-07+, PIT), value (pe/pbv/bm/ey/dy) → AYLIK mevcut. Derinlik (market-only vs +size+sektör) güce-bağlı dial-kararı, veri-sorunu-değil. Sektör 2019-07-başlangıç → sektör-nötr testler effective-start 2019-07 (ya da ilk-6-ay market-only).
**Getiri-tabanı (recon C5 — kalite-kazanımı):** Mod-A getirileri **total-return** (`tr_index_gross/net`, temettü-dahil, per-isim mevcut) üzerinden kurulur — price-only-sapmasını önler (D-211/213'ün yaşadığı sorun).

### 3.6 Frekans-uyarlaması (recon S6 — güçlendirildi)
| Frekans | Gözlem | Mod-kuralı |
|---------|--------|-----------|
| Günlük | 1848 obs / bol | A **veya** B (ikisi de uygulanabilir) |
| Aylık | 88 obs / az | **A ZORUNLU** — temporal-CPCV güvenilmez (güç-fakiri); isim-bölmesi yükü-taşır |

Senin günlük-örneğinin doğru-cevabı: **X_1/X_2 = ardışık-günler DEĞİL.** Cross-sectional ise aynı-günler-ayrı-isimler (Mod A); timing ise embargolu-bloklar (Mod B, bitişik-değil).

### 3.7 Karar-tablosu (prototip → split-modu)
| Prototip tutunma-noktası | Split-modu | Bağımsızlık-boyutu | Zorunlu-önlem |
|--------------------------|-----------|--------------------|----------------|
| İsim-sıralama (cross-sectional) | A | isim | faktör-nötrleme + sort-depth-freeze |
| Zaman-serisi tetikçi (timing) | B | zaman | purge + embargo (h=construction-window) |
| Panel (hem-isim-hem-zaman) | A+B birleşik | her-iki | nötrleme + embargo |

---

## 4. BAĞIMSIZLIK VE ANLAMLILIK (ölçülür, varsayılmaz)

Motor "ne-derece-anlamlı"yı sayı-olarak raporlar:

### 4.1 PBO (Probability of Backtest Overfitting)
Bailey–López de Prado, CSCV: *in-sample'da-en-iyi-çıkan kuralın OOS'ta medyan-altına-düşme olasılığı.* Bağımlılık-yapısını fiyatlar. Olgu-taşırsa/fold-örtüşürse PBO yükselir → "11/11≠11-bağımsız-kanıt" otomatik-cezalanır.

### 4.2 Deflated-Sharpe (DSR)
Bailey–López de Prado: Sharpe'ı (a) denenen-konfigürasyon-sayısına, (b) örneklem-uzunluğuna, (c) çarpıklık/basıklığa göre indirir. Çoklu-test-düzeltmesinin Sharpe-versiyonu. `denenen_konfig_sayisi` Stage-0'da dürüst-bildirilir.

### 4.3 Rejim — manuel-girdi, motor-tespiti-değil (S#14 düzeltmesi)
Edge'in her-rejimde-stabil-olması **gerekmez**; rejime-özgü-edge meşru. Rejim-tespiti sen+ben+TCMB+ekonomist ile, manuel, belli-frekansta → motora **etiket-olarak girer** (input-kolon). Prototip Stage-0'da hedef-kapsamını beyan eder (regime-R-hedefli / agnostik). Motor per-rejim performans raporlar; yapısal-kırılma "geçilmesi-zorunlu-bar" DEĞİL.
**Dürüst-kalıntı (masada):** rejime-özgü edge'in canlı-değeri, manuel-rejim-çağrının doğruluğuna koşulludur. maintainer-üstlenimi; motor-iddiası-değil.

### 4.4 Cross-sectional-bağımlılık ölçümü (Mod-A için)
İki isim-yarısının nötrleme-sonrası artık-getirileri arasındaki kalıntı-korelasyon raporlanır. Yüksekse konjuge-uyum şüpheli → çıktıda kırmızı-bayrak.

---

## 5. AYARLANABİLİR DIAL'LAR (kim-donar)

| # | Dial | Kim-karar | Donmuş-default / kaynak |
|---|------|-----------|--------------------------|
| 1 | ψ (durağan-sayılan-özellik) | SEN (Stage-0) | rank-IC kararlılığı (öneri); işaret-çok-gevşek, büyüklük-çok-sıkı |
| 2 | Split-modu (A/B/A+B) | Stage-0 (prototip-tipi) | karar-tablosu §3.7 (aylık→A zorunlu) |
| 3 | Faktör-nötrleme derinliği | Stage-0 | en-az market-beta (Mod-A zorunlu); +size/sektör/value opsiyonel |
| 4 | Embargo (h) | arastirma katmani-ölçer / Stage-0 | **h := sinyal-construction-window (h≥1), sinyale-özgü** (tek-sayı-değil) |
| 5 | CPCV (N,k) + PBO | düz-uygula | günlük N=10-12,k=2 (45-66 path); aylık ince |
| 6 | DSR | düz-uygula | Bailey–LdP formül |
| 7 | Cut-policy ailesi (P) | düz-uygula | {anchored, rolling, expanding} ızgara, hepsi raporlanır |
| 8 | **Split-arm-floor + sort-depth** | **Stage-0 (post-hoc-kilidi)** | likidite-floor + tercile/top-N (her-arm ≥50); sonuç-öncesi-donar |

**Plato-ilkesi (backtest-expert):** dial'lar tek-optimal-tepe değil, geniş-aralıkta-stabil olmalı. Motor parametre-duyarlılığını raporlar; dar-tepe = curve-fit-bayrağı.

**post-hoc-yasağı:** tüm eşik/keep-bar/ψ/split-modu/sort-depth sonuç-ÖNCESİ donar (Stage-0). Sonuca-bakıp-gevşetme guard-RAISE eder.

---

## 6. STAGE-0 ÖN-KAYIT ŞEMASI (recon S3 — JSON, additive-yeni + content-hash-guard)

Mevcut Stage-0'lar freeform-JSON; tipli-şema yok. §6 = **additive-yeni JSON şeması** + küçük validator + STAGE0_d213'ün content-hash snapshot-guard kalıbı (anti-slop'a birebir hizmet). Dosya-yoksa motor KOŞMAYI-REDDEDER (d213-precedent).

```json
{
  "prototip_id": "RR-Y1-007-iplikadi",
  "hipotez": "tek-cumle edge tanimi",
  "tutunma_noktasi": "cross_sectional | timing | panel",
  "split_modu": "A | B | A+B",
  "psi": "rank_ic",
  "faktor_notrleme": ["market"],
  "embargo_h": "construction_window",
  "split_arm_floor": 1e7,
  "sort_depth": "tercile | topN",
  "hedef_rejim": "regime_R | agnostic",
  "frekans": "daily | monthly",
  "getiri_tabani": "total_return",
  "keep_bar": { "pbo_max": null, "dsr_min": null },
  "denenen_konfig_sayisi": 1,
  "frozen_before_results": true,
  "date_frozen": "YYYY-MM-DD",
  "snapshots_content_hash_sha256_prefix": "...",
  "strangler_constraints": "committed-motorlar-dokunulmaz"
}
```

---

## 7. ÇIKTI-VEKTÖRÜ (pass/fail değil — vektör)

- gross / net / cost / tax getiri (realistic_cost D-207 via `clib.per_name_round_trip`, quoted-primary, FIDELITY)
- **total-return-bazlı** (tr_index, temettü-dahil) — price-only-değil
- adil-null karşılaştırması + mirror
- relative-benchmark (> max(TÜFE, TLREF), reel-deflate)
- PBO · cut-ailesi-üzerinde-deflate-edilmiş-OOS-t · DSR
- konjuge-uyum (X_1↔X_2 ψ-tutarlılığı) + kalıntı-cross-sectional-korelasyon (§4.4)
- per-rejim ayrışım (manuel-etikete göre)
- parametre-platosu-haritası (duyarlılık)

---

## 8. ANTI-SLOP GARANTİLERİ (sonradan-denetlenebilirlik)

En-tehlikeli hata-türü **sessiz-hata** — kod çökmez, sonuç-üretir, ama purge'daki off-by-one sızıntıyı-geri-getirir, sonuç sahte-temizdir. Üç-katman:

### 8.1 Golden-fixture (recon A2 — DETERMİNİSTİK, hazır)
Motor, C12'nin BİLİNEN sonuçlarını byte-yeniden-üretmeli. Recon kesin-sayıları pinledi (ALL): `gross_active_ann=+0.226676`, gross `NW-t=+6.928`, `net_active_ann=-0.220398`, `cc_cont` 11/11-fold, `n_pooled_days=1375`, `mean_rt_bps=46.78`. Null-bacağı seed-pinli (`c12...py:250 NULL_SEED+s`) → null-percentile dahil tekrar-üretilebilir.
**Kritik (recon A2):** fixture kendi VERİ-KAYNAĞINI pinler — `data/snapshots/trend_v1_ohlcv...parquet` (88 survivor) + content-hash; **clean_universe panelini DEĞİL.**

### 8.2 Synthetic-null
Random-walk verisinde PBO-yüksek + DSR-ölü çıkmalı (López de Prado sağlamlık-kontrolü). Çıkmıyorsa motor yalan-söylüyor.

### 8.3 Config-şeffaflığı
Her dial config-dosyasında, koda-gömülü-değil → 6-ay-sonra "embargo-kaçtı, hangi-mod, hangi-nötrleme, hangi-rejim-etiketi, sort-depth-ne" görülebilir.

DISC-6 (koda-göm): Stage-0-freeze + purge/embargo + çoklu-test-düzeltmesi motorun-içinde-otomatik; maintainer-freni-değil altyapı-garantisi.

---

## 9. MİMARİ (genel-motor — recon S1/S2)

```
harness(
    panel,        # clean_universe + snapshots PARQUET KATMANI (DataHub DEGIL — S1)
                  #   clean_universe/adjusted_prices_2019_2026.parquet (681 isim/1848 gun, LONG sema,
                  #   tr_index_gross/net dahil); snapshots/* (OHLCV/exposure/makro/earnings)
                  #   survivorship-temiz: 73 delisted in-sample korunmus; pit_membership PIT-uyelik
    sinyal,       # prototip — zero-discretion, kurallar tam-belirli (backtest-expert)
    split_spec,   # Stage-0'dan: mod A/B/A+B + parametreler
    dial_config   # §5 (8 dial)
) -> ciktivektoru  # §7
```

- **PARALLEL kurulur (S2):** sarmalanacak tek "5-gate harness" YOK ("beş-duvar" disiplin, per-script). Motor primitifleri **read-only tüketir**: `clib` (load_panels/liquid_at/continuous_basket/per_name_round_trip/sim_*/real_cagr) + `eng` (clean_universe/monthly_rebalance) + `d204` (per_stock_cost_panel) + `realistic_cost` (D-207) + `c9` (NW-t/binom). Yeni `panel/sinyal/split_spec/dial_config → çıktıvektörü` arayüzü yeni-yazılır.
- **Veri-arayüzü (S1):** genelleşmiş `load_panels` adaptörü; frekans-dönüşümü motorun-kendi-adaptörü (datahub-özelliği-değil).
- **Strangler:** committed-motorlar (D-203..213 + C7/C8/C9) KIRILMAZ; yeni-motor paralel, hiçbir committed-dosyaya-dokunmaz.

---

## 10. DİSİPLİN-BAĞLANTISI (değişmez kontroller)

- **PM-1-yasası:** motor hiçbir sinyali nakit-gate olarak değerlendirmez; boşta=tam-yatırımlı-EW; tetikçi sepet-içi-re-tilt. Nakde-çıkan-prototip guard-RAISE.
- **Değişmez-test-dersleri:** reel(TÜFE-deflate) + relative-benchmark + adil-null + look-ahead-safe(knowable-lag) + survivorship(delisted, 73-in-sample) + composite-optimize-YASAK + alt-grup-dilimleme-YASAK.
- **DEC-039:** ölçülmüş-veri > research > kritik > sezgi.
- **C10-yasağı:** bu motor edge-avı-aracı-değil; yeni-faktör-prototipi açmak hâlâ gerçek-yeni-değer + C10-uyumu ister.

---

## DEĞİŞİKLİK KAYDI (v0.1 → v0.2, geçmiş-silinmez)

- **S1** panel-kaynağı: "datahub (D-199/200)" → "clean_universe + snapshots parquet katmanı"; DataHub canlı-router-only (§1.2, §9).
- **S2** motor PARALLEL (wrap-değil), primitifleri read-only tüketir (§9).
- **S3** Stage-0 §6: YAML→JSON, additive-yeni + content-hash-guard + validator (§6).
- **S4** embargo-h: tek-sayı-değil, sinyal-construction-window (§3.4, §5-dial-4).
- **S5** yeni dial #8: split-arm-floor + sort-depth, Stage-0-donar/post-hoc-kilidi (§3.3, §5).
- **S6** aylık Mod-A "baskın"→"ZORUNLU" (§3.6).
- **C5** getiriler total-return-bazlı (tr_index), price-only-sapma-önlenir (§3.5, §7).
- **A2/C6** golden-fixture kendi-veri-kaynağını+content-hash pinler; sektör-nötr effective-start 2019-07 (§3.5, §8.1).

*RR-Y1-005-TASARIM v0.2 — 4 Haziran 2026, DONMUŞ. Konjuge-bölme overfit-boyutunun-fonksiyonu; motor genel-amaçlı+PARALLEL, konjuge bir-mod; bağımsızlık ölçülür-varsayılmaz; disiplin koda-gömülü; sessiz-hataya-karşı golden-fixture+synthetic-null+config-şeffaflık. Veri-duvarı YOK. Faz-2 build'e hazır.*
