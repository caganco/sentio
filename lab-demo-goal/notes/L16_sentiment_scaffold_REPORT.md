# L16 -- NEWS-SENTIMENT CROSS-SECTIONAL FORWARD-SCAFFOLD (HUKUM: SCAFFOLD-SELF-TEST PASS)

Stage-0: `lab-demo-goal/stage0/STAGE0_L16_sentiment_scaffold.json` (sonuc-ONCESI donduruldu).
Sonuc: `lab-demo-goal/results/l16_sentiment_scaffold_results.json`. ASCII. Bu bir VERI-CEKIMI DEGIL,
SCRAPER DEGIL, network YOK, yeni-edge YOK. Direktif ACIKCA SENTIMENT istedi; offline tek sentiment/haber
verisi CANLI-snapshot (`data/news_cache.json`) -- backtestable tarihsel-panel DEGIL. L11-deseni: testi
SIMDI donar (pre-registration), uygular, mekanigi SENTETIK gun-damgasiyla OFFLINE dogrular ve gercek
snapshot'i karakterize eder (data-gap'i sayisallastirir). Gercek gun-damgali panel geldiginde AYNI
harness on-kayitli testi calistirir.

## Tasarim (Stage-0'da donmus -- forward gercek-mod)
- Olay: her (sembol, yayin-gunu) icin baslik-tabanli polarite skoru (POS/NEG anahtar-kelime sozlugu,
  Turkce ASCII-fold). Giris KESINLIKLE gun-damgasindan SONRAKI ilk islem-gunu t+1 (look-ahead-safe:
  ilan-gunu sicramasi DISLANIR).
- Pencere: [+1,+H] market-relative CAR, H in {5,10}; anormal = sembol-getiri eksi o-gun EW-evren ortalamasi.
- Sort: polarite terciles; PRIMARY = long(top-sentiment) - short(bottom-sentiment) spread, olay-kumeli NW-t (lag=H).
- Keep-bar: long-short-CAR>0 AND |t|>=2 AND regime-isaret-stabil (2022-01-01) AND gercekci maliyet sonrasi yasar.
- Verdict-kurali: keep-bar gecerse TRADEABLE-EDGE (deploy-aday -> Cagan); yoksa SENTIMENT-NOT-TRADEABLE.

## Offline self-validation (sentetik, seed=20260604)
Seed'li sentetik gunluk-getiri evreni + 480 planted-olay (gun-damgali, polarite-skorlu). Skorla-orantili
[+1,+H] post-ilan drift (drift_per_score=0.020) + olay-GUNUNE skor-isaretli +-3% sicrama (t+1 girisinin
DISLAMASI gerekir).

| assert | sonuc | NW-t |
|---|---|---:|
| RECOVERY (planted-drift geri-kazanilir, dogru-isaret, \|t\|>=2) | **PASS** | 5.91 |
| PLACEBO (skor-etiketleri permute -> etki kaybolur, \|t\|<2) | **PASS** | 0.18 |
| LOOK-AHEAD (olay-gunu girisi sicramayi SIZDIRIR, \|t\| safe'ten buyuk) | **PASS** | 13.53 (vs 5.91) |

all_asserts_pass = **True**. Pipeline DOGRU ve look-ahead-GUVENLI.

## Gercek snapshot karakterizasyonu (data-gap, edge-DEGIL)
`data/news_cache.json`: 6 sembol / 60 makale / yalniz ~1-ay (ornek tarih-araligi 12 May 2026 .. 03 Haz 2026),
baslik-only. Polarite-siniflanabilir makale orani yalniz %33. En-sik basliklar KAP "Ozel Durum Aciklamasi"
(11), "pay disinda sermaye piyasasi araci" (9), "devre kesici" (8), "paylarin geri alinmasi" (6) ...
`is_backtestable_panel=False`: gun-gun tarihsel sentiment-skoru YOK, gecmis-derinlik YOK.

## Okuma
- **Mekanik kanit, edge-kaniti DEGIL**: sentetik RECOVERY yalniz tahminci-dogrulugunu kanitlar; gercek
  BIST sentiment-edge'i hakkinda HICBIR sey soylemez.
- **Look-ahead muhuru**: olay-gunu girisi (leak) t=13.5 >> guvenli t+1 girisi t=5.9 -> +-3% ilan-sicramasi
  t+1 ile DISLANIYOR. Sentiment-drift olculur, sicrama-DEGIL.
- **Veri-gap sayisal**: snapshot 6-sembol/1-ay -> backtest IMKANSIZ; gercek-test tarihsel gun-damgali
  haber-corpus + duyarlilik-skorlama hatti (Cagan-onayli ag-fetch) ister. Offline-uretilemez.
- **Ortak-fetch verimi**: snapshot KAP-ifsa basliklariyla baskin -> tek onayli KAP tarihsel-metin cekimi
  L16 (sentiment) + L17 (NLP-tip) + #1 daily-PEAD'i BIRLIKTE besler.

## Hukum: SCAFFOLD-SELF-TEST PASS (no deployable edge)
Direktifin SENTIMENT avenusu L11-forward-scaffold formuna kristalize edildi: test donmus ve pipeline-dogru,
gercek gun-damgali haber/sentiment fetch'inden (Cagan-kapili) tek-adim uzakta. Sentetik PASS yalniz
pipeline-dogrulugu + look-ahead-guvenligi kanitlar; gercek BIST-edge'i ag-fetch'in Cagan-onayina KAPILI.
N<=1 (scaffold). L16 ARSIVLENDI. Yeni-edge iddiasi YOK.
