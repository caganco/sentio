# SPEC_PIVOT_ARCHITECTURE_1 — Strangler Refactor Builder Direktifleri

**Versiyon:** 1.0
**Tarih:** 29 Mayıs 2026 — Session #8
**Status:** Architect SPEC — onaylı, Builder direktiflerine bölünmüş yol haritası
**Karar kaynağı:** `docs/ARCHITECTURE.md` **v1.2** (TEK KARAR KAYNAĞI — S1-S5 kapalı, D-176 ampirik işlendi)
**Codebase kaynağı:** `docs/PIVOT_ARCHITECTURE_AUDIT.md` (KOVA haritası, file:line, strangler sırası Q5)
**Üreten:** Architect

> Bu SPEC, ARCHITECTURE v1.2'yi **uygular, sorgulamaz.** S1-S5 ve EK KARAR 1-3 kapalı kararlardır. SPEC kod yazmaz — hangi modül, hangi sırayla, hangi test, hangi başarı kriteri sorularına yanıt verir. Her direktif tek tek build edilebilir bir Builder görevidir.

---

## §0. AMAÇ VE KAPSAM

### 0.1 Amaç

ARCHITECTURE v1.2'nin dört-katmanlı tarama-öncelikli quantamental mimarisini (A tarama / B LLM asistan / C icra / D makro şalter), **in-place strangler refactor** ile inşa edilecek **sıralı Builder direktiflerine** böler. Strangler ilkesi: yeni modüller mevcut yapının yanına kurulur, eski linear-additive çekirdek EN SON budanır (eski çalışırken).

### 0.2 SPEC'in YAPMAYACAKLARI (sınır)

- ARCHITECTURE v1.2 kararlarını sorgulamaz (S1-S5 + EK KARAR 1-3 kapalı; uygular).
- Sıfırdan repo önermez (AUDIT Q5: in-place strangler kararı verildi).
- LLM katmanını (Katman B) erkene almaz — EN SON, çekirdek edge kanıtlandıktan sonra.
- Faktör seçimini ŞİMDİ sabitlemez — Faz 0 faktör IC harness'ının çıktısı belirler.
- Kod yazmaz — yol haritası + direktif tanımı; implementasyon Builder'ın.

### 0.3 Referans yöntemi

Her direktif, dokunulacak/dokunulmayacak dosyaları AUDIT'ten **`dosya:satır`** referansıyla verir. Doğrulama geçitleri ARCHITECTURE §7.1'e, neye-dokunma invariant'ları §9'a (12 invariant) bağlıdır.

---

## §1. KRİTİK SIRALAMA KARARI (DEC-039)

**İLK direktif TAM TARAMA SİSTEMİ DEĞİL — Faz 0 = Faktör IC Validasyon Harness'ı.**

### 1.1 Gerekçe

1. **Standalone validasyon zorunluluğu (§7.1 + §3.1):** RS/momentum faktörü composite'e girmeden ÖNCE standalone valide edilmeli. BIST güçlü contrarian/reversal gösteriyor (Bildik-Gülay 2007: kaybedenler kazananları ~%15/yıl yeniyor). Bu, mimarinin en olası **tek-nokta-başarısızlığı** (§7.1 momentum uyarısı, ÜÇ KEZ tekrarlandı).

2. **İki AÇIK KRİTİK UYARISI veriyle test edilebilir (§3.1, DEC-039 kategori-a):**
   - **TEST 1 — rank-ortalama dilüsyonu:** "eşit-ağırlık rank hâlâ bir sıkıştırma olabilir; tek-faktör uç değerlerini ortaya çeker."
   - **TEST 2 — low-vol asimetri:** "low-vol asimetrik hareketlerin zıttını seçebilir."
   Bunlar sezgiyle değil, **ÖLÇÜLEREK** karara bağlanır.

3. **Funnel faktör IC'sine bağlı:** Faktör ölü mü diri mi bilmeden tarama funnel'ı inşa etmek = kör inşaat. Tüm Katman A tasarımı (hangi faktör composite'e girer, RS atılır mı reversal'a mı çevrilir) Faz 0 çıktısına dayanır.

### 1.2 D-176 nüansı (yanlış yönlendirmeyi önle)

D-176 ampirik teşhisi (§0): birincil problem **cash drag / konuşlanma** (avg_exposure %13), ortalama-alma dilüsyonu DEĞİL; seçim çalışıyor (+5.3%/trade). **Bu, TEST 1/TEST 2'yi gereksiz kılmaz** — D-176 *eski composite seçim mekanizmasının* ekonomisini ölçtü; Faz 0 ise *yeni faktörlerin standalone IC'sini* ölçer. Dilüsyon ikincil olsa da **faktör-ölü tespiti (özellikle momentum) kritik kalır.** İki ayrı soru: "eski seçim para kazandırıyor muydu" (D-176: evet) vs "yeni faktörler tek başına IC taşıyor mu" (Faz 0: ölçülecek).

---

## §2. ÖN-KAYIT — STAGE 0 (her sayılan backtest'ten ÖNCE)

ARCHITECTURE §7.1 gereği: backtest koşmadan ÖNCE yazılır, timestamp'lenir, **dondurulur (dated git commit):**

- 4 gating eşik + failure eşikleri (§5).
- Faktör tanımları (§4 Faz 0).
- Maliyet modeli: komisyon (~%0.1-0.3/side) + **%5 BSMV** (komisyon üzerine) + spread; round-trip ~%1.5.
- Benchmark: **max(TÜFE `TP.FG.J0`, TLREF `TP.BISTTLREF.KAPANIS`)**; risk-free = MMF/repo.
- **Maksimum konfigürasyon N ≤ 3 (ideal N=1).** MinBTL: <3 yıl veriyle 7 varyant = garantili overfitting (López de Prado). Bu, "beating ideas to death"i KISITLAR — önceden-kayıtlı tek tasarım.

Stage 0 iki kez bağlayıcıdır: **Faz 0 harness koşumundan önce** (faktör tanımları + IC eşiği) ve **Faz 1 funnel backtest'inden önce** (gating eşikleri). N≤3 bütçesi tüm programa yayılır, faz başına değil.

---

## §3. FAZ HARİTASI (sıralı + bağımlılık)

| Faz | Direktif | Katman | Bağımlılık | Hedef geçit |
|-----|----------|--------|------------|-------------|
| **Stage 0** | Ön-kayıt (eşikler/tanımlar dondur) | — | — | (kapı, ölçüm değil) |
| **Faz 0** | **Faktör IC Validasyon Harness'ı (DETAYLI)** | A-öncesi | Stage 0 | per-faktör IC (supportive) + TEST 1/2 + RS kararı |
| **Faz 1** | Katman A tarama iskeleti | A | Faz 0 | gating #1 (rank-IC+ICIR) + #4 (tercile) |
| **Faz 2** | Katman C icra bağlantısı | C | Faz 1 | gating #2 (PBO) + #3 (reel spread) + D-176 baseline |
| **Faz 3** | Katman D makro şalter genişletme | D | Faz 1 + 2 | exposure/DD stabilitesi (supportive) |
| **★ Çekirdek edge geçidi** | **4 gating AND** | — | Faz 1+2 (3 ile rafine) | hepsi geçerse → Faz N + Faz B |
| **Faz N** | KOVA 3 budama (composite/conviction) | — | TÜM fazlar + edge geçidi | pytest yeşil, regresyon yok |
| **Faz B** | Katman B LLM asistan | B | Çekirdek edge kanıtlı | §7.2 ablation (backtest YOK) |

### 3.1 Bağımlılık grafiği

```
Stage 0 (ön-kayıt)
   │
   ▼
Faz 0  Faktör IC Harness ──► faktör seti + RS kararı (at/reversal/tut)
   │
   ▼
Faz 1  Katman A tarama ──────────────┐ (rejim sert-kapısı: mevcut classify_regime binary)
   │                                 │
   ▼                                 ▼
Faz 2  Katman C icra            Faz 3  Katman D şalter (Faz 1 rejim kapısını genişletir)
   │                                 │
   └──────────────┬──────────────────┘
                  ▼
        ★ ÇEKİRDEK EDGE GEÇİDİ — 4 gating AND
                  │ (hepsi geçerse)
        ┌─────────┴─────────┐
        ▼                   ▼
   Faz N  KOVA 3 budama   Faz B  Katman B LLM (paper-trade)
```

**Sıralama mantığı:** Faz 3 (Katman D) Faz 1'in rejim sert-kapısını (mevcut `macro_regime_gate.classify_regime`, binary ON/OFF) **portföy-beta şalterine** (full/tighten/cash) genişletir; bu yüzden Faz 1 minimal Layer-D'yi kullanır, Faz 3 zenginleştirir — döngü yok. Faz N ve Faz B yalnızca çekirdek edge 4-gating'i geçtikten sonra başlar (strangler: eski EN SON budanır).

---

## §4. DİREKTİF DETAYLARI

Her direktif şu şablonu izler: **Amaç · Bağımlılık · Dokunulacak (file:line) · DOKUNULMAYACAK · Başarı kriteri · Test gereksinimi · Hedef geçit · Korunan invariant'lar.**

---

### FAZ 0 — FAKTÖR IC VALİDASYON HARNESS'I  ⭐ (DETAYLI — hemen build edilebilir)

**Amaç.** Üç aday faktörü (RS-vs-XU100, low-vol, USD-bazlı value) composite'e girmeden ÖNCE standalone cross-sectional rank-IC ile valide et; §3.1'in iki açık hipotezini (TEST 1 dilüsyon, TEST 2 low-vol asimetri) veriyle karara bağla. **Çıktı = Faz 1'e girecek faktör seti + RS karar kuralı** (tut / at / kısa-vadeli reversal'a çevir).

**Bağımlılık.** Stage 0 (ön-kayıt). **Ön-koşul (sertleştirilmiş — bkz. §8.2): dondurulmuş point-in-time fiyat snapshot (tek seferlik çekim → parquet).** Tekrarlanamaz fiyatla TEST 1/TEST 2 karara bağlanamaz.

**Ölçülecekler (§7.1 metodolojisi):**

1. **Per-faktör standalone rank-IC + ICIR.**
   `rank-IC = Spearman(faktör_rank_t, fwd_return_rank_{t+h})`; `ICIR = mean(IC)/std(IC)`; IC serisine **t-test**.
2. **IC decay** `h ∈ {1, 5, 10, 21, 63}` işgünü → S5 rebalance frekansını kalibre eder (haftalık tarama / iki-haftalık-aylık rebalance).
3. **TEST 1 — rank-ortalama dilüsyonu (§3.1 açık uyarı):** eşit-ağırlık composite rank-IC vs **en iyi tek-faktör IC**. `composite < en iyi tek-faktör` → rank-ortalama dilüe ediyor → **faktör SETİNİ daralt** (ağırlığı optimize ETME — invariant #4; çözüm seçim, ağırlık değil).
4. **TEST 2 — low-vol asimetri (§3.1 açık uyarı):** low-vol standalone IC + **sağ-kuyruk** (yüksek-fwd-getiri) hisseleriyle korelasyon. `IC ≤ 0` VEYA sağ-kuyrukla güçlü negatif → low-vol asimetriyi kesiyor → low-vol'u yeniden değerlendir.
5. **RS karar kuralı (EK KARAR 1 + §7.1 momentum uyarısı):** RS-vs-XU100 standalone `IC ≤ 0` → **at veya kısa-vadeli reversal sinyaline çevir** (Bildik-Gülay contrarian).

**Faktör tanımları (S3/S4 + §3.1 — Stage 0'da dondurulur):**
- **RS-vs-XU100:** 6 & 12 ay, skip-1-ay. Mutlak nominal RS YASAK (invariant #5 — enflasyon kirliliği).
- **low-vol:** getiri volatilite rank (lookback Stage 0'da sabit).
- **value:** USD-bazlı F/DD + EV/EBITDA. Nominal F/K YASAK (TMS 29, S4). UFRS/TMS 29 finansalları ZORUNLU (VUK 2025-27 ertelendi). ⚠️ 2022-2024 yapısal kırılma (TMS 29 ilk 2023 sonu) backtest'te işaretlenir.

**Kullanılacak primitive'ler (green-field DEĞİL — §3.5 / AUDIT §2.2.1):**
- `compute_universe_percentiles` — `data/short_interest_normalizer.py` (cross-sectional rank).
- `SmartMoneyNormalizer._rolling_percentile` — `signals/layers/smart_money_layer.py` (rolling percentile).
- `score_xbrl_surprise` [-40,+40] — `analytics/kap_xbrl_scorer.py:85-132` (**tüm faktör-skorlaması için referans ŞABLON**, cross-sectional native).
- `analysis/momentum.py`, `analysis/technicals.py` — RS/momentum/MA/vol **ham faktör kaynağı** (ham sub-faktör; rolled-up 0-100 KULLANMA — AUDIT §2.2.1).
- `analytics/ic_calculator.py` — IC hesap primitive'i.
- `backtest/statistical_validation.py` (DSR/PBO/CPCV/Newey-West) + `backtest/cross_validation.py` (Purged K-Fold) — CPCV makinesi yeniden kullanılır.
- `backtest/data_loader.py`, `backtest/validation_constants.py` — tarihsel veri + survivorship.

**Yeni modül.** `screening/factor_ic_harness.py` — KOVA 1'in yanına; hiçbir `composite`/`conviction`/`MASTER_WEIGHTS` import ETMEZ.

**Look-ahead guard (§7.3):**
- Takas: post-close + T+2 → ≥1 gün lag (≥2 güvenli pre-T+1); MKK ücretsiz feed ~10 işgünü gecikme → backtest lag'i gerçek feed'e eşitlenir.
- KAP: period-end DEĞİL, gerçek disclosure tarihi (FY2025 non-consol 2 Mart, consol 11 Mart 2026).
- Point-in-time evren; survivorship: halt/delist dahil (KOZAA/KOZAL/IPEKE/TRALT).

**DOKUNULMAYACAK.**
- `backtest/engine.py` harness (~490 satır: `177-202` döngü, `379-467` execute, `471-523` portföy, `344-361` makro-gate).
- composite/conviction kodu (`calculator.py`, `conviction_validator.py`, `MASTER_WEIGHTS`) — Faz N'e kadar **canlı kalır**.
- KOVA 1 risk/icra modülleri.

**Başarı kriteri.**
- Her faktör için IC + ICIR + **güven aralığı** raporlanır (per-faktör IC = supportive, ölü-faktör tespiti).
- TEST 1 ve TEST 2 veriyle karara bağlanır (dilüsyon var/yok; low-vol asimetri kesiyor/kesmiyor).
- RS karar kuralı uygulanır (IC≤0 → at/reversal).
- Faz 1'e girecek faktör seti netleşir.
- **Tekrarlanabilirlik:** aynı dondurulmuş snapshot → bit-aynı IC.

**Test gereksinimi.**
- IC hesap birim testi (sentetik veri → analitik bilinen IC).
- Look-ahead guard testi (kaydırılmış veri → sızıntı sıfır).
- Survivorship dahil testi (KOZAA/KOZAL tarihsel evrende mevcut).
- **Snapshot determinizm testi** (aynı parquet → bit-aynı IC; D-176 %67 reconciliation'a karşı — bkz. §8.2).

**Hedef geçit.** 4-gating DEĞİL — **pre-funnel faktör-seçim kapısı** (supportive per-faktör IC). Çıktı Faz 1 tasarımını belirler. Faktörün hepsi `IC≤0` çıkarsa → mimarinin çekirdek faktör seti yeniden düşünülür (premise re-think, §5 failure).

**Korunan invariant'lar.** #1 KOVA 1, #2 harness, #4 eşit-ağırlık (harness ağırlık optimize etmez, yalnız seçim), #5 RS-vs-XU100, #8 maliyet-sonrası, #9 survivorship.

---

### FAZ 1 — KATMAN A TARAMA İSKELETİ

**Amaç.** Faz 0'da hayatta kalan faktörlerle hibrit funnel'ı kur (§3.1): **SERT KAPILAR** (ardışık AND: ADV tabanı → rejim → tradeable-next-open → veri tazeliği) → **EŞİT-AĞIRLIKLI RANK COMPOSITE** (hayatta kalan faktörler, rank ortala, z-score DEĞİL) → **TAKAS TIE-BREAKER** → eşik-kapılı **top-5/10** (zayıf rejimde daha az).

**Bağımlılık.** Faz 0 (faktör seti + RS kararı). Rejim sert-kapısı için mevcut `macro_regime_gate.classify_regime` (binary ON/OFF) kullanılır; Faz 3 genişletir.

**Dokunulacak (yeni).** `screening/` modülü (Katman A). KOVA 1 **ham sub-faktörlerini** tüket (AUDIT §2.2.1 — rolled-up 0-100 DEĞİL, gömülü ağırlık taşır):
- Trend → `technical.detail["adx"]` (`signals/layers/technical_layer.py:196-204`) / `analysis/` ADX.
- Likidite → `is_adv_eligible()` (`smart_money_layer.py`, zaten boolean filtre) / `volume_surge`.
- RS/momentum → `technical.detail["momentum_score"]` / `compute_momentum_score` (yalnız Faz 0'da hayatta kaldıysa).
- Takas/yabancı → `compute_percentile_score` / `compute_level_score` (`smart_money_layer.py`).
- Value → `score_xbrl_surprise` cross-sectional (`kap_xbrl_scorer.py:85-132`).

**DOKUNULMAYACAK.** composite/conviction (canlı), backtest harness, engine sinyal aşaması (henüz değil — Faz 2).

**Başarı kriteri.**
- Funnel BIST100'den top-5/10 üretir; zayıf rejimde liste daralır.
- Tarama composite'i üzerinde **gating #1** (rank-IC ≥ 0.03, hedef 0.05; ICIR ≥ 0.5) ve **#4** (tercile top-minus-bottom spread pozitif + anlamlı) sağlanır. N≤3 konfigürasyon (ön-kayıt).
- §3.1 açık-uyarı testleri (Faz 0 ön-bulgusu) production funnel'da teyit edilir.

**Test gereksinimi.** Her sert kapı bağımsız birim testi; funnel entegrasyon testi (sentetik evren → beklenen top-N); gating CPCV ile hesaplanır; **ham-faktör tüketim testi** (rolled-up 0-100 skor kullanılmıyor doğrulaması).

**Hedef geçit.** gating #1 + #4.

**Korunan invariant'lar.** #4 eşit-ağırlık (z-score/optimize YASAK), #5 RS-vs-XU100, #8 maliyet-sonrası, #9 survivorship, #11 cash drag Katman A yapısıyla (naif eşik-düşürme YASAK).

---

### FAZ 2 — KATMAN C İCRA BAĞLANTISI

**Amaç.** Tarama çıktısını deterministik icraya bağla. `kelly_win_prob(composite)` → **EV/rank tabanlı win-prob** (Katman C'de yeniden türet). `conviction_score`/`conviction_tier` alanlarına **yeni anlam** ver (sessiz kırılma riski — §8.1). Konuşlanmayı yükselt (D-176 cash drag), **naif eşik-düşürme olmadan.**

**Bağımlılık.** Faz 1 (tarama sinyali).

**Dokunulacak.**
- Yeni `execution/` modülü (Katman C) — AUDIT Q5 adım 1.
- `backtest/engine.py` sinyal aşaması yönlendirme: `kelly_win_prob` → Katman C EV (`backtest/engine.py:365-377`, çağrı `:372`); `_composite_to_signal` (`:333-342`) → Katman A kararı; loop çağrısı (`:208-209`), sinyal→aksiyon dalı (`:216-219`).
- KOVA 1 yeniden kullan: `risk/kelly.py` (quarter-Kelly), `risk/position_sizer_v2.py` (`apply_adv_cap` D-145, `net_expected_value_check` D-146), `risk/stop_calculator.py` (vol-aware, floor -%20), `order_engine/staged_exit_manager.py` (TP1/2/3).
- conviction alanları: `models.py:53-54, 64-65` — yeni anlam ata.

**DOKUNULMAYACAK.** Harness loop/portföy/exit (~490 satır: `177-202`, `379-467`, `471-523`); composite tanımı (Faz N'e kadar); **staged exit yapısı — runner/trailing EKLENMEZ (invariant #10, D-176 reddetti).**

**Başarı kriteri.**
- Katman C pozisyon boyutunu EV/rank'tan üretir (composite'ten DEĞİL).
- conviction alanları yeni anlam taşır; **sessiz sıfırlanma yok** (§8.1).
- Uçtan uca backtest yeni tarama + yeni icra ile koşar.
- **D-176 baseline GEÇİLİR (§6):** seçim kalitesi korunur (expectancy ≥ +5.3%/trade, win ~≥58.7%, PF ≥2.19) VE avg_exposure %13'ten **belirgin yukarı.** Naif BUY-eşik-düşürme YASAK (invariant #11).
- **gating #2** (PBO < 0.5) + **#3** (net-of-cost reel spread +%3-5) sağlanır.

**Test gereksinimi.** EV/rank win-prob türetme testi; **SESSİZ KIRILMA GUARD testi** (geçerli BUY kararında conviction alanları dolu + pozisyon boyutu ≠ 0); `position_sizer_v2` adaptasyon testi; uçtan uca D-176 parity testi (yeni vs eski seçim ekonomisi); **quarter-to-half Kelly enforcement testi.**

**Hedef geçit.** gating #2 + #3 + D-176 baseline.

**Korunan invariant'lar.** #1, #2, #8, #10 (runner/trailing yok), #11 (cash drag, naif eşik-düşürme yok), #12 (DSR supportive).

---

### FAZ 3 — KATMAN D MAKRO ŞALTER GENİŞLETME

**Amaç.** Mevcut binary rejim kapısını **portföy-beta şalterine** genişlet (full / tighten / cash). Per-stock filtre DEĞİL — **portföy seviyesi** risk aç/kapa.

**Bağımlılık.** Faz 1 (rejim sert-kapı olarak kullanılıyor) + Faz 2.

**Dokunulacak.**
- `signals/macro_regime_gate.py` (`classify_regime`) — girdileri genişlet: XU100 vs 200-MA (primary), breadth (% constituents > 50-MA), trend-strength (50/200-MA slope, ADX), yabancı akış yönü (Ülkü-İkizlerli), CDS rejimi.
- `backtest/engine.py:344-361` (`_is_entry_gated_by_macro`, mevcut VIX>35 / USDTRY+%3) → portföy-beta şalterine genişlet. `_global_macro_score` (`:305-331`), `_safe_macro` (`:567-572`) yeniden kullanılır.
- Opsiyonel: `regime_hmm.py` rejim tespiti Katman D'ye taşınır — ama ağırlık override (`get_hmm_weight_override`, `engine.py:193-205`) anlamı İPTAL (composite öldü).

**DOKUNULMAYACAK.** Per-stock tarama mantığı (Katman D portföy-seviyesi); harness portföy/exit.

**Başarı kriteri.** Katman D taramayı kapılar (rejim ON → tara) ve exposure'ı modüle eder (tighten: N azalt + eşik yükselt; cash). Backtest, exposure modülasyonunun reel getiri/drawdown'u always-on'a kıyasla iyileştirdiğini gösterir. Konuşlanma yönetimini destekler (D-176).

**Test gereksinimi.** Rejim sınıflama testi; exposure-durum geçiş testi (full↔tighten↔cash); tarama kapısıyla entegrasyon testi.

**Hedef geçit.** exposure/drawdown stabilitesi (supportive); CPCV path tutarlılığı.

**Korunan invariant'lar.** #1, #2; Katman D **portföy-seviyesi** (per-stock DEĞİL).

---

### ★ ÇEKİRDEK EDGE GEÇİDİ (Faz 1+2, Faz 3 ile rafine)

**4 gating AND** (§5.1) sağlanırsa → çekirdek edge kanıtlandı → Faz N (budama) + Faz B (LLM) açılır. **Herhangi biri başarısız → çekirdeği yeniden düşün.** Patch'leyip yeniden koşma YASAK — bu, ön-kaydın engellemek için var olduğu post-hoc rasyonalizasyondur.

---

### FAZ N (EN SON) — KOVA 3 BUDAMA

**Amaç.** Ölü linear-additive çekirdeği buda. **SADECE** çekirdek edge (4 gating) kanıtlandıktan + D-176 baseline geçildikten sonra.

**Bağımlılık.** TÜM önceki fazlar + çekirdek edge geçidi.

**Dokunulacak (buda).**
- `thresholds.py:22-29` (`MASTER_WEIGHTS`) + `SIGNAL_THRESHOLDS` + `CONVICTION_*` + `KELLY_WIN_PROB_*` **alt kümesi.** ⚠️ `thresholds.py`'nin geri kalanı (path/TTL/lookback/config — 45 dosya import eder) YAŞAR.
- `calculator.py:26-53` (`compute_composite_score`), `:66-80` (`signal_from_composite`), `:83-92` (`kelly_win_prob`).
- `conviction_validator.py:48-63` (`compute_conviction` + tier ≥0.68/0.55).
- `backtest/engine.py:257-303` (`_compute_composite`), `:333-342` (`_composite_to_signal`).
- `signals/engine.py` composite yolu (`:339` `_compute_weighted_sum`, `:344` `compute_conviction`, `:193-205` HMM override).
- 6 layer dosyasındaki `weight=MASTER_WEIGHTS["..."]` / `_w("...")` damgaları (mekanik tek-satır silme).
- `weight_validator.py` + `test_architecture.py` weight invariant'ları (`MASTER_WEIGHTS_SUM`).
- Ölü testler: `test_master_weights`, `test_conviction_validator`, `test_backtest_production_parity`, `test_layer_attribution` composite kısmı, `test_engine` composite kısmı (**~150-250 test bandı** — kesin sayı refactor sonrası `pytest` ile).

**DOKUNULMAYACAK.** KOVA 1 (data/risk/infra/kantitatif faktörler), harness, `thresholds.py` ölü-olmayan alt kümesi.

**Başarı kriteri.** composite tamamen kalkar; kalan tüm testler yeşil; yeni mimari standalone; **conviction default'larına (0.0/"WATCH") sessiz düşüş yok**; `grep MASTER_WEIGHTS` production'da = 0 (27 dosya temizlenir).

**Test gereksinimi.** Tam `pytest` yeşil; architecture testi güncellenir; dangling `MASTER_WEIGHTS` referansı yok doğrulaması; KOVA 1 regresyon yok (~1.200+ data/risk/infra testi korunur).

**Hedef geçit.** pytest yeşil + regresyon yok.

**Korunan invariant'lar.** #1, #2, #3 (strangler sırası — bu EN SON), #8.

---

### FAZ B (EN SON — çekirdek edge kanıtlandıktan sonra) — KATMAN B LLM ASİSTAN

**Amaç.** ARCHITECTURE §4 LLM asistanı. **Yalnız** çekirdek edge (4 gating) kanıtlandıktan sonra. LLM = öneri, **asla** tetik/sizing.

**Bağımlılık.** Çekirdek edge geçidi (4 gating).

**Dokunulacak (yeni).** Katman B modülü. KOVA 2 NLP'yi tüket (`nlp/finbert_analyzer.py`, `signals/sentiment/*`) + KAP event özeti (`kap_layer.py:60-92`). Çıktı: yorumlu kısa liste + bağlam + **ayı senaryosu (red-team) + hipotez** → kullanıcı dosyası (aktüatör DEĞİL).

**DOKUNULMAYACAK.** Tetik/sizing yolu (invariant #6 — LLM tetiğe bağlanmaz).

**Başarı kriteri (§7.2 — backtest EDİLEMEZ, contamination).** 6-12 ay paper-trade, post-training-cutoff veri (doğal OOS); ablation (**rules-only vs rules+LLM vs buy-and-hold**), hepsi reel/TÜFE-ayarlı. LLM katkı kanıtlamazsa → **öldür** (baseline disiplini §4.3, ego değil).

**Test gereksinimi.** Grounding testi (LLM sayı üretmiyor — verilen sayı üzerinde akıl yürütüyor); tetik-izolasyon testi (LLM çıktısı hiçbir aktüatöre bağlı değil).

**Hedef geçit.** §7.2 ablation (gating DEĞİL — paper-trade). **ASLA LLM-in-the-loop backtest (invariant #7, Lopez-Lira-Tang-Zhu 2025 memorization).**

**Korunan invariant'lar.** #6 (LLM tetiğe bağlanmaz), #7 (LLM-in-the-loop backtest yok).

---

## §5. DOĞRULAMA GEÇİTLERİ (faz faz)

### 5.1 4 GATING KRİTER (hepsi sağlanmalı — AND) [§7.1]

```
1. Composite rank-IC ≥ 0.03 (hedef 0.05) VE ICIR ≥ 0.5
   rank-IC = Spearman(signal_rank, fwd_return_rank); IC serisine t-test
   ⚠️ rank-IC > 0.15 → KUTLAMA DEĞİL, overfitting şüphesi
   ⚠️ BİRİNCİL KANIT bu (cross-sectional, binlerce hisse-ay gözlem)

2. PBO < 0.50 (hedef < 0.20) — CSCV/CPCV
   ⚠️ Optimize ağırlık YOK → yapısal düşük olmalı (tasarım avantajı)

3. Net-of-cost REEL getiri pozitif VE benchmark'ı geçer
   benchmark = max(TÜFE, TLREF); hedef +%3-5 reel spread
   ⚠️ +%10 reel spread → overfitting şüphesi; Sharpe reel/USD bazlı

4. Tercile (quintile DEĞİL) top-minus-bottom spread POZİTİF VE anlamlı
   ⚠️ Tam monotonluk (Patton-Timmermann) SUPPORTIVE, gating değil
```

### 5.2 SUPPORTIVE (gating DEĞİL — sizing/güven bilgisi)

**DSR (Deflated Sharpe Ratio)** — invariant #12: gating'den supportive'e indirildi (az örneklemde Sharpe ölçülemezse DSR de gürültülü → false-negative riski; DSR<0.90 = uyarı, tek başına reddetmez). Ayrıca: walk-forward efficiency ≥ 0.5, tam monotonluk, turnover/maliyet oranı, CPCV path drawdown stabilitesi, **per-faktör IC (ölü faktör tespiti — özellikle momentum)**.

### 5.3 FAILURE EŞİKLERİ (herhangi biri → "premise'i yeniden düşün") [§7.1]

```
- Composite rank-IC ≤ 0          → hard fail
- Composite ICIR < 0.3           → çok kararsız
- PBO > 0.50                     → muhtemelen overfit
- Net-of-cost reel getiri ≤ 0    → enflasyona/cash'e kaybediyor
- Tercile spread negatif/anlamsız
- Max drawdown > ~%35-40 VEYA CPCV path'leri arası tutarsız
- Tek dayanak faktör negatif standalone IC (özellikle momentum)
```

### 5.4 CPCV mekaniği [§7.1]

N=6 grup, k=2 → 15 split, **5 backtest path**. **Purge:** 1-2 ay holding label-overlap temizle. **Embargo:** sonrasında leak engelle. Çıktı: OOS Sharpe **dağılımı** (tek nokta değil).

### 5.5 Geçit-faz eşleştirmesi

| Geçit | Hangi fazda ölçülür | Not |
|-------|---------------------|-----|
| per-faktör IC (supportive) | Faz 0 | pre-funnel faktör seçimi; TEST 1/2/RS kararı |
| #1 rank-IC + ICIR | Faz 1 | sinyal-seviyesi; tarama composite'i |
| #4 tercile spread | Faz 1 | sinyal-seviyesi; fwd-return ile |
| #3 net-of-cost reel spread | Faz 2 | tam pipeline + maliyet modeli |
| #2 PBO | Faz 2 | tam pipeline CPCV |
| exposure/DD stabilitesi (supportive) | Faz 3 | always-on'a kıyas |
| **4 gating AND** | **Faz 1+2 (3 ile rafine)** | **çekirdek edge geçidi** |

### 5.6 Önemli ilkeler

- **Absence of evidence ≠ evidence of absence (NRR-003):** ~24 ayda genelde "kanıt yokluğu." IC ~0 + dar CI → kanıt yok → öldür. IC pozitif ama anlamsız + geniş CI → belirsiz → **deploy ETME, başarı İLAN ETME**, veri topla.
- **Gerçekçi hedef:** OOS Sharpe ~0.5-0.8 (1.5-2.0 DEĞİL — o overfit).
- **Quarter-to-half Kelly ZORUNLU** (full Kelly %50-60 drawdown riski).

---

## §6. D-176 BASELINE (yeni tarama bunu GEÇMELİ — ampirik)

Eski composite seçim mekanizmasının (terk edilen) ölçülmüş per-trade ekonomisi — **yeni tarama bu çubuğun altına düşemez:**

| Metrik | Eski (D-176) | Yeni tarama hedefi |
|--------|--------------|--------------------|
| Expectancy / trade | **+5.3%** | ≥ +5.3% (tercihen artır) |
| Win rate | **58.7%** | korunmalı (~≥58.7%) |
| Profit factor | **2.19** | ≥ 2.19 |
| Payoff ratio | **1.63** | korunmalı |
| avg_exposure | **%13** (sermayenin %87'si atıl) | **belirgin yukarı** |
| Skewness | **+0.10** (hafif pozitif) | negatif çarpıklık yok |

**Geçer kriteri (Faz 2'de):** seçim kalitesi KORUNUR **VE** konuşlanma yükselir. Yeni tarama eski seçimin **+5.3%/trade edge'ini düşürürse → tarama tasarımı başarısız.** Konuşlanma artışı **naif eşik-düşürme ile DEĞİL** (kalite düşürür — invariant #11); Katman A'nın yapısal "her zaman top-5/10 seçili" mantığıyla doğal çözülür (§5 ARCHITECTURE). Çıkış profili korunur — runner/trailing eklenmez (D-176 runner counterfactual'ı veriyle reddetti: trailing 8/10%'da net negatif).

---

## §7. NEYE-DOKUNMA — 12 INVARIANT (ARCHITECTURE §9)

Her direktifte korunur:

| # | Invariant | En yüksek risk fazı |
|---|-----------|---------------------|
| 1 | **KOVA 1 korunur** (veri/risk/icra/backtest-infra/kantitatif faktörler) | Faz N (budama) |
| 2 | **Harness korunur** (~490 satır loop/portföy/exit/execution) | Faz 2, Faz N |
| 3 | **Strangler sırası** (yeni yanına, eski EN SON) | tüm fazlar |
| 4 | **Eşit-ağırlık** (Katman A'da z-score/optimize YASAK) | Faz 0, Faz 1 |
| 5 | **RS-vs-XU100** (mutlak nominal RS YASAK — enflasyon) | Faz 0, Faz 1 |
| 6 | **LLM tetiğe bağlanmaz** (Katman B = öneri) | Faz B |
| 7 | **ASLA LLM-in-the-loop backtest** (contamination) | Faz B |
| 8 | **Maliyet-sonrası ölçüm** (komisyon + %5 BSMV + spread) | Faz 1, Faz 2 |
| 9 | **Survivorship** (halt/delist dahil — KOZAA/KOZAL/IPEKE/TRALT) | Faz 0, Faz 1 |
| 10 | **Runner/trailing EKLENMEZ** (D-176 reddetti; profit_target/stop korunur) | Faz 2 |
| 11 | **Cash drag çözümü Katman A ile** (naif BUY-eşik-düşürme YASAK) | Faz 1, Faz 2 |
| 12 | **DSR gating DEĞİL** — supportive; birincil kanıt rank-IC | Faz 1, Faz 2 |

---

## §8. RİSK NOTLARI

### 8.1 Sessiz kırılma (conviction default'ları)

`conviction_score`/`conviction_tier`, `models.py:53-54, 64-65`'te **default'lu** (`0.0` / `"WATCH"`). Composite koparılıp Katman C bağlanmazsa downstream patlamaz — sessizce default görür → **tüm pozisyon boyutlandırma 0'a düşer (gözle görülür hata yerine sessiz sıfırlanma).**

**Mitigasyon (Faz 2 zorunlu):** Bu alanlara **yeni anlam ZORUNLU** atanır + **sessiz kırılma guard testi**: geçerli BUY kararında conviction alanları dolu VE pozisyon boyutu ≠ 0 assert edilir. Bu, mimarinin en yüksek sessiz-kırılma riskidir (AUDIT §2.3, EK-5).

### 8.2 Fiyat non-determinizmi — DONDURULMUŞ SNAPSHOT ZORUNLU (sertleştirilmiş)

D-176'da yfinance fiyat kaynağında **%67 reconciliation** görüldü — fiyat verisi tekrarlanamaz. **Tekrarlanamaz fiyatla TEST 1/TEST 2 ve per-faktör IC karara bağlanamaz** (aynı kod farklı IC üretir → karar gürültüye dayanır).

**Mitigasyon — Faz 0 SERT ÖN-KOŞULU (reconciliation testi YETMEZ):**
- **Dondurulmuş point-in-time fiyat snapshot ZORUNLU:** BIST100 tarihsel fiyat (+ survivorship: halt/delist dahil) **tek seferlik çekilir → parquet'e yazılır → dondurulur.** Tüm faktör IC hesabı bu dondurulmuş snapshot'tan okur; canlı API'den DEĞİL.
- Snapshot'ın kendisi Stage 0'da timestamp'lenip versiyonlanır (dated commit / parquet hash).
- Snapshot determinizm testi (§4 Faz 0): aynı parquet → bit-aynı IC.
- **Gerekçe:** reconciliation testi sadece tutarsızlığı *tespit* eder; snapshot dondurma tutarsızlığı *ortadan kaldırır.* IC tekrarlanabilirliği için zorunlu — opsiyonel değil.

### 8.3 Az örneklem (IC birincil, Sharpe değil)

~2 yıl veri + 1-2 ay holds = ~12-40 örtüşen trade → **Sharpe'ta istatistiksel anlamlılık İMKANSIZ** (NRR-003). Birincil kanıt **cross-sectional rank-IC** (~100 hisse × ~24 ay ≈ binlerce hisse-ay). DSR bu yüzden supportive (#12). Gerçekçi hedef OOS Sharpe 0.5-0.8; quarter-to-half Kelly zorunlu. Bu, §5'in tüm gating felsefesinin temelidir.

---

## §9. KAYNAK REFERANSLARI

- **ARCHITECTURE v1.2** — TEK karar kaynağı; §0 (D-176 teşhis), §3.1 (hibrit funnel + açık kritik uyarısı), §7.1 (4 gating + DSR supportive), §7.3 (look-ahead), §9 (12 invariant), §10 (S1-S5 + EK KARAR 1-3).
- **PIVOT_ARCHITECTURE_AUDIT** — KOVA haritası, file:line, strangler sırası (Q5), composite yüzeyi (3 dosya), mevcut primitive'ler (§2.2.1), sessiz kırılma (§2.3, EK-5).
- **D-176** — trade dağılımı teşhisi (AMPİRİK): cash drag (avg_exposure %13), seçim çalışıyor (+5.3%/trade, win 58.7%, PF 2.19, payoff 1.63), runner reddedildi, skew +0.10, yfinance %67 reconciliation.
- **NRR-001** — tarama metodolojisi; ardışık-filtre+rank; RS-vs-XU100; look-ahead.
- **NRR-002** — benchmark (TLREF) + USD-bazlı value (F/DD + EV/EBITDA); S1+S4.
- **NRR-003** — validasyon eşikleri (4 gating + DSR supportive); az-örneklem; MinBTL; momentum riski; S2.

---

*SPEC_PIVOT_ARCHITECTURE_1 v1.0 — ARCHITECTURE v1.2 temelli. İlk build edilecek: Faz 0 Faktör IC Validasyon Harness'ı (§4). Faktör seçimi Faz 0 çıktısı belirler; tarama funnel'ı (Faz 1) ondan sonra. LLM (Faz B) ve KOVA 3 budama (Faz N) EN SON — çekirdek edge 4-gating'i geçtikten sonra.*
