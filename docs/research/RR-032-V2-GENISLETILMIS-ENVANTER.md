# RR-032-V2 — BIST Fundamental Veri Kaynakları: Genişletilmiş Envanter

**Tarih:** 30 Mayıs 2026
**Yazar:** Claude Code (Builder) — web research + canlı probe (throwaway)
**Status:** ⏳ Karar bekliyor (value veri kaynağı — the project, DEC-039)
**Bağlı:** [RR-032](RR-032-FIZIBILITE.md) (genişletir, yerini ALMAZ); [RR-033](RR-033-isyatirim-tms29-uyum-testi.md); [RR-034](RR-034-isyatirim-usd-feasibility.md); [RR-020](RR-020-BIST-VERISI-MAP.md); NRR-002

---

## TL;DR — En önemli 4 bulgu

1. **TradingView (tradingview-screener)** = en güçlü ÜCRETSİZ programatik bulgu: 600 BIST hissesi, P/B + EV/EBITDA + market cap + F/K, resmi scanner endpoint (scrape değil, key yok). Canlı doğrulandı + İş Yatırım'la birebir eşleşti (THYAO P/B 0.447, mktcap 409,515 mn). **AMA anlık snapshot** — İş Yatırım gibi geçmiş yok.
2. **Matriks IQ Pro (retail, ~3K TL/ay) fundamental data API SAĞLAMIYOR.** Programatik tek arayüz `MatriksIQ/ApiClient` = C# **emir-giriş** (order-entry), fundamental yok. Abonelik almak value sorununu ÇÖZMÜYOR. Programatik fundamental ancak ayrı **kurumsal veri servisi** sözleşmesiyle (custom fiyat, contact-form, enterprise) — retail sub'a dahil değil.
3. **investpy ÖLÜ** (Investing.com Cloudflare V2 → 403). Alternatif investiny sadece fiyat+arama, **fundamental YOK**. Investing.com programatik fundamental = ✗.
4. **Geçmiş derinlik herkesi vuruyor:** Ücretsiz/ucuz programatik kaynakların hepsi (TradingView, İş Yatırım, Türk portallar, Google) **anlık snapshot**. Faz 0b 24-ay IC için geçmiş UFRS fundamental hâlâ ya **MKK VYK** (≥2024, prod token bekliyor) ya **yfinance** (nominal) ya da **ücretli EODHD trial** (doğrulanmalı) ile gelir.

> **RR-032 zaten kapsadı** (tekrarlanmaz): MKK VYK, yfinance, İş Yatırım screener, Fintables, Borsa MCP, Matriks Kurumsal REST, Finnet, TradingEconomics, EVDS, KAP scrape, FMP/Finnhub/AV (o zaman "belirsiz"). **V2 deltası:** atlanan ücretsiz kanallar (Google, Investing/investpy, TradingView, Türk portallar, Datastore) + FMP/Finnhub/AV/EODHD KESIN cevap + Matriks IQ Pro retail-sub fundamental sorusu + enterprise (Refinitiv/FactSet/CapIQ).

---

## Büyük Karşılaştırma Tablosu

Sütunlar: **MktCap** / **EBITDA** / **NetBorç** / **DefterDeğ** (5. ham veri USD kuru = EVDS, hepsinde ortak, RR-021). **Hist** = geçmiş derinlik. **UFRS/TMS29**. **Erişim+Fiyat**. **Programatik**.

| # | Kaynak | MktCap | EBITDA | NetBorç | DefterDeğ | Hist (geçmiş) | UFRS/TMS29 | Erişim + Fiyat | Programatik | Entegrasyon |
|---|---|:---:|:---:|:---:|:---:|---|---|---|---|---|
| 1 | **Google Finance/Sheets** | ✓ (mktcap) | ✗ | ✗ | ✗ | sınırlı | n/a (oran yok) | Ücretsiz | GOOGLEFINANCE: sadece `pe`,`eps` — P/B,EV/EBITDA,EBITDA,defter **YOK**; "intl borsa desteklenmez" → BIST güvenilmez | ✗ value için |
| 2 | **Investing.com / investpy** | — | — | — | — | — | — | Ücretsiz | **investpy ÖLÜ** (Cloudflare 403); investiny = fiyat+arama, fundamental yok | ✗ |
| 3 | **★ TradingView** (tradingview-screener) | ✓ | ✓ (EV/EBITDA) | ◐ (türev) | ✓ (P/B) | ❌ **anlık snapshot** | ⚠️ TV hesaplıyor (kaynak belirsiz; muhtemel nominal/karma) | **Ücretsiz**, key yok | ✓✓ resmi scanner API (pip `tradingview-screener`), 600 BIST hisse | **çok düşük** (canlı kanıtlandı) |
| 4 | **Türk portallar** (Mynet/BloombergHT/ParaAnaliz) | ✓ | ◐ | ◐ | ✓ (PD/DD,F/K) | ❌ anlık | ⚠️ belirsiz | Ücretsiz | Sadece HTML-scrape; resmi API yok; BloombergHT ToS dağıtımı yasaklıyor | yüksek (fragile, TradingView'den aşağı) |
| 5 | **Borsa İstanbul Datastore** | ? | ? | ? | ? | resmi (lisanslı) | resmi kaynak | **Lisans-gated** (auth, public fiyat yok; D-130 SPA) | Auth-walled; fundamental ürün belirsiz, enterprise yönelimli | yüksek; bireysel pratik değil |
| 6 | **★ Matriks IQ Pro** (retail ~3K TL/ay) | UI'da ✓ | UI'da ✓ | UI'da ✓ | UI'da ✓ | UI'da var | terminal gösterir | ~3K TL/ay | ❌ **Fundamental API YOK** — ApiClient sadece emir-giriş (C#) | — (API yolu yok) |
| 6b | Matriks **Kurumsal** veri servisi | ✓? | ✓? | ✓? | ✓? | ? | ? | **Custom** (contact-form, enterprise) | REST/MQTT; fundamental kapsamı dokümante değil, teklif gerek | orta; kurumsal sözleşme |
| 7 | **EODHD Fundamental API** | ✓ | ✓ | ✓ | ✓ | ✓ (30 yıl iddia) | ⚠️ doğrulanmalı (trial) | **€59.99/ay** (free=US only) | ✓ REST/JSON; 70+ borsa, Istanbul (XIST) listede | düşük (REST) |
| 8a | **Finnhub** | ✓ | ✓ | ✓ | ✓ | ✓ | ⚠️ belirsiz | **Premium $11.99-99.99/ay** (free=US only) | ✓ REST; intl fundamental premium-gated | düşük |
| 8b | **FMP** | ✓(genel) | ✓ | ✓ | ✓ | ✓ | ⚠️ | Freemium | Dokümante borsalar: NYSE/NASDAQ/AMEX/EURONEXT/TSX — **BIST listede YOK** → BIST fundamental yok/minimal | ✗/düşük |
| 8c | **Alpha Vantage** | ◐ | ◐ | ◐ | ◐ | ABD odaklı | ✗ intl | Freemium | OVERVIEW ABD-merkezli; non-US fundamental esasen **yok** | ✗ |
| 9 | **Refinitiv/LSEG · FactSet · S&P CapIQ** | ✓ | ✓ | ✓ | ✓ | ✓ derin | ✓ pro | **Enterprise** ($10K-25K+/yıl); bireysel/küçük erişim **YOK** | ✓ ama kurumsal sözleşme | yüksek; ölçek dışı |

✓=var · ◐=kısmi/türev · ✗=yok · ⚠=doğrulanmalı

---

## Kaynak Kaynak NET Cevaplar

### 1. Google Finance / Sheets — ✗ value için yetersiz
`GOOGLEFINANCE()` desteklenen fundamental attribute = sadece `pe` ve `eps`. **P/B, EV/EBITDA, EBITDA, defter değeri YOK** (resmi Google docs). Ayrıca "most international exchanges desteklenmez" → BIST güvenilmez. Anlık market cap dışında value için kullanılamaz. **Programatik:** Sheets API ile çekilebilir ama veri içeriği zaten yetersiz.

### 2. Investing.com / investpy — ✗ ölü kanal
**investpy artık çalışmıyor** — Investing.com API'lerini Cloudflare V2 ile korudu, HTTP 403 (GitHub issue #611, resmi). Yazar "geçici" alternatif **investiny** yaptı ama o sadece tarihsel **fiyat + sembol arama** veriyor — **fundamental, oran, EV/EBITDA YOK**. Investing.com'dan programatik fundamental = imkansız (ToS + Cloudflare).

### 3. ★ TradingView — ✓✓ ÜCRETSİZ programatik, ama anlık
**Canlı kanıtlandı:** `tradingview-screener` (pip, key yok) `Query().set_markets("turkey")` → **600 BIST hissesi**, alanlar: `market_cap_basic`, `price_book_ratio`, `enterprise_value_ebitda_ttm`, `price_earnings_ttm`. Resmi scanner endpoint (HTML scrape değil). Çapraz doğrulama: THYAO P/B 0.447 / mktcap 409,515 mn, TUPRS mktcap 455,109 mn — **İş Yatırım değerleriyle birebir**. P/B 15/15 dolu, EV/EBITDA 9/15 (bankalar hariç — doğru). **KISIT:** anlık snapshot (geçmiş time-series screener'dan gelmiyor) → İş Yatırım gibi Faz 0b 24-ay panelini **tek başına besleyemez**. ToS gri (scanner endpoint kişisel kullanım). **En iyi ücretsiz canlı tarama kaynağı (Faz 1+) + cross-validation.**

### 4. Türk portallar (Mynet/BloombergHT/ParaAnaliz) — ◐ scrape-only, TradingView'den aşağı
Mynet Finans hisse sayfaları F/K + PD/DD gösteriyor (BeautifulSoup ile çekilebilir). BloombergHT veri dağıtımını ToS ile **yasaklıyor**. Hepsi anlık snapshot, resmi API yok, HTML-fragile. TradingView (resmi API, 600 hisse, temiz) bunların hepsinden üstün → **scrape fallback'i gereksiz**. Ayrı scrape probe çalıştırılmadı (anlık-only oldukları için TradingView ile fonksiyonel olarak özdeş, daha kırılgan).

### 5. Borsa İstanbul Datastore — ⚠️ lisans-gated, bireysel pratik değil
datastore.borsaistanbul.com resmi borsa veri ürünü (D-130'da Ember.js SPA, x-auth-token auth-walled olarak görüldü). Public fiyat yok; veri lisansı/abonelik gerektiriyor. Fundamental ürün kapsamı net değil — esas olarak fiyat/referans/endeks verisi; şirket-finansal verisi enterprise lisans gerektirir. Bireysel programatik value pipeline için pratik değil.

### 6. ★ Matriks IQ Pro — retail abonelik fundamental API VERMİYOR (kritik)
Kullanıcının öncelikli sorusu. **Net cevap: HAYIR.**
- `MatriksIQ/ApiClient` (GitHub, %100 C#) = "Dışarıdan Emir Kabul API'si" — **sadece emir gönderme/düzeltme**, fundamental veri yok.
- IQ Pro terminali UI'da F/K, PD/DD vb. gösteriyor ama bunlara **programatik erişim yolu yok** (ApiClient order-entry ile sınırlı).
- → ~3K TL/ay IQ Pro aboneliği **fundamental data API açmıyor**; "Matriks YEŞİL" senaryosu retail sub ile **gerçekleşmiyor**.
- **Tek Matriks programatik fundamental yolu:** ayrı **Kurumsal Veri ve İçerik Sağlayıcı Servisi** (REST/MQTT) — fakat custom-fiyatlı, contact-form ile teklif, AKD/takas+fiyat dokümante (fundamental kapsamı belirsiz), enterprise yönelimli. RR-032 §3'te zaten "Matriks Kurumsal REST" olarak vardı.
- matriks.ai "API for AI" (yeni): REST/JSON + SDK ama fiyat "Coming Soon", fundamental veri exposure'ı doğrulanmadı.

### 7. EODHD — ✓ ücretli ama umut verici (trial doğrulamalı)
Fundamentals Data Feed **€59.99/ay** (All-in-One €99.99). 70+ borsa, public exchange listesinde Istanbul (XIST/IS) var. Free tier sadece ABD. REST/JSON, 30 yıl tarihsel iddia. **Doğrulanması gereken tek şey:** BIST fundamental **geçmiş derinliği + TMS 29 durumu** (1 günlük trial key ile). Eğer BIST'te 24-ay UFRS fundamental veriyorsa → **Faz 0b için ücretli ama temiz çözüm** (MKK prod token beklemeye alternatif). Demo key BIST'e kapalı (403), trial gerek.

### 8. Finnhub / FMP / Alpha Vantage — KESIN cevap (RR-032 "belirsiz" kapatıldı)
- **Finnhub:** free = ABD; **uluslararası hisse + detaylı finansallar = Premium ($11.99-99.99/ay)**. BIST fundamental teknik olarak premium'da var ama TMS 29 durumu belirsiz; ücretli.
- **FMP:** dokümante borsalar NYSE/NASDAQ/AMEX/EURONEXT/TSX — **BIST listede yok**. BIST fundamental kapsaması yok/minimal → value için ✗.
- **Alpha Vantage:** OVERVIEW ABD-merkezli; non-US fundamental esasen desteklenmiyor → BIST ✗.
- (Demo key'lerle canlı probe denendi: FMP/Finnhub 401, AV demo IBM-only, EODHD 403 — yani hiçbiri anonim/ücretsiz BIST fundamental vermiyor; cevaplar resmi dokümantasyon + fiyat sayfalarından kesinleştirildi.)

### 9. Refinitiv/LSEG · FactSet · S&P Capital IQ — ✗ bireysel erişim yok
Üçü de enterprise data sağlayıcı; minimum sözleşmeler $10K-25K+/yıl, kurumsal onboarding. **Bireysel veya küçük-ölçek erişim yok.** BIST kapsaması mükemmel ama ölçek/fiyat tamamen kapsam dışı. Tamlık için listelendi; aday değil.

---

## Güncellenmiş Value-Kaynak Önerisi (DEC-039: önerir, seçmez)

**Geçmiş derinlik ekseni belirleyici** (Faz 0b = 2024-01→2026-04 aylık IC paneli):

| Kategori | Kaynaklar | Faz 0b tarihsel IC | Faz 1+ canlı tarama |
|---|---|---|---|
| **Ücretsiz + anlık** | TradingView ✓✓, İş Yatırım ✓ | ❌ geçmiş yok | ✅ **en iyi** (TradingView 600 hisse, temiz API) |
| **Ücretsiz + geçmiş + nominal** | yfinance | ◐ var ama nominal/şüpheli | ◐ |
| **Geçmiş + UFRS-TMS29** | MKK VYK (≥2024) | ✓ ama prod token bekliyor + ≥2024 kısıtı | — |
| **Ücretli + geçmiş** | EODHD €59.99/ay | ⚠️ trial ile doğrula (umut verici) | ✓ |
| **Çözmüyor** | Matriks IQ Pro retail, Google, investpy, FMP, AV, Türk portallar, enterprise | ✗ | kısmi |

**Net öneri:**
1. **Faz 0b tarihsel IC için:** Birincil aday hâlâ **MKK VYK** (UFRS-TMS29, prod token gelince) + RR-033 TMS 29 testi. **Yeni güçlü ücretli alternatif: EODHD €59.99/ay** — 1 günlük trial ile BIST fundamental geçmiş derinliği + TMS 29 durumu doğrulanmalı; çıkarsa MKK beklemeye gerek kalmadan temiz çözüm.
2. **Faz 1+ canlı tarama için:** **TradingView (tradingview-screener)** — ücretsiz, programatik, 600 BIST, P/B+EV/EBITDA+mktcap; İş Yatırım'a tercih edilir (daha temiz API, daha geniş). İkisi cross-validation için birlikte.
3. **Matriks:** Retail IQ Pro aboneliği value için **alma** (fundamental API yok). Sadece Kurumsal veri servisi teklifi anlamlı olabilir ama EODHD muhtemelen daha ucuz + dokümante.
4. **Eleme:** Google Sheets, investpy, FMP, Alpha Vantage, Türk portal scrape, enterprise sağlayıcılar — value faktörü için aday değil.

**Kalan tek "doğrula" noktası (dürüst):** EODHD'nin BIST fundamental geçmiş derinliği + TMS 29 durumu — trial key gerektirir (hesap açma kullanıcı onayı ister). Diğer tüm sorulara kesin cevap verildi.

---

## Kısıtlar

- Probe'lar tek oturum (30 May 2026), throwaway (`scripts/_probe_fundamentals_apis.py`, `_probe_tradingview.py` — silindi). `tradingview-screener` pip ile kuruldu (probe için; üretim bağımlılığı eklenmedi).
- FMP/Finnhub/AV/EODHD canlı BIST testi demo-key kapalı olduğu için yapılamadı; cevaplar resmi dokümantasyon + fiyat sayfalarından (kesin: tier/fiyat/kapsama).
- TradingView/Türk portal/İş Yatırım fundamental'lerinin TMS 29 durumu doğrulanmadı (RR-033 açık; bu kaynaklar için de geçerli — anlık oranlar UFRS mı nominal mi belirsiz).
- Build/production değişiklik YOK. `src/` dokunulmadı.
