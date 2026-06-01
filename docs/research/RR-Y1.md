# BIST'te Kantitatif/Sistematik Trading: Üç Bağımsız Soruya Yanıt

> **Metodolojik not:** Bu rapor "doğruyu ara, cevabı doğrulama" disipliniyle yazılmıştır. Her iddia için kanıt gücü (akademik-hakemli / working-paper / anekdot / pazarlama), karşıt kanıt ve **Türkiye/BIST-spesifik ampirik kanıt mı yoksa genel Gelişmekte-Olan-Piyasa (EM) ekstrapolasyonu mu** olduğu açıkça ayrılmıştır.

## TL;DR
- **Soru 1 (Değer faktörü):** BIST'te değer primine dair kanıtlar KARIŞIK ve dönemsel olarak istikrarsızdır — erken 2000'lerde zayıf-pozitif, 2005-2017 örnekleminde NEGATİF/ters (Aras vd. 2018: aylık −%1.09, t=−2.90), 2009/2013 sonrası genelde anlamsız. Sizin rank-IC (zayıf) vs. portfolio-tilt (güçlü) çelişkiniz bir hata değil, literatürde iyi bilinen metodolojik bir olgudur: IC kesitin tamamına, tilt ise yalnızca uç desillere duyarlıdır.
- **Soru 2 (Açığa satış):** Haziran 2026 itibariyle bireysel açığa satış pratikte İMKANSIZDIR — SPK 1 Mart 2026'dan beri tüm BIST açığa satışını yasaklamış ve altı kez uzatmıştır (son: 12 Haziran 2026 seans sonu). Yasak dönemleri dışında bile yalnızca BIST 50 + yüksek portföy/teminat şartı geçerliydi; Türkiye'nin en büyük retail platformu Midas açığa satış sunmuyor; tarihsel ödünç ücret/shortable-liste verisi backtest için erişilemez.
- **Soru 3 (Yöntem envanteri):** Türk birey-trader topluluğunda öne çıkan yöntemlerin çoğu momentum/teknik analiz veya hikaye-bazlı (formalize edilebilir ama tipik olarak başarısız); "takas analizi" (yabancı/kurumsal akış takibi) ve halka arz underpricing potansiyel olarak BIST'e özgü, görece az test edilmiş açılardır.

---

## Key Findings

### SORU 1 — Değer faktörü BIST'te çalışıyor mu? (çelişki çözümü)

**BIST'e özgü ampirik kanıt (akademik, hakemli):**

| Çalışma | Dönem | Metodoloji | HML/değer büyüklüğü | Sonuç |
|---|---|---|---|---|
| **Eraslan (2013, Business and Economics Research Journal)** | 2003-2010, ISE-all, 274 hisse | FF3 portfolio-sort | Aylık ortalama HML ≈ +%0.50 | ZAYIF — yalnızca yüksek B/M portföylerinde anlamlı: *"value effect exists but it is not as persistent as the size effect"* |
| **Aras, Çam, Zavalsız, Keskin (2018, Istanbul Business Research)** | Oca 2005 – Haz 2017, 150 ay, 18 kesişim portföyü | FF5, value-weighted | Aylık HML = **−%1.09, t = −2.90** | NEGATİF/ters prim; ancak HML "gereksiz değil" (regresyon sabiti −%1.05, %5'te anlamlı) |
| **Azimli (2020, Borsa Istanbul Review)** | BIST, hakemli | CAPM/FF3/FF5/Q karşılaştırması | B/M ve beta primleri anlamlı; SMB anlamsız | FF3 en iyi; RMW/CMA gereksiz — **BIST-spesifik en yetkili kaynak** |
| **Molla Ahmetoğlu (BIST30)** | 2009Q2-2018Q4 | Panel, fixed-effects | HML İSTATİSTİKSEL ANLAMSIZ | Dört-faktör yeterli |
| **Doğan vd. (2022, Discrete Dynamics in Nature and Society)** | Eki 2013 – May 2021, 396 hafta | FF6 (momentum eklenmiş) | Momentum baskın faktör, değer değil | Altı-faktör en etkili |

**EM ekstrapolasyonu (BIST-spesifik DEĞİL):** Arkol & Azimli (2024, havuzlanmış 24 EM ülkesi dahil Türkiye, 1997-2023): HML aylık +%0.73, t=4.47 (güçlü anlamlı). **Uyarı:** Bu havuzlanmış EM verisidir, izole BIST değildir; temiz bir BIST figürü olarak okunmamalıdır.

**KRİTİK: rank-IC vs. tilt/portfolio-sort çelişkisinin metodolojik açıklaması.**
Sizin "aynı faktör, zıt sonuç" çelişkiniz literatürde iyi belgelenmiş, beklenen bir olgudur. Spearman rank-IC, kesitin TAMAMINDA faktör ↔ ileri-getiri korelasyonunu ölçer. Gerçekçi modellerde IC nadiren sıfırdan anlamlı farklıdır (Zhang, Guo & Cao 2020, Wells Fargo: *"a realistic stock selection model can hardly have an IC materially different from 0; a stellar model may often have an IC of 0.05 or 0.1, or otherwise 'barely' above zero"*). Buna karşın quintile/tercile tilt = E(getiri | üst %20) − E(getiri | alt %20); prim uçlarda yoğunlaştığında güçlü çıkar. Divergansın mekanizmaları:
1. **Doğrusalsızlık/monotonluk yokluğu:** IC doğrusal-monotonik ilişki varsayar; prim yalnızca en ucuz desilde toplanmışsa IC bunu kesitin gürültülü ortasıyla seyreltir, tilt ise tam da uçları yakalar.
2. **Uçlarda yoğunlaşma:** Quintile-spread tanımı gereği yalnızca uç desillere bakar; IC bütün dağılıma duyarlıdır.
3. **Outlier/robustluk:** Pearson-IC outlier'lara duyarlı, Spearman daha dayanıklı; tilt medyan-bazlı hesaplanırsa sonuç daha da ayrışır.
4. **Farklı null hipotezi:** Quintile-sort t-istatistiği (long-short getirinin sıfıra karşı testi) IC'nin sıfıra karşı testinden farklı bir güç profiline sahiptir; biri anlamlı çıkarken diğeri çıkmayabilir (NY Fed SR788 ve UZH "Efficient Sorting" bu ayrımı resmileştirir). → **Sizin %99.6 güvenle pozitif tilt + t<2 zayıf IC kombinasyonunuz, primin uç desilde yoğunlaştığı ve kesit ortasının gürültülü olduğu bir faktör için tipik imzadır.**

**Decay durumu:**
- **Gelişmiş piyasalar (ABD) — EM-spesifik DEĞİL:** McLean & Pontiff (2016, *Journal of Finance* 71(1):5-32, DOI 10.1111/jofi.12365) 80 çalışmadan derlenen, kesitsel getirileri öngördüğü gösterilen **97 değişkeni** inceler; verbatim: *"Portfolio returns are 26% lower out-of-sample and 58% lower post-publication. The out-of-sample decline is an upper bound estimate of data mining effects. We estimate a 32% (58%–26%) lower return from publication-informed trading."* ABD'de net post-publication decay vardır.
- **Uluslararası — EM-spesifik DEĞİL:** Jacobs & Müller (2020, *Journal of Financial Economics* 135(1):213-230, DOI 10.1016/j.jfineco.2019.06.004) **39 borsada 241 kesitsel anomaliyi / iki milyondan fazla anomali-ülke-ayını** inceler; verbatim: *"we find that the United States is the only country with a reliable post-publication decline in long/short returns."* Yani ABD dışındaki piyasalarda güvenilir post-publication decay YOKTUR — bu, BIST'te değer priminin zayıflamasının yayın kaynaklı olmadığına dair güçlü bir karşıt-kanıttır.
- **BIST-spesifik:** Alt-dönem kıyaslaması (Eraslan 2003-2010 zayıf-pozitif → Aras 2005-2017 negatif → 2013 sonrası anlamsız) BIST'te değer priminin zayıfladığına/tersine döndüğüne işaret eder. Ancak Jacobs-Müller bulgusu ışığında bu, publication-driven arbitraj decay'inden ziyade **makro rejim** kaynaklıdır: yüksek enflasyon, tekrarlayan kur krizleri, büyüme/momentum hisselerinin dominansı.

**Value trap riski BIST'te: YÜKSEK.** Türk birey-trader içeriği "ucuz hisse" taramalarıyla doludur (Kanal Finans "Piyasa Değeri En Düşük Hisseler", borsaveyatirim.com "en ucuz BIST30"). Ancak araştırma kaynakları (borsabilgisi.com, Gordon büyüme modeli çerçevesi) düşük F/K'nın yapısal nedenlere bağlı olduğunu vurgular: yüksek özsermaye risk primi, enflasyonun sermaye maliyetini (r) yükseltmesi, politik risk. Düşük F/K tek başına yeterli sinyal değildir — ucuzluk, kalıcı ucuzluğun (value trap) maskesi olabilir.

### SORU 2 — Bireysel yatırımcılar BIST'te açığa satış yapabilir mi? (2026 GÜNCEL)

**Mevcut durum (Haziran 2026): PRATİKTE İMKANSIZ.** (Kaynak: SPK kararları, Borsa İstanbul, broker dokümantasyonu — BIST-spesifik)

Kronoloji (tarihlerle):
- **6 Şubat 2023:** Kahramanmaraş depremleri sonrası SPK tüm BIST açığa satışını yasakladı.
- **2 Ocak 2025:** SPK yasağı kaldırdı — ancak yalnızca BIST 50 endeksindeki paylarla sınırlı (SPK 05/12/2024 kararı). Gün-içi açığa satış tuşuna basma zorunluluğu getirildi.
- **2025 boyunca** birkaç kez geçici yeniden yasaklandı (23 Mart, 30 Mayıs 2025 kararları).
- **1 Mart 2026:** ABD-İran savaşı sonrası SPK tüm BIST açığa satışını yeniden yasakladı (Kurul Karar Organı 11/417 sayılı karar; 2 Mart'tan itibaren).
- **Uzatmalar:** 8 Mart (13 Mart'a), 15 Mart, 28 Mart (10 Nisan'a), 25 Nisan (26 Mayıs'a), 30 Mayıs 2026 (12 Haziran'a). **Son durum: 12 Haziran 2026 seans sonuna kadar geçerli — altıncı uzatma.**

**Açığa Satış Listesi kapsamı:** Yasak olmayan dönemlerde bile yalnızca BIST 50 endeksindeki ~50 hisse (AEFES, AKBNK, ASELS, BIMAS, GARAN, THYAO, TUPRS, SISE vb.). Ayrıca VBTS (Volatilite Bazlı Tedbir Sistemi) tekil hisselere "Açığa Satış ve Kredili İşlem Yasağı" tedbirini 1 ay süreyle getirebiliyor (kademeli olarak brüt takas, emir paketi, tek-fiyat, internet emir yasağına yükseliyor). Liste sık değişiyor.

**Ödünç Pay Piyasası (ÖPP / Takasbank SLB):** Mevcut. Takasbank açık-teklif yöntemiyle merkezi karşı taraf (ödünç verene karşı alan, alana karşı veren). Yıldız ve Ana Pazar payları + BYF'ler ödünce konu olabilir (GİP/PÖİP/YİP hariç). Bireyler aracı kurumun müşteri temsilcisi aracılığıyla erişebilir; ÖPP Çerçeve Sözleşmesi zorunlu. Teminat: kurum-içi/ÖPP'de ödünç tutarının %120'si değerlenmiş teminat (QNB Invest), asgari teminat oranı %110; Borsa payı on binde bir, ödünç alan ve verenden ayrı tahsil.

**Retail broker durumu:**
- **Midas:** *"Midas üzerinden henüz kredili işlemler, açığa satış veya ödünç alma/verme işlemleri yapılamamaktadır."* Midas (Midas Menkul Değerler A.Ş.) **3,5 milyondan fazla kullanıcıya** sahiptir; 19 Ağustos 2025'te QED Investors liderliğinde 80 milyon dolarlık Seri B turu alarak toplam yatırımını 140 milyon doları aşmış ve 2025'te BIST komisyonlarını kalıcı olarak sıfırlamıştır — yani Türkiye'nin en büyük retail platformu açığa satış SUNMUYOR.
- **Geleneksel kurumlar — yüksek bariyer:** Ziraat Yatırım açığa satış için **minimum 250.000 TL portföy** şartı koyuyor ve gün-sonu pozisyon kapatma zorunlu. Tacirler Yatırım: kredi komitesi onayı, 5.000 TL ve katları limit. Ak Yatırım, TEB Yatırım, QNB Invest hizmet veriyor ama hepsi çerçeve sözleşme + kredi onayı + teminat istiyor. Vakıfbank banka kanalından verilemiyor, Vakıf Yatırım gerekiyor.

**Teminat/uptick benzeri kurallar:** Başlangıç özkaynak oranı %50 (P), sürdürme oranı %35 (SPK Seri V No:65, madde 17); kriz tedbirlerinde %20'ye esnetildi. Açığa satış emri baştan "açığa satış" olarak işaretlenmek zorunda.

**Tarihsel veri erişilebilirliği (backtest için KRİTİK):**
- Günlük gerçekleşen açığa satış işlem verisi (adet, hacim, AOF) BIST tarafından gün sonu (18:30-23:59) yayınlanıyor; İş Yatırım, Fintables, yatirimkredi.com gibi kaynaklar derliyor.
- **ANCAK:** Tarihsel shortable-stock listesinin sistematik arşivi ve tarihsel ödünç (borrow) ücretleri kamuya açık değil. yatirimkredi.com editörü teyit ediyor: açığa satışların geri dönüş istatistikleri sorulunca *"Maalesef Borsa İstanbul böyle bir veriyi paylaşmıyor."* BIST DataStore'dan ücretli tarihsel veri alınabilir, ancak ödünç ücret zaman serisi standart üründe yok.
- **Sonuç:** Açığa-satış (short-leg) stratejisi backtest'i ciddi veri kısıtı altındadır; ödünç maliyeti ve borrow-availability tarihsel olarak güvenilir biçimde rekonstrükte edilemez.

### SORU 3 — Modern BIST birey-trader yöntemleri envanteri (DEĞERLENDİRME değil, ENVANTER)

| Yöntem | Formalize edilebilir mi? | Zaten-test-edilmiş versiyon? | Yeni açı? | Kanıt tipi |
|---|---|---|---|---|
| Teknik analiz / trend takip (EMA21/200, ADX, RSI) | Evet | Evet — momentum/TA; BIST backtest'leri (Comparison of Technical and Fundamental Analysis, 2021) genelde endeksi yenemiyor | Hayır | Anekdot + sistematik (zayıf) |
| Momentum (yükselen trend hisse alımı) | Evet | Evet — global momentum literatürü; Doğan (2022) BIST'te momentum'u baskın faktör buluyor | Kısmen | Sistematik (karışık) |
| Hikaye/narrative trading ("10x potansiyel", clickbait) | Hayır (belirsiz) | Evet — sentiment trading; genelde başarısız | Hayır | Anekdot (Yatırım 101 eleştirileri) |
| Temettü yatırımı (yüksek temettü verimi) | Evet | Evet — dividend-yield faktörü | Hayır | Anekdot + sistematik |
| Değer/ucuzluk taraması (düşük F/K, PD/DD) | Evet | Evet — value faktörü; BIST'te zayıf/ters (yukarı bkz.) | Hayır | Sistematik (zayıf) |
| **Takas analizi (yabancı/kurumsal net akış takibi)** | Kısmen (günlük takas dağılım raporu mevcut) | Az test edilmiş — order-flow / institutional-flow benzeri | **EVET — potansiyel BIST'e özgü açı** | Anekdot (sistematik test eksik) |
| Halka arz (IPO) underpricing / ilk gün getiri | Evet | Evet — IPO underpricing iyi belgeli; BIST'te güçlü (2023'te 54 IPO'dan 52'si ilk gün anormal pozitif getiri) | Kısmen | Sistematik (güçlü ama tahsis kısıtlı) |
| Bedelli/bedelsiz sermaye artırımı, rüçhan stratejileri | Kısmen | Az test edilmiş | **EVET — BIST'e özgü kurumsal-aksiyon açısı** | Anekdot |
| Buhur25 tarzı temettü+bedelsiz kombine izleme listeleri | Evet | Kısmen | Kısmen | Anekdot (influencer) |

**Survivorship bias uyarısı (kritik):** Yatırım 101 (300K+ YouTube abonesi, İTÜ İşletme Müh. mezunu kurucu, "geçmiş 5 yılda sistematik seçilen hisseler BIST 100/dolar/altına kıyasla 20-30 kat getiri sağladı" iddiası), Kanal Finans gibi kanalların performans anlatıları geçmiş-seçilmiş, hayatta-kalan örneklerdir. Ekşi Sözlük kullanıcı eleştirileri bu kanalların yükselenleri öne çıkarıp düşenleri gizlediğini, "en iyiyi en kötüyle karşılaştırma" yanlılığı yaptığını ve clickbait başlık kullandığını belgeliyor (ör. bir hissenin "8x potansiyel" iddiasıyla tanıtılıp sonradan değer kaybetmesi). **İnfluencer iddiaları ≠ sistematik kanıt.**

---

## Details

**Soru 1 detayları:** BIST değer-primi literatürünün ortak bulgusu, FF3'ün BIST'te FF5'ten daha iyi performans gösterdiği ve B/M priminin yalnızca belirli alt-dönemlerde/yüksek-B/M portföylerinde anlamlı olduğudur. Aras vd. (2018)'in negatif HML'si (−%1.09, t=−2.90) örneklemin 2008 sonrası büyüme-dominant yıllarca şekillenmesinden kaynaklanır. Doğan vd. (2022) ise momentum eklendiğinde değerin geri plana düştüğünü gösterir. rank-IC vs tilt ayrımı için temel kaynaklar: Zhang-Guo-Cao (2020, IC'nin sıfıra yakınlığı), NY Fed Staff Report 788 (karakteristik-sıralı portföylerde monotonluk vs nokta-tahmini ayrımı), UZH "Efficient Sorting" (sıralama testinin gücü).

**Soru 2 detayları:** Tüm bulgular SPK Kurul Karar Organı kararları, Borsa İstanbul pazar düzenlemeleri, Takasbank ÖPP Yönergesi ve broker resmi sayfalarına (Midas destek, Ziraat/Ak/Tacirler/QNB/TEB) dayanmaktadır. SPK kararları Resmi Gazete ve SPK bültenlerinde (2026/11 vb.) yayımlanmaktadır.

**Soru 3 detayları:** Takas analizi günlük "takas dağılım raporları" üzerinden formalize edilebilir (yerli birey/yerli kurumsal/yabancı kurumsal bazında net alım); en fazla net alım yapan kurumların takibi BIST'e özgü, görece az akademik olarak test edilmiş bir sinyaldir ve ilk backtest önceliği olmalıdır.

## Recommendations

**Soru 1 için:**
1. Çelişkiyi çözmek için hem rank-IC hem quintile-spread'i AYNI örneklemde, AYNI rebalancing frekansıyla raporlayın; ek olarak decile-bazında monotonluk testi (örn. MR testi) yapın. Prim yalnızca en uç desilde toplanıyorsa, güçlü tilt + zayıf IC kombinasyonu beklenen sonuçtur — çelişki değildir.
2. BIST'te değer faktörünü TEK BAŞINA kullanmayın; alt-dönem istikrarsızlığı (2005-2017 negatif) ve value trap riski yüksektir. Momentum + value kombinasyonu Doğan (2022) ışığında daha savunulabilir.
3. **Eşik:** value-only tilt'in t-istatistiği yalnızca tek bir alt-dönemde >2 çıkıp diğer alt-dönemlerde işaret değiştiriyorsa, bunu kararlı bir prim değil **rejime-bağlı bir etki** olarak işaretleyin ve canlı sermaye ayırmadan önce en az iki bağımsız alt-dönemde OOS doğrulaması arayın.

**Soru 2 için:**
1. 2026 koşullarında açığa-satış-bağımlı (long-short hisse) strateji geliştirmeyin; yasak aktif ve sürekli uzatılıyor. Yasak kalksa bile evren BIST 50 ile sınırlı ve retail erişimi yüksek-portföy bariyerli kalacaktır.
2. Short-exposure için alternatif: VİOP endeks vadeli/opsiyon kontratları (BIST 30 futures) — bunlar açığa satış yasağından etkilenmez.
3. **Backtest disiplini:** Ödünç ücreti tarihsel verisi olmadığından, herhangi bir short-leg sonucunu konservatif sabit borrow-fee varsayımıyla (örn. yıllık %10-20) stress-test edin; aksi halde net getiri ciddi şekilde abartılır.

**Soru 3 için:**
1. **İlk öncelik:** "Takas analizi" (yabancı/kurumsal net akış) — günlük takas verisi mevcut olduğundan formalize edilip backtest edilebilir; görece az test edilmiş, BIST'e özgü bir açıdır.
2. IPO underpricing güçlü görünüyor ama tahsis (allocation) kısıtları nedeniyle gerçek-dünya uygulanabilirliği ayrıca test edilmeli.
3. Hikaye/narrative ve saf TA sinyallerini düşük öncelikte tutun — hem global olarak hem BIST'te tipik olarak başarısızdır.

## Caveats

**Kapsam kontrolü (final):**
- **Soru 1:** Çoğunlukla BIST-SPESİFİK yanıtlandı (Eraslan, Aras vd., Azimli, Doğan, Molla Ahmetoğlu). Decay için ABD (McLean-Pontiff) ve uluslararası (Jacobs-Müller) bulgular EM ekstrapolasyonu olarak AÇIKÇA ayrıldı — ve Jacobs-Müller'in "decay yalnızca ABD'ye özgü" bulgusu BIST'teki zayıflamanın yayın-kaynaklı olmadığına dair karşıt-kanıt olarak sunuldu. rank-IC vs tilt açıklaması genel kantitatif literatürdendir (Wells Fargo, NY Fed, UZH).
- **Soru 2:** Tamamen BIST/SPK/Takasbank-spesifik; resmi kaynaklar, tarihler ve broker dokümantasyonuyla.
- **Soru 3:** BIST birey-trader topluluğu içeriğine dayalı (Yatırım 101, Kanal Finans, Twitter/X, Ekşi Sözlük), BIST-spesifik.
- **Atlanan açılar/sınırlar:** Azimli (2020, Borsa Istanbul Review) tam metni bot-engeli nedeniyle HML mean%/t-stat olarak çıkarılamadı (nitel sonuçlar — B/M anlamlı, RMW/CMA gereksiz, FF3 en iyi — başka kaynaklarca teyitli). VİOP türev-tabanlı short alternatifleri derinlemesine modellenmedi. Tarihsel borrow-fee verisinin ücretli BIST DataStore'da hangi granülaritede bulunduğu doğrudan satıcı teklifi düzeyinde teyit edilmedi.

**Bias uyarıları:**
- **Publication bias:** Anlamlı sonuçlar yayınlanma eğilimindedir; BIST değer-primi literatüründe pozitif bulgular aşırı temsil edilebilir. Bu, neden hakemli çalışmalar arasında bile sonuçların (pozitif/negatif/anlamsız) bu kadar dağıldığını kısmen açıklar.
- **Survivorship bias:** İnfluencer "başarı" anlatıları ve hayatta-kalan model-portföyler sistematik kanıt değildir; başarısız çağrılar sistematik olarak gizlenir.
- **Hindsight bias:** "Ucuz hisse 10x yaptı" tarzı geriye-dönük seçilmiş örnekler yanıltıcıdır; yalnızca ileriye-dönük, gerçek zamanlı OOS testi geçerlidir.
- **Evidence-strength etiketleri:** Yukarıda her ana iddia için akademik-hakemli / working-paper / anekdot / pazarlama ayrımı yapılmıştır; en güçlü dayanaklar Soru 2'dedir (resmi düzenleyici kaynaklar), en zayıf/karışık olanı Soru 1'in değer-primi büyüklüğüdür (hakemli ama çelişkili).