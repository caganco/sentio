# RR-041 — BIST Swing Trading: Giriş Sinyali Kalitesini Çıkıştan Arınmış ve Look-Ahead'siz Ölçme Metodolojisi

## TL;DR (terimsiz, 8 madde)
1. **Sinyal kalitesi çıkıştan ayrılabilir.** Çözüm: sinyalin tetiklediği hareketi "trade'in P&L'i" olarak değil, **sinyalden sonra fiyatın kendi başına ne yaptığı** olarak ölçmek. Stop/trailing'i tamamen kaldır; sadece "fiyat sinyalden sonra X gün içinde ne kadar gitti / hedefe ulaştı mı, ne kadar sürede" sorusuna bak.
2. **Üç farklı mercek kullan, biri yetmez:** (a) sabit-horizon ileri-getiri (5/10/21/63 gün), (b) TP-bazlı bariyer-değerlendirme (hedefe ulaşma oranı + süre), (c) benchmark'a-göre anormal getiri (CAR). Her biri farklı şeyi ölçer; üçü birlikte sağlam resim verir.
3. **TP-bazlı yöntem sağlam VE akademik temeli var:** López de Prado'nun **triple-barrier (üçlü bariyer)** yöntemi felsefenin akademik karşılığı. Saf sinyal kalitesi için stop bariyerini KAPAT, sadece TP + zaman bariyeri bırak ("tek-taraflı bariyer"). Look-ahead'sizdir çünkü bariyer t anında konur.
4. **TP kısmen sistematize edilebilir, ama saf algoritmik yöntemler folklor riski taşır.** En sağlam objektif TP: **volatilite-ölçekli (ATR-katı / günlük-vol-katı) hedef.** Sabit R-multiple ve geçmiş-swing-yüksek de savunulabilir. Fibonacci ve "measured move" zayıf kanıtlı. Direnç-seviyesi TP'sinin sınırlı ama gerçek öngörü gücü vardır (Osler kanıtı: en iyi firma rastgele seviyelerden %9.2 daha iyi öngördü).
5. **Aracı-kurum hedef-fiyatları TP kaynağı olarak ZAYIF.** Türkiye'ye özgü kanıt (Şahin 2020), BIST hedef fiyatlarının fiyatı öngörmek yerine — özellikle bankacılık/holding/GYO'da — fiyatı TAKİP ettiğini gösteriyor; sistematik yukarı-yönlü iyimserlik var. Edge kaynağı olarak güvenme.
6. **BIST noise gerçek ve tehlikeli:** %10 günlük fiyat limiti, düşük likidite, kapanış manipülasyonu, fat-tail/çarpıklık. Tek-gün spike ortalama-getiriyi şişirir. Çözüm: **kapanış-bazlı ölç, ortalama yerine medyan + kazanan-oranı kullan, çoklu-gün onayı iste, intraday high-touch'a güvenme.**
7. **Ortalama getiri BIST'te yanıltıcıdır.** Fat-tail ve çarpıklık nedeniyle birkaç ekstrem getiri ortalamayı domine eder. Medyan, kazanan-oranı ve hit-rate çok daha sağlam metriklerdir.
8. **Random-benchmark zorunlu:** Sinyali değerlendirmek için aynı hisse-evreninde, aynı horizon'da **rastgele giriş** null'ı kur (Monte Carlo permütasyon). "Sinyal %60 hit-rate yaptı" cümlesi, rastgele girişin de %58 yaptığı ortaya çıkana kadar anlamsızdır.

---

## KONU 1 — SİNYAL-KALİTESİ İZOLASYONU (çıkıştan arınmış, look-ahead'siz)

**Temel prensip:** Bir çıkış mekanizması (stop+trailing) sinyalin getirisine karışır çünkü ne zaman/nerede çıkılacağına dair kurallar performansı şekillendirir. D-185/186'da yaşanan tam olarak budur: ölçülen edge sinyalden değil çıkış kurallarından gelmiş olabilir. Sinyali saf ölçmek için **çıkış kararını ölçümden çıkar** ve fiyatın sinyalden sonra kendi doğal yörüngesini incele.

### (a) Sabit-horizon forward return
Sinyal anında (t) gir, **önceden belirlenmiş N gün sonra** (t+N) getiriyi ölç. Çıkış kuralı yok — pozisyon mekanik olarak N günde "kapanır" (gerçek kapanış değil, ölçüm noktası). Bu, çıkış-mekanizmasını dışlar çünkü ne stop ne trailing devreye girer; sadece "fiyat N günde nereye gitti" ölçülür.
- **N seçimi (swing için):** Tek bir N seçme — **çoklu-horizon analizi standarttır.** Profesyonel faktör-değerlendirme araçları (ör. Alphalens) rutin olarak 5/10/21 günlük (ve daha uzun) pencereleri paralel hesaplar. Swing trading için 5, 10, 21 ve 63 işlem günü (≈1 hafta, 2 hafta, 1 ay, 1 çeyrek) makul bir set. Çoklu-horizon, sinyalin **bilgi-horizonu**nu (alfa ne kadar sürede gerçekleşir ve ne zaman söner) ortaya çıkarır. Momentum sinyalleri kısa horizon'da güçlü olup hızla söner; değer sinyalleri yavaş söner.
- **Information Coefficient (IC):** Sinyal sürekli bir skor üretiyorsa, sinyal-değeri ile ileri-getiri arasındaki **rank korelasyonu (Spearman)** sinyal kalitesinin standart ölçüsüdür. Rank-IC, ekstrem değerlere (BIST fat-tail!) Pearson'dan daha dayanıklıdır. ABD hisselerinde aylık ortalama IC %5–6 "çok güçlü" sayılır — beklentileri buna göre ayarla.

### (b) Forward-return dağılımı (sadece ortalama değil)
Sinyal kalitesi tek bir sayı değildir; **dağılımdır.** Raporlanması gereken metrikler:
- **Medyan forward-return** (ortalamadan sağlam; fat-tail'i absorbe eder)
- **Kazanan-oranı** (forward-return > 0 olan sinyal yüzdesi)
- **Çarpıklık ve asimetri** (kazançlar mı kayıplar mı domine ediyor)
- **Dağılımın çeyrekleri** (Q1/Q3) ve kuyruk davranışı

Yalnız ortalama raporlamak BIST'te **tehlikeli** — birkaç limit-yukarı günü ortalamayı şişirir, ama tipik işlemi temsil etmez.

### (c) Event-study standardı (CAR)
**Olay-çalışması metodolojisi** (MacKinlay 1997'de formalize edilmiş) sinyali bir "olay" olarak ele alır ve **anormal getiri** (gerçekleşen getiri eksi beklenen/benchmark getiri) hesaplar. **CAR (cumulative abnormal return)** olay-penceresi boyunca anormal getirileri toplar.
- **Neden değerli:** Ham forward-return, sinyal-günü tüm piyasa yükseldiği için pozitif olabilir. CAR bunu düzeltir — sinyal **piyasaya/benchmark'a göre** (BIST 100 veya sektör endeksi) ekstra ne kazandırdı? Bu, BIST'in TL-bazlı enflasyonist nominal yükselişini de nötralize eder (kritik: BIST nominal getiriler enflasyon/devalüasyonla şişer).
- **Beklenen getiri modeli:** Market-model (hisse getirisini BIST 100'e regrese et, tahmin-penceresinde) veya basit market-relative (hisse getirisi − endeks getirisi). BIST için sektör-endeksi benchmark'ı da düşün.

### Bu yöntemler çıkışı NASIL dışlar?
Üçü de **çıkış kararı içermez.** Sabit-horizon mekanik olarak t+N'de ölçüm yapar. CAR olay-penceresi boyunca pasif olarak getiri biriktirir. Hiçbir stop/trailing/discretionary çıkış devreye girmez. Böylece ölçülen tamamen **sinyalin öngörü gücüdür**; çıkış becerisinin katkısı sıfırdır.

### TUZAK-UYARILARI (Konu 1)
- ⚠️ **Ortalama forward-return BIST'te güvenilmez.** Fat-tail nedeniyle medyan + kazanan-oranı kullan.
- ⚠️ **Tek-horizon yanıltır.** N=5'te güçlü görünen sinyal N=21'de sönmüş olabilir; çoklu-horizon zorunlu.
- ⚠️ **Overlapping (örtüşen) gözlemler bağımsızlık varsayımını bozar.** Aynı hisse için art arda sinyaller örtüşen pencereler üretir → istatistik testleri yanlış güven verir. López de Prado bunu açıkça uyarır; örnek-ağırlıklandırma veya örtüşmeyen örnekleme gerekir.
- ⚠️ **CAR'ın çok-günlük testlerinde varyans-değişimi ve seri-korelasyon** standart t-testini bozar; non-parametrik testler (Konu 4) gerekir.

---

## KONU 2 — TP-BAZLI DEĞERLENDİRME (triple-barrier ile sistematize)

Bu, sistem-sahibinin felsefesinin ("sinyal anında TP koy, ulaştı mı, ne kadar sürede?") doğrudan akademik karşılığıdır.

### (a) TP hedefini sinyal-anında OBJEKTİF belirleme (look-ahead'siz)
TP, **t anında bilinen bilgiyle** konmalı. Look-ahead'siz seçenekler:
1. **Volatilite-ölçekli (en sağlam):** TP = giriş + k × (t anındaki ATR veya günlük-vol). López de Prado'nun tercih ettiği yaklaşım budur — sabit eşik yerine **her sinyalin kendi volatilitesine göre** dinamik bariyer. *Advances in Financial Machine Learning* (Wiley, 2018), Bölüm 3 (Labeling, s. 43–45): fixed-horizon yöntem "observations are given a label with respect to a certain threshold after a fixed interval regardless of their respective volatilities... stock returns are known to be heteroskedastic"; triple-barrier ise "dynamically setting the upper and lower barriers for each observation based on their given volatilities." Düşük-vol dönemde dar, yüksek-vol dönemde geniş hedef.
2. **Sabit R-multiple:** TP = giriş + R × (risk birimi). Risk birimi yine ATR/vol'den türetilir, dolayısıyla (1)'in bir çeşididir.
3. **Geçmiş-swing-yüksek / direnç:** t anında görünür son swing-high veya direnç seviyesi. Look-ahead'siz olması için **yalnız geçmiş** pivot'lar kullanılmalı.
4. **Sabit yüzde:** TP = giriş × (1+%X). Basit ama volatiliteyi görmezden gelir → BIST'te zayıf.

### (b) Hit-rate + ulaşma-süresi + ulaşamazsa nerede kaldı
Bu üç metrik sinyal kalitesini şöyle yansıtır:
- **TP'ye ulaşma oranı (hit-rate):** Sinyalin "gideri" olup olmadığının doğrudan ölçüsü. Yüksek hit-rate = sinyal gerçekten hareket öngörüyor.
- **Ulaşma süresi (time-to-target / first-passage time):** Hızlı ulaşım = güçlü/keskin sinyal; yavaş ulaşım = zayıf drift. Medyan-ulaşma-süresi raporla.
- **Ulaşamazsa nerede kaldı (terminal/MFE):** Zaman-bariyerinde fiyat nerede? Ve **MFE (Maximum Favorable Excursion)** — fiyat hedefe ulaşmasa bile en fazla ne kadar lehe gitti? MFE saf sinyal-potansiyelini ölçer ve çıkıştan tamamen bağımsızdır. **MAE (Maximum Adverse Excursion)** ise sinyalin "giriş kalitesini" (ne kadar ters gitti) ölçer — düşük MAE = iyi giriş zamanlaması. (Bu metrikler John Sweeney, *Campaign Trading*, 1996'da formalize edildi.) Pratik kural: yüksek MFE-yakalama-oranı + kötü P&L → sorun çıkışta değil **giriş/sinyal kalitesinde**dir; bu da tam olarak ölçmek istediğimiz şey.

### (c) First-passage-time / barrier-hit literatürü
"Fiyat bir bariyere ne zaman/ne olasılıkla ulaşır" problemi **first-passage-time (ilk-geçiş-zamanı)** literatürünün tam konusudur (fizik/finanstan; bariyer-opsiyon fiyatlamasında olgun). Bu literatür problemine **doğrudan uygulanabilir** ve iki şey sağlar: (1) hit-olasılığının ve ulaşma-süresinin teorik dağılımı, (2) bir **null model** — saf rastgele yürüyüş (GBM) altında fiyatın TP'ye ulaşma olasılığı. Sinyalin hit-rate'ini bu GBM-null hit-rate ile karşılaştırmak edge'i izole eder. Stokastik-volatilite (Heston) altında da analitik çözümler mevcut, ki BIST'in değişken volatilitesi için daha gerçekçi. Not: First-passage çalışmaları (örn. arXiv 0902.2735), geleneksel risk-ölçümünün bir seviyeye ulaşma olasılığını **olduğundan az** tahmin ettiğini, ilk-geçiş yaklaşımının daha doğru olduğunu vurgular.

### (d) Triple-barrier method (López de Prado) — tercih edilen çerçeve
**Bu, aradığın akademik çerçevenin ta kendisi.** *Advances in Financial Machine Learning* (Wiley, 2018), Bölüm 3'te tanımlı. Üç bariyer:
- **Üst bariyer (TP/profit-taking):** kâr-al seviyesi
- **Alt bariyer (stop-loss):** zarar-kes seviyesi
- **Dikey bariyer (zaman):** maksimum tutma süresi

Hangisine **önce** dokunulursa etiket o olur (+1 TP, −1 stop, dikey'de getiri-işareti veya 0).

**Senin felsefene en yakın uyarlama — SAF SİNYAL İÇİN STOP'U KAPAT:** López de Prado yatay bariyerlerin **bağımsız** ayarlanabileceğini ve bir bariyerin **devre-dışı** bırakılabileceğini (genişlik = 0) açıkça söyler. Sinyal kalitesini çıkıştan arındırmak için: **alt (stop) bariyeri kapat, sadece üst (TP) + dikey (zaman) bariyeri bırak.** Böylece "sinyal verilen hisse, fiyat hedefe ulaşana kadar ne kadar yükseldi ve ne kadar sürede; yoksa zaman-bariyerinde nerede kaldı?" sorusunu **tam olarak** ölçersin. Bu, sistem-sahibinin tarifinin birebir formalizasyonudur.

**Look-ahead kontrolü:** Bariyerler **t anında** (sinyal anı) konur, gelecek görülmez. Etiketleme geriye dönük yapılsa da bariyer-seviyeleri yalnız t-bilgisiyle (sinyal-anı volatilitesi) belirlendiği için look-ahead yoktur. Bu, López de Prado'nun (ve Hudson & Thames implementasyonunun) açıkça vurguladığı bir özelliktir: özellikler gecikmeli kullanılır, bariyerler sinyal-anı verisinden türetilir.

**Neden fixed-horizon'dan üstün:** Fixed-horizon **yol-bağımsız**dır (path-independent) — sadece t+N'deki getiriye bakar, aradaki yolu görmez. Triple-barrier **yol-bağımlı**dır: fiyatın hedefe ne zaman/nasıl ulaştığını yakalar. Senin "ne kadar sürede" sorun tam da yol-bağımlılığı gerektirir. (Bu yüzden Mercek 1 ve Mercek 2 birbirini tamamlar; biri yolu görmezden gelip ham getiriyi, diğeri yolu/zamanı ölçer.)

### TUZAK-UYARILARI (Konu 2)
- ⚠️ **Triple-barrier yol-bağımlıdır ve intraday high/low gerektirir.** "TP'ye değdi mi" sorusu gün-içi high'a bakarsa, BIST'in gün-içi spike'ları/manipülasyonu **sahte hit** üretir. Çözüm: kapanış-bazlı hit tanımı veya çoklu-gün onayı (Konu 4).
- ⚠️ **Sabit eşikli TP heteroskedastisiteyi görmezden gelir** (López de Prado'nun fixed-horizon eleştirisinin aynısı). Volatilite-ölçekli TP kullan.
- ⚠️ **Dikey bariyerde etiket seçimi sonucu etkiler.** Zaman-aşımında "getiri-işareti" mi "0" mı? Sistem-sahibinin felsefesi için **terminal-getiri + MFE** raporlamak en bilgilendiricidir.

---

## KONU 3 — TP'NİN SİSTEMATİZE-EDİLEBİLİRLİĞİ

İnsan grafiğe bakıp "şu direnç TP olur" diyor. Sistem bunu objektif yapabilir mi?

### (a) Algoritmik TP yöntemleri — kanıtlı mı, folklor mu?
- **Volatilite-ölçekli (ATR-katı) — KANITLI/SAĞLAM.** Akademik temeli güçlü (López de Prado), heteroskedastisiteyi doğru ele alır, tamamen objektif ve look-ahead'siz.
- **Support/resistance (direnç) — KISMEN KANITLI.** Carol L. Osler, "Support for Resistance: Technical Analysis and Intraday Exchange Rates," *FRBNY Economic Policy Review*, Vol. 6, No. 2 (July 2000), pp. 53–68: altı döviz firmasının 1996–98 dönemi yayınladığı destek/direnç seviyeleri "strong evidence that the levels help to predict intraday trend interruptions" sağladı — en iyi firma rastgele seçilmiş seviyelerden **%9.2 daha iyi** öngördü ve seviyelerin **%70'inden fazlası yuvarlak sayılarla** bitiyordu. Öngörü gücü döviz-çiftleri ve firmalar arası **değişken**ti. Algoritmik S/R tespiti (pivot-clustering, ZigZag, Donchian) mümkün; Chan, Phoong, Cheng & Chen, "Support Resistance Levels towards Profitability in Intelligent Algorithmic Trading Models," *Mathematics* 2022, 10(20):3888: S/R özellikleri "increased the machine learning model's aggregate profitability performance by 65% across eight currency pairs." **Folklor uyarısı:** Osler "anlaşmada güç yok" buldu — birden çok kaynağın hemfikir olduğu seviye, tek kaynağınkinden daha güçlü değil.
- **Geçmiş-swing-yüksek — SAVUNULABILIR.** Objektif, look-ahead'siz; momentum/breakout mantığıyla uyumlu.
- **Fibonacci — FOLKLOR RİSKİ YÜKSEK.** Sağlam akademik kanıt zayıf; öz-gerçekleşen-kehanet etkisi dışında öngörü gücü tartışmalı.
- **Measured-move / ölçülü-hareket — ZAYIF KANITLI.** Sezgisel; sistematik kanıt sınırlı.

### (b) Aracı-kurum hedef fiyatları TP kaynağı olabilir mi?
**BIST'te ZAYIF ve riskli.** Türkiye'ye özgü kanıt:
- **Şahin (2020, Karadeniz Teknik Üniv. doktora tezi + ilgili makale, *Uluslararası İktisadi ve İdari İncelemeler Dergisi*):** 2010–2017 BIST verisinde, Granger/Toda-Yamamoto nedensellik testleriyle, **bankacılık/holding/GYO sektörlerinde hisse fiyatları hedef-fiyatları tek-yönlü etkiliyor** — yani hedefler fiyatı öngörmek yerine fiyatı takip ediyor (anchoring). Sadece sanayi sektöründe çift-yönlü ilişki var.
- **Erdogan ve diğ. (2010), "Performance of Analyst Recommendations in the Istanbul Stock Exchange":** "sonuçlarımız analistlerin üstün hisse-seçme becerisine sahip OLMADIĞIyla tutarlıdır."
- **"Who to trust?" (2021, Finance Research Letters):** 111 BIST hissesi, 3.191 tavsiye (Eylül 2016–Ekim 2019); yükseltme-tavsiyeleri anons-günü ortalama **+35 bps** (yabancı-aracı +57, yerel +29), düşürme **−45 bps** anormal getiri. Kısa-vadeli bilgi içeriği var ama bu hedef-fiyat *ulaşımı* değil.
- **Genel EM kanıtı (Taiwan; Hsieh ve diğ., "A multi-dimensional assessment of the accuracy of analyst target prices," 2024):** sistematik yukarı-bias **%9.4**, mutlak fiyatlama hatası **%24.8**, fiyat-değişimini aşırı-tahmin **%21**, ve **doğru yön sadece %54** (yazı-tura'dan az fazla). 1-yıl horizonunda mutlak hata %39.1.
- **16-ülke uluslararası (Türkiye dahil DEĞİL; Bilinski, Lyssimachou & Walker, "Target Price Accuracy: International Evidence," *The Accounting Review* 88(3):825–851, 2013, 2002–2009 IBES):** hedef 12 ayda **%59.1** vakada tutuluyor (en düşük İtalya %54.0, en yüksek Avustralya %66.1); ortalama mutlak hata **%44.7**. Hedefler naif-tahminden %74.5 vakada daha iyi, hata %9.8 daha düşük — yani naiften iyi ama mutlak olarak isabetsiz.

**Sonuç:** Aracı-kurum hedefleri **bağımsız edge kaynağı olarak güvenilmez**; özellikle BIST'te fiyatı takip ediyorlar ve iyimserlik-bias'ı taşıyorlar. Olsa olsa **karşılaştırma referansı** veya zayıf bir özellik olarak kullan.

### (c) KRİTİK: İnsan-TP vs algoritmik-TP performans farkı
Literatürde **doğrudan "insan-TP vs algo-TP"** karşılaştırması seyrek; ama dolaylı kanıt net: Osler insan-yayınlı S/R'nin gerçek (ama değişken) öngörü gücü olduğunu gösterdi, *Mathematics* 2022 çalışması ise **algoritmik S/R'nin ML-modeline somut kârlılık kattığını** gösterdi (%65 artış). Genel sonuç: **iyi-tasarlanmış algoritmik TP, insan-TP'ye yakın veya onu aşan tutarlılık sağlar ve ölçeklenebilir/önyargısızdır.** Ancak insan, **bağlamı** (haber, likidite, manipülasyon işareti) algoritmadan daha iyi okuyabilir.

**Pratik öneri:** TP'yi **volatilite-ölçekli objektif yöntemle sistematize et** (ana yöntem), direnç-tabanlı TP'yi ikincil mercek olarak ekle. Sinyal-kalitesini ölç ve **TP-seçimini ayrı bir değişken olarak test et** — böylece "edge sinyalde mi, TP-seçiminde mi?" sorusu da yanıtlanır (D-185/186 hatasının tekrarını önler).

### TUZAK-UYARILARI (Konu 3)
- ⚠️ **Direnç/S-R seviyeleri look-ahead sızdırabilir.** Yalnız t-öncesi pivot'lar kullanılmalı; gelecekteki high'a göre çizilen "direnç" sahte sonuç verir.
- ⚠️ **Aracı-kurum hedefi BIST'te fiyatı takip ediyor** (Şahin 2020) — öngörü sanılan şey aslında anchoring olabilir.
- ⚠️ **Fibonacci/measured-move folklor riski** — kanıtlı yöntem gibi sunma.

---

## KONU 4 — BIST-SPESİFİK TUZAKLAR (noise + asimetri)

### (a) BIST günlük noise'u sinyal-değerlendirmeyi nasıl bozar
- **%10 günlük fiyat limiti:** BIST Stars/Main hisselerinde fiyat-marjı bir önceki seansın VWAP'ından ±%10. Bu, hem hit-rate ölçümünü çarpıtır (fiyat limite takılır, TP'ye "ulaşamaz" ama momentum gerçektir) hem de tek-gün getirilerini kümelendirir.
- **Devre-kesici (circuit breaker):** Hisse-bazlı (son açık-artırma fiyatının %10'unda statik) ve endeks-bazlı (BIST 100 belirli eşiklerde durur; Eylül 2025'ten itibaren tek-aşamalı %6). İşlem-durması veri-boşlukları ve fiyat-sıçramaları yaratır.
- **Düşük likidite / thin trading:** Küçük hisselerde geniş bid-ask, daha yüksek volatilite ve mikroyapı-noise'u "etkin" getiriye eklenir (BIST mikroyapı çalışmaları — Inci & Ozenbas 2017; Aktas & Kryzanowski 2014 — bunu doğruluyor).
- **Kapanış manipülasyonu:** BIST'te kapanış-fiyat manipülasyonu literatürde belgeli; 2012'de kapanış-açık-artırması (closing call auction) bunu azaltmak için getirildi.
- **Tek-gün spike:** Manipülasyon veya haber kaynaklı tek-gün sıçraması, intraday-high'a bakan TP-hit ölçümünü **sahte-pozitif**le doldurur.

### (b) Noise'a-dayanıklı sinyal-değerlendirme
- **Kapanış-bazlı ölç, intraday-touch'a güvenme.** TP-hit'i "gün-içi high TP'ye değdi" yerine **"kapanış TP'yi aştı"** olarak tanımla → manipülatif fitilleri eler.
- **Çoklu-gün onayı:** TP-hit'i "ardışık 2 kapanış TP üzerinde" gibi tanımla → tek-gün spike'ı filtreler.
- **Forward-return düzleştirme (smoothing):** Tek-gün t+N yerine, t+N civarı birkaç-günlük ortalama-kapanış kullan → uç-gün etkisini azaltır.
- **Volatilite-ölçekli bariyer:** Sabit-yüzde TP yerine ATR-katı → düşük/yüksek-vol rejimlerini adil karşılaştırır.

### (c) BIST getiri-dağılımı asimetrisi → metrik seçimi
BIST getirileri **leptokurtik (fat-tail) ve çarpık** (gelişen-piyasa tipik; BIST GARCH çalışmaları güçlü volatilite-persistansı ve kümelenme buluyor — Bulut 2024 sektörel GARCH analizi). Sonuçlar:
- **Ortalama yanıltıcı.** Birkaç ekstrem getiri ortalamayı domine eder; örneklem-kurtosis tek bir aykırı-değerle patlar (999 normal gözleme tek bir uç-değer eklenince kurtosis 800'ün üstüne fırlayabilir).
- **Medyan + kazanan-oranı + hit-rate çok daha sağlam.** Bunlar fat-tail'e dayanıklıdır.
- **Yüksek momentler (skew/kurtosis) güvenilmez tahmin edilir** — yavaş yakınsama; küçük örneklemlerde kullanma.

### (d) Random-benchmark (saf sinyal, çıkış yokken)
**Bu, D-185/186 hatasını önlemenin anahtarıdır.** Sinyal kalitesi mutlak değil, **göreceli** anlamlıdır: aynı koşulda rastgele giriş ne yapardı?
- **Aynı-horizon random-giriş null'ı:** Aynı hisse-evreni, aynı tarih-dağılımı, aynı N-gün horizon, ama **rastgele seçilmiş giriş günleri.** Sinyalin forward-return/hit-rate dağılımını bu null-dağılımla karşılaştır.
- **Monte Carlo permütasyon testi (Timothy Masters):** Log-getirileri permüte ederek edge'i olmayan sentetik fiyat-yolları üret, sinyali her birinde yeniden çalıştır → gerçek **p-değeri.** 1.000 permütasyon standart minimum. "Sinyal X% hit-rate yaptı" ifadesi, permütasyonların yalnız küçük bir kısmı bunu aşana kadar anlamlı değildir.
- **GBM/first-passage null:** TP-hit-rate için, saf rastgele-yürüyüş altında teorik hit-olasılığını hesapla ve sinyalin hit-rate'ini bununla kıyasla.

### TUZAK-UYARILARI (Konu 4)
- ⚠️ **Intraday high-touch TP-hit BIST'te sahte-pozitif üretir** (manipülasyon/spike). Kapanış-bazlı tanım kullan.
- ⚠️ **%10 limit hit-rate'i hem şişirir hem keser** — limite takılan günleri ayrı işaretle.
- ⚠️ **Standart t-testi BIST'te yanlış güven verir** (non-normal, thin-trading, event-induced varyans). Non-parametrik testler kullan: **Corrado rank-testi** ve **generalized sign-testi** thin-trading'de parametrik testlerden üstün ve daha doğru-spesifiye (Cowan 1996; Kolari & Pynnönen GRANK-testi). Generalized sign-testi özellikle thin-trading ve uzun pencerelerde rank-testinden daha dayanıklı.
- ⚠️ **TL-bazlı nominal getiri enflasyon/devalüasyonla şişer** — CAR/benchmark-relative ölç veya reel-getiriye çevir.

---

## SENTEZ — ÖNERİLEN ÖLÇÜM PROTOKOLÜ

Sinyal-felsefesini ("sinyal ne kadar gider yaptı + TP-bazlı, çıkış karıştırmadan") look-ahead'siz, BIST-noise-dayanıklı, çıkıştan-arınmış ölçen **üç-mercekli protokol.** Her mercek farklı soruyu yanıtlar; üçü birlikte sağlam karar verir.

### MERCEK 1 — Sabit-horizon forward-return dağılımı (sinyalin ham gücü)
- Sinyal anında gir, çıkış kuralı YOK. t+5, t+10, t+21, t+63 işlem-günü **kapanış** getirilerini ölç.
- Raporla: **medyan, kazanan-oranı, Q1/Q3, çarpıklık** (ortalama ikincil). Sürekli sinyal varsa **rank-IC**.
- **Ne ölçer:** Sinyalin saf öngörü gücü ve bilgi-horizonu (alfa ne zaman söner). Yol-bağımsız.

### MERCEK 2 — TP-bazlı tek-taraflı triple-barrier (felsefenin birebir karşılığı)
- Sinyal anında **volatilite-ölçekli TP** (k × ATR_t) + **zaman bariyeri** (ör. 21 gün) koy. **Stop bariyerini KAPAT.**
- TP-hit'i **kapanış-bazlı** (tercihen 2-gün-onaylı) tanımla → BIST spike'larını eler.
- Raporla: **hit-rate, medyan-ulaşma-süresi (first-passage), zaman-aşımında terminal-getiri, ve MFE dağılımı.**
- **Ne ölçer:** "Fiyat hedefe ulaştı mı, ne kadar sürede, ulaşamazsa nerede kaldı?" — sistem-sahibinin tam sorusu, çıkıştan arınmış, yol-bağımlı.

### MERCEK 3 — Benchmark-relative CAR (gerçek edge mi, piyasa mı?)
- Sinyal-olayı etrafında BIST 100 (ve/veya sektör-endeks) market-model ile **anormal getiri** ve **CAR** hesapla; aynı horizon'larda.
- **Ne ölçer:** Sinyalin piyasanın üstünde ekstra getirisi; TL-nominal şişmeyi nötralize eder.

### HER MERCEK İÇİN ZORUNLU NULL
Üç merceğin **her birini** rastgele-giriş null'ı ve **Monte Carlo permütasyon** (≥1.000) ile karşılaştır. Sinyal, null-dağılımı istatistiksel anlamlılıkla (non-parametrik: Corrado rank / generalized sign testi) aşmıyorsa **edge yoktur.**

### KARAR-EŞİKLERİ
- Sinyal **ancak** şu durumda "kaliteli": (1) medyan forward-return ve hit-rate random-null'ı anlamlı aşıyor, (2) CAR pozitif ve anlamlı, (3) bu üçü **birden çok horizon**'da tutarlı.
- Eğer sinyal sadece MERCEK 2'de (TP-hit) parlıyor ama MERCEK 1/3'te null'ı aşamıyorsa → edge muhtemelen **TP-seçiminden** geliyor, sinyalden değil (D-185/186'nın TP-versiyonu tuzağı).
- Eğer hit-rate kapanış-bazlı tanımda intraday-touch tanımına göre **belirgin düşüyorsa** → ölçülen "gider" büyük ölçüde gün-içi noise/spike'tan geliyordu; sinyal zayıftır.

---

## SİSTEMATİZE NOTU — TP algoritmik mi, insan-TP mi?

**Karar: TP'yi PRİMER olarak algoritmik (volatilite-ölçekli) belirle; sinyal-kalitesini TP-seçiminden AYRI ölç.**
- **Ana TP yöntemi:** k × ATR_t (objektif, look-ahead'siz, heteroskedastisiteyi doğru ele alan, ölçeklenebilir). López de Prado'nun önerisiyle birebir uyumlu.
- **İkincil mercek:** geçmiş-swing-yüksek / direnç-tabanlı TP (Osler kanıtlı ama değişken; yalnız t-öncesi pivot'larla).
- **Aracı-kurum hedefi:** edge kaynağı olarak KULLANMA (BIST'te fiyatı takip ediyor — Şahin 2020; iyimser-bias). Olsa olsa zayıf bir karşılaştırma-özelliği.
- **Kritik test:** Sinyal-kalitesini **birden çok TP-tanımıyla** ayrı ayrı ölç. Eğer sinyalin "iyiliği" hangi TP kullanıldığına aşırı duyarlıysa → ölçülen şey TP-seçimi, sinyal değil. Sinyal sağlamsa, makul TP-tanımları arasında hit-rate tutarlı kalmalı. Bu, "edge nereden geliyor" sorusunu kesin yanıtlar.
- **İnsan-TP'nin yeri:** Bağlam-okuması (manipülasyon işareti, likidite, haber) için insan değerli; ama **ölçüm/backtest** için insan-TP look-ahead ve öznellik riski taşır → sistematik test algoritmik TP ile yapılmalı.

---

## KANIT BOŞLUKLARI — Kendi testimizle ne netleşmeli?

1. **BIST'e özgü optimal N ve TP-çarpanı (k):** Literatür ABD/EM odaklı. BIST'in alfa-decay'i ve volatilitesi için 5/10/21/63 ve k-değerlerini **kendi verimizle** kalibre etmeliyiz. Hangi horizon'da sinyalimiz en yüksek IC/hit-rate veriyor?
2. **TP-seçim duyarlılığı (en kritik):** Sinyal-kalitesi, TP-tanımına (ATR-katı vs direnç vs yüzde) ne kadar duyarlı? Düşük duyarlılık = sağlam sinyal; yüksek duyarlılık = ölçtüğümüz aslında TP-seçimi (D-185/186 tuzağının TP-versiyonu). **Sadece kendi testimiz bunu çözer.**
3. **Kapanış-bazlı vs intraday-touch hit-rate farkı:** BIST manipülasyon/spike'ı hit-rate'i ne kadar şişiriyor? İki tanımı yan-yana çalıştırıp farkı ölçmeliyiz.
4. **%10 limit ve devre-kesici etkisi:** Limite-takılan/durma yaşayan sinyaller hit-rate'i ne yönde çarpıtıyor? Bunları ayrı işaretleyip etkisini ölçmeliyiz.
5. **Random-null'ın gerçek seviyesi:** BIST'te aynı-horizon rastgele-girişin hit-rate/forward-return dağılımı nedir? Bu null bilinmeden hiçbir sinyal-metriği yorumlanamaz — **ilk kurulması gereken şey budur.**
6. **TL-nominal vs reel/benchmark-relative:** Enflasyonist ortamda nominal getiriler ne kadar şişiyor; CAR'a geçince edge ne kadar kalıyor? Kendi verimizde her ikisini hesaplayıp farkı görmeliyiz. (Türkiye'nin yüksek enflasyon/lira-devalüasyon ortamı nominal hit-rate'leri yapay yükseltir; hiçbir mevcut çalışma bunu açıkça kontrol etmiyor — kendi testimizde reel/benchmark-relative düzeltme şart.)
7. **MFE-tabanlı saf-potansiyel:** Sinyallerimizin MFE dağılımı nedir — fiyat hedefe ulaşmasa bile tipik olarak ne kadar lehe gidiyor? Bu, gelecekteki çıkış-tasarımını da besler (ama önce saf sinyal ölçümü).

---

### Yöntem-Kaynak Eşlemesi (özet)
- **Triple-barrier + heteroskedastisite eleştirisi:** López de Prado, *Advances in Financial Machine Learning* (Wiley, 2018), Bölüm 3, s. 43–45 + "10 Reasons Most ML Funds Fail" (GARP).
- **CAR / event-study:** MacKinlay (1997); Brown & Warner (1985).
- **Non-parametrik EM/thin-trading testleri:** Cowan (1992, generalized sign); Corrado rank-testi; Kolari & Pynnönen GRANK; "Trading frequency and event study test specification."
- **Support/resistance öngörü gücü:** Osler, FRBNY Economic Policy Review (2000); Chan ve diğ., *Mathematics* 10(20):3888 (2022).
- **BIST analyst/target price:** Şahin (2020, KTÜ); Erdogan ve diğ. (2010); "Who to trust?" (FRL 2021). EM/uluslararası karşılaştırma: Hsieh ve diğ. (2024, Taiwan); Bilinski, Lyssimachou & Walker, *The Accounting Review* 88(3) (2013).
- **Random-benchmark:** Timothy Masters, *Permutation and Randomization Tests for Trading System Development*.
- **MFE/MAE:** Sweeney, *Campaign Trading* (1996).
- **BIST mikroyapı/volatilite:** Inci & Ozenbas, *Emerging Markets Review* 33 (2017); Aktas & Kryzanowski (2014); BIST sektörel GARCH (2024).

*Not: Bu rapor ölçüm-metodolojisi tasarımıdır; bir sonraki adımda kendi BIST verimizle Kanıt Boşlukları bölümündeki sorular test edilmeli. Yukarıdaki yabancı-piyasa kanıtları (FX, ABD, Taiwan) yöntem-transferi için referanstır; BIST'e doğrudan genellenemez — özellikle hit-rate/forward-return seviyeleri kendi verimizde doğrulanmalı.*