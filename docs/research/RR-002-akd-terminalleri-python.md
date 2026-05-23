# BIST Takas ve Aracı Kurum Dağılımı Verisi Sağlayan Türk Veri Terminalleri — Python Entegrasyonu Karşılaştırması

## TL;DR
- **Python‑native, doğrudan endpoint erişimli tek seçenek "İş Yatırım public JSON" (`/_layouts/15/Isyatirim.Website/Common/Data.aspx/HisseTekil` + `urazakgul/isyatirimhisse` PyPI wrapper'ı, kararlı sürüm v5.0.1, Python ≥3.8, MIT)**'dır; ücretsiz olmakla birlikte tarihsel takas/AKD verisi sunmaz, sadece fiyat/temel veridir. Bu, "Matriks IQ AlgoTrader (C# → SQLite bridge)" yaklaşımına en kolay Python alternatifi konumundadır ama AKD/takas bilgisi için yetersizdir.
- **AKD (Aracı Kurum Dağılımı Gün Sonu) ve takas verisi 1 Ocak 2025'ten itibaren Borsa İstanbul lisansı gerektiren ücretli veri** olduğundan, hangi terminal seçilirse seçilsin temel mali yükümlülük aynıdır: AKD ≈ ₺139/ay (2025) → ₺173/ay (2026); AKDE (eşanlı) ≈ ₺357 → ₺435/ay. Front‑end terminal ücreti üstüne eklenir.
- **<500K TL retail ölçek için en pratik Python kombinasyonu: (a) Fintables Trade (₺149/ay) + BIST AKD lisansı (~₺173/ay) görsel referans + (b) İş Yatırım public JSON ile fiyat/temel veri scrape + (c) takas snapshot'larını manuel Excel/CSV export ile günlük SQLite'a aktarma**. Matriks IQ AlgoTrader (~₺1.073/ay ekran + lisanslar; 2026'da Matriks IQ Terminal ₺1.650 + ALGO modülü ₺1.643 ≈ ₺3.700+/ay) C#→SQLite bridge yatırımına bu ölçekte değmez; Matriks AlgoTrader'ın resmi olmayan Python kütüphanesi yoktur, tüm strateji kodu C# tabanlıdır.

## Key Findings

### 1) Hukuki/lisans çerçevesi — 1 Ocak 2025 değişikliği
Fintables'ın resmi açıklaması: *"Borsa İstanbul'un aldığı karar doğrultusunda; takas verileri 1 Ocak 2025 tarihinden itibaren Borsa İstanbul tarafından ücretli ve veri yayın lisans aboneliği gerektirecek şekilde düzenlenmeye başlamıştır."* (fintables.com/arastirma/yazilar/takas-analizi/takas-ve-araci-kurum-dagilimi-nedir)

Yani 2025'ten itibaren AKD ve takas verisi her platformda ek BIST lisansıyla satılır; platform tercihi sadece **front‑end ücreti + Python uyumluluğu**nu belirler, taban veri ücreti standarttır. Bu süreç bir kullanıcı şikayetinde sertçe yansıyor (sikayetvar.com/fintables/indirim): *"2024 Kasım ayında yıllık aboneliği indirimli fiyattan satmaya başladılar. Ben de şüphelenmeyip aldım, meğerse 2025 Ocak ayından itibaren takas verilerini ayrıca ücretli olarak satacaklarmış. Tabi bunu 1 ay öncesinde yıllık aboneliği pazarlarken söylemediler ve mağdur ettiler."*

BIST tarafından belirlenen 2025 birim fiyatları (Aktif Bank "01-01-2025 Veri Lisans Ücret Tablosu", aktifbank.com.tr/uploads/20250509104629568.pdf — Matriks/İdeal için identik):
- **AKD** (Aracı Kurum Dağılımı Gün Sonu): ₺139/ay
- **AKDE** (Aracı Kurum Dağılımı + Eşanlı Taraf): ₺357/ay
- **VAKD** (VİOP Aracı Kurum Dağılımı): ₺164/ay
- **MKK Verileri** (takas saklama bakiyeleri): Ideal PC Pro üzerinden ₺65/ay (Alnus Yatırım fiyat tablosu)

2026'da AKD ₺173, AKDE ₺435 olarak güncellenmiş (Ata Online 01-01-2026 tablosu).

### 2) "Takas Verisi" vs "Para Giriş‑Çıkış Analizi" — kavramsal ayrım
Matriks IQ dokümantasyonuna göre bu iki metrik birbirinden **farklıdır**:

- **Takas Analizi (Matriks IQ Yardım, takas-analizi sayfası):** *"Senedin, kurumun takasındaki lot miktarındaki değişiminin yüzdesel oranı … Maliyet sütunu … kurumun takasında bulundurduğu hisse senetlerindeki maliyetini gösterir."* → Bu **custody snapshot** verisidir; T+2 sonunda hangi aracı kurumun MKK saklamasında ne kadar lot bulundurduğunu gösterir. Kaynak: MKK + Takasbank.
- **Para Giriş‑Çıkış Analizi (Matriks Mobil IQ tanıtım):** *"BİST endekslerine ve tüm hisselere ait alış ve satış net hacimleri ile net para giriş çıkış verilerini kurum ve saat filtreleri ile tarihsel olarak bulabilirsiniz."* → Bu **flow** verisidir; seans içi gerçekleşen al/sat işlem hacimleri, hangi kurum kaç TL net alış/satış yaptı.
- **Aracı Kurum Dağılımı (AKD):** Sembolde gerçekleşen alış/satış işlemlerinin alıcı/satıcı taraf bilgisi (kurum kimliği) ile gösterilmesi; gün sonunda yayınlanır. Net alış/satış hesaplaması bu veriden türetilebilir.
- **Fintables'ın bizzat açıkladığı önemli nüans:** *"Aracı kurum dağılımında bazen takasta kurum nezdinde pay olmadığı halde satış gözüken kurumlar yer almaktadır. … neredeyse her kurumdan emeklilik ve yatırım fonlarına pay alınabilmesidir. Bunlar aracı kurum dağılımında gözükmez, yalnızca takas tarafında görürüz."* → Yani **AKD = flow proxy, Takas = stock/holdings proxy**; ikisi farklı analitik soruları yanıtlar.

Pratik öneri: Algoritmik sinyal üretiminde **her ikisini birlikte tutmak** gerek. Sadece "Para Giriş‑Çıkış" yeterli değildir; uzun vadeli pozisyon değişimleri için Takas (custody) verisi şart.

### 3) Platform inventarı — özet bulgular

#### Fintables (fintables.com)
- **Veri:** Hisse bazlı günlük takas + Aracı Kurum Dağılımı + Yabancı Takas Analizi — hepsi mevcut, ancak **2025'ten itibaren Trade veya Pro üyeliği ÜSTÜNE ayrıca BIST lisansı satın almak gerekir**.
- **Fiyat:** Trade ₺149/ay, Fon ₺149/ay, Pro ₺699/ay; yıllık ödemede %25'e varan indirim (Eylül 2025 kampanyası: "Trade ve Fon paketleri ₺999 yerine ₺749, Pro paket ise ₺4.999 yerine ₺3.749" — her ikisi de %25 indirim). Pro yıllık 2024'te ₺3.199 (Kasım 2024 @fintables X gönderisi: *"Fintables PRO yıllık abonelik ₺4.200 yerine sadece ₺3.199!"*), liste fiyatı ₺4.200/yıl. (fintables.com/uyelik-paketleri)
- **API:** Yalnızca **kurumsal paketlerde API ile veri çekme** sunulduğu açıklanmış (a1capital.com.tr/fintables: *"Kurumsal üyelik paketlerinde API ile veri çekme imkanı sunulmaktadır"*). Retail/bireysel pakette resmi API yok; Excel export var.
- **Topluluk reverse engineering:** `barangokcekli/borsa-istanbul-temettu-api` (GitHub) — FastAPI tabanlı, sadece **temettü ve sermaye artırımı** verilerini Fintables'dan parse ediyor; takas verisini kapsamıyor. `bugraskl/fon-scrapper` Playwright ile fon listesi çekiyor.
- **ToS riski:** Fintables verisinin re‑publish edilmesi yasak; "kişisel kullanım" için scraping gri alandadır.

#### Matriks (matriksdata.com)
- **Ürünler:** Matriks Mobil IQ (mobil), Matriks Veri Terminali (klasik desktop), **Matriks IQ Terminal** (yeni nesil + AlgoTrader). Resmi store: store.matriksdata.com.
- **Fiyat (2025 Aktif Bank tablosu, broker passthrough):**
  - Matriks IQ Mobile Ekran Ücreti: **₺207/ay**
  - Matriks Veri Terminali Ekran Ücreti: **₺426/ay**
  - **Matriks IQ Terminal Ekran Ücreti: ₺1.073/ay**
  - Prime farkı: ₺90 (Mobile) / ₺278 (Terminal) — Takas Grafiği, Para Giriş Çıkış, Yabancı Takas burada
  - **Dışarıdan Emir Kabulü (DEK) modülü: ₺3.540/ay** (algoritmik strateji harici sistemden emir göndermek için gerekli)
- **2026 zamlı (Ata Online tablosu):** Matriks IQ Terminal ₺1.650/ay, ALGO modülü ₺1.643/ay, GridTradingBot ₺2.550/ay, OutOrd (DEK 2026 karşılığı) ₺5.516/ay.
- **AlgoTrader / Python entegrasyon:** *"MatriksIQ, C# ile kodlamanın yanı sıra sihirbaz ekranları ile kolayca algoritma oluşturma olanağı sağlar."* (iqyardim.matriksdata.com/algotrader/) Strateji geliştirme **yalnızca C#** (ve "C++, F#, Iron Python gibi .NET dilleri" — Matriks AlgoTrader Tanıtım PDF, docplayer.biz.tr/42187653) ile yapılır. Resmi Python wrapper yoktur. "Iron Python" desteği teknik dokümanda anılır ama pratikte topluluk örneği yoktur. **C# stratejisi içinde SQL Server'a yazma topluluk pratiğidir:** r10.net'te bir kullanıcı: *"strateji içerisinde eriştiğin verileri istediğin database'e, text dosyaya vb yazabilirsin. ben sql server … kullandım."*
- **Matriks Mobil IQ Para Giriş‑Çıkış:** Prime lisansıyla aktiftir; *"Prime gösterge paneli, yabancı takas analizi, indikatör sinyalleri, temel analiz kısayolları, kurum önerileri, para giriş-çıkış analizi, dedektör mesajları, formasyon analizi özelliklerine sahip olursunuz."* (matriksdata.com FAQ) Matriks blog ayrıca "Takas Grafiği"ni de Prime kapsamında listeliyor: *"PRM (Prime Lisansı) … Prime özellikleri arasında, Prime Gösterge Paneli, Dedektif, Takas Grafiği, Seans İçi Analiz, Sentetik Emirler, Para Giriş Çıkış Analizi sayılabilir."*
- **Forum tepkisi (ekşi sözlük):** *"matriks ıq … hedef kitlesini profesyonel traderlar olarak seçerek önemli bir pazar kaybetmiş … hem pahalı hem de fonksiyonel değil … 2 küsur bin lira matriks lisansları" / "robotun islem yapmasi icin pc acik kalmak zorunda"* (operasyonel kırılganlık uyarıları)
- **Demo:** 1 ay ücretsiz; r10.net'te bir kullanıcı *"telefon numarası ile 1 aylık demo alabiliyorsun. veriler 15 dakika gecikmeli geliyor"* diye doğruluyor.

#### İdeal Data (idealdata.com.tr)
- **Fiyat (2026, Alnus Yatırım veri ücretleri sayfası):** İdeal PC Pro: **₺710,78/ay**; İdeal Mobil/Web: **₺349,92/ay**; **İdealgo (algo modülü): ₺1.990/ay**; UserDLL ₺3.500/ay; BMK ₺600/ay.
- **Algo:** İdealGo modülünde özel sistem dili (`Sistem.GrafikVerileri` … benzeri DSL) ile yazılır; C# veya Python değildir. **Python entegrasyonu yoktur.**
- **AKD / Takas:** Lisansla mevcut (AKD ₺139, MKK ₺65 — Alnus tablosunda).
- Ekşi sözlük: *"ideal matrikse göre çok daha hızlı çalışır. donma prblemi matriks ile karşılaştırılırsa yoktur … idealgo senelik 1200 liradan 2400 liraya çıkmış. %100 zam"*

#### Foreks Bilgi İletişim (foreks.com.tr)
- Bigpara, VakıfBank TradeOnline, Osmanlı Foreks Trader, Mynet Finans, Milliyet Uzman Para ve TradeMaster için piyasa verisi **arka uç sağlayıcı**dır. Foreks doğrudan retail satışta değildir.
- Foreks tabanlı tüm front‑end'lerde "veriler Foreks Bilgi İletişim Hizmetleri A.Ş. tarafından sağlanmaktadır" disclaimer'ı görülür.
- VakıfBank TradeOnline mobil değişiklik notu: *"10 gün gecikmeli verilen Takas analizinin günlük verilmesi sağlandı"* + *"araştırma bölümünde … takas analizi, aracı kurum dağılımı"*. Yani Foreks ekosistemi takas/AKD'yi banka uygulamalarına gömüyor.

#### İş Yatırım TradeMaster
- *"Veriler Matriks Finansal Teknolojiler A.Ş. tarafından sağlanmaktadır."* (isyatirim.com.tr disclaimer'ı) — yani arka uç Matriks.
- **Python erişimi:** İş Yatırım'ın `isyatirim.com.tr/_layouts/15/Isyatirim.Website/Common/Data.aspx/HisseTekil?hisse={}&startdate={}&enddate={}.json` endpoint'i ücretsiz, kayıt gerektirmiyor ve `urazakgul/isyatirimhisse` PyPI paketi (`pip install isyatirimhisse`, sürüm v5.0.1, Python ≥3.8, MIT Lisansı) ile sarmalanmış — `fetch_stock_data`, `fetch_index_data`, `fetch_financials` fonksiyonlarını sunar. Ancak bu endpoint **fiyat/hacim/finansal tablo** verisi getirir, AKD/takas verisi getirmez. README açıkça belirtir: *"isyatirimhisse … resmi İş Yatırım Menkul Değerler A.Ş. kütüphanesi değildir … yalnızca kişisel kullanım amaçları için tasarlanmıştır."*
- **Aracı kurum analizi sayfaları** İş Yatırım web'de mevcuttur — HTML scraping ile çekilebilir; topluluk projeleri (saidsurucu/borsapy, MCP server saidsurucu/borsa-mcp) bu kaynağı kullanır. Saidsurucu projesi: "Yabancı oranı (foreign_ratio) … free_float" gibi alanları sunuyor; tarihsel AKD endpoint'i resmi olarak yok.

#### Vakıfbank TradeOnline (Foreks tabanlı)
- VakıfBank müşterilerine **Karma Düzey 1 + MKK Veri Lisansı + endeks verileri ücretsiz** sağlanmakta (vakifbank.com.tr/tr/bireysel/yatirim/yatirim-urunleri/tradeonline). MKK lisansı saklama bakiyeleri = takas verisi.
- TradeOnline mobil release notes'da *"10 gün gecikmeli verilen Takas analizinin günlük verilmesi sağlandı"* satırı, geçmişte gecikme olduğu, şimdi günlük olduğunu doğruluyor.
- **Python erişimi:** Resmi API yok. Sadece mobil/web GUI. Veri redistribüsyon yasak.
- Forumda kullanıcı yorumu (r10.net): *"vakıf bank ın ücretsiz sağladığını duydum bir videoda ama … vakıf müşterisi olmam gerekiyor … telefon uygulamasından veri kazımayı otomasyona dökemeyeceğim"* — pratik otomasyon engeli ifade edilmiş.

#### Osmanlı Aktif Trader (Osmanlı Menkul + Matriks alt yapısı)
- Mobil app'in Matriks Mobil IQ paketinin private label'ı (`com.matriksdata.osmanli.aktiftrader`).
- *"Osmanlı Analizleri > Para giriş çıkış"* + *"Takas Analizi ekranı için düzenlemeler yapıldı"* + *"Aracı Kurum İşlem Hacmi ekranı eklendi"* — yani Matriks tarafındaki tüm modüller var.
- Ücret: 250.000 TL portföy üstünde canlı veri ücretsiz; altında **Fon/BES/komisyon karşılığı** Matriks/İdeal/Foreks lisansları tanımlanıyor.
- API: Yok. Sadece GUI.

#### Deniz Yatırım AlgoLab (Python‑native, ama Aralık 2025'te kapandı)
- *"Maalesef Algolab Platformu ve API hizmeti 31.12.2025 itibarıyla kullanıma kapatılmıştır. Bu proje, AlgoLab API'si için bir Python wrapper'ıdır. algolab.py ve algolab_socket.py modülleri aracılığıyla AlgoLab API'sine erişim sağlar."* (github.com/atillayurtseven/AlgoLab README)
- REST + WebSocket API, AES şifreli token akışı, `atillayurtseven/AlgoLab` ve `BoraDurkun/Algolab-api-py` Python wrapper'ları vardı; **artık çalışmıyor**. Bu, Türk piyasasında resmi retail Python API'sinin ölümü anlamına geliyor.
- Hisse fiyat & emir gönderme apileriydi; takas/AKD verisi sunmuyordu zaten.

#### Gedik Trader, A1 Capital, Tera Yatırım, Halk Yatırım, Phillip Capital TR, Ak Yatırım, HSBC, Bizim Menkul, QNB Invest
- Hepsi Matriks veya Foreks veya İdeal tabanlı veri sağlıyor — kendi front‑end'leri var. Hiçbiri **resmi REST API** sunmuyor (AlgoLab kapanışıyla birlikte retail Python API piyasada kalmadı).
- Bu kurumlar üzerinden BIST veri lisansı (AKD, PD2 vs.) Matriks/İdeal aboneliğiyle birlikte satın alınabiliyor.
- A1 Capital, Fintables ile entegrasyon ortağı (a1capital.com.tr/fintables): Fintables Mobil + A1 hesabı emir gönderim entegrasyonu mevcut.

#### Mynet Finans (finans.mynet.com), Bigpara (bigpara.hurriyet.com.tr), Milliyet Uzman Para
- Hepsi Foreks tabanlı 15 dk gecikmeli ücretsiz veri yayınlıyor.
- **AKD/Takas ekranı yok**; sadece fiyat, hacim, basit teknik. Forum scrape örnekleri (BeautifulSoup ile oyakyatirim, mynet) yaygın ama bu kaynaklarda takas verisi yok.

### 4) Python entegrasyon olgunluk haritası

| Yaklaşım | Çalışıyor mu? | Maliyet | Notlar |
|---|---|---|---|
| Matriks IQ AlgoTrader (C#→SQLite bridge) | Evet | ₺1.073 ekran + ~₺1.500 BIST lisans + ~₺1.643 ALGO modülü ≈ ₺4.000+/ay (2026 fiyatları) | Strateji C#; SQLite yazma topluluk pratiği, resmi destek yok. PC 7×24 açık kalmalı. |
| İş Yatırım public JSON + `isyatirimhisse` v5.0.1 | Evet | ₺0 | Sadece fiyat, finansal tablo, temel oranlar — **takas YOK** |
| `saidsurucu/borsapy` / `borsa-mcp` MCP server | Evet | ₺0 | İş Yatırım API + TradingView WebSocket; foreign_ratio var, AKD detayı yok |
| AlgoLab Python wrapper | **HAYIR** | — | 31.12.2025'te kapandı |
| Fintables resmi API (Kurumsal) | Kısmen | "Kurumsal" — fiyat yayınlanmamış, talep üzerine | Retail için yok |
| Fintables endpoint reverse engineering | Gri alan | Trade ₺149 + BIST AKD ₺173 ≈ ₺322/ay | ToS riski; sadece temettü için açık community proje var (`borsa-istanbul-temettu-api`) |
| Vakıfbank / Osmanlı / Gedik mobil scraping | Pratik değil | Hesap gerekli | Mobil app reverse engineering — forumda gözlenmedi |
| Matriks Mobil IQ Prime + manuel Excel export | Evet | ₺207 + ₺90 + AKD ₺173 ≈ ₺470/ay | Otomasyon değil, günlük manuel |
| MKK e‑Veri / Pusula (kurumsal) | Sadece kurumlar | — | Aracı kurum üyeliği gerekli |
| Borsa İstanbul resmi veri dağıtım lisansı | Evet, kurumsal | borsaistanbul.com VDS_dosya.rar fiyatları | r10.net: *"borsa istanbul verileri üçüncü şahıslara dağıtılamıyor … veri dağıtım lisansı dye birşey var"* — bireysel uygun değil |

### 5) Sonuç Matrisi (Zorunlu Çıktı)

| Platform | Takas Verisi | Aracı Kurum Dağılımı | Aylık Fiyat (TL, 2025‑2026) | API/Endpoint | Otomasyon Uyumlu | Tarihsel Derinlik | Python Entegrasyon Zorluğu | ToS/Risk |
|---|---|---|---|---|---|---|---|---|
| **Fintables Trade** | Evet (BIST lisansı ile) | Evet (BIST lisansı ile) | ₺149 + AKD ₺173 + AKDE ₺435 (opsiyonel) | Sadece Kurumsal; retail için yok | Hayır (GUI) | Tarihsel: yıllar geriye, takas için 2025 sonrası lisanslı | Zor (scraping, ToS gri) | Yüksek — re‑publish yasak; retail "kişisel kullanım" gri |
| **Fintables Pro** | Evet (BIST lisansı ile) | Evet | ₺699 + BIST lisansları | Kurumsal | Hayır | Aynı | Aynı | Aynı |
| **Matriks IQ Terminal + AlgoTrader** | Evet (lisansla) | Evet | ₺1.073 ekran + AKD ₺139 + Prime ₺278 + Algo ek modüller; 2026'da ₺1.650 + ₺1.643 algo | C# AlgoTrader; "Iron Python" doküman, pratikte yok | Evet (C# strateji içinden DB yazma) | Yıllar | Çok zor (C# bridge zorunlu) | Düşük (lisanslı kullanım) |
| **Matriks Mobil IQ Prime** | Evet (Takas Grafiği) | Kısmi | ₺207 + ₺90 Prime + AKD ₺139 | Yok | Hayır | Sınırlı GUI | Çok zor | Düşük |
| **İdeal PC Pro + İdealGo** | Evet (lisansla) | Evet | ₺710 + İdealGo ₺1.990 + AKD ₺139 + MKK ₺65 | Özel DSL "Sistem." dili | Sınırlı (DSL içinde dosya yazma) | Yıllar | Çok zor (Python yok) | Düşük |
| **VakıfBank TradeOnline (Foreks)** | Evet (Karma Düzey 1 + MKK ücretsiz) | Evet (GUI) | ₺0 (banka müşterisiyse, komisyon karşılığı) | Yok | Hayır | Günlük | Çok zor (mobil only) | Yüksek (KVKK + scraping riski) |
| **Osmanlı Aktif Trader** | Evet | Evet (Para Giriş Çıkış + AKD) | Portföy ≥250K TL ücretsiz; altında ek | Yok | Hayır | Yıllar | Çok zor | Düşük |
| **Gedik Trader / A1 / Halk / Ak / Phillip / Tera / Bizim / HSBC / QNB** | Lisansa bağlı (genelde Evet) | Evet | Matriks/İdeal/Foreks pass‑through fiyatları | Yok | Hayır | Yıllar | Çok zor | Düşük |
| **İş Yatırım TradeMaster + public JSON** | **HAYIR (web GUI'de var, JSON'da yok)** | Web sayfasında var (HTML scrape) | ₺0 (canlı veri komisyon karşılığı) | Yarı‑resmi JSON (`HisseTekil`), wrapper: `urazakgul/isyatirimhisse` v5.0.1 | Evet (Python) | Yıllar (fiyat); AKD scrape edilir | Kolay (fiyat); Orta (AKD scrape) | Orta — wrapper README "kişisel kullanım" diyor |
| **Deniz Yatırım AlgoLab API** | Hayır | Hayır | — | **31.12.2025 KAPATILDI** | — | — | — | — |
| **Mynet / Bigpara / Milliyet** | Hayır | Hayır | ₺0 (15 dk gecikmeli) | HTML scrape | Evet (basit) | Yıllar | Kolay (fiyat) | Düşük |
| **Borsa İstanbul Veri Yayın Lisansı (kurumsal)** | Evet (resmi) | Evet | Lisans listesi (VDS_dosya.rar) — bireysel için uygun değil | Resmi data feed | Evet | Tüm tarihsel | Kurumsal seviye | Düşük |
| **MKK Pusula** | Evet (saklama bakiyeleri) | Evet | Sadece üyelere (aracı kurum/banka) | Var | Evet | Yıllar | Kurumsal | Üyelik şart |

### 6) Matriks AlgoTrader C#→SQLite bridge ile karşılaştırma

**Matriks yaklaşımının güçlü yanları:**
- Strateji yapısı içinde AKD, takas, derinlik verisi tek yerden gerçek zamanlı erişilebilir (`AddMemberTickData(BrokerageEnum.X)`, `AddSymbolMarketDepth(Symbol)` gibi yerleşik API'ler).
- Emir gönderimi entegre (DEK modülü ile dış sistemden gönderme de mümkün).
- Backtest + optimizasyon dahili.

**Zayıf yanları (Python perspektifi):**
- C# zorunluluğu — mevcut Python tabanlı sistem (yfinance, EVDS API, Claude API) ile köprü kurmak ek katman.
- Topluluk pratiği "C# strateji → SQL Server/SQLite → Python okuma" şeklinde, ancak resmi destek yok.
- PC 7×24 açık kalmalı (ekşi sözlük şikayetleri).
- 2026'da ₺1.650 ekran + ₺1.643 ALGO + ₺139 AKD + ₺278 Prime ≈ ₺3.700+/ay = ~₺44K/yıl. <500K TL portföyde %8.8 yıllık yük.

**Python‑native alternatif maliyet/değer karşılaştırması:**

| Senaryo | Aylık (₺) | Yıllık (₺) | Takas Otomasyon | Python Köprü |
|---|---|---|---|---|
| Matriks IQ Terminal + AlgoTrader + AKD + Prime | ~3.700 | ~44.400 | Evet (C# içinden) | C#→SQLite manuel |
| Fintables Trade + AKD + İş Yat. public JSON + manuel CSV | ~322 | ~3.864 | Yarı (günlük manuel export) | Doğrudan Python |
| Fintables Pro + AKD + AKDE + İş Yat. JSON | ~1.307 | ~15.684 | Yarı | Doğrudan Python |
| VakıfBank TradeOnline (banka müşterisi) + İş Yat. JSON | ~0 + ~10K hacim komisyon | — | Hayır (mobil only) | Doğrudan Python |
| AlgoLab Python (2025 sonu kapandı) | — | — | — | — |

## Details

### Fintables endpoint analizi
GitHub'da Fintables verisi için iki resmi olmayan proje var:
- **`barangokcekli/borsa-istanbul-temettu-api`**: FastAPI mikroservis, sadece **temettü ve sermaye artırımı** verisini Fintables HTML'den parse ediyor. README: *"Scrapes dividend and capital increase tables for a given BIST ticker (e.g. EREGL) from fintables.com. Parses and normalizes Turkish-formatted numbers."* — Takas/AKD endpoint'i yok.
- **`bugraskl/fon-scrapper`**: Playwright tabanlı, 2375+ yatırım fonunun getirilerini çekiyor. Takas verisi kapsamıyor.

Yani Fintables'ın **takas verisi için keşfedilmiş public JSON endpoint'i bulunamadı**. Trade veya Pro abonesi olup BIST AKD lisansı ekledikten sonra GUI'den manuel Excel/CSV export en pratik yol.

ToS açısından r10.net'te değerli bir forum tartışması: *"matriksten çekeceğin bilgi senin girdindir. ha matriksten takas verilerini almışsın ha twitterdan ver almışsın. ama aynı şey anlık veriler için geçerli dğeildir."* — Yani gün sonu yorumlanmış takas verisini kişisel kullanım için Python'a aktarmak, public re‑broadcast yapmadığınız sürece düşük riskli.

### Aracı kurum mobil app network analizi
Forum tartışmalarında **resmi public REST API'si olan tek terminal Deniz Yatırım AlgoLab idi ve 31.12.2025'te kapatıldı**. Diğer terminallerin (Gedik, Garanti eTrader, İş Yatırım TradeMaster, Osmanlı, VakıfBank TradeOnline) network endpoint reverse‑engineering girişimleri GitHub'da kaydedilmemiş; ToS açıkça kişisel olmayan otomasyonu yasaklıyor.

İstisna: **İş Yatırım public JSON** (`/_layouts/15/Isyatirim.Website/Common/Data.aspx/HisseTekil`) — bu kayıt gerektirmediği için "yarı public", `urazakgul/isyatirimhisse` PyPI paketi ile resmileşmiş facto standard. AKD/takas için aynı domainde sayfalar mevcut ama JSON endpoint'i değil HTML; BeautifulSoup ile parse edilebilir (`bademirci/Web-Scraping-Python` örneği).

### Matriks IQ AlgoTrader teknik detay
`matriksiq.matriksdata.com/Algo_Trader_IQ.pdf` PDF dokümanı ve `iqyardim.matriksdata.com/algotrader/gerceklesen-islemlerin-kullanimi/` sayfaları:
- C# strateji içinden `AddMemberTickData(BrokerageEnum.AHLATCI_AYX)` gibi çağrılarla **aracı kurum işlemleri canlı** alınabilir. Ancak **"Bu fonksiyondan sadece canlı verinin takibi yapılabildiği için strateji çalıştırıldığı andan itibaren gerçekleşen işlemleri bu fonksiyonla yakalayabilirsiniz. O nedenle backtest veya optimizasyonda veri gelmeyecektir."** — yani tarihsel AKD strateji içinden alınamıyor.
- Tarihsel takas için ayrı bir analiz penceresi (`Takas Analizi`, `Takas Explorer`) var ve buradan **Excel export** mümkün; strateji içinden programatik erişim sınırlı.
- "Iron Python" desteği eski tanıtım PDF'lerinde anılır ama güncel doküman ve forum pratiğinde C# domine ediyor.

### "Para Giriş Çıkış Analizi" mekaniği
Matriks Mobil IQ Prime ile gelen bu analiz, **alıcı/satıcı tarafında kurum bazında o senaryo içindeki net hacim** (aktif alım hacmi − aktif satım hacmi) hesaplar. Kaynak: AKDE (Eşanlı Taraf) verisidir; AKD'den türetilir.
- Custody snapshot (Takas) ≠ Flow (Para Giriş Çıkış). Algoritmik sinyal üretiminde:
  - **Para Giriş Çıkış** intraday/multi‑day flow momentum'u için
  - **Takas** haftalık/aylık pozisyon değişimi tespiti için
  Birlikte kullanılmaları gerek (Fintables'ın blogunda açıkladığı DOHOL örneği bu farkın pratik göstergesi).

## Recommendations

### 1 Haftalık MVP — En Pratik Seçenek
**Tavsiye: Fintables Trade (₺149/ay) + BIST AKD Gün Sonu (₺173/ay, 2026) + İş Yatırım public JSON (yfinance yedek) + manuel günlük Excel/CSV → Python ETL.**
- Toplam: ~₺322/ay (~₺3.864/yıl). <500K TL portföyde %0.77 yıllık yük.
- Fintables hesabına giriş → Aracı Kurum sayfasından gün sonu CSV export → `pandas.read_csv` ile SQLite. Cron yerine günlük manuel tetikleyici (örn. her 18:30 saatinde indir).
- Python tarafı: `isyatirimhisse` v5.0.1 (`fetch_stock_data`, `fetch_financials`) ile fiyat, EVDS ile makro, Fintables CSV ile takas → tek SQLite şemasında birleştir.
- **Eşik:** 1 ayda manuel CSV indirme 20 günden fazla zaman aldığında veya hata oranı %5'i geçtiğinde sonraki aşamaya geç.

### Orta Vadeli (1‑3 ay) — Hibrit Otomasyon
**Fintables Pro (₺699/ay) + AKD + AKDE (₺608/ay) + headless browser otomasyonu (Playwright).**
- Toplam: ~₺1.307/ay (~₺15.684/yıl). %3.1 yıllık yük (<500K TL).
- Playwright ile login → CSV download endpoint'i çağrı → SQLite. Topluluk projesi `bugraskl/fon-scrapper` aynı tekniği fon listesi için doğruluyor.
- AKDE (eşanlı) verisi gün‑içi sinyal üretimi için, AKD gün sonu pozisyon değişimi için.
- **Risk:** Fintables ToS — "kişisel kullanım" çerçevesinde kalın; veriyi 3. taraflara redistribute etmeyin, sosyal medyada gerçek‑zamanlı paylaşmayın.

### Uzun Vadeli (6+ ay) — Sağlam Ölçeklenebilirlik
Üç seçenek var:

**A) Matriks IQ Terminal + AlgoTrader C#→SQLite bridge (~₺3.700+/ay = ~₺44K/yıl)**
- Eğer strateji intraday VİOP/hisse, emir gönderimi otomatik olacaksa anlamlı.
- C# strateji → SQLite → Python analytics → Claude API decision → Matriks emir geri besleme.
- Yatırım: Geliştirme süresi 4‑8 hafta (C# öğrenme + bridge).
- **Eşik:** Yıllık ₺44K maliyetin >₺200K alpha üretmesi gerek; <500K TL portföyde %8.8'lik yıllık fonksiyonel yükü hedef getiri ile karşılaştırın.

**B) Kurumsal Fintables API talebi (fiyat müzakere)**
- Kurumsal pakette resmi REST API verilir. Retail kullanıcı için pahalı (fiyat yayınlanmıyor, talep üzerine) ama temiz çözüm.
- Eşik: Portföy 1M+ TL veya çoklu hesap yönetimi durumunda değerlendirin.

**C) Aracı kurum üyeliği üzerinden MKK Pusula erişimi**
- Sadece TSPB üyesi aracı kurum/bankalar erişebilir; retail kullanıcı için pratik değil.

### Hangi seçeneği seçmeli?
**Karar matrisi:**
- Portföy <500K, strateji günlük/haftalık takas momentum → **Fintables Trade + AKD + Python ETL (Seçenek 1)**
- Portföy 500K‑2M, intraday + gün sonu → **Fintables Pro + AKD + AKDE + Playwright (Seçenek 2)**
- Portföy 2M+ veya emir otomasyonu zorunlu → **Matriks IQ + AlgoTrader (Seçenek A)** ya da kurumsal API
- Banka müşterisi (VakıfBank) ise ücretsiz GUI verisi günlük manuel takipte yeterliyse → **VakıfBank TradeOnline + İş Yat. JSON** (otomasyon yok, hibrit insan‑destekli sistem)

### Önerilen Hibrit Kombinasyon (1 hafta MVP mimarisi)
```
[Fiyat/Finansal Veri]   ← isyatirimhisse v5.0.1 (Python, ücretsiz)
[Makro Veri]            ← EVDS API (mevcut)
[Takas Snapshot]        ← Fintables CSV export (günlük manuel)
[AKD Flow]              ← Fintables CSV export (günlük manuel)
[Yedek/Doğrulama]       ← yfinance (mevcut)
        ↓
   SQLite DB
        ↓
[Sinyal Üretimi]        ← Python pandas
        ↓
[Karar Katmanı]         ← Claude API (mevcut)
        ↓
[Emir Yürütme]          ← Manuel veya brokerin web GUI
```

## Caveats

1. **Doğrulanamayan iddialar:**
   - Vakıfbank TradeOnline'ın AKD verisini "günlük" sağladığı release notes'tan teyit edildi ancak güncel mobil app'te tarihsel derinliği test edilmedi (banka müşterisi olmak gerekiyor).
   - Matriks AlgoTrader "Iron Python" desteği eski Matriks tanıtım PDF'inde anılıyor, güncel iqyardim.matriksdata.com sayfalarında C# vurgulu. Pratik Python kullanım örneği bulunamadı.
   - Fintables Pro'nun "Borsa İstanbul lisansı alabilir" söylemi, **lisansın paket içine dahil olmadığını** ima ediyor; bu, kullanıcı şikayetleri (Şikayetvar) ile doğrulandı.
   - Fintables'ın "200K+ kullanıcı" iddiası bazı broker sayfalarında geçiyor (a1capital.com.tr/fintables) ama Fintables'tan birinci elden, tarihli ve doğrulanabilir bir kullanıcı sayısı açıklaması bulunamadı — bu nedenle rapora dahil edilmedi.

2. **Fiyat varyansı:**
   - Matriks ve İdeal fiyatları **broker pass‑through** olduğundan aynı ürün farklı broker veri tablolarında ufak sapmalar gösterebilir (Aktif Bank 2025 vs Ata Online 2026 vs Alnus 2026). BIST tarafından merkezi belirlenen AKD/AKDE/MKK fiyatları her brokerda aynıdır.
   - Fintables yıllık ödemede %25'e varan indirim oranı sabit görünüyor (Kasım 2024'te %25, Eylül 2025'te %25). Aylık ₺149 (Trade) ve ₺699 (Pro) baz alındı.

3. **ToS belirsizliği:**
   - "Kişisel kullanım için scraping" Türk hukukunda net değil. Fintables, Matriks ve aracı kurum ToS'leri "yeniden yayın yasak" diyor ama programatik okuma açıkça yasaklanmıyor. AlgoLab kapanışından (31.12.2025) sonra retail API piyasası boşaldı; bu, scraping baskısının artmasını potansiyel olarak teşvik edebilir ve platformların buna karşı önlem alması beklenebilir.

4. **Veri yapısı:**
   - "Aracı Kurum Dağılımı" = işlem flow'u (alıcı/satıcı kurum)
   - "Takas" = pozisyon stock (MKK saklamasında kim ne kadar)
   - "Para Giriş‑Çıkış" = AKDE üzerinden türetilmiş net flow
   - Bu üç metrik farklı sorulara cevap verir; algoritmik sinyalde **birlikte kullanılmalı**.

5. **AlgoLab kayıp:** Türkiye'de retail için Python‑native, takas verisi olmasa da emir gönderme + canlı fiyat API'si tamamen kaybedildi. Bu durum, Matriks AlgoTrader'a karşı bir Python rakibi şu anda yok demek; topluluk projeleri (`saidsurucu/borsapy`, `urazakgul/isyatirimhisse` v5.0.1) yarı‑resmi scraping seviyesinde kalıyor.

6. **Anlık veri uyarısı:** Tüm raporda bahsedilen fiyatlar 2025 (Aktif Bank PDF) ve 2026 (Ata Online PDF) tablolarına dayalı. Borsa İstanbul fiyat zammı yıllık % seviyesinde geliyor; Fintables Trade/Pro fiyatları aylık değişebilir. Karar öncesi resmi sayfaları (fintables.com/uyelik-paketleri, store.matriksdata.com) tekrar kontrol edin.

7. **Nihai karar:** Bu rapor ham bulgu ve analiz çerçevesi sunar; "sistem için uygunluk" yargısı tamamen kullanıcıya aittir. Portföy ölçeği, strateji frekansı (gün sonu vs intraday) ve emir otomasyonu gerekliliği üç ana karar değişkenidir.