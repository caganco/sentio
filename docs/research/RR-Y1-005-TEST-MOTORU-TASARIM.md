# RR-Y1-005 — TEST MOTORU TASARIM DOKÜMANI
## Konjuge-Evren Doğrulama Çerçevesi + Genel-Amaçlı Test-Harness'i

**Statü:** TASARIM (Faz-0, kâğıt). arastirma katmani-recon (Faz-1) ve build (Faz-2) öncesi.
**Sürüm:** v0.1 — 4 Haziran 2026
**Bağlam:** DEC-045 (Yol-1 pivot-v2, altyapı-önce). Bu doküman RR-Y1-005'in *neyi-niçin* kısmıdır; *nasıl-kodlanacağı* Faz-1 recon sonrası donar.
**Disiplin-çerçeve:** DISC-6 (disiplini koda-göm), PM-1-yasası, strangler, değişmez-test-dersleri.

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

İkisi de aynı çekirdeği kullanır: `harness(panel, sinyal, split-spec, dial-config) → çıktı-vektörü`. Fark yalnızca `split-spec`'tedir.

### 1.3 Kapsam-dışı (bilinçli)
- Edge-avı **değil** (DEC-045, C10-yasağı). Bu motor alet; izin-belgesi değil. Mezarlık-ipliği bu motordan geçmek, ipliği AÇMAZ.
- Rejim-tespiti **motorun-işi-değil** (aşağıda §4.3). Rejim manuel-girdi.

---

## 2. KONJUGE-EVREN NE YAPAR, NE YAPAMAZ (dürüst-sınırlar)

Bu bölüm dokümanın omurgasıdır; abartılı-iddiadan kaçınmak motorun değerini korur.

### 2.1 Yapar
- **İsme-/evrene-özgü uydurmayı eler.** Prototip X_1'deki spesifik tickerlara/gözlemlere uyduruysa, ayrık X_2'de düşer. Bu, en sık ve en ucuz-yakalanan false-positive sınıfıdır → en yüksek pratik-değer.
- **Garden-of-forking-paths'i ölçer.** Çoklu cut/konfig denemesi → PBO ile fiyatlanır (§4).

### 2.2 Yapamaz (ve neden — bunu masada tutuyoruz)
- **Rejim-bağımsızlığı kanıtlayamaz.** BIST 2019-2026 tek-rejime-yakın; "içkin-edge" ile "bu-rejimde-şanslı" tek-rejim-içinde matematiksel-olarak ayrışmaz. **AMA bu artık bir kusur değil:** rejime-özgü-edge'i meşru sayıyoruz (§4.3). Motor "regime-R'de gerçek" der, "her-zaman gerçek" demez.
- **Cross-sectional-bağımlılığı tek-başına çözemez.** İsim-bölmesinde iki-yarı ortak-faktörlerle (piyasa-betası, sektör-eş-hareketi, rejim-şoku) kuplajlıdır — literatür: hisse-getirilerinde cross-sectional-bağımlılık baskındır. Sonuç: eğer "edge" aslında ortak-faktöre-biniyorsa, iki-yarı da gösterir ve "konjuge-uyum" gerçek-idiyosenkratik-edge kanıtı **değil** paylaşılan-faktör-kanıtı olur. → **Zorunlu önlem: bölmeden-önce faktör-nötrleme** (§3.5).

### 2.3 Çerçeve-kilidi (değişmez)
Sinyal "sürekli-forward-tahmin" (N≈gözlem, test-edilebilir) çerçevesinde test edilir; "rejim/epizod-flip-bahsi" (N≈epizod, ölçülemez) çerçevesinde **değil**. C9-extreme-tail bu yüzden ölçülemez-prior rafında kalır.

---

## 3. SPLIT-TAKSONOMİSİ (çekirdek-katkı)

### 3.1 Temel-ilke
> **Bölmeyi, overfit'in saklandığı boyutta yap.** Varsayılan-olarak-zamanda-değil.

Overfit'in saklandığı boyut, prototipin-neye-tutunduğunun fonksiyonudur. Bu yüzden tek "konjuge evren" yok; prototip-tipine göre split-modu seçilir ve **Stage-0'da önceden-beyan** edilir.

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
**Bölme-kuralı (Stage-0'da donar):** rastgele-yarı (seed-sabit, çok-tekrar) **veya** nötr-kritere-göre-yarı (ör. likidite-eşleştirilmiş çiftler). Alfabetik/sıra-tabanlı bölme YASAK (gizli-yapı sızdırır).

### 3.4 MOD B — Temporal-bölme + purge/embargo (timing prototipleri)
**Ne zaman:** prototip bir zaman-serisi sinyaliyse ("bu ay re-tilt", "bu hafta ağırlık-artır").
**Nasıl:** CPCV — zamanı N ardışık-bloğa böl, bloklardan kombinatoryel train/test yolları üret, purge + embargo uygula.
**Neyi öldürür:** zaman-spesifik şans; tek-path-yüksek-varyansı.
**İçkin-zaaf:** olgu-taşması GERÇEK → embargo onu yönetir.
**Embargo-uzunluğu (h):** sinyalin otokorelasyon-sönüm-uzunluğu kadar. Ölçülen-sayı (recon), tartışma-değil. AR(h) altında train↔test kovaryansı→0.
**Sınır:** uzun-rejim-taşması embargo'yla kapanmaz → rejim-içi-kalıcılık test edilir, rejim-bağımsızlık değil (§4.3, meşru).

### 3.5 Faktör-nötrleme (Mod-A için zorunlu, Mod-B için opsiyonel)
İsim-bölmesi geçerli-olsun diye, bölmeden-önce getiriler bilinen-ortak-faktörlerden arındırılır (en-az: piyasa-betası; mümkünse: sektör, büyüklük). Aksi-halde konjuge-uyum paylaşılan-faktörü-yakalar, edge'i-değil. Nötrleme-spesifikasyonu Stage-0'da donar.

### 3.6 Frekans-uyarlaması
| Frekans | Gözlem-bolluğu | Baskın-mod |
|---------|----------------|------------|
| Günlük | bol | A veya B (ikisi de uygulanabilir) |
| Aylık | az | A (isim-bölmesi yükü-taşır; temporal-bölme açlıktan-ölür) |

Senin günlük-örneğinin doğru-cevabı: **X_1/X_2 = ardışık-günler DEĞİL.** Cross-sectional ise aynı-günler-ayrı-isimler (Mod A); timing ise embargolu-bloklar (Mod B, bitişik-değil).

### 3.7 Karar-tablosu (prototip → split-modu)
| Prototip tutunma-noktası | Split-modu | Bağımsızlık-boyutu | Zorunlu-önlem |
|--------------------------|-----------|--------------------|----------------|
| İsim-sıralama (cross-sectional) | A | isim | faktör-nötrleme |
| Zaman-serisi tetikçi (timing) | B | zaman | purge + embargo |
| Panel (hem-isim-hem-zaman) | A+B birleşik | her-iki | nötrleme + embargo |

---

## 4. BAĞIMSIZLIK VE ANLAMLILIK (ölçülür, varsayılmaz)

"Konjuge-test ne-derece-anlamlı?" sorusunun cevabı: efektif-bağımsızlık kadar. Motor bunu sayı-olarak raporlar:

### 4.1 PBO (Probability of Backtest Overfitting)
Bailey–López de Prado, CSCV ile: *in-sample'da-en-iyi-çıkan kuralın OOS'ta medyan-altına-düşme olasılığı.* Bağımlılık-yapısını fiyatlar. Olgu-taşırsa/fold-örtüşürse PBO yükselir → "11/11≠11-bağımsız-kanıt" otomatik-cezalanır.

### 4.2 Deflated-Sharpe (DSR)
Bailey–López de Prado: Sharpe'ı (a) denenen-konfigürasyon-sayısına, (b) örneklem-uzunluğuna, (c) dağılım-çarpıklık/basıklığına göre indirir. Çoklu-test-düzeltmesinin Sharpe-versiyonu.

### 4.3 Rejim — manuel-girdi, motor-tespiti-değil (maintainer-düzeltmesi, S#14)
Edge'in her-rejimde-stabil-olması **gerekmez**; rejime-özgü-edge meşru ve iş-görür. Rejim-tespiti sen+ben+TCMB+ekonomist ile, manuel, belli-frekansta yapılır → motora **etiket-olarak girer** (input-kolon). Prototip Stage-0'da hedef-kapsamını beyan eder (regime-R-hedefli / regime-agnostik). Motor per-rejim performans raporlar; yapısal-kırılma "geçilmesi-zorunlu-bar" DEĞİL.
**Dürüst-kalıntı (masada):** rejime-özgü doğrulanmış edge'in canlı-değeri, manuel-rejim-çağrının doğruluğuna koşulludur. Bu maintainer-üstlenimi; motor-iddiası-değil.

### 4.4 Cross-sectional-bağımlılık ölçümü (Mod-A için)
İki isim-yarısının artık-getirileri arasındaki kalıntı-korelasyon raporlanır (nötrleme-sonrası). Yüksekse konjuge-uyum şüpheli → çıktıda kırmızı-bayrak.

---

## 5. AYARLANABİLİR DIAL'LAR (kim-donar)

| # | Dial | Kim-karar | Donmuş-default / kaynak |
|---|------|-----------|--------------------------|
| 1 | ψ (durağan-sayılan-özellik) | **SEN** (Stage-0) | rank-IC kararlılığı (öneri); işaret-çok-gevşek, büyüklük-çok-sıkı |
| 2 | Split-modu (A/B/A+B) | Stage-0 (prototip-tipi belirler) | karar-tablosu §3.7 |
| 3 | Faktör-nötrleme | Stage-0 | en-az piyasa-betası (Mod-A zorunlu) |
| 4 | Embargo (h) | arastirma katmani-ölçer (recon) | otokorelasyon-sönüm-uzunluğu |
| 5 | CPCV (N,k) + PBO | düz-uygula | López de Prado default |
| 6 | DSR | düz-uygula | Bailey–LdP formül |
| 7 | Cut-policy ailesi (P) | düz-uygula | {anchored, rolling, expanding} ızgara, hepsi raporlanır |

**Plato-ilkesi (backtest-expert):** dial'lar tek-optimal-noktada-tepe değil, geniş-aralıkta-stabil olmalı. Motor parametre-duyarlılığını raporlar; dar-tepe = curve-fit-bayrağı.

**post-hoc-yasağı:** tüm eşik/keep-bar/ψ/split-modu sonuç-ÖNCESİ donar (Stage-0). Sonuca-bakıp-gevşetme guard-RAISE eder.

---

## 6. STAGE-0 ÖN-KAYIT ŞEMASI (prototip-başına, sonuç-öncesi-donar)

Her prototip koşmadan önce şunu beyan eder (makine-okur, motor split-modunu buradan seçer):

```yaml
prototip_id: <ör. RR-Y1-007-iplikadı>      # C10-yasağı: mezarlık-ipliği-açmaz
hipotez: <tek-cümle edge tanımı>            # backtest-expert: net-değilse koşma
tutunma_noktasi: cross_sectional | timing | panel
split_modu: A | B | A+B                      # tutunma'dan türer
psi: sign | rank_ic | magnitude              # default rank_ic
faktor_notrleme: [market] | [market,sector,size]
embargo_h: <recon-ölçümü>                    # Mod-B/panel için
hedef_rejim: regime_R | agnostic             # manuel-etiket-kapsamı
frekans: daily | monthly
keep_bar: <donmuş-eşik-vektörü>              # PBO-üst-sınır, DSR-alt-sınır, vb.
denenen_konfig_sayisi: <DSR-için bildirilir> # dürüst-sayım
```

---

## 7. ÇIKTI-VEKTÖRÜ (pass/fail değil — vektör)

Motor ikili-hüküm vermez; karar-vektörü üretir (yorum bizim):
- gross / net / cost / tax getiri (realistic_cost D-207, FIDELITY)
- adil-null karşılaştırması + mirror
- relative-benchmark (> max(TÜFE, TLREF), reel-deflate)
- PBO · cut-ailesi-üzerinde-deflate-edilmiş-OOS-t · DSR
- konjuge-uyum (X_1↔X_2 ψ-tutarlılığı) + kalıntı-cross-sectional-korelasyon
- per-rejim ayrışım (manuel-etikete göre)
- parametre-platosu-haritası (duyarlılık)

---

## 8. ANTI-SLOP GARANTİLERİ (sonradan-denetlenebilirlik)

Araştırmadaki en-kritik-uyarı: bu makinenin en-tehlikeli hata-türü **sessiz-hata** — kod çökmez, sonuç-üretir, ama purge'daki off-by-one sızıntıyı-geri-getirmiştir ve sonuç sahte-temizdir. "AI-slop üretmeyelim"in teknik-karşılığı bu üç-katman:

1. **Golden-fixture testi:** motor, cc_cont/C12'nin BİLİNEN sonuçlarını yeniden-üretmeli. Üretemezse motor-bozuk. (cc_cont/C12 burada yalnız *bilinen-cevap*; mezarlık-ipliğini-açmaz, C10-korunur.)
2. **Synthetic-null testi:** random-walk verisinde PBO-yüksek + DSR-ölü çıkmalı (López de Prado'nun kendi sağlamlık-kontrolü). Çıkmıyorsa motor yalan-söylüyor.
3. **Config-şeffaflığı:** her dial config-dosyasında, koda-gömülü-değil → 6-ay-sonra açıp "embargo-kaçtı, hangi-mod, hangi-nötrleme, hangi-rejim-etiketi" görebilirsin.

DISC-6 (koda-göm): Stage-0-freeze + purge/embargo + çoklu-test-düzeltmesi motorun-içinde-otomatik; maintainer-freni-değil altyapı-garantisi.

---

## 9. MİMARİ (genel-motor)

```
harness(
    panel,        # mevcut datahub'dan (D-199/200), survivorship-temiz, look-ahead-safe
    sinyal,       # prototip — zero-discretion, kurallar tam-belirli (backtest-expert §2)
    split_spec,   # Stage-0'dan: mod A/B/A+B + parametreler
    dial_config   # §5
) -> ciktivektoru  # §7
```

- **Tek-evren X** = split_spec sadece temporal-CPCV.
- **Konjuge X_1/X_2** = split_spec isim-bölmesi (veya panel).
- Datahub MEVCUT (3-gün-önce); motor onu *tüketir*, yeniden-kurmaz. Recon datahub-arayüzünü envanterler.
- Strangler: committed-motorlar (D-203..213 + C7/C8/C9) KIRILMAZ; bu yeni-motor onların-üstünde, eski-harness'i değiştirmeden.

---

## 10. AÇIK-TASARIM-SORULARI (Faz-1 recon çözer / beraber-kararlaştırırız)

**Recon (arastirma katmani) çözer — codebase/veri-fizibilite:**
- Mevcut 5-gate harness'in arayüzü; yeni-motor onu sarmalayabilir mi yoksa paralel-mi?
- cc_cont/C12 sonuçları golden-fixture olarak erişilebilir/donmuş-mu?
- Embargo-h için otokorelasyon-sönümü hangi-sinyalde-ne (ölçüm).
- İsim-bölmesi için: dönem-başına-isim-sayısı yeterli-mi (bölünce her-yarı istatistiksel-anlamlı-mı)?
- Faktör-nötrleme için piyasa/sektör/büyüklük serileri datahub'da-var-mı?
- Datahub-arayüzü: panel hangi-formatta, frekans-dönüşümü nasıl.

**Beraber-kararlaştırırız (recon-sonrası):**
- ψ kesinleşmesi (rank-IC default'u recon-sayılarıyla teyit).
- Nötrleme-derinliği (sadece-market mi, +sektör/büyüklük mü) — veri-fizibiliteye-bağlı.
- CPCV (N,k) somut-değerleri (gözlem-sayısına-bağlı).

---

## 11. DİSİPLİN-BAĞLANTISI (değişmez kontroller)

- **PM-1-yasası:** motor hiçbir sinyali nakit-gate olarak değerlendirmez; boşta=tam-yatırımlı-EW; tetikçi sepet-içi-re-tilt. Nakde-çıkan-prototip guard-RAISE.
- **Değişmez-test-dersleri:** reel(TÜFE-deflate) + relative-benchmark + adil-null + look-ahead-safe(knowable-lag) + survivorship(delisted, datahub-1987) + composite-optimize-YASAK + alt-grup-dilimleme-YASAK.
- **DEC-039:** ölçülmüş-veri > research > kritik > sezgi.
- **C10-yasağı:** bu motor edge-avı-aracı-değil; yeni-faktör-prototipi açmak hâlâ gerçek-yeni-değer + C10-uyumu ister.

---

*RR-Y1-005-TASARIM v0.1 — 4 Haziran 2026. Konjuge-bölme overfit-boyutunun-fonksiyonu; motor genel-amaçlı, konjuge bir-mod; bağımsızlık ölçülür-varsayılmaz; disiplin koda-gömülü; sessiz-hataya-karşı golden-fixture+synthetic-null+config-şeffaflık. Faz-1 recon bekliyor.*
