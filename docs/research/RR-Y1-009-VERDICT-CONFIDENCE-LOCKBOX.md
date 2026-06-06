# RR-Y1-009 — Verdict-confidence qualifier + Iteration lockbox (motor-güvenilirliği sertleştirme)

**Tarih:** 2026-06-05
**Tür:** Validator-reliability hardening (alet-sertleştirme), **edge-avı DEĞİL** (C10-SAFE).
**Dayanak:** RR-Y1-005 §7 (TASARIM v0.2) · RR-Y1-005B §4.1/§4.2/§4.3 (math-spec v1.1) · RR-Y1-005-FAZ4 (DSR-N-binding) · RR-Y1-008 §1/§2 (ilk gerçek-veri sınavı: silent-confounded-PASS + lockbox-boşluğu) · D-213 (snapshot content-hash precedent).
**Çatışma-önceliği:** TASARIM v0.2 > math-spec v1.1 > bu görev > arastirma katmani.
**Spec-soyağacı:** DEC-046/049/050.
**Strangler:** committed-motorlar (`src/backtest`, `src/screening`, lab, clib) SIFIR-dokunuş; `src/engine` içinde YALNIZ additive alan/sabit + iki YENİ saf-modül (`confidence.py`, `lockbox.py`). Mevcut hiçbir verdict/keep-bar değişmedi.

---

## 0. Amaç ve çerçeve

RR-Y1-008 (motorun ilk gerçek-veri sınavı, PR #203) konjuge (Mod-A) verdict-yolunda iki güvenilirlik-boşluğu açığa çıkardı. Bu rapor o iki boşluğu **mekanik** olarak kapatır. Her iki öğe de **additive-only**: `agreement_pass`, üç uyum-koşulu ve her keep-bar **DEĞİŞMEDİ** (DEC-049). Qualifier yalnızca zaten-hesaplanmış büyüklükleri *okur*; lockbox bir istatistiğin **ne zaman** hesaplanabileceğini kısıtlar, istatistiğin kendisini asla değiştirmez.

Bu **C10-SAFE**: doğrulama-ALETİNİN güvenilirliği sertleştirilir, edge keşfedilmez; hiçbir mezarlık-faktör yeniden-açılmaz.

---

## 1. Öğe-1 — Verdict-confidence qualifier

### 1.1 Kapatılan boşluk (RR-Y1-008 §2: hi52 sessiz-confounded-PASS)

RR-Y1-008'de bilinen-ölü bir momentum-proxy (hi52) **küçük-arm, tek-rejim** kapsam-penceresinde (arm~37, yalnız 2024+) `agreement_pass=True` üretti. Konjuge'nin dar sorusu ("isim-spesifik overfit YOK") doğru cevaplandı — ama sonuç **within-regime common-factor artefaktıydı**, deploy-edilebilir-edge DEĞİL. Motor çıplak bir `True` yayınladı, **hiçbir güven-niteleyici olmadan**; confound'u downstream el-ile yakalamak zorunda kaldı.

### 1.2 Niteleyici (saf fonksiyon)

`src/engine/confidence.py` → `assess_agreement_confidence(...)` saf fonksiyon (I/O yok, global-state yok, tam unit-testlenebilir). Bir Mod-A konjuge-ölçümünün **ne kadar güvenilir** olduğunu derecelendirir:

- **`confounded`** — paylaşılan-common-factor flag'i tetiklendi (`residual_corr_flag`, §4.2) **VEYA** eval-penceresi tek-rejim. Konjuge'nin "isim-spesifik overfit yok" cevabı bu durumda within-regime common-factor artefaktı olabilir (RR-Y1-008 hi52 false-PASS).
- **`low`** — arm-başı eligible-isim `arm_floor`'un altında **VEYA** efektif name-split sayısı `r_floor`'un altında → ölçüm underpowered.
- **`high`** — yukarıdakilerin hiçbiri tetiklenmedi (yeterli breadth + yeterli R + confound-tetiği yok).

**Öncelik: confounded > low > high.** `high` adequate-arm + adequate-R + confound-tetiği-yok ister. Dönen tuple, tetiklenen her koşulu sıralı-numaralandırır (`high` için boş).

### 1.3 Donmuş eşikler (HERHANGİ bir gösterim-koşusundan ÖNCE `config.py`'de commit)

| Sabit | Değer | Bağlanma |
|---|---|---|
| `AGREEMENT_MIN_ARM_FOR_HIGH_CONFIDENCE` | 50 | = gevşetilmemiş `MIN_NAMES_PER_ARM`. RR-Y1-008'de arm~37 (gevşetilmiş 30-floor'un altında) → `low` olarak yüzeylenir, asla temiz-PASS değil. |
| `AGREEMENT_MIN_R_FOR_HIGH_CONFIDENCE` | 50 | = `SPLIT_R_MIN`. Efektif R bunun altında → `low`. |

**Confounded-tetikleri (data-driven, gameable-proof):** `residual_corr_flag is True` **VEYA** eval-penceresi tek-rejim (`d1 < REGIME_SPLIT` veya `d0 >= REGIME_SPLIT`, `REGIME_SPLIT = 2022-01-01`).

### 1.4 Rejim-tetiği KARARI: data-driven, `hedef_rejim`-etiketi DEĞİL

Tek-rejim tespiti **veriye dayanır** (eval-penceresinin frozen `REGIME_SPLIT` sınırının tamamen bir yanında kalması), Stage-0'daki `hedef_rejim` **etiketine değil.** Gerekçe: RR-Y1-008 `hedef_rejim="all"` deklare etmişti ama fiilen tek-rejimdi (yalnız 2024+); etiket-tabanlı bir kontrol o confound'u **kaçırırdı**. `hedef_rejim` yalnızca deklare-edilmiş-niyet dokümantasyonu olarak kalır; operatif tetik pencere-span kontrolüdür.

### 1.5 Additive-only garantisi (DEC-049 dokunulmadı)

`EngineOutput`'a iki yeni alan eklendi, ikisi de defaultlu: `agreement_confidence: AgreementConfidence | None = None` ve `agreement_confidence_reasons: tuple[str, ...] = ()`. `run_moda` (gerçek-yol) ve `_guard_result` (dejenere-yol) niteleyiciyi hesaplar; dejenere-yol aynı helper'a sıfır-breadth girdileri `(0, 0, False, False)` besler → doğal olarak `low` üretir (özel-durum-yok). `harness` iki alanı `EngineOutput`'a geçirir. `agreement_pass` ve üç koşul bugünküyle birebir aynı hesaplanır; niteleyici yalnız okur. Hiçbir keep-bar değişmedi.

---

## 2. Öğe-2 — Iteration lockbox (single-shot held-out enforcement)

### 2.1 Kapatılan boşluk (RR-Y1-008: enforce-edilmeyen lockbox)

iterate→validate iş-akışı konvansiyona dayanıyordu: Stage-0 *tasarımı* dondurur, ama hiçbir yapı keşif-çalışmasının nihai-verdict'in okunduğu veriye zaten dokunmuş olmasını yapısal-olarak engellemiyordu; dürüst-deneme-sayısı mekanizma değil konvansiyondu.

### 2.2 Mekanizma

Stage-0 isteğe-bağlı olarak bir held-out alt-küme **mühürler** (isimle, zaman-bloğuyla veya ikisiyle) ve bir content-hash kaydeder. Motor, frozen prototip'i bu mühüre karşı skorlamayı şu olmadıkça reddeder: Stage-0 mevcut + `frozen_before_results: true` + lockbox content-hash kayıtlı-hash ile eşleşir. Sonra değerlendirme **consumed** olarak kaydedilir → mühürlü-set asla tekrar tuning-yüzeyi olarak kullanılamaz.

İsteğe-bağlıdır: lockbox deklare-etmeyen bir Stage-0 tıpatıp eskisi gibi koşar (backward-compatible). Deklare-edildiğinde mekanik-olarak enforce edilir.

### 2.3 Bileşenler (`src/engine/lockbox.py`)

- **`lockbox_fingerprint(panel, *, names, date_start, date_end) -> str`** — mühürlü alt-kümenin **GERÇEK DEĞERLERİ** üzerinden kanonik bayt-serileştirmesinin `sha256[:16]`'ı (güçlü anti-tamper; D-213 `hash16` 16-karakter konvansiyonu). Payload sıra-değişmez (isimler sıralı, tarihler sıralı) ve tam float-değerleri bağlar: mühürlü-veriye yapılan herhangi-bir-düzenleme — yalnız koordinatları değil — hash'i değiştirir. Araştırmacı FREEZE-zamanında (Stage-0'da `lockbox_content_hash` kaydetmek için) ve motor EVAL-zamanında (sunulan-panelin mühürlü-set olduğunu doğrulamak için) AYNI fonksiyonu kullanır → deterministik ve paylaşılan.
- **`marker_path_for(stage0_path) -> Path`** — Stage-0 dosyasının kardeşi: `{stem}.lockbox-consumed.json`.
- **`assert_lockbox(stage0, panel, marker_path) -> None`** — mühür tutmadıkça skorlamayı reddeder: lockbox-deklare-ama-Stage-0-donmamış; `lockbox_fingerprint(panel) != stage0.lockbox_content_hash` ("lockbox-hash mismatch"); ya da marker zaten-aynı-hash'le mevcut ("lockbox already consumed"). Lockbox deklare-edilmediğinde no-op.
- **`consume_lockbox(stage0, marker_path) -> None`** — marker JSON'u yazar. **GERÇEK VERİ İÇERMEZ** — yalnız `{prototip_id, lockbox_hash_prefix, denenen_konfig_sayisi, consumed_at}` (16-karakter hash-prefix, değerler değil). Lockbox deklare-edilmediğinde no-op.

`harness` lockbox'ı iki noktada işler: (1) `require_stage0`'dan hemen-sonra `assert_lockbox` (refuse-early); (2) `EngineOutput` dönmeden ÖNCEKİ SON-eylem olarak `consume_lockbox` — böylece koşu-ortasında bir crash lockbox'ı **yakmaz**, yine de araştırmacı see-then-abort yapamaz.

### 2.4 Consumed-marker = COMMIT-edilen audit-trail

Marker **git-ignored DEĞİLDİR — commit-edilen bir audit-trail'dir**, Stage-0 JSON'larının kendisiyle AYNI commit-pattern'ında (production-konumu = Stage-0-kardeşi `{stem}.lockbox-consumed.json`; `tmp_path` yalnız test-aracıdır). İçeriği gerçek-veri taşımaz: yalnız `prototip_id` / 16-karakter `lockbox_hash_prefix` / `denenen_konfig_sayisi` (DSR-deflation'a beslenen dürüst-deneme-sayısı) / UTC `consumed_at` zaman-damgası.

Single-shot-guard **commit-edilen marker'la da çalışır**: taze bir `git checkout` sonrası marker mevcuttur → ikinci-koşu reddedilir = **inkâr-edilemez, non-repudiable** disiplin. `consume_lockbox` docstring'i marker'ın commit-edilmek-üzere-tasarlandığını (tmp_path yalnız-test, production-konumu Stage-0-kardeşi) açıkça deklare eder.

### 2.5 Disiplin

Bu, istatistiğin **ne zaman** hesaplanabileceğini değiştirir, istatistiği asla. Bir tasarım-değişikliğinden sonra yeniden-değerlendirmek için YENİ bir mühürlü alt-küme kaydetmelisiniz (farklı alt-küme → farklı hash → yeni, henüz-yok marker); aynı lockbox asla tekrar tuning-yüzeyi olamaz (RR-Y1-009). DSR trial-count zaten bağlı (FAZ-4(b)): `stage0.denenen_konfig_sayisi` → `harness n_trials` → `run_modb` → DSR-deflation → `dsr_n_trials`; yeni DSR-plumbing yok.

---

## 3. Test çerçevesi (tamamı additive; sıfır-regresyon)

- **`tests/test_engine_confidence.py` (YENİ):** `assess_agreement_confidence` için exhaustive branch-tablosu — high; low (arm<floor; R<floor; ikisi); confounded (residual_corr_flag=True **branch'i burada kapsanır**; single_regime=True; ikisi); öncelik (confounded, low'u yener). Saf girdiler, panel yok.
- **`tests/test_engine_lockbox.py` (YENİ):** fingerprint determinizm + value-sensitivity + sıra-değişmezlik + alt-küme-seçimi; hash-mismatch → `Stage0Error(match="lockbox-hash")`; not-frozen → `Stage0Error(match="frozen")`; single-shot (consume → ikinci assert "already consumed"); marker gerçek-veri-içermez; no-lockbox no-op.
- **`tests/test_engine_moda.py` (genişletildi):** additive-only kanıtı (`agreement_pass` noise/factor/market'te DEĞİŞMEDİ); `factor_result.agreement_confidence == HIGH`; YENİ tek-rejim fixture (factor-benzeri, `start=2024-01-02`) → `CONFOUNDED`; YENİ küçük-arm fixture (`min_names_per_arm=30`, `n_names=80`) → `LOW`.
- **`tests/test_engine_stage0.py` (genişletildi):** lockbox-alanlı doc validate + round-trip; lockbox-sız doc hâlâ validate (backward-compat); boş-hash → None normalize.
- **`tests/test_engine_harness.py` (genişletildi):** `agreement_confidence` `EngineOutput`'a thread-edilir; lockbox end-to-end (`tmp_path` Stage-0: ilk-koşu marker-yazar; ikinci-koşu "already consumed" raise; yanlış-panel "lockbox-hash" raise; lockbox-sız marker-yazmaz).

**C12 golden byte-repro yeşil:** golden bir CSV-fixture + 3 NW-skaları hash'ler (`EngineOutput`'u değil) → yeni-additive-alanlar ona şeffaf. `tests/test_engine_no_lab_import.py` `src/engine/*.py`'yi glob ile auto-keşfeder → iki yeni-modül (yalnız stdlib + numpy/pandas + `src.engine.*` import eder) bedelsiz kapsanır.

---

## 4. Kapsam-dışı (ayrı görev)

within-regime time-holdout "same-regime forward persistence" sınavı — çekirdek-sorunun kavramsal-olarak-doğru enstrümanı — kendi spec'ini hak eder; bu görevde kapsanmaz.
