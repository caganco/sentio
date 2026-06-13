# Edge Epistemolojisi ve Negatif Bilgi Sentezi

## Amaç ve Kapsam

Bu doküman, uzun-only kısıtının mutlak olmadığı, kaldıracın risk-disiplini altında sınırlı tutulduğu, sıfır-komisyonlu tek-kişilik bir sistematik alfa-araştırma programında iki şeyi sabitler:

1. **Edge epistemolojisi** — bir aday-sinyalin "gerçek edge" mi yoksa "aşırı-uydurma (overfit)" mı olduğu nasıl ayırt edilir; gelecekteki her hipotezin geçmesi gereken eşik nedir.
2. **Negatif bilginin sentezi** — tüketilmiş araştırma eksenlerinin envanteri ve bu envanterin program-düzeyindeki çıkarımı; tüketilmiş bir ekzenin neden *pozitif* bilgi taşıdığı.

Doküman bir referanstır: yöntemi anlatır, sonucu reklam etmez. Tüm iddialar ölçüm-temellidir; sezgiler hipoteze çevrilir, otorite olarak kabul edilmez.

---

## Bölüm I — Edge Epistemolojisi: Gerçek Edge ile Overfit Ayrımı

### I.1 Sonuç okunamaz; süreç okunur

Bir backtest'in yüksek Sharpe'ı, düşük p-değeri veya temiz equity-curve'ü tek başına edge'in kanıtı değildir. Yeterince çok aday-spesifikasyon denendiğinde, saf-gürültüden bu metriklerin tümünü tatmin eden bir konfigürasyon **kaçınılmaz olarak** bulunur. Dolayısıyla edge ile overfit arasındaki ayrım sonucun *kendisinde* değil, sonucu üreten *sürecte* yatar. Aynı equity-curve, dürüst bir ön-kayıttan da, gizli bir arama-uzayından da çıkmış olabilir; ikisi okunduğunda aynı görünür. Ayrımı kuran şey, çıktının değil, prosedürün denetlenmesidir.

### I.2 Üç ayırt-edici

Bir sinyalin gerçek-edge prior'unu yükselten üç bağımsız koşul:

**1. Tahmin, uyum değil (prediction vs. accommodation).**
Edge, *gözlenmeden önce* ifade edilmiş bir önermenin sonradan doğrulanmasıdır. Veriye bakıp ardından "şu pencerede şu eşikle çalışıyor" demek uyumdur, tahmin değil. Bu yüzden hipotez ve kabul-eşiği (keep-bar) ölçümden önce dondurulur; ölçüm görüldükten sonra eşiğin gevşetilmesi veya işaretin (sign) ters çevrilmesi, uyumu tahmin kılığına sokmaktır ve yasaktır.

**2. Mekanizma prior-yükselticidir, mantıksal-gereklilik değil.**
Geçerli bir mekanizma, "şu ekonomik aktör şu nedenle şöyle davranmak zorunda" iddiası **değildir** — böyle bir zorunluluk neredeyse hiçbir zaman kurulamaz ve kurulduğu iddia edildiğinde post-hoc rasyonalizasyon olma riski yüksektir. Geçerli mekanizma, *gözlemden bağımsız* olarak edge'in var-olma olasılığını yükselten bir önsel hikâyedir. Mekanizma sonucu açıklamak için sonradan inşa edildiyse, prior yükseltmez — sadece anlatıyı süsler.

**3. Tanımlanabilir karşı-taraf (counterparty).**
Her sürdürülebilir edge, parayı *kimden* aldığını yapısal olarak adlandırabilmelidir: hangi aktör, hangi kısıt veya hangi tercih nedeniyle bu fiyatı bırakmaya razıdır? Karşı-tarafı adlandırılamayan bir edge, ya henüz anlaşılmamıştır ya da yoktur. Pazar, herkesin aynı bilgiyle aynı tarafta durduğu bir yerde kimseye sürekli getiri bırakmaz.

### I.3 İstatistiksel iskele

Üç ayırt-edici niteldir; aşağıdaki araçlar onları nicel-eşiklere bağlar.

- **Çoklu-test düzeltmesi (Harvey, Liu & Zhu, 2016).** Çok sayıda faktör denendiğinde, geleneksel `t > 2` eşiği yanlış-pozitif üretir. Etkin eşik denenen hipotez sayısıyla birlikte yükselir; pratik kabul çıtası `t > 3` mertebesindedir. Deneme-sayısı kayıt altında tutulmadığında, herhangi bir tekil `t` değeri yorumlanamaz.
- **Yayın-sonrası bozunma (McLean & Pontiff, 2016).** Akademik olarak yayımlanmış anomaliler, yayından sonra getirilerinin önemli bir kısmını kaybeder — edge bilindikçe arbitraj onu aşındırır. Çıkarım: literatürde iyi-belgelenmiş bir faktörün *bugünkü* prior'u, orijinal çalışmadaki kadar yüksek değildir. "Bilinen faktör" ile "yaşayan edge" aynı şey değildir.
- **Deflated Sharpe Ratio.** Gözlenen Sharpe, denenen-konfigürasyon sayısına göre deflate edilir; deneme-sayısı bağlayıcı bir parametredir, opsiyonel değil.
- **Newey-West HAC.** Ardışık-bağımlı ve heteroskedastik getiri serilerinde standart-hata düzeltmesi; kabul çıtası HAC-düzeltilmiş `t ≥ 2` (çoklu-test bağlamında yukarı taşınır).

#### Çoklu-Test Cezası Ne Zaman Taşıyıcıdır

Deflated Sharpe Ratio gibi bir deflasyon düzeltmesi, raporlanan sonucun çok-sayıda deneme arasından en-iyi olarak seçildiği gerçeğini hesaba katmak için stratejinin anlamlılık-eşiğini yukarı taşır. Probabilistic Sharpe Ratio'nun sabit kıyas-noktasını, N bağımsız yeteneksiz (unskilled) deneme arasından maksimum olarak gözlenmesi-beklenen Sharpe oranıyla değiştirir; ayrıca örneklem-uzunluğu, çarpıklık (skewness) ve basıklık (kurtosis) için düzeltir. Tanımlayıcı özelliği deneme-sayısı terimidir: deneme sayısı büyüdükçe, bir adayın aşması gereken çıta yükselir.

Bu düzeltmenin taşıyıcı olup olmadığı, tümüyle doğrulayıcı (confirmatory) testin nasıl kurulduğuna bağlıdır.

Konjuge eğitim/test (train/test) tasarımı altında — bir evrende iteratif geliştirme, ardından kesinlikle-bağımsız bir evrende tek, dondurulmuş, ön-taahhütlü (pre-committed) bir değerlendirme — doğrulayıcı ayak tam olarak tek bir test gözlemler. O ayaktaki etkin deneme-sayısı, kuruluş gereği birdir; bu da deneme-sayısı deflasyon terimini etkisiz (inert) kılar: geliştirme evresinden çıkan sahte (spurious) bir kazanan, bağımsız testte basitçe başarısız olur. Yapısal evren-dışı (out-of-sample) kapı parametrik-değildir (non-parametric) — hiçbir dağılım-varsayımı yapmaz, etkin deneme-sayısının bir tahminini gerektirmez ve hiçbir büyük-deneme asimptotiği çağırmaz. Bu yüzden, uygulanabildiği her yerde parametrik düzeltmeye baskındır. Bu tasarımda deflasyon düzeltmesi onarılacak bir zayıflık değildir; gereksizdir (redundant), çünkü protokol çoklu-test problemini parametrik olarak değil yapısal olarak ortadan kaldırır.

Düzeltme, tümleyici (complementary) durumda doğru-araç hâline gelir: evren-dışı bir ayrık-küme (holdout) karşılanabilir olmadığında. Veri-kıt (data-scarce) bir rejimde, bağımsız bir test-ayrımı oymak, o ayrımı güç-yoksunu (underpowered) bırakabilir — gerçek bir etkiyi gürültüden ayırmak için fazla-az kesitsel isim ya da fazla-kısa bir pencere. Sorunun özünde tüm-evren olduğu, ya da ayırmanın karar-vermek için gereken gücün ta kendisini yok ettiği yerde, çoklu-test problemi yapısal olarak ortadan kaldırılamaz ve parametrik bir düzeltme gereklidir. Orada deflasyon düzeltmesi — ya da eşdeğer bir t-istatistiği kesintisi (haircut) — gerçek iş görür.

Bu niş, kullanımını yöneten özel bir ironi taşır. Parametrik bir düzeltmeyi zorlayan veri-rejimleri — kısa, kalın-kuyruklu (fat-tailed), rejim-kayan seriler — tam da düzeltmenin kendi varsayımlarının en-zayıf olduğu rejimlerdir. Dört uyarı izler:

- Beklenen-maksimum terimi bir büyük-deneme asimptotiğidir. Kasıtlı olarak küçük-deneme bir rejimde, doğru olduğu aralığın dışında uygulanır; asimptotik yaklaşımın yerine tam sıra-istatistiği (order statistic) kullanılmalıdır.
- Deneme-sayısı gerçekleşmiş bir arama-sayısıdır, serbest bir parametre değil. Bir eşik, deneme-sayısını şişirerek tatmin edilemez, çünkü onu şişirmek fiilen daha-geniş bir arama yürütmek demektir — küçük-deneme disiplininin sınırlamak için var-olduğu aynı veri-madenciliği yüzeyi. Sayı, gerçekten neyin arandığını yansıtmalıdır.
- Düzeltme yalnızca kayıt-altındaki denemeleri hesaba katar. Kayıtsız keşfedilip atılan gayrı-resmi varyantlar gerçek seçilim-yanlılığını (selection bias) yine de şişirir ve sonradan geri-kazanılamaz; bu da aramanın disiplinli kaydını, düzeltmenin bir anlam ifade etmesi için bir ön-koşul yapar.
- Deneme Sharpe oranlarının tek bir dağılımdan çekildiği varsayımı, tek bir strateji-ailesi içinde — tek bir fikrin parametre-ızgarası — geçerlidir, ama heterojen aileler arasında değil; orada denemeler-arası varyans temiz bir çekiliş değildir.

Bunlar nedeniyle, parametrik bir düzeltmenin kullanıldığı yerde, o düzeltme tek-başına bir kapı değil bir çapraz-kontrol (cross-check) işlevi görmelidir. Tekil bir parametrik sayı, bir hükmü tek-başına taşımamalıdır; t-istatistiği, deflasyon düzeltmesi ve — herhangi bir evren-dışı dilim karşılanabildiği her yerde — yapısal bir ayrık-kümenin (holdout) uzlaşması şart koşulmalıdır.

İki ilke, seçilim-yanlılığını arka-kapıdan yeniden-devreye-sokmadan bunu operasyonel kılar.

Birinci, mod-seçimi herhangi bir aday gözlenmeden önce dondurulur. Hem konjuge eğitim/test ayrımını hem de tüm-evren değerlendirmesini destekleyen bir değerlendirme-motoru, her soru için en-sadık yöntemin gerçek bir seçimini sunar — ama bu seçim, bir adayın davranışı bilindikten sonra değil, ölçümden önce verinin yapısına bakılarak yapılmalıdır. Bir sinyali hayatta-tutan hangi mod ise ona geçmek, metodolojik bir kostüm giymiş seçilim-yanlılığıdır; ve eşikleri donduran aynı ön-kayıt, mod-seçimini de dondurmalıdır.

İkinci, iki tür fizibilite ayrı tutulmalıdır. Mühendislik-fizibilitesi — bir ayrıştırıcı (parser) inşa etmek, bir panel derlemek, bir seri edinmek — çabayla çözülür; çözülmemişse sebebi maliyet ya da tereddüttür, gerçek bir duvar değil. Bilgi-fizibilitesi — bir etkiyi çözmek için gereken istatistiksel güç, o güç eldeki veride basitçe yokken — çabayla çözülmez. Hiçbir miktar çalışma, verinin içermediği gücü imal etmez. Bu sınırı tanımak, işi doğru yapmanın bir parçasıdır: eldeki-veride saptanamaz hükmü meşru bir sonuçtur, bir özen-eksikliği değil; ve onu kaydetmek başlı-başına pozitif bir sonuçtur.

### I.4 Ön-kayıt: Frozen Stage-0

Her ölçümden önce hipotez, yön (sign), kabul-eşiği ve per-faktör deneme-bütçesi (`N ≤ 3`) yazılı olarak **donar**. Ölçüm görüldükten sonra:

- Eşik gevşetilemez (post-hoc relaxation yasak).
- İşaret ters çevrilemez (sign-flip yasak — ters-işaretli bir sonucu "demek ki tersine çalışıyormuş" diye kurtarmak, hipotezi sonuca uydurmaktır).
- Sonuç-öncesi tanımlanmamış yeni bir alt-kesim eklenemez (cherry-pick yasak).

Bu prosedür, I.2'deki "tahmin, uyum değil" ilkesinin operasyonel zırhıdır.

### I.5 Konjuge ayrım protokolü

Geliştirme ile test fiziksel olarak ayrılır:

- **Geliştirme evreni (X₁):** iteratif çalışılır, geri-bildirim serbesttir, ama deneme-bütçesi sınırlıdır (`N ≤ 3`).
- **Test evreni (X₂):** geliştirme görülmeden *önce* dondurulur, **tek atış** ölçülür. Eşiğe ittirilerek geçirilen bir sonuç geçmiş sayılmaz: *PASS ettirmek ≠ PASS etmek.*

İki bağımsızlık koşulu pazarlık-konusu değildir: (a) X₁ ile X₂ örneklem-bağımsızlığı; (b) test-evreni tek-atışlığı. Test-evreni-FAIL kalıcı kapanıştır. Buna karşılık **rejim-bağımsızlık şart değildir**: rejime-bağlı bir faktör, ex-ante (öngörü-anında bilinebilir) bir nowcast ile yakalanabiliyorsa meşrudur — yeter ki bu nowcast geleceğe-bakmasın.

---

## Bölüm II — Negatif Bilgi Pozitif Bilgidir

### II.1 "Saptanamadı ≠ yok" — ve güç-uyarısı

Bir testin sinyal saptayamaması, sinyalin yokluğunu *kanıtlamaz*. Ancak bu ilke iki yönlü çalışır ve ihmal edilen yön daha önemlidir: **güç-yoksunu (underpowered) bir null ile yeterli-güçlü bir null farklı bilgi taşır.** Örneklem inceyse, saptanamama büyük ölçüde bilgi-taşımaz — "henüz bilmiyoruz" der. Buna karşılık yeterli güçle, geniş-evrende, frozen-Stage-0 altında tekrarlanan saptanamama, gerçek bir negatif bilgidir: o eksende deploy-edilebilir edge **yoktur**. İki durumu ayırmak, negatif sonucu doğru sınıflandırmanın anahtarıdır (Bölüm II.3, mezarlık ile save/wait ayrımı).

### II.2 Mezarlık: tüketilmiş eksenler

Aşağıdaki eksenler, her biri frozen-Stage-0 ve test-evreni-FAIL ile, kalıcı olarak kapatılmıştır. Liste yeniden-açılmaz; korunur, çünkü her giriş bağımsız bir bilgidir.

| Eksen | Test edilen | Hüküm | Neden |
|---|---|---|---|
| Kesitsel fiyat-faktör seçimi | Değer, momentum, düşük-oynaklık, 52-hafta-yüksek, trend (8+ varyant) | Edge yok | Temiz-evrende deploy-edilebilir kesitsel ayrışma yok |
| Ortogonal zamanlama sinyalleri | Yabancı-akım, reel-faiz | Trade-edilebilir değil | Yabancı-akım *eşzamanlı* (coincident), öncü değil; bilinebilir-gecikmeli formu tüm öngörü-içeriğini kaybeder |
| Olay-tilt | Yeniden-yapılanma türevli olay-faktörleri | Trade-edilebilir değil | Sinyal var ama harvest-edilebilir işlem-formuna dönüşmüyor |
| Türev açık-pozisyon | Tek-hisse-futures açık-pozisyon (OI) | FAIL | HAC-`t` negatif/sıfır mertebesinde |
| Öngörülebilir mekanik akım | Endeks yeniden-yapılandırma (reconstitution) | FAIL | Sıfıra-yakın `t`; mekanik-akım önceden fiyatlanıyor |
| Kazanç-sürprizi sonrası sürüklenme | PEAD (sürpriz-tercile) | FAIL | Brüt getiri dahi sıfır; likit tarafta edge yok |

**Program-çıkarımı:** Bu eksenlerin tümünde deploy-edilebilir-edge bulunamaması, pasif/akıllı-beta çapanın doğru-yaklaşım olduğunun *bağımsız teyididir*. "Offline tüketildi ≠ edge tüketildi" doğrudur; ama altı bağımsız eksenin yeterli-güçle saptanamaması, çapanın merkez-olması gerektiğine dair yan-bilgi yükünü ciddi biçimde artırır.

### II.3 Save/wait kategorisi (mezarlıktan ayrı)

Her negatif sonuç mezarlık değildir. Bir eksen, **test-evreni hiç görülmeden mühürlü kaldıysa** ve eldeki null güç-yoksunu ise, mezara girmemiştir — *save/wait* statüsündedir.

Somut örnek: içeriden-bildirim (insider-disclosure) ekseni. Üç cephe de boş çıktı —

- **Yön (alış):** trade-edilebilir tarafta edge yok; temiz-baseline'da da anlamsız.
- **Yön (satış):** gözlenen market-relative negatiflik, *olay-bağlı* değil **isim-seçilim** çıktı (placebo testi anlamsız); harvest-edilen şey bilinen-zayıf bir faktör, içeriden-alfa değil. Anlamlılık kırılgan.
- **Yoğunluk:** koordineli-küme örneklemi tek-haneli; istatistiksel güç yok, doğmadan-ölü.

Bu üç cephe boş olmasına rağmen eksen **mezarlık değildir**, çünkü: test-evreninde hiçbir frozen-Stage-0-FAIL gerçekleşmedi (X₂ mühürlü kaldı) ve null güç-yoksunu. Gelecekte daha-büyük-N, farklı-rejim veya olay-bağlı placebo-pozitifliği görülürse yeniden-açılabilir; o anda mühürlü test-evreni hâlâ temiz tek-atış olur. Mezarlık ile save/wait'i karıştırmamak, II.1'deki güç-uyarısının doğrudan operasyonel sonucudur.

### II.4 Mezarlık neden kalıcı ve diriltilmez

Mezara giren eksen, temiz bir test-evreniyle bir kez ölçülmüştür. Aynı evrene dönüp "bir de şöyle bakalım" demek, II.1'deki tek-atış disiplinini kırar ve uyum'u (accommodation) yeniden devreye sokar. McLean-Pontiff bozunması da aynı yöne işaret eder: belgelenmiş bir negatif sonucu zorlayarak tersine çevirme girişimi, edge üretmek yerine yanlış-pozitif üretir. Diriltmenin tek meşru yolu, **gelecekte temiz ve bağımsız bir evrenin** ortaya çıkmasıdır — eski evrenin yeniden-taranması değil.

---

## Bölüm III — Süreç-İçi Tehlikeler (meta-dersler)

Bu bölüm, ölçümün *kendisi* doğru kurulsa bile sentezi bozabilen tuzakları kayıt altına alır.

### III.1 Forgone-beta: sinyal-gating'in baskın maliyeti

Bir sinyalin nakdi "kapıda tutması" (sinyal yokken yatırımsız kalmak), kaçırılan piyasa-betasını en büyük kayıp-kanalı yapar — diğer faktörlerin yaklaşık **on katı** mertebesinde. Bu yüzden temel-yasa: *sinyal asla nakit-gate etmez.* Boşta-kalan sermaye tam-yatırımlı bir tabanda (örn. eşit-ağırlık) durur; tetikçi yalnızca sepet-içi yeniden-tilt yapar, yatırımlı-olup-olmamaya karar vermez.

### III.2 Rejim-bağımlılık kabul edilebilir (ex-ante nowcast mümkünse)

Bir faktörün yalnız belirli rejimlerde çalışması, onu otomatik olarak geçersiz kılmaz. Eğer rejim *öngörü-anında* (geleceğe-bakmadan) bir nowcast ile sınıflandırılabiliyorsa, faktör meşrudur. Önemli olan, bu rejim-yargısının backtest-iddiasını kirletmemesidir: diskresyoner makro/rejim-nowcast'leri, ayrı ve **ex-ante** bir ileri-deftere (forward-ledger) yazılır — tarih/rejim/tahmin/güven/ufuk/skor sütunlarıyla — ve araştırma-kaydına karışmaz.

### III.3 Baseline kontaminasyonu

Bir confound (karıştırıcı) testinde kontrol-grubu (baseline) *sinyal-taşıyan* örnekler içerirse, gerçek-sinyal **null görünür**. Karşılaştırma kirlendiğinde, fark sıfıra çekilir ve testçi yanlışlıkla "etki yok / confound kesin" hükmü verir.

Bunun bir canlı örneği: bir satış-sinyali, "satış-olmayan" diye tanımlanan bir baseline'a karşı test edildi; ancak o baseline, kendisi negatif-drift'li olan *alış-işaretli* örnekleri içeriyordu. Kontaminasyon gerçek farkı null'a çekti ve ilk hüküm ("confound kesin") bir baseline-artefaktı oldu. Temiz, olay-içermeyen bir kontrol grubuna geçildiğinde fark yeniden belirdi (ama bu sefer placebo onu *olay-bağlı* değil isim-seçilim olarak ayrıştırdı). **Kural:** confound testinde baseline temiz-kontrol (sinyal-taşımayan) olmalıdır; ve "olay vs. ters-olay" ile "olay vs. olay-yok" ayrı raporlanmalıdır.

### III.4 Yazar-denetçi bağımsızlığı

Bir ölçümü tasarlayan aktör, aynı ölçümü denetlerse, kör-noktalar **korelasyonludur** — tasarımdaki bir varsayım hatası, denetimde de aynı varsayımla gözden kaçar. Bu yüzden yazarın kendi-işini denetlemesi yapısal olarak *compromised*'tır; değer üretebilir, ama yeterli değildir. Kritik confound ve edge hükümleri, biriken-bağlamdan ve motive-akıl-yürütmeden arınmış **bağımsız (taze-bağlam) bir denetim** hak eder. Bu denetime yalnızca karar, ham çıktı ve istek aktarılır; üretim-konuşmasının kendisi aktarılmaz.

### III.5 Lokalizasyon da ölçümdür

Pahalı bir Stage-0'a girmeden önce, ucuz bir prior-kontrol çoğu zaman kararı verir. Bir hipotezin örneklem-büyüklüğünü veya yapısal-uygunluğunu *getiriye bakmadan* saymak (örn. koordineli-küme sayısının tek-haneli olduğunu görmek), aday-hipotezi pahalı ölçümden önce eler. Sayım frozen-Stage-0'dan önce ve sinyal-görmeden yapıldığı sürece, bu konjuge-ayrım protokolüyle uyumlu bir prior-kontroldür ve ön-kayıt disiplinini bozmaz.

---

## Bölüm IV — Program Düzeyinde Çıkarım

1. **Sistematik kazananın paydası risk-disiplinidir, proprietary-faktör değil.** Uzun-ufuklu kazanan azınlığın ortak-paydası pozisyon/kaldıraç-disiplini ve ruin-kaçınmadır; gizli bir faktör değil. Bu, mevcut risk-yapısını doğrular ve aday-edge yokluğunda bile programın ayakta kalmasını sağlar.

2. **Doğrulanmış pasif çapa programın merkezidir.** Bölüm II'deki negatif-bilgi sentezi, bu merkez-tercihin bağımsız teyididir. Boş bir aday-boru-hattı, yeni-eksen-zorlamak için değil, konsolidasyon için bir çağrıdır; yüksek-önselli aday yokken yeni-eksen açmak, edge üretmez, yalnız yanlış-pozitif riskini ve dikkat-enflasyonunu artırır.

3. **Gelecek her aday için ayakta-protokol:**
   Frozen Stage-0 (eşik/yön/bütçe ölçümden önce donar) → konjuge ayrım (iteratif X₁ / tek-atış X₂, örneklem-bağımsız) → ölçüm-doğrulama (differential + metamorphic + placebo + insan-checkpoint) → kritik-hüküm için bağımsız taze-bağlam denetimi. Bu zincirden geçmeyen hiçbir sonuç araştırma-kaydına edge olarak girmez.

---

*Bu doküman bir referanstır ve negatif bilgiyi de pozitif bilgi sayar: tüketilmiş eksenlerin envanteri korunur, silinmez. Geçmiş bir evrimdir; disiplin gevşemez.*
