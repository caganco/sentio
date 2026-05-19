"""Signal Engine data models."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

FinalSignal = Literal["BUY-STRONG", "BUY-WEAK", "HOLD", "SELL-WEAK", "SELL-STRONG"]
MacroRegime = Literal["RISK_ON", "RISK_OFF", "NEUTRAL"]

SIGNAL_ORDER: list[str] = ["BUY-STRONG", "BUY-WEAK", "HOLD", "SELL-WEAK", "SELL-STRONG"]


@dataclass(frozen=True)
class LayerScore:
    layer: str        # "technical" | "macro" | "kap" | "sentiment" | "smart_money" | "risk"
    score: float      # 0-100, 50=NEUTRAL
    confidence: float # 0.0-1.0
    weight: float     # masterplan weight (0.0-1.0)
    detail: dict      # audit info
    source: str       # "computed" | "missing" | "override" | "partial" | "no_events"

    def __post_init__(self) -> None:
        object.__setattr__(self, "score", round(float(self.score), 4))
        object.__setattr__(self, "confidence", round(float(self.confidence), 4))


@dataclass(frozen=True)
class ConflictInfo:
    detected: bool
    layer_a: str
    layer_b: str
    score_gap: float
    resolution: str


@dataclass(frozen=True)
class AuditTrail:
    symbol: str
    as_of_date: date
    computed_at: datetime
    layer_scores: list[LayerScore]
    weighted_sum: float
    pre_conflict_signal: FinalSignal
    conflict: ConflictInfo
    regime: MacroRegime
    risk_off_override: bool
    risk_off_trigger: str | None
    final_signal: FinalSignal
    signal_summary: str
    # Phase 4.5 (D-052) — derived conviction layer (SPEC_SIGNAL_CONVICTION_1).
    # Defaults keep all pre-4.5 constructors valid.
    conviction_score: float = 0.0          # [0,1] post macro modulation
    conviction_tier: str = "WATCH"         # BUY-STRONG | BUY-MEDIUM | WATCH


@dataclass(frozen=True)
class SignalResult:
    symbol: str
    final_signal: FinalSignal
    score: float      # WeightedSum (0-100)
    audit: AuditTrail
    # Phase 4.5 (D-052) — surfaced from audit for downstream sizing/strategist.
    conviction_score: float = 0.0          # [0,1]
    conviction_tier: str = "WATCH"


@dataclass(frozen=True)
class LocalMacroSignal:
    """Local macro signal component (TCMB, CDS, etc)."""
    component: str                 # 'tcmb' | 'cds' | 'bist_foreign_weekly'
    score: float                   # 0-100
    confidence: float              # 0.0-1.0
    raw_value: float | None        # Original value (rate%, bps, %)
    last_update: str | None        # ISO timestamp
    data_freshness: str            # 'fresh' | 'stale' | 'missing'
    audit_msg: str = ""            # Audit context
