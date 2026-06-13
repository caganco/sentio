# RR-Y1-021 — Akım-Kaynaklı Baskı (FDP) — Faz-1b AYLIK-çözünürlük İNŞA-EDİLEBİLİRLİK probu

**Sınıf:** İnşa-edilebilirlik (constructibility) / veri-fizibilite probu. **Stage-0-DEĞİL**,
ölçüm-DEĞİL, edge-iddiası-DEĞİL. Hiçbir getiri / CAR / forward-return hesaplanmadı; hiçbir
dondurulmuş pencere tüketilmedi. Tek çıktı: **aylık** FDP faktörünün KAP fon portföy-dağılım
raporlarından inşa-edilip-edilemeyeceğine dair üç-dallı fizibilite hükmü. **Go/no-go kararı
maintainer'a aittir.** RR-Y1-020 prob şablonuyla aynı; FDP'nin günlük (RR-Y1-020) değil
**aylık-çözünürlük varyantı** — yeni eksen değil, aynı şemanın çözünürlük-türevi.

**Faz-1b yeniden-açma premisi (test edildi, yeniden-türetilmedi):** Faz-1 (günlük FDP)
save/wait kapandı çünkü günlük pay-sayısı tarihçesi tüm-ücretsiz-yollardan kalktı. Premis:
fon **Portföy Dağılım Raporu**'nun KAP'a ay-sonundan ~6 gün içinde, **per-stock holdings +
katılma payı hareketleri (unit creation/redemption)** içerecek şekilde, makine-okunur
filing'lendiği; KAP zaten repo-içi PIT-damgalı kaynak olduğundan aylık FDP'nin KAP-tek-başına
kurulabileceği. Aylık çözünürlük tezi-bozmaz — Coval-Stafford tersine-dönüşü 1-3 ayda oynar.

> **Faktör (aylık):** FDP_i,month = Σ_f [ Flow_f,month × w_{f,i,month-1} ];
> Flow_f,month = aylık net yaratım/itfa × NAV; w_{f,i,month-1} = önceki-ayın raporundaki
> per-stock ağırlık (gecikmeli, akım-öncesi).

---

## TL;DR — HÜKÜM

**🟡 PARSE-INFEASIBLE (premis-edilen KAP aylık raporu MEVCUT-DEĞİL) → save/wait** (mezarlık-DEĞİL).

**Canlı-ölçüm premisi yanlışladı:** premis-edilen makine-okunur aylık per-stock "Portföy Dağılım
Raporu" **bir KAP bildirimi DEĞİLDİR.** (VBTS dersiyle aynı kalıp: görev KAP'ı kaynak-varsaydı,
veri varsayımı bozdu.) Fonlar KAP'a **kurucu (portföy yönetim şirketi)** üzerinden eşlenir;
kurucunun bildirim-akışı tamamen-erişilebilir ama yalnız **kurumsal** filing taşır (genel
açıklama, şirket bilgi formu, sorumlu-yönetim, yönetim-şirketinin kendi finansal/faaliyet
raporu). **İki bağımsız kurucuda (İş Portföy 79 bildirim, Inveo Portföy 51) → 0 portföy-dağılım
raporu, 0 per-stock holdings, 0 birim-hareketi (katılma payı) bildirimi.**

| Girdi | Bulgu (canlı-ölçülmüş) | Sonuç |
|---|---|---|
| **Per-stock aylık ağırlık** (w_{f,i}) | KAP'ta per-fund portföy-dağılım raporu **yok** (yalnız kurumsal-filing). Per-stock portföy yalnız **TEFAS**'ta (fon-detaylı-analiz), Akamai/Playwright-kapılı (Faz-1). MKK `fonbilgilendirme.com` **DNS çözülmüyor**. | denominatör **ücretsiz-yapısal-yolda yok** |
| **Aylık net yaratım/itfa** (numeratör) | KAP-filing yok; TEFAS yalnız **anlık** size-snapshot (tarihçe-yok); günlük pay-sayısı 2026-04'te emekli (Faz-1). | numeratör **ücretsiz-yolda yok** |

**Kesişim (Step-3) bağlayıcı-kısıt DEĞİL:** evren NON-DISJOINT (Faz-1: 190 YAT + 41 EMK
hisse-fonu + karma-fonlar BIST büyük-kapları tutar). Adayı öldüren ayrıklık değil; premis-edilen
**veri-kaynağının var-olmaması.**

**Mezarlık-değil gerekçesi:** olgu/literatür sağlam; per-stock portföy-verisi **var** ama yalnız
TEFAS-tarayıcı-kapısının ardında. Kavranabilir tek-yol = **Playwright tabanlı forward-recorder**
(ileriye-doğru aylık snapshot biriktirme) — geçmiş-backtest değil. Bu, ücretsiz-read-only-plain-
HTTP kapsamı dışında (ağır-bağımlılık; görev "do NOT install heavy deps to force it" der).

---

## A. KAP fon portföy raporu erişimi (STEP 1 — belirleyici soru)

### A.1 — Erişim zinciri (READ-ONLY, canlı-ölçüldü; auth/satın-alma YOK)

| Rota | Sonuç (canlı) |
|---|---|
| TEFAS `fonProfilBilgiGetir` → `kapLink` | **200** — fon-kodunu KAP kurucu-sayfasına eşler (`/tr/fon-bilgileri/genel/<slug>`); WAF-arama gerekmez |
| KAP fon-sayfası `/tr/fon-bilgileri/genel/<slug>` (SSR) | **200** — kurucu `mkkMemberOid` + `fundCode` + `kapMemberTypes [FK, PYS]` gömülü |
| KAP kurucu bildirim-akışı `/tr/bildirim-sorgu-sonuc?member=<oid>` (SSR) | **200, erişilebilir** — ama yalnız **kurumsal** bildirim; **portföy-dağılım raporu YOK** |
| KAP `api/search/combined` + `api/disclosure/list/main` | **666 / 500** — WAF otomatik-erişime kapalı (rapor zaten KAP'ta-olmadığından önemsiz) |

### A.2 — Bulgu (parse-feasibility kararı)

Premis-edilen rapor **KAP'ta bir bildirim olarak yoktur.** İki kurucuda doğrulandı:
- **İş Portföy** (OID `4028e4a1…2b9f`, fundCode TTE): 79 bildirim → en-çok "Genel Açıklama" (34),
  "Şirket Genel Bilgi Formu" (15), "Sorumlu Yönetim İlkeleri" (15), "Finansal Rapor" (4),
  "Faaliyet Raporu" (4). **Portföy-dağılım: 0.**
- **Inveo Portföy** (OID `4028e4a2…075e`, fundCode GAF): 51 bildirim → "Şirket Genel Bilgi Formu",
  "Finansal Rapor", "Sorumluluk Beyanı", "Faaliyet Raporu", "Özel Durum Açıklaması". **Portföy-
  dağılım: 0.**

Kurucu KAP'ta yalnız **kurumsal** (yönetim-şirketi-seviyesi) bilgi açıklar; **per-fund per-stock
aylık portföy + birim-hareketi açıklamaz.** Kısmî-yedek: kurucu çeyreklik/altı-aylık "Finansal
Rapor"/"Faaliyet Raporu" filing'i portföy-tablosu *içerebilir* — ama (a) **çeyreklik/altı-aylık,
aylık-değil**, (b) PDF/heterojen-format, (c) yönetim-şirketi-raporu (temiz per-fund per-stock
garanti-değil). Premis-edilen **aylık** çözünürlüğü karşılamaz.

---

## B. Numeratör inşa-edilebilirliği (mekanik aylık akım) — STEP 2

Aylık net yaratım/itfa: KAP-filing **yok**. TEFAS `fonBilgiGetir` yalnız **anlık** size verir
(tarihçe-yok); günlük pay-sayısı tarihçesi 2026-04 migrasyonunda emekli (Faz-1, RR-Y1-020).
Ardışık-aylık raporlardan ay-sonu pay-sayısı türetme yolu da **rapor-yok** olduğundan kapalı.
→ mekanik (birim-sayısı) bileşeni NAV/getiri-bileşeninden ücretsiz-yolda **ayrıştırılamaz**
(forced-vs-informed ayrım sağlaması aylık-resolüsyonda da yapılamaz).

---

## C. Denominatör & lag yapısı — STEP 3

w_{f,i,month-1} (önceki-ay ağırlık): kaynağı yalnız **TEFAS fon-detaylı-analiz** (Akamai/
Playwright-kapılı, Faz-1; v2'de per-stock JSON yok). 1-aylık lag (rapor ay-sonu+6gün)
kavramsal-olarak uygun ama **veri ücretsiz-yapısal-yolda alınamaz**. Evren-eşleme: temiz
survivorship-panel (681 isim) + 57-investable ile **NON-DISJOINT** yeniden-teyit (hisse-fonları
BIST büyük-kaplarına biner); ayrıklık bağlayıcı-kısıt değil. Prob-script bir per-stock aylık
snapshot verildiği an kesişim-sayar (yalnız sayım, getiri-yok).

---

## D. İnşa-edilebilirlik özeti — STEP 4

**FDP_i,month = aylık mekanik akım × gecikmeli aylık holding, temiz-evrene eşlenmiş.**

- **(KAP-tek-başına, premis) → İNŞA-EDİLEMEZ.** Premis-edilen aylık portföy-dağılım raporu KAP'ta
  bir bildirim değil; her-iki-leg (numeratör + per-stock denominatör) ücretsiz-yapısal-KAP-yolunda
  yok.
- **(TEFAS browser, forward) → KAVRANABİLİR-AMA-KAPSAM-DIŞI.** Per-stock portföy TEFAS'ta var ama
  Akamai/Playwright-kapılı → ancak ileriye-doğru aylık-snapshot biriktiren bir forward-recorder
  (ağır-bağımlılık) kurabilir; geçmiş-backtest **sağlamaz**. Read-only-plain-HTTP kapsamı dışında.
- **Sınırlayıcı faktör:** premis-edilen makine-okunur ücretsiz aylık kaynağın **var-olmaması**
  (KAP-rapor-yok + TEFAS-browser-kapı + MKK-domain-çözülmez).

**Phase-2'nin zorunlu kontrolleri (faktör-getiri ilişkisi BURADA hesaplanmadı):** hisse-kendi-
getirisi, fon-kendi-getirisi, orantılı-ticaret varsayımı, fon-evreni survivorship'i.

---

## E. Phase-2 çerçevesi (yalnız-belirt, HİÇBİR-ŞEY-DONDURMA/ÇALIŞTIRMA) — STEP 5

**Çift-katman tasarım:**
- **Gerçekçi-hüküm katmanı:** tam maliyet/slippage/spread + sonraki-dönem zamanlaması, **long-only**.
- **İdeal frictionless concept-ledger:** cost=slippage=spread=0 ama look-ahead-safe, survivorship-
  clean, **t→t+1 korunur** (zaman-oku asla gevşetilmez; asla bir-hüküm değil).

**Kesit yapısı:** FDP-tersil bazında **aylık** forward-return (aşırı-negatif-FDP → reversal;
aşırı-pozitif → momentum), **temiz TR-index**'e karşı. Keep-bar adayları; embargo/holdout. **Güçlü
ideal-katman + ölümcül veri-duvarı → save/wait + concept-ledger, mezarlık-DEĞİL.**

---

## F. Karar-kapısı (tek çıktı) — STEP 6

- **CONSTRUCTIBLE → Phase-2 öner.** — ❌ değil.
- **🟡 PARSE-INFEASIBLE / COVERAGE-TOO-SHALLOW → save/wait.** — ✅ **HÜKÜM.** Premis-edilen
  KAP aylık portföy-dağılım raporu mevcut-değil; her-iki-leg ücretsiz-yapısal-yolda yok. Tek-yol =
  TEFAS-browser forward-recorder (ağır-bağımlılık, kapsam-dışı) veya çeyreklik finansal-rapor PDF
  parse (aylık-değil, heterojen). **Mezarlık-değil** (olgu/literatür sağlam; veri-var ama browser-
  kapılı).
- **UNIVERSE-DISJOINT → save/wait.** — ❌ değil (evren NON-DISJOINT).

---

## Caveat'lar
- **Yalnız inşa-edilebilirlik** — getiri/sinyal/edge ölçülmedi (kapsam-dışı, DEC-053-safe).
- Online araştırma READ-ONLY: hesap-açma/satın-alma/auth/CAPTCHA/WAF-bypass **YOK**. WAF/Akamai/
  DNS bulguları olduğu-gibi rapor edildi, bypass denenmedi; ağır-bağımlılık (Playwright)
  premis-i-zorlamak için kurulmadı (görev-kısıtı).
- KAP/TEFAS erişim-olguları **canlı-ölçüldü** (2026-06, plain httpx + Chrome-UA). KAP yapılandırılmış
  API'si (`api/search/combined`, `api/disclosure/list/main`) WAF-666/500; SSR-sayfaları erişilebilir
  ama portföy-dağılım raporu içermiyor. İki kurucuda teyit.
- Ham çekilen-JSON/HTML **repoya commit-EDİLMEDİ** (forward-recorder/flow_intel emsali); yalnız
  sayım-türevi + script + bu RR-doc kalıcıdır.
- Evren-kesişimi per-stock **ölçülmedi** (browser-kapılı); NON-DISJOINT yapısal-rapor edildi.
- Investable-payda = bugünkü statik `config.yaml` listesi; span-içi-değişim modellenmedi.
- Go/no-go **maintainer kararıdır**; bu rapor olgu-sağlar, hüküm-vermez.

Kaynaklar (online, read-only): TEFAS `fonProfilBilgiGetir` (kapLink eşleme) · KAP
`/tr/fon-bilgileri/genel/<slug>` + `/tr/bildirim-sorgu-sonuc?member=<oid>` (SSR, kurumsal-only) ·
TEFAS `fon-detayli-analiz` (per-stock, Akamai-gated) · Coval & Stafford (2007) "Asset Fire Sales
(and Purchases) in Equity Markets" · Gabaix & Koijen (2021) "Inelastic Markets Hypothesis".
