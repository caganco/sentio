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

    def test_no_hardcoded_weights_in_any_layer(self):
        """src/signals/layers/*_layer.py must not hardcode a non-zero weight.

        A `weight=0.0` neutral/disabled stub does not bypass MASTER_WEIGHTS
        (the layer contributes nothing); a real literal like 0.20 does. Only
        non-zero literals are violations — import from MASTER_WEIGHTS instead.
        """
        layers_dir = Path(__file__).parent.parent / "src" / "signals" / "layers"
        pattern = re.compile(r"\bweight\s*=\s*(0\.\d+)")
        violations = []
        for f in layers_dir.glob("*_layer.py"):
            source = f.read_text(encoding="utf-8")
            if any(float(v) != 0.0 for v in pattern.findall(source)):
                violations.append(f.name)
        assert not violations, (
            f"Şu layer dosyaları hardcoded weight içeriyor: {violations}. "
            f"MASTER_WEIGHTS'ten import et."
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


class TestBacktestEngineIntegrity:
    """Backtest engine must not bypass MASTER_WEIGHTS or swallow errors."""

    def test_no_hardcoded_weights_in_backtest_engine(self):
        """src/backtest/engine.py MASTER_WEIGHTS bypass etmemeli."""
        path = Path(__file__).parent.parent / "src" / "backtest" / "engine.py"
        source = path.read_text(encoding="utf-8")
        pattern = re.compile(r"(?<!\w)(0\.\d{2})\s*[\+\*].*score", re.MULTILINE)
        matches = pattern.findall(source)
        assert not matches, (
            f"backtest/engine.py hardcoded weight literal içeriyor: {matches}. "
            f"MASTER_WEIGHTS'ten import et."
        )

    def test_backtest_engine_imports_master_weights(self):
        """backtest/engine.py MASTER_WEIGHTS'i thresholds.py'den import etmeli."""
        path = Path(__file__).parent.parent / "src" / "backtest" / "engine.py"
        source = path.read_text(encoding="utf-8")
        assert "MASTER_WEIGHTS" in source, (
            "backtest/engine.py MASTER_WEIGHTS import etmiyor — "
            "thresholds.py'den import ekle."
        )

    def test_no_bare_except_in_backtest(self):
        """backtest/engine.py bare except bloğu içermemeli."""
        path = Path(__file__).parent.parent / "src" / "backtest" / "engine.py"
        source = path.read_text(encoding="utf-8")
        assert (
            "except Exception:\n        return" not in source
            and "except:\n" not in source
        ), "backtest/engine.py bare except bloğu içeriyor. Logger ile logla."


class TestVolatilityAwareStopConstants:
    """D-110 / SPEC_STOPLOSS_VOLATILITY_AWARE_1: tier ordering + sanity."""

    def test_stop_constants_ordered(self):
        from src.signals.thresholds import (
            EXIT_STOP_LOSS,
            STOP_HARD_FLOOR,
            STOP_LOSS_EXTREME_VOL,
            STOP_LOSS_HIGH_VOL,
            STOP_LOSS_LOW_VOL,
            STOP_LOSS_MID_VOL,
        )
        assert STOP_LOSS_LOW_VOL < STOP_LOSS_MID_VOL < STOP_LOSS_HIGH_VOL < STOP_LOSS_EXTREME_VOL
        assert STOP_LOSS_EXTREME_VOL <= STOP_HARD_FLOOR
        # Mid-vol stop must match legacy -8% (1 - 0.92)
        assert round(STOP_LOSS_MID_VOL, 4) == round(1.0 - EXIT_STOP_LOSS, 4)

    def test_stop_calculator_importable(self):
        from src.risk.stop_calculator import calculate_stop, classify_vol_tier
        r = calculate_stop(100.0, 3.0, 100_000)
        assert r.stop_price > 0
        assert classify_vol_tier(0.03) == "mid"


class TestTpRegimeConditionalConstants:
    """D-109 / SPEC_TP_REGIME_CONDITIONAL_1: BULL TP multiplier contract."""

    def test_bull_tp_constants_exist_and_wider_than_baseline(self):
        from src.signals.thresholds import (
            ATR_TP1_MIN_DISTANCE_BULL,
            ATR_TP1_MULTIPLE,
            ATR_TP1_MULTIPLE_BULL,
            ATR_TP2_MULTIPLE,
            ATR_TP2_MULTIPLE_BULL,
            ATR_TP3_MULTIPLE,
            ATR_TP3_MULTIPLE_BULL,
        )
        assert ATR_TP1_MULTIPLE_BULL > ATR_TP1_MULTIPLE       # 2.5 > 1.5
        assert ATR_TP2_MULTIPLE_BULL > ATR_TP2_MULTIPLE       # 4.0 > 3.0
        assert ATR_TP3_MULTIPLE_BULL > ATR_TP3_MULTIPLE       # 6.5 > 5.0
        assert ATR_TP1_MIN_DISTANCE_BULL == 2.0

    def test_bull_tp_ordering(self):
        from src.signals.thresholds import (
            ATR_TP1_MULTIPLE_BULL,
            ATR_TP2_MULTIPLE_BULL,
            ATR_TP3_MULTIPLE_BULL,
        )
        assert ATR_TP1_MULTIPLE_BULL < ATR_TP2_MULTIPLE_BULL < ATR_TP3_MULTIPLE_BULL


class TestMacroGateSofteningConstants:
    """D-108 / SPEC_MACRO_GATE_SOFTENING_1: gate v2 constants & contract."""

    def test_cds_gate_constants_exist_and_ordered(self):
        from src.signals.thresholds import (
            CDS_PERCENTILE_HIGH,
            CDS_PERCENTILE_LOW,
            CDS_PERCENTILE_WINDOW,
            CDS_SCALING_HIGH,
            MACRO_GATE_HARD_EXIT_CDS_BPS,
            MACRO_GATE_SOFT_BEAR_BASE,
        )
        assert CDS_PERCENTILE_LOW < CDS_PERCENTILE_HIGH
        assert 0.0 < CDS_SCALING_HIGH < 1.0
        assert MACRO_GATE_SOFT_BEAR_BASE == 0.25
        assert CDS_PERCENTILE_WINDOW == 252
        assert MACRO_GATE_HARD_EXIT_CDS_BPS == 600.0

    def test_v2_returns_float_scaling_in_unit_range(self):
        from src.signals.macro_regime_gate import calculate_macro_regime_scaling_v2
        r = calculate_macro_regime_scaling_v2(42.0, 0.40)
        assert 0.0 <= r.scaling <= 1.0

    def test_v1_legacy_scaling_unchanged(self):
        from src.signals.macro_regime_gate import calculate_macro_regime_scaling
        assert calculate_macro_regime_scaling(65.0) == 1.0
        assert calculate_macro_regime_scaling(50.0) == 0.8
        assert calculate_macro_regime_scaling(40.0) == 0.0


class TestCustodyConstants:
    """D-116 / SPEC_FINTABLES_TAKAS_SCRAPER_1: custody sabitleri thresholds.py'de."""

    def test_custody_db_path_from_thresholds(self):
        """CUSTODY_DB_PATH thresholds.py'den gelmeli — hardcoded olmamalı."""
        from src.signals.thresholds import CUSTODY_DB_PATH
        assert isinstance(CUSTODY_DB_PATH, str)
        assert "custody" in CUSTODY_DB_PATH

    def test_custody_constants_exist_and_subweights_sum_to_one(self):
        """D-116 sabitleri tanımlı; foreign sub-weight toplamı 1.0."""
        from src.signals.thresholds import (
            CUSTODY_BACKFILL_DAYS,
            CUSTODY_FOREIGN_LEVEL_WEIGHT,
            CUSTODY_MOMENTUM_30D_WEIGHT,
            CUSTODY_PERSISTENCE_WEIGHT,
            CUSTODY_SCRAPE_RATE_LIMIT_SEC,
            CUSTODY_STALE_HOURS,
        )
        total = (
            CUSTODY_FOREIGN_LEVEL_WEIGHT
            + CUSTODY_MOMENTUM_30D_WEIGHT
            + CUSTODY_PERSISTENCE_WEIGHT
        )
        assert abs(total - 1.0) < 1e-9
        assert CUSTODY_STALE_HOURS > 0
        assert CUSTODY_BACKFILL_DAYS > 0
        assert CUSTODY_SCRAPE_RATE_LIMIT_SEC > 0

    def test_bist50_tickers_in_thresholds(self):
        """CUSTODY_BIST50_TICKERS tuple, ≥30 ticker, duplikasyon yok, AKSEN var."""
        from src.signals.thresholds import CUSTODY_BIST50_TICKERS
        assert isinstance(CUSTODY_BIST50_TICKERS, tuple)
        assert len(CUSTODY_BIST50_TICKERS) >= 30
        assert "AKSEN" in CUSTODY_BIST50_TICKERS
        # SPEC taslağındaki TKFEN duplikasyonu düzeltildi → tüm ticker'lar unique.
        assert len(set(CUSTODY_BIST50_TICKERS)) == len(CUSTODY_BIST50_TICKERS)


class TestHMMRegimeWeightConstants:
    """D-123 / SPEC_HMM_REGIME_WEIGHTS_1: HMM sabitleri thresholds.py'de, invariantlar sağlanmalı."""

    def test_hmm_constants_exist_and_types_correct(self):
        """ENABLE_HMM_WEIGHTS bool, HMM_N_COMPONENTS==3, tip ve değer kontrolü."""
        from src.signals.thresholds import (
            ENABLE_HMM_WEIGHTS,
            HMM_COVARIANCE_TYPE,
            HMM_MIN_TRAIN_DAYS,
            HMM_N_COMPONENTS,
            HMM_N_ITER,
            HMM_RANDOM_STATE,
            HMM_RETRAIN_INTERVAL_DAYS,
        )
        assert isinstance(ENABLE_HMM_WEIGHTS, bool)
        assert ENABLE_HMM_WEIGHTS is False   # default değişmemeli
        assert HMM_N_COMPONENTS == 3
        assert HMM_COVARIANCE_TYPE == "full"
        assert HMM_N_ITER > 0
        assert HMM_MIN_TRAIN_DAYS >= 252
        assert HMM_RETRAIN_INTERVAL_DAYS > 0
        assert isinstance(HMM_RANDOM_STATE, int)

    def test_hmm_all_tables_sum_to_one(self):
        """Her HMM ağırlık tablosu Σ = 1.00 (tolerans 1e-9)."""
        from src.signals.thresholds import HMM_WEIGHTS_BEAR, HMM_WEIGHTS_BULL, HMM_WEIGHTS_NEUTRAL
        for name, table in [
            ("BULL", HMM_WEIGHTS_BULL),
            ("NEUTRAL", HMM_WEIGHTS_NEUTRAL),
            ("BEAR", HMM_WEIGHTS_BEAR),
        ]:
            assert abs(sum(table.values()) - 1.0) < 1e-9, (
                f"HMM_WEIGHTS_{name} sum = {sum(table.values())} ≠ 1.0"
            )

    def test_hmm_neutral_weights_equal_master(self):
        """HMM_WEIGHTS_NEUTRAL == MASTER_WEIGHTS — kritik design invariant."""
        from src.signals.thresholds import HMM_WEIGHTS_NEUTRAL, MASTER_WEIGHTS
        assert dict(HMM_WEIGHTS_NEUTRAL) == dict(MASTER_WEIGHTS), (
            "HMM_WEIGHTS_NEUTRAL must be identical to MASTER_WEIGHTS "
            "so NEUTRAL regime == baseline behavior"
        )

    def test_hmm_tables_have_same_keys_as_master(self):
        """Tüm HMM tabloları MASTER_WEIGHTS ile aynı key set'ine sahip olmalı."""
        from src.signals.thresholds import (
            HMM_WEIGHTS_BEAR,
            HMM_WEIGHTS_BULL,
            HMM_WEIGHTS_NEUTRAL,
            MASTER_WEIGHTS,
        )
        expected_keys = set(MASTER_WEIGHTS.keys())
        for name, table in [
            ("BULL", HMM_WEIGHTS_BULL),
            ("NEUTRAL", HMM_WEIGHTS_NEUTRAL),
            ("BEAR", HMM_WEIGHTS_BEAR),
        ]:
            assert set(table.keys()) == expected_keys, (
                f"HMM_WEIGHTS_{name} keys {set(table.keys())} ≠ MASTER_WEIGHTS keys {expected_keys}"
            )

    def test_hmm_bull_tech_weight_above_master(self):
        """BULL rejimde teknik ağırlık MASTER_WEIGHTS'ten yüksek olmalı (momentum premium)."""
        from src.signals.thresholds import HMM_WEIGHTS_BULL, MASTER_WEIGHTS
        assert HMM_WEIGHTS_BULL["technical"] > MASTER_WEIGHTS["technical"]

    def test_hmm_bear_macro_weight_above_master(self):
        """BEAR rejimde makro ağırlık MASTER_WEIGHTS'ten yüksek olmalı (macro dominant)."""
        from src.signals.thresholds import HMM_WEIGHTS_BEAR, MASTER_WEIGHTS
        assert HMM_WEIGHTS_BEAR["macro"] > MASTER_WEIGHTS["macro"]

    def test_hmm_model_path_in_thresholds(self):
        """HMM_MODEL_PATH thresholds.py'den gelmeli, 'hmm' içermeli."""
        from src.signals.thresholds import HMM_MODEL_PATH
        assert isinstance(HMM_MODEL_PATH, str)
        assert "hmm" in HMM_MODEL_PATH


pytestmark = pytest.mark.baseline
