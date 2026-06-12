# RR-Y1-016-B — Insider-disclosure ölçüm-altyapısı (G1-fix + G2-backfill)

**Sınıf:** Fizibilite-implementasyonu. RR-Y1-016 (§2) dört-kapısının **G1 + G2**'sini
ölçülebilir-kılar. **Stage-0-DEĞİL** — hiçbir keep-bar/eşik/edge-hükmü değerlendirilmedi.
Çıktı betimseldir ve karar-girdisidir, performans-hükmü değildir.

**Bağlam.** RR-Y1-016 feasibility-probu iki blocker tespit etti: **G1 look-ahead-kirli**
(`returns.py` entry = `window_end` işlem-tarihi, `published_at` değil) ve **G2 buy-side-N
illustratif/doğrulanmamış + sell-side N=0**. Literatür (Tahaoğlu-Güner 2010) standart-yöntemin
"kamuya-açıklanma-gününü-izleyen-gün (t+1) girişi" olduğunu doğrular.

**Kod-konumu.** Ölçüm-harness'ı ayrı insider-disclosure ingest servisindedir
(`caganco/trailingedge`, paket `trailing_edge`). İmplementasyon orada PR olarak açıldı; bu rapor
sentio research-registry'sinde izlenir. Kod yolları aşağıda göreli (`src/trailing_edge/...`).

---

## Durum özeti (İŞ bazında)

| İŞ | Durum | Açıklama |
|----|-------|----------|
| **İŞ-1 — G1 look-ahead-safe re-key** | **DONE + unit-tested** | Kod yazıldı, pure-unit testlerle doğrulandı (DB-siz). |
| **İŞ-3 — sell-side olay-penceresi** | **DONE + unit-tested** | Diagnostic-only builder + grouping testleri. |
| **İŞ-2 — buy-side gerçek-N** | **DB-ERTELENDİ** | Canlı `flow_intel` Postgres gerektirir; bu ortamda Docker kurulu değil, port 5432 kapalı → ger&ccedil;ek-sorgu koşulamadı. Rakam uydurulmadı. |
| **İŞ-4 — betimsel base_rate (iki taraf)** | **DB-ERTELENDİ** | DB + fiyat-verisi gerektirir; aynı blocker. |

> **Neden ertelendi (dürüst kayıt):** ölçüm-DB'si (insider-transaction + price_history) bir
> docker `pgdata` volume'ünde yaşıyor; bu çalışma-ortamında Docker yok (`command not found`,
> Docker Desktop süreci yok), 5432 kapalı. Sahte-N / sahte-asimetri **üretilmedi**. Kod-altyapı
> hazır; İŞ-2/İŞ-4 DB ayağa kalkınca tek-komutla koşulabilir.

---

## İŞ-1 — G1 look-ahead-safe re-key (DONE)

**Problem.** `signals/returns.py` entry = `get_price_on_date(ticker, window_end)`, yani kümenin
**son işlem-tarihi** kapanışı. İşlem-tarihi, KAP bildirimi yayınlanana kadar **gizli**dir
(filing-lag); o tarihte girmek t-anında-bilinmeyen bilgi kullanır → look-ahead.

**Çözüm.** Entry artık **look-ahead-safe signal-date**'e bağlandı:
- `signal_date = max(published_at)` — kümenin pencere-içi BUY işlemlerini taşıyan disclosure'lar
  **+ onları düzelten** disclosure'lar (`corrects_disclosure_id`) üzerinden. Düzeltme sadece
  daha-geç bir `published_at`'tir; `max` doğal olarak düzeltmeyi seçer.
- entry = `published_at` + **t+1** (signal-date'ten kesin-sonraki ilk işlem-günü kapanışı).
- exit = entry'den `horizon` işlem-günü sonra.
- Public-disclosure'ı çözülemeyen küme **atlanır** (look-ahead-safe girilemez; işlem-tarihine
  fallback YOK).
- `signal_date < window_end` **imkânsız** (disclosure, raporladığı işlemden önce olamaz) →
  sert look-ahead-ihlali, fail-loud.

**Tasarım.** Saf karar-mantığı (`look_ahead_safe_signal_date`, `entry_exit_offsets`) DB-bağımlı
küme-çözücüden (`resolve_cluster_signal_dates`) ayrıldı; böylece look-ahead invariant'ı
**DB-siz** unit-test edilir.

**Doğrulama (assertion + test).** İnvariant: hiçbir trade-kararı t-anında-bilinmeyen bilgiyle
alınamaz. Pure-unit testler (DB-siz) bunu kanıtlar — özellikle `test_late_filing_entry_is_after_
public_date_not_transaction_date`: işlem 2025-10-31 (gizli), KAP-yayını 2025-11-05 → signal_date =
2025-11-05, entry **kesin-sonra** (t+1), işlem-tarihinden değil. Ayrıca düzeltme-geç-kazanır,
tz→İstanbul-tarihi, boş-girdi-ValueError, t+1-offset (5/10/21/42/63-horizon).

**Etkilenen dosyalar (İŞ-1):** `src/trailing_edge/signals/entry_timing.py` (yeni),
`src/trailing_edge/signals/returns.py` (re-key), `tests/unit/signals/test_entry_timing.py` (yeni).

**Bilinen caveat (saklanmadı, dürüst-kayıt).** Aynı `disclosureIndex` altında **yerinde**
yapılan düzeltme `published_at`'i ilerletmiyor (upsert onu değiştirmiyor) ve
`corrects_disclosure_id` doldurulmuyor. Bu vakalar için geç-public-an stored-field'lardan
çözülemez. Doğru-davranış: düzeltmede `published_at`'i ilerleten **scraper-tarafı düzeltme**
(İŞ-2 backfill ile birlikte); ingestion-time gibi non-PIT damga ile **etrafından dolanılmadı**.

---

## İŞ-3 — sell-side olay-penceresi (DONE, diagnostic-only)

`signals/sell_side.py`: her **SELL-içeren disclosure** = bir olay (kümeleme YOK; betimsel
asimetri-teşhisi için kümeleme gereksiz). Olay-penceresi = disclosure içindeki SELL
işlem-tarihlerinin [min, max]'ı; insider-dedup + değer-toplamı.

**İnvariant-hatırlatma (kod docstring'inde de):** portföy long-only/no-short. Sell-side olayları
**ASLA trade-aday değil**; yalnız buy-vs-sell betimsel-asimetriyi ölçülebilir-kılmak için var.
Betimsel getiri-hesabı (İŞ-4) bilerek burada yapılmadı.

**Tasarım.** Saf gruplama (`group_sell_side_events`) DB-fetch'ten (`build_sell_side_events`)
ayrı → DB-siz unit-test.

**Etkilenen dosyalar (İŞ-3):** `src/trailing_edge/signals/sell_side.py` (yeni),
`tests/unit/signals/test_sell_side.py` (yeni).

**Caveat — olay-tanımı asimetrisi (İŞ-4 için kontrol-edilmeli).** Buy-side = çok-insider'lı küme
(`detect_clusters`, ≥min_count); sell-side = per-disclosure. İŞ-4 betimsel kıyasında bu
tanım-farkı kontrol-edilmeli (apples-to-apples), yoksa "asimetri" event-tanımından gelebilir.

---

## İŞ-2 / İŞ-4 — DB-ertelendi (ne koşulacak)

DB ayağa kalktığında, look-ahead-safe (İŞ-1) temiz girişle:
- **İŞ-2:** buy-side gerçek-N (olay + benzersiz-isim), yıllara/likidite-tabakasına dağılım,
  PEAD-referansı (1.473-olay/184-isim) ile mertebe-kıyası. (Ham buy-cluster roster için
  `output_reports/.radar_state.json` ön-bakış sağlar; gerçek-N DB-sorgusu gerektirir.)
- **İŞ-4:** buy-side ve sell-side betimsel post-disclosure getiri-profili (5/10/21/42/63-gün,
  Tahaoğlu-Güner-uyumlu), **market-relative** (en-az), mümkünse EW-relative; hit-rate + medyan +
  ortalama, her-iki-taraf-ayrı, **yorumsuz**.

---

## Net tavsiye

**Kod-altyapı G1-temiz + sell-side-ölçülebilir; kalan tek-kapı betimsel-asimetrinin (İŞ-4)
gerçek-DB'de koşulması.** O çıktı, eksenin Stage-0 ön-kaydına değip-değmediği kararının girdisi
olacak. **Stage-0'a-değer mi?** — buy-side N anlamlı-güç mertebesine ulaşıyorsa **VE** İŞ-4
betimsel buy-side getirisi sıfır-olmayan-yön gösteriyorsa **koşullu-EVET**; aksi halde
RR-Y1-014 PEAD-FAIL precedent'iyle aynı zayıf-prior geçerli. Bu rapor **hüküm-vermez**.

---

## Etkilenen Dosyalar (Affected Files)

**Ölçüm-harness (`caganco/trailingedge`, ayrı PR):**
- `src/trailing_edge/signals/entry_timing.py` — yeni (look-ahead-safe entry timing)
- `src/trailing_edge/signals/returns.py` — entry re-key
- `src/trailing_edge/signals/sell_side.py` — yeni (diagnostic sell-side events)
- `tests/unit/signals/test_entry_timing.py` — yeni (19 test'in 13'ü)
- `tests/unit/signals/test_sell_side.py` — yeni

**Research-registry (bu repo):**
- `docs/research/RR-Y1-016-B-insider-disclosure-measurement-infra.md` — bu rapor
- `docs/RESEARCH_REGISTRY.md` — RR-Y1-016-B satırı

---

**Kapsam-uyumu:** Stage-0-AÇILMADI, keep-bar-DEĞERLENDİRİLMEDİ, sign-flip-YOK,
composite-optimize-YOK. Betimsel-çıktı hüküm-değil. Sell-side trade-aday sayılmadı (yalnız-teşhis).
measurement-verification (DISC-10) kendiliğinden-tetiklenmedi. DB-bloklu deliverable'lar için
sahte-rakam üretilmedi.
