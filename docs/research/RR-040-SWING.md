# BIST Algoritmik Swing-Trading Sistemi: Üç Hipotezin Temellerine Yönelik Derin Araştırma

## TL;DR (jargonsuz, 7 madde)
1. **Üç hipotezden en sağlam temele sahip olanı PEAD'dir (kazanç sürprizi sonrası fiyat sürüklenmesi).** Türkiye'ye özgü doğrudan kanıt vardır: Ahlatcıoğlu & Okay (2021, *Borsa İstanbul Review* 21(1):92-103), geçmiş kazanca dayalı sürpriz ölçütüyle "statistically and economically significant difference of 2.9% in average cumulative abnormal return between high earnings surprise firms and low earnings surprise firms in the 60 days following the announcement" bulmuştur. Kritik avantaj: sürpriz, analist beklentisi olmadan SADECE geçmiş bilançodan (mevsimsel rastgele yürüyüş) hesaplanabiliyor — yani BIST'in veri kıtlığına dayanıklı.
2. **PEAD gelişmiş piyasalarda büyük ölçüde "öldü" (Martineau 2022: büyük hisselerde 2006'dan beri yok), ama gelişmekte olan piyasalarda hâlâ yaşıyor.** Bu, edge'in büyük/kaliteli devlerde değil, KÜÇÜK ve takip edilmeyen hisselerde yoğunlaştığı anlamına gelir — bu, kullanıcının "devlerde teknikal" sezgisiyle GERİLİMDE.
3. **Mekanik olaylar (temettü/bedelsiz/endeks) BIST'te ölçülebilir ama edge'i zayıf ve büyük ölçüde olay-öncesi (anticipation).** Bedelsiz sermaye artırımında BIST'te güçlü anormal getiri var (irrasyonel/balon davranışı); endeks dahil/çıkarmada Bildik & Gülay etkisi var ama küçük ve istatistiksel olarak zayıf; nakit temettüde işaret negatif (vergi-müşteri etkisi).
4. **Olayların sistematikleştirilebilirliği nettir.** ALGORITMA katmanı (şimdi): kazanç tarihi + SUE, bedelsiz, endeks değişimi, temettü — hepsi KAP'tan tarihli/objektif çekilebilir. LLM katmanı (sonra, Faz B): şirket haberleri, anlaşmalar, yönetim değişiklikleri, dava/regülasyon — bunlar asimetrik ve yorum gerektirir; Türkçe NLP/sentiment hâlâ olgunlaşmamış ve kanıtlanmış tek-hisse alfa üretmiyor.
5. **Fundamental-filtre × teknikal hipotezi PARÇALIDIR.** Metghalchi vd. (2021, IMEFM 14(4):713-731) teknikal kuralların Türk SMALL-CAP endeksinde işe yaradığını ama LARGE-CAP'te işe yaramadığını ("results were mixed for the large-cap index") bulmuştur — bu, kullanıcının "devlerde teknikal güvenirim" pratiğinin AKSİNE bir bulgu. Dar/kaliteli evren teknikalin gücünü artırmaz.
6. **Kompozit tuzağına dönmeden inşa MÜMKÜN ve gereklidir.** Olay-driven mimari doğal olarak GATE (fundamental geçer/geçmez) + TRIGGER (olay var/yok, tarihli) + opsiyonel FILTER (olay-penceresi içinde teknikal teyit) diliyle ifade edilir. Endüstri pratiği olayları koşullu/binary tetikleyici olarak temsil eder, ağırlıklı skor olarak DEĞİL.
7. **Test sırası önerisi: (1) PEAD — geçmiş-kazanç SUE ölçütüyle, küçük/orta hisselerde; (2) bedelsiz-sermaye-artırımı olay-penceresi; (3) hibrit (fundamental gate + PEAD trigger).** Fundamental-filtre×teknikal en zayıf temele sahip; ayrı bir alfa olarak değil, sadece bir GATE (kalite eşiği) olarak kullanılmalı.

---

## TOPIC 1 — PEAD / KAZANÇ-SÜRPRİZİ SÜRÜKLENMESİ

### Çekirdek olgu ve gelişmiş-piyasa durumu
PEAD, Ball & Brown (1968) tarafından keşfedilen ve Bernard & Thomas (1989, *Journal of Accounting Research* 27:1-36) tarafından isimlendirilen, fiyatın kazanç sürprizi yönünde açıklamadan SONRA haftalar-aylar boyunca sürüklenmesidir. Bernard-Thomas ve Foster-Olsen-Shevlin (1984), en yüksek SUE desilini alıp en düşüğü satan stratejinin 60 işlem gününde yıllıklandırılmış ~%25 anormal getiri ürettiğini raporladı (işlem maliyeti öncesi).

**KRİTİK — anomali zayıflaması:** Martineau (2022, *Critical Finance Review* 11(3-4):613-646, "Rest in Peace Post-Earnings Announcement Drift") gelişmiş piyasalarda PEAD'in BÜYÜK ölçüde kaybolduğunu gösterdi: büyük hisselerde 2006'dan beri yok ("PEAD have been non-existent since 2006"), mikro-cap'lerde son yıllarda kayboldu. Sebep yapısaldır — ondalık fiyatlama (decimalization), Reg NMS (2005) ve HFT, fiyatın açıklama GÜNÜNDE tam ayarlanmasını sağladı. Yüksek-düşük SUE getiri farkı 1980-90'larda ~%5'ten 2010'larda ~%3 veya altına düştü. (Not: 2025'te kabul edilen birkaç çalışma Martineau'ya itiraz edip "PEAD hâlâ yaşıyor" iddiasını sürdürüyor — UCLA Anderson Review'a göre tartışma kapanmış değil.)

### Gelişmekte olan piyasa ve BIST kanıtı (ÖNCELİK)
EM'de PEAD daha dirençli. Hung, Li & Wang (2015, *Review of Financial Studies* 28(4):1242-1283) küresel olarak PEAD'in finansal raporlama kalitesi şokundan sonra azaldığını, ama bu azalmanın "limits to arbitrage" düşük olan firmalarda daha belirgin olduğunu — yani arbitraj sınırları yüksek (tipik EM koşulu) yerlerde driftin SÜRDÜĞÜNÜ — gösterdi. Çin (Kong 2008; Truong 2011), Japonya, Vietnam ve Latin Amerika'da PEAD belgelendi. Mekanizma: sınırlı yatırımcı dikkati + arbitraj sınırları + yüksek işlem maliyetleri — bunların hepsi EM'de daha güçlü, dolayısıyla drift daha kalıcı.

**TÜRKİYE'YE ÖZGÜ DOĞRUDAN KANIT (en önemli bulgu):** Ahlatcıoğlu, A. & Okay, N. (2021), "Post-earnings announcement drift: Evidence from Turkey," *Borsa İstanbul Review* 21(1):92-103 (DOI 10.1016/j.bir.2020.09.001).
- **Yöntem:** Üç çeyrekli sürpriz ölçütü; hisseler her çeyrek üç quantile'e ayrılıyor; açıklama sonrası [t+2, t+61] (60 işlem günü) penceresinde kümülatif anormal getiri (CAR) ölçülüyor.
- **Bulgular (abstract'tan verbatim):**
  - Geçmiş-kazanca dayalı SUE (mevsimsel rastgele yürüyüş, "SUETF") ile: "statistically and economically significant difference of **2.9%** in average cumulative abnormal return between high earnings surprise firms and low earnings surprise firms in the **60 days following the announcement**".
  - Analist-beklentisi-bazlı sürpriz: **%2,9** hedge getiri (anlamlı).
  - Kazanç-açıklama-getirisi (EAR) bazlı sürpriz: **%2,2** hedge getiri (anlamlı).
  - **Firma büyüklüğü drift büyüklüğüne NEGATİF etki ediyor** — yani drift KÜÇÜK firmalarda daha güçlü.
  - Fama-French beş-faktör modeli (2015), açıklama sonrası getiri farkını AÇIKLAYAMIYOR (anlamlı alfa kalıyor; FF3 ve FF5 Türkiye'de aylık portföy getirilerini açıklamıyor).
  - Drift, 1. günden sonra genişlemeye devam ediyor (yüksek-sürpriz yukarı, düşük-sürpriz aşağı).
- **Örneklem:** Analist-takip alt-örnekleminde medyan hisse 9 analist tarafından takip ediliyor, ~1,3 milyar USD piyasa değeri; tam örneklemde medyan hisse HİÇ analist tarafından takip edilmiyor, ~0,4 milyar USD piyasa değeri. (Dönem/örneklem-N bu paper'ın PDF'inden doğrudan teyit edilemedi; aynı yazarların companion çalışması "over the 2007–2017... over 12,000 observations coming from 396 companies listed at Borsa Istanbul" diyor — bu paper için en yakın çıkarım ~2007-2017/2018, ~396 firma.)

### Sürpriz tanımı feasibility (KRİTİK)
BIST'te analist beklentisi verisi seyrek — ama Ahlatcıoğlu & Okay tam da bunu çözüyor: **geçmiş-kazanca dayalı (mevsimsel rastgele yürüyüş) SUE, analist-bazlı ölçütle AYNI %2,9'u veriyor.** Yani analist verisi GEREKMİYOR. Veri-realist sürpriz tanımı: SUE = (cari çeyrek kazancı − geçen yılın aynı çeyreği) / son 8 çeyreğin standart sapması (Chordia vd. 2009 yöntemi). Bu tamamen KAP bilançolarından hesaplanabilir.

**EM-geçerlilik kararı: GÜÇLÜ.** Doğrudan BIST kanıtı var; mekanizma EM mantığıyla tutarlı; veri-realist. **Tek kritik uyarı:** drift küçük/takip edilmeyen hisselerde yoğunlaşıyor — bu, kullanıcının "devlerde teknikal" sezgisine ZIT, ve küçük sermaye (~5500 USD) için likidite/işlem maliyeti riski demek. %2,9 işlem-maliyeti öncesi brüt rakamdır.

---

## TOPIC 2 — DİĞER MEKANİK OLAYLAR (temettü/bedelsiz/endeks)

### Endeks dahil/çıkarma etkisi
**BIST kanıtı:** Bildik & Gülay (2008, *International Review of Financial Analysis* 17:178-197). SSRN abstract verbatim: ISE-100 ve ISE-30 için 1995-2000 döneminde "204 additions and 180 deletions in 24 quarterly periodical index revision intervals are analyzed by using event-study and standardized cross-sectional test methodology shown by Boehmer, Musumeci and Poulsen (1991)." Dahil edilen hisseler pozitif, çıkarılanlar negatif anormal getiri üretiyor (özellikle ISE-30'da), efektif değişim gününe kadar; hacim de etkileniyor. **ANCAK:** ilgili literatür notu CAR'ların "relatively small and statistically weak" olduğunu, fiyatların hem dahil hem çıkarılan hisseler için olay-öncesi yükseldiğini, değişim gününden SONRA düştüğünü vurguluyor — yani etki büyük ölçüde anticipation/geçici fiyat baskısı (price pressure hypothesis).

**Küresel bağlam:** Greenwood & Sammon ("The Disappearing Index Effect," HBS WP 23-025) S&P 500 endeks etkisinin zamanla zayıfladığını gösterdi — front-running ve endeks fonlarının rebalancing'i önceden fiyatlaması nedeniyle. EM'de bu daha az olgunlaşmış ama trend aynı.

### Temettü ve bedelsiz (bonus/sermaye artırımı)
**Bedelsiz sermaye artırımı (GÜÇLÜ BIST etkisi):** "Cracking the fault line in stock markets: the case of bonus issue announcements" (*Journal of Capital Markets Studies* 5(1):69, 2021) — KAP verisiyle (2010 sonrası, çünkü KAP daha öncesini sağlamıyor) event-study. İç kaynaklardan yapılan bedelsizler, geçen yılın net karından dağıtılanlardan daha yüksek açıklama getirisi üretiyor. Yatırımcılar büyük-boyutlu ihraçları "memnuniyetle karşılıyor"; yazarlar bunu **sürü davranışı / fiyat balonu** ve BIST'te güçlü-form etkinliğin yokluğu olarak yorumluyor. Bu, mekanik + tarihli + objektif bir sinyal.
**Nakit temettü (NEGATİF/ters işaret):** "Market Reaction to Dividend Announcement: Evidence from Turkish Stock Market" — verbatim: "data covering the period from 2003 to 2015 including 902 events of 118 companies... a significant, negative relationship between dividend per share and abnormal returns following the announcement." Vergi-müşteri etkisi: temettü açıklanınca yatırımcılar gelecekteki vergiden kaçınmak için satıyor. Türkiye bağlamı: 2009'da zorunlu minimum temettü kaldırıldı; banka-bazlı sistem; temettü-sermaye kazancı vergi farkı.

### Algoritmik uygunluk
Bu olaylar TARİHLİ + OBJEKTİF → KAP'tan çekilebilir. En uygun "mekanik sinyal" sıralaması: (1) **bedelsiz sermaye artırımı** (en güçlü ve yönü pozitif BIST etkisi), (2) endeks değişimi (zayıf, anticipation-ağırlıklı), (3) nakit temettü (işaret ters/zayıf, dikkatli). 

**EM-geçerlilik kararı: PARÇALI.** Bedelsiz etkisi BIST'e özgü ve güçlü ama büyük ölçüde davranışsal balon (sürdürülebilirliği şüpheli); endeks etkisi zayıf ve kayboluyor; nakit temettü swing-long için ters işaret.

---

## TOPIC 3 — FUNDAMENTAL-FİLTRE × TEKNİKAL ETKİLEŞİMİ

### Metghalchi vd. (2021) — kritik Türkiye bulgusu
Metghalchi, Durmaz, Cloninger & Farahbod (2021), "Trading rules and excess returns: evidence from Turkey," *International Journal of Islamic and Middle Eastern Finance and Management* 14(4):713-731 (DOI 10.1108/IMEFM-01-2020-0043). FTSE Türkiye all-cap ve small-cap endekslerinde 23 Eylül 2003 – 9 Ağustos 2019 dönemi; beş teknikal kural (SMA, RSI, MACD, momentum, ROC), tekli ve ikili kombinasyon.
- **SMALL-CAP endeksinde (verbatim):** "For the small-cap index, some TTRs – including the famous Golden Cross, when the 50-day moving average rises above 200-day moving average – produced net annual excess returns (NAERs) over the B&H strategy, for the entire period and each sub-period, after accounting for risk and transaction costs."
- **LARGE-CAP (all-cap) endeksinde:** "Results were mixed for the large-cap index." Net edge yok.
- Bu Cakici & Topyan (2013) bulgularını destekliyor.

**KRİTİK ÇIKARIM — kullanıcının sezgisiyle ÇELİŞKİ:** Literatür, teknikal edge'in KÜÇÜK hisselerde olduğunu, büyük/likit devlerde KAYBOLDUĞUNU gösteriyor. Aynı paralel kanıt: Metghalchi vd.'nin Güney Afrika çalışması (2021, *Cogent Economics & Finance* 9:1869374) — small-cap'te kurallar B&H'yi yener (örn. ROC30+SMA200 kombinasyonunda başabaş maliyet %0,78-2,24), All Share'de yenemez (başabaş maliyet ~%0 veya negatif). Bu, kullanıcının "TTKOM/KCHOL/BIMAS gibi devlerde teknikale güvenirim" pratiğinin literatürle DESTEKLENMEDİĞİ, hatta ZIT olduğu anlamına gelir.

### Kalite + momentum etkileşimi (genel literatür, gelişmiş-piyasa — TRANSFER ŞÜPHELİ)
Quality+momentum ve fundamental-momentum kombinasyonlarının gelişmiş piyasalarda risk-ayarlı getiriyi iyileştirdiğine dair geniş literatür var (örn. QVM stratejileri, Alpha Architect'in dual momentum çalışması: fundamental momentum ve fiyat momentumu "complements, not substitutes"). Ancak bunlar PORTFÖY-kesitsel sıralama stratejileri — kullanıcının zaten elediği "cross-sectional factor ranking" paradigmasına ait. Tek-hisse swing-trading'e doğrudan transfer edilemez.

### İstatistiksel güç sorusu (KRİTİK)
Kullanıcının sorusu: fundamental filtre evreni daralttığında teknikal sinyalin gücü artar mı, yoksa örneklem küçülüp gürültü mü artar? Metghalchi kanıtı şunu söylüyor: edge "kalite" ile DEĞİL, "küçüklük/likidite-azlığı/takip-edilmemişlik" ile ilişkili. Dolayısıyla kaliteli-büyük evrene daralmak teknikal gücü ARTIRMAZ; tam tersine edge'in olduğu bölgeden UZAKLAŞTIRIR. Kullanıcının pratiği aslında bir "düşük-volatilite + kalite" alt-evren seçimidir; bunun edge'i literatürde teknikal-zamanlama olarak DEĞİL, sadece düşük-vol/kalite faktör primi olarak görünür — ve o da kesitsel, zaten elenmiş.

**EM-geçerlilik kararı: ZAYIF/PARÇALI.** Türkiye'de teknikal edge small-cap'te var ama kullanıcının hedef evreninde (devler) yok. Fundamental filtre bir ALFA kaynağı değil, sadece bir KALİTE GATE'i (riski azaltan eşik) olarak meşru.

---

## TOPIC 4 — OLAYLARIN SİSTEMATİKLEŞTİRİLEBİLİRLİĞİ (en derin soru)

### Algoritma ile sistematikleştirilebilir olaylar (objektif, tarihli, yönü-bilinen)
- **Kazanç açıklama tarihi + SUE:** KAP'ta tarihli; SUE geçmiş bilançodan hesaplanır; yön sürpriz işaretiyle bilinir. → TAM ALGORITMA.
- **Bedelsiz sermaye artırımı:** KAP duyurusu tarihli; oran objektif; BIST'te yön pozitif. → TAM ALGORITMA.
- **Endeks dahil/çıkarma:** BIST periyodik revizyon takvimi + duyuru tarihli; yön bilinir (dahil=+, çıkar=−). → TAM ALGORITMA (ama edge zayıf).
- **Nakit temettü / temettü tarihi:** KAP'ta tarihli; ex-date objektif. → ALGORITMA (ama BIST'te işaret ters).

### İnsan/LLM yorumu gerektiren olaylar (asimetrik, bağlam-bağımlı)
- **Şirket haberleri, anlaşma/sözleşme duyuruları:** boyut, kalıcılık, fiyatlanmışlık yoruma açık ("buy the rumor, sell the news").
- **Yönetim değişiklikleri:** işaret bağlama bağlı (iyi mi kötü mü?).
- **Sektör/regülasyon gelişmeleri, dava:** asimetrik, çok-değişkenli.
- Bunlar binary tetikleyiciye indirgenemez; metin anlama gerektirir.

### NLP/sentiment'in olay-yorumunu otomatik sinyale çevirmedeki başarısı (EM/Türkçe durum)
Gelişmiş piyasalarda haber-bazlı event-driven NLP (örn. "Trade the Event," arXiv 2105.12825; "PEAD.txt," *Journal of Financial and Quantitative Analysis*) ilerleme kaydetti ama düşük sinyal-gürültü oranı ve açıklanabilirlik sorunları sürüyor. **Türkçe durum OLGUNLAŞMAMIŞ:** mevcut çalışmalar çoğunlukla BIST-100 endeks/banka-hissesi YÖNÜ tahmini düzeyinde, tek-hisse olay-yorumu değil. Örneğin Kilimci & Duvar (2020, *IEEE Access* 8:188186-188198, DOI 10.1109/ACCESS.2020.3029860) BIST-100 banka hisselerinin yönünü LSTM/RNN/CNN + Word2Vec/GloVe/FastText kelime gömmeleriyle (kaynak: KAP, Bigpara, Twitter, Mynet Finans) tahmin ediyor — bu bir endeks/yön sınıflandırma çalışması, backtest-edilmiş tek-hisse olay-alfa değil. Diğer çalışmalar (Cam vd. 2024 *Heliyon*; çeşitli Twitter-sentiment çalışmaları, BERTurk %82 düzeyinde sentiment sınıflandırma doğruluğu raporluyor) da in-sample sınıflandırma doğruluğu raporluyor, işlem-maliyeti-sonrası alfa değil. **Net: tek-hisse olay-yorumunu güvenilir, backtest-edilebilir alfa sinyaline çeviren olgun bir Türkçe sistem YOK.**

### Net sonuç: katman ayrımı
- **MEKANİK katman (şimdi, algoritma):** kazanç-tarihi+SUE, bedelsiz, endeks-değişimi, temettü-tarihi. Hepsi KAP'tan tarihli/objektif.
- **LLM katmanı (sonra, Faz B):** haber/anlaşma/yönetim/regülasyon yorumu. Türkçe NLP olgunlaşana ve gerçek alfa kanıtlanana kadar ERTELEYİN.

**EM-geçerlilik kararı:** Ayrım sağlam. Kullanıcının endişesi ("olaylar yorum gerektirir, algoritma kötü backtest verir") MEKANİK alt-küme için GEÇERSİZ (onlar yorum gerektirmiyor), LLM alt-küme için GEÇERLİ (onları şimdilik dışarıda bırakın).

---

## TOPIC 5 — MİMARİ: KOMPOZİTE DÖNMEDEN OLAY ENTEGRASYONU

### Sorun
Önceki terk edilen mimari: w1·f1 + w2·f2 ağırlıklı-skor — bu, sinyalleri seyreltir (dilution), her bileşenin katkısını gizler, ve aşırı-optimizasyona (ağırlık curve-fitting) açıktır.

### Çözüm dili: GATE + TRIGGER + FILTER
Olay-driven sistemler doğal olarak KOŞULLU/binary yapıdadır, skor-ağırlık değil. Endüstri pratiği (event-triggered trading patent US 11,941,692 — "conditional order... not based solely on a price of the financial instrument"; "Trade the Event" arXiv; event-driven backtesting motorları):
- **GATE (geçer/geçmez):** Fundamental kalite eşiği — hisse uygun evrende mi? (örn. pozitif öz-sermaye, kâr, likidite/hacim eşiği). Boolean. Geçmezse hiçbir işlem yok.
- **TRIGGER (olay var/yok, tarihli):** Bir olay gerçekleşti mi? (SUE > eşik VE kazanç açıklandı; VEYA bedelsiz duyuruldu). Boolean + tarih.
- **FILTER (opsiyonel teyit):** Olay-penceresi İÇİNDE basit bir teyit (örn. açıklama-günü getirisi pozitif, hacim artışı). Boolean.

İşlem = GATE ∧ TRIGGER ∧ (opsiyonel FILTER). Hepsi VE-mantığı (confluence), toplama değil.

### Confluence kompozit-seyreltme tuzağından nasıl kaçınır
Ağırlıklı skorda zayıf bir sinyal güçlü bir sinyali "telafi edebilir" (w1·düşük + w2·yüksek = orta skor → yanlış işlem). VE-mantığı kapısında telafi YOKTUR: her koşul bağımsız olarak geçmek zorunda. Bu, her bileşenin ayrı ayrı backtest-edilebilir olmasını (fair null'a karşı) ve birinin başarısızlığının diğerini maskelememesini sağlar. Olay-penceresi (event-window) yaklaşımı zamanı da kısıtlar: işlem sadece olaydan sonra N gün içinde açılır, böylece "her gün sinyal arama" gürültüsü ortadan kalkar.

### Pozisyon boyutlandırma
Boyut bir skor DEĞİL, sabit-risk (defined-risk) olmalı: olay tetiklenince sabit %-risk ile gir, olay-penceresi sonunda (örn. 60 gün) veya stop'ta çık. Bu, ağırlık-optimizasyonu cazibesini ortadan kaldırır. Endüstride bu "run-up" ve "post-result trend trade" yapılarıyla uyumludur.

---

## SENTEZ — ÜÇ HİPOTEZİN TEMEL-SAĞLAMLIK SIRALAMASI

### 1. PEAD (EVENT-DRIVEN) — temel: **EVET (en güçlü)**
**Dayanak:** Doğrudan BIST kanıtı (Ahlatcıoğlu & Okay 2021: %2,9 / 60 gün, analist verisi gerektirmeyen geçmiş-kazanç sürpriz ölçütüyle); EM'de mekanizma dirençli (Hung-Li-Wang 2015); veri-realist (KAP bilançosu yeterli); tarihli/objektif (sistematikleştirilebilir). **Uyarılar:** drift küçük firmalarda yoğun (likidite riski, küçük sermaye için kritik); gelişmiş piyasalarda kaybolmuş (BIST'te 2020-sonrası kalıcılığı kendi testinizle doğrulanmalı); %2,9 işlem-maliyeti öncesi brüt. **İLK TEST EDİLECEK.**

### 2. HİBRİT (fundamental GATE + PEAD TRIGGER) — temel: **PARÇALI (umut verici)**
**Dayanak:** Fundamental filtreyi alfa kaynağı olarak DEĞİL, riski azaltan kalite GATE'i olarak kullanmak savunulabilir (zayıf/zarar-eden şirketlerde swing yapmama pratiği makul risk yönetimi). PEAD trigger'ı ile birleştirilince confluence (VE) mantığı kompoziti önler. **Uyarı:** GATE evreni daralttığında PEAD edge'i (küçük firmalarda yoğun) ile çelişebilir — kalite-gate küçük takipsiz firmaları eleyebilir, ki tam da drift'in olduğu yer orası. Bu gerilim kullanıcının kendi verisiyle ölçülmeli. **İKİNCİ TEST.**

### 3. FUNDAMENTAL-FİLTRELİ TEKNİKAL — temel: **HAYIR (bağımsız alfa olarak)**
**Dayanak:** Metghalchi vd. (2021) teknikal edge'i Türk SMALL-CAP'te buldu, LARGE-CAP'te BULAMADI — kullanıcının "devlerde teknikal" pratiğinin AKSİNE. Kullanıcının kendi testleri zaten tüm evrende giriş-zamanlamasının alfa olmadığını gösterdi. Dar/kaliteli evrene daralmak teknikal gücü artırmaz; sadece örneklemi küçültüp gürültüyü artırır. **Karar:** Teknikali bağımsız sinyal olarak DEĞİL, yalnızca olay-penceresi içinde opsiyonel bir teyit FILTER'ı olarak kullanın. Ayrı bir hipotez olarak test etmeye değmez.

---

## SİSTEMATİKLEŞTİRME HARİTASI: olay → algoritma / LLM

| Olay | Tarihli? | Yön bilinir? | Yorum gerektirir? | BIST kanıtı | Katman |
|---|---|---|---|---|---|
| Kazanç açıklaması + SUE | Evet (KAP) | Evet (sürpriz işareti) | Hayır | Güçlü (Ahlatcıoğlu-Okay %2,9 / 60 gün) | **ALGORITMA (öncelik)** |
| Bedelsiz sermaye artırımı | Evet (KAP) | Evet (pozitif) | Hayır | Güçlü ama davranışsal balon (JCMS 2021) | **ALGORITMA** |
| Endeks dahil/çıkarma | Evet (revizyon takvimi) | Evet | Hayır | Zayıf, anticipation-ağırlıklı (Bildik-Gülay 2008) | **ALGORITMA (düşük öncelik)** |
| Nakit temettü | Evet (KAP/ex-date) | Evet ama ters işaret | Hayır | Negatif ilişki (2003-2015, 902 olay) | **ALGORITMA (long için ters)** |
| Şirket haberleri/anlaşma | Kısmen | Hayır | Evet | NLP olgunlaşmamış (TR) | **LLM (Faz B)** |
| Yönetim değişikliği | Evet | Hayır (bağlam) | Evet | Yok | **LLM (Faz B)** |
| Regülasyon/dava | Kısmen | Hayır | Evet | Yok | **LLM (Faz B)** |

---

## KANIT BOŞLUKLARI (literatürün çözemediği, kendi testinizle ölçülmesi gereken)

1. **PEAD'in BIST'te 2020 SONRASI kalıcılığı.** Ahlatcıoğlu-Okay ~2007-2017/18 dönemini kapsıyor; gelişmiş piyasalarda PEAD öldü. BIST'te 2020-2026 döneminde (yüksek enflasyon, retail patlaması) hâlâ var mı — KENDİ VERİNİZLE ölçün.
2. **Küçük-sermaye uygulanabilirliği.** Drift küçük/takipsiz firmalarda yoğun; ~5500 USD ile bu hisselerde işlem-maliyeti/likidite/slipaj sonrası net %2,9'un ne kadarı kalır — literatür çözemez.
3. **Fundamental GATE × PEAD gerilimi.** Kalite-gate, drift'in olduğu küçük firmaları eleyebilir. Net etki (gate uygulanınca edge artar mı azalır mı) sadece kullanıcının kendi backtestiyle bilinir.
4. **Bedelsiz etkisinin sürdürülebilirliği.** "Balon/sürü" olarak yorumlanmış; long-swing'de tutulabilir bir drift mi yoksa açıklama-günü spike'ı mı — olay-penceresi testi gerekli.
5. **Sürpriz eşiği kalibrasyonu.** SUE'nin hangi eşiği (kaçıncı quantile, hangi standartlaştırma penceresi) BIST'te ayrışıyor — data-snooping riskiyle, out-of-sample doğrulama şart.
6. **Türkçe NLP alfa.** Mevcut çalışmalar in-sample doğruluk raporluyor; işlem-maliyeti-sonrası tek-hisse alfa kanıtı yok — Faz B'de kendi testiniz gerekli.

## ÖNERİLER (aşamalı, somut, eşiklerle)
- **Aşama 1 (hemen): PEAD'i test edin.** Geçmiş-kazanç SUE ölçütü (cari çeyrek − geçen yılın aynı çeyreği, son 8 çeyrek std ile standartlaştır) ile, KAP açıklama tarihlerini kullanarak, [t+2, t+61] long-only olay-penceresi. **Karar eşiği:** kendi verinizde fair-null'a karşı anlamlı (t>2) ve işlem-maliyeti-sonrası pozitif net getiri çıkarsa devam; çıkmazsa PEAD'i de eleyin (önceki iki paradigma gibi).
- **Aşama 2 (Aşama 1 başarılıysa): likidite/kalite GATE'i ekleyin.** Sadece risk azaltma amaçlı (zarar-eden/aşırı-illikit hisseleri ele). **Eşik:** GATE eklenince Sharpe artmalı VEYA maksimum drawdown düşmeli; net getiri PEAD-only'nin altına düşerse GATE'i gevşetin (çünkü drift küçük firmalarda).
- **Aşama 3 (paralel/opsiyonel): bedelsiz olay-penceresi.** Ayrı, bağımsız bir mekanik strateji olarak test edin; PEAD ile aynı confluence-mimarisinde. **Eşik:** açıklama-günü spike'ından SONRA tutulabilir drift varsa devam.
- **Faz B (ileride): LLM katmanı.** Sadece mekanik katman kârlı ve istikrarlı olduktan sonra; Türkçe haber-yorumunu binary trigger'a çeviren bir modül, AYRI backtest ile.
- **Mimari kuralı (hepsinde):** GATE ∧ TRIGGER ∧ FILTER (VE-mantığı), ağırlıklı skor YOK; sabit-risk pozisyon boyutu, optimizasyon-edilmiş ağırlık YOK.

## KISITLAR VE UYARILAR
- BIST kanıtı önceliklendirildi; gelişmiş-piyasa kanıtı (quality+momentum, event-driven NLP) transfer-şüpheli olarak işaretlendi.
- PEAD/olay literatürü data-snooping'e açık; raporlanan getiriler işlem-maliyeti öncesi brüt rakamlardır.
- "Devlerde teknikal" sezgisi literatürle desteklenmiyor — bu bir inanç, kanıt değil; Metghalchi kanıtı bunun aksini söylüyor.
- Ahlatcıoğlu-Okay'ın tam dönem/örneklem-N'si birincil PDF'den teyit edilemedi (companion paper'lardan ~2007-2017, ~396 firma çıkarımı yapıldı).
- Kilimci & Duvar (2020) çalışması taslakta "BERTurk %82-86" olarak hatalı nitelenmişti; düzeltildi — o çalışma kelime-gömme + LSTM/RNN/CNN ile BIST-100 banka-hissesi yönü tahmin ediyor, tek-hisse olay-alfa değil.