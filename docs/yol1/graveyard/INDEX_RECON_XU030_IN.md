# Graveyard: XU030 Periodic Reconstitution IN Event Study

**Thread:** RR-Y1-011-E (index-recon demand-shock)
**Stage-0:** `docs/yol1/STAGE0_INDEX_RECON_XU030_IN.json`
**Verdict date:** 2026-06-09
**Keep-bar result:** FAIL

---

## Keep-bar Decision

| Kriter | Eşik | Sonuç |
|--------|------|-------|
| KB1: NW-t net (N=24, lag=3) | >= 2.0 | **0.052** FAIL |
| KB2: Her iki zamansal yarida pozitif | evet | Yari A +3.79%, Yari B -3.58% **FAIL** |
| KB3: Gross CAR > maliyet | gross > 46.8bp | 57.5bp PASS |

**Verdict: NOT-TRADEABLE (SERAP)**

---

## Neden Basarisiz Oldu (Graveyard Honesty — D-122 zorunlu)

### 1. Tam orneklemde istatistiksel sifir
NW-t = 0.052. 24 olaydan hesaplanan ortalama CAR (gross) = +0.58% — tamamen gurultu icinde.

### 2. Dramatik zamansal kirilma
Ilk 12 olay (2019-06 → 2023-06): ort. net +3.79%, NW-t = +4.11.
Son 12 olay (2023-09 → 2025-09): ort. net -3.58%, NW-t = -0.90.
Isaret tam tersine dondu. Stage-0 bu spliti dondurdu — post-hoc degil.

### 3. Mekanizma muhtemelen ilan aninda fiyatlanmis
11-19 gunluk kamu ilan penceresi kamuya acik → arb kapasitesi olan kurumlar zaten one konumlaniyor.
Erken donem apparent guc: BIST pasif fon evreni kucukken talep soku daha az fiyatlanmisti (spekulatif).
Gec donem: Pasif fon buyumesi + piyasa yapisi degisimi → fenomen yok.

### 4. Hisse-spesifik gurultu N=24'u domine ediyor
- AEFES 2024-12-20: -29.2% (kurumsal negatif haber penceresi icinde)
- DSTKF 2025-09-12: +26.4% (yeni-halka-arz momentumu)
- AKSEN 2022-09-21: +20.9% (enerji krizi momentum)
- ASTOR 2023-06-16: +16.8% (buyume hissesi momentum)

Bu olaylar rekonstitusyon mekanizmasindan degil, hisse-spesifik guclu-gurultuden kaynaklanir.

---

## Neden Bir Duzeltme Bu Mezarligi Kurtarmaz

| Tempting fix | Neden yasak |
|-------------|-------------|
| "2019-2022 alt-ornegini kullanalim" | Post-hoc; Stage-0 temporal split donmus; K1/K3 zincir bloku |
| "XU050/XU100'e genisletelim" | Farkli tez, sifirdan Stage-0 gerekir |
| "Buyuk outlier olaylari cikaralim" | Post-hoc outlier temizligi yasak |
| "Daha uzun pencere deneyelim" | Farkli Stage-0 gerekir; K1/K3 zincir bloku |

---

## Deger (Negatif Bilgi)

BIST'te index-inclusion anomalisinin 11-19 gunluk kamuya acik pencerede retail-erisimli olmadigi ampirik olarak teyit edildi. Bu "anlamsiz null" degil; ileri arastirma icin:
- Kurumsal isinma-suresi analizi (sadece kurumsal erisilebilir pencere: ilan oncesi)
- KAP-iceriden bilgi akisi sorusu (farkli Stage-0, farkli mekanizma)
Bu direktif bu sorulan acmaz — kapatir.
