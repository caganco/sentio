# RR-Y1-016-C — X1 betimsel buy-vs-sell post-disclosure asimetri (ölçüm)

**Sınıf:** Betimsel ölçüm (RR-Y1-016-B IŞ-4'ün koşulması). **Stage-0-DEĞİL**, keep-bar-YOK,
hüküm-YOK. Çıktı **karar-girdisidir**. Yalnız **X1 look-half** (donmuş konjuge-split,
[freeze](RR-Y1-016-CONJUGATE-SPLIT-FREEZE.json), `frozen_rule_sha256=240514c3…`); **X2
mühürlü ve görülmedi** (tek-atış Stage-0'a saklı, DEC-053).

**Provenance (DISC-1 dürüstlük):** Veri = **taze KAP scrape (run-2, post-UTF-8, 2026-06-12;
yerel pg16.9)** — kanonik panel DEĞİL (kurtarılamaz). Kanonik panel geri gelirse iki kaynak
ayrışabilir; bu sonuç fresh-scrape soyundandır.

**Yöntem.** Olay = her disclosure'ın o-taraf (BUY/SELL) işlem içermesi (iki-taraf simetrik →
event-tanımı-asimetrisi kontrol-edildi). Giriş = look-ahead-safe signal-date (`max(published_at)`,
düzeltme-duyarlı) + **t+1** (IŞ-1). Getiri = **market-relative** (hisse − XU100), 5/10/21/42/63
işgünü. Veri: 592 disclosure (271 buy / 382 sell tx), 18 ay (2025-01-22→2026-06-12), 127 ticker
fiyatlı + XU100 (409 bar). X1: 78 ticker / X2: 83 mühürlü. Olay: 134 buy / 147 sell (X1).

---

## Sonuç tablosu (X1, market-relative aktif getiri %)

### Buy-side (long-only altında **yegâne trade-edilebilir** taraf)
| horizon | N | hit% | medyan% | ort% |
|---|---|---|---|---|
| 5g | 118 | 50.0 | −0.05 | +0.50 |
| 10g | 118 | 42.4 | −1.33 | −0.26 |
| 21g | 110 | 41.8 | −2.15 | −1.32 |
| 42g | 109 | 39.5 | −4.95 | −1.60 |
| 63g | 99 | 41.4 | −4.77 | +3.22 |

### Sell-side (**yalnız teşhis** — long-only/no-short, trade-aday-DEĞİL)
| horizon | N | hit% | medyan% | ort% |
|---|---|---|---|---|
| 5g | 137 | 47.5 | −0.39 | +0.07 |
| 10g | 136 | 47.1 | −0.98 | −0.07 |
| 21g | 133 | 32.3 | −2.56 | −0.80 |
| 42g | 130 | 35.4 | −6.69 | −2.24 |
| 63g | 124 | 38.7 | **−10.85** | −0.57 |

Ham çıktı: [`RR-Y1-016-X1-asymmetry-result.json`](RR-Y1-016-X1-asymmetry-result.json).
Script: [`scripts/probe/rr_y1_016_x1_asymmetry.py`](../../scripts/probe/rr_y1_016_x1_asymmetry.py).

---

## Betimsel gözlemler (yorumsuz hüküm-değil)

1. **Her iki taraf da disclosure sonrası piyasaya-göre NEGATİF sürükleniyor.** Hit-rate'ler
   çoğunlukla <%50; medyanlar negatif ve horizon uzadıkça derinleşiyor.
2. **Buy-side (trade-edilebilir taraf) zayıf-ila-negatif.** Pozitif market-relative sürüklenme
   YOK — medyan 21g −%2,15, 42g −%4,95. "Insider alımı → outperformance" naif tezi X1'de
   görünmüyor. (63g ort +%3,22 vs medyan −%4,77 = sağ-kuyruk outlier-çarpıklığı, sağlam-pozitif
   değil; medyan daha güvenilir.)
3. **Sell-side daha güçlü-negatif**, özellikle uzun-horizon (63g medyan −%10,85, hit %38,7).
   Insider SATIŞ disclosure'ı sonrası hisse piyasanın altında kalıyor — **yön-bilgisi taşıyan
   taraf bu**. Ama long-only/no-short → trade-edilemez, yalnız teşhis.
4. **F1/F2 asimetri gözlemi (hipotez→gözlem):** literatür-yönüyle tutarlı — **güçlü directional
   sinyal sell-side'da**; fakat güçlü-olan taraf tam da **trade-EDİLEMEYEN** taraf. Trade-edilebilir
   buy-side X1'de pozitif-edge göstermiyor. F1/F2 artık "olabilir" değil; X1'de **gözlendi**:
   asimetri var, yön = sell-side-güçlü ama investability-yanlış-tarafta.

---

## Stage-0 kararına etki (X2 mühürlü kalır)

Bu betimsel X1-bakışı, ön-imzalı DISC-3 beklentisini (clean-X2 Stage-0 FAIL-eğilimli) **destekler**:
trade-edilebilir buy-side'da pozitif market-relative sürüklenme yok; sell-side bilgili ama
invariant-bloklu. **Net (karar-girdisi, hüküm-değil):** mevcut X1-kanıtı, X2 lockbox'ını bir
buy-side long Stage-0'a yakmayı **motive etmiyor** — beklenen-değer düşük (decay-karşı-prior +
buy-side düz/negatif sürüklenme ile uyumlu). Stage-0-açma/keep-bar kararı maintainer'a aittir.

## Caveat'lar

- **Fresh-scrape** (kanonik-panel-değil); tek-config, betimsel.
- N hücre-başına mütevazı (~100-137); 63g'de N düşüyor (yeni olayların geleceğe-uzanan horizon'u yok).
- Olaylar per-disclosure-simetrik; buy-side **trading sinyali** çok-insider küme (`detect_clusters`),
  burada modellenmedi — bu tablo asimetri-teşhisidir, trade-sinyali değil.
- Market-relative = XU100 **fiyat** endeksi (total-return değil); hisse-vs-benchmark per-seri
  işgünü-offset (küçük hizalama yaklaşımı).
- 9 ticker yfinance'te fiyatsız (düştü); 11 buy / 5 sell olay giriş-fiyatı-yok diye atlandı.
- Ort vs medyan ayrışması (outlier) → medyanlar daha sağlam.

---

**Kapsam-uyumu:** Stage-0-açılmadı, keep-bar-değerlendirilmedi, sign-flip-yok, composite-optimize-yok,
mezar-diriltme-yok. Sell-side trade-aday sayılmadı (yalnız-teşhis). X2 görülmedi. measurement-
verification (DISC-10) kendiliğinden-tetiklenmedi. Betimsel-çıktı hüküm-değil, sonraki-kararın-girdisi.
