# L2 -- SHORT-TERM REVERSAL (contrarian) -- HUKUM: NOT-TRADEABLE (yanlis-isaret + maliyet-duvari)

Stage-0: `lab-demo-goal/stage0/STAGE0_L2_short_reversal.json` (sonuctan ONCE donduruldu).
Sonuc: `lab-demo-goal/results/l2_short_reversal_results.json`. ASCII. Olcum-only, look-ahead-safe.

## Kurulum
Contrarian: LONG = gecmis-getiri ALT-tercile (kaybedenler), SHORT = UST-tercile (kazananlar).
Iki donmus spec: REV_1M (aylik, 21g formasyon), REV_1W (haftalik, 5g formasyon). Deploy-okuma =
long-loser-tercile vs EW-full; academic = loser-minus-winner (L-W) spread. D-207 gercekci maliyet
(= bid-ask-bounce panzehiri). ALL + LIQUID. NW-t lag-3 / regime / breakeven.

## Bulgu 1 -- REVERSAL YANLIS-ISARET (reddedildi): BIST 2019-2026 KISA-VADE MOMENTUM gosteriyor
| spec | scope | long-loser costfree (t) | long-loser NET (t) | L-W spread (t) |
|---|---|---|---|---|
| REV_1M | ALL | -0.87% (-4.99) | -1.76% (-10.2) | **-1.16% (-3.63)** |
| REV_1M | LIQUID | -1.25% (-3.22) | -1.60% (-4.19) | -1.08% (-1.80) |
| REV_1W | ALL | -0.21% (-4.69) | -1.09% (-24.8) | **-0.31% (-3.43)** |
| REV_1W | LIQUID | -0.36% (-4.06) | -0.68% (-7.75) | **-0.46% (-3.52)** |

L-W spread HER yerde NEGATIF ve anlamli -> kaybedenler kazananlarin ALTINDA kalir = kaybedenler
kaybetmeye, kazananlar kazanmaya devam eder. Bu KLASIK-reversal'in (Lehmann/Jegadeesh) ve eski
Bildik-Gulay-contrarian-bulgusunun TERSI. Long-loser-tercile EW-full'un anlamli ALTINDA. Regime
sign-stable -> tutarli. Yani contrarian-reversal hipotezi REDDEDILDI; isaret MOMENTUM yonunde.

## Bulgu 2 -- ters-yon (kisa-vade MOMENTUM) deploy-edilebilir-DEGIL: MALIYET-DUVARI
Kazanan-tercile (momentum-long) vs EW-full (pre-committed short-leg ciktisi):
| spec | scope | costfree (t) | NET-after-cost (t) | breakeven / realized bps | turnover |
|---|---|---|---|---|---|
| REV_1M | ALL | +0.24% (1.27) | -0.58% (-2.93) | 39 / 128 | 0.64 |
| REV_1M | LIQUID | -0.17% (-0.29) | -0.51% | 0 / 46 | 0.69 |
| REV_1W | ALL | +0.11%/h (2.23) | -0.71% (-12.6) | 17 / 128 | 0.63 |
| REV_1W | LIQUID | +0.10%/h (0.90) | -0.20% | 16 / 46 | 0.64 |

Momentum gross-edge KUCUK (~10bp/hafta) ve LIKIT'te ANLAMSIZ (t=0.90); turnover ~0.63-0.69 ->
realized ~46bp (likit), breakeven 16-39bp. Gross-edge breakeven'in ALTINDA -> klasik MALIYET-DUVARI.
Sadece REV_1W-ALL gross marjinal-anlamli (t=2.23) ama o da illikit-suru + maliyet-sonrasi t=-12.6.

## Hukum: REVERSAL-NOT-TRADEABLE
- Pre-registered contrarian-reversal: REDDEDILDI (yanlis-isaret; keep-bar long-loser-tercile NEGATIF).
- Ters-yon momentum: ayri-deploy-edilebilir-edge DEGIL (maliyet-duvari; likit-gross anlamsiz).
DURUST-beklenti (Stage-0: maliyet-duvari) dogrulandi; ARTI beklenmedik-ama-tutarli ek-bulgu: isaret
reversal-DEGIL momentum (program'in mevcut 120g-momentum/EDGE-2 "gercek-ama-daralan" notuyla uyumlu;
kisa-vade momentum daha-da-yuksek-turnover -> daha-da-maliyet-yasakli). Kutlama-yok; momentum-yonu
in-sample GORULDU -> ayri-celebratory-L2b ACILMAZ (HARKing-yasak); VIEW-olarak-belgele.

## Ana ders (graveyard-tema pekisti)
Tekrar eden duvar: tercile-sepet + aylik/haftalik-turnover -> ~46bp likit-maliyet her kucuk-edge'i
yer. Maliyet-sonrasi yasayan tek-sey DUSUK-TURNOVER event-driven olur; ama L1(index)/L3(PEAD) orada
anlamli-edge bulamadi. L2 ARSIVLENDI -> reversal-VIEW (BIST kisa-vade momentum, deploy-edilemez).
