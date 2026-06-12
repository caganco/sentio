# RR-Y1-016-F — Cluster-intensity güç-prior kontrolü (sayım, getiri-YOK)

**Sınıf:** Prior-fizibilite / güç-kontrolü. **Stage-0-DEĞİL**, hipotez-testi-DEĞİL, edge-testi-DEĞİL.
Tek-soru: cluster-intensity ekseni bir frozen-Stage-0'ı taşıyacak **güç-varyasyonuna** sahip mi?
X1-only; **X2 mühürlü-dokunulmadı**; yeni-veri YOK; taze-scrape soyu.

**KRİTİK — getiriye BAKILMADI.** Bu yalnız küme-dağılımı sayımıdır. Cluster-getiri ilişkisine
bakmak frozen-Stage-0 ön-kaydından-önce sinyali-görmek = **DEC-053 ihlali** olurdu. Güç-önce,
getiri-sonra (ayrı, soğuk-kafa karar).

**Bağlam.** Insider-yön-ekseni kapandı (buy-side-edge-yok 016-C/E; sell-side-isim-seçilim 016-D/E).
Açık-kalan tek-meşru-soru: cluster-intensity — tek-insider-alımı değil, aynı-pencerede
N-bağımsız-insider koordineli-alım (Seyhun-tipi net-insider-pressure). Stage-0'a-değmeden-önce
güç ölçülür.

**Karar-kuralı (PRE-FROZEN).** Yüksek-yoğunluk-küme çok-az (tek-haneli-olay / bir-elin-ismi) →
cluster-Stage-0 doğmadan-ölü, eksen tümüyle-kapanır. Yeterli-N (frozen-Stage-0-taşıyabilir) →
cluster-intensity ayrı-frozen-Stage-0-adayı (ayrı karar).

**Tanım (projenin kendi config'i — `config/base.yaml`):** window=30 gün, cluster = aynı-ticker'da
30-günde ≥2 distinct-insider BUY; yoğunluk = distinct-insider sayısı.

---

## Cluster-yoğunluğu dağılımı (X1; 40 ticker, 134 BUY işlem)

**Ticker başına maksimum yoğunluk:**
| max distinct-insider | ticker sayısı |
|---|---|
| 1 | 32 |
| 2 | 6 |
| 3 | 2 |
| 4+ | 0 |

**Yüksek-yoğunluk özeti:**
| eşik | distinct isim | pencere-olayı | birleşik episode | isimler |
|---|---|---|---|---|
| ≥2 insider | **8** | 24 | 11 | AKSA, ARTMS, AVOD, ENKAI, GENIL, MOGAN, SARKY, TMPOL |
| ≥3 insider | **2** | 7 | 3 | ENKAI, MOGAN |
| ≥4 insider | **0** | 0 | 0 | — |

≥3 olayların hepsi 2025'te; likidite: 1 mid / 1 high.

---

## Karar (pre-frozen kurala göre): **DOĞMADAN-ÖLÜ (güç-yok)**

- **≥3-insider koordineli küme: yalnız 2 isim (ENKAI, MOGAN), 3 episode** — tam-tamına
  "tek-haneli-olay / bir-elin-ismi". **≥4: sıfır.**
- Projenin kendi eşiği ≥2'de bile yalnız **8 isim / 11 episode** — kesitsel bir frozen-Stage-0'ın
  (X1/X2-split + rejim-istikrarı + likidite-stratifikasyonu) gerektireceği güçten çok-uzak.
- Pre-frozen kural devreye girer → **cluster-intensity Stage-0 doğmadan-ölü; insider-disclosure
  ekseni tümüyle-kapanır (save/wait, X2 mühürlü-kalır).**

### Çıkarım
İçeriden-alım-satım açıklamaları ekseni, **bu panelde** (X1, 2025-2026) ne yön (016-C/D/E) ne de
koordinasyon-yoğunluğu (016-F) tarafında bir frozen-Stage-0'ı taşıyacak ham-mal taşımıyor:
- Yön: trade-edilebilir buy-side edge-siz; sell-side isim-seçilim/un-tradeable.
- Yoğunluk: ≥3-insider kümeler tek-elde sayılır → güç-yok.

**Save/wait notu (dürüst sınır):** Bu X1-yarısı + 2025-2026 penceresidir. Tam-panel (X2 + 2019-geri)
sayıları büyütür, ama (a) X2 mühürlü (dokunulmaz), (b) 2019'a-genişletme FAIL-eğilimli-eksende
"biraz-daha-derine" örüntüsüdür ve ≥3-küme sayısı tam-panelde-bile düşük-onlarda kalır → kesitsel
güç hâlâ sınırda. Eksen şimdilik **save/wait** ile kapanır; yeni-veri-akışı (radar zamanla biriktirir)
ileride yeniden-açabilir, ama bu bugünün-kararı-değil.

## Caveat'lar
- **Yalnız sayım — getiri ölçülmedi** (DEC-053-güvenli; güç-önce-getiri-sonra).
- Cluster = proje config'i (30g, ≥2 distinct-insider).
- "distinct insider" = distinct `insider_name`; ilişkili-taraflar dahil olabilir → bağımsızlık
  **üst-sınırı** (gerçek-bağımsız-insider bundan az olabilir, yani güç daha-da-zayıf).
- Pencere-olayları örtüşen-pencereleri fazla-sayar; **distinct-isim** ve **birleşik-episode** sağlam-sayımdır.
- X1-only, taze-scrape soyu, X2 mühürlü. measurement-verification (DISC-10) kendiliğinden-tetiklenmedi.

Ham: [`RR-Y1-016-F-cluster-intensity-result.json`](RR-Y1-016-F-cluster-intensity-result.json);
script: [`scripts/probe/rr_y1_016_f_cluster_intensity.py`](../../scripts/probe/rr_y1_016_f_cluster_intensity.py).
