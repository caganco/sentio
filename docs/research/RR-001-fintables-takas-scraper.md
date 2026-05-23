# BIST Takas/Saklama Verisi ile Smart Money Sinyal Üretimi — Kapsamlı Araştırma Raporu

## TL;DR

- **MKK hisse-bazında günlük takas verisi açık API ile değil, lisanslı veri dağıtıcıları (BIST Düzey 2+) üzerinden geliyor; ücretsiz erişim aylık PDF bültenle sınırlı.** Hisse-seviyesinde günlük yabancı oranı için pratik tek yol İş Yatırım "Günlük Yabancı Oranları" raporu ve `arastirma.isyatirim.com.tr` JSON endpoint'i (resmi olmayan, scraping ile, "yalnızca kişisel kullanım" ToS notlu).
- **Akademik literatür "ownership (sahiplik seviyesi)" sinyalinin "flow (akış)" sinyalinden daha iyi alpha ürettiğini gösteriyor; Türkiye için Ülkü & İkizlerli (2012) net foreign flow'un piyasa-düzeyinde negatif feedback trade edildiğini, bu yüzden L2 (Macro) katmanına ait olduğunu doğruluyor.** Smart money sinyali olarak ownership seviyesi + 30-gün değişimi + 10-gün persistence + TEFAS hisse-yoğun fon allocation proxy kombinasyonu önerilir.
- **1 hafta tek geliştirici ile MKK scraper + L5 yeniden mimarisi yapılabilirlik skoru: 6/10 (önerilen 2 hafta + MVP scope ile 8/10).** Pratik scraping yolu (İş Yatırım JSON, TEFAS API, KAP) çalışıyor; ancak hisse-bazlı "saklayıcı kurum sayısı" gibi en zengin metrikler ücretli veri dağıtıcıları arkasındadır.

---

## BÖLÜM 1: VERİ KAYNAKLARI

### A. MKK (Merkezi Kayıt Kuruluşu)

**Erişilebilir Ücretsiz Veri**

1. **MKK Aylık Piyasa Bülteni** — PDF formatında, ay sonları itibarıyla güncellenir. URL: `https://www.mkk.com.tr/veri-hizmetleri/mkk-aylik-piyasa-bulteni`. Erişim ücretsiz, login gereksiz. Dosya pattern'i: `MKK-Aylik-Piyasa-Bulteni-{Ay}-{Yıl}.pdf` (Mayıs 2026 itibarıyla Nisan 2026 bülteni mevcut). İçerik: toplam bakiyeli yatırımcı sayısı, yerli/yabancı dağılım, portföy büyüklüğü, endeks bazlı kırılımlar.
2. **Kaydi Sistem İstatistikleri** — `https://www.mkk.com.tr/veri-hizmetleri/kaydi-sistem-istatistikleri`. Hesap/yatırımcı sayısı aylık trend.
3. **Borsa Trendleri Raporu** — `https://www.mkk.com.tr/veri-hizmetleri/borsa-trendleri-raporu`. Halka açık şirketlerin piyasa değeri, fiili dolaşım oranları, yerli/yabancı saklama dağılımı, risk iştahı endeksi.

**Ücretli/Lisanslı (Hisse-Bazında Günlük Veri)**

Hisse bazında günlük yabancı saklama oranı, kurumsal/bireysel ayrım, saklayıcı kurum sayısı verileri **MKK'nın 2013 duyurusu (No. 631)** ile 10 iş günü gecikmeli kamuya açıklama uygulaması durdurulmuştur. MKK'nın resmi duyurusu (TR sayfası `https://www.mkk.com.tr/tr/duyuru/631`): *"e-MKK Bilgi Portalı'nda günlük olarak yayınlanan 'Yerli Yabancı Saklama Oranları' 01.01.2013 tarihinden itibaren 10 iş günü gecikmeli olarak yayınlanacaktır. Güncel veriler, Kuruluşumuz ile veri dağıtım sözleşmesi imzalamış olan veri yayın kuruluşlarından temin edilebilir."*

→ **Hisse bazında güncel takas verisi MKK'dan doğrudan ücretsiz alınamıyor; veri dağıtıcı (data vendor) sözleşmesi gerekiyor.**

**PUSULA Platformu** (`https://www.mkk.com.tr/veri-hizmetleri/pusula`) — yalnızca aracı kurum üyelerine açık, ücretli üyelik sözleşmesi gerektirir; veriler günlük/aylık iki frekansta, ülke/bölge ve il bazında kırılım sunar; Excel ve PDF formatında ihraç edilir.

**VAP (Veri Analiz Platformu)** — `https://www.vap.org.tr/` — kurumsal yönetim/finansal oran verileri; takas özelinde değil.

**MKK API Portal** — `https://apiportal.mkk.com.tr/` — üyelik gerektiren API; retail kullanıma yönelik değil.

### B. Borsa İstanbul Yabancı İşlem Verisi

`https://www.borsaistanbul.com/veriler/veri-yayini/veri-yayin-urunleri` veri yayın ürünleri sayfasında tanımlanan seriler:
- **Aylık**: "yabancı banka/aracı kurum veya şahıs nam ve hesabına gerçekleştirilen işlemler", müşteri/fon/portföy işlemleri, üye bazında işlem dağılımı, açığa satış işlemleri
- **Haftalık**: En aktif 20 pay ve 20 üye, değerleme oranları, üye bazında işlem hacimleri
- **Günlük (Düzey 2+ paketinde)**: "Üye Bazında Saklama Bakiyeleri, Yerli Yabancı Saklama Bilgileri, Fiili Dolaşımda Bulunan Paylar Raporu, Saklamada Bireysel/Kurumsal Yatırımcı Oranı, Pay Senedi Bazında Yatırımcı Sayısı" — Akbank veri yayın paketleri sayfasında bu kapsam doğrulanır (`https://www.akbank.com/mevduat-yatirim/yatirim/hisse-senedi/veri-yayin-paketleri`).

→ **BİST'in günlük yerli/yabancı saklama verisi ücretli Düzey 2+ paketinin parçasıdır; lisans gerektirir.** Açık veri yalnızca aylık aggregate seviyede mevcut.

**datastore.borsaistanbul.com** — bülten verileri (OHLCV, hacim) CSV/ZIP indirme; takas verisi içermez.

### C. TEFAS

URL: `https://www.tefas.gov.tr/`. **Resmi olmayan ama public, ücretsiz JSON endpoint'leri mevcut**:
- `https://www.tefas.gov.tr/api/funds/fonGnlBlgSiraliGetir` — fon fiyat/büyüklük/yatırımcı sayısı
- `https://www.tefas.gov.tr/api/funds/dagilimSiraliGetirT` — fon portföy dağılımı (50+ varlık kalemi: hisse, repo, eurobond, kıymetli madenler vb.)

Doğrulayan Python kütüphaneleri: **pytefas** (`https://github.com/mirzazad/pytefas` — modern, yeni endpoint'leri kullanır), **tefas-crawler**, **borsapy** içindeki TEFAS modülü, **eneshenderson/Tefas-API** (çoklu dil desteği).

**Fon bazında BIST hisse pozisyonları** — TEFAS portföy dağılımında aggregate "hisse senedi" oranı açıkça yer alır; ancak hangi spesifik BIST hisseleri tutulduğu TEFAS'tan değil, **KAP üzerinden fonun "Portföy Dağılım Raporu"**ndan (PDF/XBRL) alınır. SPK Tebliği VII-128.4 kapsamında çeyreklik portföy dağılım raporları KAP'a iletilir.

Tarihsel derinlik: Çoğu Python kütüphanesinde günlük veri ~5 yıla kadar geriye gider; Kaggle'da 5-yıllık historical fund amount dataset mevcut (`https://www.kaggle.com/datasets/onurcete/tefas-historic-fund-amounts`).

### D. SPK / KAP

**KAP (`https://www.kap.org.tr/`)** — XBRL altyapısı kullanır; şirket bildirimleri (özel durum, finansal raporlar, fon portföy dağılım raporları, ortaklık yapısı değişiklikleri) ücretsiz erişilebilir. MKK 2013'te KAP'ı Borsa İstanbul'dan devraldı. KAP veri yayın servisi ve SWIFT entegrasyonu kurumsal kanaldır; retail için web scraping pratiktir.

Doğrulanmış Python kütüphaneleri:
- **pykap** (`https://github.com/cemsinano/pykap`) — finansal raporlar, faaliyet raporları (FAR), kurumsal yönetim uyum raporları (KYUR), sürdürülebilirlik (SUR), temettü politikası (KDP) erişimi
- **KAP_Notifications** (`https://github.com/alperaydyn/KAP_Notifications`) — bildirim bazlı tarama
- **KAP_Scraper** (`https://github.com/Caglarsonmez/KAP_Scraper`) — şirket listesi taraması

Tilburg Üniversitesi 2025 tezi (`http://arno.uvt.nl/show.cgi?fid=187964`): *"the ChromeDriver navigates KAP's dynamic JavaScript-rendered interface through company-specific disclosure URLs"* — şirket detay sayfaları için Selenium gerekebilir, ancak bildirim listesi tablosu statik HTML.

**SPK Bültenleri** — `https://www.spk.gov.tr/` üzerinden aylık bültenler PDF; hisse bazında takas verisi içermez.

### E. Pratik Yan Kaynak — İş Yatırım (Resmi Olmayan)

Hisse bazında **günlük yabancı oranı** verisinin ücretsiz kaynağı olarak en pratik yol:

**arastirma.isyatirim.com.tr** "Günlük Yabancı Oranları" raporu (`https://arastirma.isyatirim.com.tr/category/gunluk-raporlar/gunluk-yabanci-oranlari/`) — hisse bazında günlük artış/azalış (basis points), 10-günlük sürekli artış/düşüş listeleri (örn. 21/05/2026 raporu: *"DAPGM:5.55 bps, TURSG:5.09 bps, EKOS:1.57 bps artış... TUCLK:-2.85 bps, CEOEM:-2.39 bps, EFOR:-1.99 bps düşüş"*).

**JSON endpoint örneği** (urazakgul/veri-kaynaklari-python ve isyatirimhisse paketinde doğrulanmış):
```
https://www.isyatirim.com.tr/_layouts/15/Isyatirim.Website/Common/Data.aspx/HisseTekil?
hisse={TICKER}&startdate={DD-MM-YYYY}&enddate={DD-MM-YYYY}.json
```

**borsapy** kütüphanesi (`https://github.com/saidsurucu/borsapy`) `fast_info["foreign_ratio"]` alanı ile yabancı oranını sunar — kaynak: İş Yatırım.

**Önemli not:** isyatirimhisse PyPI sayfasındaki resmi uyarı (kütüphane geliştiricisinin notu): kütüphane *"yalnızca kişisel kullanım amaçları için tasarlanmıştır"*, aşırı talep web sitesi performansını etkileyebilir. **Scraping legaldir ama rate-limit'e duyarlı; commercial-grade kullanımda ToS sorunu çıkabilir.**

### Erişim Özet Tablosu

| Kaynak | Format | Frekans | Tarihsel Derinlik | Erişim | Scraping Engeli |
|---|---|---|---|---|---|
| MKK Aylık Bülten | PDF | Aylık | 2025+ ana sayfada, eskileri arşivde | Ücretsiz | Yok (statik link) |
| MKK Borsa Trendleri | PDF | Çeyreklik/yıllık | Çoklu yıl | Ücretsiz | Yok |
| MKK e-VERİ/PUSULA | Excel/PDF | Günlük/aylık | — | Üye + ücretli | Login wall |
| BİST Düzey 2+ Veri Yayını | Vendor feed | Günlük | — | Lisanslı (vendor) | Lisans gerekir |
| BİST Datastore (bülten) | CSV/ZIP | Günlük | 2015-12-01'den | Ücretsiz | Yok |
| TEFAS API | JSON | Günlük | ~5 yıl | Ücretsiz (resmi olmayan) | Bazı sayfalar JS-render |
| KAP | HTML/PDF/XBRL | Anlık | Tam arşiv (2009+) | Ücretsiz | JS-render (Selenium gerekebilir) |
| İş Yatırım JSON | JSON | Günlük | Çoklu yıl | Ücretsiz (gri zon) | Rate limit, "kişisel kullanım" |

---

## BÖLÜM 2: AKADEMİK TEMEL

### A. Ülkü & İkizlerli (2012): Türkiye-Spesifik Bulgular

**Künye**: Ülkü, N. & İkizlerli, D. (2012). "The interaction between foreigners' trading and emerging stock returns: Evidence from Turkey." *Emerging Markets Review* 13(4), 381–409. URL: `https://www.sciencedirect.com/science/article/abs/pii/S1566014112000283`. (DOI muhtemelen 10.1016/j.ememar.2012.09.001; ScienceDirect robots.txt nedeniyle doğrudan doğrulanamadı.)

**Veri ve Metodoloji** (ScienceDirect abstract verbatim): *"Using monthly foreign flows data on Istanbul Stock Exchange (ISE) and employing a structural VAR model, we analyze the interaction between foreigners' trading and emerging stock returns."* Ülkü'nün OTKA K 81343 projesi kapanış raporuna göre (`https://core.ac.uk/download/pdf/20327386.pdf`, s.12) örneklem: **Ocak 1997 – Eylül 2010 (n=165), Kaynak: ISE**.

**Temel Bulgu 1 — Negatif Feedback Trading (aylık)**: Yabancı yatırımcı Türkiye'de aylık frekansta negatif feedback yapar — fiyat yükselince satar; düşünce ise her zaman almaz. OTKA raporu (s.2) verbatim: *"Foreign investors do engage in positive feedback trading at the daily frequency, but in negative feedback trading at the monthly frequency. This finding is uniform across many countries and geographies."* Asimetri: *"foreigners sell following rises, but not buy following falls — typically in economies with large external (or twin) deficits (Turkey, Hungary, Romania, Czech Republic, Spain ...)."*

**Temel Bulgu 2 — Sinyal Frekansı**: **Daily foreign flow ≠ monthly foreign flow** sinyali. Günlük: pozitif feedback (momentum), aylık: negatif feedback (kontra). Ülkü OTKA raporu (s.2): *"It is more likely that their trading follows rather than leads returns. It appears that what has been described in the extant literature as the contemporaneous price impact of foreign flows at the daily frequency may in fact be, to a large extent, foreigners responding to the same information which market prices already have adjusted (Ülkü and Weber, 2010)."*

**Temel Bulgu 3 — Permanent vs Temporary Price Impact**: Citing literature (ResearchGate citation excerpt): *"Ulku and Ikizlerli (2012) and Ulku (2016) show that negative feedback trading and permanent price impacts of foreign portfolio flows improve efficiency and restore stability of EMs."* Structural VAR impulse-response analizinde foreign flow şokunun kalıcı (permanent) bir bileşeni var.

**Market-Level vs Individual Stock**: 2012 makalesi aggregate ISE/BIST monthly flow analiz eder; individual stock-level analiz Ülkü & Weber (2010, "Bigger Fish in Small Pond") companion paper'a aittir. **Net foreign flow piyasa-düzeyinde (aggregate) anlamlıdır, individual stock seviyesinde aynı güçte değildir** — bu da L2 (Macro) katmanına taşımayı destekler.

### B. Ownership vs Flow Ayrımı

Bu ayrım smart-money sinyal kalitesi açısından kritiktir:

- **Flow (akış)** — kısa-vadeli alım-satım davranışı; Türkiye'de literatür flow'un piyasa-genelinde (macro) sinyal olduğunu, individual stock için noisy olduğunu gösteriyor.
- **Ownership (sahiplik seviyesi/değişimi)** — pozisyon stoku; "smart money" literatüründe daha güçlü alpha üreten metrik.

**S&P Global Market Intelligence raporu** "An IQ Test for the Smart Money" (`https://www.spglobal.com/content/dam/spglobal/mi/en/documents/general/An-IQ-Test-For-The-Smart-Money.pdf`) dört institutional ownership sinyal sınıfı tanımlar: **(1) Ownership Level, (2) Ownership Breadth, (3) Change in Ownership Level, (4) Ownership Dynamics**. Rapor bu sinyallerin fundamental ve teknik sinyallere tamamlayıcı olduğunu, *"statistically significant return spreads and Q1 active returns in Russell 3000 over our back test window"* ürettiğini belgeliyor.

**IHS Markit Research Signals** araştırması (Haziran 2021, `https://cdn.ihsmarkit.com/www/pdf/0621/Institutional_ownership_data_Quantitative_research_results.pdf`) verbatim: *"Value Momentum Analyst Model (VMA) overlay with 5% weights in three ownership factors — Top 10 Ownership Concentration, % Hedge Fund Holdings (Shares), and Changes in Active Shares Holdings — demonstrated additional monthly alpha of 9.1 bps (US Total Cap), 20.0 bps (Developed Europe), and 5.0 bps (Developed Pacific)."*

**Wu & Xu (2021, Journal of Portfolio Management forthcoming)** — AlphaArchitect özeti (`https://alphaarchitect.com/using-institutional-investors-trading-data-in-factors/`): *"enhanced anomaly-based strategies of buying stocks in the long legs of anomalies with entries and shorting stocks in the short legs with exits outperform the original anomalies, with an increase of 19–54 bps per month in the Fama–French five-factor alpha."*

### C. Emerging Market Karşılaştırmaları

**Korea** — Choe, Kho & Stulz (2005) *Review of Financial Studies* 18(3): 795-829 (`https://www.nber.org/papers/w10502`; SSRN ID 552107). SSRN abstract verbatim: *"foreign money managers pay more than domestic money managers when they buy and receive less when they sell for medium and large trades. The sample average daily trade-weighted disadvantage of foreign money managers is of 21 basis points for purchases and 16 basis points for sales."* → **Kore'de yabancı sophisticated görünmüyor**; medium/large trade'lerde yerli kurumsal daha iyi performans gösteriyor. Bu Ülkü & İkizlerli'nin negative feedback bulgusuyla tutarlıdır (yabancı flow "smart" değil rebalancing-driven).

**Indonesia** — Dvořák, T. (2005), *Journal of Finance* 60(2): 817–839 (DOI 10.1111/j.1540-6261.2005.00747.x), verbatim abstract: *"domestic investors have higher profits than foreign investors. Clients of global brokerages have higher long-term and smaller medium (intramonth) and short (intraday) term profits than clients of local brokerages."*

**Qin & Bai (2014, Int'l Review of Finance)** "Foreign Ownership Restriction and Momentum – Evidence from Emerging Markets" (`https://onlinelibrary.wiley.com/doi/10.1111/irfi.12019`): *"stocks fully investible for foreign investors exhibit stronger price momentum than non-investible stocks ... fully investible stocks have no post-earnings-announcement drift (PEAD)"* — yabancı yoğunluğu kısa-vade momentum'u güçlendirir, fundamental drift'i azaltır.

**Regime Conditioning** — Sungwoo Kang (Korea University ECE), "When the Rules Change: Adaptive Signal Extraction via Kalman Filtering and Markov-Switching Regimes," arXiv:2601.05716 (Şubat 2026): *"foreign investor predictive power increases several-fold during crisis periods relative to bull markets; individual investors chase momentum asymmetrically, reacting far more strongly to positive than to negative shocks."* → Foreign ownership sinyali regime-conditional ağırlandırma faydası gösterir.

### D. Sinyal Frekansı Önerisi

Literatür ittifakı:
- **Günlük foreign flow (raw)**: Türkiye için NEGATİF veya zayıf sinyal — özellikle individual stock seviyesinde.
- **Haftalık-aylık foreign flow**: Macro-level olarak market timing'de değerli; L5 (stock-picking) için değil **L2 (Macro)** katmanına ait.
- **Ownership level/change (aylık)**: Cross-sectional stock-picking için en güçlü.
- **Ownership breadth değişimi**: Yeni institutional entry/exit anomaly signal'larını güçlendirir.

→ **CB-007 bulgusu literatürce desteklenmektedir: net_foreign_flow L2'ye, foreign_ratio (ownership) ve değişimi L5'te kalmalıdır.**

---

## BÖLÜM 3: SCRAPING TEKNİK ANALİZİ

### A. MKK Sayfaları

**MKK Aylık Piyasa Bülteni** (`https://www.mkk.com.tr/veri-hizmetleri/mkk-aylik-piyasa-bulteni`):
- Statik HTML (Drupal CMS); PDF link'leri doğrudan `<a href="https://www.mkk.com.tr/sites/default/files/{YYYY-MM}/MKK-Aylik-Piyasa-Bulteni-{Ay}-{Yıl}.pdf">` pattern'iyle listelenir.
- `requests` + `BeautifulSoup` yeterli; Selenium gereksiz.
- robots.txt kısıtı görünmüyor; rate-limiting saldırgan değil ama ToS dikkate alınmalı.

**PDF tablo çıkarımı**: pdfplumber veya tabula-py ile aylık aggregate metrikler (yerli/yabancı yatırımcı sayısı, portföy büyüklüğü) çekilebilir. **Hisse bazlı veri PDF'de YOK.**

**e-VERİ ve PUSULA** — login wall arkasında; scraping pratiği yok.

### B. Borsa İstanbul

**Bülten verileri** — `datastore.borsaistanbul.com` 2015-12-01'den itibaren ZIP/CSV indirme; `requests` ile direkt; tarih bazlı URL pattern. Github örneği: `bombadilli/Borsa-Istanbul` repo'su bunu doğruluyor.

**Veri Yayın Paketleri sayfası** statik HTML; gerçek veri için lisanslı vendor gerekir.

### C. TEFAS

**Resmi JSON endpoint'leri** (pytefas tarafından doğrulanmış):
- `requests` yeterli; cookie/session gereksiz.
- Selenium yalnızca grafik veri (FonAnaliz sayfasındaki hover-based daily series) için gerekli.
- Rate-limit gevşek, ama abuse'a karşı korumalı.

### D. KAP

- `kap.org.tr` ana liste sayfaları (`/tr/bist-sirketler`) HTML statik.
- Şirket detay/disclosure sayfaları JavaScript ile render edilebilir; pykap ve KAP_Notifications repolarında bazı çağrılar Selenium/ChromeDriver kullanıyor.
- Tüm KAP bildirimleri arşivlenmiş, 2009+ açık.

### E. Genel Teknik Notlar

- **Tarihsel derinlik**: MKK bültenleri 2025+ ana sayfada, daha eskileri arşivde; BİST datastore 2015-12-01; TEFAS ~5 yıl; KAP tam arşiv; İş Yatırım JSON 2-5 yıl.
- **IP/User-Agent blocking**: İş Yatırım'ın "Please wait while your request is being verified..." sayfası (`https://arastirma.isyatirim.com.tr/...`) Cloudflare benzeri korumayı işaret ediyor. User-Agent rotation ve makul rate-limit (saniye başına 1-2 istek) önerilir.
- **Türkiye'de Web Scraping Hukuksal Statü**: Genel olarak public veriye erişim yasaldır; ancak ToS ihlali, KVKK (kişisel veri) ve telif hakları riskleri dikkate alınmalı. İş Yatırım kendi ToS'ünde "kişisel kullanım" sınırı koyuyor — ticari sistemde lisansa geçiş düşünülmeli.

---

## BÖLÜM 4: L5 SMART MONEY KATMANI YENİ MİMARİ ÖNERİSİ

### A. Takas Verisinden Çıkarılabilecek Yeni Sinyaller

Mevcut formül `foreign_ratio × 0.70 + short_interest × 0.30` static-snapshot bir ownership level kullanıyor — alpha potansiyeli sınırlı. Akademik literatür (S&P, IHS Markit, Wu & Xu) **dinamik ownership değişim** sinyallerinin daha güçlü olduğunu gösteriyor.

Önerilen 5 alt-sinyal:

1. **`foreign_ownership_level`** — Mevcut `foreign_ratio` (cross-sectional z-score ile normalize). Statik seviye; smart money konsantrasyonu proxy'si.
2. **`foreign_ownership_change_30d`** — Son 30 günde foreign_ratio değişimi (bps). İş Yatırım günlük serisinden hesaplanır. Pozitif değişim = institutional entry. Wu & Xu (2022) "changes in ownership breadth" literatürünce destekleniyor.
3. **`foreign_ownership_momentum_persistence`** — 10-gün üst üste artış/azalış sayısı (İş Yatırım raporları zaten "10 gün/9 gün sürekli artan" formatında yayınlıyor). Persistence faktörü S&P "Ownership Dynamics" sinyaline benzer.
4. **`short_interest_normalized`** — Mevcut short_interest, BİST açığa satış aylık serisinden (`https://www.borsaistanbul.com/veriler/veri-yayini/veri-yayin-urunleri`).
5. **`institutional_fund_holding_signal`** — TEFAS hisse-yoğun fonların aggregate hisse oranı değişimi (TEFAS API `dagilimSiraliGetirT` endpoint'i ile hisse-yoğun fonların hisse oranlarının ay-üzeri değişimi). Fon tarafından satın alınan/satılan stokların proxy'si.

**Erişilemeyen ama Ideal Sinyaller (Veri Engeli)**
- Hisse bazlı saklayıcı kurum sayısı zaman serisi (concentration metric) — MKK ücretli vendor verisi gerekir.
- Belirli kurumların pozisyon değişimleri — Türkiye'de 13F muadili yok; KAP'ta yalnızca %5+ pay sahibi açıklamaları (özel durum) mevcuttur, parça parça.

### B. Sinyal Kombinasyon Yaklaşımı

- **Cross-sectional z-score**: Her sinyal BIST 100/BIST 50 evren içinde z-score'a normalize edilsin (mean=0, std=1). Mutlak threshold yerine relative ranking, Türkiye'nin hızlı değişen makro/kur ortamında daha robust.
- **Dinamik ağırlık**: Statik weight başlangıç için yeterli; ileride regime-conditional weighting eklenebilir — Kang 2026 (arXiv:2601.05716) yabancı yatırımcı sinyal gücünün kriz dönemlerinde "several-fold" arttığını gösteriyor.
- **Skor normalize aralığı**: 0–100 (mevcut OS Trading System konvansiyonu varsayılır).

### C. Önerilen Yeni L5 Kompozisyonu (SPEC Taslağı)

```
L5_smart_money_score = (
    0.35 * foreign_ownership_change_30d_zscore +    # En güçlü alpha bileşeni (Wu & Xu, S&P)
    0.25 * foreign_ownership_level_zscore +          # Statik smart money konsantrasyonu
    0.15 * foreign_ownership_momentum_persistence +  # 10-gün persistence (S&P Ownership Dynamics)
    0.15 * short_interest_normalized_zscore +        # Mevcut sinyal (azaltılmış ağırlık)
    0.10 * institutional_fund_holding_signal         # TEFAS proxy (deneysel)
)
# Sigmoid ile 0-100 aralığına normalize
L5_final = 50 + 50 * tanh(L5_smart_money_score / 2)
```

**Gerekçe**: Akademik literatür **change > level** (Wu & Xu Q-J alpha 19-54 bps/ay; IHS Markit VMA overlay +9.1 ila +20.0 bps/ay); 0.35 + 0.25 = %60 ownership-tabanlı, %30 short interest + persistence (mevcut sistemden devamlılık), %10 fund holding (deneysel).

### D. Implementasyon Pseudo-Code

```python
# data_sources/mkk_scraper.py
import requests, pandas as pd, numpy as np, sqlite3
from bs4 import BeautifulSoup
import pdfplumber
from datetime import datetime

ISYATIRIM_BASE = "https://www.isyatirim.com.tr/_layouts/15/Isyatirim.Website/Common/Data.aspx"

def fetch_foreign_ratio_history(ticker: str, start: str, end: str) -> pd.DataFrame:
    """İş Yatırım JSON endpoint'inden hisse bazlı geçmiş yabancı oranı."""
    url = f"{ISYATIRIM_BASE}/HisseTekil?hisse={ticker}&startdate={start}&enddate={end}.json"
    r = requests.get(url, headers={"User-Agent": "OS-Trading/1.0"}, timeout=10)
    r.raise_for_status()
    return pd.DataFrame(r.json()["value"])

def fetch_mkk_monthly_bulletin(year_month: str) -> dict:
    """MKK aylık PDF bülteninden aggregate yerli/yabancı yatırımcı sayısı."""
    base = "https://www.mkk.com.tr/sites/default/files"
    # Pattern doğrulanmış: {YYYY-MM}/MKK-Aylik-Piyasa-Bulteni-{Ay}-{Yıl}.pdf
    # pdfplumber ile tablo çıkar
    ...

def fetch_tefas_equity_allocation(date: str) -> pd.DataFrame:
    """TEFAS fon portföy dağılımı (hisse yüzdesi)."""
    url = "https://www.tefas.gov.tr/api/funds/dagilimSiraliGetirT"
    payload = {"date": date, "kind": "YAT"}
    r = requests.post(url, json=payload, timeout=15)
    return pd.DataFrame(r.json()["data"])

# signals/l5_smart_money.py
def compute_foreign_ownership_change(df: pd.DataFrame, window: int = 30) -> float:
    """Son N günde foreign_ratio değişimi (basis points)."""
    if len(df) < window:
        return np.nan
    return (df["foreign_ratio"].iloc[-1] - df["foreign_ratio"].iloc[-window]) * 10000

def compute_persistence(df: pd.DataFrame, window: int = 10) -> float:
    """Üst üste artış (+) veya azalış (-) gün sayısı, [-N, +N] aralığında."""
    diffs = df["foreign_ratio"].diff().tail(window)
    if (diffs > 0).all(): return window
    if (diffs < 0).all(): return -window
    return diffs.apply(np.sign).sum()

def l5_smart_money_score(ticker: str, conn: sqlite3.Connection) -> float:
    df = pd.read_sql(f"SELECT * FROM foreign_ratio WHERE ticker = ? ORDER BY date",
                     conn, params=(ticker,))
    foi_change = compute_foreign_ownership_change(df, 30)
    foi_level = df["foreign_ratio"].iloc[-1]
    foi_persist = compute_persistence(df, 10)
    # Cross-sectional z-score için tüm evren gerekir
    universe = pd.read_sql("SELECT ticker, foreign_ratio_change_30d, foreign_ratio_level FROM signal_universe", conn)
    z_change = (foi_change - universe["foreign_ratio_change_30d"].mean()) / universe["foreign_ratio_change_30d"].std()
    z_level  = (foi_level  - universe["foreign_ratio_level"].mean()) / universe["foreign_ratio_level"].std()
    # ... z_short, z_fund analojik
    score = (0.35 * z_change + 0.25 * z_level + 0.15 * (foi_persist / 10) +
             0.15 * z_short + 0.10 * z_fund)
    return 50 + 50 * np.tanh(score / 2)

# Storage: SQLite — basit, <500K TL ölçeğine uygun
# Tablolar:
#   foreign_ratio (date, ticker, foreign_ratio, source)
#   mkk_monthly (year_month, total_investors, foreign_investors, foreign_portfolio_tl)
#   tefas_allocation (date, fund_code, equity_pct, ...)
#   l5_signals (date, ticker, foi_change, foi_level, foi_persist, short_int, fund_signal, score)
# 5 yıl × ~500 hisse × günlük ≈ <10 GB; Parquet'e geçiş ileride backtest performansı için.
```

**Caching**: İş Yatırım rate-limit nedeniyle `requests-cache` (24 saat TTL) veya custom SQLite cache; aynı ticker × tarih için tekrar çağrı yapılmaması kritik.

---

## YAPILABILIRLIK SKORU: 6/10 (BASIT MVP) — 8/10 (2 HAFTA + KAPSAMLI)

**1 hafta tek geliştirici (Python, requests/BeautifulSoup/Selenium, sqlite) ile MKK scraper + L5 yeniden mimarisi**:

**Pozitif faktörler (+)**:
- İş Yatırım JSON endpoint'i pratik ve doğrulanmış (urazakgul/isyatirimhisse, borsapy)
- TEFAS API açık ve dokümante (pytefas, eneshenderson/Tefas-API)
- KAP statik bildirim listesi scrape edilebilir (pykap)
- MKK aylık bülten PDF link'leri statik
- L5 algoritması mevcut sisteme inkremental ekleme — tam rewrite değil

**Negatif faktörler (–)**:
- MKK'dan hisse-bazlı günlük takas verisi alınamıyor (2013 Duyuru 631 sonrası) — en zengin metrik (saklayıcı kurum sayısı concentration) erişilemiyor
- İş Yatırım Cloudflare benzeri koruma + "kişisel kullanım" ToS sınırı
- Türkiye akademik literatür individual stock seviyesinde foreign flow sinyalinin zayıf olduğunu işaret ediyor — alpha beklentisi modere olmalı
- Cross-sectional z-score için tüm BIST evreninin günlük çekilmesi (~500 hisse × günlük); ilk historical backfill ciddi (~2-3 gün), incremental sonrası rahat
- Backtesting + walk-forward validation 1 haftaya sığmaz; ya MVP scope kısıtlanmalı ya da 2 haftaya yayılmalı

**Potansiyel Blocker'lar**:
1. **İş Yatırım IP banning** — VPN/proxy rotation gerekebilir; alternatif: Mynet Finans veya başka aggregator
2. **MKK PDF format değişikliği** — pdfplumber regex'leri dayanıklı yazılmalı
3. **TEFAS endpoint değişikliği** — resmi olarak dokümante olmadığı için riskli
4. **Cross-sectional ranking historical kapsama sorunu** — yeni listelenen hisseler için 30-gün penceresi tutmaz
5. **TCMB politika faizi %37 ortamında (Mayıs 2026)** — yüksek risk-free oranı L5 sinyalini ezecek; absolute alpha thresholds yeniden kalibre edilmeli

**Tavsiye**: 1 hafta yerine **2 hafta + MVP scope** (sadece İş Yatırım + mevcut short_interest, TEFAS ve MKK PDF Phase 2'ye); ilk hafta scraper + SQLite + foreign_ownership_change sinyali; ikinci hafta TEFAS fund holding + persistence + walk-forward backtest. Bu plan ile yapılabilirlik **8/10**.

---

## CAVEATS

1. **Ülkü & İkizlerli (2012) makalesinin DOI'si birincil kaynaktan doğrulanamadı** (ScienceDirect robots.txt); ScienceDirect PII (S1566014112000283) doğru, DOI tahminen 10.1016/j.ememar.2012.09.001 — yayın için doğrulanmalı. "Permanent price impact" verbatim quote 2012 makalesinin tam metninden değil, citing literature paraphrase'inden alınmıştır.
2. **MKK hisse bazlı tarihsel veri ücretsiz versiyonu mevcut değil**; 2013 öncesi e-MKK Bilgi Portalı'nda yayınlanan günlük veri Duyuru No. 631 ile kaldırıldı; sadece veri dağıtım sözleşmesi imzalamış kuruluşlardan temin edilebiliyor.
3. **İş Yatırım JSON endpoint'leri resmi API değil**; isyatirimhisse PyPI sayfası açıkça "yalnızca kişisel kullanım" notu içerir; ticari kullanım için lisans değerlendirilmelidir.
4. **TEFAS endpoint'leri resmi public API olarak ilan edilmemiştir**; pytefas/tefas-crawler reverse-engineered. Endpoint değişiklik riski.
5. **Akademik bulgular Turkish/EMR literatürünü genelliyor**; kendi backtesting'iniz olmadan parameter tuning sonuçları farklı çıkabilir. Özellikle 2026 makro koşullarında (TCMB politika faizi %37 — Ocak 2026 PPK kararı; Mayıs 2026 piyasa beklentisi Haziran toplantısı için %37,00) regime değişiklikleri sinyal kalitesini etkileyebilir.
6. **Slippage <500K TL ölçeği için ihmal edilse de**, foreign_ratio değişimi 1-3 bps seviyesinde küçük olabilir; sinyal-noise eşiği için minimum threshold (örn. cross-sectional top/bottom decile filtering) gerekli.
7. **Wu & Xu (2021)** çalışması Journal of Portfolio Management'ta "forthcoming" durumunda görünüyor (AlphaArchitect özetinden); kesin yıl/sayı için yayın tarihinde tekrar kontrol edilmelidir.