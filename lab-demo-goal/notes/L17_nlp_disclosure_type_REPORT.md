# L17 -- NLP DISCLOSURE-TYPE-CONDITIONED DRIFT FORWARD-SCAFFOLD (HUKUM: SCAFFOLD-SELF-TEST PASS)

Stage-0: `lab-demo-goal/stage0/STAGE0_L17_nlp_disclosure_type.json` (sonuc-ONCESI donduruldu).
Sonuc: `lab-demo-goal/results/l17_nlp_disclosure_type_results.json`. ASCII. VERI-CEKIMI DEGIL, SCRAPER
DEGIL, network YOK, yeni-edge YOK. Direktif ACIKCA NLP istedi. L16'dan FARKLI: sinyal duyarlilik-polaritesi
DEGIL, ifsa TIPI (buyback / sermaye-artirim / derecelendirme / temettu / yonetisim ...) -- on-kayitli
anahtar-kelime taksonomisiyle siniflanir; bir-tip sonraki market-relative drift'i ONGORUYOR-mu, tipler-arasi
Bonferroni-kontrollu. Offline yalniz CANLI snapshot var -> L11-deseni: testi donar, uygular, sentetik
dogrular, snapshot-tip-dagilimini karakterize eder.

## Tasarim (Stage-0'da donmus -- forward gercek-mod)
- Taksonomi (9 tip): BUYBACK / DIVIDEND / CAPITAL_INCREASE / RATING / GOVERNANCE / AUDIT_REPORT /
  CIRCUIT_BREAKER / SPECIAL_GENERAL / OTHER. Turkce ASCII-fold anahtar-kelime eslemesi.
- Olay: her (sembol, yayin-gunu, tip); giris t+1 (look-ahead-safe, ilan-gunu DISLANIR). Pencere [+1,+H]
  market-relative CAR, H in {5,10}.
- Test: her-tip icin CAR ortalamasi vs sifir, olay-kumeli NW-t (lag=H). Cok-test: Bonferroni alpha =
  0.05 / n_types (9 tip -> alpha=0.00556) raw |t|>=2 bariyeri YANINDA raporlanir.
- Keep-bar: bir-tip mean-CAR ANLAMLI (Bonferroni-sonrasi) AND regime-stabil AND gercekci maliyet sonrasi yasar.
- Verdict-kurali: gecerse o-tip TRADEABLE-EDGE (deploy-aday -> Cagan); yoksa NLP-TYPE-NOT-TRADEABLE.

## Offline self-validation (sentetik, seed=20260604)
Seed'li sentetik evren + 540 planted-olay (9 tipe rastgele dagitilmis). YALNIZ BUYBACK tipine [+1,+H]'de
pozitif drift (drift=0.030) eklenir; ayrica olay-GUNUNE +3% sicrama (t+1 DISLAMASI gerekir). Diger tipler
saf-gurultu -> Bonferroni'nin yanlis-pozitif uretmedigini de gosterir.

| assert | sonuc | NW-t |
|---|---|---:|
| RECOVERY (BUYBACK planted-drift geri-kazanilir, dogru-isaret, \|t\|>=2) | **PASS** | 2.70 |
| PLACEBO (tip-etiketleri permute -> etki kaybolur, \|t\|<2) | **PASS** | 0.92 |
| LOOK-AHEAD (olay-gunu girisi sicramayi SIZDIRIR, \|t\| safe'ten buyuk) | **PASS** | 7.20 (vs 2.70) |

all_asserts_pass = **True**. Pipeline DOGRU, look-ahead-GUVENLI, cok-test-kontrolu yerinde.

## Gercek snapshot karakterizasyonu (data-gap, edge-DEGIL)
`data/news_cache.json`: 6 sembol / 60 makale. Tip-dagilimi: OTHER=20, SPECIAL_GENERAL=11, CIRCUIT_BREAKER=8,
BUYBACK=6, CAPITAL_INCREASE=4, RATING=3, GOVERNANCE=3, AUDIT_REPORT=3, DIVIDEND=2. OTHER-orani %33.
`is_backtestable_panel=False`: gun-damgali tarihsel metin-panel YOK -> tip-kosullu CAR testi onayli
tarihsel ifsa-fetch ister.

## Okuma
- **Mekanik kanit, edge-kaniti DEGIL**: BUYBACK-recovery yalniz planted etkiyi geri-kazanir; gercek
  BIST tip-drift'i hakkinda HICBIR sey soylemez.
- **Look-ahead muhuru**: leak t=7.2 >> safe t=2.7 -> ilan-gunu sicramasi t+1 ile DISLANIYOR.
- **Cok-test-disiplini**: 9-tip Bonferroni on-kayitli -> gercek-kosumda tip-tarama p-hacking'e donmez.
- **Veri-gap sayisal**: snapshot tip-cesitliligi var ama gecmis-derinlik/gun-damgasi YOK -> backtest
  IMKANSIZ. Gercek-test tarihsel KAP tam-metin arsivi + NLP-pipeline (Cagan-onayli) ister.
- **Ortak-fetch**: L16 + #1 daily-PEAD ile ayni KAP-gun-damgali-metin fetch'inden beslenir.

## Hukum: SCAFFOLD-SELF-TEST PASS (no deployable edge)
Direktifin NLP avenusu L11-forward-scaffold formuna kristalize edildi, L16-polaritesinden ayri: HANGI
ifsa-tipi drift ongoruyor, cok-test-kontrollu. Test donmus + pipeline-dogru; gercek gun-damgali ifsa-metin
fetch'inden (Cagan-kapili) tek-adim uzakta. Sentetik PASS yalniz pipeline + look-ahead-guvenligi + Bonferroni
mekanigini kanitlar. N<=1 (scaffold). L17 ARSIVLENDI. Yeni-edge iddiasi YOK.
