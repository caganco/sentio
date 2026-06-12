# RR-Y1-016-D — Sell-side confound kontrolü (evren-içi + placebo, betimsel)

**Sınıf:** Fizibilite-teşhisi (DISC-5). **Stage-0-DEĞİL**, keep-bar/eşik/edge-hükmü YOK.
Betimsel çıktı, karar-girdisi. **X1-only**; **X2 mühürlü-kalır** (DEC-053 tek-atış). Yeni-split
YOK — RR-Y1-016-C'de donmuş aynı sha256-ticker-split (`240514c3…`, X1).

**Soru.** RR-Y1-016-C'de X1 sell-side market-relative drift'i negatif çıktı (63g medyan −%10,85).
Bu (i) gerçek insider-yön-bilgisi mi, (ii-a) evren/timing-seçilim-confound mu, yoksa (ii-b)
isim-sabit-confound mu? ABD-literatürü (Lakonishok-Lee) insider-satışını az-bilgilendirici bulur
(diversifikasyon/likidite/vergi) → confound ciddi olasılık.

**Provenance:** taze KAP scrape soyu (run-2, 2026-06-12), kanonik-panel DEĞİL. localhost flow_intel.
Giriş look-ahead-safe: `published_at`+t+1 (correction-aware); kontrol/placebo psödo-olaylarında
psödo-tarih + t+1. seed=42, 10k permutation, 10k bootstrap.

**Gruplar (X1, per-disclosure olay — tüm gruplar aynı granül, event-def-asimetri kontrol):**
sell 147 olay / buy 134 / no-disclosure kontrol 183 psödo-olay (>90g uzakta) / placebo 135
(48 sell-ismi). x1_ticker (fiyatlı) 67.

---

## Katman A — Evren-içi kıyas (RAW; XU100-relative DEĞİL — birincil)
Sell-flagged drift'i vs non-sell (buy+kontrol) drift'i, ham getiri %:

| horizon | N sell | N non-sell | ham fark (sell−nonsell) | size/likidite-ayarlı fark | perm-p (mean) | perm-p (median) | bootstrap %95 CI |
|---|---|---|---|---|---|---|---|
| 21g | 133 | 293 | −3,10 | −3,30 | 0,113 | 0,111 | [−6,77 ; +0,75] |
| 42g | 130 | 292 | −3,72 | −4,09 | 0,199 | 0,274 | [−9,51 ; +2,03] |
| 63g | 124 | 282 | −5,47 | −11,53 | 0,208 | 0,564 | [−13,77 ; +2,92] |

→ Hiçbir horizon'da anlamlı değil (perm-p ≥ 0,11; tüm CI'lar sıfırı kesiyor). Nokta-tahminler
negatif ama **istatistiksel olarak ayrışmıyor**.

### Market-relative referans (yalnız-kıyas; medyan, vs XU100)
| horizon | sell medyan | non-sell medyan |
|---|---|---|
| 21g | −2,56 | −1,07 |
| 42g | −6,69 | −1,48 |
| 63g | **−10,85** | −0,87 |

→ Market-relative'de sell-vs-nonsell **medyan-gap büyük**, ama evren-içi RAW kıyas bunu
doğrulamıyor. Mekanizma: sell-disclosure'ları XU100'ün daha-çok-yükseldiği pencerelerde
kümeleniyor; XU100-çıkarımı sell'i orantısız cezalandırıyor. Yani 016-C'deki market-relative
sell-underperformance büyük ölçüde **timing/beta artefaktı**, hisse-bazlı gerçek-zayıflık değil.

## Katman B — Placebo / random-date (aynı sell-isimleri)
Gerçek sell-event'i vs aynı-isimlerde disclosure-olmayan rastgele-tarih:

| horizon | N sell | N placebo | fark (sell−placebo) | perm-p (median) | bootstrap %95 CI |
|---|---|---|---|---|---|
| 21g | 133 | 135 | −3,76 | 0,658 | [−8,43 ; +0,87] |
| 42g | 130 | 135 | −6,63 | 0,286 | [−13,98 ; +0,65] |
| 63g | 124 | 135 | −8,27 | 0,282 | [−18,90 ; +2,23] |

→ Gerçek sell-drift'i aynı-isimlerin placebo-drift'inden **anlamlı ayrışmıyor** (perm-p ≥ 0,28).
Drift event'e değil, **isme** bağlı görünüyor.

---

## Net teşhis (betimsel, hüküm-değil)

**(ii-a) evren/timing-confound — tüm horizonlar.** X1 sell-side negatif drift'i confound-kontrolünü
**geçmiyor**:
- **Katman A:** sell, evren-içi non-sell'den (buy+kontrol) anlamlı ayrışmıyor (perm-p 0,11–0,56).
  Market-relative gap'in büyük kısmı sell-disclosure'larının güçlü-piyasa pencerelerinde
  kümelenmesinden gelen **timing/beta artefaktı**.
- **Katman B:** sell-drift'i aynı-isimlerin placebo'sundan ayrışmıyor (perm-p 0,28–0,66) → **event-bağlı
  değil, isim-sabit** (ii-b ile de tutarlı).
- Nokta-tahminler negatif eğilimli ama **anlamsız** → "gerçek event-bağlı asimetri" (i) **kurulamıyor**.

Bu, ABD-literatürüyle (Lakonishok-Lee: insider-satışı bilgilendirici-değil) hizalı ve 016-C resmini
**pekiştiriyor:** trade-edilebilir buy-side'da edge yok (016-C); trade-edilemeyen sell-side'ın görünür
"sinyali" de büyük ölçüde confound (016-D).

**Stage-0 kararına etki (X2 mühürlü):** mevcut kanıt insider-disclosure ekseninde bir buy-side
Stage-0'ı **motive etmiyor**; sell-side hem invariant-bloklu hem confound-eğilimli. Karar maintainer'a.

## Caveat'lar
- **Underpowered null:** N mütevazı (147 sell-olay / 48 sell-isim). "Ayrışmıyor" ≠ "yok kanıtı";
  confound-tutarlı + güç-zayıf. Nokta-tahminler negatif eğilimli kalıyor.
- Mean vs median perm-p yakın (fat-tail'e rağmen sonuç sağlam: ikisi de NS).
- Within-universe RAW birincil; market-relative referans-only.
- Kontrol/placebo = >90g disclosure'dan uzak psödo-olaylar; size/likidite = likidite-decile-stratifiye
  (ince hücreler düşürüldü).
- Fresh-scrape soyu, kanonik-panel-değil. Sell-side yalnız-teşhis (long-only/no-short korunur).

---

**Kapsam-uyumu:** Stage-0-açılmadı, keep-bar-değerlendirilmedi, sign-flip-yok, composite-optimize-yok,
X2-dokunulmadı. Betimsel-çıktı hüküm-değil. Sell-side trade-aday sayılmadı. measurement-verification
(DISC-10) kendiliğinden-tetiklenmedi. Ham: [`RR-Y1-016-D-confound-result.json`](RR-Y1-016-D-confound-result.json);
script: [`scripts/probe/rr_y1_016_d_confound.py`](../../scripts/probe/rr_y1_016_d_confound.py).
