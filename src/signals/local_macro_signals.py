"""Composite local macro signals (TCMB + CDS + BIST Foreign Weekly)."""
from dataclasses import dataclass

from .local import (
    BistForeignOwnershipClient,
    CDSClient,
    DXYClient,
    LocalMacroCache,
    TCMBClient,
)
from .models import LocalMacroSignal
from .thresholds import LOCAL_MACRO_WEIGHTS


@dataclass
class LocalMacroResult:
    """Aggregated local macro scores."""

    tcmb: LocalMacroSignal
    cds: LocalMacroSignal
    bist_foreign_weekly: LocalMacroSignal
    dxy: LocalMacroSignal
    tl_bond_proxy: LocalMacroSignal
    composite_score: float


class LocalMacroSignals:
    """Composite local macro signals.

    When called with no arguments (default path), returns a singleton so that
    YAML fallback is loaded only once per process.  Passing an explicit cache
    always creates a fresh instance (used by tests and by direct cache injection).
    """

    _instance: "LocalMacroSignals | None" = None

    def __new__(cls, cache: LocalMacroCache | None = None):
        if cache is not None:
            # Explicit cache → never share the singleton
            return super().__new__(cls)
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, cache: LocalMacroCache | None = None):
        if getattr(self, "_initialized", False) and cache is None:
            return
        if cache is None:
            cache = LocalMacroCache()
            cache.load_from_yaml_fallback()
        self.cache = cache
        self.tcmb = TCMBClient(cache)
        self.cds = CDSClient(cache)
        self.bist_foreign_weekly = BistForeignOwnershipClient(cache)
        self.dxy = DXYClient(cache)
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
        dxy_signal = self.dxy.score()
        tl_bond_proxy_signal = self.cds.get_tl_bond_proxy()

        # LOCAL_MACRO_WEIGHTS: local standalone composite (TCMB + CDS + foreign).
        # Used for LocalMacroResult.composite_score only — macro_layer.py uses
        # individual component signals with MACRO_WEIGHTS_COMPOSITE instead.
        tcmb_contrib = (
            tcmb_signal.score * tcmb_signal.confidence * LOCAL_MACRO_WEIGHTS["tcmb"]
        )
        cds_contrib = (
            cds_signal.score * cds_signal.confidence * LOCAL_MACRO_WEIGHTS["cds"]
        )
        foreign_contrib = (
            foreign_signal.score
            * foreign_signal.confidence
            * LOCAL_MACRO_WEIGHTS["bist_foreign_weekly"]
        )

        composite = tcmb_contrib + cds_contrib + foreign_contrib

        return LocalMacroResult(
            tcmb=tcmb_signal,
            cds=cds_signal,
            bist_foreign_weekly=foreign_signal,
            dxy=dxy_signal,
            tl_bond_proxy=tl_bond_proxy_signal,
            composite_score=composite,
        )
