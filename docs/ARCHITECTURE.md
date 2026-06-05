# ARCHITECTURE — BIST OS Mimari Sözleşmesi v3.0
## Tek-kaynak-gerçek. Önceki v2.0 (trend/swing paradigması) GEÇERSİZ.

**Tarih:** 1 Haziran 2026
**Statü:** Yön kararı. Detay-SPEC ayrı (SPEC_YOL2).

> ÜÇ EVRİM: (1) 5-katman composite → tarama-öncelikli quantamental (v1.x);
> (2) cross-sectional faktör → trend/swing (v2.0); (3) trend/swing ÇÜRÜDÜ →
> **disiplinli statik maruziyet + maliyet/vergi + mütevazı-faktör + BIST-niş**
> (v3.0). Geçmiş mimariler SİLİNMEZ (pivot=evrim). Kanıt: 4 test + 3 araştırma.

---

## NEDEN v3.0 — TEK CÜMLE
Dört bağımsız test (faktör/trend/maruziyet/eski-sistem) + üç araştırma (RR-FINAL/
MUTLAK/OMEGA) kanıtladı: **BIST'te bu ölçekte sistematik büyük-giriş-edge YOK;**
değer maliyet/vergi-disiplini + risk-primi-zemini + mütevazı-faktör-tilt + BIST-
nişlerinde (illikidite, contrarian). v2.0'ın "trend/swing Katman A motoru" çürüdü.

---

## TEMEL PARADİGMA (v3.0)
"Tahmin/zamanlama/seçim-dehası" DEĞİL → "**disiplinli maruziyet + maliyet-minimizasyonu
+ risk-yönetimi + kanıtlı-mütevazı-faktör-hasadı.**" Edge'in %80+'i hata-yapmamaktan
(maliyet, vergi, aşırı-işlem, duygusal-hata) gelir; kalanı mütevazı-primlerden.

Hedef: Reel getiri > max(TÜFE, para-piyasası-fonu). "Piyasayı sürekli-büyük-yenmek"
DEĞİL (kanıt: imkansıza yakın). Gerçekçi piyasa-üstü: yılda birkaç-puan USD-reel.

---

## YOL 2 KATMANLARI (v3.0 — RR-OMEGA öncelik-sıralı)

### Katman 0 — MALİYET/VERGİ DİSİPLİNİ (en yüksek kesinlik ~%90)
- Düşük/sıfır-komisyon aracı (Midas %0 + BSMV); banka-kanalı maliyetinden kaçın
- Yerli BIST hisse: %0 sermaye-kazanç-stopajı (post-2006, Geçici 67); temettü %15
- Devir-hızı minimize (Barber-Odean: aşırı-işlem = düşük net-getiri)
- Bu katman "alfa" değil ama EN KESİN değer-kaynağı.

### Katman 1 — RİSK-PRİMİ ZEMİNİ (sistematik al-tut)
- Geniş BIST maruziyeti (endeks/temsili-sepet) ile piyasa risk-primi
- Türkiye ERP ~%10.34 (Damodaran, çok-oynak, USD); zemin-getiri, beceri-değil
- Maruziyet-ORANI kararı (ne kadar equity) statik/kural-temelli (D-187: aktif-
  zamanlama elendi; statik baz-tahsis generic-ama-değerli)

### Katman 2 — MÜTEVAZI-FAKTÖR TILT (sistematik, kural-temelli, long-only)
- Değer + Kalite/Kârlılık + Düşük-volatilite çoklu-faktör tilt (+%2-4 piyasa-üstü)
- Yıllık/yarı-yıllık rebalance, düşük-devir
- ⚠️ MOMENTUM DAHİL ETME (BIST'te zayıf/negatif — Bildik-Gülay)
- Eşit-ağırlık veya yok; composite-optimize YASAK (invariant #4)

### Katman 3 — BIST-NİŞ (sınırlı pay, ampirik-test sonrası)
- İllikidite primi: KÜÇÜK-SERMAYE AVANTAJI (devler giremez; t=3.46). Slippage yer.
- Contrarian (kaybedenleri-al): BIST'in en-belgelenmiş anomalisi, ama decay-testi gerekli
- Bunlar araştırma kapsamında test edilip Yol 2'ye terfi-eder (varsayılmaz)

### Katman 4 — İNSAN-YARGISI (test edilecek, varsayılmaz)
- Saf-endeks vs aday-daraltma+insan-seçim: HANGİSİ daha iyi → TEST ("testle doğrula" prensibi)
- İnsan-seçim-katmanı değer-katıyor-mu, dürüst-benchmark'a karşı ölçülür (D-187 mantığı)
- İleri-dönük test (gerçek seçimler kaydedilir, endeksle karşılaştırılır)

### EXECUTION (Fikir A — yeniden-tanımlı, paralel ARGE)
- Order-splitting + optimal-timing + smart-routing (HFT-hız-yarışı DEĞİL)
- EHB-donanım (FPGA sinyal-işleme) — illikidite-slippage'ı azaltır, CV-değerli
- İTÜ-EHB kaynakları besler (ko-lokasyon DEĞİL — o imkansız)

---

## 12 İNVARİANT (v1.2'den korunan — DEĞİŞMEZ)
Mimari sözleşme. Her spec saygı gösterir:
- #4: Composite ağırlığı OPTİMİZE EDİLMEZ (eşit-ağırlık veya yok)
- #5: Mutlak nominal RS YASAK (enflasyon kirliliği) → reel/relative
- #9: Survivorship dahil (delisted'lar: KOZAA/KOZAL/IPEKE/TRALT class)
- Snapshot dondurma: tüm ölçümler frozen parquet'ten (look-ahead guard)
- reel + XU100-relative zorunlu (nominal-drift tuzağı)
- adil-null zorunlu (giriş-seçimi mi çıkış-mekaniği mi)
- look-ahead: sinyal-t / aksiyon-t+1
- Stage-0 ön-kayıt; post-hoc gevşetme YASAK
(Tam liste `tests/test_architecture.py`'de CI-enforced olarak tutulur;
v3.0 bunları DEĞİŞTİRMEZ, sadece Katman-A paradigmasını günceller)

---

## STRANGLER (korunur)
Eski mimari + Faz 0 + trend kodları SİLİNMEZ. v3.0 üstüne kurulur. Yeni modüller
mevcut yapının YANINA (src/screening/, src/execution/ vb.). Reusable parçalar
(snapshot/IC/look-ahead-guard, fair_random_null, reel-deflate, XU100-relative,
forward-return, HAC-t, Holm) yeniden-kullanılır.

---

## YÖNETİŞİM — ÜÇ-KATEGORİ
Bulgular üç kategoride değerlendirilir: Bloke(1, durdur) / İyileştirme(2, backlog) / Nüans(3, kaydet).
Sadece Kategori-1 sistemi yeniden-açar. Sistem kusursuz değil, kanıt-temelli+bloke-hatasız
kurulur, iyileştirilerek olgunlaşır.

---

*ARCHITECTURE v3.0 — 1 Haziran 2026. Trend/swing (v2.0) çürüdü; disiplinli-maruziyet+
maliyet/vergi+mütevazı-faktör+BIST-niş paradigması. 4 test + 3 araştırma dayanağı.
Geçmiş silinmez. Detay: SPEC_YOL2.*
