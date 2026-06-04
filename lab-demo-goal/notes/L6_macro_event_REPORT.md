# L6 -- MACRO-EVENT (CPI-release) event-window study (HUKUM: DESCRIPTIVE-VIEW, deploy-edilebilir-edge YOK)

Stage-0: `lab-demo-goal/stage0/STAGE0_L6_macro_event.json` (sonuctan ONCE donduruldu).
Sonuc: `lab-demo-goal/results/l6_macro_event_results.json`. ASCII. Olcum-only, look-ahead-safe.

## Kurulum + VERI-TAVANI (kritik on-kosul)
Dusuk-turnover EVENT-DRIVEN sinif (meta-bulgunun "maliyet-sonrasi-yasayabilecek-tek-yapi" dedigi).
Olay = TUIK CPI-ilan gunleri (`macro_event_dates.parquet`, n=88 cpi_release). AMA veri YALNIZCA
TARIH tasiyor -- actual/forecast (SURPRIZ buyuklugu) YOK. Drift'i tasiyan-bilesen tam-da SURPRIZ
oldugu icin, burada ancak KOSULSUZ ilan-penceresi etkisi olculebilir = bu verinin TAVANI.
Ek-kisitlar: CPI tarihleri kural-proxy (`exact=False`, gercek-TUIK +/-1-2 gun) -> tight-pencere
smear; PPK gecmisi yok (n=2, cikarsamadan DISLANDI). PRIMARY=XU100 (yatirilabilir endeks),
SECONDARY=EW-full (microcap, yatirilamaz). tau0 = event_date'e >=-ilk islem-gunu. AR = r - tum-orneklem
gunluk-ortalama (market-timing-overlay null). PRIMARY-stat = olay-clustered t (per-event CAR);
NW-t HAC capraz-kontrol; rejim-split 2022-01; Bonferroni 4-pencere (p<0.0125). Gross-first.

## Bulgu -- yatirilabilir endekste (XU100) ANLAMLI-yon YOK (significance-wall)
| pencere | tip | CAR | clustered-t | p_raw | NW-t | rejim-stable | Bonferroni |
|---|---|---|---|---|---|---|---|
| pre[-5,-1] | descriptive | -0.21% | -0.48 | 0.63 | -0.51 | True | gecmez |
| event[0] | contaminated | +0.21% | +1.00 | 0.32 | +0.98 | True | gecmez |
| post[+1,+5] | TRADEABLE | +0.61% | +1.48 | 0.14 | +1.45 | **False** | gecmez |
| post[+1,+10] | TRADEABLE | +0.55% | +0.93 | 0.35 | +0.99 | False | gecmez |

En-buyuk sinyal = post[+1,+5] +0.61% AMA t=1.48 (ham-0.05'i bile gecmez) ve rejim-isaret-stabil-DEGIL.
Yani daha cost-testine GELMEDEN gross-anlamlilikta dusuyor (significance-wall; cost-wall'dan once).
Maliyet-sonrasi net pozitif gorunse de (40bp dusunce +0.21%) ANLAMSIZ oldugu icin onemsiz.

## Tek-niteliksel-iz: ENDEKS-DUZEYI bilgi-olay-imzasi (DESCRIPTIVE, tradeable-degil)
CPI-ilan-gununde XU100 |AR| = 1.50% vs diger-gunler 1.19% (~%26 goreli vol-sicramasi) -- klasik
bilgi-olay-imzasi (oynaklik artar, yon belirsiz). AMA: (a) EW-full'da bu iz NEREDEYSE-YOK
(1.07% vs 1.06%) -> endeks-duzeyi/makro-beta olgusu, mikro-kesit-degil; (b) vol-sicramasi YON
tasimaz -> long/short sinyali DEGIL. Sadece niteliksel gozlem.

## SECONDARY EW-full: tum-pencereler anlamsiz; post net-NEGATIF
post[+1,+5] +0.31% (t=0.76, net -0.09%), post[+1,+10] +0.14% (t=0.20, net -0.26%). Mikro-kesitte
de ilan-penceresi edge yok; net maliyet-altinda. Tutarli null.

## Hukum: DESCRIPTIVE-VIEW
Yatirilabilir XU100'de hicbir CPI-ilan-penceresi yon-etkisi ham-anlamli bile degil; en-buyuk
post-pencere t=1.48 + rejim-stabil-degil (significance-wall). Endeks-duzeyi vol-bump descriptive.
DURUST-beklenti (Stage-0: NULL/DESCRIPTIVE; surpriz-yok + proxy-tarih + PPK-n2) OLCUMLE dogrulandi.
Kutlama-yok. N<=1 (tek on-kayitli kosu, 2.tur YOK). L6 ARSIVLENDI -> VIEW.

## Bilimsel kazanim (graveyard-tema + SUMMARY ile tutarli)
Kosulsuz-ilan-penceresi etkisi SINIRLANDI (post[+1,+5] gross ~+0.6%, anlamsiz). Asil-deger:
bu null, SURPRIZ-KOSULLU testin neden gerektigini somutlastiriyor -> ileri-yol = (1) KESIN
CPI-tarihleri (Ulusal Veri Yayimlama Takvimi) + (2) actual/forecast SURPRIZ serisi + (3) PPK
tam-gecmis (canli-kaydedici / TCMB-scrape). Bu, kaynak meta.json'un kendi siniflandirmasi
("data acquisition only; edge-prior WEAK, no edge claimed") ve program-SUMMARY meta-bulgusuyla
("deger mevcut-veride yeni-faktor degil, YENI-VERI-TURUNDE") %100 ortusur. Mevcut-veri-event-uzayi
(index-rebalance L1, aylik-PEAD L3, makro-ilan L6) likit-tradeable-edge tasimiyor.
