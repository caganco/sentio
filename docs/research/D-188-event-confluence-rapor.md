# D-188 — Olay-Tetikli Confluence Testi: Motor + İleri-Dönük Kayıt + Veri-Fizibilite

**Tarih:** 2026-05-31 · **Branch:** `feat/event-confluence-test` · **Tür:** Ölçüm-altyapısı + Stage 0 ön-kayıt + veri-fizibilite
**Dayanak:** RR-040 (SWING — olay-güdümlü temel), RR-041 (SİNYAL — çıkıştan-arınmış + look-ahead'siz ölçüm + zorunlu random-benchmark), RR-038 (modern BIST maliyet/rejim), DEC-039.

---

## 1. TL;DR — NE YAPILDI, NE YAPILMADI

**YAPILDI:** Olay-tetikli confluence için **iki ölçüm motoru** + **Stage 0 ön-kayıt** + **dürüst veri-fizibilite** kuruldu:
- **(3A) Backtest motoru** — temiz, network-free, sentetik-test edilebilir; token/veri gelince geçmişle koşar.
- **(3B) İleri-dönük (forward/paper) kayıt sistemi** — **bugünden** temiz, look-ahead'siz örneklem biriktirir (manuel-tetikli).
- İki-null (olay-koşullu + olaysız), Holm olay-tipi-başına AYRI, `published_at`/t+1, XU100-relative, reel-YoY sürpriz, maliyet+slippage — hepsi **sonuç görülmeden donduruldu** (DEC-046).

**YAPILMADI (bilerek):** **Ölçüm-verdict YOK.** Üç olay-türünün de dondurulabilir *tarihsel-backtest* verisi yok; ileri-dönük örneklem yeni başladı. Kirli/sığ veriyle backtest = değersiz (D-185 ~%99 max-DD artefaktı dersi). Verdict, yeterli örneklem birikince (backtest token/veri **VEYA** forward accrual ≥ `MIN_EVENTS_PER_TYPE=30`) üretilecek.

**Çapa:** Yol 2 (ana sistem, gerçek para). Bu (D-188) Yol 1 **LAB** — paralel, kâğıt-üzeri, gerçek-paraya ancak kanıtla terfi.
**Gerçekçi-beklenti (ön-kayıtlı):** bulunsa bile birkaç-puan XU100-relative kenar, **katlama değil** (Bessembinder). "Edge yok" da geçerli, değerli sonuç.

---

## 2. NEDEN BU TEST

- D-185/D-186: **saf-teknik** kısa-vade swing (S/R-flip, konsolidasyon, Donchian) → adil-null'ı **GEÇEMEDİ**, elendi. Getiri = nominal-drift + çıkış-mekanizması, giriş-becerisi DEĞİL.
- D-187: aktif maruziyet-zamanlaması (200-MA switch) da **GEÇMEDİ**.
- **Olay-tetikli** swing (katalizör + teknik teyit confluence) → **hiç test edilmedi.** RR-040/RR-041 + geniş literatür uyarısı: koşulsuz cross-sectional/IC/random-null testleri **olay-odaklı, seyrek, koşullu** kenarı YAPISAL kaçırabilir → "saf-teknik elendi" event-driven'a **transfer olmaz**. Bu test o boşluğu doğru metodolojiyle açar.

---

## 3. İKİ BİLEŞEN

### 3A. Backtest motoru (token/veri bekler; şimdi sentetik-test)
| Modül | Sorumluluk |
|---|---|
| `event_config.py` | Stage 0 donmuş parametreler; DEC-046; N-kilit (3 olay-türü) |
| `event_detect.py` | E1 reel-YoY sürpriz (TÜFE-deflate, pozitif-baz); E2/E3 `data_pending` stub (uydurma yok) |
| `event_confirm.py` | Teknik-teyit: hacim-artışı + kırılım (look-ahead safe) |
| `event_study.py` | Forward-return (t+1 giriş), XU100-relative; confluence ayrıştırma |
| `event_null.py` | NULL-1 (olay-koşullu) + NULL-2 (olaysız), seeded determinist |
| `event_runner.py` | Holm olay-tipi-başına AYRI + DEC-046 verdict (`undetermined` < MIN) |

### 3B. İleri-dönük kayıt sistemi (REV-1; bugünden, manuel-tetikli)
`event_forward_recorder.py` — kanıtlı `src/data/signal_logger.py` desenini olaylara uyarlar:
- **`EventForwardRecorder`** — değişmez, append-only, `natural_key`-idempotent sinyal log. **Forward-return YAZILMAZ** → **ön-kayıt garantisi** (`as_of_timestamp` < fill-time). Look-ahead/overfit/survivorship **yapısal imkansız**.
- **`EventReturnFiller`** — t+5/+20/+60 olgunlaşınca forward + XU100-relative HESAPLAR + AYRI returns dosyasına ekler ((natural_key,horizon)-idempotent). Sinyal log değişmez.
- **`run_manual`** — auth-suz KAP feed'iyle (`kap_scraper.fetch_kap_news`, **token YOK**) günlük olayları yakalar; **manuel-tetikli** (cron sonraya bırakıldı). Erişilemezse `data_pending` (uydurma yok).

**Kritik içgörü (the maintainer):** token uzun süre gelmeyebilir → forward sistem token-darboğazını **bypass eder** (auth-suz feed bugün çalışıyor, §5d).

---

## 4. METODOLOJİ (Stage 0'da DONDURULDU)

- **İki null (zorunlu):** NULL-1 (aynı olay-günlerinde teknik-teyit rastgele) "teknik, olaya değer katıyor mu?"; NULL-2 (olaysız rastgele günlerde aynı teknik) "olay, tekniğe değer katıyor mu?". Confluence ancak **HER İKİ** null'ı >%95 geçerse gerçek.
- **Holm-Bonferroni olay-tipi-başına AYRI** (3 horizon üzerinde), tek havuzda toplama YOK (Faz 0 lowvol60 dersi).
- **Look-ahead:** olay-günü = `published_at`; aksiyon **t+1** (duyurudan SONRAki bar — hız-dezavantajı modellenir).
- **XU100-relative zorunlu** (nominal-drift tuzağı, D-186). Reel-CPI ikincil.
- **Sürpriz = reel YoY** (net_income birincil + revenue teyit, TÜFE-deflate). Nominal değil — yüksek-enflasyonda nominal "en çok şişen"i seçer, gerçek sürprizi değil.
- **Maliyet:** 50 bps round-trip (RR-038) + 20 bps olay-günü slippage = **70 bps**.
- **DEC-046 (donmuş):** (1) NULL-1 ≥%95 ∧ (2) NULL-2 ≥%95 ∧ (3) XU100-relative pozitif (maliyet-sonrası) ∧ (4) Holm-per-type anlamlı. Geçemezse → confluence de edge taşımıyor. Örneklem < 30 → `undetermined` (pass/fail değil). **Post-hoc gevşetme YASAK.**

---

## 5. VERİ-FİZİBİLİTE BULGULARI (canlı read-only probe, 2026-05-31)

Tam çıktı: [`docs/event_test/D188_DATA_FEASIBILITY.json`](../event_test/D188_DATA_FEASIBILITY.json).

| # | Soru | Bulgu |
|---|---|---|
| **(a)** | MKK_VYK_TOKEN olmadan ne kadar veri? | **Token YOK** (doğrulandı). `fetch_fr_history("THYAO",2022,2023)` → **0 satır**. Tarihsel E1 XBRL erişilemez → yalnız yfinance fallback. |
| **(b)** | KAP-4.0 cutoff gerçek derinlik? | `_MIN_DISCLOSURE_INDEX=538004`; altı html-only (XBRL yok). KAP 4.0 ~2021 → XBRL kazanç derinliği **~2021+, 2019 DEĞİL**. (Cutoff'un tam tarihi canlı API ister.) |
| **(c)** | yfinance duyuru-tarihi look-ahead riski? | `quarterly_income_stmt` yalnız **dönem-sonu** verir (duyuru ~6-10 hafta sonra → dönem-sonunu olay-günü saymak **ağır look-ahead**). `get_earnings_dates` THYAO.IS için **25 satır döndü** (duyuru-tarihi VAR) ama tüm evren kapsamı/doğruluğu **doğrulanmadı** → risk **ORTA**. Forward recorder bunu tamamen by-pass eder (gerçek-zamanlı yayın-tarihi). |
| **(d)** | E2/E3 yol + bugün hangi tür erişilebilir? | E2 (endeks-dahil) tarihsel: **kaynak YOK** (`data_pending`). E3 (önemli-KAP) tarihsel: ODA pagination **token ister** (`data_pending`). **FORWARD:** auth-suz `fetch_kap_news("THYAO")` → **2 canlı kayıt, token YOK** ✓ → forward E1/E3 yakalama **bugün başlayabilir** (recent-only, WAF-kırılgan → nazikçe ele alınır). |

**Özet:** Backtest = token/veri bekliyor (üç tür de). Forward = auth-suz feed bugün çalışıyor → temiz örneklem birikimi başlayabilir.

---

## 6. NEYİN FROZEN-HAZIR / NEYİN BLOKE

- ✅ **Hazır:** İki motor (sentetik-test geçti), Stage 0 ön-kayıt, DEC-046, iki-null, Holm-per-type, forward recorder (manuel), reusable altyapı (XU100-relative, fair-null mekaniği, block-bootstrap, signal_logger deseni).
- ⏳ **Bloke (backtest):** E1 tarihsel XBRL (MKK_VYK_TOKEN); E2 endeks-dahil kaynağı (yok → **ayrı spec**); E3 ODA tarihsel (token). yfinance-fallback duyuru-tarihi → orta look-ahead riski (tercih edilmez).
- 🟢 **Açık (forward):** auth-suz KAP feed → E1/E3 forward yakalama bugün; verdict `MIN_EVENTS_PER_TYPE` dolunca.

---

## 7. ATIF-DİSİPLİNİ (REV-2)

- **Kanıt = kod yolu:** auth-suz gerçek-zamanlı erişim iddiası `src/data/kap_scraper.py:180 _fetch_kap_api` (POST `memberDisclosureQuery`, `disclosureCategory` param, token/login yok) + canlı probe (§5d, 2 kayıt) ile **kanıtlandı** — varsayımla değil.
- **`NRR_EXPLORE.md`** bir veri-erişim fizibilite **probe BRIEF'i** (görev tanımı), **sonuç değil**; clone3'te `/demo-tests/` veya `DATA_ACCESS_FEASIBILITY.md` **yok** → kayıt-altı verdict yok. Bu yüzden "byCriteria auth-suz doğrulandı" diye **referans verilmedi** (kanıtsız-atıf yasağı).
- **`NRR-001-SCREENING.md`** içerik-ilgili: §3 "RS XU100-relative, nominal değil" + look-ahead/survivorship disiplini → XU100-relative + reel-sürpriz + look-ahead seçimlerimize **gerçek dayanak**. **AMA UNTRACKED** (`git status: ??`) → kayıt-altı kanıt değil; PR'a **dahil edilmedi**; commit kararı **the maintainer/Orchestrator**'a (başkasının untracked araştırmasını sessiz commit'leme — shared-tree dersi).

---

## 8. CAVEAT'LAR (açık)

- Backtest üç tür de `data_pending` → **ölçüm ertelendi** (uydurma yok).
- Forward accrual **yavaş** (olay seyrek) → uzun süre küçük-n; verdict `MIN_EVENTS_PER_TYPE`'a kilitli.
- Auth-suz KAP feed **recent-only + WAF-kırılgan** → forward yakalama aralıklı olabilir; kaçırmalar loglanır, uydurulmaz.
- Olası backtest yfinance OHLCV survivors-only → **üst-sınır**.
- E2/E3 backtest **ayrı veri-sağlama speci** ister.
- `sample_noevent_technical_returns` canlı evrende O(n²) eğilimli (`max_pool` cap'li); ölçüm aktifleşince vektörleştirilmeli.

---

## 9. DEC-039 + ÖNERİ

Bu program **ÖLÇMEYE HAZIRLAR**; verdict (backtest token/veri **VEYA** forward örneklem sonrası) **the project** kararı. Builder **ÖNERİR, atfetmez.**

**Öneri:** (1) Forward recorder'ı **bu hafta manuel** başlat (auth-suz feed çalışıyor, token gerekmez) → temiz örneklem biriksin. (2) Backtest için MKK_VYK_TOKEN sağlanırsa E1 tarihsel açılır; sağlanmazsa forward tek-başına yeterli (daha temiz). (3) E2 endeks-dahil için ayrı veri-sağlama speci. **"Edge yok" sonucu da geçerli** → swing'in son alt-kümesi de kapanırsa Yol 2'ye netçe çapalanılır.

---

## 10. DOSYALAR

- Ön-kayıt: [`docs/event_test/STAGE0_event_confluence_preregistration.json`](../event_test/STAGE0_event_confluence_preregistration.json)
- Fizibilite: [`docs/event_test/D188_DATA_FEASIBILITY.json`](../event_test/D188_DATA_FEASIBILITY.json)
- Motor: `src/screening/event_{config,detect,confirm,study,null,runner}.py`
- Forward: `src/screening/event_forward_recorder.py`
- Testler: `tests/test_event_confluence.py` (28 test, sentetik, network-free)
- **Sonraki adım:** forward manuel-başlat + (varsa) token → backtest; verdict örneklem sonrası.
