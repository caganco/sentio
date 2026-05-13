"""Composite local macro signals (TCMB + CDS + BIST Foreign Weekly)."""
from dataclasses import dataclass
from typing import Optional

from .local import (
    BistForeignOwnershipClient,
    CDSClient,
    LocalMacroCache,
    TCMBClient,
)
from .models import LocalMacroSignal


@dataclass
class LocalMacroResult:
    """Aggregated local macro scores."""

    tcmb: LocalMacroSignal
    cds: LocalMacroSignal
    bist_foreign_weekly: LocalMacroSignal
    composite_score: float


class LocalMacroSignals:
    """Composite local macro signals."""

    def __init__(self, cache: Optional[LocalMacroCache] = None):
        if cache is None:
            cache = LocalMacroCache()
        self.cache = cache
        self.tcmb = TCMBClient(cache)
        self.cds = CDSClient(cache)
        self.bist_foreign_weekly = BistForeignOwnershipClient(cache)

    def score(self) -> LocalMacroResult:
        """
        Compute composite local macro signal.

        Returns: LocalMacroResult with individual component scores.
        """
        tcmb_signal = self.tcmb.score()
        cds_signal = self.cds.score()
        foreign_signal = self.bist_foreign_weekly.score()

        # Composite: currently 50% TCMB + 50% CDS (stub: foreign weight 0)
        # TODO: Rebalance weights after Layer 5 integration
        tcmb_contrib = tcmb_signal.score * tcmb_signal.confidence * 0.5
        cds_contrib = cds_signal.score * cds_signal.confidence * 0.5
        foreign_contrib = foreign_signal.score * foreign_signal.confidence * 0.0

        composite = tcmb_contrib + cds_contrib + foreign_contrib

        return LocalMacroResult(
            tcmb=tcmb_signal,
            cds=cds_signal,
            bist_foreign_weekly=foreign_signal,
            composite_score=composite,
        )
