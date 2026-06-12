# RR-Y1-017-B — VİOP SSF basis: temiz-naive-X₂ pencere fizibilitesi + eksen hükmü (save/wait)

**Sınıf:** Veri-probu (DATA PROBE ONLY). **Stage-0-DEĞİL.** Getiri-YOK, basis→forward-return
ilişkisine BAKILMADI, edge-hükmü-YOK. Bu rapordaki tek "hüküm" **eksen-statüsüdür** (save/wait) ve
yalnız **veri-mevcudiyeti + peek-durumu** olgularına dayanır — bir getiri/performans ölçümüne değil.
RR-Y1-017'nin (veri-erişilebilirlik) devamı: 017 "panel kurulabilir mi?"yi yanıtladı; 017-B "hangi
pencere **temiz/görülmemiş** (naive-X₂), hangi pencere **peek-edilmiş**?" sorusunu yanıtlar.

**Kapsam-ayrımı (ZORUNLU, 017 ile aynı):** Basis = futures − spot (fiyat/uzlaşma). **OI ayrı ve
mühürlü** (`viop_ssf_oi_k2`, axis=derivative-oi, verdict=FAIL, revival_status=PERMANENT, S#15) —
okunmadı/çalıştırılmadı. Yalnız L23 harness'inin **hangi veriyi tükettiği** (date-range, ticker-set,
basis→getiri-ilişkisine bakıp-bakmadığı) tespit edildi; **hiçbir getiri/hüküm/parametre L23'ten
içe-aktarılmadı** — "ne görüldü"yü tespit ettik, "ne bulundu"yu değil.

---

## Q1 — Kontaminasyon kapsamı: L23 hangi veriyi "gördü"?

Kaynak: `lab-demo-goal/harness/l23_viop_ss_basis.py` + `stage0/STAGE0_L23_viop_ss_basis.json`
(yalnız **veri-kapsam alanları** okundu).

| Boyut | L23'ün tükettiği veri (olgu) |
|---|---|
| Settlement (futures) ayağı | VIOP arşivi **plain** dosyalar (`VIOP_GUNSONU_FIYATHACIM.M.*.csv`); `VIOP_AS_*` AHT-varyantı **dışlandı**; segment `SSF`; settlement = `UZLASMA FIYATI` |
| **Sert tarih-clamp** | `MIN_YYYYMM = 201901` (harness sabiti) → **2019-01 öncesi her ay atlandı**; oysa plain settlement 2017-03'e kadar diskte mevcut |
| Etkin tarih-aralığı | **2019-01 … 2026-05**, ~**89 ay-sonu** (fiyat-paneli sınırlı) |
| Spot ayağı | `adjusted_prices_2019_2026.parquet` (raw `close` = basis paydası; forward return aynı panel) — kendisi de **2019+** |
| Ticker-seti | Aynı-gün spot-eşleşen SSF dayanak: **medyan 47/ay (min 29, max 51), 63 distinct** |
| **basis → forward-return'e baktı mı?** | **EVET.** `build_forward()` + `evaluate()` basis(m)'i **m+1 (birincil) ve m+2 (robustluk)** forward spot-getirisiyle eşleştirdi; tercile cross-sectional; **LIQUID + ALL** kapsamları |
| ⇒ "Görülen" (peeked) | **2019-01 … 2026-05 basis→forward-return ilişkisi** (her iki horizon, her iki kapsam) **kontamine** |
| ⇒ "Görülmemiş" (naive) | **2019-01 öncesi her şey.** 2017-03…2018-12 plain settlement diskte vardı ama clamp ile dışlandı; ona eşlenecek pre-2019 spot-paneli de yoktu → pre-2019 = **temiz / naive-X₂ aday penceresi** |

**Q1 sonucu:** Temiz-naive-X₂ aday penceresi = **pre-2019**. L23 ona hiç dokunmadı (tarih-clamp + pre-2019 spot-yokluğu).

---

## Q2 — Pre-2019 naive pencere: temiz eşleşen-spot paneli kurulabilir mi?

**Disk-olguları (salt-okuma):**
- **3196 resmi spot fiyatlar:** **1988-01 … 2026-05** (461 aylık dosya). Format-bölünmesi: **`.csv`
  2016-12 → 2026-05** (`clean_universe_builder` doğrudan `*.csv` glob'lar); **`.zip` 1988-01 →
  2016-11** (önce offline-extraction gerekir).
- **`corporate_actions/` dizini BOŞ (0 dosya)** → `clean_universe_builder` **yol-3 hybrid** yoluna
  düşer (yfinance + col-14 `ca_code` + price-implied), offline corp-action-ZIP yoluna değil.
- **VIOP settlement:** plain (L23-şeması) **2017-03 → 2026-05**; pre-2017 dosyalar **PK/zip-sarmalı
  ve FARKLI şema** (`boardid;securityshortname;tradedate;open;…` — `PAZAR SEGMENTI`/`SSF` etiketi
  YOK), L23 kolon-indeks parser'ı (`SEG_COL=3=='SSF'`) bunlar üzerinde **çalışmaz**.
- **Pre-2019 SSF cross-section:** 2017-03 ve 2018-06'da **~20 distinct dayanak** (vs 2019-2026 medyan
  ~47) — ince, L23'ün `MIN_NAMES=30` tabanının **altında**.

### Constructibility hükmü (olgu; iki alt-dönem)

| Pencere | Hüküm | Spesifik blocker / caveat |
|---|---|---|
| **2017-03 … 2018-12** (gerçekçi naive pencere) | **Kurulabilir (offline)** — caveat'lı | Settlement: plain dosyalar, L23-uyumlu, **L23 tarafından görülmemiş**. Spot: 3196 `.csv` 2016-12+ mevcut → `clean_universe` offline kurar. **Caveat A:** corp-action ZIP'leri yok → yalnız **bedelsiz** bölünmeler tam-offline ayarlanır (col-14 `'01'` + price-implied); **bedelli/rüçhan** isimleri **free-online yfinance** ister (yoksa dışlanır). **Caveat B:** ~20-isim cross-section, 30-tabanının altında (kapsam-olgusu, hüküm-değil). |
| **2005 … 2016** (derin tarih) | **Yalnız offline-mühendislik sonrası kurulabilir; kısmen-blocked** | **Blocker 1 (şema):** pre-2017 VIOP segment-siz İngilizce şema → **yeni parser + SSF-kontrat-kodu-ile-tanımlama** gerekir (`SSF` etiketi yok). **Blocker 2 (extraction):** 3196 spot pre-2016-12 `.zip` → `*.csv` glob işlemeden önce extract gerekir (offline). **Kapsam:** bu şemada SSF enumerable-değil; erken-yıllarda SSF cross-section neredeyse-boş. Network-blocked değil, ama gerçek mühendislik + ince/boş erken-SSF. |

**Redenominasyon / look-ahead olguları:**
- **2005-2018 içinde TRY redenominasyonu YOK** (6-sıfır 2005-01'de, arşiv başında/öncesinde; 2020-07
  index-redenominasyonu pencere-sonrası ve SSF `D_EQ_FPD`-etkilemez). Asıl şema-caveat'ı **2017
  plain-vs-pre-2017 İngilizce-şema kırılması**dır, redenominasyon değil.
- **Look-ahead güvenliği:** `clean_universe` back-adjustment yapı-gereği look-ahead-safe (faktör(t) =
  ex_date > t olayların suffix-çarpımı, geriye-uygulanır; D-185 survivorship-kontrolleri delisted
  isimleri içerir). Raw-close basis-paydası aynı-gün → güvenli. **Tek** look-ahead/bütünlük-riski:
  **yfinance bedelli fallback** (network-bağımlılık + pre-2019 delisted-rüçhan isimlerinde olası
  survivorship-boşluğu).

---

## Eksen hükmü: **save/wait (mezarlık-DEĞİL)**

| Olgu | Durum |
|---|---|
| Veri var mı? | **EVET** — kanonik, on-disk, 2019-2026 / 63-ticker basis paneli (L23 fiilen kurmuş, 3.906 gözlem, %100 match) |
| Güç-zengin pencere (2019-2026) | **PEEKED** — L23 basis→forward-return'e baktı (her iki horizon/kapsam) → frozen-X₂ olarak kullanılamaz (DEC-053) |
| Temiz naive-X₂ pencere (2017-2018) | **UNDERPOWERED** — ~20 SSF isim, 30-tabanının altında |
| Derin tarih (2005-2016) | **Blocked-ish** — yeni pre-2017 parser gerekir + erken-SSF neredeyse-boş |
| Frozen-X₂ Stage-0 koşuldu mu? | **HAYIR — X₂ hiç çalıştırılmadı** |

**Karar:** Hiçbir frozen-X₂ Stage-0 koşulmadığı için bu **bir ölçülmüş-negatif değildir** → eksen
**save/wait**, mezarlık-DEĞİL. (RR-Y1-016 insider-ekseninin save/wait kapanışıyla aynı disiplin:
X2/lockbox mühürlü kalır, ölçülmemiş bir negatif mezara yazılmaz.)

**KORUMA NOTU (PRESERVATION):** **2017-2018 penceresi temiz tek-atış X₂ olarak MÜHÜRLÜ tutulur.**
Eksen ileride yeniden-açılırsa (daha-derin SSF cross-section / vendor-uzatması ile isim-sayısı
30-tabanını aşarsa), bu pencere henüz-görülmemiş tek bağımsız doğrulama-atışıdır — şimdi peek edilirse
o değer kaybedilir. Bu pencerede basis→getiri ilişkisine **bakılmadı** ve **bakılmamalı** (gelecekteki
frozen Stage-0'a kadar).

**Prior:** low-to-medium, **prob tarafından değiştirilmedi** (bu bir veri-fizibilite + peek-haritası,
bir kanıt-güncellemesi değil).

**Ex-ante tradability duvarı (not):** SSF cross-section ince; uzak-ay (back-month) kontratlar illikit →
roll stale-back-ay settlement riskine maruz; front-month dışlaması en-likit kontratı da çıkarabilir.
Bu, bir gelecekteki Stage-0 için ham-mal-tarafı (investability) uyarısıdır.

**OI mühürlü kalır.** Hiçbir OI modülü okunmadı/çalıştırılmadı.

---

## Caveat'lar
- **Yalnız veri-kapsam + peek-haritası** — getiri/basis-getiri-ilişkisi ölçülmedi (kapsam-dışı, tasarım gereği).
- L23'ten yalnız **veri-kapsam alanları** (tarih-clamp, ticker-sayımı, evaluate-varlığı) okundu; hiçbir
  getiri/hüküm/parametre içe-aktarılmadı.
- "~20 SSF isim" 2017-03 + 2018-06 nokta-örneklemesidir; tam 2017-2018 trajektörü biraz değişebilir
  ama 30-tabanının altında olduğu olgusu sağlamdır.
- Go/no-go + Stage-0-açma **maintainer kararıdır**; bu rapor olgu+statü-sağlar, edge-hükmü-vermez.
