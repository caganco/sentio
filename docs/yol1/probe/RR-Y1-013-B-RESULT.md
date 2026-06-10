# RR-Y1-013-B KAP Katman-2 Gün-Damgası Backfill — Sonuç

> **Veri-backfill görevi — Stage-0 ölçümü DEĞİL.** Hiçbir CAR / getiri / drift /
> Sharpe / t-istatistiği üretilmedi (`no_performance_metrics: true`, özet-JSON'da
> makine-okunur). Tasarım-parametreleri (ilk-duyuru, gün-çözünürlük, seans-kuralı,
> T+2) RR-Y1-013 §2'den devralındı; değiştirilmedi. Karar-ağacı (RR-Y1-013-B §6)
> Orchestrator + Çağan'dadır; aşağıdaki hüküm otomatik-Stage-0-tetikleyici değildir.
>
> Üretici script: `scripts/probe/pead_daydate_backfill.py` (src/engine sıfır-dokunuş;
> RR-Y1-013 probe-scripti/çıktıları değiştirilmedi — üstüne katman). Panel:
> `data/probe/pead_announcement_daydated.parquet` (22.492 olay-anahtarı). Kanıt:
> `data/probe/pead_daydate_backfill_summary.json`. Koşu: 2026-06-10 17:29 UTC.

## Güncellenmiş G1 Hükmü: PASS

§4 barının (sonuç-görmeden donmuş) dört bileşeni tek tek:

| Bar bileşeni | Eşik | Ölçülen | Sonuç |
|---|---|---|---|
| Öncelik-1 (tercile-uç) gün-damgalı | ≥%95 | **737/737 = %100** | ✓ |
| Genişletilmiş spot-kontrol (≥20 isim) exact-day | ≥%90 | **24/24 isim = %100** | ✓ |
| Seans-kuralı tüm-olaylara uygulanmış | zorunlu | 22.492/22.492 (bayrak+D0+T+2 sütunları dolu; takvim-sonu 10/13 kenar-NaT işaretli) | ✓ |
| Restate-ayrımı bütünlüğü | zorunlu | damga = min(publishDate) inşaat-gereği; restate-payı %13,4 ≈ degoran multi-step %11,9; ay-uyuşması %96,6 exact | ✓ |

**G1: CONDITIONAL → PASS.** Frozen T+2 giriş-parametresi artık BIST verisinde
gün-çözünürlüklü, look-ahead-safe uygulanabilir.

## Kanal Mimarisi (koşu-öncesi ölçülen kısıtla belirlendi — sessiz değil, raporlu)

Direktif Adım-2 toplu-çekimi MKK VYK API'ye yazıyordu. Koşu-öncesi keşif ölçümü
bunun **uygulanamaz** olduğunu gösterdi ve roller takas edildi:

- **MKK VYK servis-bandı bulgusu:** liste-API'si `start_index=538004` (KAP-4.0
  tabanı) istense bile şirket-başına en-eskiyi ~2023-02'den başlatıyor;
  `disclosureDetail` vintage-taraması: 2023-03/05/08/11 OK, 2024-03+ ve 2026-05
  **ER005** (bildirim-bulunamadı). Kimlikteki gateway **TEST'tir (apigwdev)** ve
  ~2023-02→2024-02 dar veri-snapshot'ı servis eder. 2019-2022 duyuruları bu
  kanaldan damgalanamaz → MKK-primary tasarım, kapsam-barını yapısal olarak
  geçemezdi.
- **Toplu kaynak → KAP public `byCriteria`** (RR-Y1-011-C/D'de kanıtlanan yol):
  `publishDate` saniye-hassasiyetli PIT, `stockCodes`/`year`/`period` liste-satırında;
  arşiv 2019-öncesine iner. 92 POST ile 2019-01→2026-06 TÜM piyasa FR-sınıfı
  tarandı (64.260 tekil kayıt; 2.000-kayıt-tavanında otomatik pencere-bisection;
  **doygun-gün: 0** → sessiz-kırpma yok).
- **Çapraz-doğrulama → MKK VYK** (kimlikli, ayrı altyapı): aynı `disclosureIndex`
  üzerinden exact-day karşılaştırma (aşağıda).
- **Üçüncü kanal → degoran step-month** (RR-046 devir-envanteri, bağımsız veri-satıcısı):
  tam-panel ay-uyuşması.

## Kapsam Oranları

| Evren | Hedef | Damgalı | Kapsama |
|---|---|---|---|
| **Öncelik-1: tercile-uç (likit∩SUE, fy2019-2025)** | 737 | 737 | **%100** |
| Öncelik-2: tüm SUE-tanımlı (fy2019-2025) | 5.771 | 5.611 | %97,2 |
| Tüm piyasa FR olay-anahtarı (bağlam) | — | 22.492 | 1.085 ticker |

- Öncelik-1'i %97,4'ten %100'e taşıyan düzeltme: KAP `stockCodes` alanının
  **bugünkü (yeniden-adlandırılmış) kodu** retroaktif taşıdığının teşhisi; 6
  doğrulanmış alias (kapTitle-kanıtlı, veri-temizliği): DGNMO→DGKLB, BESLR→KERVT,
  TRALT→KOZAL, TRMET→KOZAA, TRENJ→IPEKE, LRSHO→ITTFH. (Koza/İpek-grubu + İttifak —
  projenin klasik survivorship-isimleri — panelde böylece gün-damgalı.)
- Öncelik-2 kalanı (160 olay, %2,8): alias-haritası yalnız öncelik-1-kritik 6
  çiftle sınırlı tutuldu; kalanın baskın bilinen-nedeni ek ticker-rename'ler +
  takvim-dışı mali-yıl vakaları. Ölçüm-kritik değil; ileride top-up mümkün.

## Genişletilmiş Spot-Kontrol (≥20 isim, exact-day)

24 farklı isim, öncelik-1 olayları; KAP-public `publishDate` vs MKK VYK
`disclosureDetail.time`, **24/24 exact-day eşleşme**. Örneklem MKK'nın çalışan
bandı içinden (2023-04..2023-11; test-gateway kısıtı — aşağıda Bilinen Sınırlar):

| İsim | Dönem | disclosureIndex | KAP-public gün | MKK VYK gün | Eşleşme |
|---|---|---|---|---|---|
| CEMAS | 2023Q3 | 1216745 | 2023-11-09 | 2023-11-09 | ✓ |
| IEYHO | 2023Q3 | 1216742 | 2023-11-09 | 2023-11-09 | ✓ |
| GSDHO | 2023Q3 | 1216718 | 2023-11-09 | 2023-11-09 | ✓ |
| YGYO | 2023Q3 | 1216691 | 2023-11-09 | 2023-11-09 | ✓ |
| IHLAS | 2023Q3 | 1216658 | 2023-11-09 | 2023-11-09 | ✓ |
| SNGYO | 2023Q3 | 1216630 | 2023-11-09 | 2023-11-09 | ✓ |
| HALKB | 2023Q3 | 1216396 | 2023-11-09 | 2023-11-09 | ✓ |
| BERA | 2023Q3 | 1216357 | 2023-11-09 | 2023-11-09 | ✓ |
| ULKER | 2023Q3 | 1216355 | 2023-11-09 | 2023-11-09 | ✓ |
| ADESE | 2023Q3 | 1216060 | 2023-11-08 | 2023-11-08 | ✓ |
| EKGYO | 2023Q3 | 1215962 | 2023-11-08 | 2023-11-08 | ✓ |
| ENKAI | 2023Q3 | 1215954 | 2023-11-08 | 2023-11-08 | ✓ |
| AVOD | 2023Q3 | 1215871 | 2023-11-08 | 2023-11-08 | ✓ |
| PETKM | 2023Q3 | 1215443 | 2023-11-08 | 2023-11-08 | ✓ |
| IHEVA | 2023Q3 | 1215401 | 2023-11-07 | 2023-11-07 | ✓ |
| IHLGM | 2023Q3 | 1215397 | 2023-11-07 | 2023-11-07 | ✓ |
| DOHOL | 2023Q3 | 1215224 | 2023-11-07 | 2023-11-07 | ✓ |
| KATMR | 2023Q3 | 1215183 | 2023-11-07 | 2023-11-07 | ✓ |
| OZKGY | 2023Q3 | 1215171 | 2023-11-07 | 2023-11-07 | ✓ |
| CIMSA | 2023Q3 | 1214655 | 2023-11-06 | 2023-11-06 | ✓ |
| TUKAS | 2023Q3 | 1214570 | 2023-11-06 | 2023-11-06 | ✓ |
| ALBRK | 2023Q3 | 1214072 | 2023-11-03 | 2023-11-03 | ✓ |
| FORMT | 2023Q3 | 1212628 | 2023-10-31 | 2023-10-31 | ✓ |
| RTALB | 2023Q3 | 1212118 | 2023-10-30 | 2023-10-30 | ✓ |

**Üçüncü-kanal (tam-panel ölçek, n=5.611):** degoran step-month vs KAP ilk-duyuru
ayı: **%96,6 exact-month, %98,8 ±1 ay**. RR-Y1-013'ün 5/5 spot bulgusunun
5.611-olaya ölçeklenmiş halidir; ay-proxy ↔ KAP-PIT tutarlılığını bağımsız
veri-satıcısı kanalından doğrular. Kuyruk (fark ≥2 ay: ~%1,2) degoran geç-ingest
imzasıdır; T+2 için belirleyici damga KAP'tır.

## Seans-Kuralı ve T+2 (frozen §2 uygulaması)

- Dağılım: **post_session 19.152 (%85,2)** / in_session 2.885 (%12,8) /
  non_trading_day 455 (%2,0). Mod-saat 18:00. **Seans-kuralı yük-taşıyıcıdır:**
  olayların %87'sinde D0 ≠ yayın-günü; kuralsız panel yaygın look-ahead taşırdı.
- D0 = yayın-günü (seans-içi) veya ertesi-işgünü (≥18:00 / tatil); giriş =
  D0 + 2 işgünü, takvim = clean_universe fiili işlem-günleri (tatil-duyarlılığı
  doğrulandı: THYAO 2019Q2 → D0 Cum 2019-08-09 → giriş 2019-08-16, Kurban-arası
  doğru atlanır).
- Kenar: D0 takvim-sonrası 10 olay, giriş takvim-sonrası 13 olay (2026-05-26
  panel-sonu civarı duyurular) → NaT + sayım raporlu.

## Restate-Ayrımı Bütünlüğü

- Damga = aynı (ticker, yıl, dönem) anahtarındaki FR-bildirimlerinin
  **min(publishDate)**'i (inşaat-gereği ilk-duyuru); sonraki bildirimler
  `restate_step_flag` + `n_filings` + `last_filing_ts` ile ayrı tutulur.
- KAP restate-payı %13,4 ↔ RR-Y1-013 degoran multi-step %11,9 (tutarlı büyüklük;
  KAP-tarafı konsolide/solo çift-dosyalamayı da içerir → üst-sınır).
- Ay-uyuşması %96,6 exact: degoran en-erken-step ayı ile KAP ilk-bildirimi ayı
  örtüşür — en-erken-step seçiminin doğruluğunu tam-panel ölçeğinde doğrular.

## Çıktı Sözleşmesi ve Veri Envanteri

`data/probe/pead_announcement_daydated.parquet` (22.492 satır) — direktif §5
sütun-eşlemesi: `first_announcement_date_day` ✓, `intraday_session_flag` ✓,
`d0`↔D0, `entry_date_t2`↔entry_date_T+2, `restate_step_flag` ✓,
`source_disclosure_index`↔source_api_ref, `fiscal_period` ✓; ek denetim-sütunları:
`first_announcement_ts` (saniye), `n_filings`, `last_filing_ts`, `subject`, `ruleType`.

| Katman | Konum | Not |
|---|---|---|
| Ham KAP-public yanıtları | `data/bist_datastore_archive/kap_fr_daydate_raw/` (91 pencere, .json.gz) | frozen-snapshot; junction'lı ortak arşiv; git-ignored, **CI-dışı** (RR-Y1-011-D recon_cache precedenti) |
| Türetilmiş panel + kanıt | `data/probe/` (parquet + JSON) | commit edilir |

**API istek sayımı:** KAP public **94** POST (92 toplu + 2 şema-keşfi; 0,8 sn/istek
nazik tempo, doygun-gün 0). MKK VYK **~109** çağrı (şema/retention-keşfi 5,
vintage-taraması 8, ilk spot-denemesi 24 — tamamı ER005, bant-keşfine girdi oldu —
ara-koşu 24, kesin-koşu 24, + ara doğrulamalar; test-gateway, 1 istek/sn).

## Süreç-Notu (şeffaflık)

Ara-koşulardan birinde cache-yükleyici, bisect edilen doruk-aylarının
çocuk-pencerelerini atlayarak 64.260 yerine 61.911 kayıt yükledi (sessiz-kırpma).
Hata kayıt-sayısı mutabakatıyla yakalandı, yükleyici düzeltildi; kesin-koşu tam
çekimle birebir aynı tekil-kayıt sayısını (64.260) yeniden üretti. Kırpılmış
ara-koşunun hiçbir çıktısı teslim-artefaktlarına girmedi.

## Bilinen Sınırlar / Uyarılar

1. **MKK çapraz-doğrulama bandı dar:** kimlikteki gateway TEST (apigwdev),
   servis-bandı ~2023-02→2024-02 → spot-örneklem 2023-dönemine yığılı (24 isim,
   tek-çeyrek ağırlıklı). Bant-dışı yıllar için gün-damgası tek-kanal (KAP public)
   + degoran ay-uyuşması (%96,6, n=5.611) ile desteklenir. Prod-gateway kimliği
   gelirse bant genişletilebilir.
2. **Öncelik-2 kalanı 160 olay (%2,8)** damgasız (ek rename/takvim-dışı mali-yıl);
   öncelik-1 %100 olduğundan ölçüm-kritik değil.
3. `restate_step_flag` bildirim-sayısı-tabanlıdır; konsolide/solo çift-dosyalamayı
   da işaretler (restate üst-sınırı).
4. Yarım-gün seanslar (arife) ayrıca modellenmedi; kural frozen haliyle (≥18:00)
   uygulandı.
5. KAP public kanalının kendi yayın-altyapısı tek-kaynaktır; MKK bandı-içi 24/24
   exact-day + degoran ay-kanalı dışında üçüncü bir gün-düzeyi arşivle
   karşılaştırılmadı (PDP = aynı platformun eski adı, ayrı arşiv değil).
6. Görev-kapsamı dışı bırakılanlar: decay-riski, maliyet (D-207 çağrılmadı),
   benchmark-inşası, 2023Q4/2024Q4 olay-sayısı düşüşü kök-nedeni (RR-Y1-013
   listesiyle aynı).
