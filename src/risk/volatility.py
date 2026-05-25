"""
Vol-targeting Faz 1: realized vol hesaplama + portföy katkı analizi.
GÖZLEM MODU — pozisyon kararına ETKİ YOK.
Dayanak: RR-016 §5.1–5.5 (D-147).
"""
import numpy as np
import pandas as pd
import yfinance as yf

from src.signals.thresholds import (
    PORTFOLIO_TARGET_VOL_ANNUAL,
    VOL_SCALAR_CAP,
    VOL_SCALAR_FLOOR,
)


def realized_vol_ticker(ticker: str, lookback: int = 20) -> float:
    """
    Ticker için realized volatility (yıllık) hesaplar.
    yfinance'dan günlük kapanış fiyatları çeker, log return std × sqrt(252).

    Args:
        ticker: BIST sembolü (ör. "TTKOM"). Otomatik olarak "<ticker>.IS" olarak eklenir.
        lookback: Kullanılacak gün sayısı (varsayılan: 20).

    Returns:
        Yıllık volatility (float). Yeterli veri yoksa 0.0 döner.
    """
    symbol = f"{ticker}.IS" if not ticker.endswith(".IS") else ticker
    data = yf.download(
        symbol,
        period=f"{lookback + 10}d",
        progress=False,
        auto_adjust=True,
    )
    if data.empty or len(data) < 2:
        return 0.0
    prices = data["Close"].squeeze().dropna()
    if len(prices) < 2:
        return 0.0
    returns = np.log(prices / prices.shift(1)).dropna()
    if len(returns) < 1:
        return 0.0
    return float(returns.tail(lookback).std() * np.sqrt(252))


def realized_vol_portfolio(
    holdings: dict[str, float],
    lookback: int = 20,
) -> float:
    """
    Portföy seviyesinde realized vol (korelasyonsuz yaklaşım).

    σ_port = sqrt(Σ w_i² × σ_i²)

    Ref: RR-016 §9.3 — korelasyon düzeltmesi Faz 2'de eklenir.

    Args:
        holdings: {ticker: weight} — ağırlıklar 0–1 arası (toplamı 1 olması şart değil).
        lookback: günlük return penceresi.

    Returns:
        Yıllık portföy volatility (float). Boş holdings → 0.0.
    """
    if not holdings:
        return 0.0
    variance_sum = 0.0
    for ticker, weight in holdings.items():
        sigma = realized_vol_ticker(ticker, lookback)
        variance_sum += weight ** 2 * sigma ** 2
    return float(np.sqrt(variance_sum))


def vol_contribution(
    ticker: str,
    weight: float,
    sigma: float,
    port_sigma: float,
) -> float:
    """
    Tek hisse volatilite katkısı (normalize edilmiş kesir).

    katkı = weight × sigma / port_sigma

    Risk Parity Lite eşiği: katkı > MAX_SINGLE_VOL_CONTRIB (0.40) → kırmızı uyarı.
    Ref: RR-016 §5.5, §9.4.

    Args:
        ticker: BIST sembolü (yalnızca log amaçlı, hesaba girmez).
        weight: Pozisyon ağırlığı (0–1).
        sigma: Ticker'ın yıllık realized vol'u.
        port_sigma: Portföyün yıllık realized vol'u.

    Returns:
        Normalize katkı oranı (float). port_sigma == 0 ise 0.0 döner.
    """
    if port_sigma == 0.0:
        return 0.0
    return float(weight * sigma / port_sigma)


def compute_vol_scalar(
    realized_vol: float,
    target_vol: float = PORTFOLIO_TARGET_VOL_ANNUAL,
) -> float:
    """
    vol_scalar = clip(target_vol / realized_vol, VOL_SCALAR_FLOOR, VOL_SCALAR_CAP)

    Faz 1'de SADECE raporlama amaçlıdır — pozisyon kararına ETKİ YOK.

    Ref: RR-016 §5.1 Sanity Tests 1–4:
      σ=0.30 → 0.50; σ=0.10 → 1.50 (cap); σ=0.75 → 0.20 (floor); σ=0.15 → 1.00.

    Args:
        realized_vol: Yıllık realized vol (örn. 0.30 = %30).
        target_vol: Hedef vol (varsayılan: PORTFOLIO_TARGET_VOL_ANNUAL = 0.15).

    Returns:
        Vol scalar (float, [VOL_SCALAR_FLOOR, VOL_SCALAR_CAP]).
    """
    if realized_vol <= 0.0:
        return VOL_SCALAR_CAP
    raw = target_vol / realized_vol
    return float(np.clip(raw, VOL_SCALAR_FLOOR, VOL_SCALAR_CAP))
