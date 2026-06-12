# RR-Y1-016 — Insider-disclosure ekseni: fizibilite-probu + lokalizasyon

**Sınıf:** DISC-5 fizibilite-zinciri · veri-mimari-öncesi · **Stage-0-DEĞİL** · salt-okuma ile
üretildi (hiçbir analiz koşturulmadı, hiçbir keep-bar/eşik değerlendirilmedi, hiçbir motor
dosyası değiştirilmedi). Çıktı **betimseldir ve karar-girdisidir**, performans-hükmü değildir.

**Amaç.** KAP insider-disclosure (içeriden-öğrenen bildirim) ekseninin Stage-0 ön-kayda değip
değmediğini, ölçümden-önce dört-kapıyla belirlemek; ve denetim-referansında geçen
**"edge satış-tarafında olabilir, alış-tarafında zayıf" (F1/F2) asimetri-bulgusunun**
ölçülmüş bir sonuç mu yoksa hipotez mi olduğunu lokalize etmek.

**Veri-kaynağı.** Insider-disclosure flow repo'su (ayrı ingest servisi: KAP insider-bildirim +
Ticaret-Sicil; Postgres arka-uç). Kod yolları aşağıda göreli (`src/flow_intel/...`) verilmiştir.

---

## 0. Arama yüzeyi

| konum | durum |
|-------|-------|
| insider-disclosure flow repo (master + 2 branch) | tarandı — yön-analizi yalnız burada |
| `lab-demo-clone1` (CONSTRUCTION-as-EDGE, C-serisi) | tarandı — buy/sell yön-asimetri ölçümü **yok** |
| `lab-demo-goal` (edge-discovery, L1-L23) | tarandı — yok |
| sentio `docs/` ağacı (master + branch'ler) | tarandı — F1/F2 asimetri-ölçümü **yok** |
| `lab-demo-clone2` | **diskte mevcut değil** (referansta öncelikli denmişti; yok) |

Yöntem: filename + içerik grep (her branch tree), commit-mesaj arama, lab tree'leri. Buy/sell
yön-asimetri terimleri (`sell-side`/`buy-side`/`asimetri`/`satış-tarafı`/`alış-tarafı`/`F1`/`F2`)
flow repo'da ve sentio docs'ta **sıfır eşleşme**.

---

## 1. Lokalizasyon hükmü — F1/F2 = ÖLÇÜLMEMİŞ HİPOTEZ

**"Edge sell-side'da olabilir, buy-side zayıf" asimetrisinin BIST-verisinde ölçülmüş hiçbir
kanıt-dosyası yoktur.** Dosyalarda literally ne yazdığı:

- **Pipeline buy-only.** `src/flow_intel/signals/cluster.py:136` → `.where(transaction_type == "BUY")`;
  docstring *"scan ALL BUY transactions in history"*. `signals/cross_reference.py:59` →
  `WHERE kit.transaction_type = 'BUY'`. Küme → outcome → base_rate zincirinin tamamı **yalnız
  alış** kümeleri üzerinde çalışır.
- **Sell-side hiç ölçülmemiş.** SELL işlemleri tx-graninde saklanır
  (`models/kap.py`: `CheckConstraint("transaction_type IN ('BUY','SELL')")`) ama **hiçbir zaman
  kümelenmez / outcome üretmez / getiri-testine girmez** → `signal_outcomes`'ta sell-side satır = **0**.
- **Asimetri hiçbir yerde geçmiyor.** Flow repo'da "sell-side/buy-side/asimetri" grep'i boş.
  `reports/_audit/*` brief'leri ağ/koordinasyon forensiği (NET_BUY pressure, composite anomaly
  86.5) — getiri-asimetri **testi değil**.
- Asimetri-iddiasının kaynağı **literatür** (Tahaoğlu-Güner 2010 ve benzeri), ölçülmüş
  BIST-sonucu değil.

**Ek soru — buy-side-only daha önce BIST'te test edildi mi? EVET (ama look-ahead-kirli).**
Flow pipeline'ının tamamı buy-side-only bir konstrüksiyon ve çalıştırılmış: yerel Postgres'te
gerçek alış-kümesi roster'ı mevcut (`output_reports/.radar_state.json`: KAPLM skor 85, MACKO ×4,
ENKAI, AKSA, BEGYO, GENIL…). Mevcut betimsel buy-side getiri çıktısı — **örnek/illustratif
artefakt** (`reports/sample/daily_signal.example.json`, ticker maskeli; **gerçek-ölçüm değil**):

| horizon | N (outcome) | hit-rate | medyan ret | ort ret |
|---------|-------------|----------|------------|---------|
| 5g  | 29 | 44.8% | −1.87% | −2.0%  |
| 20g | 29 | 55.2% | +3.81% | −0.48% |
| 60g | 23 | 52.2% | +0.61% | +5.91% |

> Çıplak-getiri (market-relative değil), maliyet-öncesi, N≈30, ve **look-ahead-kirli** (aşağı G1).
> Hüküm verilemez; sell-side karşılığı olmadığı için **asimetri ölçülemez**.

---

## 2. Dört-kapı fizibilite tablosu

| Kapı | Verdict | Kanıt + gerekçe |
|------|---------|-----------------|
| **G1 — Look-ahead-safe gün-damgası** | **CONDITIONAL** | PIT alanı **var**: `models/kap.py KapDisclosure.published_at` (TZ-stamp), `scrapers/kap/parser.py:262` KAP `publishDate`'ten parse; düzeltme modellenmiş (`is_correction`/`corrects_disclosure_id`; `scrapers/kap/insider.py:67` correction-dedup). **AMA** getiri-harness'ı `published_at`'i kullanmıyor: `signals/returns.py:33` entry = **`window_end` (son işlem-tarihi)** close'u. Disclosure işlemden SONRA yayınlandığından, işlem-tarihinde girmek look-ahead'dır. PASS için entry → `max(published_at)` + `t+1`. Sentio precedent: `docs/event_test/STAGE0_event_confluence_preregistration.json` (`event_day=published_at`, `action=t+1`). |
| **G2 — Örneklem-gücü (iki taraf ayrı)** | **CONDITIONAL** (doğrulanmamış) | Buy-side: gerçek ama **mütevazı** roster (base_rate N≈30 outcome, illustratif). Sell-side: **N=0** (hiç kümelenmemiş). PEAD referansının (1.473 olay / 184 isim) ~bir-büyüklük-mertebesi altında. Buy-side tek-başına anlamlı-test için **sınırda**; gerçek-N canlı DB sorgusu ister (koşturulmadı). |
| **G3 — Buy/sell-asimetri teşhisi** | **FAIL (mevcut veriyle ölçülemez)** | Mekanizma var (`signals/returns.py`/`signals/base_rate.py`) ama tx-yönüne göre bölünmüyor ve sell-side outcome'u yok. Mevcut artefaktlardan asimetri-yönü **gözlenemiyor** → F1/F2 hipotez olarak kalıyor. Betimsel asimetri üretmek **yeni ölçüm** ister (bu probe'un kapsamı dışı). |
| **G4 — PM-1 uyumu** | **PASS (buy-side)** | Buy-side sinyal doğası gereği **sepet-içi-tilt**: kümeler `cluster_score` ile sıralanır (`base_rate.py min_cluster_score`), nakit-gate gerektirmez → PM-1 uyumlu. Sell-side long-only/no-short invariant'ı altında **trade-edilemez**, yalnız teşhis. |

---

## 3. Net tavsiye

**"Koşullu Stage-0'a-değer — ama önce iki blocker giderilmeli."** Sıralama:

1. **G1-fix (zorunlu ön-koşul):** getiri-girişini `published_at` + `t+1`'e re-key et; aksi halde
   her ölçüm look-ahead-kirli. Düşük efor; precedent mevcut.
2. **G2-backfill (zorunlu):** sell-side'ı tx-graninden olay-pencereleri olarak kur (kümeleme şart
   değil) + buy-side N'i gerçek-DB'den doğrula. Buy-side N anlamlı-güç mertebesine yaklaşmıyorsa
   Stage-0 güç-zayıf kalır.
3. Ancak (1)+(2) sonrası **G3 betimsel asimetri** anlamlı koşulabilir; o çıktı Stage-0 ön-kayıt
   kararının girdisi olur.

**Sell-side yalnız teşhis** (trade-aday-değil); **yegane trade-edilebilir taraf buy-side**
(G4 PASS). Mevcut illustratif buy-side rakamı cesaret-verici görünse de **N≈30 + look-ahead-kirli +
çıplak-getiri** olduğundan düzeltmeden hüküm verilemez.

**Takip:** G1-fix + G2-backfill implementasyonu **RR-Y1-016-B**'ye taşındı (ölçüm-altyapısı;
Stage-0-DEĞİL). Bu raporun negatif/feasibility-bilgisi kalıcı-değerlidir ve RR-Y1-015 registry
felsefesiyle tutarlıdır.

---

**Kapsam-uyumu:** Hiçbir analiz koşturulmadı, hiçbir keep-bar/edge-hükmü üretilmedi, hiçbir dosya
değiştirilmedi. G3 mevcut-veriyle ölçülemediği için betimsel-rakam **uydurulmadı** (hipotez olarak
işaretlendi). Sell-side trade-aday sayılmadı (yalnız-teşhis).
