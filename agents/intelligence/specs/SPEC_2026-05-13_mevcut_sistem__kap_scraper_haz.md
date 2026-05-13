# Analiz: Sistem Durumu & Kritik Boşluk

Mevcut pipeline:
```
KAP Scraper → [?] → Daily Report
Macro Feed  → [?] → Daily Report
```

**Sorun:** İki veri kaynağı var, report var — ama ortada **sinyal üretimi yok**. Orchestrator ham veriyi görüyor, karar veremiyor.

---

# Öneri: SPEC — Signal Engine

## Gerekçe (3 cümle)

KAP + Macro verisi şu an raporlanıyor ama **trade edilemiyor**. Orchestrator'ün "al / sat / bekle" kararı vermesi için normalize edilmiş, skorlanmış sinyal vektörüne ihtiyacı var. Bu olmadan daily report sadece haber bülteni, hedge fund değil.

---

# SPEC: Signal Engine (Alpha Generator)

## Tanım
KAP event'lerini ve macro metriklerini alıp her hisse için **[-1, +1] normalize sinyal skoru** üreten modül. Orchestrator bu skoru doğrudan pozisyon kararına bağlar.

## Dosya Yapısı
```
src/
  signals/
    __init__.py
    engine.py          # Ana orkestrasyon
    kap_signals.py     # KAP event → sinyal dönüşümü
    macro_signals.py   # Macro feed → sinyal dönüşümü
    combiner.py        # Ağırlıklı sinyal birleştirme
    schema.py          # Pydantic modeller
  tests/
    test_signal_engine.py
intelligence/
  specs/
    SPEC_2025-XX-XX_signal-engine.md
```

## Fonksiyon İmzaları

```python
# kap_signals.py
def score_kap_event(event: KAPEvent) -> SignalVector:
    """
    KAP event tipine göre sinyal üretir.
    Örn: 'kâr açıklaması +%20 beklenti üstü' → +0.8
    """

def classify_event_type(raw_event: dict) -> EventCategory:
    """
    'ÖZEL DURUM', 'FİNANSAL RAPOR', 'ORTAKLIK YAPISI' → Enum
    """

# macro_signals.py
def score_macro_environment(macro_snapshot: MacroSnapshot) -> MacroSignal:
    """
    Enflasyon, faiz, USD/TRY trendi → risk-on / risk-off skoru
    """

def detect_regime(macro_history: list[MacroSnapshot]) -> MarketRegime:
    """
    'RISK_ON' | 'RISK_OFF' | 'TRANSITION' döner
    """

# combiner.py
def combine_signals(
    kap_signal: SignalVector,
    macro_signal: MacroSignal,
    weights: SignalWeights = DEFAULT_WEIGHTS
) -> FinalSignal:
    """
    Ağırlıklı ortalama + regime filtresi uygular.
    RISK_OFF'ta kap_weight *= 0.5
    """

# engine.py
def run_signal_engine(
    kap_events: list[KAPEvent],
    macro_snapshot: MacroSnapshot,
    universe: list[str]  # ticker listesi
) -> SignalReport:
    """
    Tüm pipeline'ı çalıştırır. Daily report'a beslenir.
    """
```

## Input/Output Formatları

```python
# Input: KAP Event (mevcut scraper'dan)
{
    "ticker": "THYAO",
    "event_type": "FINANCIAL_REPORT",
    "headline": "2024 Q3 net kâr 12.4 milyar TL",
    "timestamp": "2025-01-15T09:30:00",
    "raw_text": "..."
}

# Input: Macro Snapshot (mevcut feed'den)
{
    "usdtry": 34.2,
    "inflation_yoy": 47.1,
    "policy_rate": 45.0,
    "bist100_mom": -2.3,
    "timestamp": "2025-01-15"
}

# Output: FinalSignal
{
    "ticker": "THYAO",
    "signal_score": 0.73,        # [-1, +1]
    "direction": "LONG",          # LONG | SHORT | NEUTRAL
    "confidence": 0.81,           # [0, 1]
    "regime": "RISK_ON",
    "contributing_factors": [
        {"factor": "earnings_beat", "weight": 0.4, "score": 0.9},
        {"factor": "macro_environment", "weight": 0.3, "score": 0.6},
        {"factor": "sector_momentum", "weight": 0.3, "score": 0.5}
    ],
    "signal_timestamp": "2025-01-15T09:35:00",
    "expires_at": "2025-01-16T18:00:00"   # TTL
}

# Output: SignalReport (engine.py çıktısı)
{
    "generated_at": "2025-01-15T09:35:00",
    "regime": "RISK_ON",
    "signals": [FinalSignal, ...],   # universe'deki tüm hisseler
    "top_longs": ["THYAO", "EREGL"],
    "top_shorts": ["VESTL"],
    "universe_coverage": 0.94        # sinyal üretilen hisse oranı
}
```

## Bağımlılıklar
```
pydantic>=2.0
numpy>=1.24
pandas>=2.0
scikit-learn>=1.3    # normalize için
pytest>=7.0
```

## Test Kriteri

```python
# test_signal_engine.py

def test_earnings_beat_generates_positive_signal():
    event = KAPEvent(
        ticker="THYAO",
        event_type="FINANCIAL_REPORT",
        headline="Net kâr beklentinin %23 üzerinde"
    )
    signal = score_kap_event(event)
    assert signal.score > 0.5
    assert signal.direction == "LONG"

def test_risk_off_dampens_signals():
    macro = MacroSnapshot(usdtry=42.0, inflation_yoy=85.0, policy_rate=50.0)
    regime = detect_regime([macro])
    assert regime == "RISK_OFF"
    # RISK_OFF'ta hiçbir sinyal 0.9 üzerinde olmamalı
    assert combined_signal.score <= 0.9

def test_full_pipeline_returns_signal_report():
    report = run_signal_engine(
        kap_events=MOCK_EVENTS,
        macro_snapshot=MOCK_MACRO,
        universe=["THYAO", "EREGL", "VESTL"]
    )
    assert len(report.signals) == 3
    assert report.universe_coverage == 1.0
    assert all(-1 <= s.signal_score <= 1 for s in report.signals)

def test_signal_ttl_is_set():
    # Sinyalin geçerlilik süresi olmalı
    assert report.signals[0].expires_at > report.generated_at
```

---

## Orchestrator'e Katacağı Değer

| Şu An | Signal Engine Sonrası |
|---|---|
| "THYAO iyi haber aldı" | "THYAO: +0.73 sinyal, LONG, %81 güven" |
| Manuel yorum | Otomatik pozisyon önerisi |
| İki ayrı veri kaynağı | Tek unified karar vektörü |
| Daily report = bülten | Daily report = actionable brief |

**Bu SPEC onaylanırsa** → Builder'a gönderebilirim.