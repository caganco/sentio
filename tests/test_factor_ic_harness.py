"""Faz 0 Factor IC Harness tests (D-177). Synthetic/fixture only, no network."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.screening import factors, snapshot
from src.screening import factor_ic_harness as h


# ---------------------------------------------------------------------------
# Synthetic builders
# ---------------------------------------------------------------------------

def _dates(n: int) -> pd.DatetimeIndex:
    return pd.bdate_range("2024-01-01", periods=n)


def _panel(dates, symbols, values: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame(values, index=dates, columns=symbols)


# ---------------------------------------------------------------------------
# 1. IC unit (Spearman): perfect / anti / random
# ---------------------------------------------------------------------------

def test_ic_unit_spearman_sign():
    dates, syms = _dates(30), [f"S{i}" for i in range(10)]
    order = np.tile(np.arange(10, dtype=float), (30, 1))
    factor = _panel(dates, syms, order)
    fwd_perfect = _panel(dates, syms, order)             # same ordering -> +1
    fwd_anti = _panel(dates, syms, order[:, ::-1].copy())  # reversed -> -1
    rng = np.random.default_rng(7)
    fwd_rand = _panel(dates, syms, rng.standard_normal((30, 10)))

    assert h.daily_ic_series(factor, fwd_perfect).mean() > 0.99
    assert h.daily_ic_series(factor, fwd_anti).mean() < -0.99
    assert abs(h.daily_ic_series(factor, fwd_rand).mean()) < 0.3


# ---------------------------------------------------------------------------
# 2. Look-ahead guard: factors use only past prices
# ---------------------------------------------------------------------------

def test_lookahead_guard_factor_uses_only_past():
    dates, syms = _dates(120), ["A", "B", "C"]
    rng = np.random.default_rng(1)
    px = 100 * np.cumprod(1 + 0.01 * rng.standard_normal((120, 3)), axis=0)
    close = _panel(dates, syms, px)

    vol_full = factors.realized_vol(close, 20)
    t = dates[80]
    # corrupt all prices AFTER t; realized_vol at dates <= t must be unchanged
    close_mod = close.copy()
    close_mod.loc[dates[81]:] = 9999.0
    vol_mod = factors.realized_vol(close_mod, 20)

    past = vol_full.loc[:t]
    pd.testing.assert_frame_equal(past, vol_mod.loc[:t])


# ---------------------------------------------------------------------------
# 3. Survivorship fixture: harness ingests a delisted ticker while it exists
# ---------------------------------------------------------------------------

def test_survivorship_fixture_ingests_delisted(tmp_path):
    dates = _dates(60)
    syms = ["AAA", "BBB", "DLST"]
    rng = np.random.default_rng(2)
    px = 100 * np.cumprod(1 + 0.01 * rng.standard_normal((60, 3)), axis=0)
    close = _panel(dates, syms, px)
    close.loc[dates[30]:, "DLST"] = np.nan  # delisted halfway

    def fake_fetch(universe, start, end):
        out = {}
        for t in universe:
            s = close[t].dropna()
            if len(s) >= 20:
                out[t] = pd.DataFrame({"Close": s})
        return out

    def fake_macro(start, end):
        return pd.DataFrame({"BIST100": close["AAA"]})  # any index proxy

    long_df, meta = snapshot.freeze_price_snapshot(
        ["AAA", "BBB", "DLST"], "2024-01-01", "2024-12-31",
        out_dir=tmp_path, fetch_fn=fake_fetch, macro_fn=fake_macro,
    )
    assert "DLST" in meta["loaded_universe"]      # ingested while it existed
    stocks, _ = snapshot.to_close_panel(long_df)
    assert stocks.loc[dates[10], "DLST"] == pytest.approx(close.loc[dates[10], "DLST"])
    assert pd.isna(stocks.loc[dates[40], "DLST"])  # excluded after delist
    # known delisted (not provided) reported as a gap
    assert set(meta["survivorship"]["excluded_delisted"]) >= {"KOZAA", "KOZAL"}
    assert "OPTIMISTIC" in meta["survivorship"]["bias_direction"].upper()


# ---------------------------------------------------------------------------
# 4. Snapshot determinism: same frozen parquet -> bit-identical hash + IC
# ---------------------------------------------------------------------------

def test_snapshot_determinism(tmp_path):
    dates = _dates(60)
    syms = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]
    rng = np.random.default_rng(3)
    px = 100 * np.cumprod(1 + 0.01 * rng.standard_normal((60, 6)), axis=0)
    close = _panel(dates, syms, px)

    def fake_fetch(universe, start, end):
        return {t: pd.DataFrame({"Close": close[t]}) for t in universe}

    def fake_macro(start, end):
        return pd.DataFrame({"BIST100": close["AAA"]})

    df1, m1 = snapshot.freeze_price_snapshot(
        syms, "2024-01-01", "2024-12-31", out_dir=tmp_path,
        fetch_fn=fake_fetch, macro_fn=fake_macro, timestamp="FIXED",
    )
    # second call loads the frozen parquet (idempotent) -> identical hash
    df2, m2 = snapshot.freeze_price_snapshot(
        syms, "2024-01-01", "2024-12-31", out_dir=tmp_path,
        fetch_fn=fake_fetch, macro_fn=fake_macro,
    )
    assert m1["content_hash"] == m2["content_hash"]

    stocks, _ = snapshot.to_close_panel(df1)
    fwd = factors.forward_returns(stocks, 5)
    rank = h.rank_panel(stocks, invert=True)
    ic_a = h.daily_ic_series(rank, fwd)
    ic_b = h.daily_ic_series(rank, fwd)
    np.testing.assert_array_equal(ic_a, ic_b)  # bit-identical


# ---------------------------------------------------------------------------
# 5. IC source equivalence: local series == ICCalculator (primitive), <1e-9 @5dp
# ---------------------------------------------------------------------------

def test_ic_source_equivalence_primitive():
    dates, syms = _dates(40), [f"S{i}" for i in range(12)]
    rng = np.random.default_rng(5)
    rank = _panel(dates, syms, rng.random((40, 12)))            # factor rank [0,1]
    fwd = _panel(dates, syms, rng.standard_normal((40, 12)))    # fwd returns

    ranks = {"f1": rank}
    fwd_panels = {5: fwd}
    signal_df = h.build_signal_df(ranks)
    s = fwd.stack(future_stack=True).dropna()
    s.name = "forward_return"
    s.index.names = ["signal_date", "symbol"]
    returns_df = s.reset_index()
    returns_df["horizon"] = 5

    res = h.compute_factor_ic(signal_df, returns_df, ranks, fwd_panels, "f1", 5)
    assert res["ic_source"] == "primitive"
    assert res["equivalence_ok"] is True
    assert not np.isnan(res["primitive"]["mean_ic"])


# ---------------------------------------------------------------------------
# 6. TEST 2: block-bootstrap determinism + delta_skew plumbing
# ---------------------------------------------------------------------------

def test_block_bootstrap_deterministic():
    rng = np.random.default_rng(9)
    series = rng.standard_normal(120)
    ci_a = h.block_bootstrap_ci(series)
    ci_b = h.block_bootstrap_ci(series)
    assert ci_a == ci_b                       # fixed seed -> identical
    assert ci_a[0] <= ci_a[1]


def test_run_test2_deterministic_and_shaped():
    dates = _dates(150)
    syms = [f"S{i}" for i in range(15)]
    rng = np.random.default_rng(11)
    # half low-vol (sigma 0.005), half high-vol (sigma 0.03)
    sig = np.array([0.005] * 7 + [0.03] * 8)
    rets = rng.standard_normal((150, 15)) * sig
    px = 100 * np.cumprod(1 + rets, axis=0)
    close = _panel(dates, syms, px)

    r1 = h.run_test2(close)
    r2 = h.run_test2(close)
    assert r1["delta_skew"] == r2["delta_skew"]                # deterministic
    assert r1["block_bootstrap_ci95"] == r2["block_bootstrap_ci95"]
    assert len(r1["warnings"]) == 4
    assert "DIAGNOSTIC" in r1["status"]


# ---------------------------------------------------------------------------
# 7. RS relativity (drift cancels) + low-vol rank inversion
# ---------------------------------------------------------------------------

def test_rs_relativity_drift_cancels():
    dates, syms = _dates(300), ["A", "B"]
    # both stocks move EXACTLY with the index -> relative strength ~ 0
    base = 100 * np.cumprod(1 + 0.01 * np.sin(np.arange(300) / 5.0))
    close = _panel(dates, syms, np.column_stack([base, base]))
    xu = pd.Series(base, index=dates)
    rs = factors.rs_vs_xu100(close, xu, lookback=126, skip=21)
    tail = rs.dropna()
    assert np.nanmax(np.abs(tail.to_numpy())) < 1e-9


def test_lowvol_rank_inversion():
    dates = _dates(80)
    syms = ["LOW", "HIGH"]
    rng = np.random.default_rng(4)
    low = 100 * np.cumprod(1 + 0.002 * rng.standard_normal(80))
    high = 100 * np.cumprod(1 + 0.05 * rng.standard_normal(80))
    close = _panel(dates, syms, np.column_stack([low, high]))
    vol = factors.realized_vol(close, 20)
    rank = h.rank_panel(vol, invert=True)
    last = rank.dropna().iloc[-1]
    assert last["LOW"] > last["HIGH"]   # low vol -> higher rank


# ---------------------------------------------------------------------------
# 8. D-178: overlap-corrected honest_t deflates naive_t on autocorrelated series
# ---------------------------------------------------------------------------

def test_honest_t_below_naive_on_autocorrelated():
    # AR(1) high-persistence series (overlap-like autocorr), positive mean.
    rng = np.random.default_rng(42)
    n, phi = 300, 0.85
    x = np.empty(n)
    x[0] = 0.0
    for i in range(1, n):
        x[i] = phi * x[i - 1] + 0.02 * rng.standard_normal()
    x = x + 0.05  # positive mean so t-stats are non-trivial
    s = h.ic_stats(x, hac_lag=30)   # bandwidth >> 1 -> HAC widens SE
    assert abs(s["t_nw"]) < abs(s["t_naive"])   # honest_t deflates overlap-inflated naive_t
    assert s["hac_lag"] == 30


# ---------------------------------------------------------------------------
# 9. D-178: non-overlapping stride subsample (count + determinism)
# ---------------------------------------------------------------------------

def test_nonoverlap_stride_subsample():
    ics = np.arange(100, dtype=float)
    r5 = h.nonoverlap_stats(ics, stride=5)
    assert r5["n_obs"] == len(ics[::5])          # 20 disjoint points
    assert r5["stride"] == 5
    assert h.nonoverlap_stats(ics, stride=5) == r5   # deterministic
    assert h.nonoverlap_stats(ics, stride=20)["n_obs"] < r5["n_obs"]  # bigger stride -> fewer


# ---------------------------------------------------------------------------
# D-183 Faz 0b: value factor (P/B, EV/EBITDA) tests
# ---------------------------------------------------------------------------

def _funds(rows):
    cols = ["ticker", "fiscal_year", "period_end", "pub_date", "is_bank",
            "book_eaoop", "issued_capital", "cash", "total_liab",
            "operating_profit", "d_and_a"]
    return pd.DataFrame(rows, columns=cols)


def test_value_ratios_pb_ev_computation():
    funds = _funds([
        {"ticker": "A", "fiscal_year": 2024, "period_end": "2024-12-31",
         "pub_date": "2025-04-30", "is_bank": False, "book_eaoop": 1000.0,
         "issued_capital": 100.0, "cash": 200.0, "total_liab": 500.0,
         "operating_profit": 300.0, "d_and_a": 50.0},
    ])
    dates = pd.bdate_range("2025-06-02", periods=1)
    close = pd.DataFrame({"A": [50.0]}, index=dates)
    pb, ev = h.factors.value_ratios(funds, close, dates, par=1.0)
    # shares=100, mcap=5000; P/B=5000/1000=5; EV=(5000+500-200)=5300; EBITDA=350
    assert pb.iloc[0]["A"] == pytest.approx(5.0)
    assert ev.iloc[0]["A"] == pytest.approx(5300.0 / 350.0)


def test_value_ratios_point_in_time():
    funds = _funds([
        {"ticker": "A", "fiscal_year": 2023, "period_end": "2023-12-31",
         "pub_date": "2024-04-30", "is_bank": False, "book_eaoop": 1000.0,
         "issued_capital": 100.0, "cash": 0.0, "total_liab": 0.0,
         "operating_profit": 100.0, "d_and_a": 0.0},
        {"ticker": "A", "fiscal_year": 2024, "period_end": "2024-12-31",
         "pub_date": "2025-04-30", "is_bank": False, "book_eaoop": 2000.0,
         "issued_capital": 100.0, "cash": 0.0, "total_liab": 0.0,
         "operating_profit": 100.0, "d_and_a": 0.0},
    ])
    dates = pd.DatetimeIndex(["2024-12-01", "2025-06-02"])
    close = pd.DataFrame({"A": [50.0, 50.0]}, index=dates)
    pb, _ = h.factors.value_ratios(funds, close, dates, par=1.0)
    # 2024-12: only 2023 public (book 1000) -> P/B=5; 2025-06: 2024 public (book 2000) -> P/B=2.5
    assert pb.loc["2024-12-01", "A"] == pytest.approx(5.0)
    assert pb.loc["2025-06-02", "A"] == pytest.approx(2.5)


def test_value_ratios_bank_ev_null_and_negative_book():
    funds = _funds([
        {"ticker": "BANK", "fiscal_year": 2024, "period_end": "2024-12-31",
         "pub_date": "2025-04-30", "is_bank": True, "book_eaoop": 1000.0,
         "issued_capital": 100.0, "cash": None, "total_liab": None,
         "operating_profit": None, "d_and_a": None},
        {"ticker": "NEG", "fiscal_year": 2024, "period_end": "2024-12-31",
         "pub_date": "2025-04-30", "is_bank": False, "book_eaoop": -50.0,
         "issued_capital": 100.0, "cash": 0.0, "total_liab": 0.0,
         "operating_profit": 10.0, "d_and_a": 0.0},
    ])
    dates = pd.bdate_range("2025-06-02", periods=1)
    close = pd.DataFrame({"BANK": [50.0], "NEG": [50.0]}, index=dates)
    pb, ev = h.factors.value_ratios(funds, close, dates, par=1.0)
    assert pb.iloc[0]["BANK"] == pytest.approx(5.0)     # bank P/B ok
    assert np.isnan(ev.iloc[0]["BANK"])                 # bank EV/EBITDA NULL (D-182)
    assert np.isnan(pb.iloc[0]["NEG"])                  # negative book -> NaN


def test_usd_conversion_rank_invariant():
    # dividing every ticker's ratio by the same FX(t) cannot change rank (D-180)
    from scipy import stats as _st
    row = np.array([5.0, 2.5, 8.0, 1.1, 3.3])
    fx = 34.7
    rho, _ = _st.spearmanr(row, row / fx)
    assert rho == pytest.approx(1.0)
