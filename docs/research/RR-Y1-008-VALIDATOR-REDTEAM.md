# RR-Y1-008 — VALIDATOR-VALIDATION / RED-TEAM (doğrulama-motorunun ilk gerçek-veri sınavı)

**Tarih:** 2026-06-05
**Tür:** Validator-validation (alet-sınavı), **edge-avı DEĞİL** (C10-SAFE).
**Dayanak:** RR-Y1-005 §7 (TASARIM v0.2) · RR-Y1-005B §4.1/§4.3/§5 (math-spec v1.1) · RR-Y1-005-FAZ4 (DSR-N-binding) · D-213 KAPSAM-GUARD (kapsam-koşullu pencere precedent) · D-208/D-209 (anlamlılık-duvarı deseni) · demo-clone1 C11/C12 (discover→freeze→OOS).
**Çatışma-önceliği:** TASARIM v0.2 > math-spec v1.1 > spec > arastirma katmani.
**Strangler:** `src/engine` + committed-motorlar (`src/backtest`, `src/screening`, lab, clib) SIFIR-dokunuş; yalnız `examples/rry1008/` + `docs/` altında YENİ dosya.

---

## 0. Amaç ve çerçeve

RR-Y1-005 doğrulama-motoru (`src/engine/`, genel-amaçlı post-hoc-denetlenebilir **strateji-doğrulama ALETİ**) FAZ-4-sertleştirme ile TAMAMLANDI (PR #202). Ama bugüne dek **yalnız sentetik-fixture + C12 golden-byte-repro** ile koştu — **hiç gerçek BIST verisinde sınanmadı.** Bu rapor motorun ilk gerçek-veri sınavıdır; iki bölüm:

- **BÖLÜM 1 (bilinen-cevap / robustluk):** 3 **bilinen-ölü** mezarlık-faktörü (value_static, mom120, hi52) Mod-A'dan geçirir. Cevabı zaten biliyoruz (deploy-edilebilir edge YOK). Motor **hükmü** reproduke ediyor mu (konjuge-uyum FAIL)?
- **BÖLÜM 2 (adversarial red-team):** kasıtlı garden-of-forking-paths overfit kurar (K=24 mom-varyant ailesinden sabit-yarıda en-iyiyi cherry-pick), sonra motorun bunu **yakaladığını** kontrol eder (single-split FAIL, konjuge FAIL, bucket-PBO yüksek, DSR anlamsız).

Bu **validator-validation, edge-avı DEĞİL (C10-SAFE).** Hiçbir mezarlık-faktör yeniden-açılmaz; beklenmeyen PASS veren faktör flag-ve-raporla makine-teşhisi olarak ele alınır, **asla** keşfedilmiş-edge olarak değil. Ders-değeri: "doğrulayıcıyı kasıtlı-overfit'le red-team'ledik; reddetti" = güven kazandıran negatif-kontrol.

### Ön-kayıt (mandatory pre-registration)

Her koşunun beklenen hükmü, koşudan ÖNCE donmuş bir Stage-0 JSON'da kayıtlıdır (`examples/rry1008/stage0/*.json`, `frozen_before_results: true`, `date_frozen: 2026-06-05`); motorun kendi `require_stage0` guard'ı şema-yoksa/donmamışsa koşmayı reddeder. Sonuca bakıp yeniden-yorumlamak motorun yasakladığı şeydir.

### Ön-kayıtlı kararlar (her koşudan önce donmuş)

- **IC forward-horizon h = 21 işlem-günü (~1 ay)** her iki bölüm için. Gerekçe: bilinen-hükümler (value-SERAP t~0.76, mom120-negatif, hi52-KESIN-KAPANDI corrected-t=1.17) hepsi ~1-aylık-tutma testlerinden geldi → elma-elmaya reproduksiyon ~aylık IC-horizon gerektirir.
- **NW lag = 21** (`DialConfig(nw_lag=21)`) — örtüşen 21-günlük forward-return otokorelasyonunu düzeltir. Ön-kayıtlı, tune-EDİLMEDİ.
- **Frekans = GÜNLÜK panel**; Bölüm-1 = Mod-A (`SplitMode.NAME`), Bölüm-2 = `SplitMode.PANEL` (A+B → uyum + DSR).

### KRİTİK kuplaj (gelecek-prototipler için uyarı — moda.py:427)

`h = int(signal.construction_window)` ve Mod-A IC, **h-periyot-forward getiriye** karşı hesaplanır (`forward_return(panel, h)`). Yani `construction_window` **ÇİFT-ROL** oynar: sinyalin kendi iç-lookback'i AYRIDIR (`scores()` içinde yaşar, mom120=120g / hi52=252g / her varyantın kendi lookback'i), ama `construction_window` AYNI ZAMANDA IC-forward-return horizon'udur. Bu faktörler için aylık-sinyal→aylık-getiri olduğundan **benign**, ama `construction_window != tutma-horizon` olan gelecek-bir-prototip sessizce **yanlış IC-horizon** seçerdi. Bu yüzden Stage-0 JSON'da ve burada **açıkça deklare edilmiştir.**

---

## 1. KAPSAM-GUARD: tam-panel breadth-dejenerasyonu (HEADLINE BULGU)

İlk koşu tüm-tarih (2019–2026) survivorship-honest likit evrende yapıldı. **Mod-A dejenere oldu:** `continuous_basket(min_cov=1.0)` 7-yıl-penceresinde yalnız ~74 sürekli-isim bırakır; 10M-TL ADV-floor bunu **~38 isme** indirir — bir varsayılan Mod-A arm-çifti için gereken `>= 2×min_names_per_arm` (≥100) eşiğinin altında. Motor **breadth-guard ile güvenle reddetti** (`agreement_pass=False`, metrikler NaN, guard-mesajı: "only 38 eligible names; need >= 100"). Konjuge-makinesi **hiç koşmadı** — bu bir IC-ölçümü DEĞİL, bir kapsam-reddidir.

- **Bölüm-1 tam-panel:** 3 faktör de breadth-guard üzerinden dejenere-FAIL (konjuge hiç koşmadı).
- **Bölüm-2 tam-panel:** single-split overfit'i YAKALADI (X2 NW-t=1.628 < 2); motor Mod-A dejenere; DSR=1.0.

**Bu headline-bulgudur — iki yönlü:**
1. **Engine-safety PASS:** motor, istatistiksel-olarak-anlamsız bir ince-evrende sahte-IC üretmek yerine breadth-guard ile durdu. Partial-leg-kontratı (RR-Y1-005 Faz-3) tam-da-tasarlandığı-gibi: arm-kuramayan-ince-evren ASLA-raise-etmez → guard kaydeder, alanları None/NaN bırakır.
2. **BIST-spesifik yapısal-sınır:** survivorship-honest likit-evren (10M-ADV, 7-yıl-sürekli) **name-split-konjuge için fazla küçük.** Doku↔bağımsızlık-gerilimi burada bir **veri-hacmi-duvarı** olarak tezahür ediyor: konjuge agreement disjoint isim-yarıları ister; likit+sürekli BIST evreni iki istatistiksel-anlamlı yarı sağlamaya yetmiyor.

Yüksek-güven konjuge-doğrulaması bu yüzden **sentetik-fixture'larda kalır** (RR-Y1-005B §7); gerçek-BIST konjuge yalnız kapsam-koşullu/underpowered bir sağlamadır.

---

## 2. KAPSAM-koşullu re-run (KAPSAM-GUARD, sonuç-ÖNCESİ yeni Stage-0)

§1'deki dejenerasyon, konjuge-makinesini fiilen koşturmak için bir kapsam-önkoşulu re-run gerektirdi (D-213 KAPSAM-GUARD precedent; hükme ORTOGONAL). Re-run, dial'ları bir **KAPSAM-kriteriyle** seçer (hükümle değil):

- **ADV-floor 10M-TL KORUNDU** — mümkün-olan-en-yüksek, **SIFIR likidite-gevşetme** (illikit-tuzağı reddedildi; gratis-1M'e inilmedi).
- **Pencere: `eval_window_start = 2024-01-02`** — 10M-floor altında 75 uygun-isim veren (margin>30) tek pencere. Bir KAPSAM-sweep'le seçildi.
- **`min_names_per_arm = 30`** (= motorun `MIN_NAMES_CROSS_SECTION`'ı) — minimal-uygulanabilir-power.

Sonuç: panel = **600 gün × 681 isim [2024-01-02 .. 2026-05-26]**; Mod-A artık fiilen koşuyor (arm'lar ~37).

**UNDERPOWERED-uyarı (ön-kayıtlı):** küçük-arm (~37) → gürültülü per-arm rank-IC. Bu re-run "makine-koşuyor + yön-sağlaması"dır, **yüksek-güven konjuge-hüküm DEĞİL.** keep-bar DEĞİŞMEDİ; ön-kayıtlı beklenti DEĞİŞMEDİ (graveyard-faktörler → FAIL; red-team → CAUGHT). Pencere-kısıtı bir **rejim-confound'u** taşır (§3'te hi52 bulgusu).

---

## 3. BÖLÜM 1 — bilinen-cevap (Mod-A, kapsam-koşullu)

| faktör | beklenti (ön-kayıt) | agreement_pass | t_cross_median | sign_consistency | pbo | hüküm-tuttu? |
|---|---|---|---|---|---|---|
| value_static | FAIL (SERAP, cost-free t~0.76) | False | +1.1708 | +0.70 | +0.11 | **EVET** |
| mom120 | FAIL (negatif / reversal-dominant) | False | +1.7573 | +0.84 | +0.40 | **EVET** |
| hi52 | FAIL (KESIN-KAPANDI, gate2 t~1.17) | **True** | +2.6152 | +1.00 | +0.35 | **HAYIR (beklenmeyen PASS)** |

**value_static ve mom120:** hüküm reproduke edildi (`agreement_pass=False`). Konjuge-uyum üç-koşulundan en az biri çöker (value: t_cross<2 + sign<0.90; mom120: t_cross<2 + sign<0.90). Mezarlık kapalı kalır.

**hi52: BEKLENMEYEN PASS** (`agreement_pass=True`, t_cross=2.62, sign=1.00, pbo=0.35). **Per C10 yorum-kuralı bu bir EDGE DEĞİLDİR** — flag-ve-raporla. Üç-olası-açıklama (RR-Y1-005 speci):

- (i) engine-bug — **olası-değil:** value+mom120 aynı motorda doğru-FAIL verdi; mom120 (momentum-akrabası) t_cross=1.757'de neredeyse-eşikte. Motor ayrımcı davranıyor.
- (ii) konjuge-farklı-şey-ölçüyor — kısmen: konjuge name-split-OOS cross-arm-IC ölçer; orijinal KESIN-KAPANDI hükmü tam-tarih 5-gate / NW-anlamlılık-duvarından (gate2 t~1.17) geldi. Farklı-pencere + farklı-istatistik.
- (iii) **within-regime common-factor (EN-OLASI, ÖN-KAYITLI sınır):** hi52 (52-hafta-yükseğe yakınlık = close/252g-max) bir **momentum/trend-proxy'sidir.** Kapsam-penceresi (2024-01→2026-05) BIST'te güçlü-trendli/momentum-dostu tek-rejimdir. Küçük (~37-isim) likit evrende tek-trendli-rejim üzerinde hi52 ≈ "yükselen-isimler-yükselmeye-devam-eder" = **yaygın piyasa-momentum common-factor'u**, isim-spesifik kesitsel-edge DEĞİL. Market-nötrleme piyasa-seviyesini kaldırır ama pervasif within-regime momentum common-factor'unu kaldırmaz. mom120'nin de (momentum) t_cross=1.757/sign=0.84 ile neredeyse-geçmesi bu "pencere momentum-dostu" okumasını doğrular.

**Kritik:** hi52 PASS'ı, kapsam-penceresinin (breadth için zorunlu) getirdiği **rejim-confound'unun yüzeye-çıkmasıdır** — bu red-team'in kapsam-dışı bıraktığı **rejim-overfit (bilinen sınır)** kanalının ta kendisi. UNDERPOWERED-uyarı (küçük-arm + tek-rejim) bunu ön-kaydetmişti. **Mezarlık kapalı kalır;** hi52 yeniden-AÇILMAZ. Bu, ön-kayıtlı C10-yorum-kuralının ve underpowered-warning'in **doğrulanmasıdır** — motor değil, gerçek-veri-penceresi confounded; alet bu sınırı sadık-raporladı.

---

## 4. BÖLÜM 2 — adversarial red-team (üç-katman, kapsam-koşullu)

**Reçete:** (a) K=24 mom-varyant ailesi (lookback{20,40,60,120,180,240} × sign{+continuation,−reversal} × winsorize{none,[0.05,0.95]}) ölçümden ÖNCE donduruldu (`signals.mom_variant_family()`); (b) deterministik sabit isim-yarısı X1 (seed=0, 144 isim) üzerinde her varyantın in-arm mean rank-IC'si hesaplanıp **X1-en-iyi cherry-pick**; (c) o kazanan DONDURULUP disjoint X2 (145 isim) yarısında single-split; (d) donmuş-kazanan tam-motordan (`SplitMode.PANEL`, Stage-0 `denenen_konfig_sayisi=24` → DSR N=24-deflate).

**Cherry-pick (X1 leaderboard tepesi):**

```
mom120_cont_w0.05-0.95   X1 mean-IC = +0.04249   <- KAZANAN (DONMUŞ)
mom120_cont              X1 mean-IC = +0.04226
mom180_cont_w0.05-0.95   X1 mean-IC = +0.04109
```

| katman | metrik | gerçekleşen | overfit-yakalandı? |
|---|---|---|---|
| **1 — single-split** | X1 IC +0.04249 → X2 IC +0.03188 (selection-tax +0.01060); X2 NW-t (lag=21) = **+1.992** | |t|<2 → **EVET** (kıl-payı) |
| **2 — konjuge-uyum** | `agreement_pass=False` (t_cross=1.756, sign=0.84) | **EVET** |
| **2 — bucket-PBO** | pbo = **0.40** (< 0.50) | HAYIR |
| **3 — DSR** | dsr = **1.0** (N=24) | HAYIR |

**Yorum (C10-SAFE):** overfit **bağlayıcı-hüküm-katmanlarında yakalandı** — `agreement_pass=False` (motorun nihai-hükmü) VE single-split (maintainer'ın asıl-fikrinin doğrudan-testi). PBO ve DSR bağımsız-olarak flag-etmedi; bu bir **alarm-değil** (diğer-katmanlar yakaladı) ama gerçek-bir-bulgudur (§5/§6). Re-run'da hiçbir-katman bir-edge keşfetmedi; PASS-çıksaydı bile C10/DISC-1 gereği flag-not-edge olurdu.

### 4.1 Layer-1 single-split = maintainer'ın "optimize-et-X1, X2'ye-it" fikrinin doğrudan-cevabı

maintainer'ın önerdiği red-team tam-olarak işledi: X1'de cherry-pick'lenmiş kazanan (IC +0.04249), disjoint X2'de **IC +0.03188'e çöktü** (selection-tax +0.0106), NW-t **+1.992 < 2** → single-split FAIL. Seçim-vergisi gözlendi, kazanan OOS-anlamlılık-eşiğini geçemedi. **ÇALIŞTI.**

---

## 5. DSR=1.0 — PROMINENT bulgu + Faz-4(b) binding-incelemesi

**Bulgu:** DSR = **1.0**, N=24'te-bile, cherry-pick-kazananı **FLAG-ETMEDİ.** Yakalama single-split (t=1.992<2) + konjuge (agreement_pass=False) + (tam-panelde) breadth-guard tarafından yapıldı; **DSR yakalamadı.**

### Faz-4(b) DSR-binding mekaniği (RR-Y1-005-FAZ4 (b))

DSR formülü (`compute_dsr`, deflation `dsr.py` üzerinden):

```
DSR = Φ( SR_obs·√(T−1)/√denom  −  E[max_N] )
E[max_24] = (1−γ)·Φ⁻¹(1−1/24) + γ·Φ⁻¹(1−1/(24e)) = 1.9798   (γ = Euler-Mascheroni)
```

N=24-deflation, standardize-Sharpe biriminde **~1.98'lik bir çıkarma** uygular. **Binding matematiksel-olarak DOĞRU** (gerçekten E[max_24]≈1.98 çıkarıyor) AMA burada **efektif-olarak zayıf-bağlayıcı**, iki nedenle:

1. **Büyük OOS-T:** Mod-B `oos_sharpe` günlük-eksende her CPCV-path'i için yüzlerce-günlük segmentler; `sharpe_newey_west` √252-yıllıklaştırır. `√(T−1)` faktörü (~20+) standardize-Sharpe-t'sini onlarca-birime taşır → ~2-birim çıkarma ihmal-edilebilir → Φ(büyük)→1.0.
2. **Kanal-uyumsuzluğu (DAHA TEMEL):** DSR, `run_modb`'nin **TÜM-EVREN GROSS cost-free** top-tilt Sharpe'ı üzerinde koşar. Ama bu red-team'in imal-ettiği overfit **isim-altkümesi cherry-pick'i**dir (X1-yarısında en-iyi). Bu kanal **tam-evren Sharpe'ında hiç-belirmez** — cherry-pick avantajı isim-yarısına özgüdür, tam-evrende yıkanır. Yani **DSR yapısal-olarak bu red-team'in overfit'ini yakalayamaz**; tasarım-gereği. İsim-seçim-overfit'ini konjuge-name-split + single-split yakalar (doğru-katmanlar).

**Hüküm (Faz-4(b)):** binding zayıf-DEĞİL/bug-DEĞİL — doğru-hesaplanıyor; ama (a) yüksek-Sharpe uzun-günlük-pencere gross-sinyaller için ~2-birim-deflation efektif-olarak yutulur ve (b) DSR isim-seçim-overfit'ine **ortogonaldir** (search-overfit'i tam-evren gross-getiride ölçer, isim-altkümesinde değil). Bu, DSR'ın necessary-not-sufficient doğasıyla tutarlıdır: DSR'ın işi gross-getiride çoklu-test-deflation'udur, maliyet-uygulanabilirliği veya isim-seçim-overfit'i değil. **Diğer-katmanlar yakaladığı için alarm-değil, ama tasarım-sınırı olarak kayda-değer bir bulgu.**

---

## 6. Kanal-netliği ve yorum-kuralları (RR-Y1-005 specinden, verbatim)

- Bu red-team **isim-spesifik + arama (search) overfit'ini** probe-eder (konjuge + PBO + DSR'ın işi); **rejim-overfit'i probe-ETMEZ** (bilinen-sınır, kapsam-dışı). hi52'nin §3'teki beklenmeyen-PASS'ı tam-da bu kapsam-dışı kanaldan (rejim-confound) gelmiştir.
- Beklenmeyen PASS = **EDGE DEĞİL (C10).** Flag: (i) engine-bug / (ii) konjuge-farklı-ölçüyor / (iii) within-regime common-factor; raporla, AÇMA.
- C10/DISC-1 / kapsam-kayması-yok: Bölüm-1 = tam-olarak 3 sabit-faktör ("bir-tane-daha" YOK); Bölüm-2 = tam-olarak 1 adversarial-aile (K=24 donmuş). Hiçbir PASS hiçbir-mezarlığı açmaz.

---

## 7. Ders-değeri (negatif-kontrol güvenilirliği)

Doğrulama-motoru, gerçek-BIST verisinde ilk-kez üç-bağımsız-sınavdan geçti: (1) **breadth-guard** istatistiksel-olarak-anlamsız ince-evrende sahte-IC üretmeyi reddetti; (2) **bilinen-ölü faktörlerin** 3'ünden 2'sini doğru-reddetti, 3.'sünün (hi52) beklenmeyen-PASS'ını ön-kayıtlı C10-yorum-kuralıyla bir **rejim-confound flag'i** olarak izole etti (mezarlık kapalı); (3) kasıtlı **garden-of-forking-paths overfit'ini** bağlayıcı-katmanlarda (konjuge + single-split) yakaladı. "Doğrulayıcıyı kasıtlı-overfit'le red-team'ledik; reddetti — ve yakalamayan-katmanı (DSR) da tasarım-sınırı olarak dürüstçe-raporladık" = güven kazandıran negatif-kontroldür.

---

## 8. Tekrarlanabilirlik

- `python -m examples.rry1008.run_part1_known_answer` — Bölüm-1 tablosu (gerçek-veri, multi-dakika; CI-toplanmaz, veri git-ignored).
- `python -m examples.rry1008.run_part2_redteam` — Bölüm-2 üç-katman tablosu.
- Stage-0: 4 donmuş JSON (`examples/rry1008/stage0/`); Stage-0-yoksa/uyumsuzsa `require_stage0` → `Stage0Error` (ön-kayıt canlı).
- Donmuş-kararlar: h=21, nw_lag=21, GÜNLÜK, Bölüm-1=NAME, Bölüm-2=PANEL, K=24, window=2024-01-02, ADV-floor=10M, min_names_per_arm=30.

**Sıfır-regresyon:** committed-kod SIFIR-değişiklik; `src/engine` + motorlar dokunulmadı → `pytest tests/` etkilenmez. Yeni-script CI-toplanmaz.
