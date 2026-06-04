# lab-demo-goal L5 -- web sentez (borsapy/borsamcp veri turleri + BIST anomali literaturu)

Iki otonom web-arastirma raporunun damitilmis ozeti. Amac: (a) AKLIMIZA-GELMEYEN yeni veri
turleri, (b) likit-evren + gercekci-maliyet-sonrasi YASAMA-sansi olan anomaliler. ASCII.

## A. borsapy / borsa-mcp ve akraba repolar -- cektikleri veri turleri

Repolar: borsapy (saidsurucu, ~641*), borsa-mcp (~589*), isyatirimhisse (~149*),
tefas-crawler/pytefas, pykap/kap-tr-sdk.

YENI (bizde-YOK, BEDAVA, derin-gecmis VAR) -> aday-yapan:
- TEFAS fon akimlari + yatirimci-sayilari: ~5 yil bedava gecmis. Fon-bazinda gunluk
  net-akim + pay-sahibi-sayisi. -> retail/kurumsal akim proxy, momentum/contrarian timing.
- KAP olay-madenciligi: tam bedava gecmis. Bildirim metni/tipi (temettu, sermaye-artirimi,
  geri-alim, yonetim, ortaklik-yapisi). -> event-study malzemesi (bizde sadece earnings/macro var).

YENI ama SINIRLI (forward-snapshot gerekir, derin-bedava-gecmis YOK):
- Yabanci-takas-orani (foreign ownership ratio): guclu sinyal AMA bedava-API yalniz
  guncel-anlik; gecmis-panel icin ileriye-dogru biz-snapshotlamaliyiz. Simdi baslat = 1yil-sonra-test.
- Analist-revizyonlari / hedef-fiyat: ayni -- forward-snapshot gerekir.

VAPORWARE / paid / kullanilamaz:
- Short-selling hacmi, blok-islemler, tick-derinligi (order-book L2): paid veya bedava-API'de yok.

## B. BIST anomali literaturu -- likit/maliyet-aware hayatta-kalma notu

Her madde: guc-derecesi + likit-evrende-maliyet-sonrasi-beklenti. ONEMLI uyari: atifli
orneklerin TAMAMI 2019-2026 enflasyon-rejimi ONCESI -> dis-gecerlik supheli, biz-test-etmeli.

- **PEAD (post-earnings-announcement-drift): ORTA, EN-IYI event-driven aday.** ~+2.9%/60g
  (Ahlatcioglu-Okay 2020). FIYAT-DISI sinyal (kazanc-surprizi) -> selection-bias-dusuk.
  ~30-40bp maliyeti gecer (dusuk-turnover, olay-bazli). Bizde earnings_dates.parquet VAR
  (SUE %59 NaN, AYLIK cozunurluk) -> L3.
- **Yabanci-akim: GUCLU ama yalniz ENDEKS-seviyesi** (cross-sectional DEGIL). Index-timing
  overlay olabilir; tek-isim secimi-degil. Bizde gunluk-yabanci-akim-panel YOK (bkz A: snapshot).
- **Kisa-vade reversal (1h/1ay): akademik-GUCLU ama microcap-yogun + bid-ask-bounce**
  (Bildik-Gulay contrarian). Likit-evrende + gercekci-maliyet ZOR (yuksek-turnover). -> L2,
  DURUST-beklenti = maliyet-duvari. Yine de hic izole-test-edilmedi, olcmeye-deger.
- **Endekse-dahil-olma (index-inclusion): ORTA ama global-OLARAK-zayifliyor.** Bildik-Gulay 2008:
  HACIM-etkisi > FIYAT-etkisi; etki EFEKTIF-GUN civari zirve, sonra reversal. -> L1
  (pit_membership ile event-study). Tradeable yalniz [+1,+K] (ilan-tarihi-yok; on-pencere descriptive).
- **Dusuk-volatilite: BIST'te TERSINE-donmus** -> lowvol63 zaten SERAP cikti (graveyard, tutarli).
- **MAX / piyango (asiri-getiri-tercihi): ORTA; short-bacak microcap** -> deploy-zor (long-only biz).
- **Illikidite-primi: GUCLU ama = microcap-serabi** -> dogru-sekilde-disladigimiz sey (graveyard ana-ders).

## C. Sonuc -- oncelik guncellemesi (agent-bilgisiyle)

1. **L1 INDEX-REBALANCE** [BASLIYOR]: pit_membership DOKUNULMAMIS, event-driven, dusuk-turnover,
   deploy-edilebilir (uyeler likit), literatur-destekli. Beklenti: ORTA-ama-zayiflayan; [+1,+K]
   tradeable, on-pencere descriptive. EN-YUKSEK-NOVELTY-elde-veriyle.
2. **L3 PEAD**: agent EN-IYI-event-driven dedi; FIYAT-DISI; bizde veri-VAR (aylik). Yuksek-oncelik.
3. **L2 SHORT-REVERSAL**: izole-test-edilmemis; DURUST-beklenti maliyet-duvari ama ucuz-olcum.
4. **L4 CALENDAR**: ucuz tarama, VIEW-belgele, multiple-testing-aware.
5. **YENI-VERI-KUYRUGU (forward-snapshot, sonraki-faz)**: yabanci-takas-orani + analist-revizyon
   snapshotlamayi BUGUN-baslat -> ileride-test. TEFAS-fon-akimi + KAP-olay = bedava-derin-gecmis,
   ayri-cekim-isi (repo read-only; lab'da snapshot-script yazilabilir, AMA once eldeki-veriyi-tuket).

ANA-CIKARIM: likit + maliyet-aware evrende hayatta-kalmaya en-yakin iki-sey = (a) PEAD,
(b) yabanci-akim endeks-timing. Index-rebalance novelty-en-yuksek ve elde-veri-var -> ilk-test.
