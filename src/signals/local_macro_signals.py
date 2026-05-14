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
    """Composite local macro signals.

    When called with no arguments (default path), returns a singleton so that
    YAML fallback is loaded only once per process.  Passing an explicit cache
    always creates a fresh instance (used by tests and by direct cache injection).
    """

    _instance: "LocalMacroSignals | None" = None

    def __new__(cls, cache: Optional[LocalMacroCache] = None):
        if cache is not None:
            # Explicit cache → never share the singleton
            return super().__new__(cls)
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, cache: Optional[LocalMacroCache] = None):
        if getattr(self, "_initialized", False) and cache is None:
            return
        if cache is None:
            cache = LocalMacroCache()
            cache.load_from_yaml_fallback()
        self.cache = cache
        self.tcmb = TCMBClient(cache)
        self.cds = CDSClient(cache)
        self.bist_foreign_weekly = BistForeignOwnershipClient(cache)
        self._initialized = True

    @classmethod
    def _reset(cls) -> None:
        """Test helper — reset the default singleton."""
        cls._instance = None

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
