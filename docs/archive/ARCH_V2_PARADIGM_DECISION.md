# ARCHITECTURE v2.0 — Paradigma Karar Belgesi (Katman A Motor Değişimi)

**Tarih:** 30 Mayıs 2026
**Statü:** Yön kararı (O+Cagan). Tam ARCHITECTURE.md v2.0 revizyonu Architect'e devredilecek.
**Dayanak:** Faz 0 IC harness (D-177/178/183) + Critic CB-017 + RR-UST (taksonomi) + RR-038 (modern BIST)

---

## NEDEN v2.0 — TEK CÜMLE

ARCHITECTURE v1.2'nin Katman A motoru (**eşit-ağırlık cross-sectional faktör rank composite**: RS + low-vol + value), Faz 0'da ampirik olarak BIST'te zayıf çıktı; üç bağımsız kanıt kaynağı (ölçüm + critic + literatür) bu paradigmanın **küçük-sermaye-bireysel-BIST profili için yapısal olarak yanlış araç** olduğunu doğruladı. Dört-katman iskeleti KORUNUR; sadece Katman A'nın motoru değişir.

---

## NE DEĞİŞMEZ (v1.2'den korunan)

- **Dört katman iskeleti:** D (makro şalter) / A (tarama) / B (LLM asistan, en son) / C (icra: Kelly+ADV+stop)
- **Sorumlulukların ayrılması:** sert kısıtlar=deterministik, tarama=kantitatif, sentez=LLM(öneri), nihai karar=Cagan
- **LLM asla aktüatör değil** (öneri, tetik değil)
- **Hedef:** reel getiri > max(TÜFE, para piyasası). Edge'in %80'i hata yapmamaktan.
- **Stage 0 ön-kayıt, look-ahead disiplini, survivorship, snapshot dondurma** (tüm doğrulama protokolü)
- **Strangler in-place refactor** (eski çekirdek kanıtlanana kadar pasif kalır)
- **Kullanıcı nihai karar verici** (Katman A öneri → Cagan seçer → Katman C icra)

---

## NE DEĞİŞİR — KATMAN A MOTORU

### ESKİ (v1.2) — YANLIŞLANDI
```
Katman A = SERT KAPILAR + EŞİT-AĞIRLIK RANK COMPOSITE (RS + low-vol + value)
→ cross-sectional faktör sıralama ("en iyi skorlu hisseleri al")
```

**Neden yanlışlandı (üç kanıt):**
1. **Faz 0 ölçümü:** rs6/rs12/value honest_t<2 (geçmedi); sadece lowvol60 marjinal.
2. **Critic CB-017:** lowvol60 ≈ D-katmanı rejim-gölgesi (D-koşullu IC %90.5); bağımsız alpha zayıf; multiple-testing'de kırılgan.
3. **RR-UST + RR-038 (literatür):** Cross-sectional faktör = kurumsal teknoloji (büyük-N, long-short, çeşitlendirilmiş). Küçük-sermaye-bireysel-sadece-long-BIST için yapısal olarak uygunsuz (breadth yetersiz, short yasak, maliyet erozyonu). **Modern BIST'te (2020-2024 veri) kesitsel momentum TERSİNE (reversal baskın — Ünal 2021/2024, %1 anlamlı): kazananlar sonradan zayıf kalıyor.**

### YENİ (v2.0) — TREND-BAŞI YAKALAMA + REVERSAL-KAÇINMA + KALİTE SÜZGECİ + REJİM TEYİDİ

```
Katman A = 
  SÜZGEÇ (faktör/temel — GETİRİ MOTORU DEĞİL, izleme listesi daraltıcı):
    likidite (BIST30/50 + likit BIST100) + temel kalite + makul değerleme
    → "hangi hisselere bak" — Cagan'ın zayıf olduğu finansal analizi otomatikler
  +
  ANA MOTOR (zaman-serisi trend-başı yakalama):
    - Hisse kendi sağlıklı trendinde mi (MA üstü, yükselen dip-zirye)
    - TREND BAŞLANGICI / düşük-riskli giriş (destek-direnç flip, 
      konsolidasyon-retest) — Cagan'ın doğal tarzı
    - ⚠️ KESİTSEL "EN ÇOK YÜKSELENİ AL" YASAK (BIST reversal gerçeği)
  +
  KAÇINMA FİLTRESİ (reversal riski):
    - Parabolik / aşırı-uzamış / hype hisseleri AL listesinden ÇIKAR
    - (modern BIST: hızlı kazananlar sonradan ortalama-altı)
  +
  REJİM TEYİDİ (Katman D ile birlikte, tek-hisse değil):
    - Yabancı + yerli kurumsal net akış ENDEKS/REJİM seviyesinde
    - Yabancı alım rejimi → long-bias artır; satış rejimi → temkin/nakit
    - ⚠️ Yabancı akış TEK-HİSSE al-sinyali DEĞİL (RR-038: tekil öngörü zayıf)
```

**Neden bu yön (kanıt):**
- RR-038: Modern BIST reversal-baskın → "trend başını yakala, uçtan kaç" doğru yanıt
- RR-038: Yabancı akış endeks-seviye öncü/bilgili (rejim ✓), tek-hisse zayıf
- RR-UST: "Süzgeç (faktör) → Zamanlama (trend/breakout) → Olay" en sinerjik kombinasyon (CAN SLIM mantığı)
- Cagan tarzı örtüşmesi: destek-direnç flip + konsolidasyon-retest + parabolikten-kaçınma + iyi-finansal-aşağıda-kalmış = raporun önerisiyle birebir

---

## KATMAN A SİNYAL MANTIĞI — CONFLUENCE (Cagan içgüdüsü)

İki bağımsız sinyal HİZALI ise konviksiyon yüksek:
```
Kalite-süzgeç GEÇTİ (iyi finansal + aşağıda kalmış)
  + Teknik kurulum OLGUN (destek-direnç flip / konsolidasyon-retest, parabolik DEĞİL)
  + Rejim TEYİT (yabancı/kurumsal akış + XU100 trend pozitif)
  → yüksek konviksiyon → Kelly-ölçekli pozisyon (Katman C)

Biri var diğeri yoksa → düşük konviksiyon → küçük/yok
```
Confluence = signal confirmation. Cagan'ın "iki yönden tümdengelim" (teknik beğendiğime yabancı akışı da varsa öncelik / yabancı akışı olana teknik bakışı) içgüdüsünün sistemsel karşılığı.

---

## OPSİYONEL EK KATMAN (Faz ilerideki)

**Olay-güdümlü (RR-UST 4/5):** PEAD (bilanço sürprizi drift), endeks dahil/çıkar, bedelli/bedelsiz. Trend sistemiyle düşük korelasyonlu ek edge. Ana motor kanıtlandıktan SONRA eklenir.

---

## BAŞARI KISTASI — PER-TRADE (Cagan psikolojisi + gerçeklik)

**v1.2'deki "yıllık portföy getirisi" çerçevesi → per-trade expectancy + fırsat sıklığı:**
- Her işlem, tuttuğu sürenin faiz fırsat-maliyetini ASİMETRİK yensin (Cagan hedefi: ~%10-15 / birkaç hafta)
- Maliyet eşiği: per-trade ~%1.5-3 brüt hareket (BSMV komisyon-üzerinden, düşük; RR-038)
- Fırsat sıklığı × per-trade getiri = gerçek performans (nakit beklerken fırsat maliyeti var)
- Gerçeklik kontrolü: toplam yıllık, mevduat (~%40) üstüne çıkmalı (yoksa mevduat daha mantıklı)
- Expectancy TÜM işlemlerin ortalaması (kazanan+kaybeden) — survivorship-in-memory tuzağına karşı

---

## VADE

Birkaç hafta–birkaç ay (Cagan içgüdüsü ✓, RR-038 onayı). Çok-kısa-vade YASAK (reversal + maliyet erozyonu).

---

## KRİTİK AÇIK NOKTA — ANA MOTOR TEST EDİLMEMİŞ

**RR-038 kanıt boşluğu:** Zaman-serisi trend-takibinin modern BIST kârlılığı akademik olarak TEST EDİLMEMİŞ (kesitsel reversal kanıtlı ama o farklı şey). Yeni Katman A motoru, **kendi backtest'imizle ölçülmeli** — yeni ölçüm programı (kendi Stage 0). Bu sefer literatür ön-uyarısıyla giriyoruz (kesitsel momentum YAPMA — baştan biliyoruz).

**Sıradaki test (yeni paradigma ön-koşulu):**
"BIST'te zaman-serisi trend / destek-direnç-flip / breakout-retest kurulumları, parabolik-kaçınma filtresiyle, 2019-2026'da per-trade expectancy + maliyet-sonrası ne veriyor?"

---

## v1.2 → v2.0 GEÇİŞ NOTU (geçmiş korunur)

- v1.2 cross-sectional faktör motoru SİLİNMEZ — "denendi, BIST'te zayıf çıktı, evrim" olarak kayıtta (Faz 0 sonuçları docs/factor_ic/ korunur)
- lowvol60: ana sinyal değil ama SÜZGEÇ bileşeni olarak kalabilir (rejim-gölgesi sorunu süzgeçte sorun değil)
- value (MaliTablo): getiri motoru değil, KALİTE SÜZGECİ (Cagan'ın "iyi finansal" filtresi)
- Bu, pivotun İKİNCİ evrimi (1: composite→tarama; 2: cross-sectional faktör→trend/swing)

---

## ARCHITECT'E DEVİR

Tam ARCHITECTURE.md v2.0 revizyonu Architect'e (Cowork plan-mode SPEC) verilecek. Bu belge yön kararıdır; Architect build-edilebilir detayda §3 Katman A'yı yeniden yazar, diğer bölümleri (D/B/C, doğrulama, look-ahead) v1.2'den korur + per-trade kıstas + confluence mantığını işler.
