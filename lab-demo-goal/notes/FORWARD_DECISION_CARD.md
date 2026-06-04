# FORWARD DECISION CARD -- daily-PEAD (KAP gun-damgasi) go/no-go

Tek-sayfa karar-karti. the maintainer icin: otonom-faz mevcut-veride TUKENDI; geriye TEK gercek-lever kaldi
= onayli KAP gun-damgasi fetch'i (FORWARD_DATA_SPEC #1). Bu kart, o fetch'in NEYI cozecegini ve
NEYIN deploy-edge sayilacagini ON-KAYITLI olarak soyler. Hicbir yeni-olcum/iddia yok; tum sayilar
commit'li L8-L11 sonuclarindan. Karar the maintainer'in; otonom-faz ag-sinirinda durur.

## Bugun NE BILIYORUZ (mevcut-veride kapali, 4-eksen)
- **Power [L8]**: sabit etki/varyansta n_required(|t|=2) = n_obs*(2/|t_obs|)^2. Gozlenen-etki bandi
  [95, 759] olay. Kit event-siniflari (index-rebalance ~2/yil, CPI ~12/yil) bu bandi insan-ufkunda
  GECEMEZ; yalnizca yuksek-gelis-hizli daily-PEAD gecebilir.
- **Hacim [L9]**: GERCEK earnings-panel -> ~136 likit-SUE-testable olay/yil (yalniz %19 likit);
  ay->gun bounded ~95 bagimsiz date-cluster/yil. L8'in varsaydigi ~120/yil'i ~1.3x icinde DOGRULAR.
  Band [95,759] bu hizda ~1-8 yilda birikir.
- **Etki/Isaret [L10]**: olay-seviyesi aylik SUE yari-bolme (pos-neg, market-relative) LIKIT'te
  +0.69%/ay = DOGRU-isaretli ama ANLAMSIZ (Welch t=0.64; sd_event ~%18.5/ay). ISARET-engeli YOK.
  |t|=2 icin gun-damgali etki aylik-yari-bolmenin ~2-5.5x'i gerek (1-8yil) -- ve gunluk-pencere
  gurultusu << aylik oldugu icin bu KONSERVATIF (gercekte daha-kolay).
- **Calistirilabilir-harness [L11]**: on-kayitli daily-PEAD testi (t+1 giris, market-relative
  [+1,+H] CAR, SUE-tercile long-short, olay-kumeli NW-t, gercekci cost, keep-bar) yazildi ve
  sentetik gun-damgasiyla DOGRULANDI (recovery t=5.9 / placebo t=0.18 / look-ahead-leak t=13.5).

## Fetch'in MALIYETI ve KAPSAMI
- Maliyet: BIR onayli network fetch-run (KAP publication_date gun-damgalari). YENI-scraper DEGIL --
  `kap_historical_fetcher` semasinda `publication_date` zaten var, cache'ler bos.
- Cikti: `data/cache/kap_pead_daystamped.parquet` [symbol, publication_date, fiscal_year, quarter, sue].
- Sonra: `python lab-demo-goal/harness/l11_forward_daily_pead.py` (kod-degisikligi YOK; sentetik->gercek
  otomatik gecer). Gercek-kosumda D-207 per-isim cost isaretli-noktada baglanir.

## ON-KAYITLI KEEP-BAR (gercek-test; sonuctan ONCE donmus -- L11 Stage-0)
deploy-edge SAYILIR <=> LIKIT ust-tercile market-relative CAR:
1. rel-net CAR > 0 (gercekci round-trip cost SONRASI), VE
2. olay-kumeli |NW-t| >= 2.0 (lag=H), VE
3. rejim-isaret-stabil (2022-01-01 split, iki-tarafta ayni-isaret), VE
4. dogru-isaret (pozitif-SUE ust-tercile, drift yonu).
Hepsi gecerse -> TRADEABLE-EDGE (deploy-aday, sonraki-adim the maintainer). Aksi -> NOT-TRADEABLE.

## IKI olasi sonuc ve ANLAMI
- **TRADEABLE cikar**: programin ILK deploy-edge'i; en-guclu power-sinifindan, on-kayitli, look-ahead-safe,
  gercekci-maliyet-sonrasi. Dogrudan deploy-degerlendirmesine gider.
- **NOT-TRADEABLE cikar**: daily-PEAD da graveyard'a -- AMA bu sefer "en-guclu power-sinifi da gecmedi"
  bilgisiyle; programin mevcut-veri+KAP-gun-damgasi alani KESIN kapanir. Honest-null, kayit, kutlama-yok.
  (L3'un aylik-null'unun gunluk-cozunurlukte de surmesi olasi senaryo.)

## NE cozMEZ
Fetch yalnizca daily-PEAD'i cozer. #2 surpriz-kosullu-makro (consensus-surprise verisi ayri),
#3 TEFAS fon-akisi, #4 daily-foreign-ratio hala AYRI veri + ayri onay ister. Bu kart onlari kapsamaz.

## Tavsiye-cercevesi (karar the maintainer'in)
daily-PEAD, mevcut-veriden cikarilabilecek EN-YUKSEK-beklenen-degerli forward-deney: tek-fetch maliyeti,
4-eksen hazir, on-kayitli keep-bar, calistirilabilir-harness. Otonom-faz burada KASITLI durur (ag-siniri).
Go/no-go ve fetch-yetkisi the maintainer'da.
