# lab-demo-goal -- otonom edge-kesif AR-GE ajandasi

Amac: yeni edge adaylari + yeni faktor + yeni veri turleri. Production repo READ-ONLY;
tum is bu dizinde. Mevcut disiplinli olcum cercevesini REUSE: gercekci maliyet (D-207
quoted-primary, ~28-42bp likit round-trip), likit-evren (ADV>=1e7 TL), NW-t (HAC), rejim
split (2022-01), Stage-0 ON-KAYIT (sonuctan once dondur), DURUST beklenti (kutlama-yok),
anlamlilik-vs-maliyet duvari ayrimi, look-ahead-safe ZORUNLU, ASCII.

## Onceki program durumu (graveyard -- TEKRAR TEST ETME)
- Cross-sectional fiyat/hacim faktorleri: value (SERAP), momentum/EDGE-2 (gercek ama daralan),
  hi52 (anlamlilik-duvari, D-208), lowvol63 (SERAP), value-rejim-kolu (elendi). 3/3 kapali.
- Time-series: NAV-iskonto-MR holding (SERAP, D-206).
- Event: dividend pre-ex run-up H2b (anlamlilik-duvari, D-209, KAPANDI).
- ANA DERS: cogu gorunur-edge illikit-microcap'te yasiyor, likit-evrende gercekci-maliyet
  sonrasi kayboluyor. Likit-evren + ~30-40bp maliyet = gercek test.

## Eldeki veri (lokal, dogrulandi inv-01)
- adjusted_prices_2019_2026.parquet: 681 sembol, 2019-01..2026-05, 1848 gun. close, vwap,
  value_tl, volume, bist100/bist30 (uyelik bayragi), ca_code, adjusted_close/vwap,
  tr_index_gross/net. (VWAP + traded-value VAR.)
- d207_quoted_spread_panel.parquet: 440 sembol quoted spread (maliyet).
- fundamentals_2019_2026.parquet: aylik, 677 sembol: mktval, net_profit, equity, net_div,
  pe, pbv, dy, ey, bm, dyld.
- pit_membership_2019_2026.parquet: date x symbol, in_bist100 + in_bist30 (POINT-IN-TIME).
  -> INDEX-REBALANCE event study (DOKUNULMAMIS).
- earnings_dates.parquet: 794 sembol, SUE (59% NaN), announce_month/consume_from_month
  (look-ahead-safe), degoran-month-proxy. -> PEAD (aylik cozunurluk).
- macro_event_dates.parquet: 90 olay (CPI + PPK), event_date/reference_period/exact.
- trend_v1_ohlcv: 89 sembol full OHLCV (gap/range studies, ama dar evren).
- exposure: gold_tl (2023+), tlref, tufe, xu100 (2019+).

## Aday kuyrugu (oncelik sirasi)
- L1 INDEX-REBALANCE (pit_membership): BIST100/30 ekleme/cikarma event study. Event-driven,
  dusuk-turnover -> maliyet-survivable. Index-inclusion effect literaturde belgeli (Shleifer
  1986, Harris-Gurel). EN-YUKSEK-NOVELTY + deploy-edilebilir (uyeler likit). [BASLIYOR]
- L2 SHORT-TERM REVERSAL (1w/1m): BIST'in en-belgeli anomalisi (Bildik-Gulay contrarian).
  Likit-evren + gercekci maliyet. DURUST beklenti: muhtemelen maliyet-duvari (yuksek turnover,
  kaybedenleri al). Ama hic izole-test edilmedi.
- L3 PEAD: earnings drift, SUE high-minus-low forward return, look-ahead-safe. Aylik.
- L4 CALENDAR/SEASONALITY: turn-of-month / day-of-week / month / pre-holiday. Ucuz tarama,
  cogu maliyet-sonrasi tradeable-degil; VIEW olarak belgele. Multiple-testing-aware.
- L5 WEB SENTEZ: borsapy/borsamcp veri turleri + BIST anomali literaturu -> yeni-aday katalog.
- (sonra) macro-surprise drift, volume-shock reversal, VWAP-deviation reversal, lottery/MAX.

## Disiplin checklist (her aday)
1. Stage-0 dondur (hipotez, pencere, evren, maliyet, keep-bar, DURUST beklenti) SONUCTAN ONCE.
2. look-ahead-safe (pozisyon yalniz gozlenen-veriyle acilir; maliyet/likit trailing).
3. Likit-evren (ADV>=1e7) + ALL ikisi de raporla.
4. Gercekci maliyet (D-207) + breakeven + turnover.
5. NW-t (HAC), rejim-split sign-stability.
6. Verdict: TRADEABLE-aday / DEGIL (anlamlilik-duvari mi maliyet-duvari mi).
7. Sonuc ne olursa kaydet. Kutlama-yok. p-hacking/grid-supurme YASAK.
