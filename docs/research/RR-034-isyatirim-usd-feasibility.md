# RR-034 — İş Yatırım USD-Bazlı Value Fizibilite Kontrolü (D-180)

**Tarih:** 30 Mayıs 2026
**Yazar:** Arastirma katmani — canlı probe (throwaway)
**Status:** ⚠️ Kontrol tamamlandı — USD-bazlı "Yol A" tarihsel IC için YEŞİL DEĞİL (snapshot-only). Karar maintainer (DEC-039).
**Bağlı:** [RR-033](RR-033-isyatirim-tms29-uyum-testi.md) (D-179 INCONCLUSIVE devamı); [RR-032 §6 Yol A](RR-032-FIZIBILITE.md); NRR-002; [RR-021](RR-021-TCMB.md) (EVDS USD/TRY)

---

## TL;DR

D-179 yan bulgusu: İş Yatırım `getScreenerDataNEW` USD-bazlı değer veriyor (field 9 = Market Cap USD). Hipotez: USD-bazlı değerleme TMS 29'u baypas eder → MKK'ya gerek kalmaz. **Canlı probe ile test edildi.**

**Sonuç: HİPOTEZ KISMEN GEÇERSİZ — iki bağımsız nedenle:**

1. **İş Yatırım USD değerleri snapshot-only** — geçmiş yok. 5 tarih/dönem parametresi varyantı da yok sayıldı; değerler bugünkü TL ÷ bugünkü tek spot kur (45.71, EVDS ile %0.2 farkla eşleşti). Faz 0b 24-ay paneli **tek başına beslenemez**.
2. **Kavramsal:** P/B ve EV/EBITDA **birimsiz oranlar** — USD'ye çevirmek oranı değiştirmez (aynı kurda pay/payda sadeleşir). Dolayısıyla USD, cross-sectional value sıralamasında TMS 29 sorununu **otomatik baypas etmez**. USD'nin gerçek faydası: absolute level'ın zaman-karşılaştırılabilirliği + USD-getiri.

**Alternatif yol (Q4) fizibil:** Geçmiş TL fundamental + EVDS dönem-sonu kuru ile **biz çeviririz**. EVDS tarafı **tamamen hazır** (584 günlük gözlem, 28 ay-sonu kuru, 2024-01→2026-04). Darboğaz: **geçmiş TL fundamental kaynağı** — RR-032 Yol B/C'ye geri döner ve TMS 29 sorusu (RR-033) hâlâ açık kalır.

---

## Soruların Cevapları

### Q1 — İş Yatırım USD değerlerini nasıl hesaplıyor? ✅ Anlık TL ÷ anlık spot

478 ticker için implied FX = field8 (Market Cap TL) ÷ field9 (Market Cap USD):

| Metrik | Değer |
|---|---|
| n | 478 |
| median implied rate | 45.7134 |
| min / max | 45.6836 / 45.7368 |
| ±%1 bandında | **478/478 (%100)** |
| EVDS bugünkü USD/TRY (TP.DK.USD.A) | 45.6312 |
| implied median / EVDS | **1.0018 (≈1.0)** |

→ Tüm ticker'larda **tek bir spot kur** kullanılıyor; bu kur EVDS güncel kuruyla eşleşiyor. Yani field 9 = **anlık TL market cap ÷ anlık spot USD/TRY**. Anlık market cap için bu doğru ve yeterli.

**Oranlar (field 29 EV/EBITDA, field 30 P/B):** Birimsiz — TL ve USD'de aynı sayı. USD'ye çevirmek bunları değiştirmez (önemli kavramsal nokta, aşağıda).

### Q2 — Kapsama? ✅ Mükemmel (478 ticker)

| Field | Açıklama | Dolu | Kapsama |
|---|---|---|---|
| 8 | Market Cap (mn TL) | 478/478 | %100 |
| 9 | Market Cap (mn USD) | 478/478 | %100 |
| 30 | Cari PD/DD (P/B) | 478/478 | %100 |
| 163 | Cari Net Nakit (mn TL) | 476/478 | %100 |
| 29 | Cari FD/FAVÖK (EV/EBITDA) | 471/478 | %99 |
| 388 | Yıllık Cari FAVÖK (EBITDA, mn TL) | 471/478 | %99 |

→ Kapsama **darboğaz değil**. ~478 ticker (BIST'in tamamına yakını) tüm value alanlarında dolu.

### Q3 — Geçmiş derinlik? ❌ YOK — snapshot-only (en kritik bulgu)

`getScreenerDataNEW` payload'ına 5 farklı tarih/dönem parametresi eklendi:

| Eklenen parametre | Sonuç |
|---|---|
| `tarih=31-12-2024` | THYAO MktCap **DEĞİŞMEDİ** (409515) — yok sayıldı |
| `donem=2024/12` | DEĞİŞMEDİ |
| `period=2024` | DEĞİŞMEDİ |
| `date=2024-12-31` | DEĞİŞMEDİ |
| `yil=2024` | DEĞİŞMEDİ |

→ Endpoint tarih parametresini **tamamen yok sayıyor**; her zaman bugünkü snapshot'ı döndürüyor. Repo kanıtıyla tutarlı (`isyatirim_scraper.py` sentetik-seed mantığı geçmiş veri yokluğunu telafi ediyor).

**Sonuç:** İş Yatırım screener Faz 0b'nin gerektirdiği 2024-01→2026-04 aylık geçmiş USD değerlemesini **veremez**. Snapshot dondurmak da geçmişi yaratmaz (geçmiş hiç yok). **"Yol A-USD" tarihsel IC için YEŞİL OLAMAZ.**

### Q4 — Alternatif: biz mi çevirelim? ✅ EVDS tarafı hazır, darboğaz TL fundamental

`fetch_series("TP.DK.USD.A", "01-01-2024", "30-04-2026")`:

| Metrik | Değer |
|---|---|
| Dönen gözlem | 584 günlük |
| Aralık | 2024-01-02 (29.44) → 2026-04-30 (44.99) |
| Çıkarılabilir ay-sonu kuru | 28 ay |
| Look-ahead | Yok — her dönem **kendi ay-sonu kuruyla** çevrilir |

Çevrim demo: 100,000 mn TL @ 2024-06 (kur 32.84) = 3,044.9 mn USD.

→ **EVDS tarafı %100 hazır** (RR-021 teyidi value bağlamında doğrulandı). USD'ye çevirmek trivial. **Tek eksik: geçmiş TL fundamental serisi** (defter değeri, EBITDA, net borç per ticker-dönem). Bu da bizi RR-032'ye geri götürür:
- **Yol B** (MKK VYK XBRL ≥2024) — dev gateway donuk (RR-033/D-179), prod token bekleniyor
- **yfinance** — geçmiş var ama nominal + accuracy şüpheli (RR-032 §3)
- TMS 29 sorusu (RR-033) hâlâ açık: TL fundamental TMS29-adjusted mı?

---

## Kavramsal Caveat — "USD baypas eder" neden kısmen yanlış

NRR-002 "USD-bazlı F/DD + EV/EBITDA" önerdi; bu doğru ama **mekanizma yanlış anlaşılmamalı**:

- **P/B ve EV/EBITDA birimsiz oranlardır.** USD'ye çevirmek = pay ve paydayı aynı kura bölmek → oran **aynı kalır**. Yani nominal-TL P/B = nominal-USD P/B, ve TMS29-TL P/B = TMS29-USD P/B. **USD çevrimi cross-sectional value sıralamasında nominal-vs-TMS29 farkını sadeleştirmez.**
- TMS 29 problemi **paydadaki defter değerinin reel mi nominal mi** olduğudur (yüksek maddi-varlık şirketlerinde nominal defter değeri reel özkaynağı eksik gösterir). USD'ye spot kurla çevirmek bu reel-vs-nominal farkını **korur** (sadece birim değişir).
- **USD'nin gerçek faydası:**
  1. **Absolute level'ın zaman-karşılaştırılabilirliği** — 2024 USD market cap ile 2026 USD market cap karşılaştırılabilir; TL'de enflasyon bozuyor.
  2. **USD-denominated getiri** (Faz 0b IC label tarafı) — reel/USD getiri NRR-002 tercihi.
  3. **EV/EBITDA'da EBITDA bir akış** (son 12 ay) → stok (defter değeri) kalemine göre tarihsel-maliyet birikiminden daha az etkilenir; bu, P/B'den çok EV/EBITDA'yı enflasyona dayanıklı kılar — ama bu **flow-vs-stock** meselesi, USD meselesi değil.

→ Yani value faktörünün TMS 29 kalite sorusu (RR-033) **USD ile çözülmez**; ayrı bir doğrulama olarak kalır. USD katmanı getiri/level karşılaştırması için gerekli, fundamental-kalite için yeterli değil.

---

## Öneri (DEC-039: önerir, seçmez)

| Bulgu | İşaret ettiği yol |
|---|---|
| İş Yatırım USD anlık + %99-100 kapsama | Anlık tarama / canlı sinyal için **kullanılabilir** (Faz 1+ live screening) |
| Snapshot-only, geçmiş yok | Faz 0b tarihsel IC için **İş Yatırım USD tek başına YETERSİZ** |
| EVDS geçmiş kur hazır | "Biz çeviririz" yolu **EVDS tarafından engellenmiyor** |
| Darboğaz = geçmiş TL fundamental | **RR-032 Yol B/C'ye dön**; MKK prod token veya yfinance kalite kararı kritik |
| Oran birimsizliği | USD, TMS 29 kalite sorusunu **çözmez** → RR-033 hâlâ koşturulmalı |

**Net öneri:** İş Yatırım USD screener'ı Faz 0b value faktörünün **tarihsel IC ölçümü için kullanma** (geçmiş yok). Bunun yerine:
1. Geçmiş TL fundamental kaynağını netleştir (MKK VYK prod token → Yol B, veya yfinance → kalite riski).
2. O TL fundamentalleri EVDS dönem-sonu kuruyla USD'ye çevir (altyapı hazır, trivial).
3. RR-033 TMS 29 testini prod MKK token gelince koştur (USD bunu baypas etmiyor).
4. İş Yatırım USD screener'ı **Faz 1+ canlı tarama** için sakla (anlık + tam kapsama orada değerli).

Karar maintainer'da.

---

## Kısıtlar

- Probe tek oturum (30 Mayıs 2026), throwaway — `scripts/_probe_isyat_usd.py`, `_probe_evds_usd_hist.py` (commit edilmedi, silindi).
- İş Yatırım "Cari" alanları = son filed dönem (muhtemelen 2024 yıllık / son çeyrek); hangi spesifik dönem olduğu screener'da belirtilmiyor — bu da TMS29-adjusted mı sorusunu (RR-033) açık bırakıyor.
- Build/production değişiklik YOK. `src/` dokunulmadı.
