"""Architectural protection tests — enforce design principles. (4 tests)"""
import re
from pathlib import Path

import pytest

from src.signals.local_macro_signals import LocalMacroSignals
from src.signals.thresholds import MASTER_WEIGHTS, SIGNAL_THRESHOLDS


class TestThresholdsSingleSource:
    """Verify that all threshold constants are centralized in thresholds.py."""

    def test_thresholds_file_is_single_source(self):
        """All SIGNAL_THRESHOLDS keys must be defined in thresholds.py, not hardcoded elsewhere."""
        thresholds_path = Path(__file__).parent.parent / "src" / "signals" / "thresholds.py"
        engine_path = Path(__file__).parent.parent / "src" / "signals" / "engine.py"

        # Read thresholds.py
        thresholds_content = thresholds_path.read_text()

        # Verify all expected keys are defined
        for key in ("buy_strong", "buy_weak", "hold_lower", "sell_weak"):
            assert f'"{key}"' in thresholds_content or f"'{key}'" in thresholds_content, (
                f"Threshold key '{key}' not defined in thresholds.py"
            )

        # Read engine.py and check for hardcoded thresholds
        engine_content = engine_path.read_text()

        # Pattern: search for literal threshold values like 72.0, 60.0, etc.
        # These should NOT appear in engine.py if properly imported from thresholds.py
        forbidden_patterns = [
            r'\b72\.0\b',      # buy_strong
            r'\b60\.0\b',      # buy_weak / hold_upper
            r'\b48\.0\b',      # hold_lower
            r'\b32\.0\b',      # sell_weak
        ]

        for pattern in forbidden_patterns:
            # Ignore comments and docstrings
            lines = engine_content.split('\n')
            for i, line in enumerate(lines, 1):
                # Skip comment lines
                if line.strip().startswith('#') or line.strip().startswith('"""') or line.strip().startswith("'''"):
                    continue
                # Skip docstring content (rough heuristic)
                if re.search(pattern, line):
                    # Verify this is accessing from SIGNAL_THRESHOLDS dict
                    if 'SIGNAL_THRESHOLDS[' not in line and 'SIGNAL_THRESHOLDS.get' not in line:
                        pytest.fail(
                            f"engine.py:{i} contains hardcoded threshold {pattern}. "
                            f"Use SIGNAL_THRESHOLDS instead."
                        )

    def test_no_hardcoded_thresholds_in_engine(self):
        """Verify engine.py does not hardcode weight values (must import MASTER_WEIGHTS)."""
        engine_path = Path(__file__).parent.parent / "src" / "signals" / "engine.py"
        engine_content = engine_path.read_text()

        # Weight values should never appear as raw floats in engine.py
        weight_patterns = [
            r'\b0\.20\b',      # technical
            r'\b0\.35\b',      # macro
            r'\b0\.15\b',      # kap
            r'\b0\.05\b',      # risk / sentiment
            r'\b0\.25\b',      # old kelly fraction (allowed in comments/config)
        ]

        lines = engine_content.split('\n')
        for i, line in enumerate(lines, 1):
            # Skip comments, docstrings, and imports
            if line.strip().startswith('#') or 'import' in line or 'MASTER_WEIGHTS' in line:
                continue
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                continue

            for pattern in weight_patterns:
                if re.search(pattern, line):
                    # Check if it's in a config or comment context (allowed)
                    if any(x in line for x in ['#', 'kelly_fraction', 'comment', 'example']):
                        continue
                    # Otherwise, raise error
                    pytest.fail(
                        f"engine.py:{i} contains hardcoded weight {pattern}. "
                        f"Import from MASTER_WEIGHTS instead."
                    )


class TestWeightSumValid:
    """Verify MASTER_WEIGHTS sum is in acceptable range."""

    def test_weight_sum_valid(self):
        """All layer weights must sum to 0.85–1.05 (neutral fuzzing tolerance)."""
        total_weight = sum(MASTER_WEIGHTS.values())

        assert 0.85 <= total_weight <= 1.05, (
            f"MASTER_WEIGHTS sum is {total_weight:.4f}, "
            f"but must be in [0.85, 1.05]. "
            f"Current weights: {MASTER_WEIGHTS}"
        )

        # Verify no negative weights; zero allowed for deactivated layers (e.g., sentiment)
        for layer, weight in MASTER_WEIGHTS.items():
            assert weight >= 0, f"Layer '{layer}' has negative weight: {weight}"
            # Sentiment allowed to be 0 (deactivated pending DistilBERT Phase 4.2.1)
            if layer != "sentiment":
                assert weight > 0, f"Active layer '{layer}' has non-positive weight: {weight}"


class TestSingletonPattern:
    """Verify LocalMacroSignals maintains singleton pattern."""

    def test_singleton_not_duplicated(self):
        """Calling LocalMacroSignals() twice should return the same instance."""
        # Reset singleton to ensure clean test
        LocalMacroSignals._reset()

        # First call
        instance1 = LocalMacroSignals()

        # Second call
        instance2 = LocalMacroSignals()

        # Should be identical objects
        assert instance1 is instance2, (
            "LocalMacroSignals singleton pattern broken: "
            "multiple instances created when only one expected"
        )

        # Verify _instance is set
        assert LocalMacroSignals._instance is not None
        assert LocalMacroSignals._instance is instance1

    def test_singleton_reset_works(self):
        """_reset() method should clear the singleton for tests."""
        # Create instance
        instance1 = LocalMacroSignals()
        assert LocalMacroSignals._instance is not None

        # Reset
        LocalMacroSignals._reset()
        assert LocalMacroSignals._instance is None

        # Next creation should be new instance
        instance2 = LocalMacroSignals()
        assert instance2 is not instance1


pytestmark = pytest.mark.baseline
