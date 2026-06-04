"""Tier-A tests for the data adapter -- synthetic parquets only (real
clean_universe/snapshots parquets are gitignored, so CI never sees them)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.engine import data_adapter as da
from src.engine.contracts import Frequency, Panel


def _write_synthetic(root: Path) -> pd.DatetimeIndex:
    cu = root / "data" / "clean_universe"
    snap = root / "data" / "snapshots"
    cu.mkdir(parents=True)
    snap.mkdir(parents=True)
    dates = pd.bdate_range("2019-01-02", periods=6)
    # symbol -> (close_base, value_tl, bist100, bist30, drop_day_index | None)
    spec = {
        "AAA": (10.0, 2e7, 1, 1, None),
        "BBB": (20.0, 5e7, 1, 0, None),
        "CCC": (5.0, 1e6, 1, 0, None),  # illiquid (below 1e7 floor)
        "DDD": (8.0, 3e7, 0, 0, 3),  # one-day gap -> coverage < 1.0
    }
    rows = []
    for sym, (base, vtl, b100, b30, drop) in spec.items():
        for i, dt in enumerate(dates):
            if drop is not None and i == drop:
                continue
            grow = 1.0 + 0.01 * i
            rows.append(
                {
                    "date": dt,
                    "symbol": sym,
                    "adjusted_close": base * grow,
                    "tr_index_gross": grow,
                    "tr_index_net": grow,
                    "value_tl": vtl,
                    "bist100": b100,
                    "bist30": b30,
                }
            )
    pd.DataFrame(rows).to_parquet(cu / "adjusted_prices_2019_2026.parquet")
    for name in ("exposure_d187_xu100", "exposure_d187_tufe", "exposure_d187_tlref"):
        pd.DataFrame(
            {"date": dates, "value": np.linspace(1.0, 1.05, len(dates))}
        ).to_parquet(snap / f"{name}.parquet")
    return dates


class TestLoadPanel:
    def test_shapes_and_fields(self, tmp_path):
        dates = _write_synthetic(tmp_path)
        p = da.load_panel(tmp_path)
        assert isinstance(p, Panel)
        assert set(p.names) == {"AAA", "BBB", "CCC", "DDD"}
        assert p.close.shape[0] == len(dates)
        assert not p.tr_gross.isna().all().all()  # total-return surfaced
        assert "bist100" in p.membership
        assert "bist30" in p.membership
        assert len(p.market) == len(dates)
        assert p.frequency is Frequency.DAILY

    def test_window_filter(self, tmp_path):
        dates = _write_synthetic(tmp_path)
        p = da.load_panel(tmp_path, start=dates[1], end=dates[3])
        assert list(p.dates) == list(dates[1:4])


class TestLiquidNames:
    def test_floor_excludes_illiquid(self, tmp_path):
        dates = _write_synthetic(tmp_path)
        p = da.load_panel(tmp_path)
        liq = da.liquid_names(p, dates[-1], min_tl=1e7, trailing=63)
        assert {"AAA", "BBB", "DDD"} <= liq
        assert "CCC" not in liq


class TestContinuousBasket:
    def test_gap_excluded_at_full_coverage(self, tmp_path):
        dates = _write_synthetic(tmp_path)
        p = da.load_panel(tmp_path)
        full = da.continuous_basket(p, dates[0], dates[-1], min_cov=1.0)
        assert "DDD" not in full  # missing one day
        assert {"AAA", "BBB", "CCC"} <= set(full)

    def test_gap_included_at_lower_coverage(self, tmp_path):
        dates = _write_synthetic(tmp_path)
        p = da.load_panel(tmp_path)
        loose = da.continuous_basket(p, dates[0], dates[-1], min_cov=0.5)
        assert "DDD" in loose


class TestForwardReturn:
    def test_known_value_and_no_future(self, tmp_path):
        dates = _write_synthetic(tmp_path)
        p = da.load_panel(tmp_path)
        fr = da.forward_return(p, 1)
        assert fr.loc[dates[0], "AAA"] == pytest.approx(0.01, abs=1e-9)
        assert np.isnan(fr.loc[dates[-1], "AAA"])  # last row has no t+1
