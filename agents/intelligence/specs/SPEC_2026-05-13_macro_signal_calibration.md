# SPEC: Macro Signal Per-Symbol Volatility Scaling

## Tanım
`score_macro_component()` fonksiyonu şu an tüm semboller için sabit ±5% threshold kullanıyor. Her sembol tipi için ayrı scaling faktörü tanımlanacak; forex/commodity/vix/equity grupları farklı normalize edilecek.

## Değiştirilecek Dosya
```
src/signals/macro_signals.py
```

## Fonksiyon İmzaları

```python
# Yeni eklenen sabit — dosya başında tanımla
SYMBOL_VOLATILITY_PROFILES: dict[str, dict] = {
    "USDTRY": {"group": "forex",     "scale": 0.02, "clip": (-1.0, 1.0)},
    "EURTRY": {"group": "forex",     "scale": 0.02, "clip": (-1.0, 1.0)},
    "VIX":    {"group": "vix",       "scale": 0.15, "clip": (-1.0, 1.0)},
    "BRENTOIL":{"group": "commodity","scale": 0.05, "clip": (-1.0, 1.0)},
    "XAU":    {"group": "commodity", "scale": 0.03, "clip": (-1.0, 1.0)},
    # DEFAULT group kullanılır: equity
    "_default": {"group": "equity",  "scale": 0.05, "clip": (-1.0, 1.0)},
}

def get_symbol_scale(symbol: str) -> dict:
    """
    Sembol için volatility profile döner.
    Bilinmeyen semboller _default profiline düşer.
    """

def score_macro_component(
    symbol: str,
    raw_change_pct: float,
    profile_override: dict | None = None,
) -> float:
    """
    Sembol bazlı scaling ile normalize edilmiş makro sinyal skoru döner.
    
    Args:
        symbol: Sembol adı (SYMBOL_VOLATILITY_PROFILES key'i)
        raw_change_pct: Ham fiyat değişimi, ondalık (0.03 = %3)
        profile_override: Test/override için manuel profil. None = SYMBOL_VOLATILITY_PROFILES'dan al.
    
    Returns:
        float: [-1.0, 1.0] aralığında normalize skor
    """
```

## Input/Output Formatları

```python
# Input
symbol          = "VIX"
raw_change_pct  = 0.12   # VIX %12 arttı

# Output
score = score_macro_component("VIX", 0.12)
# → 0.12 / 0.15 = 0.80  (VIX scale=0.15 kullanıldı)
# → clip(-1,1) → 0.80

# Karşılaştırma (eski davranış)
# → 0.12 / 0.05 = 2.40  → clip(-1,1) → 1.0  ← yanlış doygunluk

# Forex örneği
score = score_macro_component("USDTRY", 0.018)
# → 0.018 / 0.02 = 0.90

# Bilinmeyen sembol
score = score_macro_component("THYAO", 0.03)
# → _default (equity, scale=0.05) → 0.03 / 0.05 = 0.60
```

## Edge Case'ler

| Case | Beklenen Davranış |
|---|---|
| `raw_change_pct = 0.0` | → `0.0` dön, sıfıra bölme yok |
| Sembol SYMBOL_VOLATILITY_PROFILES'da yok | → `_default` profili kullan, log uyarısı yaz |
| `profile_override` verilmiş | → SYMBOL_VOLATILITY_PROFILES'ı ignore et |
| `scale = 0` (hatalı config) | → `ValueError` fırlat, silent pass etme |
| Sonuç clip dışı | → clip sonrası değeri dön, orijinal değeri debug log'a yaz |

## Test Kriterleri

```python
# Tüm bu assert'ler geçmeli:

assert score_macro_component("VIX", 0.15) == pytest.approx(1.0)      # tam doygunluk
assert score_macro_component("VIX", 0.075) == pytest.approx(0.5)     # yarı skala
assert score_macro_component("VIX", 0.30) == pytest.approx(1.0)      # clip üst
assert score_macro_component("VIX", -0.30) == pytest.approx(-1.0)    # clip alt
assert score_macro_component("USDTRY", 0.02) == pytest.approx(1.0)   # forex tam
assert score_macro_component("USDTRY", 0.01) == pytest.approx(0.5)   # forex yarı
assert score_macro_component("UNKNOWN_SYM", 0.05) == pytest.approx(1.0)  # default
assert score_macro_component("VIX", 0.0) == pytest.approx(0.0)       # sıfır change
```

## Bağımlılıklar
Yeni bağımlılık yok. Mevcut `src/signals/macro_signals.py` import yapısı korunacak.
