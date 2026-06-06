# RR-046 — PEAD + MAKRO-EVENT Veri-Edinim FİZİBİLİTE (Yön-A, AŞAMA-1)

**Tür:** VERİ-FİZİBİLİTE-PROB (edge-test-DEĞİL, ölçüm-DEĞİL, Stage-0-gerekmez).
**Tarih:** 3 Haziran 2026. **arastirma katmani/maintainer.**
**Bağlam:** Yol-1 offline-paradigma-havuzu (cross-sectional hi52/lowvol63/value-regime + event
dividend/bonus + NAV-holding D-206 + NAV-fund RR-045/NRR-009) HEPSİ-SERAP. Yeni-yön: **olay-güdümlü**
anomali = PEAD (Post-Earnings-Announcement-Drift) — kesitsel-duvardan kaçar (event-driven). İkincil:
makro-event (TÜİK-TÜFE + TCMB-PPK takvimi) drift/sürpriz. Bu rapor SADECE **veri-edinim
fizibilitesi**; edge-test (PEAD/makro ölçümü) AYRI sonraki D-XXX.

> **★ KRİTİK-AYRIM (directive):** PEAD edge-prior **GÜÇLÜ** (global en-sağlam anomali; Ball-Brown
> 1968, Bernard-Thomas 1989). AMA bu rapor edge'i ÖLÇMEZ — yalnız "veri çekilebilir-mi" sorusunu
> yanıtlar. BIST maliyet/turnover-duvarı edge-test'te (sonraki-adım) sınanır. Makro-event edge-prior
> ZAYIF (zaten-fiyatlı beklenti) — yine de veri-ucuz, takvim kayıt-altına-alınır.

---

## TL;DR — HÜKÜM

**ÇEKİLEBİLİR — iki-katmanlı.** PEAD'in kritik-eksik-parçası kazanç-açıklama-TARİHİ; iki bağımsız
kaynaktan elde edilir. SUE-sürprizi degoran net_profit'ten ZATEN-hesaplanabilir (konsensüs
GEREKMEZ). Makro-takvim public + ucuz. **Tavsiye: AŞAMA-2 = degoran-ay-proxy GENİŞ/DERİN (2009+) +
sınırlı-bütçe KAP-tam-gün rafinasyonu (2019+ alt-küme).**

| Soru | Cevap | Sonuç |
|---|---|---|
| **Q1 SUE-SÜRPRİZ** | SUE = (net_profit[t] − net_profit[t−4ç]) / std. degoran net_profit ZATEN-elde (2009+). Konsensüs/analist GEREKMEZ (seasonal-random-walk; retail-uygun). **UYARI:** net_profit YIL-İÇİ-KÜMÜLATİF → de-kümüle gerek (Ç_t = YTD_t − YTD_{t−1}). | **HESAPLANABİLİR (lokal, bedava)** |
| **Q2 AÇIKLAMA-TARİHİ (tam-gün)** | KAP MKK-VYK `disclosureDetail.time` = gerçek-açıklama-zamanı, temiz/parse-edilir, look-ahead-safe (kapanış-sonrası → t+1). **KANIT:** THYAO 2022-Yıllık → time='01.03.2023 18:22:22'. **Derinlik ~2019+** (KAP-4.0 cutoff, index<538004 = html-only). **Maliyet = pagination + detay-çağrı/dosya = RR-042-tuzağı** tam-ölçekte (~bin-mertebe çağrı @1/sn). | **ÇEKİLEBİLİR ama BÜTÇELİ (2019+)** |
| **Q3 AÇIKLAMA-TARİHİ (ay-proxy, BEDAVA)** | degoran net_profit YTD-kümülatif + rapor-arası DÜZ-taşınır → **adım-değiştiği ay ≈ rapor-yayın-ayı**. Ay-çözünürlük, 2009+, parse-gerek-YOK (panel zaten-elde). **KANIT:** THYAO Ç2-adımı 2023-08, Ç3 2023-11, Yıllık 2023-03. | **BEDAVA + DERİN (2009+), ay-çözünürlük** |
| **Q4 MAKRO-TAKVİM** | TÜİK-TÜFE: Ulusal Veri Yayımlama Takvimi (yıllık, ayın ~3'ü 10:00). TCMB-PPK: yıl-sayfaları + EVDS; lokal-DB'de YALNIZ 2 satır (2026-04/05, tarihçe-YOK). Düşük-hacim, düşük-risk. | **PUBLIC + UCUZ, lokal-değil (çekilir)** |

**HÜKÜM = ÇEKİLEBİLİR.** PEAD-tarihi iki-katman: (1) **BEDAVA degoran-ay-proxy 2009+** (geniş panel,
ay-çözünürlük, doğrulandı); (2) **KAP-tam-gün 2019+** (gün-çözünürlük, look-ahead-safe, ama
sınırlı-bütçe-çekim — RR-042 kör-pagination-tuzağı). SUE lokal-hesaplanır (de-kümüle-şart). Makro
takvim public/ucuz. **AŞAMA-2-onayı maintainer'a kalır (aşağıdaki PAUSE).**

---

## Q1 — SUE-SÜRPRİZ: konsensüs olmadan hesaplanabilir mi?

PEAD iki-parça: **(a) sürpriz** (beklenmeyen-kazanç) + **(b) drift-penceresi** (açıklama-sonrası
yönlü-sürüklenme). Sürpriz için iki-yol:

1. **Analist-konsensüs sürprizi** (I/B/E/S tarzı): BIST-retail için **YOK/pahalı** — eleme.
2. **SUE / seasonal-random-walk** (Foster-Olsen-Shevlin 1984): beklenti = bir-yıl-önceki-aynı-çeyrek
   net-kâr; sürpriz = fark / tarihsel-std. **Konsensüs GEREKMEZ** — yalnız firmanın kendi
   net_profit-tarihçesi. Bu, retail-uygun + akademik-standart PEAD-tanımı.

`src/data/clean_universe_fundamentals.py` → `RAW_COLS` içinde `net_profit` ZATEN-var; degoran aylık
2009+ panel mevcut. SUE bedava-türetilir.

> **★ DE-KÜMÜLE UYARISI (kritik, look-ahead'den ayrı):** degoran `net_profit` **yıl-içi-kümülatif**
> (YTD): Ç1=Ç1, Ç2-rapor=Ç1+Ç2, Ç3=Ç1+Ç2+Ç3, Yıllık=tüm-yıl. SUE için ÇEYREKLİK gerekir →
> `Q_t = YTD_t − YTD_{önceki-çeyrek-aynı-yıl}` (Ç1'de YTD=Q). Yıl-sınırında sıfırlanır. Ham-YTD ile
> SUE yanlış-olur. Bu AŞAMA-2'de bir-kez doğru-kurulur (ölçüm-değil, türetme).

**Cevap: SUE HESAPLANABİLİR — lokal, bedava, konsensüs-siz; de-kümüle tek-şart.**

---

## Q2 — AÇIKLAMA-TARİHİ (tam-gün): KAP'tan parse-edilebilir mi?

PEAD'in **tek-gerçek-eksik-parçası** = kazanç hangi-GÜN açıklandı (drift t=0 buradan başlar).
degoran panel "dönem-sonu"nu bilir (Ç-sonu); **açıklama-günü AYRI** ve KAP'ta.

**Mekanik (RR-042'den, doğrulandı):** MKK-VYK `get_disclosures(disclosure_class='FR')` listesi
**tarih-İÇERMEZ** — alanlar: `disclosureIndex/title/disclosureClass/disclosureType/companyId/
subReportIds/acceptedDataFileTypes`. Tarih YALNIZ `get_disclosure_detail(index).time`'da.

**CANLI-KANIT (bu prob, 2 çağrı):**
- `get_disclosures(start_index=0, disclosure_class='FR', company_id=1107)` (THYAO) → 3 kayıt, hiçbiri
  tarih-içermiyor (liste-seviye).
- `get_disclosure_detail(1118481)` → **time='01.03.2023 18:22:22'**, year=2022, period='Annual',
  subject='Financial Report'.

→ Açıklama-tarihi **temiz, parse-edilir** (`_parse_tr_date` ZATEN-var: '01.03.2023 18:22:18' →
'2023-03-01'). Saat **18:22 = kapanış-sonrası** → look-ahead-safe (giriş t+1). Dönem-sonu (`year`/
`period`) ayrı-alanda saklanır → ikisi karıştırılmaz.

**Derinlik:** `_MIN_DISCLOSURE_INDEX = 538004` (KAP-4.0 cutoff). Altı = html-only (XBRL-yok) ≈
**pre-2019**. Tam-gün-tarih güvenilir-parse ≈ **2019+**. (Eski-tarihler html-scrape gerektir, bu
prob-kapsamı-dışı.)

> **★ MALİYET-TUZAĞI (RR-042 dersi):** MKK-VYK'da tarih/event-type FİLTRESİ YOK; kör-pagination
> pahalı (IP-rate-limit, non-lineer-index). Tam-panel tam-gün için: her-firma × her-çeyrek bir
> detay-çağrı + liste-pagination. ~150-firma × ~28-çeyrek (2019-2026) ≈ **bin-mertebe çağrı @ 1/sn**
> = saatler-mertebesi, sınırlı/cache'lenebilir AMA hızlı-prob-DEĞİL. Bütçeli-koşu (maintainer-onay).

**Cevap: ÇEKİLEBİLİR (tam-gün, look-ahead-safe, 2019+) AMA BÜTÇELİ — kör-pagination RR-042-tuzağı.**

---

## Q3 — AÇIKLAMA-TARİHİ (ay-proxy): BEDAVA alternatif var mı?

**EVET — ve bu raporun en-değerli-bulgusu.** degoran net_profit YTD-kümülatif + rapor-arası
**DÜZ-taşınır** (yeni-rapor gelene-kadar önceki-değer sabit). Demek: net_profit'in **adım-değiştiği
ay ≈ raporun-yayınlandığı ay**. Bu, panelden bedava-okunan AY-ÇÖZÜNÜRLÜKLÜ açıklama-proxy'si, 2009+.

**CANLI-KANIT (THYAO, degoran net_profit adım-ayları):**
- Ç2-2023 raporu → adım 2023-08'de (Ağustos, ~Ç2-bildirim-penceresi).
- Ç3-2023 → adım 2023-11.
- Yıllık-2022 → adım 2023-03 (KAP-tam-gün 2023-03-01 ile TUTARLI — proxy ay-içinde doğru).

→ Proxy, KAP-tam-gün ile **ay-düzeyinde örtüşür**. Gün-içi-hassasiyet yok (ay-pencere) ama:
**(a) bedava** (panel-elde, çağrı-yok), **(b) derin** (2009+, KAP-4.0-cutoff-yok), **(c) tüm-evren**
(degoran kapsamı). PEAD-edge-test'in İLK-okuması için ay-proxy yeterli; gün-hassasiyet ancak
dar-pencere-drift (CAR[0,+1]) ölçerken kritikleşir → o-zaman 2019+ KAP-rafinasyonu.

> **★ Look-ahead notu:** ay-proxy de **lag-gerektirir** — adım-ayı M ise sinyal M-sonu-bilinir,
> tüketim >= M+1 (degoran publication_lag_note: "month-M known at end-M"). Proxy bu-kısıtla
> look-ahead-safe; KAP-tam-gün ise gün-düzeyinde daha-keskin (18:22→t+1).

**Cevap: BEDAVA ay-proxy VAR (2009+, doğrulandı); KAP-tam-gün yalnız dar-drift-pencere için gerek.**

---

## Q4 — MAKRO-TAKVİM: TÜİK-TÜFE + TCMB-PPK tarihleri (2019-2026)

İkincil-yön (edge-prior-ZAYIF ama veri-ucuz; takvim kayıt-altına-alınır):

- **TÜİK-TÜFE:** "Ulusal Veri Yayımlama Takvimi" yıllık-yayınlanır; TÜFE her-ay ~**3'ünde 10:00**
  açıklanır (sabit-pencere, public). Tarihçe public-takvim-arşivinden + sabit-kural-ile türetilebilir.
- **TCMB-PPK (faiz-kararı):** yıl-sayfaları (public takvim) + EVDS. `src/signals/local/tcmb_client.py`
  EVDS-entegre (`_EVDS_BASE`, `_EVDS_POLICY_SERIES`). **UYARI:** `data/local_macro.db` →
  tcmb_decisions YALNIZ **2 satır** (2026-04-10, 2026-05-08) = canlı-cache, **tarihçe-YOK**. PPK-tarih
  geçmişi public-takvimden çekilir (yılda ~8-12 toplantı → düşük-hacim, RR-042-tuzağı-YOK).

**Cevap: PUBLIC + UCUZ (düşük-hacim, low-risk); lokal-değil → AŞAMA-2'de takvim-arşivi çekilir.**

---

## Mekanizma / Neden bu-yön meşru

Kesitsel-faktör havuzu (D-205 hi52, NRR-007 lowvol63, NRR-008 value-regime) + NAV (D-206 holding,
RR-045/NRR-009 fund) tükendi: hepsi ya SERAP ya yapısal-engel (BIST-prim, long-only-uyumsuz).
**PEAD farklı-sınıf:** olay-güdümlü, kesitsel-sıralama-değil → kesitsel-duvarı by-pass. Edge-prior
global-güçlü (en-replike-edilen anomali). BIST'te **henüz-test-edilmedi** (bu-lab'da); veri-fizibilite
ön-koşulu bu-raporla karşılandı. Makro-event ikincil, edge-zayıf ama veri kayıt-altına-değer.

---

## Sonraki adım — AŞAMA-2 (PAUSE, maintainer-onay-bekler)

> **DURDU. Aşağısı ÖNERİ; çekim YAPILMADI.** directive: "olumluysa AŞAMA-2-çekim (maintainer-onay)".

**Önerilen AŞAMA-2 (iki-katman, veri-edinim-only, motor-dokunma):**

1. **PEAD-tarih KATMAN-1 (BEDAVA, geniş/derin):** degoran net_profit adım-ay-proxy 2009+ tüm-evren →
   `data/snapshots/earnings_dates.parquet` (sütun: ticker, period_end, announce_month_proxy, source).
   De-kümüle + SUE-türetme aynı-koşuda (look-ahead-safe lag).
2. **PEAD-tarih KATMAN-2 (BÜTÇELİ, dar/keskin):** KAP-tam-gün 2019+ alt-küme (likit-evren) →
   aynı-parquet'e `announce_date` (gün) + `announce_source='KAP'` ekle. Sınırlı-bütçe (RR-042: dar
   pencere, cache-zorunlu, kör-pagination-yok). CAR[0,+1] keskin-drift için.
3. **MAKRO-takvim:** TÜİK-TÜFE (Ulusal-Takvim + ~3'ü-kural) + TCMB-PPK (yıl-sayfaları/EVDS) 2019-2026 →
   `data/snapshots/macro_event_dates.parquet` (event_type, event_date, source). Düşük-hacim.

**KISIT (AŞAMA-2):** VERİ-EDİNİMİ-only (edge-test YOK = ayrı-D-XXX). repo: yalnız `data/snapshots/`
(read-only-genişletme, committed-motor SIFIR-dokunuş). look-ahead-safe ZORUNLU (announce =
gerçek-açıklama, dönem-sonu-DEĞİL). ASCII. branch+PR+yeşil-CI.

---

## Dürüstlük

- KAP-tam-gün KANITLANDI (THYAO 2022-Yıllık='01.03.2023', temiz/look-ahead-safe) AMA derinlik ~2019+
  (KAP-4.0 cutoff) + maliyet RR-042-tuzağı (bütçeli-koşu, hızlı-prob-değil).
- degoran-ay-proxy bedava+derin (2009+) doğrulandı AMA ay-çözünürlük (gün-içi-yok); dar-drift-pencere
  için 2019+ KAP-rafinasyonu gerekir — iki-katman bu-yüzden.
- SUE konsensüs-siz-hesaplanır AMA de-kümüle ZORUNLU (YTD→çeyreklik); atlanırsa SUE-yanlış.
- PEAD edge-prior GÜÇLÜ (global) AMA bu rapor edge-ÖLÇMEZ; BIST cost/turnover-duvarı edge-test'te
  (sonraki-D) sınanır — burada iddia-YOK.
- Makro-event edge-prior ZAYIF (beklenti-fiyatlı); veri-ucuz olduğu-için kayıt-altına-alınır, edge
  vaadi-YOK.
- Kutlama-yok; bu yalnız veri-fizibilite — "çekilebilir-mi" sorusuna EVET (iki-katman), edge-sorusu
  AÇIK-ve-sonraki-adım.
