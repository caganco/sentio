# RR-Y1-019 — VBTS tedbir-olayı edge-adayı **Faz-1 fizibilite probu** (betimsel)

**Sınıf:** Veri-erişilebilirlik + evren-kesişim probu. **Stage-0-DEĞİL**, ölçüm-DEĞİL,
edge-iddiası-DEĞİL, hipotez-testi-DEĞİL. Hiçbir getiri/CAR/sinyal/backtest hesaplanmadı —
yalnız (a) olay-akışının erişilebilirliği, (b) evren-kesişiminin **ölçümü** (counts-only),
(c) negatif-görüş ifadesinin yapısal-fizibilitesi. Span **sonuca-bakılmadan ex-ante
donduruldu: 2024-06 → 2026-06 (son 24 ay, takvim-bazlı)**.

**Kapsam-ayrımı (ZORUNLU):** Go/no-go ve Stage-0 kararı bu rapora ait değildir —
maintainer'a aittir. Faz-2 (dual-layer ölçüm) yalnız *belirtilir*, KOŞULMAZ. Hiçbir frozen
pencere tüketilmedi. Tedbir tetik-eşiği (non-public) fiyattan geri-türetilmedi — ama tedbirin
**kendisi** (uygulanan kademe) günlük bültende açıkça yayımlanır: **olay = tedbir-durumu.**

**Aday (literatür-çıpalı, Autore vd.):** VBTS (Volatilite Bazlı Tedbir Sistemi) anormal
fiyat/hacim gösteren paylara 1 ay süreyle kademeli tedbir uygular — (1) Açığa Satış & Kredili
İşlem Yasağı → (2) Brüt Takas → (3) Emir Paketi → (4) Tek Fiyat Yöntemi → (5) Emir İletim
Kanalı Kısıtı; her alt-kademe üst-kademe uygulanırken sürer. Mekanizma: kaldıraç-ve-netleşme
yakıtıyla yukarı-itilen paylar, yakıt mekanik-çekilince (brüt takas aynı-gün-netleşmeyi,
marj-yasağı kaldıracı kaldırır) geri-döner. Karşı-taraf: de-leverage'a zorlanan perakende
momentum/pump kalabalığı.

> **Düzeltme notu (v2).** Bu raporun ilk hâli olay-akışını "erişilemez (DATA-INFEASIBLE)"
> bulmuştu; bu YANLIŞTI ve bu sürümle düzeltildi. VBTS tedbir-durumu, Borsa İstanbul'un
> **public, auth-suz, makine-okunur günlük bülteni** (`thm`) içinde doğrudan yayımlanıyor;
> 24-aylık panel başarıyla kuruldu ve evren-kesişimi **ölçüldü** (aşağıda). Hüküm
> **UNIVERSE-DISJOINT (ölçülmüş)**'e güncellendi.

---

## A. Veri kaynağı ve envanter

### A.1 — VBTS tedbir-durumu — **VAR (public günlük bülten)**
Repo-içi: olay-akışı repo'da tutulmuyor (`kap_parser.py` `EventCategory`'de tedbir-sınıfı yok;
`flow_intel` insider-only; datastore `short_selling` pozisyon-verisi, tedbir-durumu değil).
**Public kaynak (yeni-edinim, read-only, auth-suz):** Borsa İstanbul **Pay Piyasası Günlük
Bülteni — `thm` dosyası** (`borsaistanbul.com/data/thm/{YYYY}/{AA}/thm{YYYYAAGG}{seans}.zip`,
açık ZIP→CSV, ISO-8859-9). Her `.E` pay için günlük işlem-kuralı durumu, tedbir kademelerini
**doğrudan** kodlar:

| Bülten kolonu | Değer | VBTS kademe eşlemesi |
|---|---|---|
| `BRUT TAKAS` | `1` | Kademe-2 (brüt takas) |
| `MAKSIMUM EMIR DEGERI(TL)` | ≤ 1.000.000 TL (proxy) | Kademe-3 (emir paketi) |
| `ISLEM YONTEMI` | `TF` | Kademe-4 (tek fiyat yöntemi) |
| `ACIGA SATIS` | `0` | Kademe-1 (açığa satış yasağı) — **piyasa-geneli yasakla maskeli** |

**Olay** = ardışık işlem-günleri arası **yukarı geçiş** (state transition). KAP'a gerek YOK,
auth YOK, paywall YOK.

### A.2 — Kesişim paydası (iki liste) — **HAZIR**
- Survivorship-clean panel: `data/clean_universe/adjusted_prices_2019_2026.parquet`
  (681 sembol, 2019-01-02 → 2026-05-26; `bist30`/`bist100` PIT-flag).
- PIT üyelik: `data/clean_universe/pit_membership_2019_2026.parquet` (günlük, → 2026-05-26).
- Investable liste (statik): `config.yaml → portfolio.tickers` = **57 isim**
  (satır-içi "58" yorumu bayat). BIST30 + seçili BIST100.

### A.3 — Pipeline (counts-only, getiri-YOK)
- `scripts/probe/rr_y1_019_vbts_bulletin_build.py` — public `thm` bültenlerini indirir
  (yerel cache; **ham CSV commit-EDİLMEZ**), `.E` pay tedbir-durumunu çıkarır, ardışık-gün
  geçişlerinden olay + tedbir-popülasyonu üretir.
- `scripts/probe/rr_y1_019_vbts_universe_intersection.py` — olay-tablosunu **PIT üyelik
  olay-tarihine-göre** (look-ahead-safe, bugünkü üyeliğe-DEĞİL) join'ler; counts-only kesişim.
  Getiri/CAR/fiyat-tepkisi **okunmaz** (Faz-2).

---

## B. Online erişim haritası (READ-ONLY; auth/satın-alma YOK; 2026-06-13)

| Yol | Sonuç |
|---|---|
| **Borsa İstanbul Günlük Bülten `thm`** (`/data/thm/...zip`) | ✅ **public, auth-suz, makine-okunur** — kullanılan kaynak |
| KAP public disclosure API (`www.kap.org.tr/tr/api/search/*`, `home-data/*`) | ✅ auth-suz erişilebilir, ama VBTS **KAP konu-taksonomisinde YOK** (181 konu; yalnız "SPK Tedbir Kararı" + "Yatırımcı Bazında Tedbir" — VBTS değil) |
| KAP legacy `memberDisclosureQuery` | ReadTimeout (emekli endpoint) — kullanılmadı, gereksiz |
| Üçüncü-taraf agregatör data endpoint | 401 (kendi-hesap-auth'u gerekir) — kullanılmadı |
| Geçmişe-dönük ücretli tedbir arşivi | ücretli — gereksiz (public bülten yeterli) |

**Düzeltme:** İlk-sürümdeki "KAP duvarlı → DATA-INFEASIBLE" sonucu, *yanlış (legacy/iç)
endpoint'lere* çarpmaktan kaynaklanıyordu. KAP public API aslında auth-suz erişilebilir; ama
VBTS oraya değil **Borsa İstanbul günlük bültenine** ait. Doğru public kaynak bulununca panel
sorunsuz kuruldu. Hiçbir auth bypass / paywall-aşımı / hack kullanılmadı — yalnız public bülten.

---

## C. Step-bazlı bulgular (hüküm-değil — olgu)

**Step-1 (veri-fizibilitesi) — ÇÖZÜLDÜ.** Frozen span 2024-06-01 → 2026-06-12: **506 işlem-günü**
`thm` bülteni indirildi/parse edildi. Çıkarım: **165 tedbir-giriş olayı** (ardışık-gün yukarı
geçiş): Kademe-2=59, Kademe-3=71, Kademe-4=35; **136 distinct olay-ismi**. Ayrıca **376 distinct
isim** span boyunca tedbir altına girdi (max-kademe: K2=25, K3=276, K4=75). Span sonuç-bağımlı
hiç-tüketilmedi; coverage-kenarı: PIT üyelik 2026-05-26'da biter (son ~2 hafta üyelik-flag'siz).

**Step-2 (evren-kesişimi — *karar-verici*) — ÖLÇÜLDÜ.** PIT üyelik **olay-tarihine-göre**
join'lendi (look-ahead-safe). Sonuç:

| Sınıf | Giriş-olayları (165) | Tedbir-popülasyonu (376) |
|---|---|---|
| **Investable-57 isabet** | **0** | **3** (K3×2, K4×1) |
| BIST30 | 0 | 0 |
| BIST100-ex30 | 1 | 1 |
| Panelde, endeks-dışı (mikro-kap) | 164 | 322 (+53 PIT-flag-yok = çok-küçük) |

**Açık yorum:** 165 tedbir-girişinin **0'ı** investable listeye, **0'ı** BIST30'a değiyor
(1 tanesi BIST100-ex30). 376 tedbir-isminden yalnız **~3'ü** (≈%0,8) investable. VBTS neredeyse
tümüyle **endeks-dışı mikro-kap havuzunda** yaşıyor; held/investable evrenden **ayrık**. →
held-evren üzerinde long-only avoid/exit ekranı **neredeyse boş** (~%0,8 dokunma-oranı).

**Step-3 (tradability — negatif-görüş mümkün mü).** Yerleşik düzenleyici olgulardan tam
değerlendirilir (yeni-ölçüm değil):
- Açığa satış perakende için fiilen kapalı (piyasa-geneli yasak Şub-2023→Oca-2025 tam;
  BIST-50 istisnası Oca-2025; Mar-2025 yeniden-sıkı; repo `RR-Y1.md` teyit). Bülten de doğrular:
  2026-06-12'de **611 payın 611'i `ACIGA SATIS=0`**.
- VBTS Kademe-1'in kendisi tedbir-isimlerinde açığa-satışı yasaklar → en-güçlü adayların
  *üstünde* short yapısal-imkansız.
- SSF/warrant rotası yok: tedbir-isimleri düşük-likidite mikro-kap; SSF/warrant genelde yok.
- Brüt takas: tedbirli isme long-girişte T+2 ön-finanse nakit zorunluluğu.
- **Hüküm:** Negatif-görüş ifadesi **yapısal olarak kapalı** → aday inşa-gereği **long-only
  avoid/exit ekranı**. (Yumuşatılmadı.)

**Step-4 (Faz-2 çerçevesi — *belirtildi, KOŞULMADI, hiçbir-şey DONDURULMADI*).** Onaylanırsa:
- **Realistic katman (verdict):** tam maliyet+slippage+spread+brüt-takas + sonraki-seans-açılış
  zamanlaması; **long-only**. (Held-evren-kesişimi ≈0 olduğu için bu katman pratikte boş.)
- **Ideal/frictionless katman (concept-ledger, ASLA-verdict):** maliyet=slippage=spread=0, AMA
  look-ahead-safe + survivorship-clean + t→t+1 korunur (zaman-oku gevşetilmez). Mikro-kap
  376-isim popülasyonunda "olgu gerçek mi / temiz yönsel-sinyal var mı"yı tradability'den
  bağımsız yanıtlar.
- Olay-çalışması: tedbir-girişi etrafında CAR, temiz TR-endeksine-göre, **tedbir-seviyesi
  kesit**. Keep-bar + embargo/holdout Stage-0-öncesi belirlenir.
- **Eşleme:** güçlü ideal-katman sinyali + ölümcül tradability-duvarı → **save/wait +
  concept-ledger**, mezarlık-DEĞİL.

---

## D. Karar-kapısı (probun yegâne çıktısı) — üç-dal

- **DATA-INFEASIBLE:** panel kurulamaz → save/wait. *(Geçerli-değil: panel kuruldu.)*
- **UNIVERSE-DISJOINT + ideal-katman-ilgisi-yok:** olaylar held-evrene değmez → save/wait.
- **PHENOMENON-MEASURABLE:** temiz panel var + Faz-2 etkiyi yanıtlayabilir → Faz-2-öner.

### Gözlenen-duruma göre hüküm: **🟡 UNIVERSE-DISJOINT (ölçülmüş) → save/wait**

Panel public bültenden **kuruldu** (506 gün, 165 olay, 376 isim); kesişim **ölçüldü**:
held/investable evrene dokunma ≈%0 (0/165 olay, 3/376 isim; BIST30=0). Dolayısıyla:
- **held portföy için long-only avoid/exit ekranı neredeyse-boş** — realistic katman pratikte
  vacuous. Bu *ölçülmüş* bir olgu, varsayım değil.
- **save/wait (mezarlık-DEĞİL):** hiçbir frozen-Stage-0 koşulmadı, getiri ölçülmedi, X₂
  açılmadı. Negatif olan *edge* değil, *held-evren-kesişimi*. Olgu (tedbir→reversiyon) mikro-kap
  havuzunda mevcut-olabilir ve **ölçülebilir** — ama trade-edilebilirlik yapısal-kapalı
  (short yok + mikro-kap likidite). → save/wait + concept-ledger.
- **Faz-2'nin yegâne meşru-değeri ideal-katman olgu-kataloğu** (mikro-kap 376-isim üzerinde,
  yön gerçek mi); held-portföy P&L'ine etkisi ≈0. Bu ayrı, soğuk bir maintainer kararı.

---

## Caveat'lar
- **Yalnız fizibilite + kesişim-sayımı — getiri/CAR/fiyat-tepkisi ÖLÇÜLMEDİ** (Faz-2).
- **Ham bülten artefaktı commit-EDİLMEDİ** (yerel cache `data/probe/_vbts_cache/` + ara
  parquet'ler `.gitignore`'da); yalnız counts-only sonuç (`rr_y1_019_vbts_intersection_result.json`)
  + script + bu rapor kalıcıdır.
- **Kademe eşlemesi yaklaşık:** K2=brüt-takas (kesin), K4=tek-fiyat=TF (kesin), K3=emir-paketi
  (max-emir-değeri ≤1M TL **proxy**, gürültülü-olabilir), K1=açığa-satış (piyasa-geneli yasakla
  maskeli, ayrışmıyor), K5=kanal-kısıtı (bu dosyada yok). Faz-2'de incelenir. Kesişim-hükmü
  (disjoint) tüm kademelerde sağlam — gürültü hükmü değiştirmez.
- Brüt-takas bazı pazarlarda (Yakın İzleme vb.) **kalıcı segment-kuralı** olabilir; geçiş-bazlı
  tanım çoğunu doğal-dışlar (`pazar` alanı kaydedilir).
- Kesişim paydası **bugünkü statik investable liste** (57); span-içi üyelik-değişimi
  modellenmedi — dürüstlük-kaydı.
- PIT üyelik 2026-05-26'da biter (53 popülasyon-ismi `in_panel_no_pit`); BIST50 PIT-panelde yok.
- Erişim read-only/public/auth-suz; hiçbir auth-bypass/paywall-aşımı kullanılmadı.

Pipeline: [`scripts/probe/rr_y1_019_vbts_bulletin_build.py`](../../scripts/probe/rr_y1_019_vbts_bulletin_build.py) +
[`scripts/probe/rr_y1_019_vbts_universe_intersection.py`](../../scripts/probe/rr_y1_019_vbts_universe_intersection.py);
sonuç: [`data/probe/rr_y1_019_vbts_intersection_result.json`](../../data/probe/rr_y1_019_vbts_intersection_result.json).
