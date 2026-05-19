"""Stock correlation matrix for portfolio risk management (SPEC_CORRELATION_MATRIX_1).

Phase 4.3 Week 1 — correlation calculation layer only.

Computes rolling stock-to-stock log-return correlations from BIST OHLCV data.
Independent module: does NOT modify signal layers or Kelly Criterion. Kelly
adjustment / sector limits are Week 2 scope and intentionally not implemented here.
"""
import logging

import numpy as np
import pandas as pd

from src.signals.thresholds import (
    CORRELATION_CLUSTER_THRESHOLD,
    CORRELATION_MIN_SAMPLES,
    CORRELATION_WINDOW_DAYS,
)

logger = logging.getLogger(__name__)


class CorrelationMatrix:
    """Rolling-window Pearson correlation of stock log returns.

    Usage:
        cm = CorrelationMatrix()
        matrix, confidence = cm.calculate(price_df)
        rho = cm.get_correlation("GARAN", "AKBANK")
        clusters = cm.identify_clusters()
    """

    def __init__(
        self,
        window_days: int = CORRELATION_WINDOW_DAYS,
        min_samples: int = CORRELATION_MIN_SAMPLES,
    ):
        """Initialize correlation matrix calculator.

        Args:
            window_days: Rolling window length in trading days (default 60).
            min_samples: Return observations needed for confidence 1.0 (default 50).
        """
        self.window_days = window_days
        self.min_samples = min_samples
        self._matrix: pd.DataFrame | None = None
        self._confidence: dict[str, float] = {}
        self._stocks: list[str] = []

    def calculate(
        self, price_data: pd.DataFrame
    ) -> tuple[pd.DataFrame, dict[str, float]]:
        """Compute the correlation matrix from long-format OHLCV price data.

        Args:
            price_data: DataFrame with columns ['stock', 'date', 'close']
                        (extra columns such as 'volume' are ignored).

        Returns:
            (corr_matrix, confidence) where corr_matrix is a symmetric
            DataFrame of Pearson coefficients indexed/columned by stock, and
            confidence maps each stock to min(samples / min_samples, 1.0).

        Raises:
            ValueError: if required columns are missing or no data remains.
        """
        required = {"stock", "date", "close"}
        missing = required - set(price_data.columns)
        if missing:
            raise ValueError(f"price_data missing required columns: {sorted(missing)}")
        if price_data.empty:
            raise ValueError("price_data is empty")

        # Wide format: rows = date, cols = stock, values = close price.
        pivot = price_data.pivot(index="date", columns="stock", values="close")
        pivot = pivot.sort_index()

        # Keep only the most recent window (+1 row so the first return survives
        # the .shift(1) differencing below).
        if len(pivot) > self.window_days + 1:
            pivot = pivot.iloc[-(self.window_days + 1):]

        # Log returns avoid spurious correlation driven by shared price trend.
        log_returns = np.log(pivot / pivot.shift(1)).dropna(how="all")

        corr_matrix = log_returns.corr(method="pearson")

        confidence = {
            stock: min(int(log_returns[stock].notna().sum()) / self.min_samples, 1.0)
            for stock in log_returns.columns
        }

        self._matrix = corr_matrix
        self._confidence = confidence
        self._stocks = list(corr_matrix.columns)

        logger.info(
            "Correlation matrix computed: %d stocks, %d return samples",
            len(self._stocks),
            len(log_returns),
        )
        return corr_matrix, confidence

    def get_correlation(self, stock_a: str, stock_b: str) -> float:
        """Return the correlation between two stocks.

        Returns 1.0 for a stock with itself, 0.0 when the pair is unknown or
        the coefficient is undefined (e.g. a flat price series).
        """
        if stock_a == stock_b:
            return 1.0
        if self._matrix is None:
            raise RuntimeError("calculate() must be called before get_correlation()")
        if stock_a not in self._matrix.index or stock_b not in self._matrix.columns:
            return 0.0
        value = self._matrix.at[stock_a, stock_b]
        if pd.isna(value):
            return 0.0
        return float(value)

    def get_confidence(self, stock: str) -> float:
        """Return the confidence score (0.0-1.0) for a stock's correlations."""
        return self._confidence.get(stock, 0.0)

    def get_sector_exposure(self, stock: str, sector_map: dict[str, str]) -> float:
        """Mean correlation of `stock` to other stocks in the same sector.

        Args:
            stock: Target stock symbol.
            sector_map: Mapping of stock symbol -> sector name.

        Returns:
            Average pairwise correlation to sector peers, or 0.0 if the stock
            has no peers / unknown sector.
        """
        if self._matrix is None:
            raise RuntimeError("calculate() must be called before get_sector_exposure()")
        sector = sector_map.get(stock)
        if sector is None:
            return 0.0
        peers = [
            s
            for s, sec in sector_map.items()
            if sec == sector and s != stock and s in self._stocks
        ]
        if not peers:
            return 0.0
        correlations = [self.get_correlation(stock, peer) for peer in peers]
        return float(np.mean(correlations))

    def identify_clusters(
        self, threshold: float = CORRELATION_CLUSTER_THRESHOLD
    ) -> list[list[str]]:
        """Group stocks that move together (pairwise correlation > threshold).

        Greedy single-pass clustering: each unvisited stock seeds a cluster and
        absorbs every still-unvisited stock correlated above `threshold`.

        Returns:
            List of clusters, each a sorted list of stock symbols.
        """
        if self._matrix is None:
            raise RuntimeError("calculate() must be called before identify_clusters()")
        clusters: list[list[str]] = []
        visited: set[str] = set()

        for stock in self._stocks:
            if stock in visited:
                continue
            cluster = {stock}
            visited.add(stock)
            for other in self._stocks:
                if other in visited:
                    continue
                if self.get_correlation(stock, other) > threshold:
                    cluster.add(other)
                    visited.add(other)
            clusters.append(sorted(cluster))

        return clusters
