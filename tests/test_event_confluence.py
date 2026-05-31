"""D-188 event-triggered confluence -- behavior tests (network-free, synthetic).

Covers: real-YoY surprise deflation, technical confirmation (volume surge + breakout),
look-ahead guard (event_date / t+1 entry), XU100-relative returns, the TWO nulls
(determinism + beats-95 logic), Holm-per-event-type, DEC-046 verdict logic, end-to-end
structure, and the architecture invariant (no composite/engine imports).

Forward-recorder tests live in the same file (added with the recorder module).
"""
from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.screening import event_confirm as ec
from src.screening import event_detect as ed
from src.screening import event_null as en
from src.screening import event_runner as er
from src.screening import event_study as es
from src.screening.event_forward_recorder import EventForwardRecorder, EventReturnFiller


# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------
def _flat_ohlcv(n: int = 300, start: str = "2023-01-02", base: float = 100.0,
                vol: float = 1000.0) -> pd.DataFrame:
    idx = pd.bdate_range(start, periods=n)
    close = np.full(n, base, dtype=float)
    return pd.DataFrame(
        {"Open": close, "High": close * 1.001, "Low": close * 0.999,
         "Close": close, "Volume": np.full(n, vol, dtype=float)},
        index=idx,
    )


def _spike_bar(df: pd.DataFrame, pos: int, vol_mult: float = 10.0,
               close_jump: float = 1.10) -> pd.DataFrame:
    """Make bar `pos` a confirmation bar: huge volume + close above prior highs."""
    df = df.copy()
    df.iloc[pos, df.columns.get_loc("Volume")] = df["Volume"].iloc[:pos].mean() * vol_mult
    new_close = float(df["High"].iloc[max(0, pos - 20):pos].max()) * close_jump
    df.iloc[pos, df.columns.get_loc("Close")] = new_close
    df.iloc[pos, df.columns.get_loc("High")] = new_close * 1.001
    return df


# ---------------------------------------------------------------------------
# Technical confirmation
# ---------------------------------------------------------------------------
def test_bar_pos_finds_last_bar_on_or_before():
    df = _flat_ohlcv(50)
    d = str(df.index[10].date())
    assert ec.bar_pos(df, d) == 10
    # a weekend / gap date resolves to the prior bar
    assert ec.bar_pos(df, "2050-01-01") == 49
    assert ec.bar_pos(df, "1990-01-01") == -1


def test_volume_surge_true_and_false():
    df = _spike_bar(_flat_ohlcv(100), 50)
    d = str(df.index[50].date())
    assert ec.volume_surge(df, d) is True
    flat = _flat_ohlcv(100)
    assert ec.volume_surge(flat, str(flat.index[50].date())) is False


def test_breakout_true_and_false():
    df = _spike_bar(_flat_ohlcv(100), 50)
    d = str(df.index[50].date())
    assert ec.breakout(df, d) is True
    flat = _flat_ohlcv(100)
    assert ec.breakout(flat, str(flat.index[50].date())) is False


def test_technical_confirm_requires_both():
    df = _spike_bar(_flat_ohlcv(100), 50)
    d = str(df.index[50].date())
    assert ec.technical_confirm(df, d) is True
    # volume surge only (no breakout): bump volume but keep close flat
    vol_only = _flat_ohlcv(100)
    vol_only.iloc[50, vol_only.columns.get_loc("Volume")] = 99999
    assert ec.technical_confirm(vol_only, str(vol_only.index[50].date())) is False


# ---------------------------------------------------------------------------
# Earnings real-YoY surprise (E1)
# ---------------------------------------------------------------------------
def _tufe(start="2021-01-01", periods=80, monthly_infl=0.03) -> pd.Series:
    idx = pd.date_range(start, periods=periods, freq="MS")
    return pd.Series(100.0 * np.cumprod(np.full(periods, 1 + monthly_infl)), index=idx, name="tufe")


def test_real_yoy_deflates_nominal():
    # net income 100 -> 250 (nominal +150%), CPI 100 -> 150 (+50%) => real ~ +66.7%
    assert ed._real_yoy(250, 100, 150, 100) == pytest.approx(2.5 / 1.5 - 1.0, rel=1e-6)
    # invalid base -> NaN
    assert not np.isfinite(ed._real_yoy(250, -10, 150, 100))


def test_detect_earnings_high_surprise_and_positive_base():
    fundamentals = pd.DataFrame([
        {"ticker": "AAA", "year": 2022, "period": "12", "net_income": 100, "revenue": 1000,
         "publication_date": "2023-03-01"},
        {"ticker": "AAA", "year": 2023, "period": "12", "net_income": 250, "revenue": 2000,
         "publication_date": "2024-03-01"},
        # BBB has a negative prior base -> excluded
        {"ticker": "BBB", "year": 2022, "period": "12", "net_income": -50, "revenue": 500,
         "publication_date": "2023-03-01"},
        {"ticker": "BBB", "year": 2023, "period": "12", "net_income": 80, "revenue": 900,
         "publication_date": "2024-03-01"},
    ])
    tufe = pd.Series([100.0, 150.0], index=pd.to_datetime(["2023-03-01", "2024-03-01"]))
    events = ed.detect_earnings_events(fundamentals, tufe, threshold=0.20)
    tickers = {e["ticker"] for e in events}
    assert "AAA" in tickers and "BBB" not in tickers
    aaa = next(e for e in events if e["ticker"] == "AAA")
    assert aaa["event_date"] == "2024-03-01"
    assert aaa["surprise_real"] == pytest.approx(2.5 / 1.5 - 1.0, rel=1e-3)


def test_detect_earnings_empty_on_missing_columns():
    assert ed.detect_earnings_events(pd.DataFrame(), None) == []
    assert ed.detect_earnings_events(pd.DataFrame({"ticker": ["X"]}), None) == []


def test_index_and_material_kap_data_pending():
    idx_events, idx_pending = ed.detect_index_inclusion()
    kap_events, kap_pending = ed.detect_material_kap()
    assert idx_events == [] and idx_pending is True
    assert kap_events == [] and kap_pending is True


# ---------------------------------------------------------------------------
# Event study -- look-ahead guard + XU100-relative
# ---------------------------------------------------------------------------
def test_forward_window_entry_t_plus_one():
    df = _flat_ohlcv(100)
    # make prices rise after the event so entry/exit are identifiable
    df.iloc[51:, df.columns.get_loc("Close")] = 110.0
    fw = es.forward_window(df, str(df.index[50].date()), horizon=5, offset=1)
    assert fw is not None
    entry_date, exit_date, gross = fw
    assert entry_date == str(df.index[51].date())   # t+1
    assert exit_date == str(df.index[56].date())    # t+1+5


def test_forward_window_none_near_series_end():
    df = _flat_ohlcv(100)
    assert es.forward_window(df, str(df.index[98].date()), horizon=5) is None


def test_relative_net_minus_cost_when_tracking_index():
    df = _flat_ohlcv(100)
    df.iloc[51:, df.columns.get_loc("Close")] = 105.0
    fw = es.forward_window(df, str(df.index[50].date()), horizon=5)
    entry_date, exit_date, gross = fw
    # index identical to the stock -> excess return ~ 0, so rel_net ~ -cost
    xu = df["Close"].copy()
    rel = es.relative_net(gross, xu, entry_date, exit_date, cost_bps=70)
    assert rel == pytest.approx(-70 / 10_000.0, abs=1e-4)


def test_build_event_returns_and_split():
    df = _spike_bar(_flat_ohlcv(120), 50)          # confirmation bar at 50
    df.iloc[51:, df.columns.get_loc("Close")] = 130.0
    flat = _flat_ohlcv(120)                          # no confirmation
    flat.iloc[51:, flat.columns.get_loc("Close")] = 130.0
    prices = {"AAA": df, "BBB": flat}
    xu = _flat_ohlcv(120)["Close"]
    ev_date = str(df.index[50].date())
    events = [
        {"ticker": "AAA", "event_date": ev_date, "event_type": "E1_earnings"},
        {"ticker": "BBB", "event_date": ev_date, "event_type": "E1_earnings"},
    ]
    enriched = es.build_event_returns(events, prices, xu, horizons=(5,))
    assert {e["ticker"]: e["technical_confirm"] for e in enriched} == {"AAA": True, "BBB": False}
    sp = es.split_confluence(enriched, 5)
    assert sp["n_confluence"] == 1 and sp["n_event_only"] == 1


# ---------------------------------------------------------------------------
# Two nulls -- determinism + beats-95 logic
# ---------------------------------------------------------------------------
def test_event_conditional_null_deterministic():
    pool = np.linspace(-0.05, 0.05, 200)
    a = en.event_conditional_null(pool, 20, 0.01, seed=42, n_resamples=300)
    b = en.event_conditional_null(pool, 20, 0.01, seed=42, n_resamples=300)
    assert a["null_mean"] == b["null_mean"] and a["random_pctile"] == b["random_pctile"]


def test_no_event_null_deterministic():
    pool = np.linspace(-0.05, 0.05, 500)
    a = en.no_event_null(pool, 20, 0.01, seed=7, n_resamples=300)
    b = en.no_event_null(pool, 20, 0.01, seed=7, n_resamples=300)
    assert a["null_mean"] == b["null_mean"] and a["p_value"] == b["p_value"]


def test_null_beats_95_when_observed_far_above_pool():
    pool = np.random.default_rng(0).normal(0.0, 0.01, 500)
    res = en.event_conditional_null(pool, 30, observed_confluence_mean=0.05,
                                    seed=1, n_resamples=500)
    assert res["beats_95"] is True and res["random_pctile"] >= 0.95


def test_null_degenerate_when_all_events_confluence():
    pool = np.linspace(-0.05, 0.05, 40)
    # n_draw == pool size -> no contrast
    res = en.event_conditional_null(pool, 40, 0.0, seed=1, n_resamples=100)
    assert res["degenerate"] is True


def test_sample_noevent_technical_returns_excludes_events():
    df = _spike_bar(_flat_ohlcv(120), 50)
    df.iloc[51:, df.columns.get_loc("Close")] = 130.0
    prices = {"AAA": df}
    xu = _flat_ohlcv(120)["Close"]
    ev_date = str(df.index[50].date())
    # with the only confirmed bar excluded as an event -> empty pool
    pool = en.sample_noevent_technical_returns(prices, xu, {("AAA", ev_date)}, horizon=5)
    assert pool.size == 0


# ---------------------------------------------------------------------------
# Holm-per-type + DEC-046 verdict
# ---------------------------------------------------------------------------
def test_holm_per_event_type_stepdown():
    res = er.holm_per_event_type({5: 0.001, 20: 0.20, 60: 0.40}, alpha=0.05)
    assert res["reject"][5] is True and res["reject"][20] is False
    assert res["any_significant"] is True


def test_holm_none_pvalues_no_significance():
    res = er.holm_per_event_type({5: None, 20: None}, alpha=0.05)
    assert res["any_significant"] is False and res["m"] == 0


def test_verdict_undetermined_small_sample():
    per_h = {5: {"null1": {"beats_95": True}, "null2": {"beats_95": True}, "confluence_mean": 0.02}}
    holm = {"reject": {5: True}}
    v = er._verdict(per_h, holm, n_confluence=3, min_events=30)
    assert v["status"] == "undetermined" and v["passes"] is False


def test_verdict_pass_and_fail():
    per_h = {5: {"null1": {"beats_95": True}, "null2": {"beats_95": True}, "confluence_mean": 0.02}}
    holm_pass = {"reject": {5: True}}
    holm_fail = {"reject": {5: False}}
    assert er._verdict(per_h, holm_pass, 40, 30)["status"] == "pass"
    assert er._verdict(per_h, holm_fail, 40, 30)["status"] == "fail"


# ---------------------------------------------------------------------------
# End-to-end (synthetic, network-free)
# ---------------------------------------------------------------------------
def test_run_event_confluence_test_structure():
    df = _spike_bar(_flat_ohlcv(120), 50)
    df.iloc[51:, df.columns.get_loc("Close")] = 130.0
    prices = {"AAA": df}
    xu = _flat_ohlcv(120)["Close"]
    ev_date = str(df.index[50].date())
    events_by_type = {"E1_earnings": [
        {"ticker": "AAA", "event_date": ev_date, "event_type": "E1_earnings"}]}
    res = er.run_event_confluence_test(events_by_type, prices, xu, horizons=(5,))
    assert res["directive"] == "D-188"
    cell = res["results"]["E1_earnings"]
    assert "per_horizon" in cell and "5" in cell["per_horizon"]
    assert cell["verdict_DEC046"]["status"] == "undetermined"  # n=1 < 30


# ---------------------------------------------------------------------------
# Forward recorder -- pre-registration guarantee + idempotent append-only
# ---------------------------------------------------------------------------
def _recorder_fixture(n: int = 120, event_pos: int = 50):
    df = _spike_bar(_flat_ohlcv(n), event_pos)
    df.iloc[event_pos + 1:, df.columns.get_loc("Close")] = 130.0
    prices = {"AAA": df}
    xu = _flat_ohlcv(n)["Close"]
    ev_date = str(df.index[event_pos].date())
    events = [{"ticker": "AAA", "event_date": ev_date, "event_type": "E1_earnings",
               "surprise_real": 0.45}]
    return prices, xu, ev_date, events, df


def test_recorder_signal_has_no_forward_at_write(tmp_path):
    """Pre-registration guarantee: the signal is recorded WITHOUT any forward outcome."""
    prices, _xu, _ev, events, _df = _recorder_fixture()
    rec = EventForwardRecorder(str(tmp_path))
    n = rec.record_events(events, prices)
    assert n == 1
    sigs = rec.load_signals()
    assert sigs.iloc[0]["signal_fired"] == True  # noqa: E712 (parquet bool)
    # no forward-return columns exist in the immutable signal record
    assert not any(c.startswith(("fwd", "rel", "gross", "return_t")) for c in sigs.columns)
    assert "as_of_timestamp" in sigs.columns


def test_recorder_idempotent(tmp_path):
    prices, _xu, _ev, events, _df = _recorder_fixture()
    rec = EventForwardRecorder(str(tmp_path))
    assert rec.record_events(events, prices) == 1
    assert rec.record_events(events, prices) == 0  # same natural_key -> no duplicate
    assert len(rec.load_signals()) == 1


def test_return_filler_fills_matured_horizon(tmp_path):
    prices, xu, _ev, events, df = _recorder_fixture()
    EventForwardRecorder(str(tmp_path)).record_events(events, prices)
    filler = EventReturnFiller(str(tmp_path))
    future = str(df.index[-1].date())   # all horizons matured by series end
    n = filler.fill(future, prices, xu, horizons=(5,))
    assert n == 1
    rdf = filler.load_returns()
    assert rdf.iloc[0]["horizon"] == 5 and rdf.iloc[0]["rel_net_return"] is not None
    # idempotent: filling again adds nothing
    assert filler.fill(future, prices, xu, horizons=(5,)) == 0


def test_return_filler_skips_unmatured_horizon(tmp_path):
    prices, xu, ev_date, events, _df = _recorder_fixture()
    EventForwardRecorder(str(tmp_path)).record_events(events, prices)
    filler = EventReturnFiller(str(tmp_path))
    # 'today' == event date -> the t+1+5 exit is in the future -> nothing matured
    assert filler.fill(ev_date, prices, xu, horizons=(5,)) == 0
    assert filler.load_returns().empty


def test_signal_immutable_after_fill(tmp_path):
    """Filling returns must not alter the signal log (append-only separation)."""
    prices, xu, _ev, events, df = _recorder_fixture()
    rec = EventForwardRecorder(str(tmp_path))
    rec.record_events(events, prices)
    before = rec.load_signals().to_dict("records")
    EventReturnFiller(str(tmp_path)).fill(str(df.index[-1].date()), prices, xu, horizons=(5,))
    after = rec.load_signals().to_dict("records")
    assert before == after


# ---------------------------------------------------------------------------
# Architecture invariant (strangler): no composite / engine / conviction imports
# ---------------------------------------------------------------------------
def test_no_composite_or_engine_imports():
    forbidden_modules = ("signals.engine", "backtest.engine", "conviction", "composite")
    forbidden_names = {"MASTER_WEIGHTS", "compute_composite_score", "compute_conviction"}
    src_dir = Path(__file__).parent.parent / "src" / "screening"
    for name in ("event_config.py", "event_detect.py", "event_confirm.py",
                 "event_study.py", "event_null.py", "event_runner.py",
                 "event_forward_recorder.py"):
        tree = ast.parse((src_dir / name).read_text(encoding="utf-8"))
        modules, used = [], set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            elif isinstance(node, ast.Import):
                modules += [a.name for a in node.names]
            elif isinstance(node, ast.Name):
                used.add(node.id)
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)
        for mod in modules:
            assert not any(t in mod for t in forbidden_modules), f"{name} imports {mod}"
        assert not (used & forbidden_names), f"{name} uses {used & forbidden_names}"
