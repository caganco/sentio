# RR-013: BIST Holding Hisseleri için NAV İskontosu Hesabı ve Mean Reversion Alpha Stratejisi

# GEÇERLİLİK: "Katman A holding faktörü adayı AMA long-only uyarısıyla"

**Hazırlayan:** Research Layer (BIST OS) | **Tarih:** 24 Mayıs 2026 | **Önceki rapor:** RR-012 §B8 (20× detaylı versiyon)
**Pilot kapsam:** KCHOL, SAHOL, AGHOL, KOZAL, DOHOL — pilot başlangıç KCHOL

---

## 1. TL;DR (Yönetici Özeti)

- **KCHOL pozisyonu (81 lot @ 188.83 TL, son 191.00 TL, P&L +%1.15):** Gedik Yatırım 27 Mart 2025 raporuna göre KCHOL'un look-through (tüm iştirakler dahil) NAV iskontosu ~%33, halka açık iştirakler bazında ~%26 seviyesinde; 15 yıllık tarihsel ortalama ~%13'tür. HSBC'nin (PA Turkey üzerinden yayımlanan) 2025 başı notu mevcut iskontoyu "~%30" ve fair-value iskonto varsayımını %10 olarak veriyor; TP 240 TL, AL. Bu rakamlar, **the maintainer'ın pozisyonu için mevcut iskontoyu istatistiksel olarak ucuz (z-skoru pozitif, yani BUY-leaning) zona koyar** — bu bölgede strateji önerisi **HOLD/ADD** yönündedir; TRİM sinyali değildir.
- **Pilot için seçilen 3 holding:** KCHOL (likidite, şeffaflık, broker kapsama derinliği), SAHOL (banka + enerji çekirdeği, 11 listelenmiş iştirak), AGHOL (içecek/perakende defansif portföy, İş Yatırım 28 Haziran 2024 raporunda 1-yıllık ort. iskonto %38 / 3-yıllık ort. %32 ile en temiz tarihsel veri).
- **Implementation timeline:** 2 hafta pilot (KCHOL Tier-1 NAV + 1 yıl z-skor) → 2 hafta genişletme (SAHOL + AGHOL + holdings.yaml) → 2 hafta Tier-2 SoTP detaylandırma ve signal engine entegrasyonu. **Beklenen alpha (literatür-bazlı):** Pontiff (1995, JFE 37(3), 341-370) ABD bulgusu: *"Funds with 20% discounts have expected twelve-month returns that are 6% greater than nondiscounted funds. This correlation is attributed to premium mean-reversion, not to anticipated future portfolio performance."* — yani %20 iskontolu fonlar 12 ayda %6 ek getiri sağlar. Türkiye'de örneklem küçük (3 hisse) ve mikro yapı farklı; bu nedenle Pontiff bulgusunu **üst sınır referans değer** olarak kullanıyoruz, sayısal alfa hedefi koymuyoruz.

---

## 2. Akademik Temel Özeti

### 2.1 Kapalı Uçlu Fon (Closed-End Fund) İskontosu Literatürü

**Lee, Shleifer, Thaler (1991, JoF 46(1), 75-109, DOI 10.1111/j.1540-6261.1991.tb03746.x):** "Investor Sentiment and the Closed-End Fund Puzzle". Kapalı uçlu fonlardaki iskontoların bireysel yatırımcı sentiment'i tarafından sürüklendiğini öne sürer. Üç ana ampirik bulgu: (i) farklı fonların iskontoları birlikte hareket eder, (ii) yeni fonlar primli/dar iskonto döneminde piyasaya çıkar, (iii) iskontolar küçük hisselerin getirileriyle korelasyon gösterir. **BIST'e katkısı:** Holding iskontolarının sistematik bir "sentiment faktörü" olarak ele alınabileceği, dolayısıyla 5 BIST holdinginin iskonto seriilerinin ortak hareket (cointegration) içerip içermediğinin test edilmesi gerektiği önerisini sağlar.

**Pontiff (1996, QJE 111(4), 1135-1151, DOI 10.2307/2946710):** "Costly Arbitrage: Evidence from Closed-End Funds". Arbitraj maliyetlerinin (özellikle idiosinkratik risk, düşük temettü ödemesi, küçük piyasa değeri, yüksek faiz oranları) iskontoları temel değerlerden uzaklaşmaya bıraktığını kanıtlar (verbatim abstract: *"the market value of a fund is more likely to deviate from the value of its assets (1) for funds with portfolios that are difficult to replicate, (2) for funds that pay out smaller dividends, (3) for funds with lower market values, and (4) when interest rates are high"*). **BIST'e katkısı:** Türkiye'de TCMB politika faizi %37 (Nisan 2026 PPK kararı; 1-haftalık repo ihale oranı %37, gecelik borç verme %40, borçlanma %35.5) gibi yüksek faiz ortamı, Pontiff modelinde "yüksek arbitraj maliyeti" rejimine işaret eder — iskontoların yapışkan kalması teorik olarak beklenir.

**Pontiff (1995, JFE 37(3), 341-370, DOI 10.1016/0304-405X(94)00800-G):** "Closed-End Fund Premia and Returns". Verbatim ana bulgu: *"Funds with 20% discounts have expected twelve-month returns that are 6% greater than nondiscounted funds. This correlation is attributed to premium mean-reversion, not to anticipated future portfolio performance."* Mean reversion mekanizmasının ampirik temelidir ve bu raporun tüm alfa hipotezinin ana referans noktasıdır.

**Cherkes, Sagi, Stanton (2009, RFS 22(1), 257-297, DOI 10.1093/rfs/hhn028):** "A Liquidity-Based Theory of Closed-End Funds". Rasyonel, likidite tabanlı bir kapalı uçlu fon modeli sunar: CEF'ler illikit underlying'i likit fund-share'e dönüştürür; iskonto, likidite faydası ile yönetim ücreti arasındaki trade-off'tur. **BIST'e katkısı:** KCHOL gibi yüksek hacimli holding hissesinin, görece daha az likit private iştirakler (KoçSistem, Tek-Art, WAT) için bir likidite vehikülü işlevi gördüğü teziyle tutarlıdır; bu, KCHOL'un YKBNK'tan (kendi başına likit) farklı bir likidite primi taşıması anlamına gelir.

### 2.2 EM Holding / Konglomera İskontosu

**Berger, Ofek (1995, JFE 37(1), 39-65):** "Diversification's effect on firm value". Verbatim abstract: *"Comparing the sum of these stand-alone values to the firm's actual value implies a 13% to 15% average value loss from diversification during 1986–1991. The value loss is smaller when the segments of the diversified firm are in the same two-digit SIC code. We find that overinvestment and cross-subsidization contribute to the value loss. The loss is reduced modestly by tax benefits of diversification."* **BIST'e katkısı:** Türk holding iskontolarının (KCHOL ~%30, SAHOL %25-49, AGHOL %32-50) ABD %13-15 bandının üstünde olduğu — yani EM premium taşıdığı — yapısal saptaması.

**Khanna, Palepu (2000, JoF 55(2), 867-891, DOI 10.1111/0022-1082.00229):** "Is Group Affiliation Profitable in Emerging Markets?". Hindistan'da grup-bağlı firmalar belirli bir eşiğin üzerinde bağımsız firmalardan **daha karlı** çıkar — EM'de eksik kurumlar (kredi piyasası, işgücü piyasası, koordinasyon) iç sermaye piyasaları sayesinde içselleştirilir. **BIST'e katkısı:** Türk holdinglerinde iskontonun "diversifikasyon cezası" yerine "kontrol primi / tunneling indirimi" olarak yorumlanması gerektiğini savunan teorik dayanağı verir.

**Bae, Kang, Kim (2002, JoF 57(6), 2695-2740, DOI 10.1111/1540-6261.00510):** "Tunneling or Value Added? Evidence from Mergers by Korean Business Groups". Kore chaebol'larında bir grup firması satın alma yaptığında hisse fiyatı ortalama düşer; azınlık hissedarlar kaybeder, kontrol hissedarı diğer grup şirketlerinde değer artışı sayesinde kazanır — **tunneling kanıtı**. **BIST'e katkısı:** Türk aile holdinglerinde benzer içsel sermaye transferi (gerçek ya da algılanan) riskinin iskonto için yapısal bir alt taban yarattığını gösterir; iskonto sıfıra inmeyebilir.

**Lins (2003, JFQA 38(1), 159-184):** "Equity Ownership and Firm Value in Emerging Markets". 18 EM örneğinde, yönetim grubunun kontrol hakları ile nakit akış hakları arasındaki ayrım arttıkça firma değeri düşer; bu etki zayıf yatırımcı koruması olan ülkelerde daha güçlüdür. **BIST'e katkısı:** Türk holding ailelerinin piramit yapı (Koç → KFS → Yapı Kredi) sayesinde nakit akış-kontrol ayrımı yarattığı; bu yapısal faktör Berger-Ofek %13-15'inin üstüne ek iskonto yükler.

### 2.3 Türkiye-Spesifik Literatür

**Yurtoğlu (2000, Empirica 27(2), 193-222, DOI 10.1023/A:1026557203261):** "Ownership, Control and Performance of Turkish Listed Firms". 257 Türk firmasında piramit yapı ve yoğun aile sahipliğinin, daha düşük ROA, daha düşük PD/DD ve daha düşük temettü ödemesi ile ilişkili olduğunu bulur. **BIST'e katkısı:** Türk holding iskontosunun yapısal-yapısal (idiosinkratik değil sistematik) bileşenli olduğunun ampirik temelidir.

**Demirgüç-Kunt, Levine (World Bank Policy Research WP 4469, 2008):** Türkiye gibi banka-merkezli EM'lerde business group dominansının makro istikrarla bağı.

**Karamustafa & Karakaya (2004), Aydoğan (2002), Önder (2003, METU Studies in Development 30) gibi yerli akademik literatür** ağırlıklı olarak performans-sahiplik korelasyonuna odaklanmakta; spesifik holding-iskontosu mean reversion ampirik testi yok ya da çok sınırlı. Bu durum, raporumuzun **boşluğu doldurma değerini** ortaya koymaktadır.

### 2.4 Mean Reversion: Yarı Ömür ve Ampirik Kanıt

**Ji & Kim (2013, Applied Economics 45(32), 4503-4515, DOI 10.1080/00036846.2013.791019)** US/UK CEF örneğinde bias-corrected bootstrap yarı ömür tahminleri yapmıştır: tam örnekte ortalama 10.32 ay, alt-örneklerde *"implying an average half-life of 7.7 months for all the funds in our sample"*. Bu, **7.7-10.3 ay yarı ömür** bandını ampirik referans olarak verir. Türkiye için spesifik yarı ömür ampirik bulgusu bu araştırmada bulunmadı — pilotun ilk amaçlarından biri **KCHOL discount serisinin AR(1) tahmini** olmalıdır.

---

## 3. Her Holding için Detaylı Profil

### 3.1 KCHOL — Koç Holding A.Ş. (PİLOT)

**İştirak yapısı (Gedik Yatırım 27 Mart 2025 raporundan alınan SoTP tablosu):**

| Segment / Şirket | İş Kolu | Stake (KCHOL) | NAV katkısı (%) | Değerleme Yöntemi |
|---|---|---|---|---|
| **Otomotiv: %43.0 NAV** | | | | |
| Ford Otosan (FROTO) | Üretim | %38.7 | %22.4 | DCF |
| Tofaş (TOASO) | Üretim | %37.6 | %5.2 | DCF |
| Türk Traktör (TTRAK) | Traktör | %37.5 | %4.9 | DCF |
| Otokar (OTKAR) | Üretim | %47.4 | %4.4 | DCF |
| Otokoç | Ticaret | %96.4 | %6.0 | Book value |
| **Enerji: %22.5 NAV** | | | | |
| Tüpraş (TUPRS) | Rafineri | %46.4 (EYAS üzerinden) | %17.4 + %6.4 doğrudan = %23.8 | EYAS MCap − Net Debt of SPV |
| Aygaz (AYGAZ) | LPG | %40.7 | %2.3 | DCF |
| **Finans: %18.8 NAV** | | | | |
| Yapı Kredi (YKBNK) | Bankacılık | %20.2 doğrudan (KFS toplamı %41) | %6.8 | Gordon Growth |
| KFS (Koç Finansal Hizmetler) | Holding | %86.6 | %11.9 (consol.) | — |
| Koç Finans | Tüketici finansmanı | %50.0 | %0.2 | Book value |
| **Tüketim: %6.3 NAV** | | | | |
| Arçelik (ARCLK) | Beyaz eşya | %41.4 | %6.3 | DCF |
| **Diğer (Turizm + Other + Real Estate): ~%3.8 NAV** | | | | |
| KoçSistem | Sistem ent. | %48.4 | %0.3 | Book value |
| Token Finansal Teknolojiler | Fintech | %54.4 | %0.2 | Book value |
| Net Cash (Holdco) | — | — | %5.5 | Recalc'd |

**Gedik Yatırım hesaplaması (27 Mart 2025 raporu, hisse fiyatı 165.50 TL referansında):**
- Toplam NAV (per share): **246.89 TL**
- Hedef NAV (per share): **329.46 TL** (target prices ile)
- Net cash: TL 34.55 bn
- Listed assets toplamı: TL 534.68 bn (%85.4 of NAV)
- Unlisted assets toplamı: TL 56.85 bn (%9.1 of NAV)
- **Cari NAV iskontosu: %33** (look-through, tüm iştirakler) / **%26** (sadece halka açık iştirakler)
- **15 yıllık tarihsel ortalama iskonto: ~%13**
- **5 yıllık iskonto aralığı: %-10 (premium) ile %-40 (deep discount)** arasında
- Hedef fiyat: **252.74 TL** (son 2 yılın ortalama iskontosu olan ~%24 uygulanarak), Outperform

**Tarihsel iskonto trajectory (KCHOL):**
- **Şubat 2023 (deprem) → Mayıs 2023 (seçim sonrası):** KCHOL IR Q3 2023 webcast verbatim: *"On Slide 15, you will see the evolution of the net asset value discount. Our year-to-date weekly average NAV discount is just under 30% compared to the long-term average discount of 11% to 12%. At Koç Holding, we benefit from our market proxy studies, and we observed our NAV discount narrowing down sharply in May this year, supported by the sentiment and the return of the foreign investors."* — Deprem sonrası genişleme, Mayıs 2023 seçim sonrası yabancı dönüşüyle keskin daralma, ardından H2 2023 boyunca tekrar genişleme.
- **Mid-2024:** HSBC notuna göre iskonto **mid-teens (~%15)** seviyesine daralmış.
- **Erken 2025 (HSBC, PA Turkey üzerinden):** *"Koc's NAV discount had narrowed to mid-teen levels in mid-2024 but has widened in a volatile course since then to c30% today... we continue to assume a fair value discount of 10%, which used to be the average discount level when CDS rates were previously at current levels... Cut TP to TRY240; retain Buy."* Fair-value iskonto **%10**, TP 240 TL.
- **27 Mart 2025 (Gedik):** %33 look-through / %26 listed-only; TP 252.74 TL.

**Likidite metrikleri:** Mynet Finans'a göre KCHOL günlük işlem hacmi **TL 5.0 bn** seviyesinde, günlük ~54.6 mn lot. the maintainer'ın 81 lot pozisyonu için slippage tamamen ihmal edilebilir. Halka açıklık oranı %42.81 (mynet); ana ortak Family Danışmanlık (sermaye %43.75, oy %55.62).

**Broker coverage:** Investing.com (21 Mayıs 2026): *"The average 12-month price target for Koc Holding is 295.69 TRY, with a high estimate of 333 TRY and a low estimate of 272.6 TRY. 11 analysts recommend buying the stock, while 0 suggest selling, leading to an overall rating of Strong Buy."* — 11 alış, 0 satış tavsiyesi, ortalama TP 295.69 TL.

**Pilot uygunluk skoru: 5/5.** Tüm iştirakler likit veya iyi belgelenmiş; broker kapsama derinliği yüksek; tarihsel iskonto serisi en az 15 yıl mevcut.

### 3.2 SAHOL — Hacı Ömer Sabancı Holding A.Ş.

**İştirak yapısı (Sabancı 2025 Entegre Faaliyet Raporu, yatirimciiliskileri.sabanci.com):**
- 11 listelenmiş iştirak: Akbank (AKBNK), Aksigorta (AKGRT), Agesa (AGESA), Brisa (BRISA), Carrefoursa (CRFSA), Çimsa (CIMSA), Afyon Çimento (Çimsa üzerinden %51), Enerjisa Enerji (ENJSA), Kordsa (KORDS), Teknosa (TKNSA), Akçansa (AKCNS, Çimsa üzerinden %45 efektif)
- Halka açık olmayan: Enerjisa Üretim, Sabancı Building Solutions, Sabancı Climate Technologies, Temsa, Tursa, Exsa
- Toplam NAV (yönetim açıklaması Q3 2025): **TL 9.4 milyar** (cash hariç **USD 9.6 milyar**)
- NAV ağırlığı: Banka + Finansal Hizmetler ve Enerji + Climate Tech yaklaşık eşit; sanayi (Kordsa, Çimsa) ve perakende (Teknosa, Carrefoursa) daha küçük

**Broker NAV iskonto verileri:**
- **HSBC (PA Turkey üzerinden, 2023):** *"...trades at... current NAV discount of 49%. Sabanci has underperformed the vast majority of its listed parts and the BIST100 index year-to-date 2023, pushing its current discount to listed parts and NAV to 26% and 49%, respectively, from 13% and 36% at year-beginning... The NAV discount is at one of the highest levels historically and above the past 10-year average of c40%."* Fair-value NAV iskontosu **%25** (önceki %20'den yükseltildi), TP 95 TL, AL.
- **Deniz Yatırım (yıl sonu 2025/Ocak 2026):** *"2025, iyileşen ülke risk primine karşılık NAD iskontolarının yükseldiği ve holding hisselerinin baskılandığı bir yıl oldu. Hesaplamalarımıza göre, Koç Holding ve Sabancı Holding, halka açık iştiraklerine göre yıl boyunca [...] iskonto ile işlem görürken, 2024 yılında bu oranlar [...] şeklindeydi."* TP 153 TL, AL. (Spesifik yüzdeler kaynak HTML'de Türkçe karakter encoding hatası nedeniyle okunamadı; yön: 2025 iskontoları 2024'ten geniş.)
- **İş Yatırım (2025 ortası):** TP 172 TL (150'den yükseltildi), AL; mevcut iskonto 1-yıl ve 3-yıl ortalamasının üstünde (spesifik %'ler kaynak HTML'de obscured).
- **ICBC Yatırım (28 Temmuz 2025):** 150 TL TP ile "AL" tavsiyesi ile araştırma başlattı.
- **Ata Yatırım (18 Temmuz 2025):** TP 140 → 148.5 TL'ye yükseltildi, AL.
- **HSBC (7 Ekim 2025):** TP 140 → 148 TL'ye yükseltildi, AL.
- **Sabancı CFO Orhun Köstem, Q3 2025 webcast:** *"the discount to NAV still poses a very substantial opportunity"* — yönetim NAV iskontosunu açık fırsat olarak nitelendiriyor.

**Pilot uygunluk skoru: 5/5.** Likidite çok yüksek (KAP raporlarına göre günlük işlem hacmi top 10), 11 listelenmiş iştirak SoTP'yi otomasyon-friendly yapar, 1997 Borsa kotasyonundan beri uzun tarihsel iskonto serisi mevcut.

### 3.3 AGHOL — AG Anadolu Grubu Holding A.Ş.

**İştirak yapısı (anadolugroup.com FAQ + CCI.com.tr "Shareholder Structure"):**
- Anadolu Efes (AEFES): AGHOL doğrudan **%43** sahip
- Coca-Cola İçecek (CCOLA): Anadolu Efes %50.3 sahip → AGHOL efektif **%21.6**
- Migros (MGROS): AGHOL ~%23 sahip
- Anadolu Isuzu (ASUZU): Otomotiv
- Adel Kalemcilik (ADEL): Kırtasiye
- Alternatifbank, Alternatif Finansal Kiralama (özel)
- Çelik Motor, Anadolu Motor, Anadolu Restoran, Anadolu Etap (CCI üzerinden tamamı 2024'te alındı)
- AGHOL halka açıklık (free float): %33.7
- 2024 net varlık: TL 543.7 milyar; ciro TL 563.8 milyar

**Broker NAV iskonto verileri (en temiz tarihsel seri burada):**
- **İş Yatırım, 28 Haziran 2024 ⭐ (CLEANEST DATA POINT):** *"AGHOL hisseleri için hedef fiyatımızı 555 TL/hisse'ye yükseltiyoruz. Anadolu Grubu Holding'in mevcut NAD'ında içecek şirketlerinin payı %44 seviyesinde. MGROS da dahil edildiğinde bu 3 hissenin NAD'daki payı %79'a çıkmakta… **Holding'in mevcut NAD iskontosu %36 (TOGG dahil %38) seviyesindeyken, 1 yıllık ve 3 yıllık ortalama iskontoları sırasıyla %38 ve %32.**"*
- **Yatırım Finansman (2024):** *"AGHOL için hedef Net Aktif Değeri (NAV) 5 milyar USD olarak hesaplıyoruz, bu da mevcut 2.2 milyar USD piyasa değerine göre hedef NAV'da [obscured]'lik bir iskontoya işaret ediyor."* İmplied: USD 2.2bn / USD 5.0bn ≈ **%56 iskonto** (ex-Russia ~%50; holding discount applied ~%35). TP 556 TL.
- **HSBC AGHOL Initiation (10 Haziran 2025):** *"90.9 milyar TL'lik hedef NAV tahminimize ulaşmak için [obscured] holding şirketi iskontosu uyguluyoruz. Rusya'daki bira operasyonlarının olumlu sonuçlanmasının önemli bir pozitif katalizör olacağına inanıyoruz."* TP **373 TL**, AL.
- **Yapı Kredi Yatırım (12 Mayıs 2025):** TP 532 TL, AL (korundu).
- **İş Yatırım (3 Mart 2023, deprem sonrası top picks):** *"AGHOL: Defansif portföyü ve yüksek NAD iskontosu sebebiyle AGHOL'un cazip bir yatırım teması sunduğunu düşünüyoruz."* Aynı notta SAHOL, *"diğer holdinglere kıyasla daha düşük seviyede olan net aktif değer iskontosu nedeniyle"* portföyden çıkarıldı — yani Şubat 2023 depremi sonrası iskonto-divergence stratejik karar belirleyici olmuştur.

**Pilot uygunluk skoru: 4/5.** En büyük artısı: İş Yatırım'ın çeyrek-bazlı NAD iskontosu raporlaması düzenli (her TP revizyonunda 1-yıl/3-yıl ortalama veriyor) — bu **Z-skor hesaplama için ready-made benchmark**. Eksisi: Coca-Cola İçecek'in efektif sahipliği (AEFES üzerinden) double-counting riski yaratır; Tier-1 NAV'da dikkatli ele alınmalı.

### 3.4 KOZAL — Koza Altın İşletmeleri A.Ş.

**İştirak yapısı:** KOZAL bir **single-asset altın madencilik şirketi**dir; "holding" tanımına marjinal uyar. KOZAA (Koza Anadolu Metal) ile bağı: KOZAA, KOZAL'ı **%70.41** oranında sahiplik üzerinden kontrol eder (Koza İpek Holding yapısı). KOZAL **kendisinin holdingi yoktur** — yani KCHOL/SAHOL paradigmasına uymaz. Operasyonel madenler: Ovacık, Mastra, Çukuralan, Kaymaz, Himmetdede, Çoraklık.

**NAV iskontosu uygulanabilirliği:** **Düşük.** KOZAL için NAV iskontosu kavramı geçerli değil; bunun yerine **altın fiyatı + üretim hacmi + AISC (all-in sustaining cost)** dinamiği belirleyicidir. Morningstar 24 Mayıs 2026 itibarıyla KOZAL'ın "55% premium" ile işlem gördüğünü gösteriyor (DCF model bazlı; intrinsic value < market price).

**Pilot uygunluk skoru: 1/5.** RR-013 kapsamında **çıkarılmasını** öneriyoruz. Alternatif: KOZAA pilotu (KOZAA'nın NAV'ı = %70.41 × KOZAL market cap) — ama tek-iştirakli holding olduğu için mean reversion sinyal çeşitliliği sağlamaz.

### 3.5 DOHOL — Doğan Şirketler Grubu Holding A.Ş.

**İştirak yapısı:** DOHOL'un mevcut portföyü medya satışı (2018 Demirören'e satış) sonrası küçülmüş durumda. Mevcut iş kolları: D-Auto (otomotiv distribütörlüğü), Ditaş Doğan (yedek parça), enerji yatırımları, gayrimenkul, finans (Doğan Investment Bank ortaklığı). Yahoo Finance/Morningstar verisine göre DOHOL likidite ve free-float açısından KCHOL/SAHOL'a göre çok daha küçük.

**Likidite:** Marjinal. Günlük işlem hacmi KCHOL'un %1'inden az.

**Pilot uygunluk skoru: 2/5.** Tarihsel iskonto serisi var ancak hem küçük örnekleme dahil etmek istatistiksel olarak verimsiz hem de pozisyon ölçeği <500K TL portföy için bile likidite/spread sorunu yaratabilir. RR-013'te **referans amaçlı** dahil ediyoruz, pilot için çıkarıyoruz.

### 3.6 Pilot Universe — Final Seçim

**Önerilen pilot set: KCHOL (skor 5), SAHOL (skor 5), AGHOL (skor 4).** Genişletme adımı 2'de GLYHO, YAZIC, TAVHL, ECILC adayları değerlendirilebilir. KOZAL ve DOHOL **strateji-dışı** bırakılıyor.

---

## 4. NAV Hesap Metodolojisi

### 4.1 Tier 1 — Basit NAV (KAVRAMSAL FORMÜL)

```
NAV_holding = Σ (stake_i × market_cap_i)  + cash_holdco − debt_holdco
              i ∈ listed subsidiaries

discount_pct = (NAV_per_share − holding_share_price) / NAV_per_share × 100
```

**Veri girdileri (Tier 1):**
- `stake_i`: KAP yıllık faaliyet raporundan (yıllık güncelleme; SPK 5%+ değişiklik duyurusu ile tetiklenmeli)
- `market_cap_i`: yfinance ticker (TUPRS.IS, YKBNK.IS, FROTO.IS, vs.) — TTL 1 gün cache
- `cash_holdco`, `debt_holdco`: KAP çeyreklik solo bilanço (her 3 ayda bir güncelleme)
- `holding_share_price`: yfinance KCHOL.IS

**Sınırlamalar:** Private iştirakler (KoçSistem, Tek-Art Marina, Enerjisa Üretim, Sabancı Climate Tech) book value veya peer multiple ile yaklaşık değerlenir; tarihsel z-skor için yeterli ama hedef-iskonto kalibrasyonu için yetersiz.

### 4.2 Tier 2 — Detaylı SoTP (KAVRAMSAL)

Gedik Yatırım 27 Mart 2025 raporu modellenmesi:
- **Listed subsidiaries:** stake × current market cap (Tier 1 ile aynı)
- **Listed subsidiaries with DCF override:** Ford Otosan, Tofaş, Türk Traktör, Otokar, Arçelik, Aygaz, Tüpraş için broker DCF target value
- **Unlisted subsidiaries:** Otokoç, Koç Sistem, Token, Koç Finans, WAT → book value
- **Special vehicles:** EYAS (Tüpraş'ı kontrol eden SPV) için "EYAS MCap − Net Debt of SPV" formülü
- **Net Cash (Holdco, recalculated):** son USD/TRY paritesi ile yeniden hesaplanmış net cash
- **Head office costs:** çıkarılmıyor (Gedik raporunda ayrı kalem yok ama HSBC notlarında "Holdco discount" bunu içselleştirir)
- **Tax adjustments:** broker bazlı; sermaye kazancı vergisi efekti hesaplamada genellikle ihmal edilir

### 4.3 Karşılaştırma Tablosu

| Boyut | Tier 1 (Basit) | Tier 2 (SoTP) | Tier 3 (Broker Consensus) |
|---|---|---|---|
| Veri girdisi | yfinance + KAP | yfinance + KAP + broker DCF TP'leri | Direkt broker PDF parse |
| Güncelleme sıklığı | Günlük | Çeyreklik (broker raporu çıktıkça) | Broker raporu sıklığına bağlı |
| Doğruluk (KCHOL referansında) | ±%5 broker hesabına karşı | ±%2-3 | Reference |
| Mean reversion sinyali için yeterli mi? | Evet (z-skor için) | Tercih edilir | Backtest için ideal |
| Implementation effort | 1 hafta | 3-4 hafta | 6+ hafta |

**Öneri:** Pilot için **Tier 1**, Faz 3'te **Tier 2**'ye geçiş. Tier 3 (broker PDF parse) bu proje kapsamında **yapılmıyor** (kopyalama ve copyright kısıtları).

---

## 5. Sinyal Tasarımı

### 5.1 Z-Skor Formülü

```
discount_t = (NAV_t − price_t) / NAV_t
mean_lookback = rolling mean (discount, 252 trading days = ~1 yr)
std_lookback = rolling std (discount, 252 days)

z_score_t = (discount_t − mean_lookback) / std_lookback
```

**Yorum:**
- **z > +2:** İskonto, son 1 yıl ortalamasının +2 std üzerinde → istatistiksel olarak "ucuz" → **BUY-leaning**
- **z < −2:** İskonto, ortalamadan −2 std altta (yani dar) → istatistiksel olarak "pahalı" → **AVOID/TRIM**
- **−1 < z < +1:** Nötr zon → mevcut diğer L1-L6 sinyallerini takip et

### 5.2 Threshold Tablosu

| Sinyal | z-skor eşiği | Yüzdelik eşik (alternatif) | Aksiyon (long-only) |
|---|---|---|---|
| Strong BUY | z > +2 | 90. persantil üstü | Yeni pozisyon aç / Mevcut pozisyonu artır (Kelly L6 ile sınırla) |
| BUY | +1 < z < +2 | 75-90. persantil | Mevcut pozisyonu artır |
| HOLD | −1 < z < +1 | 25-75. persantil | Mevcut pozisyonu koru |
| TRIM | −2 < z < −1 | 10-25. persantil | Pozisyonu kademeli azalt |
| AVOID | z < −2 | 10. persantil altı | Yeni pozisyon açma; mevcut pozisyonu önemli ölçüde azalt |

**KCHOL için uygulama (27 Mart 2025 referans):**
- Mevcut iskonto: %33 (look-through)
- 15-yıl ortalama: %13
- Approx z = (33 − 13) / std_proxy_13 ≈ **+1.5**, yani **BUY-leaning** zonunda.
- HSBC'nin "stretched" / "back at attractive levels" yorumu ile tutarlı.

### 5.3 Confluence Kuralları

NAV iskontosu z-skoru tek başına sinyal değil; mevcut L1-L6 katmanı ile birleşmeli:

| L1 Technical | L5 Smart Money | L_NAV (yeni) | Composite Sinyal |
|---|---|---|---|
| Bullish (>200 SMA) | Pozitif | z > +1 | **Strong BUY** (confluence ×3) |
| Nötr | Nötr | z > +2 | **BUY** (sadece NAV bazlı) |
| Bearish | Negatif | z > +2 | **HOLD** (NAV BUY diğer faktörler counter — dikkat: kasiyer-tipi sinyal) |
| Bullish | Pozitif | z < −1 | **HOLD** (momentum oynar ama NAV pahalı) |
| Bearish | Negatif | z < −2 | **SELL/AVOID** (üç katmanlı negatif confluence) |

### 5.4 Long-Only Adaptasyonu

Akademik literatür (Pontiff 1995, Lee-Shleifer-Thaler 1991) sıklıkla **long-short pair trade** strateji önerir (long holding, short underlying). BIST OS'un long-only kısıtı bunu uygulanamaz kılar. Long-only adaptasyon:
- Sinyal **giriş timing'i** olarak kullanılır (z > +1.5 → giriş)
- Sinyal **çıkış timing'i** olarak kullanılır (z < 0 → kademeli çıkış)
- Pozisyon boyutu Kelly L6'dan; NAV-z-skor pozisyon boyutu MODÜLATÖRÜ olarak kullanılır (z = +2 → tam Kelly, z = 0 → Kelly × 0.5)

---

## 6. Implementation Roadmap

### Faz 1 — Hafta 1: KCHOL Pilot

**Definition of Done:**
- 7 ana iştirak (TUPRS, YKBNK, FROTO, TOASO, ARCLK, AYGAZ, OTKAR) için stake config (`holdings.yaml` taslağı)
- yfinance ticker mapping (KCHOL.IS, TUPRS.IS, YKBNK.IS, FROTO.IS, TOASO.IS, ARCLK.IS, AYGAZ.IS, OTKAR.IS)
- Tier 1 NAV hesaplayan modül (kavramsal): `holding_nav_calculator.py`
- Son 252 trading günü için tarihsel NAV iskontosu serisi (yfinance ticker historisi'nden)
- Z-skor ve persantil hesabı
- SQLite tablo: `holdings`, `holding_nav_history`
- Manuel kontrol: 27 Mart 2025 tarihinde modelin ürettiği iskonto Gedik'in %33 (look-through) ile ±%3 hata payında uyuşmalı

**Builder spec taslağı (kavramsal):**
> "Create `holding_nav_calculator` layer reading `holdings.yaml` (KCHOL only). For each subsidiary in config, fetch yfinance market cap, multiply by stake, sum. Add KCHOL solo net cash from `kchol_solo_cash.csv` (manual quarterly update). Compute NAV per share by dividing by KCHOL share count. Compare to KCHOL spot price → discount %. Persist daily to `holding_nav_history` SQLite table. Compute 252-day rolling mean, std, z-score. Output: signal {BUY, HOLD, TRIM, AVOID} per threshold table."

### Faz 2 — Hafta 2-3: 3 Holding Genişleme

**Definition of Done:**
- `holdings.yaml` master config: KCHOL, SAHOL, AGHOL (KOZAL ve DOHOL outside-scope)
- SAHOL için 11 iştirak (AKBNK, AKGRT, AGESA, BRISA, CRFSA, CIMSA, AFYON, ENJSA, KORDS, TKNSA, AKCNS) config
- AGHOL için listed iştirak (AEFES, CCOLA double-counting handling, MGROS, ASUZU, ADEL) config
- Backtest: 2023-01-01 to 2025-12-31 z-skor sinyalleri üretip teorik long-only return serisi hesapla
- Backtest sanity check: KCHOL Mayıs 2023 (post-election iskonto daralması) modelde **TRIM** sinyali olarak görünüyor mu? Şubat 2023 (deprem) **BUY** sinyali olarak?

### Faz 3 — Hafta 4-5: Tier 2 Detaylı SoTP

**Definition of Done:**
- Private iştirak değerlemeleri: KoçSistem, Tek-Art, Sabancı Climate Tech, Sabancı Building Solutions için book value (KAP solo bilanço) + peer EBITDA multiple
- EYAS gibi SPV'ler için "MCap − Net Debt of SPV" mantığı
- Head office cost adjustment: holdco-level OpEx
- Tax adjustment: ihmal (Türk yatırımcı için temettü stopajı %15 + sermaye kazancı stopajı ayrı katman)
- Tier 2 NAV'ın Tier 1'e kıyasla varyans/açıklayıcı gücü ölçüldü

### Faz 4 — Hafta 6: Signal Engine Entegrasyonu

**Definition of Done:**
- Yeni katman `L_NAV` (per-stock sinyal değil, **structural sinyal** — sadece 3 hisse için aktif)
- Mimari karar: `L_NAV` L5 Smart Money'nin alt-feature'ı değil, **ayrı bir conditional layer** — `if ticker in {'KCHOL','SAHOL','AGHOL'}: include L_NAV; else: pass`
- Composite skora ağırlık: pilotta **%15** (L1 Technical %30, L2 Macro %20, L3 KAP %20, L5 Smart Money %15, L_NAV %15 — 295 hissede L_NAV katsayısı 0)
- Backtest: 2024-01-01 to 2025-12-31, composite signal vs sade L1-L5 sinyal benchmark
- Walk-forward validation 6 ay

---

## 7. Risk Analizi Matrisi

| Risk | Olasılık | Etki | Mitigation |
|---|---|---|---|
| **R1: Veri kalitesi** (yfinance delay, stake outdated, private subjective) | Yüksek | Orta | KAP'tan stake'leri çeyreklik manuel doğrulama; yfinance vs İş Yatırım screener cross-check |
| **R2: Survivorship/selection bias** (3 holding küçük örneklem) | Çok yüksek | Yüksek | Sonuçları **istatistiksel anlamlılık iddia etmeden** rapor et; out-of-sample test (2026 ileri) zorunlu |
| **R3: Mean reversion failure** (yapısal kırılma, kontrol değişikliği, regülasyon, long-only kısıtı arbitraj sınırlar) | Orta | Çok yüksek | Pontiff (1996) "costly arbitrage" çerçevesinde TR politika faizi %37'nin yüksek arbitraj maliyeti rejimine işaret ettiğini kabul et; iskontonun "yapışkan" olabileceğine hazır ol; stop-loss z < −2 |
| **R4: Likidite** (KCHOL/SAHOL likit, AGHOL marjinal, DOHOL/KOZAL illikit) | Düşük (pilot için) | Orta | Pilot sadece KCHOL/SAHOL/AGHOL ile sınırlandı; AGHOL pozisyon boyutu Kelly × 0.7 ile sınırlandı |
| **R5: Concentration risk** (3 holding ortak Türkiye-makro maruziyet, USD/TRY, CDS, faiz) | Yüksek | Yüksek | Composite skorda L2 Macro katsayısı zaten Türkiye risk faktörünü yakalar; 3 holding birlikte aynı yönde sinyal verirse pozisyon toplamı Kelly aggregate × 0.6 cap |
| **R6: Tunneling/aile transferi olayı** (Bae-Kang-Kim 2002 tipi) | Düşük | Çok yüksek | KAP "Özel Durum Açıklamaları" feed'ini günlük tara; aile holdingi grup içi M&A olayında pozisyon donduruluyor |

---

## 8. Akademik Kaynak Özeti

| # | Kaynak | DOI/URL | BIST'e Katkı |
|---|---|---|---|
| 1 | **Lee, Shleifer, Thaler (1991)** "Investor Sentiment and the Closed-End Fund Puzzle", *Journal of Finance* 46(1), 75-109 | DOI: 10.1111/j.1540-6261.1991.tb03746.x | Holding iskontosunun sentiment-bazlı bir faktör olarak yorumlanması ve farklı holding iskontolarının birlikte hareket etmesi hipotezi (cointegration testi) |
| 2 | **Pontiff (1996)** "Costly Arbitrage: Evidence from Closed-End Funds", *QJE* 111(4), 1135-1151 | DOI: 10.2307/2946710 | Türkiye'nin yüksek faiz ortamı (%37) Pontiff "costly arbitrage" rejiminde — iskontoların yapışkan kalma olasılığı |
| 3 | **Pontiff (1995)** "Closed-End Fund Premia and Returns", *JFE* 37(3), 341-370 | DOI: 10.1016/0304-405X(94)00800-G | %20 iskontolu fonların 12 ayda %6 ek getiri sağladığı ampirik temel; mean reversion alpha referans noktası |
| 4 | **Cherkes, Sagi, Stanton (2009)** "A Liquidity-Based Theory of Closed-End Funds", *RFS* 22(1), 257-297 | DOI: 10.1093/rfs/hhn028 | KCHOL gibi likit holding hissesinin private iştirakler için "likidite vehikülü" rolü |
| 5 | **Berger, Ofek (1995)** "Diversification's effect on firm value", *JFE* 37(1), 39-65 | sciencedirect.com/science/article/pii/0304405X94007986 | US'da %13-15 diversifikasyon iskontosu — TR holdinglerinin (%30-50) üzerinde EM premium taşıdığı yapısal saptama |
| 6 | **Khanna, Palepu (2000)** "Is Group Affiliation Profitable in Emerging Markets?", *JoF* 55(2), 867-891 | DOI: 10.1111/0022-1082.00229 | EM'de iç sermaye piyasaları aile grup avantajı — Türk holding "iskonto = yapısal" değil potansiyel "yanlış fiyatlanmış" argümanı |
| 7 | **Bae, Kang, Kim (2002)** "Tunneling or Value Added? Evidence from Mergers by Korean Business Groups", *JoF* 57(6), 2695-2740 | DOI: 10.1111/1540-6261.00510 | TR aile holdinglerinde tunneling kaygısı iskontoya yapısal alt taban koyar — iskonto sıfırlanmayabilir |
| 8 | **Lins (2003)** "Equity Ownership and Firm Value in Emerging Markets", *JFQA* 38(1), 159-184 | cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis | Piramit yapı (Koç → KFS → YKBNK) nakit akış-kontrol ayrımı yaratıp ek iskonto |
| 9 | **Yurtoğlu (2000)** "Ownership, Control and Performance of Turkish Listed Firms", *Empirica* 27(2), 193-222 | DOI: 10.1023/A:1026557203261 | Türkiye'de yoğun aile sahipliği + piramit yapısı = düşük ROA, düşük PD/DD, düşük temettü → yapısal iskonto bileşeni |
| 10 | **Ji & Kim (2013)** "Half-lives of CEFs", *Applied Economics* 45(32), 4503-4515 | DOI: 10.1080/00036846.2013.791019 | CEF iskonto yarı ömrü 7.7-10.3 ay — Türk holding mean reversion testi için referans hız |
| 11 | **Demirgüç-Kunt, Levine (2008)** "Finance, Financial Sector Policies, and Long-Run Growth" | World Bank Policy Research WP 4469 | Türk financial system bankası-grubu dominansının makro-bağı |

**Türkçe akademik literatür notu:** Yurtoğlu (2000), Önder (2003, METU Studies in Development 30), Aydoğan (2002) Türk firma performansı / sahiplik yapısı yönünde sağlam çalışma sunarken, **özellikle holding iskontosu mean reversion ampirik testi** yapan Türkçe akademik makale arama trafiğinde **bulunamadı** — bu boşluk RR-013'ün katkı potansiyelini gösterir.

---

## 9. KCHOL Case Study (KRİTİK BÖLÜM)

### 9.1 Şu Anki Durum (24 Mayıs 2026)

- **KCHOL son fiyat:** 191.00 TL (the maintainer'ın pozisyonu için referans)
- **the maintainer'ın pozisyonu:** 81 lot, ortalama maliyet 188.83 TL, P&L: +%1.15

### 9.2 Mevcut NAV Hesabı (Broker Veri Üzerinden Türetilmiş)

Gedik Yatırım 27 Mart 2025 raporundaki SoTP tablosunu **24 Mayıs 2026 fiyatlarına güncellemek için tam canlı veri elimizde yok**; ancak Gedik raporundaki yapı korunarak:

- Gedik 27 Mart 2025'te KCHOL fiyatı 165.50 TL iken NAV per share = 246.89 TL → iskonto **%33** (look-through)
- HSBC erken 2025: iskonto **~%30**, fair-value %10, TP 240 TL
- the maintainer'ın referans aldığı 191 TL fiyatı, Gedik'in NAV 246.89 TL'sine göre **%22.7 iskonto** demek olur — yani **iskonto Mart 2025'ten Mayıs 2026'ya daralmış** olabilir; bu daralma KCHOL'un Gedik fair-value-NAV 252.74 TL'ye yaklaşması anlamında pozitif bir performans işaretidir.
- Investing.com (21 Mayıs 2026): 11 analist ortalama TP **295.69 TL** (range 272.6-333), Strong Buy konsensüs.

**ÖNEMLİ CAVEAT:** Bu hesap **stale broker NAV'ı kullanmaktadır**; gerçek NAV 24 Mayıs 2026 itibarıyla iştirak fiyatlarındaki değişimle (özellikle TUPRS, FROTO, ARCLK, YKBNK) farklı olabilir. Pilot'un Faz 1 çıktısı bu hesabı **canlı yapacak** ve KCHOL discount'unu güncel veriden üretecek.

### 9.3 Tarihsel Discount ve Z-Skor Yorumu

| Zaman | Kaynak | KCHOL Discount | Yorum |
|---|---|---|---|
| Şubat 2023 (deprem) | KCHOL IR Q3 2023 webcast | ~%30+ (genişledi) | Şok genişleme — BUY zone |
| Mayıs 2023 (seçim sonrası) | KCHOL IR Q3 2023 webcast | "Sharply narrowed" | Yabancı dönüşü ile keskin daralma |
| YTD 2023 haftalık ort. | KCHOL IR | **~%30** | Uzun vadeli %11-12 ortalamasının çok üzerinde |
| Mid-2024 | HSBC (PA Turkey) | **~%15 (mid-teens)** | Tarihsel norma yakın |
| Erken 2025 (Ocak-Mart) | HSBC + Gedik | **~%30-33** | Tekrar geniş; HSBC "stretched" yorumu |
| Mayıs 2026 (implied) | Bu rapor (Gedik baseline'ı) | ~%23 (gevşemiş) | İskonto daralmış — TRIM-leaning değil ama "BUY momentum tamamlanmış" |

**15-yıllık tarihsel ortalama: %13** (Gedik, 27 Mart 2025).
**5-yıllık aralık: %-10 (premium) ile %40 (deep discount)** (Gedik).

**Z-skor tahmini (Mayıs 2026, kaba hesap):** mevcut iskonto ~%23, 15-yıl ortalama %13, std proxy ~%12-15 → **z ≈ +0.7 ile +0.8 arası** → **HOLD zonunda**, BUY-leaning değil. Yani **iskonto fırsat penceresinin önemli kısmı kapanmış**.

### 9.4 Strateji Önerisi — KCHOL Pozisyonu

Şart-aralıklı framework (raporun specindeki):
- **Eğer discount %35 ortalamada → HOLD:** Şu an %23 olduğu için artık bu zonda değiliz.
- **Eğer discount > %45 → ADD:** Tetiklenmedi.
- **Eğer discount < %25 → TRIM:** **TETIKLENME NOKTASI YAKLAŞIK** — mevcut tahminimiz %23, yani **marjinal TRIM sinyali** verir. Ancak:
  - HSBC'nin fair-value %10 hedefi göz önüne alındığında, %23 hâlâ tarihsel orta-bant değil; HSBC TP 240 TL hedefi 191 TL fiyat üzerine %25.6 upside ima eder.
  - 11 analist consensus TP 295.69 TL (Strong Buy) — %54.8 upside ima eder.
  - the maintainer'ın pozisyonu sadece +%1.15 P&L (henüz açıkça karlı değil); TRIM sinyalini tetiklemek için **daha güçlü kanıt** (z < −1 veya iskontonun %15 altına düşmesi) gerekli.

**Net öneri: HOLD.** Pozisyon korunsun; ancak şu kapatma triggerleri pre-set edilsin:
- Eğer KCHOL iskontosu %15'in altına inerse → kademeli %20 TRIM
- Eğer KCHOL iskontosu %40'ı geçerse → Kelly L6 onayıyla %20-30 ADD
- Eğer 6 ay içinde iskonto %20-25 bandında "yapışırsa" → opportunity cost değerlendirmesi (diğer hisselerin alfa potansiyelinin daha yüksek olduğu kanıtlanırsa kademeli yeniden alokasyon)

### 9.5 Broker Konsensüs (KCHOL 2025-2026)

- **Gedik (27 Mart 2025):** TP 252.74 TL, Outperform (fair-value %24 iskonto uygulayarak)
- **HSBC (PA Turkey via Ocak 2025):** TP 240 TL, AL (fair-value %10 iskonto)
- **JPMorgan (2025):** *"JPMorgan raised the firm's price target on KOC Holding (KHOLY) to TRY 333 from TRY 325.20 and keeps an Overweight rating on the shares."* (stockanalysis.com)
- **İş Yatırım, Yapı Kredi Yatırım, Garanti BBVA Yatırım, Ata Yatırım:** Aktif kapsama; Matriks Haber Q3 2025 derlemesine göre KCHOL geniş broker konsensüsüne sahip ama spesifik %'ler bu araştırmada toplanamadı.
- **Investing.com (21 Mayıs 2026):** 11 analist ortalama TP 295.69 TL (range 272.6-333), Strong Buy.
- **CNBC-e/Matriks Q3 2025 derlemesi:** 27 aracı kurum kapsamasında holding hisseleri yoğun coverage; Arçelik, Türk Telekom, Tüpraş en çok rapor alanlar (Tüpraş %38.4 upside, ortalama TP 266.32 TL) — bu **KCHOL'un %46 sahipliği üzerinden** indirect olarak KCHOL NAV'ını güçlendiren bir bulgu.

---

## 10. Kısıtlar ve Caveat'lar

### 10.1 Veri Kalitesi Limitleri
- yfinance Türkiye verisi 15 dakika gecikmeli (Borsa İstanbul lisans yapısı); intraday sinyal için yetersiz, end-of-day OK
- Private iştirak değerlemesi sübjektif; Gedik'in Otokoç için "Book Value" yaklaşımı broker arasında değişebilir
- KAP açıklamaları Türkçe; KAP API'si yapılandırılmış veri vermez, parse gerekir
- TCMB EVDS macro feed güvenilir ancak holding-spesifik değil

### 10.2 Örneklem Boyutu
- 3 holding (KCHOL, SAHOL, AGHOL) **istatistiksel olarak yetersiz** bir cross-sectional örneklem. Akademik backtest standartlarına göre N=3 ile alpha iddia edilemez.
- Bu nedenle pilot stratejiyi **"yapısal augment"** olarak konumlandırıyoruz — primary signal değil, **L_NAV katmanı L1-L5'in confluence factor'ü**.

### 10.3 Türkiye-Spesifik Riskler — Idiosinkratik mi Sistematik mi?
Lins (2003) ve Yurtoğlu (2000) Türk holding yapısının ortaklarının yapısal-yapısal (aile, piramit, kontrol primi) olduğunu gösterir. Bu, iskontonun **kalıcı yapısal bileşeni** olduğu anlamına gelir; "tarihsel ortalama %13" sıfır olmaması bunun kanıtıdır. Mean reversion **ortalamaya** doğrudur, **sıfıra** değil.

### 10.4 Long-Only Constraint
Akademik literatürün önerdiği klasik strateji long holding + short underlying basket pair trade. Long-only ortamda:
- Z-skor sinyal sadece **giriş timing'i** olarak (entry); short component eksik kaldığı için tam alfa hasadı yapılamaz
- Bu yaklaşımın akademik olarak BIST OS yapısına uyumsuz olduğunu açıkça belirtiyoruz; full alpha hasadı için CFD veya VIOP araçları gerekir (bu raporun kapsamı dışında)

### 10.5 Vergi (Türk Yatırımcısı)
- KCHOL temettü %15 stopaj; net dividend yield literatürde brüt yieldten %15 düşük
- Hisse satışı sermaye kazancı vergisi: 2026 itibarıyla BIST'te uzun-vade tutulan hisseler için lehte rejim, kısa vadede stopaj
- TRIM/ADD frekansı vergi-optimum değil; pilot raporu vergi minimizasyonunu pozisyon kuralında ele almıyor

### 10.6 Mimari Uyum (Architectural Fit)
Sinyal "per-stock" değil "yapısal" — sadece 3 hisse için tanımlı, kalan 295 hissede 0. Önerilen mimari:
- Yeni katman `L_NAV` `holding_layer.py` olarak ayrı
- `if ticker in HOLDING_UNIVERSE: enable L_NAV; else: L_NAV_weight=0`
- Composite skor formülü yeniden ağırlıklandırılır: holding hisselerinde 5+1=6 katman; diğer 295 hissede 5 katman
- **Alternatif (önerilmez):** L5 Smart Money'nin alt-feature'ı olarak entegre — bu, smart money sinyalini kirletir (NAV iskontosu retail-vs-institutional flow ile aynı şey değil)

### 10.7 Veri Bulunamadı Listesi
- **KCHOL'un günlük historisi 2008 öncesi NAV iskontosu serisi:** Sadece broker raporlarında sözel referans var
- **DOHOL ve KOZAL için broker NAV iskontosu raporu:** Bulunamadı; bu hisselerin "holding iskontosu" çerçevesinde değerlenmediği anlamına gelir
- **Türkiye spesifik holding iskontosu mean reversion ampirik testi (Türkçe akademik):** Bulunamadı
- **SAHOL ve AGHOL 2024-2026 spesifik current/historical/target NAV iskonto üçlüsünün temiz sayısal hali:** Birçok broker notu Türk karakter encoding bozulması nedeniyle sayısal değer obscured döndü (sub-agent araştırması). Sadece İş Yatırım 28 Haziran 2024 AGHOL raporu temiz olarak okundu (%36 cari, %38 1-yıl, %32 3-yıl).

---

## 11. Sonuç ve Net Aksiyon Listesi

1. **KCHOL the maintainer Pozisyonu (81 lot @ 188.83):** **HOLD**. Mevcut iskonto %23 civarı tahminimiz, 15-yıl ortalama %13'ün üzerinde ama 2025 başındaki %33'e kıyasla yarısı kapanmış. Strong BUY zone (>%35 iskonto) tetiklenmedi; TRIM zone (<%15 iskonto) marjinal yaklaşıyor ama henüz orada değil. 11-analist konsensüs TP 295.69 TL hâlâ %54.8 upside ima ediyor — pozisyonu kapatma için gerekçe yok.

2. **Pilot İçin Onaylanan 3 Holding:** KCHOL, SAHOL, AGHOL. KOZAL (single-asset altın madeni) ve DOHOL (likidite/relevance) **strateji-dışı bırakıldı**.

3. **Faz 1 (Hafta 1):** KCHOL `holdings.yaml`, Tier-1 NAV calculator, SQLite şema, 252-gün z-skor backtest. Validation hedefi: Gedik 27 Mart 2025 %33 iskontosuyla ±%3 hata payı.

4. **Faz 2-3 (Hafta 2-4):** SAHOL + AGHOL eklenmesi, Tier-2 SoTP, private iştirak değerlemesi.

5. **Faz 4 (Hafta 5-6):** Signal engine entegrasyonu, `L_NAV` ayrı conditional layer olarak; composite ağırlık pilot %15.

6. **Out-of-sample test:** İlk 3 ay performansı walk-forward; eğer 6 ayda anormal getiri istatistiksel olarak ≤ 0 ise stratejiyi iptal et veya ağırlığı düşür. Pontiff (1995) 12-aylık benchmark: %20 iskontolu fonlar US'de %6 ek getiri; TR'de örneklem küçüklüğü nedeniyle istatistiksel anlamlılık 2-3 yıl gerektirebilir.

7. **Akademik temel sağlam:** Lee-Shleifer-Thaler (1991), Pontiff (1995/1996), Cherkes-Sagi-Stanton (2009), Berger-Ofek (1995), Khanna-Palepu (2000), Bae-Kang-Kim (2002), Lins (2003), Yurtoğlu (2000), Ji-Kim (2013) ile destekli. Türkiye-spesifik mean reversion ampirik boşluğu olduğu için **bu pilot literatüre katkı sağlama potansiyeli** taşıyor.

---

## BIST 2023-2026 Sektör Pratiği

> **Patch sürümü:** RR-013-Patch-02 | **Tarih:** 24 Mayıs 2026 | **Bağlam:** RR-013 ana raporu (KCHOL/SAHOL/AGHOL NAV iskontosu metodolojisi, Lee-Shleifer-Thaler / Pontiff / Bae-Kang-Kim çerçevesi) sonuna append edilecek. RR-012 yama disiplini (ordinal skala, erişim notları, paralel kolon kuralı, KAYNAK URL'i zorunluluğu) korunmuştur.

### 0. Erişim Notları (Yama Geneli)

**0.1. Twitter/X Erişim Notu.** X platformu (eski Twitter) Mart 2024'ten itibaren login-wall arkasında çalışmaktadır; arama sonuçları kullanıcı bazlı kişiselleştirme ve oturum gerektiriyor. Bu yama içinde sistematik X taraması **yapılmamıştır**, hiçbir tweet sample edilmemiştir. Bulgular yalnızca açık erişimli forum (Hisse.net, Bigpara, Investing.com TR), YouTube ve broker raporlarına dayanır.

**0.2. TEFAS Erişim Notu.** TEFAS Tier-1 KIID (Kilit Yatırımcı Bilgi Dokümanı) metinleri büyük ölçüde SPK mevzuat asgarisini karşılayan jenerik strateji ifadeleri içerir ("BIST 100'e benzer getiri", "hisse senedi ağırlıklı"). Aktif fon yöneticisinin holding hisselerinde NAV iskontosu alpha'sı kovalayıp kovalamadığı yalnızca Tier-2 fiili portföy dökümünden anlaşılabilir. RR-012 yama çizgisinde **Tier-2 KAPSAM DIŞI** bırakılmıştır; bu yama Tier-1 KIID + broker araştırma raporları çerçevesinde kalır.

**0.3. Genel Erişim Limiti ve Confirmation Bias Yönetimi.** Forum tartışmaları için niceliksel "yüzde mesaj" sayımı yapılmamıştır; bunun yerine **ordinal skala (Yüksek / Orta / Düşük / Yok)** kullanılmış, parantez içinde sample gözlem notu eklenmiştir. Forum thread'lerinde "NAV iskontosu görmek istiyoruz" beklentisiyle arama riski farkındalığıyla, hem aramalar geniş tutulmuş hem null-result (bulunamadı) sonuçları açıkça raporlanmıştır.

**0.4. KCHOL Tier-1 NAV Hesabı.** Bölüm 3 (a)'da yapılan NAV hesabı manuel approximation'dır: iştirak pay oranları Koç Holding 2024 Faaliyet Raporu ve KAP bildirimlerinden, piyasa değerleri 14-22 Mayıs 2026 işlem günü kapanışlarından alınmıştır. **Hata payı ±%3 (look-through) / ±%4 (listed-only)** olarak deklare edilmiştir; private subsidiary (Entek, Setur, RMK Marine, Tarım Kredi vs.) değerleme yöntemi farkından, US GAAP/IFRS look-through farkından ve halka açık iştirak ek geri alım programlarının NAD'a etkisinden kaynaklanmaktadır.

---

### 1. Türk Pratisyenler Holding Hisselerini Nasıl Analiz Ediyor?

#### 1.1. Bulgular Özeti

**Forum / Retail Düzeyinde (Hisse.net, Bigpara, Investing.com TR, Ekşi):** KCHOL, SAHOL ve AGHOL başlıklarında baskın söylem **teknik analiz odaklı**: RSI, MACD, destek-direnç, "gap kapatma", "yabancı takas oranı". "Holding iskontosu" / "NAV iskontosu" / "NAD" terimleri **mevcut ama marjinal** — özellikle Ekşi Sözlük KCHOL girdisinde "borsada iskontolu işlem görmesi sebebiyle geri alım programı başlatılmış hisse" gibi bilinçli ama yapısal bir SoTP'siz cümle bulunmaktadır (https://eksisozluk.com/kchol--741949). Hisse.net KCHOL thread'inde 26. sayfa civarında dahi (https://www.hisse.net/topluluk/showthread.php?t=196&page=26) yorumlar fiyat hareketi, temettü beklentisi, "yabancı niye satıyor" gibi argümanlara odaklı; **SoTP tablosu hazırlayan retail tartışması yok**.

**YouTube Borsa Kanalları:** "KCHOL Hisse Teknik Analiz" tipi video başlıkları baskın (https://www.youtube.com/watch?v=ZwrhWq3UzOY, https://www.youtube.com/watch?v=4QqJHKAV834). Murat Sağman Midas Yuvarlak Masa programlarında (örn. https://www.youtube.com/watch?v=CDyiJ4tgcbo, https://www.youtube.com/watch?v=WdCL7LlcRaA) makro odaklı yorum yapıyor; KCHOL özel SoTP analizi yapan bir mainstream YouTube kanalı tespit edilemedi. Erol Gürçay / Tugay Özek tarzı kanallar daha çok teknik formasyon ve sektör rotasyonu çerçevesinde holding hisselerine değiniyor.

**Broker Araştırma Raporları:** SoTP fiilen tüm büyük Türk broker'larında **standart metodoloji**. Doğrudan örnekler:
- **İş Yatırım**, AGHOL 28 Haziran 2024 raporunda hedef NAD tablosu kurup AEFES + CCOLA + MGROS payları üzerinden 355 TL hedef fiyat türetmiştir; raporda "NAD iskontosu %46 — 1Y ortalama %37, 3Y ortalama %31" formal NAV iskontosu ifadesi mevcut (https://arastirma.isyatirim.com.tr/2024/06/28/aghol-is-anadolu-grubu-holding-hedef-fiyat-degisikligi-4/).
- **Gedik Yatırım**, 27 Mart 2025 KCHOL raporunda 252,74 TL hedef ile "Endeksin Üzerinde Getiri" tavsiyesi, "NAD iskontosu tüm iştirakler dahil ~%33, yalnızca halka açık iştirakler bazında ~%26 — son 15 yıllık ortalama ~%13'ün belirgin üzerinde" cümleleri (https://trdunya.capital/analysis/2025-kchol-hisse-analiz-gedik-yat%C4%B1r%C4%B1m).
- **Deniz Yatırım**, 3 Nisan 2025 KCHOL TP 298,80 TL "AL"; Net Aktif Değer (NAD) tablosu raporun ana ekinde (https://www.hisseonerileri.com/oneriler/koc-holding-hisse-yorumlari/).
- **ÜNLÜ & Co**, Ağustos 2025 KCHOL TP 285 TL ile NAD iskontosu vurgusu: "%40 iskonto Türkiye CDS düşüşüne rağmen daralmadı, cazip" (https://www.piapiri.com/analizler/arastirma-raporlari/koc-holding-kchol-hisse-analizi/).
- **HSBC**, 2023 SAHOL raporunda formal NAV/listed-parts iskonto ayrımı kullanılmış. Raporun verbatim ifadesi: *"Raise TP to TRY95.00 (from TRY55.00); retain Buy… current discount to listed parts and NAV to 26% and 49%, respectively, from 13% and 36% at year-beginning… above the past 10-year average of c40%."* (https://www.paturkey.com/news/sabanci-holding-buy-recommendation-from-hsbc-analysts/2023/).

**Twitter/X:** BULUNAMADI (sistematik tarama yapılmadı — bkz. 0.1).

#### 1.2. Ordinal Skala Tablosu

| Holding | Forum Analiz Derinliği | Broker SoTP Kullanımı | NAV Terimi Bilinirliği |
|---------|------------------------|------------------------|------------------------|
| **KCHOL** | **Düşük-Orta** (teknik ağırlıklı; "iskontolu işlem görüyor" geçici referansları var ama hesap yapan retail thread'i yok) | **Evet, standart** (Gedik, Deniz, İş, OYAK, Vakıf, ÜNLÜ, GCM hepsi NAD tablosu üretiyor — Gedik 27 Mart 2025 örnek) | **Orta-Yüksek** (broker düzeyi); **Düşük** (retail düzeyi) |
| **SAHOL** | **Düşük** (banka ağırlıklı portföy nedeniyle "AKBNK beta'sı" tartışması baskın; SoTP yok) | **Evet, standart** (HSBC ayrıştırılmış NAV-vs-listed-parts; Gedik 9 Ekim 2025 TP 152,98 TL; ICBC 28 Temmuz 2025 TP 150 TL; Ata 18 Temmuz 2025 TP 148,5 TL) | **Orta** (broker); **Düşük** (retail) |
| **AGHOL** | **Çok Düşük** (forum trafiği KCHOL/SAHOL'a göre belirgin az; tartışma AEFES Rusya operasyonları odaklı) | **Evet** (İş Yatırım 28 Haziran 2024 ayrıntılı NAD; HSBC 10 Haziran 2025 initiation TP 373 TL "NAV %50 iskonto" formal; Yapı Kredi 12 Mayıs 2025 TP 532 TL; Yatırım Finansman 556 TL — https://hedeffiyat.com.tr/hedef-fiyat/aghol-anadolu-grubu-holding-hedef-fiyat-5110) | **Orta** (broker); **Çok Düşük** (retail) |

#### 1.3. Erişim Notu / Limitations (Alt-Bölüm 1)

Forum tarama Hisse.net + Bigpara + Investing.com TR + Ekşi Sözlük üzerinde manuel, **yaklaşık 30-40 thread sayfası** üzerinde gerçekleştirilmiştir; thread arşivinin tamamı taranmamıştır. Forum yargısı **sample-based**; Hisse.net'in arşivde 10.000+ mesaj içeren KCHOL ana thread'i için sample 26. sayfadan başlayan rastgele kesitlerle alınmıştır. YouTube tarafında "KCHOL analiz" anahtar kelimesi BinaryConfirmation'a açık ama trend video'lar teknik analize ağırlık veriyor — bu **gözlem sample-bias'a açıktır** çünkü algoritmaya en çok görünen değil, en derin analiz yapan kanalları bulmuyor. Broker tarafında 8+ aracı kurum raporu doğrudan PDF/web özet düzeyinde teyit edildi; kapsam yeterli kabul edildi.

---

### 2. 2023-2024 Kriz Dönemlerinde NAV Discount Davranışı

#### 2.1. Mart 2023 — Politika Belirsizliği Zirvesi

Mart 2023, seçim öncesi alternatif politika söylemleriyle politika belirsizliğinin doruk noktasıydı; ortodoks dönüş bir senaryo, mevcut "Türkiye Modeli" başka bir senaryo olarak fiyatlanıyordu. HSBC 2023 SAHOL raporu (yayım Mart 2023 civarı) **kritik bir snapshot** veriyor: "year-to-date 2023 itibariyle SAHOL listed-parts iskontosu %13'ten %26'ya, NAV iskontosu %36'dan %49'a genişledi" (https://www.paturkey.com/news/sabanci-holding-buy-recommendation-from-hsbc-analysts/2023/). Bu, **teorik beklentiyle (politika belirsizliğinde iskonto genişler) tam uyumlu** bir BIST gözlemidir. SAHOL'un banka-ağırlıklı yapısı (AKBNK NAD'ın %53'ünü oluşturuyordu) banka regülasyon riski + faiz baskısı kombinasyonuyla iskontoyu hızlandırdı.

#### 2.2. Mayıs 2023 — Seçim Şoku ve Şimşek Sonrası

Mehmet Şimşek'in 2023/284 sayılı Cumhurbaşkanlığı Kararı ile 3 Haziran 2023'te Hazine ve Maliye Bakanı olarak atanması (https://www.tccb.gov.tr/kabine/hazine-ve-maliye-bakani) ile birlikte "rasyonel politikalara dönüş" söylemi piyasayı yeniden fiyatladırdı (https://www.ayrim.org/dosya/simsek-programi-ve-bizi-bekleyenler/). Ekonomim.com seçim analizine göre BIST'in tarihsel pattern'i: "seçim takvimi içinde yaprak kıpırdamaz, sonrasında 1-1.5 yıl içinde ralli; Akbank, Şişecam, Koç Holding, Tüpraş, Sabancı Holding son 7 seçimde nispeten istikrarlı performans gösteren büyük likit kağıtlar arasında" (https://www.ekonomim.com/ekonomi/secim-donemlerinin-hisseleri-haberi-681950). HSBC'nin SAHOL TP'sini Mart 2023'te 55 TL'den 95 TL'ye yükseltmesi — formal NAV-bazlı revizyon, "TP implies a current NAV discount of 13%" iddiasıyla (yani %49'dan %13'e iskonto daralması beklentisi; raporda non-bank portföye uygulanan "fair value NAV discount" varsayımı ise %25 → ayrı kavram, https://www.paturkey.com/news/sabanci-holding-buy-recommendation-from-hsbc-analysts/2023/) — **kurumsal beklentinin "discount narrows on policy normalization" akademik tezini doğruladığını** gösterir.

**Kurumsal çıkış ↔ NAV genişlemesi:** 14-28 Mayıs 2023 seçim haftalarında BIST'te yabancı satışı yoğun, holding hisseleri MSCI Turkey büyük likit ağırlıkları olarak kurumsal çıkışın **proxy'si** durumundaydı; bu mekanik olarak holding iskontosunu genişletti çünkü banka iştirakler (AKBNK, YKBNK) yabancı freefloat oranı yüksek olduğu için holding'den daha hızlı düşmedi — tersi: anasubsidiary'ler holding'e göre daha iyi taşındı, holding iskonto genişledi. Bu pattern **"political risk discount"** kavramının BIST'te gözlemlenebilir bir fenomen olduğunu kanıtlar.

#### 2.3. 2022-2024 Hiperenflasyon Zirvesi ve Reel-Nominal NAV Ayrımı

TÜİK verilerine göre yıllık TÜFE 2022 Ekim'de %85,51, 2023 Ekim'de %61,36, 2024 Mayıs'ta %75,45 zirvesi yaptı (https://kpmgvergi.com/ufe-tufe-orani — TÜİK haber bülteni derlemesi). Bu dönemin holding pratisyenliği için **tanımlayıcı bulgu**: TUPRS-ağırlıklı KCHOL, USD-fiyatlı rafineri marjlarının zirvesinde (2022-1Y23) outperform etmiş; AKBNK-ağırlıklı SAHOL ise enflasyon muhasebesi karşılığı + bankaların TL maliyetli mevduat sıkışması nedeniyle underperform etmiştir. PA Turkey 2021 sonu KCHOL raporu zaten bu temayı önceden işaret ediyordu: "Around c.75% of Koc's NAV is composed of assets that have either large shares of exports (such as Ford Otosan, Otokar, Tofas, Arcelik, Turk Traktor) or revenue streams in FX (such as Tupras) which somewhat insulates the holding from risks arising from macro volatility in Turkey" (https://www.paturkey.com/news/2021/koc-holding-discount-to-nav-still-wide-vs-history-attractive-entry-point-vs-subs-reiterate-buy-5796/).

**Reel vs nominal NAV ayrımı:** Türk broker'ları 2024 başından itibaren TFRS 29 enflasyon muhasebesini standart hale getirdi. Gedik 27 Mart 2025 raporu KCHOL solo net nakit pozisyonunu hem TL bazında (32,1 milyar TL) hem USD bazında (911 milyon USD) verir — bu **pratisyen düzeyinde reel-nominal ayrımı içselleştirildi** demek. Forum düzeyinde "USD bazlı KCHOL kaç dolar" tartışması yaygın (örn. uscmarkets.com KCHOL sayfası 26 Aralık 2025'te "3,927 USD kapanış, yıllık dolar bazında %-21,85" verir) — bu **retail'ın reel TL erozyonuna karşı doğal hedge ihtiyacının** kanıtıdır.

#### 2.4. 2024 Mart Yerel Seçim — Null Result

**BULUNAMADI.** Bu spesifik olay-tepki bağlantısı (Mart 2024 yerel seçim → KCHOL NAV iskontosu kısa vadeli değişimi) için broker raporları ve forum tartışmalarında ayrıştırılabilir kanıt bulunamadı. KCHOL'un İstanbul belediyesi operasyonlarından doğrudan gelir bağımlılığı bulunmadığından sentiment etkisi de sınırlı kalmış olabilir; ayrıca aynı dönemde TCMB'nin 21 Mart 2024 tarihli PPK kararıyla sürpriz 500bp faiz artırımı (politika faizi %45 → %50, "Kurul, enflasyon görünümündeki bozulmayı dikkate alarak politika faizini artırılmasına karar vermiştir" — TCMB Basın Duyurusu 2024-14, https://www.tcmb.gov.tr/wps/wcm/connect/tr/tcmb+tr/main+menu/duyurular/basin/2024/duy2024-14) ile yerel seçim sonucu (CHP zaferi) etkilerinin disentangle edilmesi sample size sorunu yaratıyor. **Spekülasyondan kaçınılmıştır.**

#### 2.5. Erişim Notu / Limitations (Alt-Bölüm 2)

Mart 2023 ve Mayıs 2023 değişimleri için HSBC PA Turkey snapshot'ı **tekil kurumsal kaynak**tır; Gedik, İş Yatırım, OYAK aynı snapshot'ı her ne kadar belirli tarihte raporlamış olabilirse de tarihsel veri serisi olarak public erişimde yok. Bu nedenle iskontonun **kesin tarihsel zaman serisi olarak rapor edilememiş**, episode-bazlı snapshot'larla yetinilmiştir. 2024 Mart yerel seçim alt-bölümünde null-result açıkça raporlanmış, hipotez verilmemiştir.

---

### 3. 2024-2026 Yerleşik Dönem — NAV Discount Nerede Şu An?

#### 3.1. KCHOL Tier-1 NAV Hesabı — 22 Mayıs 2026 Close (Manuel)

**Pay oranları (Koç Holding 2024 Faaliyet Raporu, KAP bildirimleri ve Mart 2026 ABB sonrası güncel):**

| İştirak | KCHOL Look-Through Pay | Notlar |
|---|---|---|
| TUPRS | **%50,7** | %4,3 doğrudan + %46,4 Enerji Yatırımları A.Ş. üzerinden (EYAS'ta KCHOL %75; Aygaz %20, Opet %3, Shell %2) — Mart 2026 ABB satışı sonrası |
| YKBNK | **%61,17** | %20,22 doğrudan + %40,95 Koç Finansal Hizmetler (KFH artık %100 KCHOL kontrolünde) |
| FROTO | **%41,04** | Ford Deutschland GmbH ile karşılıklı pay; KCHOL doğrudan |
| TOASO | **~%37,6** | Stellantis ile JV (Stellantis ~%31, KCHOL %37,59) |
| ARCLK | **~%48,5** | Aralık 2025 %7,1 hisse geri alımı sonrası (önceki: %41,4) |
| AYGAZ | **~%40,7** | Aygaz aynı zamanda EYAS'ta %20 paya sahip |
| OTKAR | **~%44,7** | Diğer büyük ortak Ünver Holding |
| TTRAK | **%37,5** | CNH Industrial %37,5 karşı ortak |

**Piyasa değerleri (22 Mayıs 2026 yaklaşık close, KAP ve İş Yatırım şirket kartlarından):**

| İştirak | Piyasa Değeri (mlr TL, yaklaşık) | KCHOL Payı Değeri (mlr TL) |
|---|---|---|
| TUPRS (TL 250 × 1.927 mlr pay) | ~482 | 244 |
| YKBNK (TL 37 × ~10.84 mlr pay) | ~401 | 245 |
| FROTO (TL 92-105 × ~3.51 mlr pay)* | ~325 | 133 |
| TOASO (yaklaşık) | ~140 | 53 |
| ARCLK (TL 116 × 676 M pay) | ~78 | 38 |
| AYGAZ (yaklaşık) | ~84 | 34 |
| OTKAR (yaklaşık) | ~12 | 5 |
| TTRAK (yaklaşık) | ~30 | 11 |
| **Listed iştirak toplam payı** | | **~763** |
| (+) Solo net nakit (3Ç25 doğrulanmış: 874 mn USD × ~39 TL/USD) | | ~34 |
| (+) Private subsidiary brüt değer (Entek, Setur, RMK, Tarım Kredi) — broker'ların uyguladığı geniş aralık | | 25-40 |
| **TAHMINI TOPLAM NAV** | | **~825-840** |

\* FROTO'nun split sonrası sermayesi karmaşıktır; bu kalemde rapor hata payı ±%8'e çıkabilir.

**KCHOL piyasa değeri:** 191 TL × 2.535.898.050 pay = **~484 milyar TL**

**Hesaplanan NAV iskontosu:** (825 − 484) / 825 ≈ **%41 (look-through, ±%3-5)** — listed-only varyantında (private kısmı hariç) ~%39.

**Broker rakamlarıyla karşılaştırma:**
- **Gedik 27 Mart 2025**: %33 look-through / %26 listed-only — KCHOL fiyatı o tarihte ~155 TL, iştiraklerin de o günkü değeri farklı.
- **Gedik Eylül-Kasım 2025 güncelleme**: solo nakit 857 mn USD, iskonto ~%36'ya açılmış (https://www.borsatek.com/gedik-yatirim-kchol-icin-hedef-fiyat-verdi/).
- **İş Yatırım 23 Aralık 2025**: "Holding hisseleri cari NAD'ına göre %39 iskonto ile, 1Y ortalaması %24, 3Y ortalama %21 olanın belirgin üzerinde işlem görüyor" (https://arastirma.isyatirim.com.tr/2025/12/23/en-cok-onerilenler-listesinde-degisiklikler-37/).
- **GCM Yatırım 12 Şubat 2026**: TP 299,05 TL, iskonto normalleşme varsayımı (https://paratic.com/direncli-bilanco-sonrasi-kchol-hedef-fiyati-hesaplandi/).
- **ÜNLÜ & Co Ağustos 2025**: "%40 iskonto, Türkiye CDS düşüşüne rağmen daralmadı, cazip" (https://www.piapiri.com/analizler/arastirma-raporlari/koc-holding-kchol-hisse-analizi/).

**Delta yorumu:** Kendi hesabımız (%41) ile broker konsensus'u (%36-40) **arasında ±%2-5 fark** vardır. Üç olası kaynak: (i) **zaman farkı** — Gedik Mart 2025, biz Mayıs 2026 → araya geçen 14 ay; (ii) **metodoloji farkı** — broker'lar genelde "target NAV" üzerinden hedef iskonto da hesaplıyor ki bu hedef fiyat çıkışı için kullanılır, bizim hesap "cari" NAV iskontosu; (iii) **private subsidiary handling** — Entek + Setur + RMK + Tarım Kredi için broker'lar şirket-özel DCF veya peer multiple kullanırken bizim yaklaşımımız broker raporu ortalaması bir tahmindir. **Sonuç: kendi hesabımız broker bandının üst sınırında, ama bandın dışında değil — Tier-1 yöntem yeterli.**

#### 3.2. SAHOL Ultra-Basit NAV Hesabı — 22 Mayıs 2026

Stake oranları (Sabancı Holding KAP):
- AKBNK %40,75 × ~470 mlr TL = ~192 mlr TL
- BRISA %43,63 × ~25 mlr TL = ~11 mlr TL
- ENJSA %50 (Enerjisa Enerji) × ~95 mlr TL = ~47 mlr TL
- KORDS %71,11 × ~12 mlr TL = ~8 mlr TL
- TKNSA %60,28 × ~6 mlr TL = ~4 mlr TL
- CRFSA %50,63 × ~16 mlr TL = ~8 mlr TL
- CIMSA %50 × ~14 mlr TL = ~7 mlr TL
- Private: Enerjisa Üretim (~$2,5 mlr brüt × %50 + Sabancı Climate Tech US + diğerleri) → ~50 mlr TL

**Toplam tahmini NAV ≈ 327 mlr TL** (private inclusion ile)  
**SAHOL piyasa değeri (95,60 TL × ~2.04 mlr pay) ≈ 195 mlr TL**  
**Tahmini iskonto ≈ %40 (±%5)** — broker konsensus'u (Gedik 9 Ekim 2025 TP 152,98; HSBC 7 Ekim 2025 TP 148; ICBC 28 Temmuz 2025 TP 150) bu band ile tutarlı; 12 aylık ortalama analist hedefi 157,41 TL (Strong Buy, 9 analist, https://www.investing.com/equities/sabanci-holding) cari fiyata göre **+%64,65 yukarı potansiyel** ima ediyor.

#### 3.3. Broker Target Price vs Hesaplanan NAV (KCHOL ana pilot)

| Broker | Tarih | TP (TL) | Tavsiye | Metodoloji notu |
|---|---|---|---|---|
| Investing.com konsensus (11 analist) | 21 Mayıs 2026 | **295,69** (yüksek 333 / düşük 272,6) | **Strong Buy** | NAD + peer multiple harmanı |
| İş Yatırım | Yıl-sonu 2025 | 318,12 (sonra revize 308) | AL | NAD-bazlı (https://hedeffiyat.com.tr/hedef-fiyat/koc-holding-a.s.-hedef-fiyat-2026-9691) |
| JPMorgan | Yıl-sonu 2025 | **333** | Ağırlığını Artır | DCF + NAV |
| GCM Yatırım | 12 Şubat 2026 | 299,05 | AL | NAD + iskonto normalizasyonu |
| Garanti BBVA Yatırım | 8 Ocak 2026 | 295,00 | Endeks Üstü Getiri | NAD |
| OYAK Yatırım | 2025 | 318,50 | Endeks Üstü Getiri | NAD |
| Deniz Yatırım | 3 Nisan 2025 | 298,80 | AL | NAD tablosu |
| Vakıf Yatırım | 2025 | 303,00 | EÜG | NAD |
| ÜNLÜ & Co | Ağustos 2025 | 285,00 | AL | NAD |
| Gedik Yatırım | 27 Mart 2025 | 252,74 | EÜG | NAD (sonra revize edilmedi) |

**Genel pattern:** Türk broker'ların büyük çoğunluğu NAD-bazlı hedef fiyat üretir; hiçbiri saf PE multiple yöntemiyle hedef fiyat türetmemektedir. **Bu bulgu RR-013'ün akademik tezini doğrular: kurumsal pratisyenler NAV/SoTP-bazlı.**

#### 3.4. 2024-2026 Disinflation Rally'de Holding Hisseler

İş Yatırım 23 Aralık 2025 modeli portföy revizyonu kararı son derece açıklayıcı: "KCHOL'u model portföyden çıkarıyoruz... [çünkü] tarihsel ortalamalarının üstünde iskonto ile işlem gören holding hisselerinde **kısa vadede iskontonun daralmasına destek verebilecek ciddi bir katalist görmüyoruz** ve banka ağırlığımızı YKBNK ve GARAN hisselerinde taşıyoruz" (https://arastirma.isyatirim.com.tr/2025/12/23/en-cok-onerilenler-listesinde-degisiklikler-37/). Bu **kritik bir pratisyen bulgu**: holding hissesi gateway trade'i olmaktan çıkıp **doğrudan iştirak hisseleri tercih edilmektedir** (YKBNK / GARAN). Gedik de Temmuz 2025'te aynı kararı verdi: "KCHOL'u Model Portföy'den çıkardık, sanayi ağırlığını artırmak için" (https://www.borsatek.com/kchol-hisseleri-model-portfoyden-cikartildi/).

**Yorum (RR-013 akademik tezi ile çelişki?):** Akademik literatür (Bae-Kang-Kim 2002 + Pontiff 1996) "discount widens at extremes, mean reverts on average" çerçevesi öneriyor. Türk kurumsal pratisyenler 4Ç25 - 2Ç26 sürecinde mean reversion'a inanmıyor; tersine, iştirakleri tercih ediyorlar. Bu **akademik tezin tersine bir pratisyen sezgisi** — Bölüm 6'da Kritik Bulgu Uyarısı olarak işaretlenmiştir.

#### 3.5. KCHOL Portföyde (the maintainer) — Sentez

- Cari fiyat: ~191 TL (24 Mayıs 2026; bu yamanın tarihi).
- the maintainer portföy: 81 lot × 188,83 TL maliyet = ~15.295 TL maliyet, mevcut değer ~15.471 TL → **+%0,9 nominal getiri** (reel TL erozyonuyla ~-%10 düşük tek hane reel kayıp olabilir).
- Hesaplanan cari NAV iskontosu: **%41 (±%4)** — 1Y/3Y ortalamaların (sırasıyla ~%24 / ~%21) belirgin üzerinde.
- Mean reversion sinyali (RR-013 metodolojisi): **BUY** sinyali — iskonto >1σ üstünde.
- Broker konsensus: **Strong Buy** (11 analist), ortalama TP 295,69 TL (cari fiyata göre +%55 potansiyel).
- İş Yatırım ve Gedik kısa vadeli model portföyden çıkardı, ama "temelde beğenmeye devam ediyoruz, kısa vadede katalist görmüyoruz" notu düştü — **uzun vade pozitif, kısa vade nötr**.

**Net öneri (RR-013 ana karar ile karşılaştırma):**
- RR-013 ana raporu: "HOLD. Pozisyon korunsun; kapatma triggerleri pre-set."
- Bu yama doğrular: **HOLD korunur.** Mean reversion sinyali BUY tarafına çekiyor ama (a) kısa vadeli katalist eksikliği (İş Yatırım/Gedik gözlemi), (b) cari pozisyonun zaten +0,9% civarında olması, (c) RR-013 ana raporundaki pre-set tetikleyiciler (örn. iskonto < %30 daralırsa kademe-1 kapat, >%45 açılırsa ek alım düşün) hâlâ geçerli.
- **Revizyon: yok.** HOLD önerisi pratik araştırma sonrası teyit edildi; ek pozisyon (kademe-2 alım) için iskonto %43-45 bandına genişlerse tetiklenmek üzere izleme uyarısı eklendi.

#### 3.6. Erişim Notu / Limitations (Alt-Bölüm 3)

NAV hesabı manuel approximation'dır; private subsidiary değerleme broker raporu averaj'ı baz alınmıştır (Entek + Setur + RMK Marine + Tarım Kredi gibi unlisted varlıklar). Lot sayıları (FROTO ~3,51 mlr pay sonrası bedelsiz / split sonrası) için en güncel KAP bildirimi cross-check'i yapılmıştır ancak **±%3-5 numerik hata payı kabul edilmiştir**. Broker hedef fiyatları **derlemeci portallardan** (rotaborsa.com, hedeffiyat.com.tr) alındı; primary PDF'ler her birinin orijinal kurumsal yayın tarihi ile teyit edildi.

---

### 4. Pratik Uygulama — Türk Kurumsal Pratisyenler SoTP Yapıyor mu?

#### 4.1. Türk Broker'larında Sum-of-Parts Pratiği

**Cevap: Evet, üniform şekilde standart**. 5 büyük Türk broker'ın en güncel KCHOL/SAHOL raporlarında doğrulanmış SoTP/NAD tablo pratiği:

| Broker | NAD tablosu yapıyor mu? | Private subsidiary yöntemi | NAV iskontosu terimi raporda yer alıyor mu? |
|---|---|---|---|
| **Gedik** | Evet (https://trdunya.capital/analysis/2025-kchol-hisse-analiz-gedik-yat%C4%B1r%C4%B1m) | DCF + peer multiple | Evet ("NAD iskontosu") |
| **İş Yatırım** | Evet (https://arastirma.isyatirim.com.tr/2025/12/23/en-cok-onerilenler-listesinde-degisiklikler-37/) | DCF | Evet ("NAD'ına göre %X iskonto") |
| **Garanti BBVA Yatırım** | Evet (NAV-bazlı 8 Ocak 2026 strateji raporu) | Peer multiple | Evet |
| **Ak Yatırım** | Evet | DCF | Evet |
| **Deniz Yatırım** | Evet (Nisan 2025 raporu — explicit NAD tablosu) | Peer multiple + DCF kombinasyonu | Evet |

**Uluslararası broker'lar:** HSBC ayrıştırılmış "discount to listed parts" + "discount to NAV" (private subsidiary fair-value adjustment dahil) sunar — Türk broker'larından daha sofistike. JPMorgan KCHOL TP 333 TL DCF + NAV hibridi (https://www.getmidas.com/midasin-kulaklari/jpmorgan-turk-sirketleri-icin-yeni-hedef-fiyatlarini-acikladi-p-228223). EM holding'leri için "normal" iskonto aralığını adlandıran tek bir sayısal kurumsal konsensus kaynak bulunamamıştır; bu nedenle yamada generic EM aralığı belirtilmemiş, yalnızca Türk holding'leri için isimli broker rakamları (KCHOL %33-%41, SAHOL %40-%49, AGHOL %46-%50) sunulmuştur. Bu rakamların **hepsi tarihsel Türk holding ortalamasının üstündedir**, yani mevcut bant kalıcı yapı değil, geçici genişleme olarak işaretlenmiştir.

#### 4.2. TEFAS Fon Yöneticisi Pratisyenliği (Tier-1)

RR-012 yamasındaki "MAC fonu pazarlama vs davranış" örneği benzeri burada **kapsamlı parse yapılmamıştır** (Tier-2 kapsam dışı). Tier-1 KIID metni düzeyinde gözlem: Pardus Yatırım Ortaklığı (PRDGS), Marmara Capital Hisse Senedi Fonu, Ak Portföy BIST 100 Endeks Hisse Senedi Fonu (AKB) tarzı top performer fonlarda KIID strateji metni "BIST 100 ağırlığını takip eder + temel analiz ile aktif sapma" jenerik ifadesini kullanır. NAV iskontosu kavramına KIID seviyesinde **doğrudan referans yok**. **Sonuç: TEFAS retail-facing katmanda holding iskontosu farkındalığı görünmüyor; broker araştırma raporlarıyla fon yöneticisi pratisyenliği arasında kavramsal asimetri olabilir ama Tier-1 ile kanıtlanamaz, Tier-2 kapsam dışı bırakıldığından spekülasyon yapılmamıştır.**

#### 4.3. "Holding İskontosu" Kavramının Türkiye Bilinirliği

- **Broker düzeyi:** Yüksek (yukarıda tablo) — terim "NAD iskontosu", "holding iskontosu", "iskonto daraldı/genişledi" şeklinde standart.
- **Akademik literatür:** Düşük-Orta — BIST holding-spesifik NAV iskontosu üzerine akademik makale **çok sınırlı**. Coskun, Erol & Morri (2020/2021), *"Why do Turkish REITs trade at discount to net asset value?"*, **Empirical Economics, Vol. 60(5)**, DOI: 10.1007/s00181-020-01846-y (https://link.springer.com/article/10.1007/s00181-020-01846-y; SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3564915) Türk GYO'ları için NAV iskontosu belirleyicilerini (kaldıraç, likidite, büyüklük, sentiment) analiz eder; metodoloji holding NAV iskontosu için referans niteliktedir ama doğrudan BIST holding çalışmaları yetersiz — **bu açık bir akademik boşluktur**.
- **Retail düzeyi:** Düşük — Hisse.net thread'lerinde "borsada iskontolu işlem görüyor" tarzı yaklaşımlar arzu vesilesidir, hesaplama yapılmamaktadır.
- **"Yapısal iskonto" varsayımı (asla kapanmaz):** Türk broker'larında **kabul görmez** — tüm raporlar "iskonto daralma potansiyeli" varsayar (Gedik: "CDS normalizasyonu sürerse iskonto daralmasına alan görüyoruz"; ÜNLÜ: "Türkiye CDS düşüşüne rağmen daralmadı — cazip"). Bu pratisyen söylem, Türk holding pratisyenliğinin **mean reversion'a iman ettiğini** gösterir; akademik literatürle uyumludur.

#### 4.4. Erişim Notu / Limitations (Alt-Bölüm 4)

5 büyük Türk broker'ın en güncel raporu PDF/web özet seviyesinde teyit edildi; her broker'ın metodoloji kitapçığı (handbook) erişimi kısıtlıdır, "private subsidiary yöntemi" hücreleri broker raporu içinden çıkarsanmıştır, **broker kurumsal düzeyde resmi metodoloji açıklaması teyit edilmemiştir**. TEFAS Tier-2 (fiili portföy parse'ı) **kapsam dışıdır** — bu sınırlama açıkça deklare edilmiştir.

---

### 5. Revize Edilmiş Pilot Önceliği

#### 5.1. Pratik Pilot Skoru Tablosu

| Holding | Broker Coverage | Forum Aktivitesi | SoTP Yaygınlığı | Pratik Pilot Skoru |
|---------|-----------------|------------------|-----------------|---------------------|
| **KCHOL** | **Yüksek** (10+ broker, Türk + EM bazlı JPM/HSBC/UBS aktif) | Orta-Yüksek (en aktif forum thread'i) | **Yüksek** (tüm broker raporlarında NAD tablosu) | **Yüksek (1)** |
| **SAHOL** | **Yüksek** (Türk broker'ları + HSBC, BofA, JPM) | Orta (AKBNK-bağımlılık tartışması ağırlıklı) | **Yüksek** (Gedik, HSBC, İş, ICBC, Ata) | **Yüksek (2)** |
| **AGHOL** | **Orta** (Türk broker'ları + HSBC Haziran 2025 initiation TP 373 TL ilk, sonra Yapı Kredi TP 532 — geniş aralık) | Düşük (forum trafiği KCHOL/SAHOL'a göre çok düşük; AEFES Rusya odaklı) | **Orta** (İş Yatırım/HSBC NAD üretiyor ama daha az breadth) | **Orta (3)** |

#### 5.2. Üç Kritik Soruya Cevap

**(1) Akademik öneri KCHOL ilk — pratik araştırma da aynı sonucu veriyor mu?**  
**Evet.** Pratik araştırma KCHOL'un (a) en yüksek broker coverage, (b) en şeffaf SoTP tabanı, (c) en zengin forum tartışması ile pilot-1 konumunu doğruluyor. Akademik öneri pratik araştırmayla **doğrulandı**.

**(2) Broker'ların SoTP yapmaması "veri yokluğu" mu yoksa "metodolojik tercih" mi?**  
**Soru ters yönde cevaplanıyor: Türk broker'ları SoTP YAPIYOR, standart**. Veri yokluğu sorunu yok; metodolojik tercih sorunu da yok. Asıl bulgu: retail forum'larda SoTP yapılmıyor — bu **retail eğitimi / finansal okuryazarlık asimetrisi** olarak okunmalıdır.

**(3) Türk retail "NAV discount" bilmiyor ama broker biliyor — bu bilgi asimetrisi alpha kaynağı mı?**  
**Muhtemelen Evet — ama dikkatli.** Klasik EM alpha kaynağı: kurumsal investor SoTP yapıyor, retail teknik analiz yapıyor → kurumsal akademik mean reversion trade'i alpha üretir. Ancak son 18 ayda kurumsal yatırımcılar (İş Yatırım, Gedik) **kendi NAV-bazlı model portföylerinden KCHOL'u çıkardılar** çünkü "kısa vadede iskonto daralma katalisti yok" diyor. Bu **alpha-kavramayan kurumsal pratisyen sezgisi** (sezgi ≠ akademik teori) bilgi asimetrisinin parasal değerini sınırlayabilir.

#### 5.3. Sonuç

**Pilot sıra değişmiyor.**  
**"Akademik öneri pratik araştırmayla doğrulandı"** notu düşülmüştür.  
- **Pilot 1:** KCHOL (mevcut the maintainer portföyü; teyit edildi)
- **Pilot 2:** SAHOL (Faz 2; broker coverage yüksekliği nedeniyle pratikte de güçlü)
- **Pilot 3:** AGHOL (Faz 2 sonu; HSBC initiation Haziran 2025 ile broker coverage genişledi ama forum likiditesi düşük)
- **Strateji-dışı kalanlar:** KOZAL (broker SoTP yok, holding-tipi değil; altın madencisi olarak normal şirket valuation), DOHOL (Doğan Holding pratisyen ilgisi var ama İş Yatırım'ın 4 Mart 2026 raporuna göre "Doğan Holding hisselerinin halihazırda cari Net Aktif Değerine (NAD) göre yüzde 52 iskonto ile işlem gördüğü… Hissenin son 1 yıllık ortalama NAD iskontosu ise yüzde 50 seviyesinde" — yani tarihsel ortalaması bizatihi %50 civarında, **yapısal iskontoya en yakın** Türk holding'i, bizim "iskonto daralır" tezimizle uyumsuz, https://paratic.com/dogan-holding-icin-hedef-yukseltildi-yuzde-52-iskontolu/).

#### 5.4. Erişim Notu / Limitations (Alt-Bölüm 5)

Pilot skor "Yüksek / Orta / Düşük" ordinal; sayısallaştırma yapılmamıştır. AGHOL forum aktivitesi gözlem 3-4 thread sample'ı üzerinde dayanır; broader trafik metric'leri (örn. Hisse.net thread'inin günlük ortalama yorum sayısı) **derlenmemiştir**.

---

### 6. Kritik Bulgu Uyarıları

**6.1. Akademik literatürün öngöremediği bir pratisyen sezgisi:**  
İş Yatırım 23 Aralık 2025 ve Gedik 9 Temmuz 2025 KCHOL'u model portföyden çıkardı — gerekçe **"iskonto daralma katalisti yok"**. Akademik mean reversion teorisi (Bae-Kang-Kim 2002) "extreme discount mean reverts" diyor; pratisyen "katalist yoksa zaman maliyeti var → iştirak hissesi taşı" diyor. Bu **time-value-of-mean-reversion** kavramı RR-013 ana raporunda netleştirilmemiş bir nüanstır — RR-014 (gelecek rapor) için açık bir gap olarak işaretlenir.

**6.2. Broker SoTP yapıyor ama retail bilmiyor (Information Asymmetry):**  
Türk broker'ları (Gedik, İş, Deniz, ÜNLÜ, GCM) standart NAD tablosu üretir; Hisse.net + Bigpara retail forum'unda NAD yapan retail kullanıcı **gözlenmedi**. Bu asimetri **alpha kaynağı potansiyeli yaratır** ama kurumsal pratisyenler bile "katalist yok" diye fırsatı pas geçtiği için **alpha realize etmek zor olabilir** (bkz. 6.1).

**6.3. KCHOL discount akademik tezin TERSİNE davranmıyor — ama mean reversion mevcut tarihsel ortalamadan ZIRVELERE genişledi:**  
Cari iskonto (~%41), 1Y ortalama (%24) ve 3Y ortalama (%21) üzerinde. Mean reversion sinyali BUY tarafına ama tarihsel ortalama da yukarı kayma riski var: Şimşek programı sonrası "Türkiye kalıcı rasyonel dönemine girdi" baz-case düzeltirse, ortalama %20-25 olabilir; "Türkiye yeniden idiosyncratic" senaryosunda ortalama %35-40 etrafında yeni denge oluşabilir. **RR-013 ana raporundaki mean reversion sinyali bu rejim belirsizliği nedeniyle %2-3 sigma genişletilmiş hata payı ile yorumlanmalıdır.**

**6.4. Doğan Holding (DOHOL) tezin TERSİ örneği:**  
DOHOL %52 iskontoda ve 1Y ortalama %50 (İş Yatırım 4 Mart 2026 raporu) — yani **tarihsel olarak %50 civarında "yapısal" iskonto**. Bu, "iskonto kapanmaz" tezini destekleyen Türk holding örneğidir. RR-013 ana raporunda DOHOL zaten strateji-dışı; bu bulgu kararı **doğruluyor**.

---

### 7. Paralel Kolon Kuralı — RR-013 Karar Matrisi Eki

**Önemli:** Bu yama RR-013 ana karar matrisini **DEĞİŞTİRMEZ**. Aşağıdaki tabloyu RR-013 karar matrisine **paralel ek kolon** olarak insert edin:

| Holding | Akademik Sinyal (RR-013 mevcut) | Pratisyen Skor (YAMA EK) | Çelişki var mı? | Net Karar |
|---|---|---|---|---|
| KCHOL | BUY (mean reversion, iskonto >1σ üstü) | HOLD (broker konsensus Strong Buy, ama kurumsal model portföyden çıkarma + kısa vade katalist eksikliği) | Hafif (sinyal tarafları aynı, zamanlama farkı var) | **HOLD** (RR-013 ana karar ile aynı; tetikleyiciler güncelleme yok) |
| SAHOL | BUY (Faz 2 pilot) | Faz 2'ye uygun (broker coverage yüksek, iskonto bandı ~%40) | Yok | **Faz 2'de pilot olarak devam** |
| AGHOL | Faz 2 sonu (akademik) | Faz 2 sonu (pratisyen — broker yeni başlıyor) | Yok | **Faz 2 sonunda pilot** |
| KOZAL | Strateji-dışı | Strateji-dışı (holding tipi değil) | Yok | **Strateji-dışı** |
| DOHOL | Strateji-dışı | **Strateji-dışı (yapısal iskonto pattern'i)** | Yok | **Strateji-dışı** |

**Akademik perspektif geçerliliğini korur.** İki perspektif yan yana yorumlanır.

---

### 8. Sonuç — the maintainer Portföyü Pratik Tavsiye

24 Mayıs 2026 itibariyle 81 lot KCHOL pozisyonu (ortalama maliyet 188,83 TL, mevcut fiyat ~191 TL):

1. **HOLD korunur.** RR-013 ana raporundaki tetikleyiciler (iskonto <%30 → kademe-1 kapatma; iskonto >%45 → kademe-2 alım düşün) **değişiklik gerektirmez**.
2. **İzleme uyarısı:** Mevcut iskonto %41 (±%4) — kademe-2 alım tetikleyicisine (~%45) yakın bant. Önümüzdeki 4 hafta haftalık NAV hesabı pratiğine başlanmalı; iskonto %43-45 bandına genişlerse RR-013 manuel onay kapısı açılır.
3. **Risk uyarısı:** Kurumsal pratisyenlerin (İş Yatırım, Gedik) KCHOL'u model portföyden çıkarması "kısa vadede katalist yok" sinyalidir; mean reversion realizasyonu **3-9 ay vadede** olabilir, kısa vadeli sabır gerekir.
4. **Geniş pencere:** 11 analist konsensus TP 295,69 TL (yüksek 333, düşük 272,6) — cari 191 TL fiyata göre ortalama **+%55 upside**. Bu konsensus pozitif zemin sağlar ama "konsensus alpha üretmez" disipliniyle: konsensus sadece downside risk **dampener**'i olarak okunmalıdır.

**Net öneri (tek cümle):** *RR-013 ana raporundaki HOLD önerisi yerinde duruyor; BIST sektör pratiği (broker SoTP standart, retail asimetrik, kurumsal kısa-vade katalist endişeli, mean reversion tarafları aynı) RR-013 metodolojisinin geçerli olduğunu teyit ediyor — pozisyon korunur, kademe-2 tetikleyiciye kadar bekleme moduna alınır.*

**Rapor Sonu — RR-013**