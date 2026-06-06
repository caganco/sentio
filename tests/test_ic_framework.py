"""IC Framework Faz 1 tests (D-139, SPEC_IC_FRAMEWORK_1)."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analytics.ic_calculator import FDRResult, ICCalculator
from src.analytics.ic_history import IC_HISTORY_SCHEMA, ICHistoryWriter
from src.data.signal_logger import _HORIZONS, ReturnFiller, ReturnRecord


# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------

LAYER_COLS = (
    "l1_tech_score", "l2_macro_score", "l3_kap_score",
    "l4_sent_score", "l5_sm_score", "l6_risk_score",
)


def _make_layer_panel(n_dates: int = 30, n_symbols: int = 12, seed: int = 7):
    """(signal_df, returns_df) with horizons 5 and 20.

    l1_tech_score is a strong-but-noisy proxy for the 5d forward return (so
    its IC is significantly positive); l2..l6 are random (IC near zero).
    """
    rng = np.random.default_rng(seed)
    dates = [date(2026, 1, 5) + timedelta(days=i) for i in range(n_dates)]
    symbols = [f"SYM{j:02d}" for j in range(n_symbols)]
    r5 = rng.standard_normal((n_dates, n_symbols)) * 0.02
    r20 = rng.standard_normal((n_dates, n_symbols)) * 0.03

    sig_rows, ret_rows = [], []
    for i, d in enumerate(dates):
        for j, sym in enumerate(symbols):
            sig_rows.append({
                "date": d, "symbol": sym,
                "l1_tech_score": float(r5[i, j] + rng.standard_normal() * 0.004),
                "l2_macro_score": float(rng.standard_normal()),
                "l3_kap_score": float(rng.standard_normal()),
                "l4_sent_score": float(rng.standard_normal()),
                "l5_sm_score": float(rng.standard_normal()),
                "l6_risk_score": float(rng.standard_normal()),
                "regime_label": "BULL", "liquidity_tier": "BIST100",
                "price_limit_hit": False,
            })
            ret_rows.append({"signal_date": d, "symbol": sym, "horizon": 5,
                             "forward_return": float(r5[i, j]), "price_limit_hit": False,
                             "filled_at": datetime(2026, 5, 20, tzinfo=timezone.utc)})
            ret_rows.append({"signal_date": d, "symbol": sym, "horizon": 20,
                             "forward_return": float(r20[i, j]), "price_limit_hit": False,
                             "filled_at": datetime(2026, 5, 20, tzinfo=timezone.utc)})
    return pd.DataFrame(sig_rows), pd.DataFrame(ret_rows)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestICConstants:

    def test_new_ic_constant_values(self):
        from src.signals import thresholds as t
        assert t.IC_HORIZON_T10 == 10
        assert t.IC_BAYESIAN_TAU_MIN_DAYS == 60
        assert t.IC_BAYESIAN_TAU_FULL_DAYS == 730
        assert t.IC_FDR_ALPHA == 0.10
        assert t.IC_FDR_M_TESTS == 12
        assert t.IC_INVESTABLE_MONTHS_MIN == 6   # maintainer override (was 24)

    def test_decay_slope_ordering(self):
        from src.signals.thresholds import IC_DECAY_SLOPE_REVIEW, IC_DECAY_SLOPE_WARN
        assert IC_DECAY_SLOPE_REVIEW < IC_DECAY_SLOPE_WARN < 0

    def test_path_constants_are_str(self):
        from src.signals import thresholds as t
        assert isinstance(t.IC_HISTORY_PATH, str) and "ic_history" in t.IC_HISTORY_PATH
        assert isinstance(t.IC_WEIGHT_HISTORY_PATH, str) and "weight_history" in t.IC_WEIGHT_HISTORY_PATH
        assert isinstance(t.DELISTED_TICKERS_PATH, str) and "delisted" in t.DELISTED_TICKERS_PATH
        assert isinstance(t.SECTOR_RETURNS_CACHE, str) and "sector" in t.SECTOR_RETURNS_CACHE


# ---------------------------------------------------------------------------
# ReturnRecord / ReturnFiller (T10 + sector demean)
# ---------------------------------------------------------------------------

class TestReturnFillerSector:

    def test_return_record_has_sector_fields_default_none(self):
        r = ReturnRecord(signal_date=date(2026, 5, 1), symbol="AAA", horizon=5,
                         forward_return=0.01, price_limit_hit=False,
                         filled_at=datetime(2026, 5, 6, tzinfo=timezone.utc))
        assert r.sector_adjusted_return is None
        assert r.sector is None

    def test_horizons_include_t10(self):
        assert 10 in _HORIZONS

    def _run(self, tmp_path: Path, prices: dict, sectors: dict):
        sm = tmp_path / "sector_mapping.json"
        sm.write_text(json.dumps({t: {"sector": s} for t, s in sectors.items()}),
                      encoding="utf-8")
        returns_path = tmp_path / "returns.parquet"
        filler = ReturnFiller(returns_path=str(returns_path), sector_mapping_path=str(sm))
        today = date(2026, 5, 20)

        def price_fetcher(symbol, d):
            return prices[symbol][1] if d == today else prices[symbol][0]

        def reader(d):
            return pd.DataFrame([{"symbol": s, "date": d, "price_limit_hit": False}
                                 for s in prices])

        filler.fill(today, price_fetcher, reader)
        return pd.read_parquet(returns_path)

    def test_sector_demean_correct(self, tmp_path: Path):
        # AAA +10%, BBB -10%, same sector X -> mean 0 -> adj == raw
        df = self._run(tmp_path,
                       prices={"AAA": (100.0, 110.0), "BBB": (100.0, 90.0)},
                       sectors={"AAA": "X", "BBB": "X"})
        sub = df[df["horizon"] == 5]
        aaa = sub[sub["symbol"] == "AAA"].iloc[0]
        bbb = sub[sub["symbol"] == "BBB"].iloc[0]
        assert aaa["forward_return"] == pytest.approx(0.10, abs=1e-4)
        assert aaa["sector"] == "X"
        assert aaa["sector_adjusted_return"] == pytest.approx(0.10, abs=1e-4)
        assert bbb["sector_adjusted_return"] == pytest.approx(-0.10, abs=1e-4)

    def test_unknown_ticker_sector_none(self, tmp_path: Path):
        df = self._run(tmp_path,
                       prices={"AAA": (100.0, 110.0), "CCC": (100.0, 105.0)},
                       sectors={"AAA": "X"})   # CCC not mapped
        sub = df[df["horizon"] == 5]
        ccc = sub[sub["symbol"] == "CCC"].iloc[0]
        assert ccc["sector"] is None
        assert pd.isna(ccc["sector_adjusted_return"])


# ---------------------------------------------------------------------------
# compute_fdr_panel
# ---------------------------------------------------------------------------

class TestFDRPanel:

    def test_returns_fdrresult_shape(self):
        sig, ret = _make_layer_panel()
        r = ICCalculator(sig, ret).compute_fdr_panel(date(2026, 5, 20))
        assert isinstance(r, FDRResult)
        assert r.method == "fdr_bh"
        assert r.alpha == 0.10
        assert r.n_tests == 12
        assert len(r.results) == 12
        # 6 layers x 2 horizons {5, 20}
        assert {row["horizon"] for row in r.results} == {5, 20}

    def test_p_adj_ge_p_raw(self):
        """BH adjusted p-values are >= raw p-values (step-up monotonicity)."""
        sig, ret = _make_layer_panel()
        r = ICCalculator(sig, ret).compute_fdr_panel(date(2026, 5, 20))
        for row in r.results:
            if not np.isnan(row["p_adj"]):
                assert row["p_adj"] >= row["p_raw"] - 1e-9

    def test_detects_real_signal(self):
        """l1_tech_score (proxy for r5) should be FDR-significant at horizon 5."""
        sig, ret = _make_layer_panel()
        r = ICCalculator(sig, ret).compute_fdr_panel(date(2026, 5, 20))
        l1_t5 = [x for x in r.results
                 if x["layer"] == "l1_tech_score" and x["horizon"] == 5][0]
        assert l1_t5["ic"] > 0.2
        assert l1_t5["significant"] is True


# ---------------------------------------------------------------------------
# ICHistoryWriter
# ---------------------------------------------------------------------------

class TestICHistoryWriter:

    def test_run_daily_writes_k04_schema(self, tmp_path: Path):
        sig, ret = _make_layer_panel()
        calc = ICCalculator(sig, ret)
        hp = tmp_path / "ic_history.parquet"
        writer = ICHistoryWriter(history_path=str(hp))
        n = writer.run_daily(date(2026, 5, 20), calc=calc)
        assert n == 12
        assert hp.exists()
        df = pd.read_parquet(hp)
        assert list(df.columns) == [f.name for f in IC_HISTORY_SCHEMA]
        assert (df["date"].astype(str) == "2026-05-20").all()
        assert not df["group_adjust"].any()        # Faz 1 raw IC
        assert df["icir_120d"].isna().all()         # Faz 2 column

    def test_append_idempotent_same_day(self, tmp_path: Path):
        sig, ret = _make_layer_panel()
        calc = ICCalculator(sig, ret)
        hp = tmp_path / "ic_history.parquet"
        writer = ICHistoryWriter(history_path=str(hp))
        d = date(2026, 5, 20)
        writer.run_daily(d, calc=calc)
        second = writer.run_daily(d, calc=calc)   # same day -> skip
        assert second == 0
        assert len(pd.read_parquet(hp)) == 12

    def test_no_data_returns_zero(self, tmp_path: Path):
        """Missing signal logs -> NO_DATA, nothing written."""
        writer = ICHistoryWriter(
            history_path=str(tmp_path / "ic_history.parquet"),
            signal_log_dir=str(tmp_path / "nonexistent"),
            returns_path=str(tmp_path / "returns.parquet"),
        )
        assert writer.run_daily(date(2026, 5, 20)) == 0

    def test_module_does_not_import_engine(self):
        src = Path(__file__).parent.parent / "src" / "analytics" / "ic_history.py"
        content = src.read_text(encoding="utf-8")
        assert "from src.signals.engine" not in content
        assert "import src.signals.engine" not in content


# ---------------------------------------------------------------------------
# IC Decay Monitor (D-140)
# ---------------------------------------------------------------------------

class TestDecayMonitor:

    def _write_ic_history(self, path: Path, n_days: int, slope: float = 0.0, seed: int = 1):
        """Write synthetic ic_history.parquet with given IC trend slope per day."""
        import pyarrow as pa
        import pyarrow.parquet as pq
        from src.analytics.ic_history import IC_HISTORY_SCHEMA

        rng = np.random.default_rng(seed)
        rows = []
        for i in range(n_days):
            for layer in ("l1_tech_score", "l2_macro_score"):
                for horizon in (5, 20):
                    ic_val = 0.05 + slope * i + rng.standard_normal() * 0.005
                    rows.append({
                        "date": date(2026, 1, 5) + timedelta(days=i),
                        "layer": layer,
                        "horizon": horizon,
                        "ic": float(ic_val),
                        "p_value": 0.05,
                        "p_adj": 0.05,
                        "significant": True,
                        "n_obs": 100,
                        "group_adjust": False,
                        "icir_120d": float("nan"),
                        "decay_slope_30d": float("nan"),
                        "decay_slope_60d": float("nan"),
                    })
        df = pd.DataFrame(rows)
        tbl = pa.Table.from_pandas(df, schema=IC_HISTORY_SCHEMA, safe=False)
        pq.write_table(tbl, path, compression="snappy")

    def test_compute_decay_returns_expected_keys(self, tmp_path: Path):
        hp = tmp_path / "ic_history.parquet"
        self._write_ic_history(hp, n_days=40)
        sig, ret = _make_layer_panel()
        result = ICCalculator(sig, ret).compute_decay(
            "l1_tech_score", 5, history_path=str(hp))
        assert set(result.keys()) == {"slope_30d", "slope_60d", "slope_120d", "status"}

    def test_compute_decay_no_history_returns_ok(self, tmp_path: Path):
        sig, ret = _make_layer_panel()
        result = ICCalculator(sig, ret).compute_decay(
            "l1_tech_score", 5,
            history_path=str(tmp_path / "nonexistent.parquet"))
        assert result["status"] == "ok"
        assert np.isnan(result["slope_30d"])

    def test_compute_decay_ok_status(self, tmp_path: Path):
        hp = tmp_path / "ic_history.parquet"
        self._write_ic_history(hp, n_days=40, slope=0.0001)   # slight positive trend
        sig, ret = _make_layer_panel()
        result = ICCalculator(sig, ret).compute_decay(
            "l1_tech_score", 5, history_path=str(hp))
        assert result["status"] == "ok"

    def test_compute_decay_warn_status(self, tmp_path: Path):
        hp = tmp_path / "ic_history.parquet"
        # slope=-0.0015 per day -> after 30 obs: well below IC_DECAY_SLOPE_WARN=-0.001
        self._write_ic_history(hp, n_days=40, slope=-0.0015)
        sig, ret = _make_layer_panel()
        result = ICCalculator(sig, ret).compute_decay(
            "l1_tech_score", 5, history_path=str(hp))
        assert result["status"] == "warn"

    def test_compute_decay_review_status(self, tmp_path: Path):
        hp = tmp_path / "ic_history.parquet"
        # slope=-0.003 per day -> below IC_DECAY_SLOPE_REVIEW=-0.002
        self._write_ic_history(hp, n_days=40, slope=-0.003)
        sig, ret = _make_layer_panel()
        result = ICCalculator(sig, ret).compute_decay(
            "l1_tech_score", 5, history_path=str(hp))
        assert result["status"] == "review"

    def test_compute_decay_insufficient_history_nan(self, tmp_path: Path):
        hp = tmp_path / "ic_history.parquet"
        self._write_ic_history(hp, n_days=10, slope=0.0)   # only 10 rows < 15 (half of 30)
        sig, ret = _make_layer_panel()
        result = ICCalculator(sig, ret).compute_decay(
            "l1_tech_score", 5, history_path=str(hp))
        assert np.isnan(result["slope_30d"])

    def test_ic_history_writer_writes_decay_after_30_days(self, tmp_path: Path):
        """After 35 days of existing history, run_daily writes non-NaN slope_30d."""
        hp = tmp_path / "ic_history.parquet"
        self._write_ic_history(hp, n_days=35)
        sig, ret = _make_layer_panel()
        calc = ICCalculator(sig, ret)
        writer = ICHistoryWriter(history_path=str(hp))
        writer.run_daily(date(2026, 5, 24), calc=calc)
        df = pd.read_parquet(hp)
        today_rows = df[df["date"].astype(str) == "2026-05-24"]
        assert not today_rows.empty
        l1 = today_rows[today_rows["layer"] == "l1_tech_score"]
        assert not l1.empty
        # slope_30d non-NaN because >= 15 rows in 30d window exist
        assert not np.isnan(l1.iloc[0]["decay_slope_30d"])


# ---------------------------------------------------------------------------
# Delisted Tickers (D-140, SPEC K-07)
# ---------------------------------------------------------------------------

class TestDelistedSkip:

    def _delisted_json(self, path: Path, entries: list) -> None:
        path.write_text(
            json.dumps({"version": "1.0", "tickers": entries}),
            encoding="utf-8",
        )

    def _run_filler(
        self,
        tmp_path: Path,
        prices: dict,
        delist_path: Path | None = None,
    ) -> pd.DataFrame:
        returns_path = tmp_path / "returns.parquet"
        sm = tmp_path / "sector_mapping.json"
        sm.write_text("{}", encoding="utf-8")
        filler = ReturnFiller(
            returns_path=str(returns_path),
            sector_mapping_path=str(sm),
            delisted_map_path=str(delist_path) if delist_path else None,
        )
        today = date(2026, 5, 20)

        def price_fetcher(symbol, d):
            return prices[symbol][1] if d == today else prices[symbol][0]

        def reader(d):
            return pd.DataFrame([
                {"symbol": s, "date": d, "price_limit_hit": False}
                for s in prices
            ])

        filler.fill(today, price_fetcher, reader)
        if not returns_path.exists():
            return pd.DataFrame()
        return pd.read_parquet(returns_path)

    def test_delisted_symbol_skipped(self, tmp_path: Path):
        """Symbol with delist_date <= today is skipped for ALL horizons."""
        dl = tmp_path / "delisted.json"
        # today = 2026-05-20 >= delist_date 2026-05-10 -> currently delisted -> skip
        self._delisted_json(dl, [{"ticker": "AAA", "delist_date": "2026-05-10"}])
        df = self._run_filler(tmp_path, {"AAA": (100.0, 110.0)}, delist_path=dl)
        assert df.empty or "AAA" not in df["symbol"].tolist()

    def test_non_delisted_symbol_not_skipped(self, tmp_path: Path):
        """Symbol with delist_date far in the future is not skipped."""
        dl = tmp_path / "delisted.json"
        self._delisted_json(dl, [{"ticker": "ZZZ", "delist_date": "2020-01-01"}])
        df = self._run_filler(tmp_path, {"BBB": (100.0, 110.0)}, delist_path=dl)
        assert not df.empty
        assert "BBB" in df["symbol"].tolist()

    def test_unknown_ticker_not_in_delisted_map(self, tmp_path: Path):
        """Symbol absent from delisted map is not affected."""
        dl = tmp_path / "delisted.json"
        self._delisted_json(dl, [{"ticker": "OTHER", "delist_date": "2020-01-01"}])
        df = self._run_filler(tmp_path, {"CCC": (100.0, 110.0)}, delist_path=dl)
        assert not df.empty
        assert "CCC" in df["symbol"].tolist()

    def test_mixed_delisted_and_active(self, tmp_path: Path):
        """Delisted tickers filtered; active tickers proceed normally."""
        dl = tmp_path / "delisted.json"
        self._delisted_json(dl, [{"ticker": "AAA", "delist_date": "2026-05-10"}])
        df = self._run_filler(
            tmp_path,
            {"AAA": (100.0, 110.0), "BBB": (100.0, 105.0)},
            delist_path=dl,
        )
        symbols = df["symbol"].tolist() if not df.empty else []
        assert "BBB" in symbols
        assert "AAA" not in symbols
