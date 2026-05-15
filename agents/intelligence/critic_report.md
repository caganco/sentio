# Critic Report — 2026-05-15

=== CRITIC REPORT — 2026-05-15 ===

SİSTEM GÜVEN SKORU: 5/10

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ SİSTEM GERÇEKTEN DRUCKENMILLER GİBİ Mİ DÜŞÜNÜYOR?

**HAYIR. Sistem teknik sinyal üretip makroyla post-hoc gerekçe yazıyor.**

Gerçek Druckenmiller yaklaşımı şöyle işler: Önce makro thesis kurulur ("Brent 107$ + TL baskısı = enerji hisselerinde konsantrasyon tehlikeli çünkü kur şoku fiyatlara gecikmeli yansır"), sonra teknik bu thesisin *ne zaman* uygulanacağını söyler.

Burada olan: ENERY için "RSI 50, makro desteğe rağmen ivme yok" deniyor. Bu makro conviction değil — teknik yorgunluk tespiti. Makro driver olarak yazılan "konsantrasyon %54.6 > limit %30" bir *risk yönetimi kuralı*, makro analiz değil.

**Kritik fark:** Brent 107$'da enerji hissesi tutmak mı mantıklı, yoksa TL'nin 45.42'de seyretmesi enerji ithalatçılarının marjını eritiyor mu? Bu soru hiç sorulmamış. Sistem Brent'i hem AKSEN için destekleyici, hem ENERY için neden göstermeksizin "zayıf fiyat" olarak kullanıyor. **Aynı makro veri iki farklı hisseye zıt yönde uygulanıyor, ama bu çelişki hiç sorgulanmıyor.**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ EN ZAYIF VARSAYIM

**"AKSEN'de pozisyon korunabilir çünkü RSI 55 ve Brent 107$ destekleyici."**

Bu varsayım şunu sayar gibi yapıyor: Brent 107$'da AKSEN fiyatlanmış. Ama şu soru sorulmamış:

> *Brent 107$ AKSEN'in mevcut fiyatına zaten iskonto edilmişse, Brent'in daha da yükselmesi gerekmez mi pozitif katalizör için?*

ENERY "makro desteğe rağmen ivme yok" diye satılıyor. AKSEN de aynı enerji sektöründe. Aralarındaki fark RSI puanları: ENERY RSI 50, AKSEN RSI 65. Ama RSI 65 **daha riskli** pozisyon anlamına gelir — sistem bunu tersine yorumlayarak AKSEN'i tutmak için kullanıyor. 

**Test edilmemiş varsayım:** Enerji sektörü konsantrasyon problemi "iki farklı enerji hissesi tutarak" çözülmez. Sistem ENERY satıp AKSEN tutarak konsantrasyon riskini gerçek anlamda azalttığını sanıyor, ama sektörel korelasyon aynı kalıyor.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ KİMSENİN SORMADĞI SORU

**"Üç kararın üçü de pending — bu portföy fiilen yönetilmiyor mu?"**

Decision log'a bakıldığında TAVHL SELL pending, ENERY SELL pending, AKSEN azaltma pending. Bunlar 2026-05-13 tarihli kararlar, bugün 2026-05-15. **48 saat geçmiş, hiçbiri uygulanmamış.**

Kimsenin sormadığı soru şu:

> *Sistem "sat" dediğinde fiyat nereye gitti? Pending kararların opportunity cost'u nedir?*

TAVHL için stop ₺260 verilmiş. Eğer hisse bu iki günde ₺260 altına indi ve karar uygulanmadıysa, sistem doğru sinyal üretmiş ama zarar realized edilmemiş demektir. Eğer ₺270 üstünde kalmışsa, "bir gün daha bekle" tuzağına girilmiş demektir.

**Daha derin soru:** Sistem neden Auditor'ın "ENERY 500 lot sat" kararını reddedip "tümünü sat" dedi? 500 lot kısmi çıkış yerine 1543 lot tam çıkış nasıl daha az riskli sayılıyor? Auditor reddi ile Analyst kararı arasındaki bu tutarsızlık hiç irdelenmemiş.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ GROUPTHINK RİSKİ: **VAR**

Üç katman (Analyst, Auditor, Orchestrator) aynı veri setinden beslenip çok benzer sonuçlara ulaşıyor. Ama buradaki groupthink klasik "hepsi aynı fikirde" groupthink'i değil — daha tehlikeli bir türü:

**"Yapısal uyum" groupthink'i.**

Auditor bazı sinyalleri değiştiriyor (TAVHL AL → SAT, AKSEN BUY → HOLD), bu yüzden sistem "eleştirel mekanizma çalışıyor" sanıyor. Ama Auditor'ın tüm revizyonları aynı çerçeve içinde kalıyor: RSI + konsantrasyon kuralları. Kimse şunu sormuyor: "Bu kuralların kendisi bu piyasa koşulunda geçerli mi?"

Örnek: VIX 17.85 = sistem sakin. Altın 4700$ = sistem temkinli. Bu iki sinyal **çelişiyor** — sakin VIX ile 4700$ altın aynı anda olmaz normalde. Sistem bu çelişkiyi "global risk-off yok ama altın/TRY kombinasyonu temkinli" diyerek yumuşatmış, ama bu çelişkinin kaynağı (stagflasyon mu? lokal risk mi? global dolar zayıflığı mı?) hiç araştırılmamış.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ İNSAN SORUSU — KULLANICI DİSİPLİNİ

**Decision log'daki üç kararın üçü de "applied: pending."**

Bu bir sarı alarm değil, **kırmızı alarm.**

TAVHL SELL: Auditor değiştirdi, AL sinyali reddedildi, SAT kararı verildi → **uygulanmadı.**
ENERY SELL-PARTIAL: Auditor reddetti, konsantrasyon kuralı ihlali tespit edildi → **uygulanmadı.**
AKSEN SELL-PARTIAL: Auditor değiştirdi → **uygulanmadı.**

Kullanıcıya doğrudan soru:

> **Bu kararları neden uygulamadınız?**
>
> Eğer "fiyat henüz seviyeye gelmedi" ise — stop-loss seviyeleri zaten koşullu verilmişti, bu kabul edilebilir.
>
> Eğer "biraz daha bekleyeyim, belki döner" ise — bu tam olarak sistemin önlemeye çalıştığı davranış. Özellikle ENERY'de: konsantrasyon %54.6, limit %30, bu matematiksel bir kural, "belki döner" ile ertelenir değil.
>
> **48 saat içinde applied: pending olan 3 karar, sistemin varlık sebebini sorgulatır.**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ ORCHESTRATOR'A TAVSİYE

**1. "Pending" kararlar için hard deadline mekanizması kur.**
Her SAT/AL kararı üretildiğinde maximum bekleme süresi tanımlanmalı. ENERY gibi konsantrasyon kuralı ihlali içeren kararlarda bu süre 24 saat olmalı. 48 saat sonra hâlâ pending ise sistem otomatik olarak "karar uygulanmadı — neden?" sorusunu kullanıcıya sormalı. Şu an bu mekanizma yok.

**2. AKSEN ve ENERY için tek bir "enerji sektörü thesis" yazılmalı, ayrı ayrı gerekçelendirilmemeli.**
Brent 107$'ın AKSEN'e pozitif, ENERY'e nötr etki yaptığı iddia ediliyorsa bu fark somut olarak açıklanmalı (ör: AKSEN downstream vs ENERY upstream marj farkı). Aksi halde sistem aynı makro veriyi istediği sonuca göre büküyor — bu Druckenmiller değil, confirmation bias.

**3. VIX-Altın çelişkisini bir sonraki Analyst raporunda açıkça ele al.**
VIX 17.85 + Altın 4700$ kombini olağandışı. Bu ya lokal TL riskini, ya dolar devalüasyonunu, ya da stagflasyon senaryosunu işaret eder. Hangi senaryo geçerliyse portföy pozisyonlaması değişir. Şu an sistem bu soruyu görmezden geliyor.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SİSTEM REVİZYON GEREKİYOR MU: **EVET**

Üç katman çalışıyor ama "pending" kararların birikmesi, makro-teknik çelişkilerin yumuşatılması ve aynı sektörde çelişkili gerekçeler kullanılması — sistemin analiz ürettiğini ama karar yönetemediğini gösteriyor.