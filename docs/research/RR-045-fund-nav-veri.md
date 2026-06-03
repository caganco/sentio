# RR-045 — FON-NAV-ARB Veri-Edinim FİZİBİLİTE (ETF/CEF iskonto, holding-DEĞİL)

**Tür:** ARAŞTIRMA / FİZİBİLİTE + veri-edinim-planı (ölçüm-DEĞİL, edge-test-DEĞİL).
**Tarih:** 3 Haziran 2026. **Builder/the maintainer.**
**Bağlam:** Yol-1 offline-paradigma-havuzu tükendi (cross-sectional hi52/lowvol63/value-regime +
event dividend/bonus + NAV-holding D-206 hepsi-SERAP). demo-goal-HANDOFF (FINDINGS.md): tek
deploy-edilebilir reel-getiri motoru = piyasanın kendisi (beta, alfa-değil). NAV-fund-arb
EN-YÜKSEK-ev olarak işaretlendi: dört-duvardan-kaçar — düşük-turnover + likit + long-only +
arbitraj-mekanizması-NET.

> **★ KRİTİK-AYRIM (directive):** D-206 = HOLDING-iskonto (KCHOL/SAHOL) **SERAP-oldu**. BU rapor =
> ETF/closed-end-FUND iskonto/prim — **FARKLI mekanizma**. Holding iskontosu yönetim/likidite/
> kontrol-primi-sürücülü ve gürültülü; kapalı-uçlu-fon iskontosu **saf-NAV-arbitraj** (CEF-literatür
> güçlü: Pontiff 1995, Lee-Shleifer-Thaler 1991). Holding-SERAP bunu yanlışlamaz; yeni-paradigma,
> meşru-yeni-test. **Bu rapor SADECE veri-fizibilitesi; ölçüm sonraki-adım (the project).**

---

## TL;DR — HÜKÜM

**NAV HAZIR-açıklanıyor (kompozisyon-hesabı GEREKMEZ) ama yalnız HAFTALIK + yayın-lag'li.** Tek
saf-CEF adayı = **MKYO** (Menkul Kıymet Yatırım Ortaklığı; sabit-pay, markete-edilebilir-portföy →
NAV günlük-değerlenebilir). FAKAT **N KÜçÜK (~9, XYORT)** — cross-sectional duvarı YENİDEN vurur.

| Soru | Cevap | Sonuç |
|---|---|---|
| **S1 EVREN** | Saf-CEF = MKYO **~9 firma** (XYORT). GYO(REIT) çok-ama stale-değerleme-NAV; GSYO illikit; BYF(ETF) yaratım/itfa→iskonto-DAR; TEFAS açık-uçlu = NAV'DAN-işlem→iskonto-YOK. | N=9 → **paradigma N-zayıf** (dürüst-uyarı) |
| **S2 NAV ERİŞİMİ** | MKYO net-aktif-değer + birim-pay-değeri **KAP'ta HAFTALIK** açıklanır (takip-eden-hafta-başı); günlük yalnız BİAŞ-ağırlıklı-fiyat > 2× birim-NAV ise (SPK). Kompozisyon-hesap GEREKMEZ. | **HAZIR-NAV ama HAFTALIK + lag** |
| **S3 TARİHSEL** | MKYO piyasa-fiyatı = BIST derin-günlük (3196 zaten elde). MKYO NAV-tarihçesi = KAP haftalık-bildirim-arşivi (yıllar-derinlik, HAFTALIK granül, parse-gerek). TEFAS TarihselVeriler 2010-01+ (ama açık-uçlu = iskonto-yok). | **Backtest MÜMKÜN, haftalık-çözünürlük + lag** |
| **S4 LİTERATÜR** | CEF-iskonto-MR ABD'de güçlü (Pontiff: %20-iskonto→+%6/12ay). BIST-MKYO = analog ama N=9; D-206-holding bağımsız. | **Mekanizma-net, evren-ince** |

**HÜKÜM = HAZIR-NAV (kompozisyon-hesap-DEĞİL) ama HAFTALIK + lag; backtest-edilebilir AMA N=9
binding-kısıt.** Tavsiye: KÜÇÜK historical+forward MKYO-haftalık-iskonto-MR fizibilite-okuması,
**N=9 baştan paradigma-zayıf-flag'li**. BYF-iskonto arb-için-çok-dar; TEFAS-açık-uçlu iskonto-yok.

---

## S1 — EVREN: BIST'te kaç tradeable+likit ETF/CEF/BYF?

Türkiye'de "fon" şemsiyesi dört ayrı mekanizmaya ayrılır; arbitraj-uygunluğu KESKİN-farklı:

| Tip | Ne | Pay-yapısı | NAV-niteliği | İskonto-arb? | N (yaklaşık) |
|---|---|---|---|---|---|
| **MKYO** (Menkul Kıym. Y.O.) | Markete-edilebilir-menkul-kıymet tutan kapalı-uçlu-ortaklık | **SABİT** (closed-end) | **Günlük-değerlenebilir** (portföy = likit-hisse/tahvil) | **★ EVET — ideal** | **~9 (XYORT)** |
| **GYO** (Gayrimenkul Y.O.) | REIT — gayrimenkul tutar | Sabit | **STALE** (ekspertiz-değerleme, yıllık/çeyreklik) | Hayır — değerleme-lag = TUZAK | ~30+ |
| **GSYO** (Girişim Serm. Y.O.) | VC-trust — özel-şirket | Sabit | STALE + illikit | Hayır | ~birkaç |
| **BYF** (Borsa Yat. Fonu / ETF) | Açık-uçlu, yaratım/itfa | **Değişken** | iNAV intraday (Borsa İst.) | Zayıf — arbitraj iskontoyu-DAR-tutar | ~20+ |
| **TEFAS açık-uçlu** | Yatırım-fonu (mutual) | Değişken | Günlük-NAV | **YOK — NAV'DAN-işlem** | yüzlerce (ilgisiz) |

**KRİTİK ayrım (directive'in S1-sorusu):**
- **CEF (closed-end, sabit-pay) iskonto-arb-için-İDEAL** çünkü pay-sayısı sabit → fiyat NAV'dan
  serbest-sapar → iskonto/prim oluşur ve mean-revert-edebilir. **BIST'te bunun karşılığı = MKYO.**
- **Açık-uçlu ETF (BYF) prim/iskonto-DAR** çünkü yetkili-katılımcı yaratım/itfa ile arbitrajı
  anında-kapatır. BIST-BYF'lerde iskonto genelde birkaç-bps; arb-edge-yok.
- **TEFAS açık-uçlu fonlar NAV'DAN işlem görür** → tanım-gereği iskonto-yok → bu-paradigma-dışı.

**MKYO evreni (XYORT, ~9 — 2014-2018 akademik + güncel XYORT örtüşür):** ATLAS, EUKYO (Euro Kapital),
EUYO (Euro Menkul), ETYAT (Euro Trend), GRNYO (Garanti), ISYAT (İş), MTRYO (Metro), OYAYO (Oyak),
VKFYO (Vakıf). **N≤~9; likidite değişken (bazıları ince-işlem).**

**Dürüst-uyarı (directive'in "N yine-az-mı"):** EVET. N=9 = cross-sectional-paradigmayı (D-205/
NRR-007/008) öldüren AYNI az-N-duvarı. Üstelik bugün-var-olan-MKYO = survivorship-seçimi.
**Bu, fon-arb paradigmasının en-zayıf-noktası ve baştan-beyan edilmeli.** Time-series-MR (her-MKYO
kendi-iskonto-tarihçesine-göre, D-206-mimarisi-gibi) az-N'i kısmen-aşar ama tamamen-değil.

## S2 — NAV ERİŞİMİ (en-kritik soru): hazır-mı yoksa kompozisyon-hesap-mı?

**Cevap: NAV HAZIR-açıklanır; kompozisyon-hesabı GEREKMEZ — AMA frekans HAFTALIK + yayın-lag.**

- **MKYO (saf-CEF aday):** SPK/KAP düzeni gereği MKYO **net-aktif-değer tablosunu + birim-pay-NAV'ı
  HAFTALIK** açıklar (genelde takip-eden-hafta-başı KAP bildirimi). **Günlük** NAV açıklama-zorunluğu
  yalnız BİAŞ-ağırlıklı-ortalama-fiyat birim-NAV'ın **2 katını aşarsa** doğar (SPK kuralı; prim-koruma).
  → **Kompozisyon-tek-tek-fiyatlama GEREKMEZ** (birim-NAV doğrudan-açıklanmış); bu D-206'nın
  istirak-mktcap-toplama yükünü ORTADAN-kaldırır. Bedeli: **çözünürlük HAFTALIK**, günlük-değil.
- **BYF (ETF):** iNAV (gösterge-NAV) Borsa İstanbul tarafından **intraday** yayınlanır → günlük/anlık
  ama iskonto-DAR (arb-edge-yok).
- **TEFAS açık-uçlu:** günlük-NAV var ama NAV'DAN-işlem → iskonto-yok (ilgisiz).
- **Borsa İstanbul iNAV:** BYF için var; MKYO için iNAV-feed standart-değil → MKYO'da KAP-haftalık-NAV ana-kaynak.

**Çıktı (directive):** MKYO için NAV **HAZIR** (kompozisyon-hesap-DEĞİL) ama **HAFTALIK + lag** →
look-ahead-safe kurgu HAFTALIK-NAV'ı yayın-tarihinden-SONRA kullanmalı (D-206 leg-bazlı-lag dersiyle
aynı disiplin). discount(t) = (birim-NAV(yayın<=t) - piyasa-fiyat(t)) / birim-NAV.

## S3 — TARİHSEL DERİNLİK: backtest-doğrudan-mı, forward-recorder-mı?

**Cevap: backtest MÜMKÜN (forward-only-DEĞİL), ama HAFTALIK-çözünürlük + yayın-lag ile.**

- **MKYO piyasa-fiyatı:** BIST günlük-tarihçe ZATEN-elde (3196 günsonu-fiyat/hacim paneli, 2009+).
  Ayrı-edinim GEREKMEZ.
- **MKYO NAV-tarihçesi:** KAP **haftalık net-aktif-değer bildirim arşivi** (yıllar-derinlik;
  RR-042'de KAP-bildirim-formlarının yapılandırılmış-olduğu doğrulandı). Granül = HAFTALIK;
  parse-gerek (KAP arşiv-tarama, tarih-filtresi-zayıf → RR-042'deki kör-pagination maliyeti riski).
- **TEFAS TarihselVeriler:** 2010-01'den günümüze günlük-fiyat (genel-bilgi + portföy-dağılımı).
  AMA bu açık-uçlu-fon-NAV'ı = iskonto-yok → **MKYO-arb-için kullanılamaz** (yalnız BYF-NAV-kontrolü
  veya portföy-benchmark için yardımcı olabilir). NOT: TEFAS-API alternatifi ~1.5y sığ; TarihselVeriler
  sayfası 2010+ derin.

**Look-ahead (directive):** NAV-açıklama-lag KESİN-modellenmeli — haftalık-NAV ancak KAP-yayın-tarihinden
sonra bilinir; t-anındaki-iskonto t-1-veya-önceki-yayınlanmış-NAV'a-göre. D-206 leg-bazlı-lag konvansiyonu
doğrudan-tekrar-kullanılır.

## S4 — LİTERATÜR + MEKANİZMA

- **CEF-iskonto mean-reversion (güçlü literatür):** Pontiff 1995 — geniş-iskontolu-CEF'ler sonraki-yılda
  daha-yüksek-getiri (~%20-iskonto → +%6/12ay anomalisi). Lee-Shleifer-Thaler 1991 — iskonto sentiment-
  sürücülü ve mean-revert-eder. Mekanizma: sabit-pay → fiyat NAV'dan-sapar → iskonto-genişken-AL,
  daralınca-NAV'a-yakınsa-SAT (long-only, düşük-turnover, yarı-ömür-aylar).
- **BIST-MKYO belgeli-mi?** Akademik-literatür-INCE: mevcut BIST-MKYO-çalışmaları çoğunlukla
  TOPSIS/PROMETHEE-sıralaması veya bilanço-rasyo-analizi (ör. dergipark çalışmaları) — saf-NAV-iskonto-MR
  zaman-serisi-testi belgeli-DEĞİL. → bu **test-edilmemiş-hipotez** (D-206-NAV-holding'le aynı durust-
  belirsizlik). BIST-MKYO iskontolarının-büyük + kalıcı-olduğu piyasa-folklorunda-bilinir ama
  arb-edilebilirlik (likidite/maliyet/lag-sonrası) ÖLÇÜLMEMİŞ.
- **Açık-uçlu-mu-CEF-mi-baskın?** BIST'te işlem-hacmi açık-uçlu-TEFAS + BYF'de yoğun; saf-CEF (MKYO)
  küçük-niş (XYORT ince). → arb-için-ideal-tip = az-sayıda-ve-ince-işlemli (S1-N-zayıflığını pekiştirir).
- **D-206 ile ilişki:** D-206-holding-iskonto SERAP'tı çünkü holding-iskontosu yönetim/kontrol-primi/
  istirak-likidite-sürücülü (saf-NAV-arb-DEĞİL) + within-beta-işareti-YANLIŞ. MKYO-iskontosu
  daha-saf-NAV-arb (portföy = markete-edilebilir-hisse, kontrol-primi-yok) → **bağımsız-test, SERAP-değil
  diye-iddia-EDİLMEZ ama mekanik-olarak-daha-temiz-aday.**

## Veri-edinim PLANI (the maintainer ne-açmalı) — boşa-veri-toplama-YOK (D-200 dersi)

Önce NE-gerektiği netleşti; minimal-edinim:

1. **MKYO piyasa-fiyatı:** EK-EDİNİM-YOK. 3196 günsonu-paneli (2009+) zaten-elde; XYORT-9-sembol filtrele.
2. **MKYO haftalık-NAV (TEK kritik-eksik):** KAP haftalık net-aktif-değer / birim-pay-değeri bildirimleri.
   - Kaynak: KAP fon-portföy / net-aktif-değer bildirim-arşivi (RR-042'deki MKK_VYK/KAP structured-form
     yolu; auth + IP-rate-limit dikkat). 9-sembol × haftalık × ~yıllar = ORTA-hacim.
   - the maintainer-aksiyonu: KAP-arşiv-erişimi (veya MKK_VYK CA-benzeri NAV-bildirim endpoint'i) + **açık
     istek-bütçesi** (RR-042 kör-pagination-maliyet-uyarısı geçerli). Pre-fetch ÖNCE küçük-prob
     (1-2 sembol, 1 yıl) ile parse-edilebilirlik + lag doğrulanır.
3. **TEFAS (opsiyonel, yardımcı):** TarihselVeriler 2010+ — yalnız BYF-iNAV-kontrolü / portföy-benchmark
   için; MKYO-arb-için DEĞİL.
4. **Makro (varsa-elde):** TÜFE-deflate (reel-getiri) + carry-kontrol için reel-TLREF — D-206-altyapısı zaten-var.

**AÇMA-SIRASI:** önce (2) küçük-prob ile NAV-parse + lag + haftalık-çözünürlük DOĞRULA → fizibil-ise
9-sembol tam-arşiv. (1)(3)(4) ek-açma-gerektirmez.

## Test-edilebilir-mi HÜKÜM

- **NAV-niteliği: HAZIR-NAV** (birim-NAV doğrudan-KAP'ta; kompozisyon-tek-tek-hesap GEREKMEZ).
  D-206'nın en-ağır-yükü (istirak-mktcap-toplama + unit-harmonization) burada YOK.
- **Frekans/lag: HAFTALIK + yayın-lag** (günlük-değil) → çözünürlük D-206'dan-kaba; gate-tasarımı
  haftalık-iskonto + lag-safe-olmalı.
- **Tarihsel: BACKTEST-EDİLEBİLİR** (forward-only-DEĞİL): fiyat-elde + NAV-KAP-arşivi yıllar-derinlik.
  Forward-recorder yalnız haftalık-arşiv-boşluğu-çıkarsa yedek.
- **Binding-kısıt: N=9 (survivorship-seçim)** → istatistik-güç + genelleme ZAYIF; cross-sectional-duvarı
  yeniden. Time-series-MR (per-MKYO, D-206-mimari) kısmen-aşar.

**Net hüküm:** fon-NAV-arb **fizibil ama-ZAYIF-evrenli**. Veri-tarafı çözülebilir (HAZIR-haftalık-NAV +
elde-fiyat + KAP-arşiv); paradigma-tarafı N=9 ile-kırılgan. **Dürüst: bu dört-duvardan-kaçma-adayı
likidite + long-only + düşük-turnover + net-mekanizma açısından-GEÇERLİ, ama az-N nedeniyle "yüksek-ev"
iddiası temkinli-okunmalı.** Fizibil-değil-DEĞİL; ama "kolay-kazanç" da-değil.

## Sonraki adım

1. **the maintainer-karar:** KAP haftalık-NAV küçük-probu (1-2 MKYO, 1 yıl) açılsın-mı → parse + lag + haftalık-
   çözünürlük + iskonto-büyüklüğü/kalıcılığı ön-bak. (boşa-toplama-yok; ÖNCE-prob).
2. Prob-OLUMLU-ise: D-206-mimarisini MKYO-haftalık-iskonto-MR'a-uyarla (Stage-0-dondur, time-series-gate,
   look-ahead-safe-haftalık-lag, LOHO, carry-trap, D-204-maliyet) — **AYRI ölçüm-adımı (the project), bu-rapor-DEĞİL.**
3. Prob-OLUMSUZ (NAV-arşiv-sığ/parse-imkansız/iskonto-yok): forward-recorder-only beyan VEYA paradigma-kapat.
4. **N<=3 kilidi + grid-yasak + measurement-only** kısıtları ölçüm-adımında geçerli; bu-rapor-yalnız-fizibilite.

---

**Dürüstlük-notu:** likit-saf-CEF (MKYO) az/ince → paradigma N-zayıf (açık-beyan). Tarihsel-NAV var
(KAP-haftalık-arşiv) → forward-only-değil ama haftalık-çözünürlük + lag açık-beyan. holding-D-206-SERAP
bu-fon-arb'ı yanlışlamaz (farklı, daha-saf-NAV-mekanizma). Fizibil-ama-zayıf-evrenli; ölçüm sonraki-adım.
