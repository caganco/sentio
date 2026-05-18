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
    """Verify MASTER_WEIGHTS sum is in acceptable range.

    Logic delegated to src.utils.weight_validator (D-052). The static sum stays
    in [0.85, 1.05]; 0.78 is the emergent runtime floor, not the static sum.
    """

    def test_weight_sum_valid(self):
        """Static sum in band, no negative/zero active weights (sentiment may be base-weighted)."""
        from src.utils.weight_validator import validate_master_weights

        report = validate_master_weights()  # raises ValueError on violation

        assert 0.85 <= report["static_sum"] <= 1.05, report
        # Emergent normalizer floor is the documented 0.78 (DEC-009).
        assert abs(report["emergent_floor"] - 0.78) < 1e-9, report

    def test_weight_sum_validator_rejects_bad_weights(self, monkeypatch):
        """Validator must raise when the static sum leaves the safety band."""
        import src.utils.weight_validator as wv

        monkeypatch.setattr(wv, "MASTER_WEIGHTS", {"technical": 2.0, "macro": 0.5})
        with pytest.raises(ValueError, match="static sum"):
            wv.validate_master_weights()


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


class TestL5VerdaIndependence:
    """Verify L5 core is VERDA-independent (D-059)."""

    def test_l5_no_verda_dependency(self):
        """L5 core connector'larında VERDA referansı olmamalı."""
        import pathlib

        files_to_check = [
            "src/signals/layers/smart_money_layer.py",
            "src/signals/layers/connectors/smart_money_connector.py",
            "src/signals/layers/connectors/smart_money_mock.py",
            "src/signals/layers/connectors/bist_datastore_connector.py",
        ]
        for fpath in files_to_check:
            p = pathlib.Path(fpath)
            if p.exists():
                source = p.read_text(encoding="utf-8")
                assert "verda" not in source.lower(), (
                    f"{fpath} contains 'verda' reference — L5 core must be VERDA-free"
                )


pytestmark = pytest.mark.baseline
