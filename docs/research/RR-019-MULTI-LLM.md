---
report_id: RR-019
title: "Multi-LLM Orchestration — Sentio İçin AI Jüri Sistemi"
last_updated: 2026-05-24
phase_position: "Phase 6+ (Q1 2027+)"
priority: "Nice-to-have, NOT must-have"
status: "Araştırma + Tasarım (implementation bekler)"
predecessors: [RR-010, RR-011, RR-012, RR-013, RR-015, RR-016, RR-017, RR-018]
---

# RR-019: Multi-LLM Orchestration — Sentio İçin AI Jüri Sistemi

> **Snapshot:** Mayıs 2026. LLM landscape 3–6 ayda değişir. Bu raporu son revize tarihi için header'daki `last_updated` alanına bak. Yeni model çıktığında veya fiyat değiştiğinde tablolar geçersizleşir.

---

## 1. TL;DR

**Hedef Okuyucu:** Şu anki maintainer (Phase 5 sonu, RR-018 backtest framework var). Bu özetin amacı, "RR-019'u bugün uygulamam gerekir mi?" sorusuna net cevap vermek.

- **Konum:** Phase 6+ (Q1 2027+, uzak zaman). AUM 500K TL ve junior quant pozisyon eşiğine gelene kadar **incremental katkıdır**. Bugün uygulanmaz; bugün **sadece araştırma + tasarım** olarak rafa kaldırılır.
- **Öneri:** "7-agent ideal ama 2-LLM pratiktir." TradingAgents (Xiao et al. 2024, arXiv:2412.20138) v7 mimarisi (7 specialist agent + Bull/Bear debate + Risk team) hedef retail butceyi ($20/ay) asar; pratik MVP **2-LLM jüri**: Claude Opus 4.7 (Bull advocate) + GPT-5.4 (Bear advocate), disagreement-aware position sizing ile.
- **Asıl alpha kaynağı değildir.** RR-010 (Smart Money), RR-012 (EM faktörler), RR-017 (HMM Regime) ana alpha taşıyıcılarıdır. RR-019 katkısı: **kalibrasyon iyileştirmesi + drawdown koruma**, çünkü iki LLM güçlü çelişkide pozisyon sıfırlanır (Du et al. 2023 multiagent debate: arXiv:2305.14325).
- **Maliyet sınırı:** 2-LLM MVP ham fiyatla ~$3.60/ay; RR-011 L4 Sentiment (~$10/ay) ile birleşik ~$13.60/ay (cache'siz yüksek tarafta $20'yi zorlar) → **prompt caching + selective debate** ile $11–14/ay'a indirilir (Anthropic %90 cache read indirimi, doğrulanmış kaynak: platform.claude.com/docs).
- **Şimdi yapılacak:** Sadece bu raporu referans olarak sakla. Türkçe finansal context test framework (Bölüm 4) arastirma katmani-deliverable seviyesinde hazır; AUM eşiği aşıldığında ilk iş test seti üretmek olur.

---

## 2. Akademik Temel Özeti

**Hedef Okuyucu:** Gelecekteki maintainer / arastirma katmani. Bu bölüm Multi-LLM yaklaşımının niçin alpha ürettiğine dair literatürün özeti — implementation kararı vermeden önce okunması zorunlu.

### 2.1 Multiagent Debate (MAD)

Du, Li, Torralba, Tenenbaum, Mordatch (2023) — **"Improving Factuality and Reasoning in Language Models through Multiagent Debate"** (arXiv:2305.14325, ICML 2024). Birden fazla LLM örneğinin yanıtlarını birbirine sunup birkaç tur tartışmasının matematik, strateji ve gerçeklik (factuality) görevlerinde performansı belirgin şekilde artırdığını gösterdi. Spesifik kanıt: aritmetik görevlerde multi-agent debate **%81.8 doğruluk vs. tek-ajan %67.0**; GSM8K matematik benchmark'unda **%85.0 vs. tek-ajan %77.0** (Du et al. ICML 2024). Yöntem black-box: model loglarına gerek yok, sadece API çıktıları yeterli. Bu RR-019 için temel motivasyondur: iki bağımsız LLM'in çıktısı tek LLM'inkinden daha kalibre edilmiştir.

Liang, He, Jiao ve diğerleri (2023/2024) — **"Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate"** (arXiv:2305.19118, EMNLP 2024). Tek LLM'in kendisini denetlemesinin "Degeneration-of-Thought" (DoT) probleminden muzdarip olduğunu, çoğul ajanlı "tit-for-tat" tartışmanın bunu kırdığını gösterdi. BIST için anlamı: Claude Opus'un tek başına ürettiği bullish bias, ikinci bir bear-advocate LLM tarafından kırılabilir.

### 2.2 Disagreement-Aware Uncertainty Quantification

Jiang (2026) — **"DiscoUQ: Structured Disagreement Analysis for Uncertainty Quantification in LLM Agent Ensembles"** (arXiv:2603.20975). 5-ajanlı sistemde DiscoUQ-LLM yöntemi AUROC 0.802 ile baseline "LLM Aggregator" (0.791) üzerinde, ECE (Expected Calibration Error) 0.036 vs. 0.098 — **iki kat daha iyi kalibre edilmiş güven skorları**. Anahtar bulgu: ajanların ne kadar anlaştığı değil, **nasıl anlaşmadığı** (kanıt örtüşmesi, argüman gücü, sapma derinliği) sinyal taşır. RR-019 başlangıçta basit vote-counting kullanacak; ileride DiscoUQ benzeri yapılandırılmış uyuşmazlık analizine geçebilir.

Kadavath et al. (2022) — **"Language Models (Mostly) Know What They Know"** (arXiv:2207.05221). Büyük LLM'lerin kendi P(True) skorlarını üretebildiği ve bunların makul kalibrasyon gösterdiği — yani LLM'lerden kendi güven skorlarını sözel olarak istemek kullanılabilir bir sinyaldir. RR-019 prompt tasarımı bu bulguya dayanır: her LLM çıktısı `{sentiment, confidence: HIGH/MEDIUM/LOW, reasoning}` JSON şemasında olacak.

Lin, Hilton, Evans (2022) — **"Teaching Models to Express Their Uncertainty in Words"** (arXiv:2205.14334). GPT-3'ün doğal dilde ("90% confidence", "high confidence") kalibre güven ifade edebildiğini gösterdi; verbalized probability vs. logit-based probability karşılaştırması. Sentio için: token-cost açısından verbalized confidence yeterli (LLM'den logit çekmeye gerek yok).

### 2.3 Token-Efficient Multi-Agent Debate

Fan, Yoon, Ji (2025) — **"iMAD: Intelligent Multi-Agent Debate for Efficient and Accurate LLM Inference"** (arXiv:2511.11306). Paper abstract verbatim: *"iMAD significantly reduces token usage (by up to 92%) while also improving final answer accuracy (by up to 13.5%)."* MAD'in her sorgu için tetiklenmesinin verimsiz olduğunu, sadece "muğlak" durumlarda tetiklenirse maliyet/doğruluk dengesinin dramatik iyileştiğini gösterdi. Mekanizma: tek-ajan self-critique ile 41 dilbilimsel özellik çıkarılır, hafif bir classifier MAD'i tetikleyip tetiklememeye karar verir. Sentio için optimum strateji: **"selective debate"** — sadece tek-LLM HOLD/AMBIGUOUS dönerse ikinci LLM tetikle.

Liu et al. (2024) — **"GroupDebate: Enhancing the Efficiency of Multi-Agent Debate Using Group Discussion"** (arXiv:2409.14051). Ajanları gruplara bölüp grup-içi tartışma + grup-arası özet paylaşımı ile token maliyetini Arithmetic'te %45, GSM8K'da %42.6, MMLU'da %50.6, MATH'ta %51.7 azalttı; MMLU'da %25, MATH'ta %11 doğruluk artışı. 2-LLM setupta GroupDebate doğrudan uygulanmaz ama "sıkıştırılmış özet" prensibi (her tur sonunda sadece anahtar bullet noktaları paylaşmak) token tasarrufu sağlar.

### 2.4 Finansta LLM ve Multi-Agent

Lopez-Lira ve Tang (2023/2024/2025, v6 Ekim 2025) — **"Can ChatGPT Forecast Stock Price Movements? Return Predictability and Large Language Models"** (arXiv:2304.07619, Journal of Financial Economics, forthcoming). Knowledge-cutoff sonrası haberlerde GPT-4 için spesifik bulgu (verbatim): *"our evidence shows that sophisticated models like GPT-4 can accurately discern the immediate economic implications of a news headline, achieving a daily portfolio hit rate of 93.3% (88.8%) for identifying the initial response."* Yani **%93.3 (parantez içi %88.8) günlük portföy-gün hit rate** — başlangıç tepkisi için ABD piyasası. GPT-4 ayrıca sonraki sürüklenmede özellikle küçük hisse senetleri ve negatif haberler için anlamlı tahmin gücü sergiledi. Forecasting yeteneği model boyutuyla artıyor: GPT-1/2/BERT yetersiz, GPT-4 başarılı — **finansal akıl yürütme LLM'lerin "emergent" yeteneğidir**. Önemli ileri görüş: "Strategy returns decline as LLM adoption rises" — yani RR-019 alpha penceresi adopsiyon arttıkça daralacak.

Xiao, Sun, Luo, Wang (2024/2025 v7) — **"TradingAgents: Multi-Agents LLM Financial Trading Framework"** (arXiv:2412.20138). 7 uzman ajanlı (fundamental/sentiment/technical/news analist + bull/bear researcher + trader + risk team) framework, üç hisse üzerinde 3 ay backtest'te Sharpe 5.60, 6.39, 8.21 raporladı — **yazarlar bizzat şu uyarıyı koydu (verbatim):** *"the exceptionally high SR resulted from the phenomenon that there were few pullbacks in TradingAgents during that period."* Yani 3 aylık pencere generalize edilemez. Her karar **11 LLM çağrısı + 20+ tool call** gerektirir → maliyet yüksek. GitHub: github.com/TauricResearch/TradingAgents (Apache-style). RR-019 için ders: framework cazip, ama maliyet kısıtı altında doğrudan kopyalanamaz; **özüne sadık 2-LLM minimum viable variant** seçilmeli.

---

## 3. 2-LLM Setup Önerisi

**Hedef Okuyucu:** arastirma katmani. Bu bölüm "hangi modeli niçin seçmeliyim ve roller nasıl tanımlanmalı" sorusunu yanıtlar.

### 3.1 Model Seçimi (Mayıs 2026 Snapshot)

> **Snapshot:** Mayıs 2026. Fiyatlar Anthropic, OpenAI ve Google'ın resmi sayfalarından alınmıştır. 3–6 ayda model versiyonları ve fiyatlar değişir.

| Model | Input ($/M tok) | Output ($/M tok) | Context | Kaynak | Seçim Gerekçesi (1–2 cümle) |
|---|---|---|---|---|---|
| **Claude Opus 4.7** | $5.00 | $25.00 | 1M | claude.com/pricing; platform.claude.com/docs/en/about-claude/pricing | Sistemin mevcut Strategist LLM'i (D-110). Anthropic'in flagship modeli; karmaşık akıl yürütme ve uzun bağlamda lider. Yeni tokenizer aynı text için %35'e kadar daha fazla token tüketebilir — kıyaslama gerekli (Anthropic docs). |
| **Claude Sonnet 4.6** | $3.00 | $15.00 | 1M | claude.com/pricing | Opus'a göre %40 daha ucuz, kalite/maliyet dengesinin "tatlı noktası". 2-LLM jüri için Opus yerine Sonnet kullanmak maliyeti yarıya indirir; ancak nüanslı KAP yorumunda Opus avantajlı. |
| **Claude Haiku 4.5** | $1.00 | $5.00 | 200K | claude.com/pricing | RR-011 L4 Sentiment Tier 2'de zaten kullanılıyor. Strategist v2 için yetersiz (akıl yürütme derinliği) — sınıflandırma katmanı olarak ideal. |
| **GPT-5.5** (April 2026) | $5.00 | $30.00 | 1M | openai.com/api/pricing | OpenAI flagship; Claude Opus'tan farklı eğitim → "echo chamber" riskini azaltır. Output GPT-5.4'ün 2 katı; pahalı ama reasoning derinliği yüksek. Cached input %90 indirim. |
| **GPT-5.4** | $2.50 | $15.00 | 1.1M | pricepertoken.com; openai.com/api/pricing | Bear advocate için **birinci tercih**: daha ucuz (GPT-5.5'in yarısı), 1.1M context, OpenAI line'ında 2026 baseline. RR-019 2-LLM MVP'sinde önerilen muhatap model. |
| **GPT-5.4 Nano** | $0.20 | $1.25 | — | openai.com | Selective debate gating için. Sadece "ambiguous mu?" kararını vermek üzere tetikleyici sınıflandırıcı olarak kullanılabilir. |
| **Gemini 2.5 Pro** | $1.25 (≤200K) | $10.00 | 1M | ai.google.dev/gemini-api/docs/pricing | 2M context için Gemini 3.1 Pro alternatif; ucuz, ama BIST/Türkçe finansal yorum geçmişi sınırlı. Yedek seçenek. |
| **Gemini 2.5 Flash** | $0.30 | $2.50 | 1M | ai.google.dev/gemini-api/docs/pricing | Selective debate gating için Nano alternatifi; ücretsiz tier mevcut. |
| **Trendyol-LLM-Asure-12B** | self-host | self-host | 32K | huggingface.co/Trendyol/Trendyol-LLM-Asure-12B | 12B parametre, Gemma 3-12B base, Türkçe + e-ticaret odaklı multimodal. Model card: "general encyclopedic world knowledge is intentionally limited." **Finansal yorum için doğrudan uygun değil**; özel fine-tune gerektirir. HF capture: 585 download / 38 like (Feb 2026). Self-host GPU maliyeti $20/ay bütçeyi aşar. |
| **Trendyol-LLM-8B-T1** | self-host | self-host | 32K | huggingface.co/Trendyol/Trendyol-LLM-8B-T1 | 8B, Qwen 3-8B base, reasoning modeli, /think modu. Türkçe akıl yürütme için tek production-grade açık model — ama BIST KAP test edilmiş değil. HF: 143 download / 31 like. |
| **TURNA / TabiBERT (BOUN-TABILAB)** | self-host | self-host | — | huggingface.co/boun-tabi-LMG/TURNA; huggingface.co/boun-tabilab/TabiBERT | Boğaziçi TABILAB akademik modelleri; TabiBERT TabiBench'te %77.58, BERTurk'ten +1.62 pp önde (Türker et al. arXiv:2601.12538). Encoder; generative değil — sentiment scoring için OK, jüri rolü için değil. |

**Önerilen 2-LLM kombinasyonu (MVP):** **Claude Opus 4.7 (Bull) + GPT-5.4 (Bear).** Gerekçe: farklı sağlayıcı (echo chamber azaltma), her ikisi de 1M+ context, Bull/Bear toplam ~$7.50 input + ~$40 output per 1M token.

### 3.2 Rol Tasarımı

**İki opsiyon değerlendirildi:**

**Opsiyon A — Bull Advocate + Bear Advocate.** Klasik TradingAgents yaklaşımı. Her LLM verilen daily_report'a "bu hisse bugün al/sat/tut sinyali mi?" sorusuna farklı bir bias'la cevap verir; uyuşmazlık → belirsizlik.
- *Avantaj:* literatürde validate edilmiş (Xiao et al. 2024, Liang et al. 2024 MAD framework).
- *Dezavantaj:* her LLM aynı verinin farklı yorumunu üretir, ancak temel veri eksikliğini telafi etmez.

**Opsiyon B — Macro Lens + Stock-Specific Lens.** Bir LLM makro/sektör perspektifinden (TCMB politikası, kur, EM akımları), diğeri hisseye özel (KAP, çeyreklik, holding NAV) odaklı yorum üretir.
- *Avantaj:* katmanları açıkça ayrıştırır; her LLM'in güçlü olduğu boyut farklılaşır.
- *Dezavantaj:* uyuşmazlık yorumlanması zor — farklı boyutta uyuşmazlık aynı sinyali vermez.

**Öneri: Opsiyon A (Bull/Bear).** Disagreement skoru daha temiz tanımlanır. Opsiyon B Phase 6+'da denenebilir.

### 3.3 Disagreement-Aware Sizing Formülasyonu

Mevcut position sizer (RR-016 sonrası v3):

```
final_size = base_kelly × conviction_tier_mult × vol_scalar × dd_scalar
```

RR-019 sonrası önerilen v4 (opsiyonel kolon):

```
final_size = base_kelly × conviction_tier_mult × vol_scalar × dd_scalar × llm_agreement_scalar
```

`llm_agreement_scalar` tablosu (Du et al. 2023 "consensus = reliable signal" prensibinden uyarlanmış):

| LLM₁ Çıktısı | LLM₂ Çıktısı | llm_agreement_scalar | Yorum |
|---|---|---|---|
| BUY-STRONG | BUY-STRONG | **1.0** | Tam consensus, kelly tam pozisyon |
| BUY-STRONG | BUY-MEDIUM | **0.85** | Yön aynı, conviction farkı |
| BUY-MEDIUM | BUY-MEDIUM | **0.85** | Yön aynı, ikisi de medium |
| BUY | HOLD | **0.50** | Yarım pozisyon |
| HOLD | HOLD | **0.30** | Düşük conviction (taban koruma) |
| BUY | SELL | **0.00** | Güçlü çelişki → SKIP |
| SELL | SELL | **0.00** | Long-only, SELL = pozisyon yok |

Sanity test örnekleri:

```
# Test 1: full consensus
base_kelly=0.06, conviction_mult=1.0, vol_scalar=1.0, dd_scalar=1.0, llm_agreement=1.0
→ final_size = 0.06 × 1 × 1 × 1 × 1 = 6.0% portföy
PASS ✓

# Test 2: bir LLM BUY, diğer HOLD
base_kelly=0.06, ..., llm_agreement=0.50
→ final_size = 0.06 × 0.50 = 3.0% portföy
PASS ✓ (yarım pozisyon)

# Test 3: güçlü çelişki
base_kelly=0.06, ..., llm_agreement=0.00
→ final_size = 0.0 → trade SKIP
PASS ✓

# Test 4: drawdown durumunda çelişki
base_kelly=0.06, conviction=1.0, vol_scalar=0.8, dd_scalar=0.5 (RR-016 -10% DD), llm_agreement=0.5
→ final_size = 0.06 × 0.8 × 0.5 × 0.5 = 1.2% → mikro pozisyon
PASS ✓ (skalarlar çarpımsal, drawdownda çelişki büyük caydırıcı)
```

---

## 4. Türkçe Finansal Context Test Framework (Deliverable)

**Hedef Okuyucu:** arastirma katmani. Bu bölüm direkt başlanabilecek seviyede; AUM eşiği aşıldığında ilk iş bu test setini üretmek.

### 4.1 Test Seti Yapısı

**Toplam 100 BIST KAP açıklaması (2024–2026 dönemi)**, beş kategoride 20'şer örnek. Kategoriler beklenen LLM-jüri agreement seviyesine göre zorlukla sıralanır:

| # | Kategori | Örnek Sayısı | Zorluk | Beklenen LLM-LLM Agreement |
|---|---|---|---|---|
| 1 | Kâr payı / temettü açıklaması | 20 | Kolay | %90+ |
| 2 | Yönetim kurulu değişikliği | 20 | Orta | %75–85 |
| 3 | Hukuki süreç (dava açıldı/karara bağlandı) | 20 | Zor | %60–75 |
| 4 | Sermaye artırımı / bedelli/bedelsiz | 20 | Zor | %50–70 |
| 5 | Faaliyet raporu özetleri (çeyreklik) | 20 | Çok zor | %40–65 |

**Veri kaynağı:** kap.org.tr public archive; her örnek `{kap_id, ticker, date, raw_text_tr, category}` formatında saklanır.

### 4.2 Manuel Ground Truth (Inter-rater Agreement)

- **maintainer + 1 finans uzmanı** (junior quant pozisyon ağı, mentorlar veya BÜMK alumni network) **bağımsız etiketleme** yapar. Etiket uzayı: `{BUY-STRONG, BUY-MEDIUM, HOLD, SELL-MEDIUM, SELL-STRONG, IRRELEVANT}`.
- **Cohen's κ ≥ 0.7 koşulu**: iki etiketleyici Cohen's kappa ≥ 0.7 olmadıkça test seti onaylanmaz.
- **Uyuşmazlık çözümü:** 3. rater (mentor) tie-breaker olarak karar verir.
- Cohen's κ hesabı için `sklearn.metrics.cohen_kappa_score` yeterlidir.

### 4.3 LLM Test Koşulları

```yaml
test_setup:
  temperature: 0.0           # deterministic, reproducibility için
  max_tokens: 500            # cevap kısa tutulur
  prompt_structure: identical_across_models
  few_shot: 5_examples       # her kategoriden 1 örnek, ground truth ile
  output_format: |
    {
      "sentiment": "BUY-STRONG|BUY-MEDIUM|HOLD|SELL-MEDIUM|SELL-STRONG|IRRELEVANT",
      "confidence": "HIGH|MEDIUM|LOW",
      "reasoning": "...max 200 Turkish chars..."
    }
```

Kritik tasarım kararları:
- **Temperature 0.0**: aynı prompt aynı çıktı (reproducibility).
- **Few-shot 5**: zero-shot bias'ı kırar; kategori başına 1 örnek temsil.
- **JSON output**: pars edilebilir, manuel okuma minimum.

### 4.4 Metrikler

- **Accuracy (kategori bazlı + toplam)**: `(doğru_etiket_sayısı / toplam_örnek) × 100`.
- **Cohen's κ (LLM çıktısı vs. ground truth)**: chance-adjusted agreement; 0.6+ moderate, 0.8+ substantial.
- **Calibration**: LLM `confidence: HIGH` çıkışlarının accuracy ≥ 85%, `MEDIUM` 65–85%, `LOW` ≤ 65% beklenir. Sapma = miscalibration (Lin et al. 2022 verbalized probability).
- **Inter-LLM agreement matrix**: confusion matrix LLM₁ × LLM₂ → jüri logic'ini (Bölüm 3.3) ampirik kalibre eder.

### 4.5 Literatür Proxy Beklentiler

> **Önemli caveat:** Aşağıdaki sayılar **ABD/genel İngilizce data üzerinden Türkçeye proxy tahminidir**; gerçek BIST sonuçları arastirma katmani tarafından test edildikten sonra yazılır. Hipotez verme yasaktır — bunlar sadece "ne beklemek mantıklı" sezgisidir.

- Lopez-Lira & Tang (2025, JFE forthcoming): ABD'de GPT-4 haber başlıkları → günlük portföy hit rate **%93.3 (negatif örneklerde %88.8)**. Bu **portföy seviyesinde** ölçüm; tek-haber sentiment etiketi accuracy literatürde tipik %75–85 düzeyinde.
- Lopez-Lira & Tang ayrıca: "Forecasting ability generally increases with model size" — Opus 4.7/GPT-5.5 muhtemelen GPT-4'ten daha iyi.
- **Türkçe için tahmini -%5 ila -%10 düşüş**: çünkü pretraining İngilizce ağırlıklı; finansal terminoloji ABD merkezli. Türkçe için tahmin: **%65–80 accuracy**.
- BERTurk/TabiBERT (Türker et al. 2025): Türkçe genel benchmark'ta TabiBERT %77.58 toplam ortalama, BERTurk'ten +1.62 puan. **Finansal alt-alanda muhtemelen %70–75**. LLM'nin bunu aşması beklenir ama doğrulama arastirma katmani testinden sonra.
- Boğaziçi / BOUN TABILAB modelleri encoder'dır — generative değil; doğrudan kıyas yapılamaz, sentiment scoring baseline'ı olarak kullanılabilir.

### 4.6 Çıktı Format

```
results/rr019_turkish_test_v1/
├── ground_truth.csv          # kap_id, ticker, date, raw_text, gold_label, rater_1, rater_2, kappa
├── llm_outputs/
│   ├── claude_opus_47.jsonl  # kap_id, sentiment, confidence, reasoning
│   ├── gpt_54.jsonl
│   └── gemini_25_pro.jsonl
├── metrics_summary.md        # accuracy, kappa, calibration table
├── heatmap.png               # arastirma katmani generate; 5 kategori × N model
└── final_ranking.md          # weighted_accuracy / cost_per_call
```

**Final ranking formülü:**
```
score = (overall_accuracy × 0.5) + (kappa × 0.3) + (calibration_bonus × 0.2)
ranking = score / cost_per_1k_tokens
```

---

## 5. TradingAgents Framework Analiz

**Hedef Okuyucu:** Phase 6+ maintainer. 7-agent'a "ne zaman geçilir" kararı için referans.

### 5.1 Framework Özellikleri

TradingAgents v7 (Xiao, Sun, Luo, Wang — arXiv:2412.20138, son revize Haziran 2025; github.com/TauricResearch/TradingAgents):

- **7 uzman ajan:** Fundamental Analyst, Sentiment Analyst, Technical Analyst, News Analyst, Bull Researcher, Bear Researcher, Trader.
- **Risk Management Team:** Aggressive/Conservative/Neutral risk profilli üç sub-agent + fund manager.
- **İletişim mekanizması:** structured documents + diagrams + natural language dialogue.
- **Reflection agent:** geçmiş kararları geri okuyup gelecekteki kararları rafine ediyor.
- **Backbone LLM:** GPT-4o-mini, GPT-4o, o1-preview (paper). Anthropic Claude desteği eklenmiş durumda (GitHub).

### 5.2 BIST Adaptasyon Effort

| Görev | Tahmini Effort | Açıklama |
|---|---|---|
| Türkçe prompt çevirisi (7 ajan) | 1–2 hafta | Sistem promptları Türkçeye çevrilmeli, BIST terminolojisi (KAP, SPK, BIST 100, holding NAV) eklenmeli |
| KAP integration | 1 hafta | News Analyst'a kap.org.tr feed bağlanması |
| Türkçe sentiment lex/LLM | 1 hafta | RR-011 hibrit sistem zaten var; Sentiment Analyst için entegrasyon |
| Holding NAV bilgisi (RR-013) | 0.5 hafta | Fundamental Analyst'a NAV verisi enjekte etmek |
| TCMB/EVDS makro feed | 0.5 hafta | News Analyst'a EVDS API bağlamak |
| Backtest harness (RR-018) entegrasyonu | 1 hafta | Daily decisions → trade execution loop |
| **TOPLAM** | **5–6 hafta** | ~1 ay+ tek geliştirici işi |

Effort: Yüksek. Bu nedenle 2-LLM MVP önce, 7-agent sonra.

### 5.3 Maliyet

TradingAgents bir kararda **11 LLM çağrısı + 20+ tool call** kullanır (yazarların açıklaması; "Beginners in AI" özeti). Tipik karar maliyeti (Opus 4.7 baseline):

- 11 LLM çağrısı × ~1500 input + ~500 output token = 16.5K input + 5.5K output
- Per-trade maliyet: 16.5K × $5/M + 5.5K × $25/M = $0.0825 + $0.1375 ≈ **$0.22 / trade**
- Aylık 30 trade: **~$6.60/ay sadece TradingAgents** (Opus 4.7)
- GPT-5.4 ile: 16.5K × $2.50/M + 5.5K × $15/M = $0.0413 + $0.0825 ≈ **$0.12/trade** → **~$3.60/ay**
- L4 Sentiment ($10/ay) + TradingAgents ($6.60–$10/ay) = **$15–$20/ay** (Opus 4.7 + caching).

**Aslında 7-agent direkt bütçeyi aşmayabilir**, eğer prompt caching agresif uygulanır ve Sonnet/GPT-5.4 kullanılır. Ama uygulama riski (5–6 hafta effort) ve Sharpe stabilization belirsizliği yüksek.

### 5.4 Önemli Caveat: Backtest Sınırlamaları

TradingAgents Sharpe 5.60–8.21 raporu **sadece 3 aylık** backtest üzerinden geldi; yazarların bizzat verbatim açıklaması (paper §experiments): *"the exceptionally high SR resulted from the phenomenon that there were few pullbacks in TradingAgents during that period."* — yani **kısa pencere artifactı**. RR-019, bu bulguyu "framework çalışır ama gerçek alpha bilinmiyor" olarak yorumlar. Mutlaka RR-018 backtest framework'üne plug edilerek 5+ yıl BIST tarihsel veride re-test edilmelidir.

### 5.5 2-LLM vs 7-Agent Karşılaştırma

| Boyut | 2-LLM MVP | 7-Agent TradingAgents |
|---|---|---|
| Effort | 1 hafta | 5–6 hafta |
| Aylık maliyet (cache + Opus/GPT-5.4) | $3–7 | $7–20 |
| Akademik validation | Güçlü (Du 2023, Liang 2024) | Sınırlı (1 paper, 3-ay test) |
| Türkçe context | Doğrudan test edilebilir | Çok katmanlı, debug zor |
| Disagreement signal | Net (2'li vote) | Multiplexed, yorumu zor |
| Drawdown koruma | Açık (skip on conflict) | Risk team'e bağlı, opak |
| Backtest entegrasyonu | RR-018'e plug kolay | Stateful, replay zor |
| **Karar** | **MVP için tercih** | Phase 6+++ (AUM 1M+ ve junior pozisyon sonrası) |

---

## 6. Architectural Entegrasyon

**Hedef Okuyucu:** arastirma katmani. Mevcut `src/agents/strategist.py` dosyasını v2'ye yükseltirken backward-compat korunmalı.

### 6.1 Mevcut Strategist (v1)

```
src/agents/strategist.py
  input:   daily_report (Markdown, ~2K token)
  process: single Anthropic API call (claude-opus-4-7)
  output:  advisory_report (~600 token Markdown)
  cost:    ~$5–10/ay
  boundary: DEC-010 — advisory only, never executive
```

### 6.2 2-LLM Strategist v2 Önerisi

```
src/agents/strategist_v2.py
  input:   daily_report
  
  parallel calls (asyncio.gather):
    - LLM_bull = anthropic.messages.create(
        model="claude-opus-4-7",
        system=BULL_ADVOCATE_SYSTEM_PROMPT_TR,
        messages=[{"role":"user","content":daily_report}],
        cache_control={"type":"ephemeral"},   # 5-min TTL prompt cache
      )
    - LLM_bear = openai.responses.create(
        model="gpt-5.4",
        instructions=BEAR_ADVOCATE_SYSTEM_PROMPT_TR,
        input=daily_report,
      )
  
  synthesis:
    - parse both as JSON {sentiment, confidence, reasoning}
    - compute disagreement_score ∈ [0, 1]
    - if disagreement < 0.3: full position recommendation
    - if 0.3 ≤ disagreement < 0.7: half position
    - if disagreement ≥ 0.7: skip (long-only, conflict resolved by no trade)
  
  output:
    - advisory_report (~800 token, includes both perspectives + final)
    - disagreement_score (float)
    - llm_agreement_scalar (float in [0,1], for position_sizer v4)
```

### 6.3 position_sizer Entegrasyonu

Versiyon yol haritası:
- **v1** (mevcut, Phase 4 öncesi): `base_kelly`
- **v2** (RR-014 slippage sonrası, mevcut): `base_kelly × conviction_tier_mult`
- **v3** (RR-016 drawdown sonrası): `base_kelly × conviction_tier_mult × vol_scalar × dd_scalar`
- **v4** (RR-019 sonrası, **OPSİYONEL**): `× llm_agreement_scalar` ek kolon
- v1 → v3 default; v4 ayrı feature flag ile aktive edilir.

**Backward-compat test:** `llm_agreement_scalar = 1.0` durumunda v4 ≡ v3. Bu, "RR-019 implement edildi ama çelişki yok" durumunu temsil eder ve mevcut backtest sonuçlarını değiştirmemelidir.

### 6.4 DEC-010 Boundary Uyumu

DEC-010: "LLM advisory only, never executive."

RR-019 bu boundary'yi **GÜÇLENDİRİR**, kırmaz:
- 2 LLM uyuşmazlık durumunda öneri **DAHA YUMUŞAK** olur (skip), daha agresif değil.
- Hiçbir LLM doğrudan order üretmez; sadece position size suggestion verir.
- Final karar maintainer'da kalır; LLM jüri sadece sayısal `llm_agreement_scalar`'ı raporlar.
- Skip durumunda maintainer manuel override edebilir ("LLM'ler çelişti ama ben yine de alacağım" — DEC-010 izin verir).

---

## 7. Maliyet Analizi (Detaylı)

**Hedef Okuyucu:** maintainer. Bütçe kararı için.

> **Snapshot:** Mayıs 2026. Anthropic, OpenAI, Google resmi fiyat sayfalarından. Yeni model çıkışı veya fiyat değişikliği ile geçersizleşir.

### 7.1 Aylık Token Tüketimi Varsayımları

- 30 trading günü × 1 daily report = **30 rapor/ay**
- Daily report input: ~2.000 token (haberler + KAP + macro snapshot)
- Output per LLM: ~600–800 token (jüri için iki taraf raporlar)
- Per trade (selective debate sonrası): **avg ~2K input × 2 LLM + ~1.5K output × 2 LLM**

### 7.2 2-LLM Senaryosu — Ham Fiyat

**Bull = Opus 4.7, Bear = GPT-5.4:**
```
Aylık input  = 30 × 2K × 2 LLM = 120K token
Aylık output = 30 × 0.75K × 2 LLM = 45K token

Opus input  = 60K × $5/M  = $0.30
Opus output = 22.5K × $25/M = $0.5625
GPT-5.4 input  = 60K × $2.50/M = $0.15
GPT-5.4 output = 22.5K × $15/M = $0.3375

Toplam ham: ~$1.35/ay (sadece Strategist v2, L4 hariç)
```

**Daha gerçekçi (zengin context):**
```
input per call = 8K token (full daily report + history)
output per call = 1.5K token

Aylık input  = 30 × 8K × 2 = 480K token
Aylık output = 30 × 1.5K × 2 = 90K token

Opus  in/out: 240K × $5/M + 45K × $25/M = $1.20 + $1.125 = $2.325
GPT-5.4 in/out: 240K × $2.50/M + 45K × $15/M = $0.60 + $0.675 = $1.275

Toplam ham: ~$3.60/ay (Strategist v2, cache yok)
```

### 7.3 2-LLM Senaryosu — Prompt Caching ile

Anthropic prompt caching kuralları (platform.claude.com/docs/en/build-with-claude/prompt-caching): cache write 1.25× input (5-dakika TTL) veya 2× (1-saat TTL); **cache read 0.10× input (= %90 indirim)**. Minimum cache uzunluğu Opus için 4.096 token.

OpenAI cached input: GPT-5.5 ve GPT-5.4 ailesinde **%90 indirim** (cached input $0.50/M tok, vs. $5/M tok GPT-5.5 standard) — kaynak: openai.com/api/pricing.

Daily report'un büyük bir kısmı sabit sistem promptu + sabit makro context'tir. ~6K token cache'lenebilir, ~2K dinamik kalır.

```
Cache write (ilk gün): 6K × 1.25 × $5/M = $0.0375 (Opus)
Cache read (sonraki günler): 6K × $0.50/M = $0.003/call
Dinamik input: 2K × $5/M = $0.01

Per call (cache hit): $0.013 input + 1.5K × $25/M output = $0.013 + $0.0375 = $0.0505
Per call x 30 days = $1.52
Cache writes (~6/ay): 6 × $0.0375 = $0.22

Opus aylık (cache): ~$1.74
GPT-5.4 benzer mantıkla: ~$0.85

Toplam cached: ~$2.60/ay (Strategist v2)
```

### 7.4 7-Agent (TradingAgents) Senaryosu

(Bölüm 5.3'te detaylandırıldı.)

- Opus 4.7 ham: $6.60/ay
- Opus 4.7 + cache: ~$3.30/ay
- GPT-5.4 ham: $3.60/ay
- GPT-5.4 + cache: ~$1.80/ay
- **Karma (önerilen)** = Opus reasoning + GPT-5.4 routine + Haiku/Nano gating: ~$2–4/ay

### 7.5 Aylık Projeksiyon Karşılaştırma

| Senaryo | Ham Fiyat | + Prompt Caching | + L4 Sentiment | Toplam |
|---|---|---|---|---|
| Mevcut (v1, single Opus) | $5–10 | $1–2 | $10 | **$11–12** |
| 2-LLM MVP (Opus+GPT-5.4) | $3.60 | $2.60 | $10 | **$12.60** |
| 2-LLM (Sonnet 4.6 × 2) | $1.80 | $1.20 | $10 | **$11.20** |
| 7-Agent (Opus 4.7) | $6.60 | $3.30 | $10 | **$13.30** |
| 7-Agent (GPT-5.4) | $3.60 | $1.80 | $10 | **$11.80** |
| 7-Agent (karma) | $4–5 | $2.50–3.50 | $10 | **$12.50–13.50** |

**Hedef retail butce ($20/ay) tüm senaryolarda karşılanabilir** — kritik nüans: cache'i agresif uygulamak ve büyük input context'i statik tutmak şart. Cache uygulanmazsa 2-LLM bile $15–20/ay seviyesine çıkar.

---

## 8. RR-011 ile Sinerji — Birleşik Token Bütçesi

**Hedef Okuyucu:** arastirma katmani/maintainer. RR-011 ve RR-019 birlikte çalıştığında bütçeyi yönetmek.

### 8.1 Bileşenler

**L4 Sentiment (RR-011 hibrit, D-124 aktif):**
- Tier 1 lexicon: $0, her gün ~2.000 haber işliyor.
- Tier 2 LLM (Claude Haiku 4.5): sadece "muğlak" haberler için. ~$10/ay baseline (maintainer ölçümü).

**Strategist v2 (RR-019 2-LLM):**
- Aylık ~$3.60–$13 (Bölüm 7).

### 8.2 Birleşik Aylık Tahmini

- Ham: $13.60–$23 (yüksek tarafta $20 hedefini aşar)
- Cached: $11–$14 (rahat)

### 8.3 4 Optimizasyon Stratejisi

1. **Anthropic stable prompt caching (1-saat veya 5-dakika TTL).** Sistem promptu + sabit Türkçe context + sabit BIST sözlüğü cache'lenir. Cache read maliyeti standart input'un %10'u. Production ölçümü (dev.to "Anthropic prompt caching cut our RCA cost by 90%"): Haiku 4.5 üzerinde %90+ cache-hit oranıyla input maliyeti tam fiyatın **onda birine** düşüyor — yani caching'in teorik %90 değil, **pratik %88–90 fiili** tasarruf sağladığı production'da doğrulanmış.
2. **Selective debate (iMAD prensibi, arXiv:2511.11306).** Tek-LLM (Bull) önce çalışır; HOLD veya conviction LOW dönerse Bear LLM tetiklenir. Aksi halde Bear atlanır. Paper abstract: *"reduces token usage by up to 92% while also improving final answer accuracy by up to 13.5%."*
3. **Haiku 4.5 (zaten kullanılıyor) → Haiku 5 (2026 H2 muhtemel lansman) geçişi.** Eğer Anthropic Haiku 5 çıkarırsa ve Haiku 4.5'tan ucuzsa, L4 Tier 2 fiyat-aşağı revize edilir. **BULUNAMADI:** Haiku 5 lansman tarihi resmi açıklanmadı; bekleme stratejisi.
4. **L4 Tier 2 frequency reduction.** Mevcut: günlük batch. Önerilen: haftalık batch (yedi günün tüm muğlak haberlerini bir batch'te işlemek). Batch API (%50 indirim) ile birleşince L4 maliyeti $10 → $3–5/ay.

### 8.4 Optimizasyon Sonrası Tahmini Bütçe

- Mevcut v1 + RR-011 baseline: $15–20/ay
- v2 (2-LLM) + RR-011 + optimizasyon: **$13–16/ay** → maintainer hedefini karşılar ✓
- 7-Agent + RR-011 + optimizasyon: $14–18/ay → marjinal, AUM artmadan riskli

---

## 9. Risk & Failure Modes

**Hedef Okuyucu:** maintainer. Operasyonel risk ve mitigasyon.

| Risk | Olasılık | Etki | Mitigasyon |
|---|---|---|---|
| **API outage (Claude/OpenAI down)** | Orta (her 6 ayda 1–2 saat) | Yüksek (daily report gecikir) | Fallback: tek LLM'le devam et; eğer her ikisi de down ise lexicon-only L4 + sabit Strategist template; circuit breaker timeout 30s |
| **Cost runaway (runaway debate, max_tokens overflow)** | Düşük | Orta | Her API call'da `max_tokens` cap (Opus 1500, GPT-5.4 1500); aylık usage alert ($25 eşik); selective debate gating |
| **Echo chamber (2 LLM aynı eğitim → similar bias)** | Orta | Yüksek (yanlış consensus → yanlış alfa) | Farklı sağlayıcı (Anthropic + OpenAI) zorunlu; periyodik (3 ayda) prompt phrasing rastgele perturbation; aylık disagreement rate monitör (eğer %5'in altına düşerse echo chamber alarmı) |
| **Calibration drift (Opus 4.7 → 4.8/Mythos güncellemesi)** | Yüksek (her 3–6 ayda model güncellenir) | Orta | Türkçe test seti (Bölüm 4) **her major version güncellemesinde yeniden çalıştırılır**; Cohen's κ ≥ 0.6 koşulu, sağlanmazsa eski versiyona pin |
| **Türkçe context degradation (yeni model İngilizce iyileştirmesine Türkçeyi feda eder)** | Düşük | Yüksek | Bölüm 4 test framework periyodik (çeyrekte 1) çalıştırılır; sonuç önceki version'dan -10pp düşerse alarm |
| **Pricing change (provider zammı)** | Orta (1–2 yılda 1) | Orta | Mayıs 2026 snapshot referans; aylık `last_updated` tarihi check; bütçe overflow olursa Sonnet/Haiku/cached'e otomatik düş |
| **LLM jüri overconfidence (her ikisi de yanlış ama agree)** | Orta | Yüksek | RR-019 alpha kaynağı **değil**; RR-010/012/017 ana sinyal, RR-019 sadece sizing modifier. LLM yüksek conviction ama L1/L2/L5 ile çelişiyorsa maintainer diskresyoner override yapar |

---

## 10. BIST 2024–2026 Sektör Pratiği

**Hedef Okuyucu:** maintainer. Türkiye'de "AI-assisted trading" ne kadar yaygın, mevzuat ve maliyet farkındalığı.

> **Twitter login-wall caveat:** Türk fintwit ChatGPT/Claude kullanım gözlemleri Twitter/X login-wall arkasında kalıyor. Bu bölümdeki retail gözlemleri **resmi olarak doğrulanmamıştır**; sadece anekdotal seviyede.

### 10.1 Türk Kurumsal LLM Kullanımı (Ordinal: Y/O/D/Yok)

| Kurum | Production LLM Kullanımı | Skala | Kaynak |
|---|---|---|---|
| **Garanti BBVA** ("Ugi" jenerik AI asistan) | **Y** (Yüksek) | 2025 metrikleri: **6.4 milyon aylık etkileşim**, **1.6 milyon aktif kullanıcı**, **300+ end-to-end banking transaction**; mobile customer'ların **~%50'si** Ugi ile en az bir kez etkileşim kurdu; **780.000 proaktif bildirim/ay**. Generative AI upgrade ile *"can now understand 90% of user requests"*; iç AI: **900+ AI modeli** belge tarama/extraction için. | bbva.com/en/tr/innovation/garanti-bbva-mobile-redefines-digital-banking-in-2025/; news.europawire.eu (Nisan 2025) |
| **İş Bankası** (Instabase IDP) | **O** (Orta) | ~30.000 sayfa/gün, classification accuracy 41.4% → 85%, extraction 22.5% → 75% | Nucamp aggregator citing Instabase case study |
| **Türkiye Finans** (RPA + ML IDP) | **O** | ~500 unstructured belge/gün, 80% hızlanma, %84–87 otomasyon | Nucamp/IBM/CBOT case |
| **Yapı Kredi** (RPA) | **O** | 137 otomatik süreç, 20 unattended robot | Nucamp |
| **Sektör geneli (Afyonkarahisar akademik survey)** | **Y** | **17 bankadan 16'sı (%94.1) AI kullanıyor**; ML sistemleri **günde ~40 milyon işlem** tarıyor, ~500 şüpheli vaka işaretliyor; lider bir bankada fraud zararı **-%98.7 azalış** | Nucamp aggregation citing primary academic survey |
| **Türk brokerajları (İş Yatırım, Garanti BBVA Yatırım, Ak Yatırım)** | **Yok** (production LLM) | BULUNAMADI: public LLM trading kullanımı yok | — |
| **Param, Papara fintech** | **Yok** (public LLM) | BULUNAMADI | — |

**Yorum:** Kurumsal AI Türkiye'de **müşteri etkileşimi + fraud + operations** odaklı, **trade decision** odaklı değil. Bu RR-019 için **fırsat penceresi**: BIST'te LLM-jüri kullanan kurum yok denecek kadar az, alpha henüz daralmamış.

### 10.2 Akademik Türk LLM Sahnesi

- **Trendyol Asure 12B** (huggingface.co/Trendyol/Trendyol-LLM-Asure-12B): Gemma 3-12B base, multimodal, Şubat 2026 yayın, 585 download / 38 like (HF capture). Model kartında: *"general encyclopedic world knowledge is intentionally limited"* → finansal yorumda doğrudan kullanım için **uygun değil**, fine-tune gerek.
- **Trendyol-LLM-8B-T1** (huggingface.co/Trendyol/Trendyol-LLM-8B-T1): Qwen 3-8B base, Türkçe + İngilizce reasoning, /think dual mode, 143 download / 31 like. **BIST KAP'ta test edilmemiş.**
- **BOUN-TABILAB TURNA** (huggingface.co/boun-tabi-LMG/TURNA): Akademik araştırma modeli; non-commercial.
- **TabiBERT** (huggingface.co/boun-tabilab/TabiBERT): TabiBench Türkçe NLP benchmark'unda %77.58, BERTurk'ten +1.62 pp önde (kaynak: Türker et al. Aralık 2025 paper arXiv:2601.12538, emergentmind.com özet). Encoder; generative değil.

**Sonuç:** Açık Türkçe LLM'ler hâlâ generative finansal yorum için **production-ready değildir**. RR-019 kapalı kaynak commercial LLM'lere bağımlı kalır en az 1–2 yıl daha.

### 10.3 SPK Düzenleme

SPK 2024 İdare Faaliyet Raporu (Temmuz 2025 yayını) ve III-37.1 Tebliğ değişiklik hazırlıkları (procompliance.net/spk-tarafindan-hazirliklari-surdurulen-duzenleme-calismalari-temmuz-2025/):

- *"Robo danışmanlık uygulamaları ile yatırım danışmanlığı ve bireysel portföy yöneticiliği hizmetlerinin sunulmasına ilişkin ilke ve esasların belirlenmesi"* — hazırlık aşamasında.
- *"Algoritmik ve yüksek frekanslı işlem gerçekleştiren yatırım kuruluşlarına yönelik belirlemeler yapılması"* — hazırlık aşamasında.
- Güncel yürürlük: III-37.1 Tebliğ (Resmî Gazete 11/7/2013, no. 28704); ilgili güncel SPK kararı i-SPK.37.7 (18.12.2025, 65/2354) profesyonel müşteri eşiklerini güncelledi (finansal varlık alt sınırı 1M TL → 10M TL).

**Sentio impact:** maintainer **kişisel** trading sistemi, "yatırım kuruluşu" değil → düzenleme doğrudan bağlamaz. Yetki belgesi alıp başkalarına LLM-based tavsiye satarsa SPK çerçevesi devreye girer. DEC-010 "advisory only, never executive" boundary'sı bu çerçeveye uyumlu kalır.

### 10.4 Maliyet Farkındalığı

Türk retail için $20/ay (~700 TL/ay USD 35 TL kurla) ortalamanın belirgin üzerinde — junior quant aylik ucretinin %1-2'si mertebesinde. Olası "Türk hisse senedi getirisine göre ROI" hesabı: **BIST 100 2024'ü 9,830.56 puanda kapattı; yıllık %31.6 TRY-bazlı yükseliş, dolar bazında +%9.6**" (kaynak: Türkiye Today / MKK-Borsa Istanbul verisi). 10.000 TL portföyde %31.6 = 3.160 TL/yıl TRY-bazlı getiri; $20/ay × 12 = $240/yıl × 35 TL = 8.400 TL/yıl LLM maliyeti → ROI **negatif** küçük portföyde. **AUM 100K+ TL** olmadan LLM jüri ekonomik değil. RR-019 priority "nice-to-have"in nedeni budur.

---

## 11. Crisis Period Uygunluk

**Hedef Okuyucu:** maintainer. "LLM jüri 2023 Mayıs seçim haftası faydalı olur muydu?" sorusunun cevabı.

### 11.1 Mayıs 2023 Seçim Haftası

**Olay:** 14 Mayıs 2023 ilk tur sonrası Pazartesi 15 Mayıs'ta BIST 100 pre-market %6.4'e kadar düşüş, kapanışta -%6.1; bankacılık endeksi -%9.2 (kaynak: CNN Business, "Turkish lira sinks to new record low on prospect of Erdogan re-election", 15 Mayıs 2023). 28 Mayıs ikinci tur sonrası belirsizliğin çözülmesi ile event-study CAR ortalaması **678–1019 baz puan pozitif** (Taylor & Francis / Cogent Economics & Finance 2023, doi:10.1080/23322039.2023.2265659).

**LLM jüri davranışı (hipotetik):**
- 14 Mayıs öncesi Bull/Bear arasındaki **disagreement DRAMATIK artardı** — siyasi belirsizlik = ortodoks politika dönüşü mü, devam mı? İki LLM birbirinden farklı yorumlar üretir. → `llm_agreement_scalar ≈ 0.0` → SKIP.
- 15 Mayıs sabahı %6 düşüşü engellemese de, **pozisyon almamış olmak büyük drawdown koruması**.
- 28 Mayıs sonrası belirsizlik çözüldüğünde her iki LLM consensus'a varır → pozisyona dönüş.

**Değer önerisi:** Belirsiz dönemlerde LLM jüri "panik satışından" çok "panik girişimden" korur. Drawdown koruma açısından net pozitif.

**Hindsight bias uyarısı:** Yukarıdaki "muhtemelen olurdu" yorumu **post-hoc**dur. Gerçek davranış RR-018 backtest framework'ünde Mayıs 2023 LLM call'ları replay edilerek test edilmelidir — ancak LLM API'ları o tarih için aynı modelleri sunmaz (model versiyonları değişti). En iyi durumda **stylized simulation** yapılır.

### 11.2 Haziran 2023 Politika Değişikliği

**Olay:** Mehmet Şimşek Hazine ve Maliye Bakanı, Hafize Gaye Erkan TCMB Başkanı olarak Haziran 2023 başında atandı. **22 Haziran 2023 TCMB Para Politikası Kurulu kararı (Press Release 2023-22):** Politika faizi (bir-haftalık repo) **%8.5 → %15** (+650bp); Türkiye'nin Mart 2021'den bu yana ilk faiz artırımı. TCMB statement verbatim: *"The Monetary Policy Committee has decided to increase the policy rate (the one-week repo auction rate) from 8.5 percent to 15 percent."* World Bank Türkiye Economic Monitor Ekim 2024: *"The CBRT increased the policy rate by 41.5 percentage points from 8.5 percent in May 2023 to 50 percent in March 2024, keeping it constant since."* Final hike 21 Mart 2024 (TCMB 2024-14).

**LLM training data cutoff problemi:**
- Claude Opus 4.7 ve GPT-5.4 training data cutoff 2024 H2 veya 2025 başı; Haziran 2023 sonrası ortodoks pivot **biliniyor**.
- ANCAK: Şubat–Mayıs 2023 dönemini canlı izleyen bir LLM yoktu (Mayıs 2023 mevcut modeller GPT-3.5 / Claude 2 idi).
- maintainer'ın 2026'da RR-019 implement ederken: model knowledge cutoff yeni rejimi (50% faiz) biliyor, **eski paradigmaya (%8.5 faiz) takılı kalmaz**.

**Rejim değişikliği LLM riski:** Bir sonraki rejim değişikliği (faiz tekrar inişe geçer; nitekim Aralık 2024'te TCMB %50 → %47.5 indirimle gevşemeye başladı, TCMB Press Release 2024-69; Ocak 2026'da %37'ye kadar indi) olursa LLM yeni rejimi training data'sında **bilmeyebilir**. RR-017 HMM regime detector LLM jüri için **upstream filter** rolü oynar: HMM "rejim değişti" sinyali verirse LLM çıktısına şüpheyle yaklaşılır, `llm_agreement_scalar`'a haircut uygulanır.

### 11.3 Hindsight Bias Notu

Hem 11.1 hem 11.2 **hindsight'tır**. Gerçek değer ancak RR-018 backtest framework'ünde **out-of-sample** test ile ölçülebilir. Bu rapor "LLM jüri belirsizlik durumlarında pozisyon büyüklüğünü dindirme yönünde çalışacaktır" hipotezini sunar, kanıt **değildir**.

---

## 12. Implementation Roadmap (Kısa)

**Hedef Okuyucu:** Phase 6+ maintainer/arastirma katmani. "AUM 500K TL aşıldığında ne yapılacağı."

> Bu rapor uzak-zaman (Q1 2027+) raporudur, roadmap kısa tutulmuştur. Her faz başlangıcında detay tasarım dokumanı yazılır.

| Faz | Süre | İçerik | Tetikleyici |
|---|---|---|---|
| **Faz 0 — Bekle** | Şimdi → AUM 500K eşiği | Sadece bu rapor referans. Hiçbir implementation yok. | AUM eşiği veya junior quant pozisyon |
| **Faz 1 — 2-LLM MVP** | 1 hafta | `strategist_v2.py` oluşturulur; Opus 4.7 + GPT-5.4 paralel; disagreement detection; output backward-compat (v1 default kalır) | Faz 0 koşulu |
| **Faz 2 — Türkçe Test Framework** | 2 hafta | Bölüm 4 deliverable çalıştırılır: 100 KAP örnek, 2 rater Cohen's κ, LLM run, metrics tablosu, ranking | Faz 1 tamam |
| **Faz 3 — Production Entegrasyon** | 2 hafta | position_sizer v4 (opsiyonel feature flag); RR-018 backtest harness'a plug; 6 ay paper-trade gözlem | Faz 2 metric'ler tatminkâr |
| **Faz 4 — Optimizasyon** | 1 hafta | Prompt caching aktif, selective debate (iMAD), batch API her yerde | Aylık cost > $20 olduğunda |
| **Faz 5 — 7-Agent Expansion** | 1 ay (opsiyonel) | TradingAgents fork → BIST adaptasyon (Türkçe promptlar, KAP, EVDS, holding NAV). RR-018'de 5 yıl backtest. | AUM 1M+ ve Faz 3 net pozitif Sharpe katkısı |

**Karar matrisi:**
- Faz 3 sonrası Sharpe katkısı < 0.1 → Faz 5'e geçme, mevcut sistemde kal.
- Faz 3 sonrası max drawdown -%10'dan -%7'ye düşmüş → Faz 5'e geç (downside protection değerli).
- Aylık cost > $25 ve katkı belirsiz → Sonnet 4.6 × 2 alternatifine geç (ucuz, hâlâ jüri).

---

## 13. Örnek Portföy Analizi

Örnek 3 hisse (TTKOM, KCHOL, ENERY) üzerinden LLM jüri ne öğretir.

### 13.1 Örnek Hisseler

| Hisse | Sektör | Mevcut Conviction (RR-010 Smart Money + L1–L5) |
|---|---|---|
| TTKOM | Telekom | Yüksek (dolar-bazlı kâr, defansif) |
| KCHOL | Holding | Orta (RR-013 NAV iskonto cazip) |
| ENERY | Enerji | Orta-yüksek (tema mome) |

### 13.2 LLM Jüri Davranış Senaryoları

**Senaryo 1: TTKOM çeyreklik kâr sonrası**
- Bull LLM (Opus): "Dolar bazlı kâr büyümesi sürüyor, defansif tema, BUY-MEDIUM."
- Bear LLM (GPT-5.4): "TR enflasyonu yavaşlama eğiliminde, defansif premium daralabilir, HOLD."
- `llm_agreement_scalar ≈ 0.5` → mevcut pozisyon koru, **artırma**.

**Senaryo 2: KCHOL NAV iskontosu daralma**
- Bull: "Iskonto %40 → %25, mean-reversion alfa cazip, BUY-STRONG."
- Bear: "Holding rallisi sona yaklaşıyor, NAV iskontosu daha da daralırsa upside sınırlı, HOLD."
- `llm_agreement_scalar ≈ 0.5` → yarım pozisyon. RR-013 alphası burada **doğrulanmaz** (LLM çelişiyor) → maintainer diskresyoner: RR-013 ana sinyal, LLM modifier; pozisyon büyük tutulur ama LLM uyarı not edilir.

**Senaryo 3: ENERY tema momentum kırılması**
- Bull: "Yenilenebilir enerji devlet teşvik haberi, BUY-STRONG."
- Bear: "Hisse 3 ayda %40 yükseldi, technical aşırı alım, SELL-MEDIUM."
- `llm_agreement_scalar ≈ 0.0` (çelişki) → **SKIP/REDUCE**. Long-only'da pozisyon yarıya indirilir veya yeni alım yapılmaz.

### 13.3 "maintainer'ın Diskresyoner Kararına" Katkı

LLM jüri **OTOMATİK ORDER ÜRETMEZ** (DEC-010). Çıktı:
1. Sayısal `llm_agreement_scalar` (position_sizer'a girer).
2. ~800 token bullet-format advisory: "Bull diyor ki X; Bear diyor ki Y; uyuşmazlık skoru Z."
3. maintainer her sabah daily report'ta bunu okur, RR-010/012/017 sinyalleriyle çapraz kontrol eder, **final pozisyon kararını verir**.

LLM jüri maintainer'ın **mental tartışma partneri**dir, otomat değil. Hatasız kalibrasyon hedefi değildir — hedef "maintainer'ın gözden kaçırdığı karşı argümanı görünür kılmak"tır.

---

## 14. Python Implementation Hintleri (Kavramsal)

**Hedef Okuyucu:** arastirma katmani. **PRODUCTION-READY DEĞİL** — kavramsal signature + docstring + comment. arastirma katmani bunu skelet alıp gerçek implementation yazar.

```python
# src/agents/strategist_v2.py
# KAVRAMSAL — production değil. arastirma katmani skelet olarak kullanır.

from dataclasses import dataclass
from typing import Literal, Optional
import asyncio

@dataclass
class JuryOutput:
    """Tek bir LLM jüri üyesinin yapılandırılmış çıktısı.
    
    sentiment ordinal skala (long-only context'te SELL kullanılmaz ama
    encoder olarak bırakılır; jüri logic'inde SELL → HOLD treatment).
    confidence verbalized (Lin et al. 2022 calibration approach).
    """
    sentiment: Literal["BUY-STRONG", "BUY-MEDIUM", "HOLD", 
                       "SELL-MEDIUM", "SELL-STRONG", "IRRELEVANT"]
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    reasoning: str   # ≤ 200 Türkçe karakter
    raw_response: dict  # debug için ham JSON


@dataclass
class StrategistV2Report:
    """2-LLM jüri sonrası birleşik output.
    
    llm_agreement_scalar position_sizer v4'e geçer; 0.0 = SKIP, 1.0 = full.
    advisory_text maintainer'ın okuduğu Markdown.
    """
    bull_output: JuryOutput
    bear_output: JuryOutput
    disagreement_score: float            # ∈ [0.0, 1.0], 0 = agree
    llm_agreement_scalar: float          # ∈ [0.0, 1.0], position_sizer için
    advisory_text: str                   # ~800 token Türkçe Markdown
    final_recommendation: Literal["FULL_BUY", "HALF_BUY", "HOLD", "SKIP"]


async def run_jury(
    daily_report: str,
    bull_model: str = "claude-opus-4-7",
    bear_model: str = "gpt-5.4",
    use_cache: bool = True,
    selective_debate: bool = True,
) -> StrategistV2Report:
    """2-LLM jüri orchestrator.
    
    selective_debate=True ise iMAD prensibi (arXiv:2511.11306):
      - Bull önce çalışır; eğer conviction HIGH ise Bear atlanır.
      - Bear sadece HOLD/MEDIUM/LOW conviction durumunda tetiklenir.
    
    use_cache=True ise system prompt + sabit context cache'lenir
    (Anthropic prompt caching docs; cache read = 0.10x input).
    
    DEC-010 boundary: output advisory only, executive değildir.
    Hiçbir trade order üretilmez; sadece advisory + scalar.
    
    NOT: Bu signature kavramsaldır. arastirma katmani gerçek implementation'da:
      - Anthropic AsyncClient + OpenAI AsyncClient kullanır
      - timeout 30s circuit breaker ekler  
      - max_tokens cap (1500 each)
      - retry logic (exponential backoff, 3 attempts)
      - usage cost tracking (FinOps)
      - logging structured JSON (cost, latency, agreement_score)
    """
    # 1. Build prompts (Türkçe Bull advocate vs Bear advocate)
    # 2. Bull call (mandatory)
    # 3. Bear call (conditional on selective_debate flag)
    # 4. Parse & validate JSON outputs
    # 5. Compute disagreement_score from ordinal distance
    # 6. Map to llm_agreement_scalar (Bölüm 3.3 tablosu)
    # 7. Synthesize advisory_text Markdown
    # 8. Return StrategistV2Report
    raise NotImplementedError("arastirma katmani fills this in; this is a sketch.")


def compute_agreement_scalar(bull: JuryOutput, bear: JuryOutput) -> float:
    """Bölüm 3.3 tablosundaki LLM agreement scalar hesabı.
    
    Ordinal distance: BUY-STRONG=2, BUY-MEDIUM=1, HOLD=0, SELL-MEDIUM=-1, SELL-STRONG=-2.
    Distance 0 (aynı): 1.0
    Distance 1 (komşu, aynı yön): 0.85
    Distance 2 (BUY+HOLD): 0.50
    Distance ≥ 3 (zıt yön): 0.00
    
    Sanity tests (Bölüm 3.3'te listelendi):
      - both BUY-STRONG → 1.0
      - BUY-STRONG + BUY-MEDIUM → 0.85
      - BUY + HOLD → 0.50
      - BUY + SELL → 0.00
    """
    # ... implementation skeleton
    raise NotImplementedError


# Backward-compat:
# src/agents/strategist.py (v1) DEFAULT olarak kalmaya devam eder.
# strategist_v2.py opt-in feature flag ile aktive edilir.
# Bütün backtest sonuçları v1 baseline'a karşı raporlanmalıdır.
```

**Kritik notlar:**
- Bu kod **derlemez** (NotImplementedError); skelet niteliğindedir.
- Production'da Anthropic ve OpenAI client'ları farklı API conventions kullanır; arastirma katmani her ikisini de wrap eder.
- `disagreement_score` ↔ `llm_agreement_scalar` ilişkisi: scalar = 1 − disagreement (lineer) yerine ordinal distance fonksiyonu öneriliyor (Bölüm 3.3).
- Async parallel call: `asyncio.gather(bull_task, bear_task)`, total latency = `max(bull, bear)`.

---

## 15. Akademik Kaynak Özeti

**Hedef Okuyucu:** arastirma katmani/araştırmacı maintainer. Her madde 2–3 cümle özet + DOI/arXiv URL.

1. **Du Y., Li S., Torralba A., Tenenbaum J. B., Mordatch I.** (2023). "Improving Factuality and Reasoning in Language Models through Multiagent Debate." arXiv:2305.14325. ICML 2024. Birden fazla LLM tartıştığında matematik, strateji ve gerçeklik görevlerinde performans artar; aritmetik %81.8 vs tek-ajan %67.0; GSM8K %85.0 vs %77.0. Black-box; sadece API yeterli. RR-019 ana akademik temeli. https://arxiv.org/abs/2305.14325

2. **Liang T., He Z., Jiao W., Wang X., Wang Y., Wang R., Yang Y., Shi S., Tu Z.** (2023/2024). "Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate." arXiv:2305.19118. EMNLP 2024. Tek LLM self-reflection'ın "Degeneration-of-Thought" probleminden muzdarip; "tit-for-tat" multi-agent debate (MAD) bu sorunu kırıyor. RR-019 Bull/Bear rol tasarımının temeli. https://arxiv.org/abs/2305.19118

3. **Xiao Y., Sun E., Luo D., Wang W.** (2024/2025 v7). "TradingAgents: Multi-Agents LLM Financial Trading Framework." arXiv:2412.20138. 7 uzman ajan + Bull/Bear researcher + Risk team. 3 hisse üzerinde 3 aylık backtest'te Sharpe 5.60–8.21 (yazarların kendi uyarısı: kısa pencere artifactı). RR-019 7-agent yol haritası için referans. https://arxiv.org/abs/2412.20138; github.com/TauricResearch/TradingAgents

4. **Jiang B.** (2026). "DiscoUQ: Structured Disagreement Analysis for Uncertainty Quantification in LLM Agent Ensembles." arXiv:2603.20975. Disagreement structure (kanıt örtüşmesi, argüman gücü, sapma derinliği) AUROC 0.802, ECE 0.036 — vote-counting üzerinde belirgin gelişme. RR-019 v2 (Phase 7+) için ileri kalibrasyon yöntemi. https://arxiv.org/abs/2603.20975

5. **Fan W., Yoon S., Ji H.** (2025). "iMAD: Intelligent Multi-Agent Debate for Efficient and Accurate LLM Inference." arXiv:2511.11306. Abstract verbatim: "reduces token usage by up to 92% while also improving final answer accuracy by up to 13.5%." RR-019 "selective debate" optimization stratejisinin literatür temeli. https://arxiv.org/abs/2511.11306

6. **Liu T., Wang X., Huang W., Xu W., Zeng Y., Jiang L., Yang H., Li J.** (2024). "GroupDebate: Enhancing the Efficiency of Multi-Agent Debate Using Group Discussion." arXiv:2409.14051. Agent gruplama + grup-arası özet ile token maliyeti %45–51 düşer, doğruluk %11–25 artar. RR-019 token verimliliği stratejisi. https://arxiv.org/abs/2409.14051

7. **Kadavath S. et al.** (2022). "Language Models (Mostly) Know What They Know." arXiv:2207.05221. Büyük LLM'ler P(True) self-evaluation skorlarını kalibre edilmiş şekilde üretebilir. RR-019 verbalized confidence kullanımının temeli. https://arxiv.org/abs/2207.05221

8. **Lin S., Hilton J., Evans O.** (2022). "Teaching Models to Express Their Uncertainty in Words." arXiv:2205.14334. GPT-3 verbalized probability ("90% confidence") kalibre edilmiştir, logit'lere ihtiyaç yok. RR-019 JSON output şemasında `confidence: HIGH/MEDIUM/LOW` field'ı bu bulguya dayanır. https://arxiv.org/abs/2205.14334

9. **Lopez-Lira A., Tang Y.** (2023/2025 v6). "Can ChatGPT Forecast Stock Price Movements? Return Predictability and Large Language Models." arXiv:2304.07619. Journal of Financial Economics forthcoming. Post-cutoff haber başlıklarında GPT-4 ABD piyasası başlangıç tepkisi için **%93.3 günlük portföy hit rate** (negatif örneklerde %88.8); küçük hisse ve negatif haberlerde drift tahmini. "Forecasting ability generally increases with model size." "Strategy returns decline as LLM adoption rises." RR-019 LLM-in-trading akademik motivasyonu. https://arxiv.org/abs/2304.07619

10. **Türker B. et al.** (2025). "TabiBERT." arXiv:2601.12538 (Aralık 2025). TabiBench Türkçe NLP benchmark'unda %77.58 total avg, BERTurk +1.62 pp önde. Türkçe encoder SOTA. RR-019 Bölüm 4 baseline. https://huggingface.co/boun-tabilab/TabiBERT

11. **Xiao Y., Sun E., Chen T., Wu F., Luo D., Wang W.** (2025). "Trading-R1: Financial Trading with LLM Reasoning via Reinforcement Learning." arXiv:2509.11420. RL fine-tune ile finansal LLM. RR-019 Phase 7++ için referans (RL-augmented jury). https://arxiv.org/abs/2509.11420

12. **Yang Y., Christopher M., UY S., Huang A.** (2020). "FinBERT: A Pretrained Language Model for Financial Communications." arXiv:2006.08097. Finansal sentiment için BERT-domain-adapted. Türkçe değil ama financial-domain sentiment'in baseline'ı. Lopez-Lira'nın 2023 paper'ında karşılaştırıldı: LLM'ler FinBERT'i aştı. https://arxiv.org/abs/2006.08097

13. **Anthropic Inc.** (2026). "Claude Opus 4.7 model card and pricing." claude.com/pricing; platform.claude.com/docs/en/about-claude/pricing. Mayıs 2026 fiyat snapshot: Opus 4.7 $5/$25, Sonnet 4.6 $3/$15, Haiku 4.5 $1/$5; prompt caching cache read 0.10× input.

14. **OpenAI Inc.** (2026). "OpenAI API pricing." openai.com/api/pricing. Mayıs 2026: GPT-5.5 $5/$30, GPT-5.4 $2.50/$15, GPT-5.4 Nano $0.20/$1.25; cached input %90 indirim.

15. **Google LLC** (2026). "Gemini API pricing." ai.google.dev/gemini-api/docs/pricing. Mayıs 2026: Gemini 2.5 Pro $1.25/$10 (≤200K), Gemini 2.5 Flash $0.30/$2.50, Gemini 2.5 Flash-Lite $0.10/$0.40; batch API %50 indirim.

---

## 16. Kısıtlar & Caveat'lar

**Hedef Okuyucu:** maintainer. Bu raporun ne yapamadığı ve ne zaman geçersizleşeceği.

1. **LLM evolution hızı (3–6 ay model update).** Mayıs 2026 snapshot tablo Q3 2026'da büyük olasılıkla geçersiz olur. Mekanizma: `last_updated: 2026-05-24` header alanı; her major Anthropic/OpenAI model release sonrası 2 hafta içinde Bölüm 3.1 ve Bölüm 7 fiyat tabloları yeniden kontrol edilir. Eğer yeni model fiyatı %20+ farklı veya yeni Türkçe yetenek varsa **rapor revize edilir**.

2. **Türkçe context ABD/EU'dan zayıf.** Lopez-Lira & Tang (2025) ABD GPT-4 %93.3 portföy hit rate; Türkçe için bilinen tek benchmark TabiBench (encoder, %77.58 SOTA). Generative LLM Türkçe finansal context'te kalibre edilmiş bağımsız değerlendirme **yoktur**. Bölüm 4 test framework arastirma katmani tarafından çalıştırılana kadar Türkçe accuracy beklentisi **proxy + sezgi** seviyesindedir.

3. **Maliyet kontrolü ihtiyacı.** 2-LLM ve 7-agent senaryolarının tamamı **prompt caching aktif şart**. Cache uygulanmazsa aylık $25–35'a kolayca tırmanır. FinOps disiplini (usage alert $25, max_tokens cap, batch API where async OK) **zorunludur**.

4. **Akademik literatür finansta sınırlı.** Multi-agent debate literatürü 2023–2025 arasında patladı ancak **finansta** uygulamaların sayısı azdır: TradingAgents (Xiao 2024), FinMem, FinAgent, TradingGroup (2025). Hiçbir çalışma **çoklu yıl out-of-sample backtest** sunmadı; Sharpe sonuçları kısa pencere artifactı şüphesi taşıyor. RR-019 alpha bekleyişleri **konservatif** tutulmalı.

5. **AI black box / interpretability.** LLM'in nasıl "BUY-STRONG" dediği opak. Reasoning field açıklama sağlar ama post-hoc rationalization olabilir (LLM her zaman doğru sebep vermez). maintainer ve arastirma katmani LLM çıktısına **asla sebep gösterilen veriyi doğrulamadan güvenmemelidir**.

6. **RR-018 entegrasyonu sonradan revize gereği.** Bu rapor RR-018 backtest framework'ünün "var" varsayımı altında yazıldı. RR-018 detayları (örn. trade execution model, slippage, transaction cost ayarları) RR-019'un disagreement_score → llm_agreement_scalar mappingini etkileyebilir. Faz 3'te (production entegrasyon) RR-019 mapping tablosu RR-018 ampirik çıktısına göre yeniden kalibre edilir.

7. **Echo chamber gerçek risk.** Anthropic ve OpenAI farklı sağlayıcı olsa da, eğitim verisi büyük ölçüde aynı (Common Crawl, Wikipedia, GitHub). İki LLM'in BIST hakkındaki bilgileri **highly correlated**; bağımsızlık göründüğü kadar yüksek değildir. Aylık disagreement rate metriği ile monitör edilmeli; <%5 düşerse echo chamber alarmı.

8. **Lopez-Lira "alfa daralması" hipotezi.** Aynı çalışma uyarıyor: "Strategy returns decline as LLM adoption rises." Türkiye'de LLM-trading adopsiyonu hâlâ düşük (Bölüm 10) — penceresi açık, ama ABD'de adopsiyon yayıldıkça BIST'e sıçraması beklenir. RR-019 alpha penceresi muhtemelen 2026–2028; 2029+'de incremental getiri düşer.

9. **Twitter login-wall.** Türk retail fintwit gözlemleri (kim ChatGPT/Claude kullanıyor, hangi pattern'ler) erişilemiyor. Bölüm 10.1 retail kullanım anekdotal kalıyor; resmi anket yok.

10. **Hindsight bias on crisis periods.** Bölüm 11'deki "LLM jüri 2023 Mayıs seçim haftasında muhtemelen pozisyon almazdı" yorumu post-hoc'tur. Gerçek davranış ancak RR-018 backtest framework'ünde stylized simulation ile test edilebilir.

---

*Son revize: 2026-05-24. Phase 6+ (Q1 2027+). Priority: Nice-to-have. Şimdi sadece araştırma + tasarım. Implementation AUM eşiği veya junior quant pozisyon sonrası başlar.*