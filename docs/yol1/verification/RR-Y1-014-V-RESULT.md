# RR-Y1-014-V — PEAD-FAIL Ölçüm-Doğrulama — Sonuç

> measurement-verification protokolünün ilk-uygulaması. RR-Y1-014 PEAD Stage-0
> **FAIL** (NW-t tam-panel −0.029, X2 −0.486, brüt-sıfır) verdiğinde sorulan soru:
> bu FAIL **gerçek-mi** (likit-BIST'te-PEAD-yok) yoksa **pipeline-artefaktı-mı**
> (implementasyon-hatası edge'i-sıfır-gösteriyor)? Bağımsız doğrular.
>
> **NE DEĞİL:** PEAD'in yeniden-ölçümü değil (DEC-053; mezar-açma-yok). PEAD-adayının
> kendi-verisinde yeni-NW-t aranmadı; lockbox'a dokunulmadı. Yalnız KONTROLLER
> (pozitif-kontrol / metamorphic / placebo / insan-slice) üretildi. committed-motor
> (src/engine) + RR-Y1-014 runner-primitifleri **aynı-kod-yolu, read-only.**

## HÜKÜM: **TRUSTWORTHY-WITH-CAVEATS**

PEAD-FAIL **ayakta ve güvenilir.** En-kritik kontrol (FAIL-verdict için pozitif-kontrol)
emphatik geçti: pipeline, enjekte-edilmiş bilinen-drifti **NW-t = 20.05** ile buldu.
Tüm metamorphic + post-event-placebo temiz. Hiçbir kontrol **bug-tutarlı-başarısız
değil.** İki caveat var, ikisi de FAIL'i çürütmüyor (biri onu destekliyor).

## Kontroller koşulmadan-önce donduruldu (FAZ-0)

Beklenen bantlar `EXPECT` sözlüğünde **ölçümden önce** sayısal yazıldı. Tehlikeli-hata
= **false-FAIL** (pipeline bir edge'i sıfır-gösteriyor) olduğundan pozitif-kontrol
(A1a) en-ağır kontroldü. Hiçbir eşik sonuç-görüldükten sonra gevşetilmedi.

## FAZ-1 — Differential / Pozitif-Kontrol (FAIL için EN KRİTİK)

| Kontrol | Beklenen (donmuş) | Ölçülen | Sonuç |
|---|---|---|---|
| **A1a sentetik-pozitif** | NW-t ≥ 2.0, işaret + | **NW-t = 20.05** (gross +%83,6/yıl; 491 üst/491 alt-olay enjekte) | ✓ PASS |
| A2 micro-case (aktif EXACT) | el-hesabıyla \|fark\|<1e-9 | exact | ✓ PASS |
| A2 nw_tstat çekirdek | mean-0→\|t\|<1e-9; +mean→t>0 | 0.0 / +66.6 | ✓ PASS |

**A1a yöntemi:** RAW olay-alanlarından (global-SUE üst-tercile olaylara +%0,4/gün,
alt-tercile −%0,4/gün, [entry..window_end] boyunca) `tr_gross`'a look-ahead-safe drift
enjekte edildi — `build_score_frame`'i **bypass** ederek pipeline'ın **kendi
sıralama+hizalamasını bağımsız** test eder. Pipeline drifti 20.05 NW-t ile geri-getirdi:
sıralama, T+2-hizalama ve getiri-yakalama **sağlam**. (Sıralama tersine-dönük olsaydı
alt-tercile seçilir, enjekte-drift yakalanmaz, NW-t negatif çıkardı.)

## FAZ-2 — Metamorphic (zorunlu girdi→çıktı ilişkileri)

| Kontrol | Beklenen | Ölçülen | Sonuç |
|---|---|---|---|
| B1 sign-reversal (injekte) | NW-t işaret-döner | +20.05 → **−18.98** | ✓ |
| B2 label-shuffle (injekte) | \|NW-t\| < 1.0 | **0.004** | ✓ |
| B3 look-ahead peek (giriş−1g) | \|NW-t\| < 1.0 (sıçrama-yok) | **0.25** | ✓ |
| B4 safe-shift (giriş+1g) | \|NW-t\| < 1.0 | **0.12** | ✓ |
| B5 rank-invariance (x³) | aktif EXACT-değişmez | max-fark **0.0** | ✓ |
| B7 benchmark-self (frac=1.0) | aktif == 0 EXACT | max **0.0** | ✓ |

Hepsi geçti: sinyal-pozisyonu sürülüyor (B1), isim↔skor link'i gerçek (B2), look-ahead-
hizalaması temiz/sıçrama-yok (B3/B4), sıralama rank-tabanlı değer-tabanlı-değil (B5),
benchmark-wiring doğru (B7). **B3/B4'ün temizliği** ayrıca tarih-aritmetiğinin doğru
olduğunu kanıtlar — bu C3-yorumu için kritik (aşağı).

## FAZ-3 — Placebo / Negatif-Kontrol

| Kontrol | Beklenen | Ölçülen | Sonuç |
|---|---|---|---|
| C1 pure-noise (12 seed) | \|ortalama NW-t\| < 1.0, ~0-merkezli | **mean −0.01**, max\|t\| 1.51, hepsi \|t\|<2 | ✓ |
| C3 pre-event placebo | \|NW-t\| < 1.0 | **NW-t = 2.97** | ✗ frozen-bar İHLAL |

### C3 frozen-bar ihlali — bug mu, confound mu? (eşik gevşetilmeden sınıflandırıldı)

C3 frozen-barı ihlal etti (2.97 > 1.0). Direktif-gereği: **bug-hipotezi adlandır VEYA
non-bug-sınıflandır.** Eşik **değiştirilmedi**; ihlalin sebebini sınıflandırmak için
bağımsız bir **ayırt-edici diagnostik** (mantığı önceden-yazılı) koşuldu: pre-event
sinyalini olay-yakınlığına göre parçala.

| Alt-pencere (gün) | NW-t | gross_active_ann | n_obs |
|---|---|---|---|
| near [−15,−3] | **2.87** | **+33,2%** | 495 |
| mid [−35,−16] | −0.11 | −0,9% | 743 |
| far [−62,−36] | 2.11 | +16,2% | 987 |

**Sınıflandırma: CONFOUND-runup (bug DEĞİL).** Üç kanıt:

1. **Olaya-yaklaştıkça-güçlenir:** near (event-öncesi 3-15 gün) gross +%33,2 = far'ın
   (+%16,2) ~2 katı. Bu **pre-announcement run-up**'ın klasik imzası — iyi-kazanç
   bildirecek hisseler duyurudan ÖNCE yükselir (öngörü/momentum/sızıntı). Pencere/join-
   bug'ı bu olay-yakınlık gradyanını üretmez.
2. **Placebo gelecekteki-SUE'ya göre sıralıyor:** sürpriz ancak duyuruda bilinir; pre-
   event penceresinde gelecekteki-SUE ile sıralamak **tasarım-gereği** run-up'ı yakalar.
   Yani C3'ün null'u ("pre-event drift sıfır") bu adayda **yanlış-tanımlı** — non-null
   beklenir, bug-değil.
3. **Pipeline bug'ı dışlanır:** 3-62 gün **kaydırılmış** bir pencerede 2.97 üretecek bir
   join/window-bug'ı, A1a'yı (20.05, tam-yerinde), B3'ü (giriş−1g→0.25), B4'ü (giriş+1g
   →0.12), B5'i (exact) ve B7'yi (exact-sıfır) de bozardı — **hepsi temiz.** Tarih-
   aritmetiği kanıtlanmış-doğru → pre-event sinyali **veride**, kodda-değil.

**Dahası, FAIL'i DESTEKLER:** "pre-event +%33 / post-event ~0" örüntüsü = bilgi
duyuruda-fiyatlanır, **harvest-edilebilir post-announcement-drift yok.** Bu tam olarak
RR-Y1-014'ün likit-PEAD-FAIL hükmüyle tutarlı (etkin-piyasa, sürpriz duyuruya-kadar
fiyatlanmış).

## FAZ-4 — İnsan-okunabilir-slice (LLM-zinciri-dışı kontrol)

`docs/yol1/verification/pead_slice_10events.csv` — 10 olay ham-alanlarıyla. Örnek
(YKBNK 2019Q1): duyuru 2019-05-03 (Cuma) → giriş **2019-05-07 (Salı, T+2 hafta-sonu-
duyarlı)**, SUE +0,060 → **TOP**, pencere-getirisi +%35. Tarih-hizalaması, SUE-işaret/
ölçek, tercile-üyelik **Çağan-gözüyle doğrulanabilir.** Slice ayrıca insan-kontrolünün
değerini gösteren kalemler yüzeye-çıkardı (örn. GSRAY off-takvim mali-yılı: 2019Q3
duyuru-2020-05 — futbol-kulübü Haziran-yıl-sonu; tek-olay, agrega-hizalama A1a/B3/B4
ile zaten-doğrulandı). *Pencere-getirisi tek-olay insan-checkpoint'idir; agrega-edge
yeniden-ölçülmedi.*

D2 ekstremler: en-yüksek/en-düşük SUE olayları ekonomik-makul (işaret/ölçek tutarlı).

## FAZ-5 — Doğrulama-Hükmü

**TRUSTWORTHY-WITH-CAVEATS.** PEAD-FAIL ayakta: pozitif-kontrol drifti-buldu (20.05),
metamorphic-tutuyor, post-event-placebo-null. **Bug-tutarlı-başarısızlık: SIFIR.**

### Yapılamayan / caveat-kontroller (dürüstçe listelenir)
- **A1b literatür-vakası: veri-bloklu.** Dış-PEAD-örneklemi (Yılmaz-2020 eski-dönem/
  illikit-dahil veya ABD-proxy) repo'da erişilemez. A1a sentetik-differential bu boşluğu
  kapatır (direktif: "veri-erişilemezse A1a yeterli").
- **C3 frozen-bar ihlali (2.97):** bug-DEĞİL, **CONFOUND-runup** sınıflandırıldı
  (yukarıda, ayırt-edici gradyan + diğer-kontrollerin-exonerasyonu). FAIL'i destekler.

### PEAD-FAIL üzerindeki etki
FAIL **güvenilir.** PEAD-likit-ekseni kapanışa hazır. Bu doğrulama bir **performans-
hükmü vermez** ve PEAD'i yeniden-ölçmez; yalnız FAIL'in pipeline-sağlamlığına dayandığını
bağımsız teyit eder. Stage-0 kararı / DEC-numarası / graveyard-kaydı ayrı bir
değerlendirme adımıdır ve bu raporun kapsamı dışındadır.

## Disiplin Özet-Kontrol

- [x] Kontroller koşulmadan-önce donduruldu; beklenen-bantlar sayısal-önceden-yazıldı (`EXPECT`).
- [x] PEAD-adayı kendi-verisinde yeniden-ölçülmedi (yalnız kontroller/transform/placebo); lockbox-dokunulmadı.
- [x] committed-motor + runner-primitifleri **aynı-kod-yolu** read-only kullanıldı.
- [x] C3 ihlalinde eşik **gevşetilmedi**; bağımsız diagnostik ile sınıflandırıldı (bug-değil-confound).
- [x] Yapılamayan-kontroller (A1b) dürüstçe-listelendi ("all-green-no-scope" eksik-doğrulama-sayılır — burada A1a-differential mevcut).
- [x] D1-slice insan-okunabilir-formda üretildi.
- [x] SUSPECT çıkmadı; dolayısıyla diriltme-önerisi söz-konusu-değil (çıksaydı: askıya, diriltme-yok).

## Üretim Kaydı

- Doğrulama: [`scripts/verification/verify_pead_stage0.py`](../../../scripts/verification/verify_pead_stage0.py)
  (RR-Y1-014 runner-primitifleri import; committed-motor read-only).
- Kanıt: `data/verification/pead_verification_results.{json,parquet}`.
- İnsan-checkpoint: `docs/yol1/verification/pead_slice_10events.csv`.
- Doğrulanan pipeline: `pead_signal_panel.parquet` (snapshot-hash `e5dddae304d686cb`,
  1.473 olay / 184 isim) — RR-Y1-014 ile birebir-aynı frozen panel.
