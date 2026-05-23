# BIST OS L4 Sentiment Katmanı Yeniden Mimarisi — Türkçe Finansal NLP Araştırma Raporu

## TL;DR

- **Önerilen yol: Hybrid 3-katmanlı sistem (lexicon ön-filtre → Claude Haiku 4.5 zero/few-shot → manuel review).** "FinBERT-TR" benzeri finans alanına özel bir Türkçe transformer modeli, Hugging Face üzerinde halka açık olarak BULUNAMADI; mevcut `savasy/...` ve `saribasmetehan/...` modelleri film/ürün/Twitter domain'inde eğitilmiştir ve BIST/KAP terminolojisinde tahmin edilemez davranır. En düşük maliyet/risk ile production'a alınacak yaklaşım, ucuz LLM API (Claude Haiku 4.5: $1/$5 per 1M token; Anthropic resmi pricing) + lexicon ön-filtre + batch + prompt cache kombinasyonudur. Gerçekçi aylık API maliyeti: < $5 (~150 TL).
- **Açık alternatif (1-ay yatırım): BERTurk + LoRA + LLM-distillation fine-tune.** ~1.000–5.000 KAP/haber örneği ile `dbmdz/bert-base-turkish-cased` üzerine LoRA adapter eğitilir. Yöntem kanıtı: Kubík, Šuppa & Takáč (IJCNLP-AACL 2025, doi:10.18653/v1/2025.ijcnlp-short.23), Slovak/Malta/İzlanda/Türkçe için BERTurk dahil dört dilde "annotation savings up to 30% and performance improvements up to four F1 score points" raporlamıştır. Aylık marjinal inference maliyeti ~0 TL.
- **Reddedilen yollar:** (1) Trendyol-LLM 7B / Kumru-2B'yi lokal çalıştırmak — 8B sınıfı model >16 GB VRAM ister, finansal benchmark yok; (2) `savasy/bert-base-turkish-sentiment-cased`u doğrudan finansal NLP'de kullanmak — film/ürün domain'inden geliyor; (3) TURNA — non-commercial academic-only lisansı production trading'i yasaklıyor.

## Key Findings

### 1. "FinBERT-TR" public model BULUNAMADI; Türkçe finans-domain transformer kanıt boşluğu vardır

- RESEARCH-016'nın bulgusu doğrulandı: Hugging Face üzerinde "FinBERT-TR" veya finansal Türkçe transformer adıyla eğitilmiş halka açık model yoktur.
- Mevcut Türkçe sentiment modelleri (savasy/bert-base-turkish-sentiment-cased, saribasmetehan/bert-base-turkish-sentiment-analysis, akoksal/bounti, emre/turkish-sentiment-analysis) film/ürün/tweet domain'lerinde eğitilmiş; veri seti Beyazperde sinema yorumları, ürün incelemeleri ve BOUN Twitter veri seti tabanlıdır (savasy README; github.com/akoksal/BERT-Sentiment-Analysis-Turkish).
- **METU yüksek lisans tezi** (Ahmet Şamil Tür, Ocak 2025, "Financial Sentiment Analysis in BIST100 Companies' Annual Reports", Prof. Dr. Onur Yıldırım danışmanlığında, open.metu.edu.tr/bitstream/handle/11511/113400/10565277.pdf) FinBERT (Araci/ProsusAI) ve FinBERT-Yang (yiyanghkust/finbert-tone) modellerini BIST100 yıllık raporlarının **İngilizce versiyonlarında** kullandı. KAP/PDP'nin yapısal sorununu vurguladı: "the absence of structured data poses challenges for data aggregation and analysis… Without standardized tags or XBRL implementation, comparing financial data across different companies becomes more time-consuming and prone to errors." Veri seti: 4.760 rapor / 408.561 sayfa, 99 BIST100 şirketi (Şubat 2023 itibarıyla).
- **Tilburg University MSc tezi** (Batuhan Boztepe, Ağustos 2025, "Methodological Contributions to Textual Sentiment Analysis of Turkish Annual Operating Reviews", Prof. Dr. Lieven Baele danışmanlığında, arno.uvt.nl/show.cgi?fid=187964) FinBERT'in Türkçe'ye doğrudan uygulanamadığını verbatim olarak teyit etti: *"both FinBERT variants are trained solely on English data. This poses challenges in applying them directly to other languages, especially agglutinative ones such as Turkish, where sentiment-rich morphemes can be embedded in highly inflected forms."* Boztepe, Claude Opus 4 / Sonnet 4 ve GPT-4o'yu workaround olarak kullandı, fakat tutarlılık sorunu raporladı: *"To assess the stability of the LLM outputs, the same input combinations for each report-model prompt run 3 to 5 times. Large variations in scores indicated that without enough preprocessing and further constraints, LLM sentiment scoring could lack reproducibility and correctness."* (SAHOL_2021 örneği için 3 koşumda 0.6 / 0.3 / 0.7 skorları). Bu, **self-consistency / ensemble gereksinimini destekleyen doğrudan bir kanıttır**.

### 2. BERTurk ailesi ve Türkçe encoder modelleri olgun, fine-tune edilebilir

- **dbmdz/bert-base-turkish-cased** (Schweter 2020, huggingface.co/dbmdz/bert-base-turkish-cased): 35 GB Türkçe OSCAR + Wikipedia + OPUS + Oflazer korpusu; 44 milyar token üzerinde TPU v3-8 ile 2M adım önceğitim. Yıldırım (2024, arXiv:2401.17396) Türkçe Benchmark veri setinde NER, sentiment, QA ve text classification için fine-tune edilmiş baseline'lar yayınladı; "outperformed other existing baseline approaches".
- **YTÜ Cosmos ailesi** (Kesgin, Yuce, Amasyali 2023, arXiv:2307.14134, "Developing and Evaluating Tiny to Medium-Sized Turkish BERT Models", ytu-ce-cosmos/turkish-{tiny,mini,small,medium,base}-bert-uncased): MIT lisanslı; ~5M–110M params.
- **TURNA** (Uludoğan et al., Findings of ACL 2024, arXiv:2401.14373, github.com/boun-tabi-LMG/TURNA): Boğaziçi TABILAB UL2 encoder-decoder, 1.1B params; **sadece non-commercial academic use** lisansı — production trading sisteminde kullanılamaz.
- **Mukayese benchmark** (Safaya, Kurtuluş, Goktogan, Yuret, Findings of ACL 2022, doi:10.18653/v1/2022.findings-acl.69, github.com/alisafaya/mukayese): 7 Türkçe NLP task baseline'ları; finansal subset yoktur.
- **Cross-validation çalışması** (Springer LRE 2025, doi:10.1007/s10579-025-09869-6, arXiv:2412.05964): BERTurk + Bounti binary F1 0.75; XLM-T 0.92; TurkishBERTweet (894M tweet öneğitim) 0.86. Hiçbir benchmark finansal değildir.

### 3. Türkçe finansal sentiment akademik literatür: çoğunlukla Twitter ve LSTM tabanlı

- **Sevinç (2025)** "Predicting Borsa Istanbul Banking and Finance Stocks Using Turkish Social Media Sentiment", Springer "Machine Learning in Finance" Bölüm 9, doi:10.1007/978-3-031-83266-6_9: SPK manipülasyon tespit edilen banka/finans hisseleri için Twitter + Investing.com yorumları üzerinde LSTM + CNN; "the most successful models are LSTM and CNN, achieving the highest predictive accuracy when Twitter sentiment is combined with the suspicious score." Spesifik accuracy yüzdeleri Springer paywall arkasındadır.
- **Atak (2023)** "Exploring the sentiment in Borsa Istanbul with deep learning", *Borsa Istanbul Review*, doi:10.1016/j.bir.2023.12.010, sole author Alev Atak (METU İktisat): BIST 1998–2022 yıllık raporları üzerinde FinBERT ve FinRoBERTa keyword'lü transformer sentiment indeksi, system-GMM ile bilgi asimetrisi ölçümü; **TÜBİTAK 118C-199 desteklidir**. Korpus paylaşılmamıştır.
- **Kilimci (2020, Gazi/Kocaeli, IEEE)**: KAP + Mynet Finans + Bigpara + Twitter kombine veri seti, BIST100 yön tahmini için word embedding + deep ensemble.
- **MDPI Applied Sciences 14/2/588 (2024)** "Comparative Study for Sentiment Analysis of Financial Tweets with Deep Learning Methods", Borsa İstanbul Twitter sentiment.
- **DergiPark "Stacking Sentiment Models on BIST30"** (dergipark.org.tr/en/download/article-file/4033236): LSTM+BERT+Naive Bayes+SVM ensemble.
- **TurkSentGraphExp** (Kılıç & Tulu, PeerJ CS 2729, 2025, Adana Alparslan Türkeş ÜTÜ): graph-aware explainable Türkçe sentiment.
- **2024 ScienceDirect S2214845025001024** (Türkiye 2015–2024 haber + tweet + BIST trend).
- **Ana boşluk:** Production'a alınabilir, etiketlenmiş, BIST/KAP-spesifik halka açık Türkçe finansal sentiment dataset BULUNAMADI. En yakını mehmetbugrakara/Turkish-financial-news-sentiment-analysis (GitHub, BloombergHT scraper'lı, etiketsiz pipeline) ve elifbeyzatok00/Sentiment-Analysis-and-Topic-Extraction-in-Turkish-Texts.

### 4. LLM zero-shot finansal sentiment akademik olarak doğrulandı, BIST için kanıt sınırlı

- **Lopez-Lira & Tang** (arXiv:2304.07619, son revizyon Ekim 2025, Univ. of Florida): GPT-4 başlık-bazlı sentiment, post-knowledge-cutoff veride yaklaşık **%90 portfolio-day hit rate**. Verbatim sonuç: *"a self-financing strategy that buys stocks with a positive ChatGPT 4 score and sells those with a negative score delivers the highest Sharpe ratio of 3.28 over our sample period, compared to 1.79 for GPT-3.5."* Drift-specific Sharpes: 2.97 (overnight news) ve 2.63 (intraday news). Önemli uyarı: LLM yayılımı arttıkça stratejinin yıllık Sharpe oranı 6.54 (2021Q4) → 1.22'ye (Ocak–Mayıs 2024) düştü.
- **Fatouros, Soldatos, Kouroumali, Makridis & Kyriazis** "Transforming sentiment analysis in the financial domain with ChatGPT", *Machine Learning with Applications* 14, 100508 (2023), arXiv:2308.07935: ChatGPT-3.5 forex haber sentiment'inde *"exhibited approximately 35% enhanced performance in sentiment classification and a 36% higher correlation with market returns"* FinBERT'e kıyasla.
- **AD-FCoT** (arXiv:2509.12611, 2025): Few-shot + domain-knowledge chain-of-thought, finansal sentiment'te Few-Shot baseline'a göre +0.22pp accuracy artışı.
- **Shen & Zhang** (arXiv:2410.01987, "Financial Sentiment Analysis on News and Reports Using LLMs and FinBERT"): Zero-shot ve few-shot prompt mühendisliği avantajları doğrulandı.
- **Sean Dearnaley quantize'lı LLaMA 3 8B benchmark**: Özel system prompt + 5-shot örnek ile 4 quantization seviyesinde "100% success rate in generating valid JSON" raporlandı.

### 5. Claude API fiyatlandırması (Mayıs 2026, çapraz-doğrulanmış)

Anthropic resmi pricing sayfasından (platform.claude.com/docs/en/about-claude/pricing) Nisan–Mayıs 2026 itibarıyla, altı bağımsız 3. taraf kaynakla (CloudZero, Finout, BenchLM.ai, MetaCTO, EvoLink, SiliconData) tutarlı şekilde doğrulanan:

| Model | Input ($/1M tok) | Output ($/1M tok) | Context |
|---|---|---|---|
| Claude Opus 4.7 (16 Nisan 2026'da yayınlandı) | $5.00 | $25.00 | 1M tok (flat) |
| Claude Sonnet 4.6 | $3.00 | $15.00 | 1M tok (flat) |
| Claude Haiku 4.5 | $1.00 | $5.00 | 200K tok |

- **Batch API:** "processes requests asynchronously within 24 hours at exactly 50% off all Anthropic Claude API pricing tokens" (CloudZero, Finout doğrulamalı).
- **Prompt caching:** "up to 90% cost savings on cached input tokens"; cache hit ~%10 standart input rate, cache write ~1.25×.
- **Stacking:** Batch + cache ile standart fiyatın ~%5'ine inilebilir.
- **US data residency:** 1.1× çarpan (global default ucuz).
- **Opus 4.7 tokenizer uyarısı:** "may generate up to 35% more tokens for the same input text" Opus 4.6'ya kıyasla.

### 6. Türkçe LLM alternatifleri lokal/self-hosted — değerlendirme

- **Trendyol-LLM-7B-chat-v4.1.0** (huggingface.co/Trendyol/Trendyol-LLM-7B-chat-v4.1.0): Qwen2.5-7B üzerine 13B token continued pretraining ("based on Trendyol LLM base v4.0… continued pretraining version of Qwen2.5 7B on 13 billion tokens"). Apache-2.0. Ana use case e-commerce (ürün açıklama, kategori tespiti, RAG, persona). Finansal benchmark BULUNAMADI. Aylık ~33 indirme.
- **VNGRS-AI/Kumru-2B** (Türker, Arı, Han, Ekim 2025; huggingface.co/vngrs-ai/Kumru-2B): 2B params, Mistral-family decoder-only, *"pre-trained on a cleaned, deduplicated corpora of 500 GB for 300B tokens, and supervised fine-tuned on 1M examples."* Custom Türkçe BPE tokenizer (50.176 vocab), 8.192 context, Apache-2.0. Geliştirici iddiası: Cetvel Türkçe benchmark'ta *"Kumru overall surpasses significantly larger models such as LLaMA-3.3–70B, Gemma-3–27B, Qwen-2–72B and Aya-32B"* — bağımsız doğrulanmış değildir. Aylık ~1.107 indirme; en aktif Türkçe açık model.
- **TURNA**: non-commercial academic-only.
- **YTÜ Turkish-Gemma-9b-T1**: Gemma-9B Türkçe instruct fine-tune; reasoning odaklı.

**Çıkarım:** 500K TL retail ölçekte 7–9B lokal LLM inference (16+ GB VRAM, RTX 4090 sınıfı GPU + ~700 W) maliyetli ve performansı belirsizken Claude Haiku 4.5 ile aylık <$2 maliyet (orta senaryo) elde edilebilir.

## Details

### Bölüm 1 — Türkçe finansal NLP literatürü derinleştirme

#### A. BERTurk finansal uygulamalar
- Yıldırım (2024, arXiv:2401.17396) — sentiment, NER, QA, classification baseline; finansal domain yok.
- METU (Tür, Ocak 2025) ve Tilburg (Boztepe, Ağustos 2025) tezleri BERTurk değil **İngilizce FinBERT'i** kullandı; her ikisi de Türkçe finansal sentiment için "structured public dataset" eksikliğini vurguladı.
- BIST sentiment'inde çoğunluk LSTM / klasik ML (Kilimci, Sevinç 2025); transformer fine-tune yalnızca Atak (2023) İngilizce yıllık raporlarda.

#### B. Türk üniversite NLP grupları (son 3-5 yıl, kanıt-bazlı)
- **Boğaziçi TABILAB (Arzucan Özgür):** Mutlu & Özgür (arXiv:2205.04185) Türkçe targeted sentiment dataset & BERT modelleri; TURNA (Uludoğan et al., Findings ACL 2024).
- **Yıldız Teknik COSMOS (Amasyali):** Cosmos tiny/mini/small/medium/base BERT; Turkish-Gemma-9b; Turkish-ColBERT — 2023–2025; MIT lisans.
- **Kocaeli/Gazi (Kilimci):** BIST100 word embedding + deep ensemble (2020); Twitter sentiment.
- **Koç / Mukayese (Yuret, Safaya):** Mukayese benchmark.
- **METU İktisat (Atak):** Borsa Istanbul Review 2023 transformer sentiment; TÜBİTAK 118C-199.
- **Adana Alparslan Türkeş ÜTÜ (Kılıç, Tulu):** TurkSentGraphExp PeerJ CS 2729 (2025).
- **Anadolu Üniversitesi (Sevinç):** Twitter + CMB manipülasyon sentiment 2025.
- **VNGRS-AI (Türker, Arı, Han):** Kumru-2B (Ekim 2025) — endüstri NLP, açık kaynak.

#### C. KAP/BIST sentiment akademik makaleler (kanıt-bazlı liste)
- Tür (METU 2025) — İngilizce BIST raporlar, FinBERT karşılaştırma.
- Atak (Borsa Istanbul Review 2023) — Türkçe yıllık raporlar, transformer + system-GMM.
- Sevinç (Springer 2025) — Twitter + LSTM/CNN, CMB manipülasyon hisseleri.
- Kilimci (2020) — KAP + Mynet + Bigpara + Twitter ensemble.
- MDPI 14/2/588 (2024); DergiPark Stacking BIST30; ScienceDirect S2214845025001024.

#### D. Türkçe finansal sentiment dataset durumu

| Dataset | Boyut | Domain | Lisans | Erişim |
|---|---|---|---|---|
| winvoker/turkish-sentiment-analysis-dataset | ~493K cümle, 3 sınıf | Karma (wiki, ürün) | CC-BY-SA-4.0 | HF, public |
| akoksal/bounti | BERTurk fine-tune + BOUN tweets | Tweet | model card | HF |
| Beyazperde / Demirtaş & Pechen | 10K+ örnek | Film, ürün | akademik | github.com/savasy |
| **TR-FinSent / KAP-corpus / BIST-news** | — | Finans (BIST-spesifik) | — | **BULUNAMADI** |
| Atak (BIR 2023) korpusu | BIST 1998–2022 yıllık raporlar | Finans | TÜBİTAK projesi | Paylaşılmamış |
| Sevinç (2025) Twitter/Investing | n/a | Banka/finans | Springer paywall | Paylaşılmamış |
| mehmetbugrakara/Turkish-financial-news-sentiment-analysis | etiketsiz pipeline | BloombergHT | MIT | GitHub |

### Bölüm 2 — Mevcut Türkçe modeller karşılaştırması

| Model | Params | Domain | Lisans | Yorum |
|---|---|---|---|---|
| dbmdz/bert-base-turkish-cased | 110M | Genel | MIT | Türkçe NLP standardı; fine-tune için temel |
| dbmdz/bert-base-turkish-uncased | 110M | Genel | MIT | Aksanlı karakter sorunlarına dikkat |
| savasy/bert-base-turkish-sentiment-cased | 110M | Film/ürün | model card | %95+ ama finans değil |
| saribasmetehan/bert-base-turkish-sentiment-analysis | 110M | Wiki/karma | n/a | winvoker dataset ile fine-tune, %95.4 |
| akoksal/bounti | 110M (BERTurk-128k uncased) | Tweet | n/a | Twitter spesifik |
| akdeniz27/turkish-distilbert-pre-finetuned-for-sentiment | ~66M | Genel | n/a | Daha hızlı, daha az doğru |
| ytu-ce-cosmos/turkish-base-bert-uncased | ~100M | Genel | MIT | YTÜ Cosmos |
| ytu-ce-cosmos/turkish-tiny-bert-uncased | ~5M | Genel | MIT | CPU-friendly |
| TURNA (boun-tabi-LMG) | 1.1B | Genel encoder-decoder | **Non-commercial academic** | Production'a uygun **DEĞİL** |
| Trendyol-LLM-7B-chat-v4.1.0 | 8B (Qwen2.5) | E-commerce | Apache-2.0 | Lokal kullanım için ağır |
| VNGRS-AI/Kumru-2B | 2B (Mistral) | Genel + B2B | Apache-2.0 | En umutlu açık; finansal benchmark yok |
| ytu-ce-cosmos/Turkish-Gemma-9b-T1 | 9B | Genel + reasoning | Gemma lisansı | Reasoning odaklı |

**Sentiment fine-tune için seçim: `dbmdz/bert-base-turkish-cased` + LoRA** — geniş literatür, MIT, küçük params, kanıtlanmış pipeline (akdeniz27/bert-base-turkish-cased-ner-lora).

### Bölüm 3 — Domain-specific fine-tuning fizibilite

#### Veri ihtiyacı
- **Few-shot adapter literatürü** (Pfeiffer et al. 2020) 500–1.000 etiketli örnekle başlangıç önerir.
- **LoRA Türkçe için doğrulanmış:** Kubík, Šuppa, Takáč (IJCNLP-AACL 2025, doi:10.18653/v1/2025.ijcnlp-short.23), Slovak/Malta/İzlanda/Türkçe için BERTurk dahil dört dil üzerinde Active Learning + LoRA ile **"annotation savings up to 30% and performance improvements up to four F1 score points"** raporladı (genel sonuç; spesifik Türkçe alt-sayılar yayınlanmış abstract'tan ayrıştırılamamıştır).
- **akdeniz27/bert-base-turkish-cased-ner-lora**: PEFT/LoRA ile BERTurk üzerinde NER fine-tune kanıtlanmış pipeline — 702K trainable params (toplamın %0.64'ü), batch 16, lr=1e-3, 7 epoch.
- **Inter-annotator agreement:** Cohen's kappa ≥0.7 hedef.

#### Manuel etiketleme tahmini
- Günde 200–300 KAP başlığı/haber özeti etiketlenebilir. 1000 örnek ≈ 4–5 iş günü; 5000 örnek ≈ 3–4 hafta.
- 2 annotatör + adjudicator → maliyet 2.5x.

#### Weak supervision alternatifleri
- **Snorkel-style labeling functions:** KAP kategorisi → ön label; finansal anahtar kelimeler → güçlendirme.
- **Distant supervision:** t+1 günlük getiri >+%2 → pozitif; <-%2 → negatif. 10K+ örnek üretebilir, gürültülü.
- **LLM-distillation:** Claude Sonnet/Opus ile 5–10K KAP başlığını etiketle, sonra BERTurk'ü bu etiketlerde fine-tune et. **Önerilen ana yol.**

#### Compute gereksinimi
- BERTurk base (110M) + LoRA (≤2M trainable): Colab Pro T4 GPU ile 1000 örnek × 5 epoch ≈ 20–40 dk.
- Full fine-tune: T4'te bir epoch ≈ 5–10 dk (1000 örnek). A100 ile 5x hızlı.
- 5000 örnek + full FT + A100 (Colab Pro+): toplam 2–4 saat, ≈ $5–15.

#### Senaryolar
| Senaryo | Süre | Veri | Compute | Beklenen accuracy |
|---|---|---|---|---|
| 1-hafta MVP | 5 iş günü | 500–1000 LLM-distilled label | Colab Pro | %72–78 |
| 1-ay tam | 3–4 hafta | 5000 manuel + 10K weak | Colab Pro+ / RTX 4090 | %80–85 |
| 3-ay research | 12 hafta | 50K + domain pretraining | A100 cloud | %85–90 |

### Bölüm 4 — LLM-based alternatif (Claude/GPT zero-shot)

#### Maliyet senaryoları (Claude Haiku 4.5, $1 input / $5 output)
1 çağrı ≈ 800 token input + 100 token output.
- **Düşük (1500 çağrı/ay):** 1.2M in + 0.15M out = $1.95/ay standart; **$0.98/ay batch'le** (~30 TL).
- **Orta (6000 çağrı/ay):** 4.8M + 0.6M = $7.80/ay; batch ile $3.90/ay (~130 TL).
- **Yüksek (7500 çağrı/ay):** 6M + 0.75M = $9.75/ay; batch ile $4.88/ay (~163 TL).
- **Sonnet 4.6 ile orta:** ~$23/ay standart, $12/ay batch.
- **Prompt caching ile:** System prompt + few-shot örnekleri sabit ise input %90 indirim. 6000 çağrı/ay gerçekçi maliyet **<$2/ay** (~60 TL) Haiku ile.

**Sonuç:** 500K TL portföy ölçeğinde LLM API maliyeti ihmal edilebilir mertebededir.

#### Prompt engineering pattern'ları
1. **Sistem promptu Türkçe:** "Sen Türkçe finansal haber sentiment uzmanısın. Her başlık için: (1) etkilenen şirket(ler), (2) sentiment -1.0..+1.0, (3) güven 0..1, (4) 1 cümlelik gerekçe. Sadece JSON döndür."
2. **Few-shot örnekleri (3–5):** Kâr açıklama, KAP olağandışı olay, hisse geri alım, temettü, halka arz, SPK soruşturması.
3. **Structured output:** Claude tool_use ile %100 valid JSON garanti (Dearnaley LLaMA 3 8B sonucu da bunu doğrular).
4. **CoT:** AD-FCoT küçük kazanım sağlar; opsiyonel.

#### Self-consistency
- Wang et al. 2022: 3-5 yanıt çoğunluk oyu, accuracy ~%2-5 iyileşir.
- **Önerim:** Default temperature=0.0 + n=1; sadece composite skoru üst/alt decile için 3-koşumlu self-consistency tetiklensin.

#### Doğrulanmış akademik çalışmalar
- Lopez-Lira & Tang: GPT-4 long-short Sharpe **3.28** vs GPT-3.5 **1.79**; drift Sharpes 2.97/2.63; LLM yayılımı ile 6.54→1.22 düşüş.
- Fatouros et al. (2023, ML with Applications 100508): ChatGPT-3.5 vs FinBERT *"approximately 35% enhanced performance in sentiment classification and a 36% higher correlation with market returns"*.
- AD-FCoT (2025): domain-knowledge CoT küçük katkı.
- Boztepe (Tilburg 2025): Türkçe LLM tutarsızlığı kanıtı, variance kontrolü zorunlu.

### Bölüm 5 — Hybrid yaklaşım tasarımı (ÖNERİLEN MİMARİ)

#### Tier 1: Lexicon-based hızlı filter
- **Sözlük kaynağı:** Loughran-McDonald master dictionary (sraf.nd.edu/loughranmcdonald-master-dictionary/) Türkçe çevirisi (~3500 kelime; MT + manuel review 1-2 gün) + Türkçe finansal kelimeler (rekor, zarar, iflas, konkordato, halka arz, geri alım, temettü, kâr/ciro artışı/azalışı, soruşturma, manipülasyon, sermaye artırımı, vb.) ağırlıklı toplam.
- **Eşik:** |skor| > 1.0 → kesin; 0.3 < |skor| ≤ 1.0 → ambiguous → Tier 2; |skor| ≤ 0.3 → neutral.
- **Maliyet:** ~0 TL.
- **Accuracy beklentisi:** 70–75% (literatür baseline). Haberlerin %50-60'ını filtreler.

#### Tier 2: LLM-based detailed sentiment
- Yalnızca Tier 1 ambiguous + yüksek-kararlılık gereken haberler (~300–500 çağrı/ay).
- Claude Haiku 4.5 default; high-conviction subset için Sonnet 4.6 fallback.
- Structured JSON + few-shot prompt + prompt caching.
- **Aylık maliyet < $2** (orta senaryo; batch + cache ile).

#### Tier 3: Manuel review
- Sadece composite signal üst/alt decile (top-3 buy / bottom-3 sell günde) için trader 1-2 dk gözden geçirir.
- Audit log, sonraki ay LLM prompt iyileştirme için "hard examples" haline.

#### Hybrid sistem değerlendirmesi
- **Accuracy beklentisi:** %80–88 (Boztepe LLM aralığı + lexicon ön-filtre).
- **Latency:** Tier 1 ~10 ms/haber; Tier 2 ~2-4 sn. Gün-sonu batch + intraday alarm için yeterli; sub-saniye HFT için değil.
- **Failure modes:** Lexicon ironi/negation; LLM halüsinasyon; Türkçe morfolojik ek kayıpları.
- **Mitigation:** Negation regex; LLM prompt'unda "şirket adı tam eşleşmeli" kısıtı; daily cross-check.

### Konkrete implementation (Python pseudo-code)

```python
# pip install pandas requests anthropic transformers torch
import json, re, pandas as pd
from anthropic import Anthropic

LEXICON = {
    "rekor": +1.5, "kâr": +1.2, "büyüme": +1.0, "temettü": +0.8,
    "geri alım": +0.7, "halka arz": +0.3, "anlaşma": +0.5,
    "zarar": -1.2, "iflas": -2.0, "konkordato": -2.0, "soruşturma": -1.5,
    "manipülasyon": -1.8, "düşüş": -0.8, "ihraç": -0.5, "suspended": -1.0,
}
NEGATION_RE = re.compile(r"(değil|olmadı|yalanla|reddet|iptal|sona erdi)")

def tier1_score(text: str):
    t = text.lower(); score, hits = 0.0, []
    for w, v in LEXICON.items():
        n = len(re.findall(rf"\b{re.escape(w)}\w*\b", t))
        if n:
            mod = -1 if NEGATION_RE.search(t[:200]) else 1
            score += n * v * mod
            hits.append((w, n, v*mod))
    return score, hits

ANTHROPIC = Anthropic()
SYSTEM = ("Sen Türkçe finansal haber sentiment uzmanısın. "
          "Her başlık için JSON döndür: "
          "{'company': str, 'ticker': str, 'sentiment': float -1..1, "
          "'confidence': float 0..1, 'rationale': str}. Sadece JSON üret.")
FEW_SHOT = [
    {"role":"user","content":"Garanti BBVA 3Ç25 net karı %42 arttı, beklenti üstü."},
    {"role":"assistant","content":'{"company":"Garanti BBVA","ticker":"GARAN","sentiment":0.85,"confidence":0.92,"rationale":"Beklenti üstü kar artışı"}'},
    {"role":"user","content":"SPK Aselsan hisselerinde manipülasyon soruşturması başlattı."},
    {"role":"assistant","content":'{"company":"Aselsan","ticker":"ASELS","sentiment":-0.7,"confidence":0.85,"rationale":"Regülatör soruşturması itibar/değer riski"}'},
]

def tier2_llm(text: str) -> dict:
    msg = ANTHROPIC.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=200,
        system=[{"type":"text","text":SYSTEM,"cache_control":{"type":"ephemeral"}}],
        messages=FEW_SHOT + [{"role":"user","content":text}],
        temperature=0.0,
    )
    try: return json.loads(msg.content[0].text)
    except: return {"sentiment":0.0,"confidence":0.0,"rationale":"parse_error"}

def hybrid_sentiment(text: str) -> dict:
    s, hits = tier1_score(text)
    if abs(s) > 1.0:
        return {"source":"tier1","sentiment":max(-1,min(1,s/2.0)),"confidence":0.7,"hits":hits}
    elif abs(s) <= 0.3:
        return {"source":"tier1","sentiment":0.0,"confidence":0.5,"hits":hits}
    else:
        r = tier2_llm(text); r["source"]="tier2"; r["tier1_hits"]=hits; return r
```

### Son karşılaştırma matrisi

| Boyut | 1-Hafta MVP (Hybrid + Haiku) | 1-Ay Tam (BERTurk LoRA + Hybrid) | 3-Ay Research (Domain pretrain) |
|---|---|---|---|
| Geliştirme süresi | 30–40 saat | 100–120 saat | 250–350 saat |
| Veri ihtiyacı | Lexicon (~500 kelime) + 50 eval | 1000 manuel + 4000 weak-sup | 10K manuel + 50K weak + corpus |
| Compute | Yok | Colab Pro+ ~$50 | A100 saat ~$300-500 |
| API maliyeti | <$5/ay | <$2/ay | <$1/ay (backstop) |
| Beklenen accuracy | %75–82 | %82–88 | %85–92 |
| Maintenance | Düşük | Orta (6 ayda 1 FT) | Yüksek |
| Genişletilebilirlik | Çok yüksek (LLM swap) | Yüksek | Veri set bağımlı |
| Risk | Düşük | Düşük-orta | Orta-yüksek |
| **Tavsiye** | **Faz 1 (zorunlu)** | **Faz 2 (3-6 ay sonra)** | **Faz 3 (ROI gözlemlenirse)** |

### Önerilen yol için SPEC taslağı

**Hedefler / Success criteria:**
- L4 Sentiment composite skoru, t+5 günlük BIST30 cross-sectional return ile aylık Spearman korelasyon ≥0.10 (literatür: 0.06–0.15).
- LLM hallucination rate <%5 (haftalık manuel kontrol).
- Aylık API maliyeti <300 TL.
- Tier-1 filter coverage: ≥%50.

**Mimari (textual):**
```
[KAP feed/yfinance/EVDS news adapter]
            ▼
[Preprocess: dedupe, lang detect, headline extract]
            ▼
[Tier 1: Lexicon scorer]──►(|s|>1.0 veya |s|≤0.3)──► sentiment_v
            │                                       │
            ▼ (0.3<|s|≤1.0)                         │
[Tier 2: Claude Haiku 4.5 + cache]── sentiment_v ◄──┘
            ▼
[Composite L4 → Portfolio Manager (Claude Opus 4.7)]
            ▼ (üst/alt decile)
[Tier 3: Manuel veto/onay]
            ▼
[Trade execution + audit log]
```

**Test stratejisi:**
- Altın set: 200 KAP başlığı, 2 annotatör, Cohen's kappa ≥0.7.
- Backtest: 2023–2025 historik haber + getiri, t+1/t+5 korelasyon.
- A/B: 4 hafta L4-on vs L4-off paper-trade, t-test Sharpe.
- Ablation: Tier 1-only vs hybrid vs LLM-only.

**Rollout plan:**
- Hafta 1–2: Geliştirme + altın set + backtest.
- Hafta 3: Canary paper-trade, manuel onay tüm trade'lerde.
- Hafta 4–5: Portföy %25'ine kadar sentiment ağırlığı.
- Hafta 6–8: Tam ölçek (≤500K TL retail).

## Recommendations

**Faz 1 (1 hafta, hemen başla):**
1. **Hybrid Tier-1 + Tier-2 sistemini yukarıdaki kodla inşa et.** Loughran-McDonald master listesini DeepL/Claude ile Türkçeye çevir + el ile gözden geçir (~6-8 saat). KAP'a özgü kalıpları ekle.
2. **Claude Haiku 4.5'u Anthropic Batch + prompt caching ile entegre et.** Beklenen aylık maliyet <$2.
3. **Altın test seti (200 başlık) oluştur, eşikleri (|s|>1.0, 0.3<|s|≤1.0) bu sette tunable yap.**
4. Lopez-Lira-style backtest 2023–2025 BIST30 haber + getiri.

**Faz 2 (3-6 ay sonra, Faz 1 ROI veriyorsa):**
1. **BERTurk + LoRA distillation:** Önceki ayların Tier-2 LLM çıktısını (~5–10K etiketli örnek) ground truth alıp `dbmdz/bert-base-turkish-cased` üzerine LoRA fine-tune et. Inference maliyetini sıfıra düşür.
2. **Active learning loop:** Tier-1 ↔ Tier-2 uyumsuzluklarını manuel re-label kuyruğuna ekle.

**Faz 3 (12+ ay, opsiyonel):**
1. KAP corpus üzerinde BERTurk domain-adaptive pretraining (MLM).
2. Multi-task: sentiment + entity (şirket/sektör) + olay tipi.

**Eşikleri değiştirecek benchmark'lar:**
- Aylık Spearman korelasyon <0.05 düşerse → Sonnet 4.6'ya yükselt veya prompt revize.
- API maliyet >500 TL/ay → Tier-1 eşiklerini sıkılaştır, cache hit rate incele.
- Hallucination >%10 → Tier-3 manuel oranı artır, tool_use ile structured zorla.
- Lopez-Lira "Sharpe declining" benzeri gözlem (BIST'te yıllık Sharpe <1.0) → sentiment'i alpha yerine risk-azaltıcı sinyal olarak kullan.

## Caveats

1. **"FinBERT-TR" gibi finans-spesifik bir Türkçe transformer halka açık olarak BULUNAMADI.** Tüm tartışma genel-amaçlı BERTurk ve film/ürün sentiment modelleri etrafında.
2. **Halka açık, BIST'e uygun etiketli Türkçe finansal sentiment veri seti YOK.** Atak (2023, TÜBİTAK 118C-199) ve Sevinç (2025) korpusları paylaşılmamıştır.
3. **Lopez-Lira "Sharpe declining" sonucu (6.54→1.22, ABD piyasası, 2021Q4→2024 Oca-May).** BIST'te benzer alpha-erozyonu olası; sentiment'i alpha yerine risk-azaltıcı filtre olarak kullanmak daha uzun ömürlüdür.
4. **Boztepe (Tilburg 2025) Türkçe için LLM tutarsızlık problemi belgelendi** (aynı girdide 0.6/0.3/0.7). Production'da temperature=0.0 + structured tool_use + occasional self-consistency şart.
5. **Atak (2023) ve Sevinç (2025) korpusları paywall arkasında**; replikable değil; kanıt yalnızca abstract/metodoloji düzeyinde.
6. **Trendyol-LLM ve Kumru-2B'nin finansal benchmark performansı yayımlanmamıştır.** Geliştiricilerin Cetvel'de büyük modelleri geçtiği iddiası bağımsız doğrulanmadı.
7. **TURNA non-commercial academic only lisansı** retail trading sisteminde kullanılamaz.
8. **Claude API resmi pricing sayfası direkt fetch'te yanıt vermedi**; rakamlar 6 farklı 3. taraf kaynaktan (CloudZero, Finout, BenchLM, MetaCTO, EvoLink, SiliconData; Nisan–Mayıs 2026) tutarlı doğrulandı. Uygulama öncesi resmi sayfa kontrol edilmeli.
9. **Opus 4.7 tokenizer'ı Türkçe için %35'e kadar daha fazla token üretebilir** — Sonnet 4.6 / Haiku 4.5'a default kalmak güvenli.
10. **Risk-free rate %37 (TCMB, 22 Ocak 2026 PPK kararı ile %38'den %37'ye indirim; Mart 2026 toplantısında sabit tutuldu)** ortamında küçük Sharpe kazanımları retail için anlamsız olabilir. L4 sentiment'in iş gerekçesi yalnızca alpha değil, aynı zamanda **yanlış-pozisyon riskinden korunma** (SPK soruşturması, konkordato başvurusu erken yakalama) olmalıdır.
11. **Kubík et al. IJCNLP-AACL 2025 sonuçları çok-dilli aggregate** ("up to 30% annotation savings, up to four F1 points improvement"); Türkçe BERTurk için spesifik kazanım yayınlanmış abstract'tan ayrıştırılamaz, fine-tune ROI tahmini bu nedenle bantlı verilmiştir.