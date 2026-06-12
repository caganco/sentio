# RR-Y1-016-E — Confound kontrolü temiz-baseline düzeltmesi (audit-remediation)

**Sınıf:** Fizibilite-teşhisi, audit-remediation. **Stage-0-DEĞİL**, keep-bar/hüküm YOK.
X1-only; **X2 mühürlü-dokunulmadı**; aynı donmuş sha256-split (`240514c3…`). Yeni-veri YOK
(016-C/D ile aynı X1). Taze-scrape soyu (kanonik-panel-değil). Betimsel, karar-girdisi.

**Audit bulgusu (D5).** RR-Y1-016-D Katman-A'da "non-sell" baseline'ı **buy-flagged + kontrol**
idi; ama buy-flagged isimleri 016-C'de negatif-drift gösterdi → **kontamine baseline** farkı
null'a-çekti, "confound" hükmü bu-baseline-seçiminden-etkilenmiş olabilir. Bu task baseline'ı
temizler ve **sonuç-öncesi-donmuş** karar-kuralıyla yeniden-koşar.

**Karar-kuralı (PRE-FROZEN, post-hoc-gevşetme-yok):** Birincil = **C1 (sell vs no-disclosure-kontrol-ONLY),
size/likidite-ayarlı**. C1 hâlâ-NS → confound SOLIDIFIED (eksen kapanır). C1 anlamlı (sell temiz-baseline'dan
negatif-sapar, size/likidite-sonrası) → confound CHALLENGED (sell-side yeniden-canlı, N-büyütme değer-kazanır).

İstatistik: 10k permutation (mean+median+stratified) + 10k bootstrap, seed=42. N: sell 147 olay/48 isim,
buy 134, kontrol 183, placebo 135.

---

## C1 — sell vs no-disclosure-kontrol ONLY (temiz baseline, BİRİNCİL)
| horizon | ham fark | size/likidite-ayarlı | **adj perm-p (karar)** | perm-p mean (pooled) | perm-p median (pooled) | bootstrap %95 CI |
|---|---|---|---|---|---|---|
| 21g | −4,00 | −4,72 | **0,045 ✓** | 0,070 | 0,157 | [−8,22 ; +0,35] |
| 42g | −5,24 | −6,57 | 0,054 (sınır) | 0,122 | 0,307 | [−11,90 ; +1,19] |
| 63g | −7,12 | −13,85 | **0,011 ✓** | 0,153 | 0,524 | [−16,54 ; +2,32] |

## C3 — buy vs no-disclosure-kontrol ONLY (trade-edilebilir taraf, bağımsız bilgi)
| horizon | ham fark | size/likidite-ayarlı | adj perm-p |
|---|---|---|---|
| 21g | −2,40 | −2,01 | 0,368 |
| 42g | −4,08 | −3,37 | 0,304 |
| 63g | −4,68 | +0,07 | 0,990 |

→ **Buy-side temiz-baseline'dan da anlamlı sapmıyor** (hepsi NS). Trade-edilebilir tarafta edge YOK (016-C teyit).

## C2 — sell vs buy (kıyas, referans)
21g adj −1,13 (p 0,78) · 42g adj −3,43 (p 0,49) · 63g adj −15,03 (**p 0,033**).

## Katman-B placebo (baseline-bağımsız; 016-D'den değişmez, referans)
sell vs aynı-isimlerin random-tarihi: 21/42/63g fark −3,8/−6,6/−8,3%, **perm-p median 0,67/0,28/0,28 → NS**.

---

## Karar (pre-frozen kurala göre): **CHALLENGED**

C1 size/likidite-ayarlı anlamlı (21g 0,045 ✓, 63g 0,011 ✓; 42g 0,054 sınır) → **confound-hükmü
sell-side için çürüdü**; sell-side yeniden-canlı soru; N-büyütme (016-B/2019-genişletme) değer kazanır.
**Audit haklıydı:** 016-D'nin "confound solidified" sonucu kontamine-baseline artefaktıydı.

### Dürüst nüans (kararı-gevşetme-değil, tam-tablo)
- Anlamlılık **yalnız size/likidite-stratified-mean'de** beliriyor; **pooled mean/median NS** (0,07–0,52)
  ve **bootstrap-CI'lar sıfırı kesiyor** → kırılgan, stratifikasyon+mean'e-bağlı, fat-tail-duyarlı.
- **Katman-B hâlâ NS:** sell, aynı-isimlerin placebo'sundan ayrışmıyor. C1-temiz-baseline-anlamlı + B-NS
  birlikte: ayrışma büyük-ölçüde **isim-seçilim** (sell-isimleri yapısal-daha-zayıf-drift'li isimler);
  **event-bağlı bilgi (i) hâlâ kurulmuş-değil.** Yani confound "evren/timing"-den (016-D) "isim-seçilim"e
  kayıyor; sell-event'in-kendisi sinyal taşıyor diyemeyiz.
- **Trade-edilebilirlik değişmedi:** buy-side (C3) temiz-baseline'da da düz → long-only sistem için
  uygulanabilir-edge YOK. Sell-side yön-bilgisi taşısa-bile invariant-bloklu (yalnız-teşhis).

## Net (betimsel, hüküm-değil)
- **Kural-çıktısı: CHALLENGED** → insider buy/sell ekseni "tümüyle-kapalı" SAYILMAZ; sell-side
  open-question olarak kalır, çözümü **daha-fazla-N** ister.
- **Ama yön düzeltmesi:** kanıt event-bağlı-bilgiden çok **isim-seçilim** + kırılgan-stratified-mean'e
  işaret ediyor; trade-edilebilir buy-side edge'siz. Stage-0 hâlâ motive-değil; N-büyütme yalnız
  **bilgi-amaçlı** (sell-side teşhisi), trade-amaçlı-değil. Karar maintainer'a.

## Caveat'lar
- Underpowered (sell 48-isim); stratified-mean-anlamlı / median+bootstrap-NS → kırılgan.
- C1 temiz-baseline birincil; C2/C3 bağlam. Karar pre-frozen C1-adj-stratified-perm'e bağlı (gevşetilmedi).
- Per-disclosure olay-granülü tüm gruplar; kontrol/placebo >90g disclosure'dan uzak psödo-olay.
- Fresh-scrape soyu, kanonik-panel-değil. Sell-side yalnız-teşhis (long-only/no-short korunur).
  X2 mühürlü. measurement-verification (DISC-10) kendiliğinden-tetiklenmedi.

Ham: [`RR-Y1-016-E-baseline-result.json`](RR-Y1-016-E-baseline-result.json);
script: [`scripts/probe/rr_y1_016_e_baseline.py`](../../scripts/probe/rr_y1_016_e_baseline.py).
