# RR-031 — KAP Next.js Migration: Scraping Infeasibility

**Tarih:** 28 Mayıs 2026
**Araştıran:** Claude Code (Builder)
**Durum:** ✅ Applied → `kap_scraper.py` Google RSS fallback teyit edildi
**Bağlı CB/SPEC:** — (D-170 MKK VYK API kanalı önerisi)

---

## §1 Bulgu

`kap.org.tr` eski asp/servlet arayüzünden **Next.js + WAF** mimarisine geçti.
Tarihsel scraping hedefi olan `memberDisclosureQuery` endpoint'i artık programatik
erişime kapalı: doğrudan HTTP istekleri bot-koruması tarafından engelleniyor,
JSON yerine challenge sayfası veya hata kodu dönüyor. Endpoint **ölü** kabul edilmeli.

---

## §2 Kanıt

| Belirti | Gözlem | Yorum |
|---------|--------|-------|
| **Tarpit timeout** | İstek askıda kalıyor, yanıt gelmiyor (connection hang) | WAF kasıtlı yavaşlatma (slow-loris karşıtı tarpit) |
| **HTTP 666** | Standart-dışı durum kodu | Bot algılandığında WAF'ın özel red sinyali |
| **HTTP 429** | Too Many Requests — düşük istek hacminde bile | IP-bazlı rate-limit; insan-dışı trafik fingerprint'i |

Üç belirti birlikte: endpoint canlı veri için **güvenilemez**. Retry/backoff ile
aşılamaz — bu bir rate-limit değil, mimari engel.

---

## §3 Sonuç

`src/data/kap_scraper.py` **Google News RSS fallback** kanalında kalmalıdır.
Doğrudan `kap.org.tr` endpoint'ine geçiş denemesi yapılmamalı — yatırım getirisi
sıfır, kırılganlık yüksek. Mevcut RSS tabanlı akış operasyonel; KAP açıklama
başlıkları RSS üzerinden kategorize edilmeye devam eder.

---

## §4 Alternatif — MKK VYK API (D-170, YEŞİL kanal)

Yapısal/güvenilir KAP verisi için resmi kanal: **MKK Veri ve Yatırımcı Kanalı
(VYK) API**. Next.js WAF'ı bypass etmeye çalışmak yerine yetkili API kullanılır.

- **Durum:** YEŞİL — resmi, ToS-uyumlu, rate-limit öngörülebilir
- **Spec:** D-170 olarak açılmalı (KAP scraper → MKK VYK API migration)
- **Kapsam:** finansal_rapor `kap_text` pipeline'ı (D-158 Faz 2 backtest açığını da kapatır)

---

## §5 Karar

| Soru | Cevap |
|------|-------|
| `kap.org.tr` endpoint scrape edilsin mi? | ❌ Hayır — ölü (WAF) |
| Mevcut RSS fallback korunsun mu? | ✅ Evet — operasyonel |
| Yapısal veri için yol? | ✅ MKK VYK API (D-170, YEŞİL) |

**Risk:** Yok. Mevcut davranış değişmiyor; bu rapor yalnızca `kap.org.tr`
doğrudan-scrape opsiyonunu kalıcı olarak kapatıp D-170'i işaret ediyor.

---

## Kaynaklar

- Canlı test: `kap.org.tr/tr/bist-sirketler` → Next.js `__NEXT_DATA__` hydration, API çağrıları WAF arkasında
- `memberDisclosureQuery` doğrudan istek → tarpit / HTTP 666 / HTTP 429
- Proje içi: `src/data/kap_scraper.py` (Google RSS fallback), `docs/features/KAP_LAYER.md` (D-158)
