# RR-Y1-010 — Mod-C: rejim-içi ileri zaman-holdout değerlendirme modu (TASARIM + VERDICT)

**Tür:** doğrulama-motoru yetenek-genişletmesi (additive mod). Plan → onay → build → bu rapor.
**Konum:** `src/engine/` (committed-motor SIFIR-dokunuş; strangler).
**İlişkili:** committed task-spec [`RR-Y1-010-TASK-intra-regime-time-holdout.md`](RR-Y1-010-TASK-intra-regime-time-holdout.md) (PR #207). Bu dosya **tasarım + hüküm** belgesidir; task-spec'i tekrar-etmez, onu uygular.
**Çelişki-önceliği:** TASARIM v0.2 > math-spec v1.1 > task-spec > arastirma katmani.

---

## 1. Çözülen çekirdek-soru

Motor bugün iki dar-soruyu cevaplıyor; üçüncüsü — *çekirdek* araştırma-sorusu — ikisine de erişilemiyor:

- **Mod-A (isim-bölme, `SplitMode.NAME`)** "bu isim-spesifik-overfit mi?" sorusunu **tek-zamanda** test eder.
- **Mod-B (temporal-CPCV, `SplitMode.TEMPORAL`)** zamanlama-sinyali overfit'ini fold'lar-arası test eder.
- **Hiçbiri**, bir **cross-sectional faktörün**, bir TRAIN zaman-penceresinde donduruluğunda, **AYNI REJİM İÇİNDE** daha-sonraki bir held-out penceresinde benzer **ileri cross-sectional davranış** gösterip-göstermediğini test etmez (RR-Y1-005 §3/§4.8 "aynı-rejimde-ileri-tutar-mı"; DEC-046 overfit'in-saklandığı-boyutta-böl — burada boyut **sabit-rejim-içinde-ileri-zaman**).

**Mod-C (`SplitMode.TIME_HOLDOUT = "C"`)** bu boşluğu kapatır. **Additive-only, C10-safe** (alet-altyapısı, edge-avı-DEĞİL): committed-motorlar, Mod-A/Mod-B, keep-bar'lar, üç-uyum-koşulu, RR-Y1-009 confidence-qualifier ve C12-golden **DEĞİŞMEDEN** kalır.

**Sıfır-iskonto-skorer notu:** motor parametre-fit-etmez; faktör fitted-parametre taşımaz. Dolayısıyla "train'de dondur" = araştırmacının üzerinde iterasyon-yapacağı **keşif-penceresi**; held-out pencere ise **ileri-OOS okuması**dır.

---

## 2. Mekanik (`run_modc`)

Mod-A'nın nötrleme + paylaşılan `stats`/`data_adapter` primitiflerini yeniden-kullanır:

1. `tr → daily_ret`, `mkt → daily_mkt`, `fwd = forward_return(panel, h)`, `fwd_mkt`, ve `resid_fwd = market_neutral_forward(...)` — Mod-A ile birebir (look-ahead-safe rolling-β, W=126, min-coverage 0.8).
2. `scores` paneli (`signal.scores`, tüm tarihler); `eval_dates` = `MIN_NAMES_CROSS_SECTION` (=30) tabanını geçen tarihler (β-warm-up sonrası).
3. **Sınır + embargo:** `boundary = SplitSpec.holdout_start`. `holdout = eval_dates[eval_dates >= boundary]`; `pre = eval_dates[eval_dates < boundary]`. Sınırın hemen-öncesinden `embargo_h` eval-günü **purge** edilir (`train = pre[:len(pre) - embargo_h]`) — böylece hiçbir train-dönemi ileri-getirisi sınırı-aşmaz (Mod-B'nin look-ahead-safe disiplini).
4. **Embargo / güç-guard'ı:** `holdout_start` eksik/aralık-dışı ise, ya da train/holdout her-biri `< nw_lag + 3` IC-gözlemine düşerse → dejenere **guard-sonucu** (`holdout_persistence_pass=None`, guard-mesajı) döner; yanıltıcı-sayı-DEĞİL.
5. `train_ic = rank_ic_series(...)`, `holdout_ic = rank_ic_series(...)`; `*_ic_t = nw_tstat(*, lag)`, `*_ic_mean = mean`.
6. Hüküm (bkz. §4): `holdout_persistence_pass`.
7. **residual_corr_flag (holdout):** Mod-A'nın `_eligible_names` + `name_splits` + `_arm_active_series` + `arm_active_correlation` + `residual_arm_correlation` makinesi **holdout-penceresinde** koşar (RR-Y1-008'in hi52-confound'unu yakalayan AYNI dedektör; permütasyon-null, SeedSequence-offset).
8. `holdout_crosses_regime = bool(hd0 < REGIME_SPLIT <= hd1)`.
9. `assess_holdout_confidence(...)` → grade + gerekçeler.
10. Tüm `holdout_*` / `train_*` anahtarları + `guard_messages` içeren dict döner; `harness` bunları `EngineOutput`'a geçirir.

Mod-C **standalone** bir bacaktır (`TIME_HOLDOUT` yalnız) — bilinçli olarak `PANEL` (A+B) içine katlanmaz, böylece A+B semantiği byte-değişmez.

---

## 3. Confidence-reconciliation kararı = **Seçenek-B (ayrı Mod-C alanı)**

Mod-C **tasarım-gereği tek-rejim**dir; bu nedenle RR-Y1-009'un `tek-rejim → CONFOUNDED` tetiği her-koşuyu yanlış-etiketlerdi. Çözüm: **YENİ** `HoldoutConfidence` enum + `assess_holdout_confidence()` helper + yeni `holdout_confidence` / `holdout_confidence_reasons` alanları. RR-Y1-009'un `assess_agreement_confidence`'i ve `agreement_confidence` alanı **byte-dokunulmaz** kalır.

**Neden Seçenek-A değil (mevcut-fonksiyonu mode-aware-yapmak):** shipped `assess_agreement_confidence`'ı değiştirmek bir regresyon-yüzeyi açar ve Mod-A'nın `tek-rejim→confounded` tetiğini zayıflatma-riski taşır. Ayrı-alan iki-modun semantiğini izole-eder.

### Zıt-ama-tutarlı rejim-semantiği (helper-docstring'inde açıkça-yazılı)

- **Mod-A:** *tek-rejim eval-penceresi = ŞÜPHELİ* — rejim-içi ortak-faktör artefaktı temiz-bir-PASS'i taklit-edebilir (RR-Y1-008 hi52).
- **Mod-C:** *tek-rejim = TASARIM, confound-DEĞİL* (soru zaten "bir-rejim-içinde-ileri-tutar-mı"). Buradaki confound, holdout-penceresinin **`REGIME_SPLIT`'i KESMESİ**dir: train bir-rejimde otururken holdout başka-rejime taşarsa, "aynı-rejim-ileri-tutarlılık" sorusu kirlenir.

### `assess_holdout_confidence` — öncelik: confounded > low > high

- **confounded:** `holdout_crosses_regime` (holdout `REGIME_SPLIT`'i straddle-eder) **VEYA** `residual_corr_flag` (holdout-penceresinde paylaşılan-ortak-faktör).
- **low:** `n_holdout_obs < HOLDOUT_MIN_IC_OBS_FOR_HIGH_CONFIDENCE` (=60) — yapısal-underpowered, dürüst-zorunlu-beyan.
- **high:** hiçbiri tetiklenmedi.

---

## 4. Persistence-hüküm = **mevcut-bar'ları yeniden-kullan (yeni-tunable-YOK)**

```
holdout_persistence_pass = isfinite(holdout_ic_t)
                           AND holdout_ic_t > AGREEMENT_CROSS_IC_T_MIN (=2.0)
                           AND sign(mean holdout_ic) == sign(mean train_ic)
```

Yeni-eşik eklemek post-hoc bir serbestlik-derecesi açardı; bunun yerine mevcut konjuge-bar (`AGREEMENT_CROSS_IC_T_MIN`) ve bir işaret-tutarlılığı koşulu kullanılır. Güç-hakkındaki dürüstlük **`holdout_confidence`** ile taşınır, bar-gevşetmesiyle DEĞİL.

`HOLDOUT_MIN_IC_OBS_FOR_HIGH_CONFIDENCE = 60` yeni-sabittir ama bir keep-bar **değil**: yalnız confidence-grade'i `low`'a-çeken bir **yönsel-taban** (coverage-criterion, verdict-criterion-DEĞİL). Herhangi-bir gösterim-koşusundan **ÖNCE** donduruldu.

---

## 5. Dürüst-sınır (yapısal-underpowered beyanı)

BIST 2019–2026 az-sayıda-rejimle ve sınırlı-rejim-içi-uzunlukla domine-edilir; **bir-rejim-içinde örtüşmeyen-ileri-holdout'lar kıttır** → bu mod mevcut-veride **yapısal-olarak underpowered**dır. Değeri ikidir: (a) çekirdek-soru için **kavramsal-olarak-doğru** alet, ve (b) daha-fazla-rejim-içi-veri (ya da 2026–2027 ileri-dönemi) geldiğinde **hazır-olması**. Veri-duvarını aşmaz; **testi soruyla-hizalar**. Bu yüzden `low`/`confounded` grade'leri normal-beklentidir, kusur-DEĞİL.

---

## 6. Ön-kayıt (Stage-0) protokolü

Operatif-sınır `SplitSpec.holdout_start`'tır. `Stage0`'a üç **isteğe-bağlı/bilgilendirici** alan eklendi (`hedef_rejim` gibi): `eval_window_start`, `eval_window_end`, `holdout_start`. `REQUIRED_FIELDS` **değişmedi** → mevcut-committed Stage-0 JSON'ları aynen-valid. Gerçek bir ön-kayıtlı Mod-C koşusu: rejim-penceresi + train/holdout-sınırı + embargo + beklenen-hüküm sonuçtan-önce dondurulur.

---

## 7. Değiştirilen / eklenen dosyalar

**Yeni:** `src/engine/modc.py`, `src/engine/holdout_confidence.py`, `tests/test_engine_modc.py`, `tests/test_engine_holdout_confidence.py`, bu doc.
**Additive-düzenleme:** `src/engine/contracts.py` (`SplitMode.TIME_HOLDOUT` + `HoldoutConfidence` enum + `SplitSpec.holdout_start` + 10 `EngineOutput` alanı), `src/engine/config.py` (1 donmuş-taban), `src/engine/harness.py` (Mod-C dispatch + passthrough), `src/engine/stage0_validator.py` (3 isteğe-bağlı-alan), `tests/test_engine_harness.py`, `tests/test_engine_stage0.py`, `docs/RESEARCH_REGISTRY.md`.
**Yeniden-kullanılan (DÜZENLENMEDİ):** `src/engine/moda.py` (residual-helper'lar), `src/engine/stats.py`, `src/engine/data_adapter.py`, `src/engine/neutralizer.py`, `src/engine/confidence.py` (byte-dokunulmadı).

---

## 8. VERDICT

✅ **MOTOR-MOD-C-EKLENDİ** (additive-only, sıfır-regresyon, C10-safe).

- **Mod-C bacağı çalışıyor** — zaman-değişken faktör-yüklü sentetik-fixture'larda: *kalıcı-faktör* (train+holdout) → `holdout_persistence_pass=True`, işaret-tutarlı, yeterli-genişlik + tek-rejim + ortak-faktör-bayrak-yok → **HIGH**; *train-only-faktör* → holdout-IC çöker → **persistence FAIL** (train-IC gerçek-kalsa-da).
- **Confidence-semantiği** zıt-ama-tutarlı doğrulandı: holdout `REGIME_SPLIT`'i kesince → **CONFOUNDED**; kısa-holdout (<60 gözlem) → **LOW**; embargo/güç-guard'ı sınır-kenara-yakınken yanıltıcı-sayı-yerine guard-mesajı döner.
- **Additive-only kanıtı:** `TIME_HOLDOUT` koşusu `agreement_pass`/`dsr`'yi `None` bırakır; Mod-A/Mod-B alanları kendi-modlarında dokunulmaz; C12-golden byte-repro yeşil; `test_engine_no_lab_import` iki-yeni-modülü auto-kapsadı.
- **Tam-regresyon SIFIR** (2088 passed, 4 skipped). Ruff temiz (`src/engine` + dokunulan-testler); mypy `src/engine`'de yeni-hata-yok.
- **Honest-limit:** mevcut BIST-verisinde yapısal-underpowered; değer = kavramsal-doğru-alet + 2026–2027 ileri-dönem-hazırlığı.
