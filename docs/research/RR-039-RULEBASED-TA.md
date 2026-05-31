# RR-039: Kural-Tabanlı Teknik Analiz Araştırması — Görsel Sezgiyi Makine-Hesaplanabilir Kurala Çevirmek (BIST, swing/long)

## 1. TL;DR (sade dil)
1. **Evet, görsel kurulumlar büyük ölçüde sayıya çevrilebilir.** Destek/direnç, kırılım+retest, sıkışma ve "çok-yükselmiş" gibi senin baktığın şeylerin hepsinin makine kuralı karşılığı var. Ama "trend çizgisi" ve "baş-omuz" gibi bazıları öznel kalır; objektifleştirilince bile gücü tartışmalı.
2. **Araç tarafı çözülmüş.** Gösterge hesabı için `pandas-ta` / `TA-Lib`, ekstremum (tepe/dip) bulmak için `scipy.signal.find_peaks`, kümeleme için `scikit-learn`, backtest için `vectorbt` (hızlı tarama) veya `backtesting.py` (basit, işlem-bazlı) yeterli. Devasa kurumsal framework gerekmez.
3. **Senin tarzının sistemsel karşılığı net:** destek/direnç = ekstremum kümeleme; "direnç kırıldı geri geldi destek gördü" = kapanış-üstü kırılım + hacim teyidi + tolerans bandında retest; konsolidasyon = Bollinger bandwidth / ATR daralması / NR7; "çok-yükselmiş kaçınma" = MA'dan % sapma + RSI + ardışık gün filtresi.
4. **TA gerçekten işliyor mu? Kısmen, koşullu.** En geniş akademik tarama Park & Irwin (2007), *Journal of Economic Surveys* 21(4):786–826: 95 modern çalışmadan 56'sı pozitif, 20'si negatif, 19'u karışık; "teknik stratejiler en azından 1990'ların başına kadar tutarlı ekonomik kâr üretti" — sonra zayıfladı. Sonuçlar **data-snooping** (binlerce kural deneyip en iyisini seçme) yanlılığıyla şişiyor; gerçek-zamanlı dışı testte çoğu çöküyor.
5. **Gelişmekte olan piyasalarda (BIST dahil) edge biraz daha güçlü görünüyor** — çünkü piyasa daha az verimli. Ama **işlem maliyeti çoğu çalışmada kârı siliyor.** Bu senin için en kritik uyarı: küçük sermaye + BIST komisyon/spread, marjinal edge'i yok edebilir.
6. **"Çok-yükselmiş kaçınma" mantıklı ama tek başına kanıtsız.** Mean-reversion (ortalamaya dönüş) literatürü "aşırı uzama düzeltilir" der ama "yalnızca yatay/range piyasada; güçlü trendde aylarca uzar." Yani bunu bir *filtre* (girmeyi engelleme) olarak kullanmak, *reversal sinyali* olarak kullanmaktan daha savunulabilir.
7. **Backtest'te en büyük tehlike sen olacaksın, kural değil:** look-ahead (geleceği sızdırma), survivorship (delist olanları atlamak), data-snooping (parametre overfit). Birincil kıstasın (per-trade expectancy + maliyet-sonrası + random-benchmark + rejim-ayrıştırma) tam da bu tuzaklara karşı doğru savunma.
8. **Önerilen yol:** Hafif gösterge kütüphanesi + kendi kurulum-mantığın + `vectorbt` ile tarama; N≤3 varyantı test et; her birini buy-and-hold ve **rastgele-giriş benchmark**'ına karşı maliyet-sonrası karşılaştır.

## 2. KONU 1 — Görsel Kurulumların Objektif/Algoritmik Tanımı

### 2.1 Destek/Direnç (S/R) seviyesi

| Yöntem | Mantık/Formül | Tipik parametre | Güçlü | Zayıf |
|---|---|---|---|---|
| **Swing high/low (fraktal)** | Bir bar, solundaki ve sağındaki *n* barın hepsinden yüksek/düşükse swing tepe/dip. Bill Williams fraktalı n=2. | n = 2–5 bar her iki yan | Basit, deterministik, look-ahead'i kolay kontrol edilir | Gürültülü; tek başına çok seviye üretir |
| **Pivot points (klasik)** | Pivot = (H+L+C)/3; R1, S1, R2, S2 türetilir | Bir önceki gün/hafta/ay verisi | Hesabı sabit, ileri-bakış yok | Mekanik; gerçek arz-talep bölgesini değil aritmetik seviyeyi verir |
| **Ekstremum kümeleme (clustering)** | find_peaks ile tepe/dipleri bul → fiyat yakınlığına göre kümele (Agglomerative / K-Means / yoğunluk). Çok kez test edilen fiyat = güçlü seviye | Birleştirme mesafesi % (ör. ATR'nin katı veya fiyatın %1–2'si); min. dokunuş ≥ 3 | "Aynı bölgeye kaç kez gelindi" mantığını yakalar — senin sezgine en yakın | Küme sayısı/eşik seçimi öznel; K-Means S/R için zayıf bulunmuş |
| **Hacim profili (volume profile)** | Fiyat eksenine göre işlem hacmini topla; yüksek-hacim düğümleri (HVN) S/R | Bin sayısı; bakış penceresi | Gerçek işlem yoğunluğunu yansıtır | BIST'te bar-içi hacim dağılımı verisi gerekir; günlük bar ile kabadır |

**Senin tarzına en uygun:** find_peaks + fiyat-yakınlığı kümeleme, "min. dokunuş sayısı" eşiğiyle. Açık-kaynak referans: `day0market/support_resistance` (AgglomerativeClustering ile pivot kümeleme).

### 2.2 Breakout (kırılım) + Retest
Kurala dökülmüş hali:
- **Kırılım teyidi:** Günlük **kapanış** direncin üstünde (sadece intraday wick değil). Gürültü payı: kapanış > direnç × (1 + tampon), tampon ≈ 0.5–1×ATR veya seviyenin %0.5–1'i.
- **Hacim onayı:** Kırılım barı hacmi ≥ son 20 bar ortalamasının ~1.2 katı (yaygın pratisyen eşiği; akademik kalibrasyon yok — folklor sınırında).
- **Retest toleransı:** Kırılımdan sonra fiyatın eski dirence (artık destek) geri gelmesi: |fiyat − seviye| ≤ tolerans (ör. 0.5×ATR), ve o bölgede tutunma (kapanış seviyenin üstünde kalır). Giriş retest tutunmasında.
- **Yanlış-kırılım (false breakout) reddi:** Kapanış tekrar bandın *içine* dönerse kurulum iptal.

Bu, senin "geçmiş direnç bölgesine fiyat geri gelip destek görmesi (S/R flip)" sezginin birebir kural karşılığıdır.

### 2.3 Konsolidasyon/Sıkışma
| Tanım | Formül/mantık | Tipik eşik |
|---|---|---|
| **Bollinger Bandwidth (BBW)** | (Üst bant − Alt bant)/Orta bant; 20-SMA, 2σ | BBW son 6 ayın en düşük diliminde; pratisyen eşiği ~%4 (likit hisse), volatil hissede 6–10% |
| **ATR daralması** | ATR(14) son N günde düşüş trendinde / tarihsel yüzdelik dilimin altında | ATR percentile < %25 |
| **NR7** | Son 7 barın en dar gerçek aralığına (range) sahip bar | Tam tanım, parametresiz |
| **Inside bar** | Bar high < önceki high ve low > önceki low | Parametresiz |
| **TTM Squeeze** | Bollinger bantları Keltner kanallarının *içine* girerse sıkışma | BB 20/2σ, Keltner 20/1.5×ATR |

"Konsolidasyon-retest" tarzın için: BBW düşük dilim VEYA NR7/inside bar → ardından kapanış-kırılımı.

### 2.4 Trend-başı / yeni trend (geç değil erken)
| Yöntem | Kural | Tipik parametre |
|---|---|---|
| **MA cross** | Kısa MA, uzun MA'yı yukarı keser | 20/50 veya "Golden Cross" 50/200 |
| **Donchian breakout** | Kapanış son N-bar en yükseğin üstünde (Turtle) | N=20 (kısa), 55 (uzun) |
| **ADX eşiği** | ADX > 25 → trend var (filtre); tek başına yön vermez | ADX(14) > 25 |
| **HH/HL yapısı** | Ardışık higher-high + higher-low (swing noktalarından) | Son 2–3 swing |

**Erken-yakalama tansiyonu:** Donchian-20 erken ama yanlış-kırılım çok; 50/200 geç ama temiz. Pratik kompozisyon: HH/HL yapısı + ADX>20–25 filtresi + Donchian-20 tetik. ADX'i yalnız *filtre* olarak kullan, yön sinyali olarak değil.

### 2.5 Parabolik / Aşırı-uzama (kaçınma)
| Ölçü | Formül | Tipik eşik |
|---|---|---|
| **MA'dan % sapma** | (Fiyat − MA)/MA | Fiyat 20-SMA'nın %X üstündeyse "uzamış"; X hisseye göre kalibre |
| **Z-score / %B** | (Fiyat − ortalama)/σ | Z > +2 veya %B > 1 (üst bandın üstü) |
| **Ardışık yükseliş günleri** | Kesintisiz up-close sayısı | ≥ 5–7 gün |
| **ATR katı (uzama)** | Son swing dibinden mesafe / ATR | > 4–6×ATR |
| **RSI aşırı-alım** | RSI(14) | > 70 (uyarı), > 80 (aşırı) |

Senin "çok-yükselmişten kaçınma" filtren = bu ölçülerden biri/birkaçı eşik aştığında *yeni alım yapma* (giriş engeli). Kritik uyarı: RSI>70 güçlü trendde haftalarca sürebilir → bunu satış/short sinyali değil, *giriş filtresi* olarak kullan.

## 3. KONU 2 — Kural-Tabanlı TA'nın Güvenilirliği (kanıt vs folklor)

### 3.1 Akademik kanıt panoraması
- **Brock, Lakonishok & LeBaron (1992), Journal of Finance 47:1731–1764:** Dow Jones 1897–1986, MA ve trading-range-break (TRB) kuralları. Bootstrap ile "güçlü destek"; getiriler random walk, AR(1), GARCH-M, EGARCH null modelleriyle tutarsız. **AMA işlem maliyeti dahil edilmedi** ve örnek-içi.
- **Sullivan, Timmermann & White (1999), Journal of Finance 54(5):1647–1691:** BLL'in 26 kuralını **7.846 kurallık** bir evrene genişletip (beş aile: filter rules, moving averages, support-and-resistance rules, channel breakouts, on-balance-volume averages) 100 yıllık Dow Jones günlük verisine uyguladılar ve White's Reality Check ile **data-snooping**'i ölçtüler. Sonuç: BLL'in örnekleminde kurallar hâlâ iyi görünüyor ama **1987 sonrası 10 yıllık örnek-dışı dönemde kârlılık düşük** → artan piyasa verimliliği yorumu. Yani "en iyi kural" çoğu zaman şanstan ayrılamıyor.
- **Lo, Mamaysky & Wang (2000), Journal of Finance 55(4):1705–1765:** Çekirdek-regresyon (kernel) ile baş-omuz, çift-dip gibi örüntüleri otomatik tanıdılar; ABD hisseleri **1962–1996 (31 yıllık örnek)**. "31 yıllık örnek boyunca, çeşitli teknik göstergeler artımlı bilgi içeriyor ve pratik değeri olabilir" (özellikle Nasdaq hisselerinde). **AMA Jegadeesh'in eleştirisi:** kârlılık hesaplanmadı, kernel yöntemi sağ-taraf (gelecek) bilgisi kullanıyor → gerçek-zamanlı uygulanamaz, ve tek bootstrap testi yalnız random-walk modeline karşı.
- **Park & Irwin (2007), Journal of Economic Surveys 21(4):786–826:** 95 "modern" çalışmadan 56'sı pozitif, 20'si negatif, 19'u karışık. Sonuç cümlesi: çoğu çalışma **data-snooping, ex-post kural seçimi, maliyet/risk tahmini sorunları** içeriyor.
- **Bulkowski (Encyclopedia of Chart Patterns):** Pratisyen istatistik kaynağı; örüntü başına "başarı/başarısızlık oranı." **Akademik değil**, hayatta-kalan örneklem ve öznel tanım sorunları taşır. Bulkowski'nin kendi çalışması bile örüntü başarısızlık oranlarının zamanla *arttığını* gösteriyor (10% yukarı-kırılım hedefini tutturamama oranı 1990'larda ~%14 → 2003–2007 boğa piyasasında ~%28).

**Ayrım:** İstatistiksel edge en çok **trend/momentum-temelli** kurallarda (MA, TRB, Donchian) bulunmuş; **görsel örüntülerde** (baş-omuz, üçgen) kanıt zayıf ve öznel-tanıma duyarlı. Senin destek-direnç-flip + breakout-retest tarzın, kanıtın *daha güçlü* olduğu trend/breakout ailesine düşüyor — iyi haber.

### 3.2 EM/BIST spesifik
- **Genel EM bulgusu:** Trading rules EM'de gelişmiş piyasalardan daha güçlü öngörü gösteriyor (düşük verimlilik). Chang/Lima/Tabak (2004, 11 EM), Ratner & Leal (1999, 10 EM): ham veride öngörü var **ama maliyet-sonrası genelde siliniyor**; yalnız Tayvan/Tayland/Meksika gibi birkaçında kalıcı.
- **BIST weak-form verimlilik:** Karışık. Runs test (BIST Sürdürülebilirlik) ve unit-root testleri "rassal yürüyüş reddedildi → weak-form değil → öngörülebilir" derken, bazı banka-hissesi otokorelasyon testleri verimli buluyor. Konsensüs yok; bu da "edge olabilir ama garanti değil" anlamına gelir.
- **BIST TRB/destek-direnç backtest:** Marmara Üniversitesi yüksek lisans tezi ISE-100'e BLL'in 223 kuralını (MA, Reversal, Filter, TRB/destek-direnç) uyguladı: **"maliyet yokken çoğu kural pozitif aşırı getiri; maliyet dahil edilince yalnız birkaçı ihmal edilebilir pozitif getiri."** Yani maliyet-sonrası edge silinir. (Tezin yazar/yıl bilgisi açık kaynaktan teyit edilemedi — belirsiz.)
- **Metghalchi, Durmaz, Cloninger & Farahbod (2021), Int. J. of Islamic and Middle Eastern Finance and Management 14(4):713–731:** FTSE Turkish small-cap & all-cap, 23 Eylül 2003 – 9 Ağustos 2019. Bulgu (alıntı): "small-cap endeksi için bazı teknik kurallar — ünlü Golden Cross dahil (50-günlük MA'nın 200-günlük MA'yı yukarı kesmesi) — tüm dönem ve her alt-dönem boyunca, **risk ve işlem maliyetleri hesaba katıldıktan sonra** buy-and-hold üzerinde net yıllık aşırı getiri (NAER) üretti." Large-cap'te sonuçlar karışık. Bu, küçük hissede edge'in daha güçlü olabileceğine dair somut Türkiye kanıtı — senin "iyi-finansal-aşağıda-kalmış" küçük-orta hisse önceliğinle uyumlu.

### 3.3 False breakout ve retest teyidi
- Pratisyen konsensüsü: yanlış-kırılım yaygın; **retest + hacim teyidi + kapanış teyidi** yanlış sinyalleri azaltır. **Ama bunu doğrulayan sağlam akademik istatistik (kantitatif yanlış-kırılım oranı + retest'in iyileştirme yüzdesi) bulunamadı** → bu, *folklor/test-edilmeli* kategorisinde. Senin backtest'inin tam da ölçmesi gereken şey: "retest filtresi expectancy'yi artırıyor mu, trade sayısını ne kadar azaltıyor?"

### 3.4 Metodolojik tuzaklar (en sık hatalar)
1. **Look-ahead bias:** Göstergeyi/seviyeyi bugünün kapanışıyla hesaplayıp aynı barda işlem varsaymak. Çözüm: sinyal t kapanışında, giriş t+1 açılışında.
2. **Survivorship bias:** Sadece bugün yaşayan hisseleri test etmek → delist/iflas edenleri atlamak getiriyi şişirir. BIST'te delist edilmiş eski hisseleri dahil et.
3. **Data-snooping / overfitting:** Çok parametre kombinasyonu deneyip en iyisini raporlamak. Çözüm: White's Reality Check / Sullivan-Timmermann-White çerçevesi, az sayıda önceden-belirlenmiş varyant (N≤3), out-of-sample/walk-forward.
4. **İşlem maliyeti ihmali:** EM literatürünün ana dersi. Ratner-Leal tek-yön ~0.15% (~0.30% round-trip) kullanmış; BIST'te komisyon+spread+vergi ile round-trip plausibly ≥0.3–0.5%. Maliyeti gerçekçi koy.

## 4. KONU 3 — Python Araç Ekosistemi

### 4.1 Teknik gösterge kütüphaneleri
| Kütüphane | Ne yapar | Olgunluk/bakım | Lisans | BIST/OHLCV uyumu | Sınırlama |
|---|---|---|---|---|---|
| **TA-Lib (ta-lib-python)** | 150+ gösterge + 60+ candlestick C hızında | Endüstri standardı; aktif (0.6.x, numpy 2 desteği) | BSD | pandas/numpy/polars Series; OHLCV native | Altta C kütüphanesi kurulumu gerekir (zahmetli); NaN davranışı farklı |
| **pandas-ta** | 130+ gösterge, Bollinger, squeeze, ADX, aroon | Orijinal (twopirllc) **bakım zayıf/durmuş**; "yıllık release, düşük fon" uyarısı | MIT | df.ta.* DataFrame extension; mükemmel | Orijinal repo riskli; topluluk forku **pandas-ta-classic** (xgboosted, ~329★, Apr 2026 aktif, 252 gösterge/pattern, numba hızlandırma) öner |
| **ta (technical-analysis-library-in-python)** | ~40 gösterge, basit | Orta; sade | MIT | pandas uyumlu | Daha az gösterge; daha yavaş |
| **finta** | Saf-pandas göstergeler | Düşük bakım | LGPL | pandas | Sınırlı, güncel değil |

**Öneri:** `pandas-ta-classic` (saf-Python, kurulumu kolay) ana; ağır iş/hız gerekirse `TA-Lib`. İkisi de mevcut pandas/parquet altyapına doğrudan oturur.

### 4.2 Örüntü/kurulum tespiti
| Araç | Ne yapar | Olgunluk | Not |
|---|---|---|---|
| **scipy.signal.find_peaks** | Yerel tepe/dip (ekstremum) bulma | scipy çekirdeği; çok olgun | S/R, swing HH/HL, kümeleme tabanı. **Senin için en kritik primitif.** BSD lisans |
| **scikit-learn (AgglomerativeClustering/KMeans)** | Ekstremumları fiyat-yakınlığına göre kümele → S/R bölgesi | Çok olgun, BSD | KMeans S/R için zayıf bulunmuş; Agglomerative daha iyi |
| **mplfinance** | OHLC/candlestick görselleştirme | Olgun, aktif, BSD | Tespit değil görselleştirme; doğrulama/gözle-kontrol için |
| **day0market/support_resistance** | Pivot + Agglomerative ile S/R seviye | Küçük repo, niş, deneysel | Hazır mantık örneği; production değil, fikir kaynağı |

**S/R, breakout-retest, konsolidasyon, parabolik-filtre tespiti için harici "chart pattern" kütüphanesi GEREKMİYOR** — find_peaks + sklearn + gösterge eşikleriyle kendi kurulum-mantığını yazmak hem daha şeffaf hem look-ahead-guard'a uygun.

### 4.3 Görsel/CV (CNN) tabanlı yaklaşım — dürüst değerlendirme
- Akademik denemeler var: **Velay & Daniel (2018), "Stock Chart Pattern recognition with Deep Learning", arXiv:1808.00418** (Lusis & Laboratoire de Recherche en Informatique) — CNN ve LSTM ile bayrak/çift-dip gibi yaygın chart örüntülerinin tanınmasını değerlendirir; candlestick chart görüntüsü line chart'tan ~%3 daha iyi sonuç vermiş. 2D-CNN/VGG16 ile fiyat-yönü tahmini çalışmaları da (Sezer-Ozbayoglu vb.) literatürde mevcut.
- **Dürüst hüküm: bireysel ölçek için ABARTI/pratik değil.** Nedenler: (1) etiketli eğitim verisi üretmek (binlerce örüntü işaretlemek) ağır; (2) "false positive çok maliyetli" — yazarların kendi itirafı; (3) hard-coded kural (find_peaks + geometri) çoğu bariz örüntüyü zaten yakalıyor ve şeffaf/denetlenebilir; (4) CNN bir kara-kutu, expectancy/look-ahead denetimini zorlaştırır; (5) ~5500 USD, 100 hisse, günlük bar ölçeğinde getiri/çaba oranı düşük. **Önerme: kullanma.** Klasik kural + find_peaks yeterli ve üstün.

### 4.4 Backtest framework'leri
| Framework | Tip | Olgunluk/bakım | Lisans | Senin işine uygunluk |
|---|---|---|---|---|
| **vectorbt** (polakowo) | Vektörize, numba/Rust | Açık-kaynak community sürümü **yalnız bakımda**; aktif geliştirme PRO'da (ücretli) | Apache-2.0 | **100+ hisse hızlı tarama + parametre sweep + per-trade istatistik (expectancy, win rate) hazır.** pandas/parquet ile mükemmel. Birincil tarama motoru olarak ideal |
| **backtesting.py** (kernc) | İşlem-bazlı (event) + vektör | Basit, popüler; geliştirme yavaşladı | depends/AGPL | Tek-strateji prototipi, net per-trade rapor; öğrenmesi kolay. **Lisansa dikkat** |
| **backtrader** | Event-driven, broker/komisyon/slippage modeli | Klasik ama **2018'den beri aktif geliştirme durmuş**; community fork backtrader2 | GPL-3.0 | Gerçekçi maliyet/emir modeli; ama yeni sistem için bakım-riski. Küçük deney için olur |
| **zipline(-reloaded)** | Event-driven, factor | Kurulum zahmetli; akademik/legacy | Apache-2.0 | Faktör/evren araştırması; senin ölçeğin için aşırı |

**Öneri:** Tarama + parametre keşfi için **vectorbt**; nihai aday(lar)ın gerçekçi maliyet/slippage ve per-trade expectancy doğrulaması için **backtesting.py** veya **backtrader**. Mevcut altyapına (pandas/parquet snapshot, look-ahead guard, custom expectancy) hepsi entegre olur — **devasa framework'e geçmek gerekmez.** Hatta sinyal üretimini kendi pandas kodunda yapıp, vectorbt'yi yalnız portföy/expectancy hesaplaması için kullanmak en temiz yol (look-ahead guard'ı kendi elinde tutarsın).

## 5. KONU 4 — Trend/Swing Kurulumlarının BIST/EM Backtest Kanıtı
- **BIST'te doğrudan TRB/destek-direnç backtesti az ve maliyet-sonrası zayıf:** Marmara ISE-100 tezi (223 kural) → maliyet-öncesi pozitif, maliyet-sonrası silinir. Çin (Zhu vd. 2015, *Physica A* 439:75–84, Shanghai/Shenzhen): TRB > MA, ikisi de maliyet-öncesi B&H'yi yener ama **maliyet dahil edilince kâr tamamen yok olur.** En kanonik 11-EM TRB çalışması Chang, Lima & Tabak (2004, *Emerging Markets Review* 5:295–316) Türkiye'yi içermez; bulgusu: ham veride öngörü var, **maliyet-sonrası anlamsız.**
- **Türkiye'de pozitif kanıt küçük hissede:** Metghalchi vd. (2021) small-cap'te Golden Cross dahil bazı kurallar maliyet+risk sonrası B&H'yi yendi. → **Swing/pozisyon + küçük-orta hisse + trend ailesi**, Türkiye'de edge'in en olası bulunduğu kesişim.
- **Swing için optimal kurulum tipi (EM):** Literatür kısa-vadeli MA varyantlarının uzun-vadeliden daha iyi öngördüğünü ama maliyetin de daha çok yediğini söyler. Senin hafta-ay ufkun maliyet/işlem-frekansı dengesinde *avantajlı* (az işlem = az maliyet).
- **"Çok-yükselmişten kaçınma" filtresi:** Mean-reversion literatürü "aşırı uzama yatay piyasada düzeltilir, güçlü trendde uzar" der. Yani parabolik filtre **giriş zamanlamasını iyileştirebilir (tepeden almayı azaltır) ama reversal sinyali olarak güvenilmez.** Momentum (uzayan devam eder) ile mean-reversion (uzayan döner) çelişkisi *rejime* bağlı; bu yüzden filtreyi backtest'te aç/kapa karşılaştırması yapılmalı. **Kantitatif "filtre eklenince expectancy +X%" kanıtı literatürde yok → test edilmeli.**

## 6. KONU 5 — SENTEZ: Sistemsel Kural Seti (N≤3 test adayı)
Hedef: iyi-finansal + aşağıda-kalmış (uzamamış) + S/R-flip + konsolidasyon-retest + parabolik-kaçınma. Tüm varyantlar: sadece-long, günlük bar, hafta-ay tutuş, sinyal t-kapanış / giriş t+1-açılış.

**Ortak ön-filtre (tüm varyantlarda):**
- Likidite: ortalama günlük TL hacmi eşiği (ince hisseyi ele).
- Parabolik-kaçınma (giriş engeli): fiyat 20-SMA'nın %X üstündeyse VEYA RSI(14)>75 VEYA son swing dibinden >5×ATR ise YENİ ALIM YOK.
- "İyi-finansal" = fundamental skor (dışarıdan; bu araştırma kapsamı dışı) ile hisse evrenini daralt.

**Varyant A — S/R-Flip Retest (senin çekirdek sezgin):**
- find_peaks ile son ~6–12 ay swing tepeleri → Agglomerative kümeleme (birleştirme ~1×ATR), min. 2–3 dokunuş = direnç bölgesi.
- Tetik: günlük kapanış direnç × (1+0.5%) üstünde + hacim ≥ 1.2× ort(20).
- Giriş: kırılım sonrası fiyat seviyeye geri gelip (|Δ|≤0.5×ATR) kapanış seviyenin üstünde tutunursa (retest onayı).
- Stop: retest dibinin / seviyenin 1–1.5×ATR altı. Çıkış: bir sonraki S/R bölgesi veya trailing (ör. 20-gün Donchian alt / chandelier).

**Varyant B — Konsolidasyon-Kırılım (squeeze breakout):**
- Konsolidasyon: BBW son 6 ay en düşük dilim VEYA NR7/inside-bar kümesi.
- Tetik: kapanış konsolidasyon üst sınırının üstünde + hacim teyidi.
- Filtre: ADX(14) yükseliyor veya >20; HH/HL yapısı bozulmamış.
- Stop: konsolidasyon alt sınırı. Çıkış: trailing veya ATR-katı hedef.

**Varyant C — Trend-başı Donchian + retest (geç-değil):**
- HH/HL yapısı + ADX>20–25 filtresi.
- Tetik: Donchian-20 üst kırılımı.
- Retest tercihi: kırılım sonrası eski Donchian üst seviyesine/20-EMA'ya geri çekilmede tutunma → giriş (chasing'i azaltır).
- Parabolik filtre özellikle burada kritik (Donchian erken-geç tansiyonunu dengeler).

**Test protokolü (birincil kıstasların):**
1. Per-trade **expectancy** = (Kazanma% × ort. kazanç) − (Kayıp% × ort. kayıp), R-cinsinden.
2. **Maliyet-sonrası:** round-trip komisyon+spread+vergi gerçekçi (≥0.3–0.5% varsay, BIST'e kalibre et).
3. **Random-benchmark:** aynı sayıda/sürede rastgele-giriş ile karşılaştır (vectorbt rastgele sinyal). Edge ancak random'ı *anlamlı* yenerse gerçek.
4. **Rejim-ayrıştırma:** 2019–2026'yı boğa/ayı/yatay ve yüksek/düşük-enflasyon (TL) alt-dönemlere böl; filtrenin (parabolik, retest) her rejimde aç/kapa etkisini ölç.
5. **Walk-forward / out-of-sample:** parametreyi bir dönemde seç, sonrakinde test et. N≤3 varyant → data-snooping'i sınırla.

**Tek "doğru" iddia etmiyorum:** Bunlar test-edilebilir makul adaylar. Önce Varyant A (sezgine en yakın, kanıt-ailesi en güçlü), sonra B, sonra C sırasıyla; her biri random-benchmark + maliyet-sonrası eşiğini geçemezse ele.

## 7. KANIT BOŞLUKLARI (literatür neyi çözemiyor → backtest'le ölç)
1. **Retest filtresinin nicel katkısı:** "Kapanış+hacim+retest teyidi expectancy'yi ne kadar artırır, kaç trade'i eler?" — akademik sayı yok. Senin testin ölçmeli.
2. **Parabolik-kaçınma filtresinin net etkisi:** Mean-reversion vs momentum çelişkisi rejime bağlı; filtrenin BIST swing'de expectancy'ye katkısı test-edilmeli (aç/kapa A/B).
3. **BIST-spesifik, maliyet-sonrası, survivorship-düzeltilmiş, 100+ hisse, 2019–2026 TRB/S/R-flip kanıtı yok.** Mevcut BIST çalışmaları indeks-bazlı veya örnek-içi; senin per-hisse, maliyet-sonrası, random-benchmarklı testin literatürdeki boşluğu kapatır.
4. **"İyi-finansal-aşağıda-kalmış" + teknik-tetik kombinasyonu:** Metghalchi small-cap kanıtı umut verici ama fundamental+teknik kombinasyonun BIST'te per-trade expectancy'si ölçülmemiş.
5. **Optimal S/R kümeleme parametreleri (birleştirme mesafesi, min. dokunuş) BIST volatilitesine kalibre edilmemiş** — ATR-bazlı adaptif eşik test edilmeli.
6. **Rejim bağımlılığı:** TL/enflasyon şoklarının (2021–2023) teknik edge'i nasıl değiştirdiği BIST için belgelenmemiş; rejim-ayrıştırma şart.

**Genel hüküm:** Görsel sezgin sistemleştirilebilir ve trend/breakout ailesi akademik olarak en savunulabilir kategoride. Ancak EM/BIST kanıtının ana dersi *maliyet-sonrası edge'in kırılgan olduğu*; bu yüzden başarı kuralın zarafetinden çok **maliyet disiplini + data-snooping'den kaçınma + rejim farkındalığında**. Backtest'ini birincil kıstaslarınla (expectancy + maliyet-sonrası + random-benchmark + rejim-ayrıştırma) kurman, tam da doğru savunma.

---
*Not: BIST'e özgü TRB/destek-direnç kanıtı sınırlı ve büyük ölçüde indeks-bazlı/örnek-içi; Marmara tezinin yazar/yıl bilgisi açık kaynaktan teyit edilemedi (belirsiz olarak işaretlendi). Pratisyen kaynaklarındaki hacim eşiği (~1.2×), BBW eşiği (~%4) gibi sayılar pazarlama/forklor kaynaklıdır; akademik kalibrasyonu yoktur ve senin backtest'inde doğrulanmalıdır. Geleceğe yönelik "patlayıcı hareket", "kurumsal botlar front-run ediyor" türü ifadeler bazı kaynaklarda spekülatif/anlatısaldır — kanıt olarak alınmamıştır.*