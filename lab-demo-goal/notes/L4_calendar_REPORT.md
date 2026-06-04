# L4 -- CALENDAR/SEASONALITY scan (HUKUM: DESCRIPTIVE-VIEW, deploy-edilebilir-edge YOK)

Stage-0: `lab-demo-goal/stage0/STAGE0_L4_calendar.json` (sonuctan ONCE donduruldu).
Sonuc: `lab-demo-goal/results/l4_calendar_results.json`. ASCII. Olcum-only, multiple-testing-aware.

## Kurulum
SABIT-kanonik etki seti (data-driven arama YOK): turn-of-month, day-of-week, month-of-year,
pre-holiday. XU100 gunluk-getiri PRIMARY (yatirilabilir endeks), EW-full SECONDARY (microcap-agirlikli).
OLS+Newey-West HAC differential (etki-gunu-ortalama eksi diger-gun-ortalama, lag-5). Bonferroni:
headline-aile p<0.0125 (4 test), tam-aile p<0.00263 (19 dilim). Regime sign-stability (2022-01).

## Bulgu -- yatirilabilir endekste (XU100) HICBIR etki ham-anlamli bile DEGIL
| etki | diff/gun | HAC-t | p_raw | Bonferroni |
|---|---|---|---|---|
| turn_of_month | +0.10% | 0.98 | 0.33 | gecmez |
| dow_Mon (Pazartesi) | +0.14% | 1.32 | 0.19 | gecmez |
| month_Jan (Ocak) | +0.17% | 1.12 | 0.26 | gecmez |
| pre_holiday | -0.03% | -0.31 | 0.76 | gecmez |

XU100'de tum |t|<1.4, tum p>0.18 -> ham-0.05'i bile gecen YOK, Bonferroni'yi gecen YOK. Temiz-null.

SECONDARY EW-full (microcap-agirlikli): zayif ham-anlamli gun-ici yapi -- Pazartesi +0.20% (t=2.06),
Sali -0.18% (t=-2.11), Cuma +0.17% (t=2.05), pre-holiday +0.15% (t=1.87) -- AMA hicbiri headline-Bonferroni'yi
(0.0125) bile gecmiyor, tam-aile (0.00263) cok-uzak. Ve bunlar YATIRILAMAZ microcap-serisinde
(graveyard-dersi: etkiler microcap'te yasiyor) -> deploy-edilemez.

## Tradeability -- opportunity-cost olduruyor
TOM-overlay (TOM-disi gunlerde NAKIT %0) yillik %12 vs buy-and-hold %47 (XU100). Overlay piyasanin
GUCLU enflasyon-suruklenmesinin disinda kaldigi icin ~%35/yil getiri KAYBEDIYOR. Etki anlamli-olsa-bile
sadece-TOM-gunu-tutarak hasat etmek yikici. Decisively deploy-edilemez.

## Hukum: DESCRIPTIVE-VIEW
Yatirilabilir endekste anlamli-takvim-etkisi YOK; EW-full'daki zayif gun-ici yapi microcap-bagli ve
sub-Bonferroni. DURUST-beklenti (Stage-0: descriptive-VIEW, deploy-edilemez) dogrulandi. Temiz
multiple-testing-honest null -- disiplinli takvim-taramasinin uretmesi gereken tam-sonuc. Kutlama-yok.
L4 ARSIVLENDI -> VIEW.
