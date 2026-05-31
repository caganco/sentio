# Modern Borsa İstanbul (2019–2026) Davranış Rejimi: Sistematik Swing/Pozisyon Ticaret Sistemi İçin Kanıt Haritası

*Bu rapor bir kanıt-haritalama çalışmasıdır; yatırım tavsiyesi veya görüş yazısı DEĞİLDİR. Bireysel, uzun-yönlü (long-only), tek kişilik, ~5.500 USD sermayeli bir yatırımcının sistem TASARIMINI bilgilendirmek amacıyla hazırlanmıştır. Kanıt zayıf veya yoksa "yetersiz kanıt / belirsiz" denmiş, boşluklar spekülasyonla doldurulmamıştır.*

## TL;DR (Sade Dilde, 6 Madde)

- **Trend mi, dönüş (reversal) mü?** Modern BIST'te en güncel kanıtlar (verisi 2020 ve 2024'e kadar uzanan çalışmalar) hâlâ **DÖNÜŞ/ZIT-YÖNLÜ (reversal/contrarian)** davranışın baskın olduğunu gösteriyor: hızla yükselen "kazananlar" sonraki dönemde ortalamanın altında kalıyor. Yani Bildik-Gülay (2007) bulgusu GEÇERLİLİĞİNİ KORUYOR; momentuma dönüşmedi. Tek istisna: kesitsel orta-vade (9–12 ay) için eski (2008–2015) verisinde momentum bulgusu var ama modern veriyle doğrulanmadı.
- **Tek bir hissenin kendi geçmiş getirisi (zaman-serisi momentum/trend takibi)** ile kesitsel kazanan-kaybeden ayrımı FARKLI şeylerdir; literatür ağırlıklı olarak kesitseli test ediyor ve orada dönüş baskın. Saf zaman-serisi trend takibinin modern BIST'te kârlılığına dair akademik kanıt YETERSİZ.
- **Yabancı akışı öncü mü?** Evet, kanıtlar **piyasa genelinde (endeks) yabancı net alımının bilgi taşıdığını ve ileriki getirileri öngördüğünü** gösteriyor (Ulku-Ikizlerli; 2018 kriz çalışması). Ancak bu **endeks seviyesinde** geçerli; **tek tek hisse** seviyesinde net akış gelecekteki hisse getirisini öngörmüyor. Akar'ın "yabancılar zıt-yönlü" bulgusu kısmen geçerli (yabancılar yükselen piyasada geçmiş getiriye karşı negatif-besleme yapıyor) ama "bilgisiz" değiller.
- **Swing/trend pratikte çalışır mı?** Akademik backtest kanıtı sınırlı; pratisyen kanıtı bol ama kalitesi düşük. İşlem maliyeti gerçeği kritik: %5 BSMV + komisyon + spread sonrası tek işlemin "anlamlı" olması için en az ~%1,5–3 brüt getiri gerekir.
- **Bireysel patlaması (2M+ hesap):** Pandemi sonrası (Mart 2020+) sürü davranışı GÜÇLENDİ ve spekülatif balon dönemlerinde trend kısa vadede daha çok sürdü; ama bu aynı zamanda aşırı tepki/dönüş riskini de artırdı. "Akıllı para" (yabancı kurumsal) avantajı kriz dönemlerinde KORUNDU.
- **Sistem yönü:** Kanıtlar net bir "saf kesitsel momentum (en çok yükseleni al)" stratejisini DESTEKLEMİYOR. Daha savunulabilir tasarım: zaman-serisi trend filtresi (hisse kendi trendinde mi) + yabancı/kurumsal akış teyidi (endeks/rejim bazında) + aşırı uzamış kazananlardan kaçınma + sıkı maliyet eşiği. Birçok parametre kendi backtest'imizle ölçülmeli.

---

## TOPIC 1 — Momentum vs. Reversal (Modern, Yön + Vade)

**Soru:** Modern BIST'te (a) zaman-serisi momentum, (b) kesitsel momentum/reversal, (c) hangi vade neyi domine ediyor, (d) Bildik-Gülay reversal'ı hâlâ geçerli mi?

### Bulgular

**Klasik temel (eski, modern doğrulama gerekli):** Bildik & Gülay (2007), *International Review of Finance* 7(1-2):61–87, veri 1991–2000, İMKB tüm hisseler, Jegadeesh-Titman yöntemi. Bulgu: **REVERSAL** — geçmiş kaybedenler geçmiş kazananları yener; kazanan-kaybeden arası yıllık bileşik getiri farkı kaybedenler lehine ~%15, aylık ortalama fark %1,14. Aşırı tepki (overreaction) hipotezi ile uyumlu. *Bu 25 yıllık veri; birincil dayanak yapılamaz ama modern çalışmaların referansı.*

**En güçlü modern kanıt — REVERSAL hâlâ geçerli:** Ünal (2021), *Uluslararası Yönetim İktisat ve İşletme Dergisi* 17(ICAFR Özel Sayı):165–186, DOI 10.17130/ijmeb.832584. Veri **1997–2020** (COVID dahil), BIST tüm hisse evreni, beşli (quintile) sıralama, 1–60 ay oluşturma pencereleri, t-testi. Bulgu: ilk %20'lik **kazananlar portföyü sonraki dönemlerde ortalamanın belirgin altında performans gösteriyor, t-test %1 düzeyinde anlamlı** ("bütün vadelerde ilk %20'ye giren hisselerden oluşan kazananlar portföyünün, takip eden dönemlerde ortalamanın oldukça altında performans gösterdiği ve t testi değerlerinin %1 düzeyinde anlamlı olduğu görülmektedir"). Yön: REVERSAL/aşırı tepki. (Akademik, ulusal-tier dergi.)

**En yeni veri (2024'e kadar):** Ünal & Yurtoğlu (2024), *Ekonomi, Politika & Finans Araştırmaları Dergisi* 9(4):832–853, DOI 10.30784/epfad.1496100. Veri: BIST100 bileşenleri 2000–2023; bireysel hisse 31.12.1999–15.02.2024; hisse fonları 23.02.2019–23.02.2024. Bulgu: hızla yükselen (yakın-dönem kazanan) ve endekse eklenen hisseler **sonrasında negatif performans göstererek endeksi aşağı çekiyor (t-test anlamlı)** — yani aşırı tepki/dönüş mekanizması, momentum sürekliliği DEĞİL. (Not: bu resmi J/K momentum tasarımı değil, endeks-temsil/aşırı tepki çalışması; destekleyici kanıt.)

**Likidite çalışması (orta-vade reversal):** "Liquidity and equity returns in Borsa Istanbul", veri Ocak 2002–Aralık 2012, Fama-MacBeth kesitsel regresyon. Bulgu: momentum katsayısı 3- ve 6-ay ileri getiriler için **anlamlı NEGATİF** — kazananlar kaybedene dönüşüyor; yazarlar Türkiye'de "momentum etkisi"ni "reversal etkisi" olarak ele almanın daha makul olduğunu yazıyor.

**Kısa-vade reversal (öngörülebilir):** Çelik/Ülkü (2017), *Research in International Business and Finance* 42:1445–1454. BIST'te **kısa-vadeli reversal'ın istatistiksel ve ekonomik olarak anlamlı** olduğunu, piyasa durumunun (market state) birincil öngörücü olduğunu doğruluyor. (Uluslararası hakemli dergi — yüksek kalite.)

**Çelişki / orta-vade momentum lehine kanıt:** MUFAD çalışması (veri Tem 2008–Haz 2015, BIST100, Jegadeesh-Titman J/K) **9-ay oluşturma/9–12 ay tutma ve 12-ay oluşturma/6-9-12 ay tutma** portföylerinde anlamlı MOMENTUM buluyor. Buna karşın Kandır & İnan (BDDK Dergisi) 3-6-9 ay oluşturma dönemlerinde momentumun anlamlı KÂR sağlamadığını buluyor. İki çalışma farklı vade ve dönemleri kapsıyor.

### Vade Ayrımı
- **Kısa (1–4 hafta / 1 ay):** REVERSAL (Bildik-Gülay, Çelik/Ülkü).
- **Orta (3–6 ay):** Karışık ama kesitte REVERSAL'a meyilli (likidite çalışması negatif momentum; Kandır-İnan momentum yok). Ancak MUFAD 9–12 ayda momentum buluyor (BIST100, 2008–2015).
- **Uzun (15–36 ay):** REVERSAL (Bildik-Gülay, Ünal 2021).

### Modern Geçerlilik Verdiği
**Bildik-Gülay reversal'ı: STILL VALID (GEÇERLİLİĞİNİ KORUYOR).** Modern (2020 ve 2024'e uzanan) verilerde kesitsel kazananların sonradan zayıf kaldığına dair tutarlı kanıt var; momentuma DÖNÜŞMEDİ. Saf zaman-serisi (kendi geçmiş getirisi) trend takibinin modern BIST kârlılığı: **NO EVIDENCE / belirsiz** — bu konuda doğrudan akademik çalışma bulunamadı; kendi backtest'imizle ölçülmeli. Orta-vade (9–12 ay) momentum: WEAKENED/belirsiz — yalnızca 2015 öncesi BIST100 verisinde, modern doğrulama yok. **Önemli uyarı:** 2018-19'da BAŞLAYAN örneklemle temiz, dedike J/K momentum/reversal çalışması bulunamadı — en yeni çalışmalar 2020/2024'e UZANIYOR ama örneklemleri ağırlıkla eski dönemleri de kapsıyor.

---

## TOPIC 2 — Yabancı Akışı: Öncü mü, Zıt-Yönlü mü? (Modern, Yön)

**Soru:** Yabancı net alım sonrası fiyat yükseliyor mu (öncü/bilgili para)? Akar (2008) "zıt-yönlü" bulgusu modern veride geçerli mi? %65→%35 düşüş ilişkiyi değiştirdi mi? Swing-trader "yabancı alıyor" sinyalini AL-teyidi olarak kullanabilir mi?

### Bulgular

**Temel referans (yön belirleyici):** Ulku & Ikizlerli (2012), *Emerging Markets Review*, "The interaction between foreigners' trading and emerging stock returns: Evidence from Turkey", İMKB aylık yabancı akış verisi, yapısal VAR (14 yıl örneklem). Bulgular: (1) Yabancılar **yükselen piyasalarda ve makroekonomik istikrarsızlıkta geçmiş yerel getirilere karşı NEGATİF-besleme** (zıt-yönlü) ticaret yapıyor — Akar bulgusunu kısmen destekliyor. (2) **Net yabancı akışı gelecekteki PİYASA (endeks) getirisini öngörüyor, ama tekil hisse getirisini öngörmüyor.** (3) Fiyat etkileri kalıcı → yabancı ticareti BİLGİ içeriyor. Sonuç: yabancılar "bilgisiz pozitif-besleme tüccarları" değil; piyasa koşullarına göre stratejisini ayarlayan, çoğunlukla sofistike bir gruptur.

**Modern doğrulama (2018 kriz):** "Turkish currency crunch: Examining behavior across investor types", *Journal of International Financial Markets, Institutions & Money* (2023). Bulgu: **yabancı kurumların işlemleri, işlem ayında VE takip eden ayda Türk hisse getirilerini öngörüyor — başka hiçbir yatırımcı grubu için bu doğru değil.** Yabancı kurumlar geçmiş ayda daha iyi getirili şirketlere yöneliyor (momentum besleme) ve TL'deki değer kaybı sonrası alım yapıyor. Bireysel yatırımcılar zayıf negatif-besleme eğiliminde ve düşük getirili. Yabancı kurum akışları endeks getirisiyle pozitif, diğer grupların akışıyla negatif korelasyonlu. → Yabancı kurumlar 2018 krizinde ÜSTÜN BİLGİYE sahipti.

**Yapısal değişim:** Yabancı takas oranı 2011'deki ~%65 zirvesinden (26 Temmuz 2007'de adet bazında %60,03 zirve), modern dipe geriledi. Ekonomim'in haberine göre (Şebnem Turhan, "Borsada yabancı takası dip seviyede"): "yabancıların hisse senedi piyasasındaki takas adedi oranı yüzde 16,74 ile tarihi en düşük seviyeye geriledi. Yabancıların endeksteki payı da... yüzde 37,93 seviyesine indi." Borsa İstanbul verilerine göre yabancılar 2024'te tam **3 milyar 1 milyon 762 bin 889 USD net satış** yaptı (302,1 mlr USD alım / 305,1 mlr USD satım) — üst üste 7. net-satış yılı. Buna karşılık yerli ağırlığı yükseldi: Bloomberg HT'ye göre (14.04.2023) "2023 Mart sonu itibariyle pay senedi portföy dağılımında yurtiçi bireysel yatırımcıların yüzde 37 pay ile ilk sırada" (2019'da bu pay %19 idi; yurtiçi kurumlar %23 ile ikinci). Yani yabancılar artık marjinal fiyat-belirleyici olma ağırlığını kaybetti.

### Çelişki
Akar (2008) "yabancılar zıt-yönlü" vs. çeşitli nedensellik çalışmaları "yabancı işlemden hisse getirisine tek-yönlü nedensellik" (yabancı yönlendirici). Bu çelişki yön/yöntem farkından kaynaklanıyor: Ulku-Ikizlerli bunu uzlaştırıyor — yabancılar geçmiş getiriye karşı zıt-yönlü (negatif besleme) DAVRANSA da, akışları GELECEK endeks getirisini pozitif öngörüyor (bilgili). İki bulgu çelişmiyor; farklı şeyleri ölçüyor.

### Modern Geçerlilik Verdiği
- Endeks seviyesinde "yabancı net alımı öncüdür/bilgilidir": **STILL VALID** (2018 kriz verisiyle güçlendi).
- Akar "zıt-yönlü besleme": **STILL VALID ama yanlış yorumlanmamalı** — zıt-yönlü olmaları onları bilgisiz yapmıyor.
- Tekil hisse için "yabancı alıyor → fiyat yükselecek" öncü sinyali: **WEAKENED / belirsiz** — Ulku-Ikizlerli tekil hisse öngörüsü bulamadı; ayrıca yabancı payı tarihi dipte, marjinal etki azaldı. Pratik sonuç: yabancı akışı endeks/rejim teyidi olarak kullanılabilir, ama tek hisse AL-sinyali olarak güvenilmez.

---

## TOPIC 3 — Swing/Trend Çalışırlığı (Modern, Pratik + Maliyet)

**Soru:** Donchian/MA kesişim/kırılım stratejileri 2019–2026 BIST'te kâr üretti mi? Optimal tutma vadesi? İşlem maliyeti gerçeği?

### Bulgular

**Backtest kanıtı:** Donchian kanalı / hareketli ortalama kesişim stratejilerinin 2019–2026 BIST'te kârlılığına dair **hakemli akademik backtest kanıtı YETERSİZ/bulunamadı.** Pratisyen kaynaklar (Medium, aracı kurum blogları, eğitim siteleri) bol ama metodolojik kalitesi düşük — örneklem, işlem maliyeti, çoklu-test düzeltmesi içermiyor; çoğu eğitim/pazarlama amaçlı. Bir pratisyen örneği (THYAO, tek hisse, küçük örneklem) 10 EMA/50 MA çiftinin 5 EMA/20 MA'dan daha az işlem ve daha yüksek getiri verdiğini gösteriyor — ancak bu istatistiksel kanıt DEĞİL, tek-örnek illüstrasyonu.

**İşlem maliyeti gerçeği (BIST-spesifik model):**
- **BSMV:** %5 — ancak **komisyon tutarı üzerinden** alınır, işlem hacmi üzerinden değil (6802 sayılı Gider Vergileri Kanunu; aracı kurum komisyon gelirine uygulanır). Örnek (Yatirimadeger): 200.000 TL işlemde onbinde 20 komisyon ödeyen yatırımcı BSMV hariç 400 TL, BSMV dahil 420 TL öder — yani BSMV efektif maliyeti komisyonun yalnızca %5'i kadar ek yük getirir.
- **Komisyon:** Aracı kuruma göre değişir. Garanti BBVA Yatırım tarifesi (8 Haziran 2024): "yapılan her işlemde (alım/satım) kurum azami %0,105 (binde 1,05) oranında komisyon tahsilatı yapma hakkına sahiptir" (+%5 BSMV hariç). Piyasada Midas/Trive gibi komisyonsuz veya Türkiye Finans onbinde 2 kampanya oranları da mevcut. Minimum işlem ücretleri (ör. 35 kuruş + BSMV) küçük işlemlerde bağlayıcı olabilir.
- **Spread (alış-satış farkı):** Likit BIST30 hisselerinde dar; küçük/likiditesiz hisselerde geniş — gerçek maliyetin önemli kısmı.
- **Stopaj:** Yerli bireysel için BIST hisse alım-satım kazancında stopaj geçmişte %0 uygulanmıştı; güncel oran ve istisnalar değişebilir — **2026 için doğrulanmalı (belirsiz).**

**"Anlamlı getiri" eşiği:** Round-trip (alım+satım) komisyon ~binde 2–4 + BSMV (komisyonun %5'i) + spread göz önüne alındığında, tek bir swing işleminin maliyeti aşıp anlamlı olması için kabaca **en az ~%1,5–3 brüt fiyat hareketi** gerekir (likit hisse, düşük komisyon senaryosu). Likiditesiz hisse veya yüksek komisyonda eşik yükselir. Bu, çok-kısa-vadeli/yüksek-frekanslı işlemleri ~5.500 USD küçük sermaye için maliyet açısından dezavantajlı kılar.

**Optimal tutma vadesi:** Literatürdeki vade ayrımı (kısa=reversal, orta-uzun=karışık) ile maliyet eşiği birlikte değerlendirildiğinde, sinyal-gürültü oranının en iyi olduğu aralık muhtemelen **birkaç hafta–birkaç ay** bandıdır; ama bu BIST-spesifik backtest ile DOĞRULANMALI. Akademik kesin kanıt YETERSİZ.

### Modern Geçerlilik Verdiği
- Kırılım/MA stratejileri kârlılığı: **NO EVIDENCE (akademik)** / pratisyen kanıtı düşük kalite. Kendi backtest'imiz zorunlu.
- Maliyet modeli: BSMV %5'in komisyon üzerinden alınması doğrulandı; net per-trade eşik ~%1,5–3 (senaryoya bağlı).

---

## TOPIC 4 — Bireysel Yatırımcı Patlamasının Yapısal Etkisi

**Soru:** 2M+ hesap (post-2020) herding/momentumu güçlendirdi mi yoksa gürültü/reversal'ı mı artırdı? Akıllı para avantajı arttı mı azaldı mı? Swing-trader için fırsat mı risk mi?

### Bulgular

**Yatırımcı büyümesi (ölçek):** BIST aktif yatırımcı sayısı 2015'te 1.064.754'ten 2021'de 2.002.873'e neredeyse iki katına çıktı (Merkezi Kayıt Kuruluşu). MKK'nın resmi açıklamasına göre ("Pay Piyasası Yatırımcı Sayısı 2 Milyonu Aştı"): 2020 başından itibaren pay senedi yatırımcı sayısı 786.128 kişi arttı; 15 Ocak 2021'de 2.002.873 tekil yatırımcının 1.990.756'sı yerli, 1.984.142'si yerli bireyseldi. MKK'nın 2025 yıl-sonu panoramasına göre (Bloomberg HT / AA): toplam kayıtlı yatırımcı 37,94 milyon, bakiyeli yatırımcı 10,64 milyon, pay senetlerinde portföy değeri 17,33 trln TL ve yatırımcı sayısı 6,51 milyon.

**Sürü davranışı (herding) — pandemi sonrası güçlendi:** İMKB günlük veri 2 Mart 2015–8 Eylül 2022, OLS + kırılma noktalı EKK + kantil regresyon kullanan akademik çalışma. Bulgu: **Mart 2020 ÖNCESİ sürü davranışı/boğa trendi YOK; Mart 2020 SONRASI belirgin boğa trendi ve sürü davranışı var — tüm piyasa koşulları ve getiri-dağılım kantillerinde.** Sürü davranışı, zayıf makro temellere ve COVID etkisine rağmen spekülatif balonu önemli ölçüde etkiledi.

**COVID dönemi herding (destekleyici):** DergiPark çalışmaları (Yalçın & Aybars 2022; Özkan & Yavuzaslan 2022): pandemi öncesi sürü yokken, pandemi döneminde BIST30, BIST100 ve banka/gıda/ulaştırma/teknoloji sektörlerinde sürü davranışı görüldü.

**Aşırı güven (overconfidence):** PMC'de yayımlanan çalışma (veri 2015–2021, BIST, yapay sinir ağı + nonlineer Granger nedensellik), 2018–2019 kriz ve COVID dönemini kapsıyor. Pozitif getiri rejimlerinde aşırı-güven/aşırı-işlem davranışı tespit edildi — bu, momentum/herding'i besleyen davranışsal mekanizma.

**Akıllı para avantajı:** Topic 2'deki 2018 kriz çalışması, yabancı kurumların kriz döneminde üstün bilgiye sahip kaldığını ve getirileri öngördüğünü gösteriyor — bireysel yatırımcılar düşük getirili. İçeriden öğrenenler çalışması (2015–2020, KAP bildirimleri) içeridekilerin piyasayı etkin zamanladığını (düşük performanslı hisse alıp yüksek performanslıyı sattığını) gösteriyor. → Bilgili azınlığın avantajı KORUNDU/sürüyor.

### Modern Geçerlilik Verdiği
- Herding/sürü davranışı post-2020 GÜÇLENDİ: **STILL VALID** (2015–2022 verisiyle güçlü kanıt). Bu trendlerin (özellikle balon dönemlerinde) kısa vadede daha çok sürmesini destekler — ama aynı zamanda aşırı tepki/sert dönüş riskini artırır.
- Akıllı para edge'i: **STILL VALID** (kriz dönemlerinde arttı/korundu).
- Swing-trader için: hem **fırsat** (güçlenen sürü → daha izlenebilir trend dalgaları) hem **risk** (gürültü, balon-çöküş, sert reversal). Net etki belirsiz; risk yönetimi (stop, pozisyon büyüklüğü) belirleyici.

---

## SENTEZ — Sistem Yönü İçin Çıkarım

Dört konunun birleşik sonucu:

1. **Trend mi, mean-reversion mu?** Kesitsel "en çok yükseleni al" (saf cross-sectional momentum) BIST'te kanıtlarca DESTEKLENMİYOR — modern veride bile kazananlar sonradan zayıf kalıyor (reversal baskın). Ancak bu, **trend takibinin işe yaramayacağı anlamına gelmez**: kesitsel reversal ile zaman-serisi trend takibi farklı şeylerdir. Savunulabilir yön: (a) zaman-serisi trend filtresi (hisse kendi yükselen trendinde mi — MA üstü, yükselen dip-zirve), (b) **aşırı uzamış/parabolik kazananlardan kaçınma** (reversal riski), (c) düşük-tabandan yeni trend başlangıçlarını yakalama. "Sürekli en çok artan 10 hisseyi al" YANLIŞ yön olur.

2. **Yabancıyı takip et mi, etme mi?** Endeks/rejim seviyesinde yabancı net akışı bilgili ve öncü → **rejim filtresi olarak EVET** (yabancı net alım rejiminde long-bias artır). Tekil hisse AL-sinyali olarak yabancı takas oranı → **GÜVENİLMEZ** (tek hisse öngörüsü zayıf, yabancı payı tarihi dipte). Yerli bireysel/kurumsal akış artık daha belirleyici.

3. **Hangi vade?** Kısa-vade (günler–1 ay) reversal baskın ve maliyet eşiğini aşmak zor → **çok kısa vadeden kaçın.** Birkaç hafta–birkaç ay bandı sinyal-gürültü açısından daha makul; orta-vade (3–6 ay) karışık. Kesin optimal vade kendi backtest'imizle ölçülmeli.

4. **Maliyet eşiği:** Her işlem ~%1,5–3 brüt hareket eşiğini aşmalı; ~5.500 USD küçük sermayede işlem sıklığını düşük tut, likit hisselerde kal (spread düşük), düşük-komisyon aracı kurum seç. Yüksek-frekans/scalping bu sermaye+maliyet yapısında dezavantajlı.

**Bütünleşik tasarım hipotezi (test edilecek):** Zaman-serisi trend filtresi + yabancı/kurumsal akış REJİM teyidi + aşırı-tepki (parabolik kazanan) kaçınma filtresi + birkaç hafta-ay tutma + sıkı maliyet/likidite eşiği + sabit risk yönetimi. Bu bir hipotezdir; literatür yönü gösterir, parametreleri vermez.

---

## ÖNERİLER (Aşamalı, Somut Adımlar ve Karar Eşikleri)

**Aşama 0 — Tasarım yönünü kilitle (literatür temelli):**
- Sistemi "saf kesitsel momentum" değil, **zaman-serisi trend takibi + aşırı-tepki kaçınma + akış-rejim teyidi** üzerine kur. Eşik: Eğer kendi backtest'in kesitsel kazananların 1–6 ayda anlamlı pozitif getiri verdiğini gösterirse (literatürün tersi), yönü yeniden değerlendir.

**Aşama 1 — Evren ve maliyet disiplini:**
- İşlem evrenini **likit hisselerle** (ör. BIST30/BIST50 ve yüksek hacimli BIST100 üyeleri) sınırla — spread ve slippage maliyetini düşürmek için. Açığa satış yasağının BIST50'de 2 Ocak 2025'te kalkması likiditeyi destekleyen bir gelişme.
- **En düşük komisyonlu** aracı kurumu seç; round-trip toplam maliyetini (komisyon×2 + BSMV + tahmini spread) her işlem öncesi hesapla. Karar eşiği: beklenen hedef hareket maliyetin **en az 2 katı** (yani ~%3+) değilse işleme girme.

**Aşama 2 — Sinyal ve rejim filtreleri:**
- **Trend filtresi:** Hisse yükselen orta-vadeli MA üzerinde + yükselen dip-zirve yapısında. Parabolik/aşırı-uzamış (kısa sürede aşırı sapan) hisseleri AL listesinden çıkar (reversal riski).
- **Rejim filtresi:** Genel piyasada/endekste yabancı + yerli kurumsal net akış pozitif ve XU100 kendi trend filtresinin üzerindeyse long-bias artır; aksi halde nakitte bekle veya pozisyon küçült.

**Aşama 3 — Kendi backtest'in (zorunlu, çünkü literatür parametre vermiyor):**
- 2019–2026 BIST verisinde trend/kırılım kurallarını **işlem maliyeti dahil** test et. Ölç: yıllık getiri, Sharpe, maksimum düşüş, işlem başına ortalama getiri vs. maliyet eşiği.
- Karar eşikleri: (i) İşlem başına ortalama net getiri maliyet eşiğinin altındaysa → vadeyi uzat / işlem sıklığını azalt. (ii) Maksimum düşüş sermayenin kabul edilemez kısmını (ör. >%25) siliyorsa → pozisyon büyüklüğü/stop kurallarını sıkılaştır. (iii) Strateji yalnızca tek bir balon döneminde (ör. 2021–22) kâr ediyorsa → rejim-bağımlı olduğunu kabul et, rejim filtresini zorunlu kıl.

**Aşama 4 — Risk yönetimi (her durumda):**
- Sabit yüzde-risk pozisyon büyüklüğü, her pozisyonda stop-loss, ve toplam eşzamanlı pozisyon limiti. ~5.500 USD'de aşırı parçalama (çok sayıda küçük pozisyon) minimum komisyon nedeniyle maliyetli — pozisyon sayısını sınırla.

---

## KANIT BOŞLUKLARI (Kendi Backtest'imizle Ölçülmeli)

1. **Saf zaman-serisi trend takibinin (kendi geçmiş getiri) modern BIST kârlılığı** — doğrudan akademik kanıt YOK. (Kesitsel reversal var ama bu farklı.)
2. **Donchian/MA-kesişim/kırılım stratejilerinin 2019–2026 BIST kâr/kayıp, Sharpe, maksimum düşüş** — hakemli backtest yok; kendi testimiz zorunlu.
3. **Optimal tutma vadesi (sinyal-gürültü en iyi nokta)** — net 2019–2026 vade-ayrım kanıtı yetersiz.
4. **Kesitsel momentum/reversal'ın 2019–2026'ya BAŞLAYAN örneklemle J/K testi** — mevcut en yeni çalışmalar 2020/2024'e UZANIYOR ama 2018-19'da BAŞLAMIYOR; temiz modern-rejim testi yok.
5. **Tekil hisse yabancı takas oranı değişiminin gelecek getiriyi öngörme gücü (2019–2026)** — güncel mikro-yapı kanıtı zayıf.
6. **Enflasyon muhasebesi (TMS 29, 2023 sonu) sonrası fiyat-bilanço ilişkisinin değişimi** — hisse fiyat davranışına etkisine dair doğrudan kanıt YETERSİZ; sadece özkaynak/finansal tablo etkisi çalışılmış.
7. **2026 güncel stopaj/vergi rejimi** — yerli bireysel hisse kazancı stopaj oranı doğrulanmalı.

---

## CAVEATS (Kalite ve Sınırlamalar)

- **Akademik vs. pratisyen ayrımı:** Yüksek kaliteli uluslararası hakemli kaynaklar — Bildik-Gülay (*International Review of Finance*), Ulku-Ikizlerli (*Emerging Markets Review*), 2018 kriz çalışması (*JIFMIM* 2023), Çelik-Ülkü (*RIBAF* 2017). Orta kalite ulusal-tier akademik (DergiPark/BDDK/PMC): Ünal 2021/2024, herding ve overconfidence çalışmaları — geçerli ama daha düşük güvende. Düşük kalite pratisyen (aracı kurum/medya/blog): yön gösterici değil, illüstrasyon; metodolojik kontrol yok.
- **Vade/dönem heterojenliği:** Çelişkiler büyük ölçüde farklı örneklem dönemleri ve yöntemlerden (J/K portföy vs. Fama-MacBeth vs. endeks-temsil) kaynaklanıyor; bu rapor çelişkileri gizlemeden iki tarafı da sundu.
- **Magnitude sınırı:** Modern reversal çalışmaları (Ünal 2021/2024) bulgularını çoğunlukla **anlamlılık düzeyi (%1)** olarak veriyor, tek bir aylık kazanan-kaybeden spread'i (Bildik-Gülay'ın %1,14/ay gibi) net rakamla vermiyor.
- **Yapısal değişim aktif:** Yabancı payı tarihi dipte, yerli bireysel/kurumsal ağırlık yükseliyor, yüksek-enflasyon rejimi (TÜFE ~%32–75 bandı) ve TMS 29 (2023 sonu) bilanço yorumunu değiştirdi. Bu değişimlerin fiyat davranışına net etkisi henüz tam ölçülmedi; eski bulgular dikkatle ve modern doğrulama şartıyla kullanılmalı.
- **Bu rapor sistem yönünü bilgilendirir, parametre vermez.** Tüm spesifik kurallar (MA periyotları, stop seviyeleri, vade) kendi 2019–2026 backtest'inizle ampirik olarak belirlenmelidir. Yatırım tavsiyesi değildir.