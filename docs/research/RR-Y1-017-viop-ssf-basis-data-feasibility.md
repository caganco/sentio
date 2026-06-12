# RR-Y1-017 — VİOP single-stock-futures (SSF) basis/price-discovery DATA-FEASIBILITY probe

**Sınıf:** Veri-erişilebilirlik probu. **Stage-0-DEĞİL**, ölçüm-DEĞİL, edge-iddiası-DEĞİL,
hipotez-testi-DEĞİL. Hiçbir getiri/sinyal/faktör/backtest hesaplanmadı. Yalnız **veri-olgular**:
var-mı, nerede, hangi kapsama, hangi erişim-yolu, hangi kalite/boşluk. **Go/no-go kararı bu
rapora ait değildir** — maintainer'a aittir.

**Kapsam-ayrımı (ZORUNLU):** Bu prob **basis = futures − spot** (fiyat/uzlaşma) değişkenini
inceler. **Open-interest (OI) ayrı ve mühürlü bir mezarlık değişkenidir** — bu repodaki
`viop_ssf_oi_k2` (axis=derivative-oi, verdict=FAIL, revival_status=PERMANENT, S#15) ve lab-demo
L21-OI işine **dokunulmadı, çalıştırılmadı**; yalnız varlığı not edildi. Basis ≠ OI; iki değişken
kesinlikle ayrı tutulur. Measurement-verification (DISC-10) tetiklenmedi — ölçüm yok.

---

## A. Offline envanter (mevcut repo/disk)

### A.1 — SSF uzlaşma/fiyat serisi — **VAR (kanonik offline arşiv)**

| Alan | Bulgu |
|---|---|
| Yol | `data/bist_datastore_archive/viop/` (kanonik arşiv, repo-içi göreli yol) |
| Tip | Gün-sonu fiyat/hacim arşivi (per-kontrat, per-gün) |
| Format | CSV, `;`-ayraçlı, Latin-1/windows-1254, 2 başlık-satırı (TR+EN); pre-2017 `.csv.gz`; 2020-06+ `VIOP_AS_*` (AHT) |
| Dosya deseni | `VIOP_GUNSONU_FIYATHACIM.M.YYYYMM.csv` (~256 aylık dosya) |
| Kapsama (tarih) | 2005 → 2026 ham; **yoğun/eşleşmiş 2019-2026** |
| Kapsama (ticker) | ~**63 distinct SSF dayanak** (segment `SSF` / `D_EQ_FPD`) + index futures (`INF` / `D_IX_FUT`, ayrı) |
| Fiyat-ayağı | **UZLASMA FIYATI (settlement)** = basis için çekirdek fiyat. Ayrıca açılış/yüksek/düşük/kapanış/VWAP, ISLEM_HACMI |
| Dayanak-eşleme | **DAYANAK VARLIK** kolonu (örn. `GARAN.E`) → `.E` strip → bare ticker (spot eşleme doğrudan dosyada) |
| Provenance | **Kanonik** — BIST DataStore ürün **3208** (`VIOP_GUNSONU_FIYATHACIM`). Fresh-scrape DEĞİL. |
| Look-ahead | Gün-sonu/ay-sonu snapshot; settlement = hesaplanan gün-sonu uzlaşma (son-trade DEĞİL). |

> Aynı dosyada **ACIK POZISYON (OI)** kolonu da bulunur — bu **Bucket-B (mezarlık)** değişkenidir,
> basis-probu için **okunmadı/kullanılmadı**. Basis yalnız UZLASMA + spot kullanır.

### A.2 — Eşleşen spot serisi — **VAR**

| Artifact | Yol | Kapsama | Provenance | Reusable? |
|---|---|---|---|---|
| `adjusted_prices_2019_2026.parquet` | lab-demo-goal data | 2019-2026, **63/63 SSF ticker eşleşti (100%)** | proje-paneli | ✅ basis spot-ayağı |
| `faz0_*_prices.parquet` | `data/snapshots/` | 2019-2026 / 2024-2026 spot OHLCV | snapshot | ✅ alternatif spot |
| `clean_universe_builder.py` (D-200/202) | `src/data/` | 3196 + corp-action, back-adjusted + total-return, PIT/survivorship-clean | kanonik | ✅ temiz spot inşası |

> Not: futures **ham** fiyatı izler; L23 basis'i **RAW spot close** ile kurmuş (doğru eşleştirme).
> Adjusted vs raw karıştırmak basis'i yanlı kılar → A.2'de her iki seri de mevcut.

### A.3 — Roll/expiry takvimi + kontrat-spec — **VAR (kod-içi, türetilmiş)**

| Öğe | Bulgu |
|---|---|
| Expiry kaynağı | Kontrat kodu `F_<TICKER><MMYY>` (örn. `F_GARAN0726` = Tem-2026) ay+yıl gömülü; 2020-06+ AHT dosyalarında ayrıca `VADE_TARIHI` (YYYY-MM-DD) kolonu |
| Front seçimi | DTE ≥ 10 gün, cari-ay-vade dışlanır → harness'lerde implemente (`l21/l22/l23`, `viop_loader.py`) |
| Loader | `src/data/viop_loader.py` — 3208 parse, schema-versiyon-tespiti (pre-2017 gz / 2020-07 redenomination / AHT), front-month agg, expiry parse |

### A.4 — **3-öğeli panel ZATEN KURULMUŞ** (önceki iş — lab-demo-goal, AYRI repo)

Basis paneli yalnız *kurulabilir* değil, **bir kez fiilen kurulmuş** durumda (veri-olgu olarak rapor
edilir; **bu önceki thread'lerin getiri/hüküm-içeriği bu veri-probunun kapsamı dışındadır** — onlar
lab-demo-goal'da kapalı thread'lerdir, herhangi bir bulgu-atfı maintainer'a aittir):

| Thread | Yol | Veri-içeriği (olgu) | Kapsama |
|---|---|---|---|
| **L23** (SS funding-basis) | `lab-demo-goal/harness/l23_viop_ss_basis.py` + `stage0/STAGE0_L23...json` + `results/...json` | `basis_ann = ln(F_settle/S_close)/(dte/365)`; front SSF ↔ raw spot, ay-sonu | **3.906 basis gözlemi / 89 ay / 63 ticker / 2019-2026, 100% eşleşme** |
| **L22** (index-futures term-structure) | `lab-demo-goal/harness/l22_viop_term_structure.py` (+ stage0/results) | F1 vs F2 settlement, annualized slope (INF segment, `F_XU030MMYY`) | 389 eğri-gözlemi / 111 ay-sonu / 2017-03..2026-05 |
| **L21** (SSF OI cross-section) | `lab-demo-goal/harness/l21_viop_oi_xs.py` | **Bucket-B (OI)** — not edildi, çalıştırılmadı | (OI; kapsam-dışı) |

> **Kritik olgu:** L23, futures-settlement ↔ spot eşleştirmesini ve basis serisini **2019-2026 / 63
> ticker / 100% match** ile fiilen üretmiş. Yani basis veri-paneli için **veri-edinim darboğazı yok**.

### A.5 — Yeniden-kullanılabilir altyapı

`viop_loader.py` (3208 parser), `viop_fetcher.py` (canlı EOD bülten, `borsaistanbul.com/data/vadeli/`),
`bist_datastore_client.py` (D-130, auth'lı 3208 indirici), `data_hub.py` (kaynak-router), `tr_index`,
`clean_universe_builder.py`. Hepsi basis+spot panelini birleştirmeye doğrudan uygulanabilir.

---

## B. Online erişim haritası (READ-ONLY araştırma; hesap/satın-alma/indirme YOK)

| Öğe | Public mi / Paywall mı | Kaynak | Maliyet / temas | Not |
|---|---|---|---|---|
| **SSF gün-sonu/settlement geçmişi** | **Registration/paywall-gated** | DataStore portalı `datastore.borsaistanbul.com` ("Historical data … available at DataStore") | **Letter of Undertaking** zorunlu; fiyat **açıklanmamış** (sayfa pricing belirtmiyor) | **Offline arşivin (3208) menşei budur** → mevcut panel için paywall **engel değil**; yalnız taze-uzatma/yeniden-çekim için gerekir |
| Settlement-fiyat **metodolojisi** | **Public (ücretsiz)** | `borsaistanbul.com/.../viop` | — | Gün-sonu = son-10-dk VWAP (fallback'lı); **final settlement = son-işlem-günü spot-kapanış** |
| **Roll/expiry takvimi + kontrat-spec** | **Public (ücretsiz)** | `borsaistanbul.com/.../viop/contract-specifications`, `.../maturity-months`, `.../contract-codes` | — | Vade & son-işlem-günü = kontrat-ayının son-iş-günü; 3 ardışık ay; 100 pay/kontrat; fiziki teslim |
| **Dayanak→SSF sembol eşleme** | **Kısmen public** | `.../data-vendor-symbols-viop` (Bloomberg `SFUT TI`, Reuters `AEFESc1`); `derivatives-market-procedure.pdf` | — | İndirilebilir dayanak↔kontrat map dosyası YOK; isim-konvansiyonundan çıkarılabilir. **Offline `DAYANAK VARLIK` kolonu bunu zaten çözüyor** |
| 3.-taraf vendor (geçmiş+canlı) | Ticari (kayıt-olunmadı) | **dxFeed** (BIST futures real-time+historical), **Bloomberg** (`SFUT TI`), **Refinitiv/LSEG** (`AEFESc1`), Investing.com (BIST30 futures) | vendor-fiyatı | Hiçbirine kayıt/abonelik açılmadı; yalnız varlık-tespiti |

**Paywall-olgusu (geçerli bulgu):** SSF settlement geçmişinin *canlı* resmi kanalı DataStore'dur ve
Letter-of-Undertaking + login arkasındadır (3196/takas paywall pattern'iyle aynı). Bypass denenmedi.

---

## C. Constructibility özeti (hüküm değil — olgu)

**Panel = (1) SSF settlement + (2) eşleşen spot + (3) roll/expiry takvimi.**

- **(offline-only) → KURULABILIR (zaten kuruldu).** Üç öğe de diskte mevcut: (1) 3208 arşivi
  UZLASMA + DAYANAK VARLIK, (2) `adjusted_prices_2019_2026.parquet` raw+adjusted spot (63/63 match),
  (3) kontrat-kodu/`VADE_TARIHI` + front-DTE≥10 mantığı. **L23 bu paneli fiilen 2019-2026 / 63 ticker
  / 3.906 gözlem / 100% eşleşme ile üretti.** Hiçbir online-bağımlılık gerekmez.
- **(offline + free-online) → ek-doğrulama mümkün.** Roll/expiry takvimi & kontrat-spec public-ücretsiz
  BIST sayfalarından bağımsız teyit/yenileme alır (gömülü-kod expiry-çözümünü doğrular).
- **(paywall-blocked) → YALNIZCA şu durumlarda:** arşiv-ötesi **taze SSF settlement uzatması** veya
  bağımsız vendor-temiz seri istenirse → DataStore (LoU + login, fiyat-açıklanmamış) veya ücretli
  vendor (dxFeed/Bloomberg/Refinitiv). Mevcut 2019-2026 paneli için **gerekli değil**.

**Spesifik blocker:** Mevcut panel için **blocker yok**. Tek koşullu-blocker, panelin offline-arşiv-
ötesine (taze/uzatılmış settlement) genişletilmesidir — o noktada DataStore-paywall devreye girer.

---

## D. Veri-kalitesi / look-ahead / roll-inşa riskleri (yalnız olgu)

1. **Convergence-to-expiry (mekanik).** Final settlement = son-işlem-günü spot-kapanış → basis vade-
   sonunda mekanik olarak **→0**. Ay-sonu snapshot near-expiry kontratla çakışırsa roll-down/convergence
   basis'i yapay-küçültür. Front-DTE≥10 + cari-ay-dışlama bu yüzden zaten harness'lerde uygulanıyor.
2. **Settlement ≠ son-trade.** UZLASMA = hesaplanan gün-sonu uzlaşma (son-10-dk VWAP / fallback'lar).
   Basis settle↔spot-close kıyaslar; ikisi farklı fiyat-tanımı → tutarlı-tanım korunmalı.
3. **Adjusted vs raw spot.** Futures **ham** fiyatı izler; basis **raw spot close** ile kurulmalı
   (L23 böyle yapmış). Corp-action-adjusted spot ile karıştırmak basis'i yanlı kılar. A.2'de her iki
   seri de mevcut → doğru-ayağı seçmek inşa-kararı.
4. **Roll-inşa.** SSF vade = ayın-son-iş-günü; fiziki teslim; uzak-aylar ince → roll, illikit back-ay
   settlement'ında stale-fiyat riskine maruz. Front-month dışlaması en-likit kontratı da çıkarabilir
   (aynı arşivde OI-tarafında bilinen yapısal-uyarı; basis tarafında da geçerli inşa-notu).
5. **Şema-versiyonları.** Pre-2017 `.csv.gz` İngilizce-kolonlar; 2020-07 index-redenomination (index
   futures'ta 2 sıfır düştü — **SSF `D_EQ_FPD` etkilenmez**); 2020-06+ AHT `VIOP_AS_*`. `viop_loader.py`
   şema-tespiti yapıyor; encoding windows-1254 (UTF-8-zorlama gerekebilir).
6. **Kapsama/genişlik.** ~63 SSF dayanak = ince cross-section; yoğun 2019-2026, pre-2019 seyrek.
7. **Provenance-soyu.** Futures-ayağı **kanonik** (DataStore 3208 offline arşiv); spot-ayağı proje
   temiz-paneli. L23 basis paneli **kanonik-arşiv soyu** (insider-eksenindeki fresh-scrape soyundan
   FARKLI — taze-scrape DEĞİL).
8. **OI-ayrımı.** ACIK POZISYON aynı dosyada ama basis-değişkeni değil; OI-mezarlığı (`viop_ssf_oi_k2`,
   PERMANENT) ayrı tutuldu, okunmadı/çalıştırılmadı.

---

## Caveat'lar
- **Yalnız veri-erişilebilirlik** — getiri/sinyal/edge ölçülmedi (kapsam-dışı, tasarım gereği).
- Online araştırma READ-ONLY: hesap-açma/satın-alma/paywall-indirme/CAPTCHA/form **YOK**. Paywall
  bulgusu olduğu-gibi rapor edildi, bypass denenmedi.
- L21/L22/L23 önceki thread'lerin **getiri/hüküm içeriği bu raporun kapsamı dışıdır**; yalnız
  veri-artefakt olarak (panel-var, kapsama, eşleşme) referans verildi.
- Go/no-go **maintainer kararıdır**; bu rapor olgu-sağlar, hüküm-vermez.

Kaynaklar (online, read-only):
[DataStore/Historical Data Sales](https://www.borsaistanbul.com/en/data/historical-data-sales) ·
[Contract Specifications](https://www.borsaistanbul.com/en/markets/viop/contract-specifications) ·
[Maturity / Last Trading Day](https://www.borsaistanbul.com/en/markets/viop/contract-specifications/maturity-months) ·
[Single Stock Futures](https://www.borsaistanbul.com/en/markets/viop/futures/single-stock-futures) ·
[Data Vendor Symbols — VIOP](https://www.borsaistanbul.com/en/markets/viop/market-functioning/data-vendor-symbols-viop) ·
[dxFeed BIST futures](https://dxfeed.com/market-data/futures/borsa-istanbul-futures/)
