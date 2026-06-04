# FORWARD DATA-ACQUISITION SPEC -- siradaki-faz (SPEC; CALISTIRILMADI)

Bu bir SPEC'tir, kod-calistirma DEGIL. Ag/auth gerektiren her cekim the maintainer-ONAYI ile yapilir
(repo read-only; otonom-ag-cekimi YAPILMADI). Amac: lab'in vardigi sonucu (L7) eyleme cevirmek.

## Neden bu spec (L7 sayisal-gerekce)
L7 iki-kapi bulgusu: likit-evrende BAGLAYAN kapi = ANLAMLILIK/POWER (maliyet degil). Survivable-arketip
(dusuk-turnover, event-driven, likit, dogru-isaret) DOGRU teshis edildi; eksik = yeterli BAGIMSIZ
gozlem + KESIN-zamanlama. Dolayisiyla siradaki-deger yeni cross-sectional faktor DEGIL; ayni-arketipte
POWER artiran veri: (a) daha-cok bagimsiz olay, (b) gun-damgali kesin-zamanlama (pencere-daraltma),
(c) L6-tipi event icin SURPRIZ-buyuklugu (kosullandirma sinyali).

## Onceliklendirilmis kuyruk (mevcut-infra'yi GENISLET; yeniden-yazma)

### #1 -- DAILY-PEAD: KAP ifsa gun-damgasi (EN-YUKSEK oncelik; infra COGU hazir)
- **Neden**: L3-PEAD null'unun ACIK nedeni AYLIK-cozunurluktu (consume_from_month). KAP ifsa
  gun-damgasi -> GUNLUK kazanc-surpriz event'i -> (i) bagimsiz-gozlem ~4x artar (ceyrek-basi
  cross-section yerine her-ifsa ayri olay), (ii) [t+1, t+K] pencere DAR ve look-ahead-safe.
  Tam-da L7'nin "dusuk-turnover, event-driven, likit, power-artir" receti.
- **Mevcut modul**: `src/data/kap_historical_fetcher.py` (D-170/172) zaten MKK VYK API'den
  per-filing `disclosureDetail` cekiyor; `time` (ifsa-zaman-damgasi) + `period` + XBRL net_income
  ALANLARI MEVCUT. Yani gun-damgasi cikarilabilir -- yeni-scraper gerekmez, var-olani cagir.
- **Gereken alanlar**: per-(ticker, donem): disclosure_date (gun), disclosure_time, net_income,
  revenue. SUE = mevsimsel-rassal-yuruyus (YoY de-cumulated quarterly net-profit degisimi)
  zaten L3'te tanimli -> AYNI SUE, gun-damgali event'e re-map.
- **Look-ahead-safe kayit**: consume = disclosure_date'in BIR-sonraki islem-gunu (ifsa gun-ici
  olabilir; r(t0) kontamine -> giris t0+1). KAP 4.0-oncesi (disclosureIndex<538004) html-only ->
  ATLA (zaten fetcher'da var).
- **Test (siradaki L-track)**: daily-PEAD, long top-SUE likit-tercile vs EW-full, [t+1,+K] dar-pencere,
  D-207 maliyet, olay-clustered t. Beklenti-prior: L7 der ki survivable-arketip ama POWER-sinirli;
  gun-damgali daha-cok-olay 2-sigma sansini ARTIRIR (en-iyi tek-bahis). HONEST: yine de duvar-mumkun.

### #2 -- SURPRIZ-KOSULLU MAKRO: kesin CPI-tarih + actual/forecast + PPK tam-gecmis (orta-yuksek)
- **Neden**: L6 KOSULSUZ ilan-penceresi null'du; drift'i tasiyan-bilesen SURPRIZ (actual-forecast).
  Surpriz-buyuklugu + KESIN-tarih (proxy +/-1-2g smear'i kaldirir) + PPK-gecmis (n=2->~80) ->
  L6'yi kosullu-teste cevirir (XU100 index-timing; dusuk-turnover).
- **Mevcut modul**: `src/data/macro_event_snapshot_builder.py` (RR-046, dates-only rule-proxy),
  `src/data/evds_client.py`, `src/data/tcmb_scraper.py`. GENISLET: kesin-tarih (TUIK Ulusal Veri
  Yayimlama Takvimi) + actual CPI + piyasa-forecast (consensus) + PPK 2019-2025 (TCMB press-release
  recorder / Katman-2 budgeted scrape -- snapshot_builder'in DEFER-notu bunu zaten isaret ediyor).
- **Gereken alanlar**: event_date (exact), event_type, actual, forecast/consensus, surprise=actual-forecast.
- **Look-ahead-safe kayit**: surprise yalniz ilan-ANINDA bilinir -> consume t0+1; forecast ilan-ONCESI
  forward-snapshot olarak KAYDEDILMELI (sonradan-revize edilmemis "vintage" deger). FORWARD-kayit:
  bugun-baslamali (gecmis-consensus geri-uydurulamaz -> dikkat: gecmis icin yalniz revize-edilmemis
  arsiv kullan, yoksa look-ahead).
- **Beklenti-prior**: index-timing; D-211 (yabanci-akim index-timing) NOT-TRADEABLE cikti -> temkinli
  prior. Ama surpriz fiyat-ortogonal farkli-eksen; dusuk-turnover -> denemeye-deger, HONEST-beklenti zayif.

### #3 -- TEFAS fon-akimi + yatirimci-sayisi (orta-dusuk; YENI build)
- **Neden**: 5y bedava retail/kurumsal-akim proxy; hic-denenmemis veri-turu. Index/segment-timing
  veya rejim-overlay sinyali (cross-sectional DEGIL -> cost-magnitude dusuk).
- **Mevcut modul**: YOK (fintables_scraper fundamentals-only). YENI cekim-hatti gerekir (TEFAS
  Takasbank acik-uclu API/CSV). isyatirim_scraper/datastore desenleri sablon-alinabilir.
- **Gereken alanlar**: tarih, fon-kategori (hisse/borc/para-piyasa), net-akim, toplam-AUM,
  yatirimci-sayisi. Look-ahead: TEFAS T+1 yayinlar -> consume T+2 guvenli.
- **Beklenti-prior**: kesif-asamasi; edge-prior bilinmiyor (gercek-yeni-veri). Dusuk-turnover
  overlay olarak L7-go/no-go'ya uyar; ONCE veri-betimleme, sonra Stage-0.

### #4 -- per-stock GUNLUK yabanci-oran paneli (EN-DUSUK; L7-prior olumsuz)
- **Neden-dusuk**: cross-sectional tercile sinyali -> L7 der ki likit'te sign/significance-wall
  cok-muhtemel + turnover-cost. Forward-snapshot gerektirir (anlik-API). Dusuk-beklenti.
- **Mevcut modul**: `src/data/foreign_flow_parser.py` (per-stock-capable; D-211 aggregate kullandi),
  `src/data/viop_takasbank_parser.py`, `src/data/isyatirim_scraper.py`.
- **Karar**: #1-#3 tukenmeden ACILMA (azalan-getiri).

## Disiplin notu
Bu spec'teki HICBIR madde otonom-calistirilmadi (ag/auth + repo-read-only). Her madde icin akis:
the maintainer-onayi -> veri-cekim (mevcut-modul-genislet) -> snapshot (gitignored, force-add) -> Stage-0
DONAR -> olcum (committed-engine zero-touch, strangler) -> HUKUM (TRADEABLE / temiz-arsiv). Sira:
#1 (en-yuksek power-kazanci, infra-hazir) -> #2 -> #3 -> (#4 yalniz gerekirse). Grid-supurme YOK;
her madde tek-on-kayitli-test. Kutlama-yok; sonuc-ne-olursa kaydedilir.
