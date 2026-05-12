"""Macro signals module."""
from .macro_signals import (
    MacroSignal,
    detect_regime,
    score_macro_component,
    calculate_macro_environment_score,
    generate_macro_signal,
    save_signal_json,
)

__all__ = [
    "MacroSignal",
    "detect_regime",
    "score_macro_component",
    "calculate_macro_environment_score",
    "generate_macro_signal",
    "save_signal_json",
]
