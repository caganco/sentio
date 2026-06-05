# RR-Y1-005 — FAZ-2 BUILD DİREKTİFİ (Builder)

**Hedef:** Builder (Claude Code, claude-sonnet-4-x — bu build-işi için Sonnet uygun).
**Tip:** BUILD. Kod + test yazılır. PR ile teslim. Committed-dosya-değişmez (paralel-yeni-modül).
**Donmuş-girdi:** `RR-Y1-005-TEST-MOTORU-TASARIM.md v0.2` — SPEC. Çelişki-önceliği: TASARIM > bu-direktif > Builder-tercihi. Tasarımdan-sapma gerekiyorsa DURUR, gerekçeyle Orchestrator'a sorarsın (kör-sapma-yok).
**Repo:** github.com/caganco/bist-trading-system. **Recon-temeli:** RR-Y1-005-FAZ1-RECON.md (kanıt dosya:satır).

---

## 0. NE KURUYORSUN (bir cümle)
Genel-amaçlı, ayarlanabilir, sonradan-denetlenebilir bir doğrulama-motoru: `harness(panel, sinyal, split_spec, dial_config) -> çıktı-vektörü`. Tek-evren (X) ve konjuge (X_1/X_2) testlerini aynı çekirdekle koşar. **Edge-avı-DEĞİL — alet.**

## 1. MİMARİ KURALLARI (değişmez)
1. **PARALLEL modül** — yeni dizin (öner: `src/engine/` veya `lab/engine/`, recon'la uyumlu konumu sen-öner). Sarmalanacak monolit YOK.
2. **Committed-motorlara DOKUNMA** (strangler): D-203..213 + C7/C8/C9 + realistic_cost + clib + eng + d204 hiçbiri değişmez. Primitiflerini **read-only import** edersin.
3. **SOLID:** net modül-sınırları — `data_adapter` / `splitter` / `neutralizer` / `cv_engine` (CPCV+purge+embargo) / `stats` (PBO/DSR/NW-t) / `stage0_validator` / `report`. Her biri tek-sorumluluk, bağımsız-test-edilebilir.

## 2. VERİ-ARAYÜZÜ (S1 — kritik, yanlış-yaparsan her-şey-çöker)
- Panel kaynağı = **`data/clean_universe/` + `data/snapshots/` PARQUET KATMANI.** `src/data/data_hub.py` (canlı-router) panel-girdisi DEĞİL — ondan veri-çekme.
- Ana panel: `data/clean_universe/adjusted_prices_2019_2026.parquet` (LONG: date,symbol,close,vwap,value_tl,...,adjusted_close,tr_index_gross,tr_index_net). 681 isim / 1848 gün.
- **Getiriler total-return** (`tr_index_gross/net`, C5) — price-only-DEĞİL.
- Survivorship: `pit_membership_2019_2026.parquet` (PIT-üyelik) + `clib.continuous_basket`. 73-delisted-in-sample korunur.
- Genelleşmiş `load_panels` adaptörü yaz; frekans-dönüşümü (günlük↔aylık) motorun-içinde (`eng.monthly_rebalance_dates` referans).

## 3. SPLIT-MODLARI (tasarım §3)
- **Mod A (cross-sectional):** aynı-zaman, ayrık-isim-yarıları. Bölme rastgele-seed-sabit VEYA likidite-eşleştirilmiş; alfabetik/sıra YASAK. Sort-depth dial-8.
- **Mod B (timing):** CPCV — N ardışık-blok, kombinatoryel train/test, purge+embargo. Günlük N=10-12,k=2.
- **Mod A+B (panel):** birleşik.
- **Aylık → Mod-A ZORUNLU** (S6); aylık temporal-CPCV'yi motor REDDETMELİ-veya-güç-uyarısı-RAISE-etmeli.

## 4. DIAL'LAR (tasarım §5, 8 adet) — hepsi config-dosyasından, koda-gömülü-DEĞİL
- #4 embargo: `h := sinyal-construction-window (h>=1)` — sinyale-özgü, tek-sabit-değil (S4).
- #8 split-arm-floor + sort-depth: likidite-floor + tercile/top-N (her-arm >=50 isim); **Stage-0'da-donar** (S5, post-hoc-kilidi).
- #3 faktör-nötrleme: market-beta (zorunlu, `exposure_d187_xu100`, günlük) + opsiyonel size/sektör/value (aylık; sektör effective-start 2019-07).
- #5 CPCV, #6 DSR, #7 cut-policy {anchored,rolling,expanding}: düz-uygula, hepsi-raporla.

## 5. STAGE-0 VALIDATOR (S3)
- Tasarım §6 JSON şemasını valide eden küçük modül. **Şema-dosyası yoksa motor KOŞMAYI-REDDEDER** (d213-precedent).
- `frozen_before_results` + `snapshots_content_hash_sha256_prefix` + engine-hash-assert (STAGE0_d213 kalıbını yeniden-kullan).
- post-hoc-guard: sonuç-üretildikten-sonra eşik/ψ/sort-depth değişirse RAISE.

## 6. KABUL-KAPISI (build BUNSUZ tamamlanmaz — pytest)
1. **Golden-fixture (§8.1):** motor C12'yi byte-yeniden-üretmeli. Beklenen (ALL): `gross_active_ann=+0.226676`, gross `NW-t=+6.928`, `net_active_ann=-0.220398`, `cc_cont` 11/11, `mean_rt_bps=46.78`, `n_pooled_days=1375`. Fixture **kendi veri-kaynağını pinler**: `snapshots/trend_v1_ohlcv...parquet` (88 survivor) + content-hash — clean_universe-DEĞİL (S/A2). Tolerans: byte (seed-pinli, c12 NULL_SEED+s).
2. **Synthetic-null (§8.2):** random-walk girdide PBO-yüksek + DSR-ölü. Çıkmıyorsa FAIL (motor yalan-söylüyor).
3. Her modül birim-testli; sıfır-regresyon (committed-testler yeşil-kalır).

## 7. ÇIKTI-VEKTÖRÜ (tasarım §7) — pass/fail-DEĞİL, vektör
gross/net/cost/tax (D-207 via `clib.per_name_round_trip`, total-return) · adil-null+mirror · reel-relative-benchmark (>max(TÜFE,TLREF)) · PBO·deflated-OOS-t·DSR · konjuge-uyum + kalıntı-cross-sectional-korelasyon · per-rejim ayrışım (manuel-etiket) · parametre-platosu.

## 8. DİSİPLİN (guard-RAISE şartları)
- **PM-1:** nakde-çıkan/nakit-gate prototip → RAISE. Boşta=tam-yatırımlı-EW.
- composite-optimize YASAK; alt-grup-dilimleme YASAK; look-ahead-safe(knowable-lag); reel-deflate.
- Builder ölçüm-bulgularına göre tasarımla-çelişki görürse DURUR + sorar (kör-sapma-yok).

## 9. TESLİM
- PR, CI-yeşil. Committed-dosya-değişmez (yeni paralel-modül + yeni-testler + config-örnekleri).
- PR-açıklaması: modül-haritası + kabul-kapısı-sonuçları (golden-fixture byte-eşleşme + synthetic-null) + tasarım-§-referansları.
- `RESEARCH_REGISTRY.md` satır-önerisi (commit Çağan-manuel).

## 10. YAPMA
- Edge-avı / mezarlık-iplik-açma (C10-yasağı). Bu alet, izin-belgesi-değil.
- Committed-motor-değiştirme; composite-optimize; sonuca-bakıp-dial-gevşetme.
- DataHub'dan-canlı-veri-çekme (panel parquet-katmanından).
- Tasarımdan-sessiz-sapma (çelişki → DUR + sor).

---

## EK — ÇATAL-KARARLARI (S#14, Orchestrator+Çağan; build-direktifine bağlayıcı)

Builder Faz-1.5 spec'i okuyup "STOP-and-ask" ile üç-çatal getirdi; kararlar:

**Çatal-1 — CSCV PBO → gerçek-CSCV kur (A).** Mod-A konjuge-çekirdeği için **gerçek CSCV median-rank PBO** yaz (math-spec v1.1 §4.1/§5). Mevcut `compute_pbo` (basit `P(OOS Sharpe<0)` proxy) yalnız Mod-B convenience-bacağında, **etiketli**. Gerçek-CSCV-PBO §7 fixture'larıyla doğrulanır (saf-gürültü→yüksek-PBO; gömülü-gerçek→düşük-PBO).

**Çatal-2 — teslim → Incremental 5-PR.** Faz-sırası (bağımlılık-doğru, anti-slop-kapıları-koduyla-gelir):
- **Faz-0:** scaffold + Stage-0-validator + data_adapter (parquet-katmanı, S1).
- **Faz-1:** stats + Mod-B (temporal-CPCV) + golden-fixture (byte-repro).
- **Faz-2:** neutralizer + Mod-A + konjuge-uyum (gerçek-CSCV-PBO) + 3 sentetik-fixture.
- **Faz-3:** report + çıktı-vektörü.
- **Faz-4:** hardening.
Her faz bağımsız-testli, CI-yeşil, ayrı-PR, mergeable.

**Çatal-3 — konum → SUPERSEDED (S#14-Faz-1): `src/engine/` (lab-engine-DEĞİL).**
Orijinal lab-engine gerekçesi src→lab-inversion-korkusuydu; inversion committed-only-import'la çözülüyor: stats/CV/PBO/DSR `src/backtest`'te (lab-değil); NW-anchor committed d213/d211 (c9 yalnız test-only golden, Faz-3); cost (Faz-3) lab-clib'i-değil committed `realistic_cost.py`/parquet'i okur; sektör-dial default-OFF (sector_map Faz-2-çekirdeğini gate-etmez).
- **Enforced, promised-değil:** `src/engine/` altında lab/clib import-YASAK unit-test'i (importlinter `root_package=src` lab'ı-göremez → o boşluğu bu test kapar). Strangler-saflığı mekanik-garanti.
- **Sonuç:** src/engine tam-CI-lint + mypy-strict + import-graph kapsar → eklenti-(a)/(b) MOOT; two-tier-test gereksiz; golden Faz-3 hard-gate.
- **İleri-tutarlılık (not):** sektör-dial ileride AÇILIRSA sector_map önce src'e terfi-etmeli — no-lab-import-test bunu zorlar (doğru-davranış, sürpriz-değil).

**Hand-off (Builder'a üç-dosya, sırayla):** tasarım v0.2 (bağlam) → math-spec v1.1 (formel-çekirdek) → bu build-direktifi (görev + bu-EK).
