# SPEC — YOL 2 ANA SİSTEM (v3.0 paradigması)
## Strateji-seviyesi spec. Detay-build adımları Builder plan-mode'da netleşir.

**Tarih:** 1 Haziran 2026 — Session #11
**Dayanak:** ARCHITECTURE v3.0 + RR-OMEGA öncelik-sıralaması + 4 test dersleri
**Statü:** Taslak → bağımsız-göz (Kategori-1 bloke-kontrolü) → inşa

---

## 0. AMAÇ VE FELSEFE
Yol 2 = ana sistem, gerçek-para, ÇAPA. Tahmin/seçim-dehası DEĞİL → disiplinli
maruziyet + maliyet-minimizasyonu + risk + kanıtlı-mütevazı-faktör. Hedef: reel >
max(TÜFE, para-piyasası); gerçekçi piyasa-üstü yılda birkaç-puan USD-reel.
"Yavaş ama gerçek." Yol 1 (keşif lab) paralel; oradan KANITLA terfi eden katmanlar eklenir.

---

## 1. KATMANLAR (RR-OMEGA öncelik-sıralı, inşa sırası)

### KATMAN 0 — Maliyet/Vergi Disiplini (İLK İNŞA, en kesin)
İşlevler:
- Aracı-maliyet modeli: gerçek komisyon+BSMV+spread+slippage (mevcut maliyet-modeli
  reuse; RR-014/015 kalibre)
- Vergi-katmanı: yerli-hisse %0 kazanç-stopajı, temettü %15, beyan-eşiği izleme
- Devir-hızı monitörü: aşırı-işlem uyarısı (Barber-Odean dersi)
Çıktı: her strateji-kararının NET (maliyet+vergi-sonrası) etkisi görünür.
Test: yok (bu disiplin-katmanı, ölçüm değil; doğruluğu Builder-unit-test).

### KATMAN 1 — Risk-Primi Zemini (statik maruziyet)
İşlevler:
- Geniş-BIST maruziyeti (endeks/temsili-sepet) — piyasa risk-primi al-tut
- Maruziyet-oranı: statik/kural-temelli (D-187: aktif-zamanlama elendi). Sabit
  karışım + periyodik rebalance. Oran-seçimi Cagan-kararı (risk-iştahı).
- reel + XU100-relative + USD-reel raporlama (nominal-drift tuzağı)
Test: D-187 zaten ölçtü (baz-tahsis generic-değerli). Yeni-test gerekmez; uygula.

### KATMAN 2 — Mütevazı-Faktör Tilt (sistematik, AMPIRIK-TEST GEREKLİ)
İşlevler:
- Değer + Kalite/Kârlılık + Düşük-vol çoklu-faktör tilt (long-only, eşit-ağırlık)
- Yıllık/yarı-yıllık rebalance, düşük-devir
- MOMENTUM YOK (BIST zayıf/negatif)
- composite-optimize YASAK (invariant #4) — kapı/sıralama-dili
⚠️ BU KATMAN BİR HİPOTEZ: RR-OMEGA "değer+kalite+düşük-vol ~%55-65 olasılık" dedi
AMA BIST-net-USD-reel-alfa AMPIRIK-TEST edilmeli (RR-OMEGA kanıt-boşluğu).
→ D-190 adayı: değer+kalite+düşük-vol tilt, net-maliyet-sonrası, XU100-relative,
  adil-null, Stage-0 ön-kayıt. GEÇERSE Katman 2 aktifleşir; GEÇMEZSE saf-zemin kalır.

### KATMAN 3 — BIST-Niş (Yol 1 lab'dan terfi, sınırlı pay)
- İllikidite primi (küçük-sermaye-avantajı, t=3.46) — slippage-sonrası test gerekli
- Contrarian (kaybedenleri-al) — decay-testi gerekli (Bildik-Gülay 1991-2000 eski)
Bunlar Yol 1'de test-edilip kanıtlanınca Yol 2'ye girer (varsayılmaz).

### KATMAN 4 — İnsan-Yargısı (TEST EDİLECEK, varsayılmaz)
- Saf-endeks vs aday-daraltma+insan-seçim: hangisi daha iyi?
- İleri-dönük test: Cagan gerçek-seçimlerini kaydeder, endeksle karşılaştırılır
  (D-188 forward-recorder mantığı; look-ahead/overfit yapısal-imkansız)
- İnsan-katmanı dürüst-benchmark'ı geçerse aktifleşir; geçmezse saf-sistem kalır

### EXECUTION — Fikir A (paralel ARGE, Yol 2'ye hizmet)
- Order-splitting + optimal-timing (illikidite-slippage azalt)
- EHB-donanım (FPGA) — ayrı ARGE-izi, CV-değerli
- Yol 2'nin Katman-3 (illikidite) verimini artırır

---

## 2. AMPIRIK-TEST HİPOTEZLERİ (RR-OMEGA kanıt-boşlukları → Yol 1/D-190+)
RR-OMEGA bunları "BIST-test gerekli hipotez" olarak bıraktı:
(a) Değer+kalite+düşük-vol tilt'in NET (maliyet+vergi+slippage) USD-reel alfası
(b) İllikidite priminin gerçekçi-slippage-sonrası küçük-sermaye-yakalanabilirliği
(c) Contrarian priminin 2010-sonrası (Bildik-Gülay-dışı) hâlâ-var-mı (decay)
(d) BIST endeks-revizyon etkisinin güncel-büyüklüğü
Her biri: Stage-0 ön-kayıt + reel + XU100-relative + adil-null + maliyet-sonrası.

---

## 3. YÖNETİŞİM — ÜÇ-KATEGORİ (gömülü)
Kritik/doğrulama-agent: Bloke(1, durdur) / İyileştirme(2, backlog) / Nüans(3, kaydet).
Sadece Kategori-1 yeniden-açar. Sistem kanıt-temelli+bloke-hatasız kurulur, kusursuz-değil.

---

## 4. DEĞİŞMEZ TEST-DERSLERİ (her katman-testinde)
reel + XU100-relative + USD-reel · adil-null · look-ahead (t/t+1) · survivorship ·
composite-YASAK · Stage-0 ön-kayıt · post-hoc-YASAK · maliyet+slippage · kirli-veriyle-ölçme-YOK

---

## 5. İNŞA SIRASI (öneri — Builder plan-mode netleştirir)
1. Builder repo-envanteri + reusable-map + outdated-arşiv (İLK İŞ — kod-gerçeği)
2. Katman 0 (maliyet/vergi) — en kesin, ölçüm-değil
3. Katman 1 (risk-primi zemini) — D-187 zaten ölçtü, uygula
4. D-190: Katman 2 hipotez-testi (değer+kalite+düşük-vol net-alfa)
5. Katman 2 (test geçerse) / Katman 3-4 (Yol 1 terfi + insan-test)
PARALEL: Yol 1 lab (D-188 forward veri-topluyor + niş-testler)

---

## 6. DESKTOP ≠ REPO
Bu SPEC strateji-seviyesi. Modül-envanteri, reusable-map, hangi-katman-zaten-var
→ Builder doğrular (ilk iş). Orchestrator "repo'da X var" diye kesin-konuşmaz.

---

## 7. NE DAHİL DEĞİL (scope-netliği — kapsam-daralma değil, kanıt-temelli dışlama)
- Momentum-faktör (BIST zayıf/negatif)
- Aktif maruziyet-zamanlaması (D-187 elendi)
- Cross-sectional faktör-seçim-dehası (Faz 0 elendi)
- Saf-teknik swing entry-timing (D-185/186 elendi)
- HFT-hız-yarışı (ko-lokasyon imkansız)
- Kısa-vade-büyük-getiri vaadi ("haftada %6" gerçek-dışı)
Bunlar TEST-EDİLİP elendi/imkansız — kapsam-daraltma değil, kanıt-temelli dışlama.
(Yol 1 lab hâlâ açık: olay-confluence, insider, mean-reversion, illikidite ileri-dönük)

---

*SPEC_YOL2 v3.0 — 1 Haziran 2026. Katmanlı (maliyet/vergi → risk-primi → faktör-tilt
→ BIST-niş → insan-test), RR-OMEGA öncelikli, ampirik-test-hipotezli, üç-kategori-
yönetişimli. Detay-build Builder plan-mode. Bağımsız-göz Kategori-1 kontrolü sonra inşa.*
