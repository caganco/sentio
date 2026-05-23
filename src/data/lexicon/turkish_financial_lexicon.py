"""Turkish Financial Lexicon — Loughran-McDonald adapted for BIST (D-124).

Tier-1 scoring: positive weights = bullish, negative weights = bearish.
Magnitude reflects signal strength. Negation window flips weight sign.
"""
import re

BULLISH_TERMS: dict[str, float] = {
    # Earnings / profitability
    "kâr": 1.5,
    "kar": 1.5,
    "net kâr": 2.0,
    "net kar": 2.0,
    "brüt kâr": 1.6,
    "operasyonel kâr": 1.3,
    "kârlılık": 1.4,
    "karlılık": 1.4,
    # Growth
    "büyüme": 1.4,
    "artış": 1.3,
    "artıyor": 1.2,
    "arttı": 1.3,
    "yüzde artış": 1.5,
    "ciro arttı": 1.3,
    "marj arttı": 1.5,
    # Market signals
    "rekor": 2.0,
    "rekor kâr": 2.5,
    "rekor kar": 2.5,
    "tüm zamanların rekoru": 2.5,
    # Sentiment keywords
    "güçlü": 1.2,
    "pozitif": 1.1,
    "olumlu": 1.1,
    "başarılı": 1.2,
    "iyi": 0.8,
    # Price / market
    "yükseliş": 1.5,
    "yükseldi": 1.4,
    "yükseliyor": 1.3,
    "rallisi": 1.4,
    "toparladı": 1.2,
    # Capital / dividends
    "temettü": 1.3,
    "temettü artışı": 2.0,
    "hisse geri alımı": 1.8,
    "bedelsiz hisse": 1.5,
    "sermaye artırımı": 1.2,
    # Business
    "ihracat": 1.0,
    "sipariş": 1.0,
    "kapasite artışı": 1.5,
    "anlaşma": 1.2,
    "sözleşme": 1.2,
    "iş birliği": 1.0,
    "ortaklık": 1.0,
    "ihale kazandı": 1.8,
    "lisans aldı": 1.5,
    # Analyst / market
    "beklenti üzeri": 2.0,
    "tahmin üzeri": 2.0,
    "piyasa beklentisi üzeri": 2.2,
    "güçlü büyüme": 2.0,
    "hedef fiyat yükseltildi": 2.0,
    "endeks üzeri": 1.5,
    "yatırım": 1.0,
    "genişleme": 1.2,
    "yeni pazar": 1.2,
    "al": 0.8,
}

BEARISH_TERMS: dict[str, float] = {
    # Losses
    "zarar": -1.5,
    "net zarar": -2.0,
    "operasyonel zarar": -1.8,
    "kayıp": -1.3,
    "ciro düştü": -1.5,
    # Decline
    "düşüş": -1.3,
    "gerileme": -1.2,
    "geriledi": -1.2,
    "düştü": -1.3,
    "düşüyor": -1.2,
    "azalış": -1.2,
    "azaldı": -1.1,
    # Sentiment
    "olumsuz": -1.1,
    "negatif": -1.1,
    "zayıf": -1.1,
    "kötü": -0.9,
    "endişe": -1.0,
    # Legal / regulatory
    "soruşturma": -2.0,
    "dava": -1.8,
    "tazminat": -1.5,
    "para cezası": -1.5,
    "idari işlem": -1.5,
    "spk soruşturması": -2.2,
    "spk": -1.5,
    "borsa istanbul uyarısı": -1.8,
    "sermaye piyasası kurulu": -1.8,
    "suç duyurusu": -2.0,
    # Severe / distress
    "konkordato": -3.0,
    "iflas": -3.0,
    "tasfiye": -2.5,
    "haciz": -2.0,
    "icra": -2.0,
    "borç yapılandırma": -1.8,
    "likidite sorunu": -2.0,
    "ödeme güçlüğü": -2.0,
    # Analyst / market
    "beklenti altı": -2.0,
    "tahmin altı": -2.0,
    "hedef fiyat düşürüldü": -2.0,
    "endeks altı": -1.5,
    "sat": -0.8,
}

# Negation: if any of these appear within NEGATION_WINDOW chars BEFORE a term, flip sign
NEGATION_PATTERN: re.Pattern = re.compile(
    r"(değil|olmadı|yalanla|reddet|iptal|sona erdi|etmedi|olmayan|yok)",
    re.IGNORECASE,
)
NEGATION_WINDOW: int = 60  # characters before matched term
