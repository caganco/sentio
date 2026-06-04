# L14 -- QUALITY / PROFITABILITY (ROE) CROSS-SECTIONAL FACTOR (HUKUM: QUALITY-NOT-TRADEABLE)

Stage-0: `lab-demo-goal/stage0/STAGE0_L14_quality_roe.json` (sonuc-ONCESI donduruldu).
Sonuc: `lab-demo-goal/results/l14_quality_roe_results.json`. ASCII. OLCUM (yeni-FAKTOR, sentez-degil).
Yeni-veri-CEKIMI YOK, optimizasyon YOK, grid-supurme YOK, committed-motor SIFIR-dokunus, look-ahead-safe.

GERCEKTEN YENI faktor: ROE = net_profit/equity (Fama-French RMW / Novy-Marx kalite/karlilik ailesi).
Graveyard'da DEGIL (value, momentum, hi52, lowvol, NAV-MR, temettu-runup, foreign-flow, L1-L13).
Tek on-kayitli tanim (varyant-supurme YOK = p-hacking YOK). Fiyat sinyalde YOK -> value-re-test DEGIL.

## Tasarim (donmus)
- Sinyal: ROE = net_profit/equity (equity>0), `fundamentals_2019_2026.parquet` (81 ay, 677 sembol).
  RANK-tabanli tercile -> fat-tail ROE outlier'a dayanikli (winsorize-knob YOK).
- Look-ahead-safe: formasyon ayi M'de ROE = ay M-1 (LAG=1 ay konservatif tampon; panel aylik-snapshot,
  equity/net_profit yalniz rapor-YAYINLANINCA siciyor -> mid-quarter equity ziplamasi bunu dogrular).
- Evren: ALL + LIQUID (>=1e7 TL trailing-63g medyan ADV). Benchmark: EW-full aylik (durust-bar).
- Portfoy: LONG top-ROE tercile (deploy-kapi, market-relative) + akademik long-short spread. K=1 PRIMARY,
  K=3 turnover-azaltma legi. D-207 per-isim gercekci maliyet. NW-t (HAC), rejim-split 2022-01.
- Keep-bar: K=1 LIQUID long-tercile rel-net>0 VE |NW-t|>=2 VE rejim-isaret-stabil.

## Olculen (88 formasyon ayi)
| K / scope | long-size | turnover | costfree mean (t) | NET mean (t) | rejim-stabil | L-S mean (t) | realized-cost |
|---|---:|---:|---|---|:--:|---|---:|
| K=1 ALL | ~148 | 0.094 | -0.13%/ay (t=-0.61) | -0.29%/ay (t=-1.40) | EVET | +0.16% (t=0.36) | 136bp |
| **K=1 LIQUID** | ~25 | 0.204 | **-0.32%/ay (t=-0.66)** | **-0.44%/ay (t=-0.91)** | EVET | +0.21% (t=0.28) | **41bp** |
| K=3 ALL | ~149 | 0.071 | -0.30%/ay (t=-1.49) | -0.42%/ay (t=-2.11) | EVET | -0.18% (t=-0.43) | 115bp |
| K=3 LIQUID | ~25 | 0.128 | -0.56%/ay (t=-1.09) | -0.65%/ay (t=-1.27) | EVET | +0.11% (t=0.14) | 40bp |

## Okuma (beklenti DOGRULANDI -- durust-null)
- **Kalite-primi YOK (BIST likit, 2019-2026)**: deploy-kapisi (K=1 LIQUID long-tercile) market-relative
  net = -0.44%/ay, ANLAMSIZ (t=-0.91). Keep-bar GECMEZ. `QUALITY-NOT-TRADEABLE`.
- **Bu bir COST-duvari DEGIL, bir SIGNIFICANCE/SIGN duvari**: costfree (maliyet-ONCESI) high-ROE likit
  getirisi ZATEN negatif (t=-0.66). Maliyet (~41bp, turnover dusuk 0.20) sinyali oldurmuyor; ortada
  oldurulecek brut-sinyal YOK. (hi52/L3'teki maliyet-duvarindan farkli teshis.)
- **Benchmark-bagimsiz teyit = long-short spread ~0**: high-ROE minus low-ROE (size-confound'dan goreli-bagisik)
  LIQUID'te +0.21%/ay ama t=0.28 -> sifirdan ayirt-edilemez. Yani sonuc EW-full secimine bagli degil.
- **DURUST caveat (size-confound)**: long-only top-ROE'nin EW-full'a gore negatifligi kismen 2021-23
  enflasyon/small-cap ralisini yansitir (EW-full microcap-agirlikli; high-ROE isimler buyuk/olgun).
  AMA long-short spread'in de ~0 olmasi, kalite-primi-yoklugunun benchmark'tan bagimsiz oldugunu gosterir.
- **Dusuk-turnover hipotezi dogrulandi ama kurtarmadi**: kalite yavas-sinyal (turnover 0.13-0.20,
  momentum/reversal'dan dusuk) -> maliyet drag'i kucuk; ama brut-sinyal yok oldugu icin onemsiz.
- **Rejim-stabil (negatif)**: hem pre- hem post-2022 negatif -> tutarli bir (non)etki, gecici-anomali degil.

## Hukum: QUALITY-NOT-TRADEABLE (no deployable edge)
Yeni canonical faktor olculdu ve graveyard'a temiz-eklendi: BIST likit-evrende kalite/karlilik (ROE)
primi YOK; high-ROE likit isimler EW-full'a gore (anlamsizca) underperform, long-short ROE spread'i ~0.
Teshis SIGNIFICANCE/SIGN-duvari (cost-duvari degil) -> META-BULGU'nun (gorunur-edge ya microcap ya
maliyet/anlamlilik duvari) yeni bir teyidi, simdi profitability-ekseninde. Deploy-iddiasi YOK. Sonuc
kaydedildi (kutlama-yok). ONE on-kayitli tanim; varyant-supurme yapilmadi.
