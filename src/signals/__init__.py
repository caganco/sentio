"""Signals module: macro signals + signal engine."""
from .macro_signals import (
    MacroSignal,
    detect_regime as detect_macro_regime,
    score_macro_component,
    calculate_macro_environment_score,
    generate_macro_signal,
    save_signal_json,
)
from .engine import compute_signal, compute_batch, build_signal_context_for_orchestrator
from .models import LayerScore, SignalResult, AuditTrail, FinalSignal, MacroRegime
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
]
