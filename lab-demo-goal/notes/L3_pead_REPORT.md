# L3 -- PEAD (post-earnings-announcement drift), aylik SUE sort (HUKUM: NOT-TRADEABLE)

Stage-0: `lab-demo-goal/stage0/STAGE0_L3_pead.json` (sonuctan ONCE donduruldu).
Sonuc: `lab-demo-goal/results/l3_pead_results.json`. ASCII. Olcum-only, look-ahead-safe.

## Kurulum
Sinyal = `sue` (standartlastirilmis YoY de-cumulate ceyreklik net-kar surprizi; seasonal-random-walk,
DOGRULANDI ue = net_profit_q[t]-net_profit_q[t-4C]). Her ay (son islem-gunu) consume_from_month'u
[m-K+1..m] icinde olan isimlerin SUE'su cross-sectional siralanir; LONG = ust-tercile (deploy-edilebilir,
EW-full'a-RELATIVE), academic L-S = ust-eksi-alt tercile. K=3 PRIMARY (~60g drift), K=1,2 = drift-decay
profili. Gercekci D-207 per-isim maliyet. ALL + LIQUID (>=1e7 ADV). Look-ahead-safe: giris consume_from_month'tan
(=announce_month+1) -> klasik GUNLUK PEAD'i ATTENUE eder (ilk-pop kacirilir, gecikmeli/seyreltilmis dilim).

## Bulgular (relative = EW-full'a karsi; L-S = scope-ici kendinden-benchmark)
| K | scope | long-tercile costfree (t) | long NET-after-cost (t) | L-S spread (t) | breakeven / realized bps |
|---|---|---|---|---|---|
| 1 | ALL | +0.03% (0.05) | -1.07% (-1.57) | +0.73% (0.64) | 3.4 / 137 |
| 1 | LIQUID | -1.51% (-1.90) | -1.98% (-2.49) | **-3.21% (-2.91)** | 0 / 62 |
| 2 | ALL | +0.37% (0.79) | -0.31% (-0.65) | +0.64% (1.03) | 63 / 120 |
| 2 | LIQUID | -0.92% (-1.79) | -1.23% (-2.42) | -0.77% (-0.91) | 0 / 58 |
| 3 | ALL | +0.10% (0.25) | -0.32% (-0.80) | +0.39% (0.80) | 30 / 112 |
| 3 | LIQUID | -1.32% (-3.24) | -1.55% (-3.83) | -0.83% (-1.29) | 0 / 51 |

(t = NW lag-3. Gross-mean'ler aylik, RELATIVE.)

## Hukum: PEAD-NOT-TRADEABLE (anlamlilik + maliyet duvari)
- **Deploy-gate (K=3 LIQUID long-tercile rel-net) KALDI**: pozitif-degil; aksine anlamli NEGATIF
  (-1.55%, t=-3.83). Pozitif long-deployable PEAD YOK.
- **Academic L-S**: ALL'da zayif-pozitif (PEAD-isareti ama ANLAMSIZ, t<1.1); LIQUID'de pozitif-DEGIL;
  K=1-LIQUID anlamli NEGATIF (-3.2%, t=-2.9), K=2/3'te sonuyor.
- Maliyet de duvar: aylik-tercile turnover ~0.4-0.58 -> realized 51-137bp, breakeven 0-30bp.

## Iki ONEMLI durust-cerceve notu
1. **Benchmark-confound**: K=3-LIQUID long-tercile'in "anlamli -3.8 t"si KISMEN size/likidite-confound'u:
   EW-full benchmark microcap-agirlikli -> HERHANGI likit-sepet jenerik olarak EW-full'un altinda kalir
   (microcap-serabi, graveyard ana-ders). SUE-temiz okuma = scope-ici L-S, ki o da pozitif-DEGIL.
   Dolayisiyla "anlamli ters-PEAD edge" diye ASIRI-iddia YOK; net ifade: long-only likit tercile
   deploy-gate'i gecmez. (Verdict her iki okumada da ayni -> saglam.)
2. **Cozunurluk-acigi (program icin degerli)**: agent'in "PEAD en-iyi event-driven, 30-40bp gecer" notu
   GUNLUK-cozunurluk ilan-calismalarina dayaniyordu. Elimizdeki AYLIK + look-ahead-safe consume-lag'de
   PEAD hayatta-KALMIYOR; gecikmeli-giris aksine mean-reversion yakaliyor (K=1-LIQUID L-S anlamli negatif).
   -> BIST'te PEAD yakalamak GUNLUK ilan-zaman-damgasi gerektirir (bizde YOK). Somut cozunurluk-dersi.

## Ana ders
DURUST-beklenti (Stage-0: monthly-attenuation + inflation + thin-coverage -> muhtemelen
anlamlilik/maliyet-duvari) OLCUMLE dogrulandi. Kutlama-yok. 2.tur/K-grid-supurme YOK. L3 ARSIVLENDI.
YAN-IPUCU: K=1-LIQUID L-S anlamli-negatif -> likit-isimlerde KISA-VADE-REVERSAL sinyali olabilir
-> L2 (zaten Stage-0'da reversal beklentisi onceden-ilanli) bunu BAGIMSIZ test edecek.
