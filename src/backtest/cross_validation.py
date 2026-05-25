"""Purged K-Fold ve Combinatorial Purged CV implementasyonu (D-150b).

BacktestEngine import etmez — factory callback pattern kullanılır.
Referans: LdP (2018) AFML §§7.3, 12.2

Dayanak: SPEC_STATISTICAL_VALIDATION_1 §4.3
"""
from __future__ import annotations

import math
from itertools import combinations
from typing import Iterator, List, Tuple

import numpy as np
import pandas as pd

from src.backtest.validation_constants import (
    CPCV_K,
    CPCV_N,
    PURGED_KFOLD_EMBARGO_DAYS,
    PURGED_KFOLD_PURGE_DAYS,
    PURGED_KFOLD_SPLITS,
)


class PurgedKFold:
    """Temporal K-Fold with sample purging and embargo.

    Purge: test penceresi öncesindeki örtüşen train örneklerini çıkar.
    Embargo: test penceresi sonrasındaki sızıntıyı önle.
    Referans: LdP (2018) AFML §7.3
    """

    def __init__(
        self,
        n_splits: int = PURGED_KFOLD_SPLITS,
        purge_days: int = PURGED_KFOLD_PURGE_DAYS,
        embargo_days: int = PURGED_KFOLD_EMBARGO_DAYS,
    ) -> None:
        if n_splits < 2:
            raise ValueError("n_splits must be >= 2")
        self.n_splits = n_splits
        self.purge_days = purge_days
        self.embargo_days = embargo_days

    def split(
        self,
        dates: pd.DatetimeIndex,
    ) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        """Yields (train_indices, test_indices) for each fold.

        Garantiler:
        - train_idx ∩ test_idx = ∅
        - Purge buffer: test_start - purge_days < train_date → kaldırılır
        - Embargo buffer: test_end < train_date < test_end + embargo_days → kaldırılır
        """
        n = len(dates)
        fold_size = n // self.n_splits

        for fold in range(self.n_splits):
            test_start_pos = fold * fold_size
            test_end_pos = (
                (fold + 1) * fold_size if fold < self.n_splits - 1 else n
            )

            test_start_date = dates[test_start_pos]
            test_end_date = dates[test_end_pos - 1]

            purge_cutoff = test_start_date - pd.Timedelta(days=self.purge_days)
            embargo_cutoff = test_end_date + pd.Timedelta(days=self.embargo_days)

            test_idx = np.arange(test_start_pos, test_end_pos)

            train_mask = (dates < purge_cutoff) | (dates > embargo_cutoff)
            # test indeksleri her halükarda çıkar
            train_mask[test_start_pos:test_end_pos] = False
            train_idx = np.where(train_mask)[0]

            yield train_idx, test_idx


class CombinatorialPurgedCV:
    """Combinatorial Purged Cross-Validation.

    N zaman diliminden k tanesini test olarak seçer → C(N,k) path üretir.
    Her path bağımsız IS/OOS çifti → Sharpe dağılımı için kullanılır.
    Referans: LdP (2018) AFML §12.2
    """

    def __init__(
        self,
        N: int = CPCV_N,
        k: int = CPCV_K,
    ) -> None:
        if k >= N:
            raise ValueError("k must be < N")
        self.N = N
        self.k = k

    @property
    def n_paths(self) -> int:
        """C(N, k) → toplam path sayısı. N=6, k=2 → 15."""
        return math.comb(self.N, self.k)

    def split(
        self,
        dates: pd.DatetimeIndex,
        embargo_days: int = PURGED_KFOLD_EMBARGO_DAYS,
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Returns [(train_idx, test_idx), ...] → uzunluk = n_paths.

        Test dilim çiftleri arasında embargo uygulanır.
        Dönüş sırası: combinations(range(N), k) ile deterministik.
        """
        n = len(dates)
        slice_size = n // self.N
        slices = [
            np.arange(
                i * slice_size,
                (i + 1) * slice_size if i < self.N - 1 else n,
            )
            for i in range(self.N)
        ]

        paths: List[Tuple[np.ndarray, np.ndarray]] = []

        for test_slice_combo in combinations(range(self.N), self.k):
            test_idx = np.concatenate([slices[s] for s in test_slice_combo])

            if embargo_days > 0:
                test_dates = dates[test_idx]
                embargo_mask = np.zeros(n, dtype=bool)
                for td in test_dates:
                    embargo_mask |= (
                        (dates >= td - pd.Timedelta(days=embargo_days))
                        & (dates <= td + pd.Timedelta(days=embargo_days))
                    )
                train_mask = ~embargo_mask
            else:
                train_mask = np.ones(n, dtype=bool)
                train_mask[test_idx] = False

            train_idx = np.where(train_mask)[0]
            paths.append((train_idx, test_idx))

        return paths
