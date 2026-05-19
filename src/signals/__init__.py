"""Signals module: macro signals + signal engine."""
from .engine import build_signal_context_for_orchestrator, compute_batch, compute_signal
from .macro_alignment import MacroAlignmentCalculator
from .macro_signals import (
    MacroSignal,
    calculate_macro_environment_score,
    generate_macro_signal,
    save_signal_json,
    score_macro_component,
)
from .macro_signals import (
    detect_regime as detect_macro_regime,
)
from .models import AuditTrail, FinalSignal, LayerScore, MacroRegime, SignalResult
from .thresholds import MASTER_WEIGHTS, SIGNAL_THRESHOLDS

__all__ = [
    "MacroSignal",
    "detect_macro_regime",
    "score_macro_component",
    "calculate_macro_environment_score",
    "generate_macro_signal",
    "save_signal_json",
    "compute_signal",
    "compute_batch",
    "build_signal_context_for_orchestrator",
    "LayerScore",
    "SignalResult",
    "AuditTrail",
    "FinalSignal",
    "MacroRegime",
    "MASTER_WEIGHTS",
    "SIGNAL_THRESHOLDS",
    "MacroAlignmentCalculator",
]
