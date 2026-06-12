# RR-Y1-016-G — Insider-disclosure ekseni konsolidasyonu (SAVE/WAIT, mezarlık-DEĞİL)

**Sınıf:** Negatif-bilgi konsolidasyonu (RR-Y1-015-tarzı). **Yeni-ölçüm YOK, motor-dokunmaz,
hipotez-açmaz** — yalnız mevcut 016-zincirini tek yere bağlar. **Etiket: `save/wait`,
X2-mühürlü — bu bir MEZARLIK (PERMANENT) kaydı DEĞİL.**

Registry kaydı: `data/registry/graveyard_registry.json` → `insider_disclosure_direction_intensity`
(`revival_status="save/wait"`). Provenance: **taze KAP scrape soyu (run-2, 2026-06-12), kanonik-panel-DEĞİL.**

---

## Hüküm-zinciri (tam — yanlış-hatırlamayı önlemek için)

> Bu zincir kritik: gelecek-session bunu "insider confound'du" ya da "insider'da edge vardı"
> diye **yanlış-hatırlamasın**. Gerçek hüküm aşağıdaki gibi gelişti ve bir kez **düzeltildi**.

1. **RR-Y1-016-C — buy-side edge-yok.** X1 look-half, market-relative (vs XU100), look-ahead-safe
   t+1 giriş. Trade-edilebilir BUY tarafında pozitif sürüklenme YOK (medyan 21g −2,15% / 42g −4,95%).
   SELL tarafı daha-negatif göründü (63g medyan −10,85%) — ama long-only/no-short → trade-edilemez.

2. **RR-Y1-016-D — "confound kesin" (← YANLIŞ).** Sell-negatifliği gerçek-mi confound-mu diye
   evren-içi + placebo kontrolü. Hüküm: (ii-a) evren/timing-confound. **Ama Katman-A baseline'ı
   "non-sell" = buy-flagged + kontrol idi; buy-flagged'in kendisi negatif-drift'liydi → kontamine
   baseline farkı null'a-çekti.** Hüküm baseline-seçiminden-etkilenmişti.

3. **Decision-audit (D5) yakaladı.** Kontamine-baseline major-bulgu olarak işaretlendi → düzeltme
   gerekti.

4. **RR-Y1-016-E — baseline-artefaktıydı; gerçek resim.** Temiz baseline (no-disclosure-kontrol-ONLY)
   ile yeniden: sell, temiz-baseline'dan size/likidite-ayarlı **anlamlı sapıyor** (21g p=0,045 /
   63g p=0,011) → confound-hükmü **CHALLENGED**. **Ama** pooled mean/median NS, bootstrap-CI'lar
   sıfırı-kesiyor (kırılgan), ve **Katman-B placebo hâlâ NS** → ayrışma **isim-seçilim** (sell-isimleri
   yapısal-zayıf-drift'li isimler), **event-bağlı-bilgi değil**. Buy-side (C3) temiz-baseline'da da
   düz → edge-siz. **Gerçek: buy-side-boş + sell-side-isim-seçilim (un-tradeable).**

5. **RR-Y1-016-F — cluster-yoğunluğu güç-yok.** Açık-kalan tek-meşru-soru (koordineli ≥N-insider
   alımı, Seyhun-tipi). **Getiriye BAKILMADAN** (DEC-053-güvenli) yalnız küme-dağılımı sayıldı:
   ≥3-insider koordineli küme **yalnız 2 isim** (ENKAI, MOGAN), ≥4 sıfır. Pre-frozen kural →
   **cluster-Stage-0 doğmadan-ölü.**

**NET: insider-disclosure ekseni üç-cephede-de boş → `save/wait` ile kapandı, X2 mühürlü.**

---

## Audit-değeri kaydı (DISC-10 canlı-doğrulama)

**D5 decision-audit, ilk kez KENDİ işimizde bir hükmü düzeltti** (016-D "confound kesin" →
016-E "baseline-artefaktı; gerçek mekanizma isim-seçilim"). Eksen-sonucu (trade-edilemez)
değişmedi ama **gerekçe düzeltildi.** Bu, measurement-verification / DISC-10 tezinin
**canlı-doğrulamasıdır**: yanlış-bir-hüküm konsolidasyondan-ÖNCE yakalanıp düzeltildi.
Makine-okunur kayıt: `graveyard_registry.json → decision_audit_log[D5]`.

**Ders:** confound-kontrollerinde baseline'ın **kontamine-olmaması** kritik; kirli-baseline gerçek
bir farkı null gösterebiliyor. Baseline'ı her zaman temiz (event-içermeyen) kur.

---

## Save/wait gerekçesi (neden PERMANENT değil)

- **Bu panel** X1-yarısı + 2025-2026 taze-scrape. **X2 lockbox mühürlü** (tek-atış saklı).
- Tam-panel (X2 + 2019-geri, ya da radar'ın zamanla biriktirdiği veri) ≥3-insider-küme kütlesini
  büyütebilir → gelecekte yeni-ön-kayıtlı bir Stage-0'ı yeniden-meşru-kılabilir.
- Yön alt-ekseni zayıf-önsel (buy-boş, sell-isim-seçilim); **cluster-intensity** tek yeniden-açma-adayı
  ve şu-an güç-ölü.
- Bu yüzden **mezarlık (PERMANENT) değil, `save/wait`** — bugünün-verisinde-kapalı, gelecekte-koşullu.

---

## Sıradaki-eksen: bugün-değil (dürüst boru-hattı durumu)

Yeni-eksen-zorlamak **DISC-1-yenilgisi** olur. Dürüst durum: yüksek-önselli-canlı-aday-yok —
PEAD mezar (RR-Y1-014 FAIL), insider save/wait (bu), H-B/H-C/sentiment düşük-prior, cluster-küme-yok.
Doğal-default açık-iplikleri-kapatmak (insider-kapanışı [bu doküman] + forward-defter-implement +
write-up + DSR-ops) — bunlar **yeni-hipotez-açmaz**. Ama o **ayrı-session-kararıdır**; bu doküman
yalnız insider-kapanışını bitirir.

---

**Kapsam-uyumu:** Yeni-ölçüm yok, motor-dokunulmadı, mezar-açılmadı/diriltilmedi, X2-dokunulmadı.
`save/wait` etiketi (PERMANENT-değil). Provenance taze-scrape-soyu (kanonik-panel-değil) olarak
korundu. Konsolidasyon = mevcut-FAIL/feasibility-bilgisini tek makine-okunur yere bağlama.
