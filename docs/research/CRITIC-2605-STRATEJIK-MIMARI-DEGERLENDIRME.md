# CRITIC 2605 — Stratejik Mimari Değerlendirme: Mevcut Durum, Teşhis ve Yol Haritası

**Tarih:** 2026-05-26  
**Yazar:** Arastirma katmani — maintainer ile beyin fırtınası oturumu  
**Kapsam:** L1/L2/L6 mimari analizi, "bot vs. danışman" kimlik sorusu, LLM'in gerçek rolü, uzun vadeli yön  
**Bağlı Backtest:** D-153b (stub-free H2 2025), D-153c (2024 full year)  
**Status:** maintainer'a iletilecek stratejik memo

---

## Yönetici Özeti

Mevcut sistem iki ayrı kimlik arasında sıkışmış durumda: **kural tabanlı bir sinyal botu** ile **bağlamsal bir yatırım danışmanı**. Bu kimlik belirsizliği hem mimari kararlara hem de backtest sonuçlarına yansıyor.

2024 full-year stub-free backtest sonuçları:
- Sistem: **+15.01%** — BIST100: **+29.71%** — Alpha: **−14.70pp**
- Win rate: **56%**, Profit Factor: **2.32**, Max DD: **−6.91%**

Teşhis: Negatif alpha'nın **yalnızca L3/L4/L5 eksikliğinden** kaynaklandığı sonucuna varmak yanlış. Mevcut L1/L2/L6 katmanlarında, tam stack devrede olsa bile performansı sınırlayacak mimari sorunlar var.

---

## Bölüm 1: L1/L2/L6 Mimari Teşhis

### 1.1 L1 (Technical Layer) — Üç Gerçek Problem

**Problem A: Çelişen felsefeler, rejim tespiti yok**

```python
# RSI sub-score: Mean-reversion felsefesi
RSI < 30 → skor 80  (oversold = al)
RSI > 80 → skor 10  (overbought = satma)

# MA sub-score: Trend-following felsefesi  
price > MA20 > MA50 > MA200 → skor 80  (momentum = al)
```

Bu iki yaklaşım **fundamentally çelişiyor**. Güçlü bir boğa trendinde RSI sürekli 60-75 bandında seyreder. Sistem bunu "neutral" sayıp skoru ortalara çekiyor; MA ise "al" diyor. Sonuç: birbiriyle savaşan sinyaller.

Gerçek dünyada bu ayrım **rejim tespiti** ile çözülür: trend güçlü ise (ADX > 25) momentum filtresi öne çıkar, yatay piyasada mean-reversion filtresi. Mevcut sistemde bu yoktur.

**Problem B: Sub-score'lar eşit ağırlıklı**

```python
final_score = sum(sub_scores) / len(sub_scores)  # Basit ortalama
```

RSI, MA alignment, momentum, volume surge, 52-haftalık yakınlık — beşi de eşit ağırlık alıyor. Oysa literatür MA sinyallerini RSI'dan daha güvenilir buluyor (özellikle 200MA'nın üstü/altı). 52w yakınlık ise bağlama göre hem bullish (momentum) hem bearish (overbought satış baskısı) okuyabilir — ikisi de mümkün, sistem birini seçemiyor.

**Problem C: Volume surge binary**

`volume_surge: True/False` — hacim ortalamanın %10 üstü de, %400 üstü de aynı muameleyi görüyor. Bu bilgi kaybı. Hacim hem yönü hem gücü sinyalemeli; şu anda ikincisi yok.

---

### 1.2 L2 (Macro Layer) — İki Gerçek Problem

**Problem A: BIST100 circular feedback**

```python
ASSET_DIRECTIONS = {'BIST100': 1.0, ...}  # BIST100 hem benchmark hem sinyal
```

BIST100 hem sistemimizin performansını ölçtüğümüz referans hem de BUY kararını etkileyen makro girdi. BIST yükselince L2 skoru iyileşiyor → daha fazla BUY sinyali. Bu pozitif geri besleme döngüsü boğa piyasasında sistemi **endekse karşı geç girişe** zorluyor: zaten yükselmiş endeksi görünce alıyoruz.  ### ÖNEMLİ FİKİR

Daha temiz alternatif: BIST100'ü makro katmandan çıkarmak, yerine yabancı yatırımcı net akışı (L5'te zaten var) veya endeks momentum farkı (BIST/EM relatif performans) koymak.

**Problem B: Statik korelasyonlar, kırılan rejimler**

```python
'SP500': 1.0, 'USDTRY': -1.0  # Her zaman böyle değil
```

2024 Q1'de TCMB agresif faiz artışı yaptı, TL stabilize oldu. Bu dönemde BIST-SP500 korelasyonu **tersine döndü** — SP500 düşerken BIST yükseldi. Statik ağırlıklar bu rejim değişikliğini görmüyor, bir süre yanlış yönde sinyal üretiyor.

Not: RR-017 (HMM Regime Detection) bu sorunu doğru teşhis ediyor ve ENABLE_HMM_WEIGHTS mekanizmasıyla çözüm öneriyor. Aktivasyonu AG-001'e bağlı; bu bağımlılık meşru ve korunmalı.

---

### 1.3 L6 (Risk Layer) — Matematiksel Anlamsızlık

```python
RISK_BASE_SCORE = 70   # Her zaman 70'ten başlıyor
# MASTER_WEIGHTS["risk"] = 0.03
```

**Matematiksel gerçek:** L6'nın composite'e maksimum katkısı = 70 × 0.03 = **2.1 puan**.  
En kötü senaryoda (tüm cezalar uygulanmış, skor sıfır) bile L6'nın etkisi 0 × 0.03 = 0 puan.  
Pratik aralık: composite'i yaklaşık **0 ile 2.1 puan** arasında etkiliyor.

Bu gürültü seviyesinde. L6 ya **ciddi redesign + ağırlık artışı** (minimum 0.10, pozisyon-seviyesi portföy riski eklenerek) almalı ya da mevcut haliyle kalması için açık bir gerekçe belgelenmeli.

---

## Bölüm 2: Backtest Bulguları — Dürüst Okuma

### 2.1 "Ortalama Bot" Karşılaştırması

| Strateji Tipi | Win Rate | Alpha (vs. kendi benchmark) |
|---|---|---|
| Basit RSI/MA crossover | %40–48 | −5% ile −15% |
| Retail multi-indicator | %48–55 | −3% ile +5% |
| **Bizim sistem (L1+L2+L6)** | **%56 (2024), %75 (H2 2025)** | **−14.7% (2024)** |
| Iyi kalibre quant fon | %55–65 | +2% ile +8%/yıl |
| Pasif BIST100 endeks | N/A (tanım gereği) | 0% |

**Sinyal kalitesi açısından**: Ortalamanın üstünde. Win rate %56, profit factor 2.32, max DD −6.91% — bu rakamlar basit botların çok üstünde.

**Getiri açısından**: Pasif endeks yatırımı sistemi yiyor (+29.7% vs +15%).

Bu **aktif yönetimin evrensel sorunudur**. S&P SPIVA verisine göre aktif hisse fonlarının ~%80'i 10 yılda kendi benchmark endeksinin gerisinde kalıyor. Bizim sonuç bu genel tablonun dışında değil. Ama "genel tablonun içinde olmak" hedef olmamalı.

### 2.2 2024 H1 / H2 Kırılımı — Kritik Bulgu

| Dönem | Trade | Win Rate | Avg P&L |
|---|---|---|---|
| H1 2024 (Jan–Jun) | 40 | **%32.5** | +1.40% |
| H2 2024 (Jul–Dec) | 85 | **%67.1** | +5.26% |

H1'deki %32.5 win rate alarm verici. 2024 Q1, TCMB'nin agresif faiz artışı yaptığı, TL'nin hızlı değer kazandığı, yabancı akışlarının geri döndüğü dönemdi. Sistem bu rejim değişikliğini okuyamadı ve aynı eşiklerle girmeye devam etti. **Rejim tespiti eksikliğinin somut maliyeti.**  ## ÖNEMLİ !!!!

---

## Bölüm 3: Kimlik Sorusu — Bot mu, Danışman mı?

### 3.1 Mevcut Gerçeklik

Sistem şu anda şunları yapıyor:
1. L1-L6 sayısal skorlar üretiyor (kural tabanlı, deterministik)
2. Bu skorları composite'e dönüştürüyor
3. Claude bir **anlatı yazıyor** — ama BUY/SELL kararı çoktan verilmiş

Yani Claude şu anda bir **reporter**, signal generator değil. Karar sayısal modelin kararı; Claude sadece bunu açıklıyor.

### 3.2 Hedeflenen Gerçeklik (Doğru Vizyon)

maintainer'ın vizyon ifadesi:
> *"Uzman bir danışman gibi olsun istiyorum. Çıkan sonuçlara bakayım, yapay zekanın mevcut duruma dair analizlerini okuyayım."*

Bu vizyon doğru. Ama uygulanabilmesi için mimaride paradigma değişikliği gerekiyor:

**Şu an:** Sayısal model → karar → Claude açıklar  
**Hedef:** Sayısal model (backbone) + Claude analizi (genuine input) → karar

### 3.3 Hedge Fund Anatomisi — Gerçekçi Karşılaştırma

Profesyonel hedge fonlar üç temel modelde çalışır:

**Pure Quant** (Renaissance Medallion): Tamamen matematiksel, insan takdiri yok. Giriş bariyeri aşırı yüksek — terabytlar veri, PhD ekipler, kapalı sistem. Replike edilemez.

**Discretionary Macro** (Druckenmiller/Soros tarzı): İnsan fund manager büyük thematic bahisler yapıyor. Makro narrativi okuma, policy intent anlama, zamanlamayı sezgiyle belirleme. Ölçeklenemiyor — bağlı kişiye.

**Hybrid** (Two Sigma Advisers, Bridgewater tarzı): Quant sinyaller üretir, insan (veya LLM) portföy kararını bağlama göre değerlendirir. **Bizim için uygun olan model bu.**

Tek kişilik bir BIST operasyonu için en rasyonel seçim: quant backbone + LLM'in gerçek sinyal üretici rolü.

---

## Bölüm 4: LLM'in Gerçek Rolü — Ne Yapabilir, Ne Yapamaz

### 4.1 Claude'un Gerçek Avantajları

**Yapabildiği şeyler:**

- KAP duyurularını tam metin olarak okumak — kategori değil, içerik. "Temettu" kategorisi değil: "Yönetim kurulu %8 nakit temettü kararı aldı, ama geçen yıl %15 vermişti, bu ciddi düşüş" yorumu.
- TCMB Para Politikası Kurulu toplantı metnini okumak — "faiz sabit" sayısal kararı değil, forward guidance dili: "temkinli" mi, "kararlı" mı, "veri bağımlı" mı kullanılıyor?
- Sektörel bağlamı anlamak — "FROTO zayıf rapor verdi ama bu döngüsel mi yapısal mı?" sorusunu cevaplamak.
- Çapraz piyasa narratifi kurmak — "Fed pivot beklentisi + TL stabilizasyonu + seçim öncesi teşvik paketi = BIST'e kısa vadeli para girişi" gibi zincirleme okuma.
- Yönetim kalitesini dilden çıkarmak — konferans çağrısı tonunu, yatırımcı sunumundaki commitment derecesini, geçmiş guidance isabet oranını değerlendirmek.

**Yapamadığı şeyler (dürüst liste):**

- Gerçek zamanlı fiyat verisi göremez — API olmadan market data yok.
- Kısa vadeli fiyat hareketini güvenilir biçimde tahmin edemez — bu literatürde çözülmemiş problem.
- Session'lar arası tutarlı olmayabilir — aynı soruyu iki farklı oturumda farklı cevaplayabilir. **Verification layer zorunlu.**
- Hallucination riski gerçek — özellikle spesifik sayısal iddialarda. Her LLM çıktısı doğrulanabilir kaynağa dayandırılmalı.

### 4.2 BIST'e Özgü LLM Avantajı

BIST iki nedenden dolayı LLM analizi için **özellikle verimli**:

1. **Bilgi asimetrisi yüksek**: BIST'e uluslararası analist coverage'ı az. Birçok orta ölçekli şirket için İngilizce kaynak yok. LLM Türkçe KAP metinlerini işleyebiliyor — bu S&P500 şirketlerinde olmayan bir avantaj.

2. **Kurumsal haberlerin fiyata etkisi ani ve büyük**: BIST'te retail yatırımcı dominasyonu var. KAP açıklaması geldiğinde "anlayan" ile "anlamayan" arasındaki bilgi farkı kapanması daha yavaş — bu farkı kapatan sistem avantaj sağlıyor.

---

## Bölüm 5: Stratejik Yol Haritası

### 5.1 Hızlı Kazanımlar (Mevcut Mimari İçinde, CB-014 Gerektirmez)

| # | Değişiklik | Etki | Karmaşıklık |
|---|---|---|---|
| 1 | BIST100'ü L2'den çıkar, yerine EM relatif güç | Circular feedback kaldırılır | Düşük |
| 2 | RSI sub-score'a ADX condition ekle (rejim tespiti) | H1 2024 tipi kayıp azalır | Orta |
| 3 | L6 ya redesign (ağırlık 0.10, ATR-bazlı) ya da composite'ten çıkar | Gürültü azalır veya anlamlı sinyal gelir | Orta |
| 4 | Volume surge için gradient (örn. 3 seviye: zayıf/güçlü/ekstrem) | L1 sinyal kalitesi artar | Düşük |

*Not: Bu değişiklikler PROJECT_GUIDE.md gereği spec + etkilenen dosyalar listesiyle maintainer onayına sunulmalı.*

### 5.2 Orta Vadeli (CB-014 Tamamlandığında)

- **L3 (KAP) full activation**: Sadece kategori değil, Claude duyuru metnini okuyor. Temettu açıklaması için: "önceki yıla göre artış/azalış", "yönetim açıklaması tonu", "sektör ortalamasıyla karşılaştırma"
- **L4 (Sentiment) Turkish optimization**: FinBERT İngilizce finansal metin için eğitilmiş. BIST için Türkçe finansal haber üzerinde fine-tune edilmiş model veya Claude native analiz daha iyi sonuç verir
- **L5 (Smart Money) strengthening**: BIST'te foreign investor flow en güvenilir leading indicator. Takasbank yabancı net akış + büyük lot işlem tespiti — bu katman muhtemelen en yüksek sinyal değerine sahip

### 5.3 Uzun Vade — Gerçek Hibrit Mimari

```
[Quantitative Backbone]          [LLM Intelligence]
L1 (Technical, regime-aware) ←→  KAP full-text reading
L2 (Macro, dynamic weights)  ←→  TCMB policy interpretation  
L3 (KAP, LLM-powered)        ←→  Macro narrative synthesis
L4 (Sentiment, Turkish NLP)  ←→  Market regime characterization
L5 (Smart Money, Takasbank)  ←→  Cross-asset correlation reading
L6 (Risk, ATR-based)         ←→  Portfolio-level risk assessment
        ↓                              ↓
   [Composite Score]          [Contextual Confidence]
             ↓
   [Final Advisory Output]
   "GARAN: BUY-STRONG (skor 74)
    Bağlam: TCMB faiz kararı sonrası banka hisseleri
    için yabancı alımı artıyor, KAP'ta yönetim
    güven veren forward guidance verdi, teknik
    formasyonu onaylıyor. Risk: TL volatilitesi."
```

Bu mimari artık bir "bot" değil. Bu bir **hybrid investment advisor**.

---

## Bölüm 6: Dürüst Performans Beklentisi

Tam stack devreye girdiğinde ne beklenmeli?

**Gerçekçi beklenti (akademik literatür ve benzer sistemlere göre):**
- Alpha: +5% ile +15%/yıl BIST100 üstü (CB-014 sonrası, tam stack)
- Win rate: %60-70 (L3/L4/L5 ile H2 2025'teki %75 civarı muhtemelen sürdürülebilir)
- Max DD: <%10 (mevcut stop-loss mekanizması korunursa)

**Neden bu kadar, daha fazla değil?**
- Piyasanın "boşluğu yok" iddiası yanlış — ama boşluk küçük ve erozyon hızlı
- Bir sistem iyi sonuç verince arbitraj davranışı artar, edge küçülür
- BIST için gerçek edge: hızlı KAP bilgisi işleme + Türkçe makro okuma (bu az replike ediliyor)

**Gerçek olmayan beklenti:**
- "Sürekli %30+ alpha" — bu ancak Renaissance Medallion seviyesinde, kapalı sistemde mümkün
- "Sıfır drawdown" — piyasa riski elimine edilemez, sadece yönetilebilir
- "Her dönemde BIST100'ü yenmek" — kötü makro dönemlerinde sistemin kaybetmesi normaldir

---

## Bölüm 7: Önerilen Sonraki Adım

**maintainer'a Öneri:**

1. Bu raporu okuyun, mimari bulgulara katılıp katılmadığınıza karar verin
2. Bölüm 5.1'deki hızlı kazanımları spec olarak sıralayın (ayrı D-XXX her biri için)
3. L6 redesign veya çıkarma kararını netleştirin — belirsiz bırakmayın
4. CB-014 unblocking için zaman tahmini yapın: bu tarih bilindi, Bölüm 5.2 planlanabilir
5. "LLM KAP metin okuma" protatipini küçük ölçekte test edecek bir araştırma speci açın (RR → CB → spec pipeline'ı)

---

## Ekler

### Ek A: 2024 Backtest Özet Sayılar

```
Dönem          : 2024-01-01 -- 2024-12-31
Universe       : 48/50 BIST50 ticker (KOZAA/KOZAL yfinance'ta yok)
Sistem getirisi: +15.01% (120,000 TL → 138,009 TL)
BIST100        : +29.71% (7,624 → 9,890, Jan 2 – Dec 30)
Alpha          : −14.70pp
Win rate       : 56.0% (125 closed trades)
Profit factor  : 2.32 (avg win 12.63% / avg loss 6.93%)
Max drawdown   : −6.91%
Mod            : stub-free (L1+L2+L6 only, L3/L4/L5 excluded)
```

*Not: `benchmark_return_pct: nan` bir metrics.py bug'ı — Jan 1 tatil günü NaN olunca `iloc[0]` NaN alıyor. BIST100 getirisi manuel hesapla +29.71%.*

### Ek B: Karşılaştırmalı Backtest Tablosu

| | 2025H2 Prod-Equiv | 2025H2 Stub-Free | 2024 Full Stub-Free |
|--|--|--|--|
| Trade (açılan/kapanan) | 0 (L3 tavan) | 97/45 | 255/125 |
| Getiri | — | +16.04% | +15.01% |
| BIST100 | — | +21.61% | +29.71% |
| Alpha | — | −5.57pp | −14.70pp |
| Win Rate | — | %75.6 | %56.0 |
| Profit Factor | — | — | 2.32 |
| Max DD | — | −2.70% | −6.91% |
| Sharpe* | — | −3.158* | −2.826* |

*Sharpe: metrics.py'de yıllık %42 rf vs. kısmen yıllıklaştırılmamış getiri kullanıyor; gerçek Sharpe daha az negatif. Sistematik bias, sonuçları karşılaştırırken baz alın ama mutlak değer olarak yorumlamayın.*

### Ek C: Mimari Sorun Öncelik Sıralaması

| Öncelik | Sorun | Etkisi | Çözüm |
|---|---|---|---|
| 🔴 Kritik | RSI/MA rejim çelişkisi | H1 tipi win rate çöküşü | ADX conditional + iki mod |
| 🔴 Kritik | BIST100 circular feedback | Geç giriş, endeksi taklit | L2'den çıkar |
| 🟡 Önemli | L6 matematiksel anlamsızlık | Gürültü, kaynak israfı | Redesign veya çıkar |
| 🟡 Önemli | Volume surge binary | Sinyal bilgi kaybı | 3 seviyeli gradient |
| 🟢 Orta | Statik makro korelasyonlar | Rejim değişikliğinde hata | HMM (RR-017, AG-001 bekleniyor) |
| 🟢 Orta | L4 Türkçe NLP kalitesi | Sentiment sinyal gürültüsü | CB-014 sonrası fine-tune |
