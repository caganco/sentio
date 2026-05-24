## BIST 2023-2026 Sektör Pratiği (RR-011 Yama Bölümü)

**Kapsam**: Bu bölüm, RR-011'in akademik karar matrisine (Yol 1=24/50, Yol 2=31/50, Yol 3=41/50, Yol 4=37/50) paralel bir "2024-2026 BIST Pratiği Uyumu" lensi ekler. Mevcut TL;DR, karar matrisi ve Yol 3 ana önerisi DEĞİŞMEMİŞTİR. Bu yama, akademik perspektifi saha gözlemiyle çapraz-doğrulamak için ek bir sütundur.

**KRİTİK BULGU (özet)**: Akademik en yüksek skor (Yol 3) ile sektör pratiği en yüksek skoru (Yol 3 ve Yol 4 başa baş) ÖRTÜŞÜYOR — kritik çelişki yoktur. Ancak iki yan-bulgu öne çıkıyor:

1. Türk aracı kurumlarında Türkçe finansal NLP'nin **production'da kullanıldığına dair somut LinkedIn/Kariyer.net kanıtı saha taramasında bulunamamıştır** — bu Yol 1 (custom training) için akademik 24/50 zaten zayıf skorunu pratik 2/5 ile pekiştirir (terk).
2. Pratisyenler tarafında dominant pratik **keyword + sezgi** (rule-based ailesine yakın) — Yol 4'ün pratik skoru beklenenden yüksek (4/5), ama akademik kalitesi düşük (37/50; macro-F1 hurdle riski).

---

### Alt-Bölüm 1: Türk Fintech/Trading Community NLP Kullanım Pratikleri

**A. Retail forum ve sözlük taraması**: Hisse.net ve BigPara forum içeriklerinde "FinBERT", "Türkçe sentiment NLP" gibi terimlerin sistematik kullanım kanıtı bulunamamıştır. DataKapital blog'unda (datakapital.com) sentiment analizi tekniğinin Reddit r/wallstreetbets gibi platformlarda manipülasyon tespit için kullanıldığı kabul edilmekte, ancak Türkçe için "Twitter'da insanların borsaya ilgisi gözle görülebilecek kadar azdır. Genel geçer borsa analizleri olmakla birlikte borsaya dahil detaylı analizlerin çoğunun takipçisi Reddit'tekilerle kıyaslanamayacak kadar azdır" (https://datakapital.com/blog/sosyal-medya-verileri-ile-sentiment-analiz-teknigi/). Türkiye'de BIST için **subreddit benzeri merkezi tartışma platformu yok** — Hisse.net ve BigPara forum hisse-bazlı tahta'lar şeklinde dağınık.

**B. Twitter/X Türk fintwit ekosistemi**: Ekşi Sözlük başlıkları "Twitter'daki bol takipçili borsa çomarları" (https://eksisozluk.com/twitterdaki-bol-takipcili-borsa-comarlari--5983502) ve "Twitter'da borsa analizi yapan hesaplar" (https://eksisozluk.com/twitterda-borsa-analizi-yapan-hesaplar--6596744) pratisyen gözlemini özetler: hesapların büyük çoğunluğu lisanssız, "ben dedim, yükseldi" tarzı survivor-bias açıklaması, teknik analiz grafiği + yorumdan oluşan içerikler. **ML/sentiment automation kullanımına dair açık iddia bulunamamıştır.** DataKapital'in "BIST Twitter Influencerları" listesi (https://datakapital.com/bist/twitter) etki skoru üretiyor ama bu hesapların kendi NLP kullanımı değil, dış gözlemci tarafından yapılan agregasyon.

**C. YouTube borsa kanalları**: Murat Sağman (https://www.youtube.com/playlist?list=PLBv4yZQlYYICQ71O79405ZT4rxwyd50N8) ve benzer "ekonomist" tarzı kanallarda metodoloji **kalitatif yorum** — makroekonomik veri (faiz, enflasyon, kur) + uzman görüş — şeklinde. ML sentiment kullanım kanıtı yok. Murat Muratoğlu (https://www.youtube.com/channel/UCJEzfyorQwES0hyNpqhym_Q) köşe yazarı tarzı görüş paylaşımı yapıyor.

**D. Akademik tarama (önemli istisna)**: Boztepe (2025), Niğde Ömer Halisdemir Üniversitesi Mühendislik Bilimleri Dergisi, BIST 30 üzerinde BERTurk + LSTM hibrit modeli ile sektörel asimetri tespit etti: Enerji **+%14.31** tahmin doğruluğu artışı, Çelik **-%10.03** kötüleşme (https://dergipark.org.tr/en/pub/ngumuh/article/1839166). Bu, akademik tarafta hibrit yaklaşımın **sektör-bazlı** kalibrasyon gerektirdiğini gösteriyor — ancak bu çalışma akademik bir tez, production sistem değil.

**Hipotez değerlendirmesi**: Türk pratisyenler ML sentiment kullanmıyor — keyword + gut feeling dominant. Bu boşluk:
- **Rekabet avantajı (a) tezi**: Doğrulanır — kimsenin yapmadığı bir alan, alpha açığı potansiyeli var.
- **Kimse yapmıyorsa nedeni vardır (b) tezi**: Kısmen doğrulanır — Türkçe NLP morfolojik zor (literatürde tutarlı: https://dergipark.org.tr/tr/download/article-file/1736703), 2023-2024 makro şokları (enflasyon, seçim, deprem) zaten haber sinyalini gürültüye boğmuş.
- **Net pozisyon**: (a) ve (b) BİRLİKTE doğru. Alpha açığı var ama getirisi düşük olabilir. Yol 3 LLM hybrid maliyeti düşük olduğundan bu trade-off kabul edilebilir.

---

### Alt-Bölüm 2: Türk Broker Araştırma Departmanları — NLP Kullanıyor mu?

**A. Major broker araştırma raporları yazım tarzı**: İş Yatırım, Garanti BBVA Yatırım, Yapı Kredi Yatırım gibi major brokerların günlük/haftalık raporları kalitatif yazım tarzında — "beklentilerin üzerinde sonuçlar", "model portföydeki ağırlık" gibi ifadeler (örnek: https://www.dunya.com/kose-yazisi/bist-100-icin-mola-vakti/701771 İş Yatırım Volkan Düzkancık model portföy yorumu). **Sentiment skoru, NLP-çıktısı veya quant-text sinyali deklarasyonu görülmedi.**

**B. LinkedIn / Kariyer.net pozisyon taraması (Mayıs 2026)**:
- LinkedIn Türkiye konumunda 175 "Quantitative Analyst" ilanı listeleniyor (https://tr.linkedin.com/jobs/quantitative-analyst-jobs) — ama önemli kısmı kredi risk, HFT, multi-asset trading; **hiçbiri "Türkçe finansal NLP" veya "FinBERT" beceri talep etmiyor**.
- İş Yatırım'ın açtığı "Algoritma Geliştirme Mühendisi" pozisyonu (https://www.kariyer.net/is-ilani/is-yatirim-menkul-degerler-junior-trader-2892628) algoritmik trading geliştirme, NLP değil.
- InvestAZ "Quantitative Researcher Stajyeri" (https://www.kariyer.net/is-ilani/investaz-yatirim-menkul-degerler-a-s-quantitative-researcher-stajyeri-2600984) — stajyer pozisyonu, NLP içeriği yok.
- Garanti BBVA Teknoloji'nin data scientist pozisyonları (https://tr.linkedin.com/jobs/view/data-scientist-at-garanti-bbva-4186845442) bankacılık tarafı (kredi risk, müşteri analitik), broker tarafında değil.
- Borsa İstanbul "BT BİST Yetenek 2026 — İşe Alım Sınavı (BT Birimleri)" (https://www.kariyer.net/is-ilani/borsa-istanbul-a-s-bt-bist-yetenek-2026-ise-alim-sinavi-bt-birimle-4441034) Yapay Zeka Mühendisliği ve Yapay Zeka ve Veri Mühendisliği bölümlerini uygun eğitim listesine ekledi (yeni gelişme, 13 Mayıs 2026), ancak ilan generic BT pozisyonu — NLP/sentiment/FinBERT spesifik rol değil.

**Net bulgu**: Türk aracı kurum quant masalarında **public olarak doğrulanabilen Türkçe finansal NLP / FinBERT / sentiment rolü Mayıs 2026 itibarıyla TESPIT EDİLEMEMİŞTİR**. Bu absence-of-evidence; yokluğu kanıtlamaz (içeride "Data Scientist" generic başlığı altında olabilir), ancak market white-space argümanını destekler.

**C. TEFAS top-performing fonlar ve fund manager profilleri**: İş Yatırım'ın LinkedIn'de erişilebilir profil olan İlkay Öztürk (https://www.linkedin.com/in/ilkayozturk92/) "Director of Portfolio Management" — R'da Black-Litterman, Risk Parity, FX momentum, equity factor analysis bahsediyor; **NLP/sentiment yok**. Bu, Türk asset management tarafında **klasik factor modelleme + diskresyonel** yaklaşımın hakim olduğunu doğruluyor.

**D. SPK düzenlemesi — Algo trading ve AI**:
- SPK Temmuz 2025 düzenleme çalışmaları (https://www.procompliance.net/spk-tarafindan-hazirliklari-surdurulen-duzenleme-calismalari-temmuz-2025/) açıkça belirtiyor: **"Algoritmik ve yüksek frekanslı işlem gerçekleştiren yatırım kuruluşlarına yönelik belirlemeler yapılması"** hazırlık aşamasında. Yatırım kuruluşları AI kullanımı için spesifik bildirim yükümlülüğü henüz yok.
- SPK 2024/48 sayılı kripto bülteni (https://fintechistanbul.org/2024/09/20/spk-2024-48-sayili-bulteni-ile-kripto-alanindaki-yeni-ilke-kararini-yayimladi/) emir log kayıtlarının zaman damgalı saklanmasını 08.11.2024 itibarıyla zorunlu kıldı — algo trading için audit trail beklentisi var.
- **Retail <500K TL portföy için (the maintainer'ın profili) doğrudan AI bildirim yükümlülüğü yok**, çünkü the maintainer kendi parasıyla işlem yapıyor, aracı kurum hizmeti değil.

---

### Alt-Bölüm 3: 2023-2024 Hiperenflasyon Döneminde Türkçe Haber Sentiment Anomalileri

**A. Mayıs 2023 seçim dönemi**: 14 Mayıs ilk turun ikinci tura kalmasının ardından 15 Mayıs 2023 BIST 100 açılışta -%6.4 ile devre kesici tetikledi (Borsa İstanbul KAP açıklaması, https://www.haberturk.com/secim-sonrasi-borsada-dusus-3591825-ekonomi); gün kapanışında -%6.14, BIST Bankacılık endeksi -%9.5. Sonrasında 28 Mayıs ikinci tur sonucunun ardından Mehmet Şimşek atanması ile BIST 100 Mayıs trough'undan (4,427 puan) 5 Eylül 2023'te 8,236.14 puana ulaştı — yaklaşık 3.5 ayda **+%86 toparlanma, all-time high** (Anadolu Ajansı: "BIST 100 endeksi 2023'ün başından 5 Eylül tarihine kadar yüzde 49,5'lik getiriyle 8.236,14 puana yükselerek, dünya genelinde önemli pay piyasaları arasında açık ara en iyi performansı sergiledi", https://www.aa.com.tr/tr/ekonomi/borsa-istanbul-yeni-yatirimcilarla-2023un-yildizi-olma-yolunda/2985607). Bu dönemde KAP açıklamaları içerik olarak değişmedi — sentiment modeli (nötr/kategorik) muhtemelen "hiçbir şey değişmedi" derken fiyat -%6 düştü ve sonrasında +%86 yükseldi. **Bu rejim-bağımsız sentiment için klasik fail-mode'dur.**

**B. 2022-2024 hiperenflasyon dönemi**: TÜİK Aralık 2024 verisi: yıllık TÜFE %44.38, on iki aylık ortalama TÜFE %58.51 (https://www.aa.com.tr/tr/ekonomi/enflasyon-yillik-bazda-yuzde-44-38e-geriledi/3440707). Şirket "kâr %50 arttı" haberi nominal pozitif ama enflasyon-adjusted REEL kayıp anlamına gelebilir. Eral Karayazıcı'nın Bigpara yorumu (https://bigpara.hurriyet.com.tr/bigpara-yazarlari/eral-karayazici/secim-sonrasi-borsa-istanbul_ID986622/) açıkça vurguluyor: "BIST 12 ay daha yatay kalsa bu enflasyon nedeniyle reel %35 kayıp anlamına gelir". Türkçe FinBERT modelleri reel-nominal ayrımı kodlamıyor.

**C. Şubat 2023 deprem (Kahramanmaraş)**: 6 Şubat 2023 deprem sonrası ilk iki günde BIST 100 -%9.8 (6 Şubat -%1.35; 7 Şubat -%8.62 devre kesici), 8 Şubat sabahı -%7 daha sonra borsa kapatıldı, 8-15 Şubat aralığında 5 iş günü kapalı (https://www.aa.com.tr/tr/ekonomi/borsa-kahramanmaras-merkezli-depremlerin-ardindan-bir-dizi-tedbirle-bugun-isleme-aciliyor/2820119). Etkilenen şirketlerin KAP açıklamaları "iş sürekliliği sağlanmıştır" şeklinde, semantik olarak NÖTR — ama piyasa reaksiyonu -%16. Bu **crisis-period sentiment çöküşü** ders kitabı örneği (Atak vd. olay analizi: https://www.researchgate.net/publication/376016444_2023_Yili_Kahramanmaras_Depremlerinin_BIST_30_Endeksi_Uzerine_Etkisi).

**D. Regime-aware sentiment gereği**: Loughran & McDonald (2016, "Textual Analysis in Accounting and Finance: A Survey", *Journal of Accounting Research* 54(4):1187-1230, DOI: 10.1111/1475-679X.12123; https://onlinelibrary.wiley.com/doi/abs/10.1111/1475-679X.12123) sentiment lexicon'larının domain-specific kurulmasının gerekliliğini gösterdi; Tetlock (2007, "Giving Content to Investor Sentiment: The Role of Media in the Stock Market", *Journal of Finance* 62(3):1139-1168, DOI: 10.1111/j.1540-6261.2007.01232.x; https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2007.01232.x) WSJ "Abreast of the Market" pessimism faktörünün stock-level reaction'ı predikte ettiğini bulmuştur — ancak bu çalışmalar tek bir rejim varsayar. 2023 BIST'i çoklu rejim (BULL/BEAR/CRISIS) gerektirdiği için akademik finBERT binary class yetersiz kalır.

**Hipotez değerlendirmesi**: DOĞRULANDI. Akademik finBERT binary sınıflandırma BIST 2023-2024'te yetersiz kalır. Regime-aware (BULL/BEAR/CRISIS) sentiment + nominal/reel ayrım gerekir. **Bu bulgu Yol 3 (LLM) lehinedir** çünkü LLM context window'unda "Bugün TÜFE %44, USDTRY 45.71, seçim sonrası, deprem sonrası..." gibi makro durum bilgisi prompt'ta pass edilebilir; FinBERT-TR'de bu mümkün değildir.

---

### Alt-Bölüm 4: 2024-2026 Yerleşik Dönem — Hangi Haber Kategorileri Çalışıyor?

**A. Claude prompt testi (literatür temeli)**: Lopez-Lira & Tang (arXiv:2304.07619v6, son revizyon 28 Ekim 2025; https://arxiv.org/abs/2304.07619) GPT-4'ün headline'lardan stock return tahmin etme yeteneğini gösterdi: post-knowledge-cutoff headline'lar üzerinde portfolio-day hit rate **"yaklaşık %90 (non-tradable initial reaction için)"** (verbatim abstract). GPT-1, GPT-2 ve BERT'in bu yeteneği yok — predictability "emerging capacity of complex LLMs". DİKKAT: aynı çalışma performans erimesini de raporluyor — annualized Sharpe ratio 2021Q4'te 6.54'ten 2022'de 3.68, 2023'te 2.33, Ocak-Mayıs 2024'te 1.22'ye düşmüş; LLM benimsenmesi arttıkça strateji getirisi azalıyor. Türkçe'ye doğrudan transfer kanıtlanmış değil, ama Claude Haiku 4.5 multilingual yetenekleri (https://www.anthropic.com/news/claude-haiku-4-5) bu transferin teknik olarak mümkün olduğunu sugiyor.

**B. KAP kategori başına predictive power (literatür)**:
- **Nakit temettü dağıtımı**: Kadıoğlu, Telçeken & Öcal (2015, *International Business Research* 8(9):83-94, SSRN https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3971842) — 2003-2015 BIST, 902 açıklama, **negatif anormal getiri**, tax-clientele hipotezini destekliyor. Yolcu & Öztürk (2022) ise temettü artış pozitif, azalış negatif tespit etti (https://dergipark.org.tr/en/pub/esad/article/1191625).
- **Bedelsiz sermaye artırımı**: Aydoğan & Muradoğlu (1998) ilk çalışma, pozitif reaksiyon — sonrası inefficiency azaldı.
- **Halka arz, pay geri alımı**: KAP'ta sürekli açıklamalar (örnek: BIM, ORGE'nin 2026 geri alımları; https://www.getmidas.com/kap-haberleri/). Geri alım açıklamaları kısa vadede pozitif fiyat.
- **Yönetim değişikliği**: Context-heavy — örneğin AVOD Yönetim Kurulu Başkanı'nın gözaltına alındığı 2026 örneği KAP'ta paylaşıldı. Bu tip haberler keyword bazlı (gözaltı, tutuklama) kolayca sınıflanır.
- **SPK soruşturması / MASAK**: ISATR, ISBTR, ISCTR örneğinde Adana Cumhuriyet Başsavcılığı soruşturması (https://www.getmidas.com/kap-haberleri/) — yüksek negatif sinyal.
- **Konkordato/iflas erteleme**: Az frekanslı, çok yüksek negatif sinyal.
- **Faaliyet raporu**: ODTÜ tezinde (https://open.metu.edu.tr/bitstream/handle/11511/113400/10565277.pdf) faaliyet raporu Türkçe sentiment uygulanması zor — uzun metin, NER+aspect-based gerek.

**C. 2024-2026 en predictive haber kategorileri (hipotez)**: Kâr payı dağıtımı, halka arz fiyat belirleme, SPK soruşturması ve konkordato açıkça yüksek sinyal kategorileri. Faaliyet raporu en zor. **Bu hipotezi D-127 KAP kategori meta-etiketleme mevcut çalıştığı için Yol 3 ve Yol 4 ile çapraz-doğrulanabilir.**

---

### Alt-Bölüm 5: Maliyetin Gerçekçi Değerlendirmesi (2026 Türkiye Koşulları)

**A. Yol 3 LLM API maliyet revizyonu (Mayıs 2026 fiyatlarıyla)**:
- Claude Haiku 4.5: $1/$5 per MTok; **15 Ekim 2025'te release** (Anthropic verbatim: "Claude Haiku 4.5 is available everywhere today... Pricing is now $1/$5 per million input and output tokens", https://www.anthropic.com/news/claude-haiku-4-5); Batch %50 indirim; prompt caching cache-hit %90 ucuz.
- Claude Sonnet 4.6: $3/$15 per MTok; **17 Şubat 2026'da release** (Anthropic: "Pricing for Sonnet 4.6 starts at $3 per million input tokens and $15 per million output tokens", https://www.anthropic.com/claude/sonnet).
- Günlük 50 KAP açıklaması × 800 input + 100 output token = 40K input + 5K output token/gün ≈ 1.2M input + 0.15M output token/ay = **~$1.95/ay base** (caching/batch öncesi).
- Sonnet 4.6 ($3/$15) sadece yüksek-belirsizlik açıklamaları için kullanılırsa (örn: 5 açıklama/gün) ek ~$2-4/ay.
- **Toplam LLM API: ~$4-8/ay Haiku-dominant senaryosunda, ~$15-30/ay Sonnet-yoğun senaryoda.** USDTRY 22 Mayıs 2026 kapanışı **45.7069** (TradingEconomics: "The USD/TRY exchange rate rose to 45.7069 on May 22, 2026, up 0.30% from the previous session", https://tr.tradingeconomics.com/turkey/currency) → **TL bazında ~183-366 TL/ay düşük senaryo, ~686-1.371 TL/ay yüksek senaryo.**

**A1. KRITIK: Anthropic Pro/Max subscription ≠ API quota.** Anthropic Help Center: "Claude paid plans and the Claude Console are separate products... [API/Console] usage billed separately" (https://support.anthropic.com/en/articles/9876003-i-subscribe-to-a-paid-claude-ai-plan-why-do-i-have-to-pay-separately-for-api-usage-on-console). the maintainer'ın mevcut Claude Code Pro/Max subscription'ı **API çağrılarını KAPSAMIYOR** — ayrı kredi kartı + Stripe ödemesi gerekir. **Ek dikkat: 15 Haziran 2026 itibarıyla Anthropic, Claude Agent SDK / `claude -p` / GitHub Actions / 3rd-party agent kullanımını Pro/Max chat aboneliklerinden ayrı bir metered "Agent SDK credit" havuzuna geçiriyor** ($20 Pro / $100 Max 5x / $200 Max 20x, API fiyatları üzerinden, rollover yok; kaynak: https://codersera.com/blog/anthropic-june-2026-billing-change-claude-code/, https://the-decoder.com/claude-subscriptions-get-separate-budgets-for-programmatic-use-billed-at-full-api-prices/). Direkt API anahtarı kullanımı tamamen ayrı kalmaya devam ediyor.

**A2. Türkiye'den Anthropic ödeme**: Anthropic resmi supported countries listesinde Türkiye **açıkça listelenmiş** ("Türkiye (Turkey)" hem API hem Claude.ai bölümünde, https://www.anthropic.com/supported-countries). Türk Visa/Mastercard credit cardları Stripe üzerinden çalışıyor; address-mismatch / 3DS sorunları olabilir ama spesifik kısıt yok.

**B. Yol 1 Custom FinBERT-TR maliyet gerçeği**:
- Google Colab Pro+ ~$50/ay; Türkiye'den Google Play Store/Workspace ödeme TL ile çalışıyor.
- Kaggle GPU ücretsiz 30 saat/hafta.
- Lokal RTX 4090 alım maliyeti ~50K TL Mayıs 2026 — the maintainer'ın <500K TL portföyünün %10'u kadar, irrasyonel sermaye allocation.
- Apple Silicon M3 Max MPS BERT fine-tune mümkün ama uzun.
- BERTurk v2 (versiyon 2.0.0) Mart 2025'te release oldu (Stefan Schweter, Zenodo DOI: 10.5281/zenodo.14963493; https://github.com/stefan-it/turkish-bert) — aynı repo'da 3 Mart 2025'te BERT5urk (1.42B parametre, FineWeb2 üzerinde pretrained) da release edildi; base model donanım engeli azalmış.
- **Bir kez eğitim maliyeti: $1.500-2.000 hesaplama + iki haftalık emek (önemli unutulan kalem)**. Sürdürme: 0 ama re-train her 6-12 ayda gerekli.

**C. TL bazlı toplam maliyet karşılaştırması (USDTRY 45.7069, 22 Mayıs 2026)**:

| Yol | USD bir-defalık | USD aylık | TL bir-defalık | TL aylık |
|---|---|---|---|---|
| Yol 1 Custom | $1.740 | $0 | ~79.530 TL | 0 |
| Yol 2 Domain Adapt. | $1.000 | $20 (re-host) | ~45.710 TL | 914 TL |
| Yol 3 LLM Hybrid | $0 | $4-30 | 0 | 183-1.371 TL |
| Yol 4 Rule-based | $0 | $0 | 0 | 0 |

**Round-trip karşılaştırma**: the maintainer portföy ~85K TL × yıllık 12 round-trip × %0.41 = ~4.185 TL/yıl trading cost. Yol 3 yıllık maksimum maliyeti ~16.5K TL — trading cost'un ~%4'ü.

---

### Alt-Bölüm 6: Pratik Öneri Revizyonu — Paralel Sektör Skoru

#### Yeni kolon: "2024-2026 BIST Pratiği Uyumu" (1-5)

**Yol 1 — Custom FinBERT-TR: Sektör skoru = 2/5**

Kanıt 1 (negatif): Türk aracı kurum LinkedIn taramasında (İş Yatırım, Garanti BBVA Yatırım, Yapı Kredi Yatırım, vs.) "Türkçe finansal NLP" veya "FinBERT" production rolü tespit edilemedi (https://tr.linkedin.com/jobs/quantitative-analyst-jobs).

Kanıt 2 (negatif): Tek public sektörel BERTurk+LSTM çalışması Boztepe (2025) akademik tez, **kullanım statüsü production değil** (https://dergipark.org.tr/en/pub/ngumuh/article/1839166).

Kanıt 3 (negatif): ODTÜ tezi (https://open.metu.edu.tr/bitstream/handle/11511/113400/10565277.pdf) FinBERT İngilizce'den Türkçe'ye transferin yetersizliğini doğrudan tespit etti — "intended approach... significant challenges on the Turkish side occurred".

**Spec hipotezi 2/5 ile uyumlu; sektör pratiğinde alıcı yok.**

**Yol 2 — Domain Adaptation: Sektör skoru = 3/5**

Kanıt 1 (pozitif): BERTurk model'i Hugging Face'te aktif (https://huggingface.co/dbmdz/bert-base-turkish-cased) ve Mart 2025'te v2 (Zenodo DOI: 10.5281/zenodo.14963493) ile BERT5urk (1.42B parametre T5/UL2, FineWeb2 üzerinde pretrained) release edildi (https://github.com/stefan-it/turkish-bert).

Kanıt 2 (nötr): Boztepe (2025) BIST 30 sektörel asimetri çalışması bu yolun **akademik olarak fizibil** olduğunu kanıtladı — Enerji +%14.31, ama Çelik -%10.03. Bu sektör-bazlı kalibrasyon production'da yönetim yükü.

Kanıt 3 (negatif): Türkçe etiketli finansal veri kıtlığı literatürde tutarlı olarak vurgulanıyor (https://dergipark.org.tr/tr/download/article-file/1736703).

**Spec hipotezi 3/5 doğrulanır.**

**Yol 3 — LLM Hybrid (Lexicon→Haiku→Sonnet): Sektör skoru = 4/5**

Kanıt 1 (pozitif, akademik): Lopez-Lira & Tang (arXiv:2304.07619v6, Ekim 2025) GPT-4 portfolio-day hit rate "yaklaşık %90 non-tradable initial reaction için" (verbatim abstract, https://arxiv.org/abs/2304.07619).

Kanıt 2 (pozitif, ürün): Claude Haiku 4.5 15 Ekim 2025 release, $1/$5 per MTok, batch %50 indirim (https://www.anthropic.com/news/claude-haiku-4-5); Sonnet 4.6 17 Şubat 2026 release, $3/$15 (https://www.anthropic.com/claude/sonnet).

Kanıt 3 (pozitif, kullanıcı): the maintainer zaten Claude Code Pro/Max subscriber — ancak API ayrı (https://support.anthropic.com/en/articles/9876003).

Kanıt 4 (DİKKAT, negatif): Türk pratisyenlerin **otomatize sentiment için Claude/GPT API kullandığına dair sistematik public kanıt YOK**. Tek tek hesaplarda kişisel chat kullanımı olabilir ama production-grade quant pipeline kanıtı yok. **Bu nedenle spec 5/5'i 4/5'e revize edilmiştir** — "fiilen kullanılıyor" iddiası abartılı; "kullanılması teknik olarak en uygun yol" daha doğru.

Kanıt 5 (DİKKAT, negatif): Lopez-Lira & Tang annualized Sharpe ratio'sunda LLM benimsenmesi arttıkça performans erimesi raporluyor (2021Q4: 6.54 → 2024 Ocak-Mayıs: 1.22). Türkçe için bu erime henüz başlamamış olabilir (çünkü kimse production'da kullanmıyor) — first-mover avantajı kısa pencere.

**Yol 4 — Rule-based (Lexicon + KAP kategori meta-etiket): Sektör skoru = 4/5**

Kanıt 1 (pozitif): Pratisyenlerin dominant pratiği keyword + sezgi — Ekşi Sözlük "Twitter'daki bol takipçili borsa çomarları" (https://eksisozluk.com/twitterdaki-bol-takipcili-borsa-comarlari--5983502) ML kullanım olmadığını doğruluyor.

Kanıt 2 (pozitif): D-127 KAP kategori meta-etiketleme zaten çalışıyor — D-127 + kâr payı dağıtımı / SPK soruşturması / konkordato gibi yüksek sinyalli kategorilerde literatür güçlü (Kadıoğlu vd. 2015, https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3971842).

Kanıt 3 (negatif): RR-011 akademik kalite skoru 4/10 — rule-based macro-F1 ≥0.75 hurdle riski yüksek.

**Spec hipotezi 4/5 doğrulanır.**

#### Revize edilmiş tablo

| Yol | Maliyet | Süre | Kalite | Risk | Sürdür. | Akademik Toplam | **Sektör Pratiği (1-5)** | Final Lens |
|---|---|---|---|---|---|---|---|---|
| Yol 1 Custom FinBERT-TR | 3 | 2 | 8 | 4 | 7 | **24/50** | **2/5** | Akademik ve pratik aynı yönde: TERK |
| Yol 2 Domain Adapt. | 7 | 6 | 6 | 6 | 6 | **31/50** | **3/5** | Orta hat; veri etiketleme dar boğaz |
| Yol 3 LLM Hybrid | 9 | 9 | 8 | 7 | 8 | **41/50** | **4/5** | Önerilen; akademik+pratik en yüksek |
| Yol 4 Rule-based | 10 | 10 | 4 | 8 | 5 | **37/50** | **4/5** | Pratisyen pratiğine en yakın; kalite riski |

#### Net tavsiye

**Yol 3 ana öneri KORUNUYOR.** Akademik perspektif (41/50) ile sektör pratiği perspektifi (4/5) aynı yönde işaret ediyor. Sektör perspektifinden ek mitigation:

1. **Pratisyen alpha açığı tezi**: Türk brokerlarında public NLP/sentiment quant team kanıtı yok — bu Yol 3'ün uygulanması için zaman avantajı (first-mover potansiyeli). Ama "kimse yapmıyorsa nedeni vardır" uyarısı: Türkçe morfolojik zorluk + hiperenflasyon/şok dönemlerinde sentiment-driven alpha düşük olabilir + Lopez-Lira & Tang'ın gösterdiği global LLM-strateji erimesi. **MVP sonunda macro-F1 ≥0.75 hurdle'a + 2024H2 backtest'te en az +%2 risk-adjusted return improvement koşulu eklenmeli.**

2. **Yol 4 paralel hat tezi**: Pratisyen pratiği rule-based'e yakın olduğundan, Yol 4 D-127 mevcut + Loughran-McDonald-style Türkçe leksikon olarak baseline / fallback olarak korunmalı. Yol 3 hurdle'ı tutarsa Yol 4'e fallback otomatik ensemble katmanı olabilir.

3. **Yol 1 side project / CV pozisyonu**: Sektörde alıcı yok, akademik skor düşük, maliyet yüksek. **Side project olarak savunulamaz** — fırsat maliyeti çok yüksek; alternatif olarak the maintainer'ın 2 haftalık emeği Yol 3 MVP'ye gitmeli. Yol 1 yalnızca akademik tez bağlamı olursa anlamlı (the maintainer'ın hedefleri arasında akademik publish yok).

4. **Rejim-aware sentiment eklemesi**: 2023 seçim/deprem ve 2024 hiperenflasyon anomalileri (Alt-Bölüm 3) Yol 3 LLM context'inde **prompt'a makro rejim bilgisi inject etme** ile çözülmeli — örnek prompt: "Bu KAP açıklamasını yorumlarken bilmen gerekenler: bugün TÜFE [%X], USDTRY [Y], BIST rejim [BULL/BEAR/CRISIS]". Bu, Yol 3'ün FinBERT-TR'ye sektörel avantajıdır.

5. **Anthropic billing dikkat noktası**: the maintainer'ın Pro/Max subscription'ı API'yi kapsamadığı için ayrı bütçe satırı + ayrı Stripe ödeme ayarı gerekli. 15 Haziran 2026 sonrası Claude Code agent SDK kullanımının da ayrı havuza geçeceği unutulmamalı — Yol 3 implementation script'leri **direkt API key** ile çağırılmalı (claude-code agent altında değil) ki bu ayrım net kalsın.

#### Kapanış

Sektör pratiği lensi, akademik kararı **değiştirmiyor** ama **güçlendiriyor**. Yol 3 hem teorik olarak en iyi skor (41/50) hem de saha gözlemiyle uyumlu (4/5). Yol 1 hem akademik (24/50) hem pratik (2/5) zayıf — definite reject. Yol 4 pratisyen pratiğine en yakın ama kalite riski (37/50, 4/5) — fallback rol. Yol 3 MVP 2 hafta + macro-F1 ≥0.75 hurdle'ı kalıyor; sektör perspektifinden eklenen tek koşul: 2024H2 backtest'te rejim-bağımlı performans validasyonu.

**Caveat (önemli)**: Bu yama bölümünün en yüksek epistemic risk'i Alt-Bölüm 2'deki "Türk aracı kurumlarda Türkçe finansal NLP production kullanımı yok" tespitidir — bu absence-of-evidence'dır, evidence-of-absence değil. LinkedIn / Kariyer.net public ilanlarında yok ama (a) brokerlar generic "Data Scientist" başlığı altında işe alıp internal proje olarak çalıştırıyor olabilir, (b) hedge fund / serbest fon tarafında public olmayan deneyimler olabilir. Yol 3 tavsiyesi bu belirsizliğe rağmen güçlü çünkü maliyet düşük (<400 TL/ay düşük senaryo) ve fırsat maliyeti az; **yanılgı durumunda kaybedilen 2 hafta MVP süresi**.