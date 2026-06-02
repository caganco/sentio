"""Tests for D-200 clean_universe_builder. No real DataStore files needed."""
from __future__ import annotations

import io
import json
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.data.clean_universe_builder import (
    apply_back_adjustment,
    build_and_freeze_adjusted_panel,
    build_raw_price_panel,
    compute_adjustment_factors,
    compute_total_return_index,
    content_hash,
    extract_pit_membership,
    parse_3196_monthly,
    parse_corp_actions,
)
from src.signals.thresholds import (
    CLEAN_UNIVERSE_ROOT,
    CLEAN_UNIVERSE_START,
    COL_3196_EXPECTED_COUNT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_3196_csv(rows: list[dict]) -> str:
    """Build minimal 52-col semicolon CSV with 2 header rows + given data rows."""
    n = COL_3196_EXPECTED_COUNT
    tr_header = ";".join(f"TR{i}" for i in range(n))
    en_header = ";".join(f"EN{i}" for i in range(n))
    data_lines = []
    for r in rows:
        cols = [""] * n
        cols[0] = r.get("date", "2020-01-02")
        cols[1] = r.get("ticker", "TEST.E")
        cols[11] = str(r.get("bist100", 0))
        cols[12] = str(r.get("bist30", 0))
        cols[14] = r.get("ca_code", "")
        cols[22] = str(r.get("close", "10.00"))
        cols[27] = str(r.get("vwap", "10.00"))
        cols[28] = str(r.get("value_tl", "1000000"))
        cols[29] = str(r.get("volume", "100000"))
        data_lines.append(";".join(cols))
    return "\n".join([tr_header, en_header] + data_lines)


def _price_actions_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _raw_panel_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([
        {"date": r["date"], "symbol": r["symbol"], "close": r["close"],
         "vwap": r.get("vwap"), "value_tl": r.get("value_tl"),
         "volume": r.get("volume"), "bist100": r.get("bist100", 0),
         "bist30": r.get("bist30", 0), "ca_code": r.get("ca_code")}
        for r in rows
    ])


# ---------------------------------------------------------------------------
# 1. parse_3196_monthly
# ---------------------------------------------------------------------------

def test_parse_3196_minimal(tmp_path):
    csv_content = _make_3196_csv([
        {"date": "2020-01-02", "ticker": "AKBNK.E", "close": "10.50", "bist100": 1},
        {"date": "2020-01-03", "ticker": "GARAN.E", "close": "5.20", "bist30": 1},
    ])
    p = tmp_path / "PP_GUNSONUFIYATHACIM.M.202001.csv"
    p.write_text(csv_content, encoding="utf-8")

    df = parse_3196_monthly(p)
    assert len(df) == 2
    assert "AKBNK" in df["symbol"].values
    assert "GARAN" in df["symbol"].values
    assert "AKBNK.E" not in df["symbol"].values
    assert df[df["symbol"] == "AKBNK"]["bist100"].iloc[0] == 1
    assert df[df["symbol"] == "GARAN"]["bist30"].iloc[0] == 1


def test_parse_3196_ticker_suffix_stripped(tmp_path):
    csv_content = _make_3196_csv([
        {"date": "2020-03-01", "ticker": "KOZAA.E", "close": "3.52"},
        {"date": "2020-03-01", "ticker": "THYAO.F", "close": "12.00"},
    ])
    p = tmp_path / "PP_GUNSONUFIYATHACIM.M.202003.csv"
    p.write_text(csv_content, encoding="utf-8")
    df = parse_3196_monthly(p)
    assert set(df["symbol"]) == {"KOZAA", "THYAO"}


def test_parse_3196_bad_rows_discarded(tmp_path, capsys):
    csv_content = _make_3196_csv([
        {"date": "2020-01-02", "ticker": "AKBNK.E", "close": "10.50"},
        {"date": "BAD_DATE", "ticker": "GARAN.E", "close": "5.20"},
    ])
    p = tmp_path / "PP_GUNSONUFIYATHACIM.M.202001.csv"
    p.write_text(csv_content, encoding="utf-8")
    df = parse_3196_monthly(p)
    assert len(df) == 1
    assert df["symbol"].iloc[0] == "AKBNK"
    out = capsys.readouterr().out
    assert "atildi" in out or len(df) == 1


def test_parse_3196_too_few_columns_raises(tmp_path):
    bad_csv = "TR1;TR2;TR3\nEN1;EN2;EN3\n1;2;3"
    p = tmp_path / "PP_GUNSONUFIYATHACIM.M.202001.csv"
    p.write_text(bad_csv, encoding="utf-8")
    with pytest.raises(ValueError, match="sutun"):
        parse_3196_monthly(p)


# ---------------------------------------------------------------------------
# 2. compute_adjustment_factors
# ---------------------------------------------------------------------------

def test_compute_factors_bedelsiz_single():
    actions = _price_actions_df([
        {"ex_date": date(2020, 3, 15), "symbol": "KOZAA",
         "action_type": "BEDELSIZ", "ratio": 1.0, "sub_price": None},
    ])
    bp, excl = compute_adjustment_factors(actions)
    assert "KOZAA" not in excl
    kozaa_bp = bp[bp["symbol"] == "KOZAA"].sort_values("date")
    # Before ex_date: adj_factor = 0.5
    early = kozaa_bp[kozaa_bp["date"] < date(2020, 3, 15)]
    assert abs(float(early["adj_factor"].iloc[0]) - 0.5) < 1e-9
    # From ex_date: adj_factor = 1.0
    late = kozaa_bp[kozaa_bp["date"] >= date(2020, 3, 15)]
    assert abs(float(late["adj_factor"].iloc[0]) - 1.0) < 1e-9


def test_compute_factors_cumulative():
    actions = _price_actions_df([
        {"ex_date": date(2020, 1, 10), "symbol": "AAA",
         "action_type": "BEDELSIZ", "ratio": 1.0, "sub_price": None},
        {"ex_date": date(2021, 6, 15), "symbol": "AAA",
         "action_type": "BEDELSIZ", "ratio": 1.0, "sub_price": None},
    ])
    bp, excl = compute_adjustment_factors(actions)
    assert "AAA" not in excl
    aaa = bp[bp["symbol"] == "AAA"].sort_values("date").reset_index(drop=True)
    # 3 breakpoints: EPOCH (0.25), date1 (0.5), date2 (1.0)
    factors = list(aaa["adj_factor"])
    assert abs(factors[0] - 0.25) < 1e-9
    assert abs(factors[1] - 0.5) < 1e-9
    assert abs(factors[2] - 1.0) < 1e-9


def test_compute_factors_bedelli_no_subprice_excludes():
    actions = _price_actions_df([
        {"ex_date": date(2020, 5, 1), "symbol": "BBB",
         "action_type": "BEDELLI", "ratio": 0.2, "sub_price": None},
    ])
    bp, excl = compute_adjustment_factors(actions)
    assert "BBB" in excl
    assert bp[bp["symbol"] == "BBB"].empty


def test_compute_factors_bedelli_with_raw_panel():
    raw = _raw_panel_df([
        {"date": date(2020, 4, 30), "symbol": "CCC", "close": 10.0},
        {"date": date(2020, 5, 1), "symbol": "CCC", "close": 8.0},
    ])
    actions = _price_actions_df([
        {"ex_date": date(2020, 5, 1), "symbol": "CCC",
         "action_type": "BEDELLI", "ratio": 0.5, "sub_price": 2.0},
    ])
    bp, excl = compute_adjustment_factors(actions, raw)
    assert "CCC" not in excl
    ccc_bp = bp[bp["symbol"] == "CCC"].sort_values("date")
    # TERP = (1*10 + 0.5*2) / 1.5 = 11/1.5 ≈ 7.333; factor = 7.333/10 ≈ 0.7333
    early = ccc_bp[ccc_bp["date"] < date(2020, 5, 1)]
    expected_factor = (10.0 + 0.5 * 2.0) / (1.0 + 0.5) / 10.0
    assert abs(float(early["adj_factor"].iloc[0]) - expected_factor) < 1e-6


def test_compute_factors_empty_input():
    empty = pd.DataFrame(columns=["ex_date", "symbol", "action_type", "ratio", "sub_price"])
    bp, excl = compute_adjustment_factors(empty)
    assert bp.empty
    assert len(excl) == 0


# ---------------------------------------------------------------------------
# 3. apply_back_adjustment
# ---------------------------------------------------------------------------

def test_apply_adjustment_pass_through():
    raw = _raw_panel_df([
        {"date": date(2020, 1, 2), "symbol": "XXX", "close": 15.0, "vwap": 14.5},
    ])
    empty_bp = pd.DataFrame(columns=["symbol", "date", "adj_factor"])
    result = apply_back_adjustment(raw, empty_bp, excluded_symbols=set())
    assert abs(result["adjusted_close"].iloc[0] - 15.0) < 1e-9


def test_apply_adjustment_factor_applied():
    raw = _raw_panel_df([
        {"date": date(2020, 1, 1), "symbol": "YYY", "close": 20.0, "vwap": 20.0},
        {"date": date(2020, 6, 1), "symbol": "YYY", "close": 10.0, "vwap": 10.0},
    ])
    bp = pd.DataFrame([
        {"symbol": "YYY", "date": date(1900, 1, 1), "adj_factor": 0.5},
        {"symbol": "YYY", "date": date(2020, 5, 1), "adj_factor": 1.0},
    ])
    result = apply_back_adjustment(raw, bp, excluded_symbols=set())
    early = result[result["date"] == date(2020, 1, 1)]["adjusted_close"].iloc[0]
    late = result[result["date"] == date(2020, 6, 1)]["adjusted_close"].iloc[0]
    assert abs(early - 10.0) < 1e-9
    assert abs(late - 10.0) < 1e-9


def test_apply_adjustment_excluded_dropped():
    raw = _raw_panel_df([
        {"date": date(2020, 1, 2), "symbol": "DROP", "close": 5.0, "vwap": 5.0},
        {"date": date(2020, 1, 2), "symbol": "KEEP", "close": 8.0, "vwap": 8.0},
    ])
    empty_bp = pd.DataFrame(columns=["symbol", "date", "adj_factor"])
    result = apply_back_adjustment(raw, empty_bp, excluded_symbols={"DROP"})
    assert "DROP" not in result["symbol"].values
    assert "KEEP" in result["symbol"].values


# ---------------------------------------------------------------------------
# 4. compute_total_return_index
# ---------------------------------------------------------------------------

def test_total_return_no_dividend():
    adj = pd.DataFrame([
        {"date": date(2020, 1, 2), "symbol": "AAA", "adjusted_close": 10.0},
        {"date": date(2020, 1, 3), "symbol": "AAA", "adjusted_close": 11.0},
        {"date": date(2020, 1, 6), "symbol": "AAA", "adjusted_close": 10.0},
    ])
    divs = pd.DataFrame(columns=["ex_date", "symbol", "amount_per_share"])
    tr = compute_total_return_index(adj, divs)
    assert len(tr) == 3
    row0 = tr[tr["date"] == date(2020, 1, 2)].iloc[0]
    assert abs(row0["tr_index_gross"] - 1.0) < 1e-9
    row1 = tr[tr["date"] == date(2020, 1, 3)].iloc[0]
    assert abs(row1["tr_index_gross"] - 1.1) < 1e-9


def test_total_return_with_dividend():
    adj = pd.DataFrame([
        {"date": date(2020, 3, 1), "symbol": "BBB", "adjusted_close": 10.0},
        {"date": date(2020, 3, 2), "symbol": "BBB", "adjusted_close": 10.0},
    ])
    divs = pd.DataFrame([
        {"ex_date": date(2020, 3, 2), "symbol": "BBB", "amount_per_share": 1.0},
    ])
    tr = compute_total_return_index(adj, divs)
    row1 = tr[tr["date"] == date(2020, 3, 2)].iloc[0]
    # ret = (10 + 1) / 10 = 1.1
    assert abs(row1["tr_index_gross"] - 1.1) < 1e-9


def test_total_return_net_vs_gross():
    adj = pd.DataFrame([
        {"date": date(2020, 4, 1), "symbol": "CCC", "adjusted_close": 10.0},
        {"date": date(2020, 4, 2), "symbol": "CCC", "adjusted_close": 10.0},
    ])
    divs = pd.DataFrame([
        {"ex_date": date(2020, 4, 2), "symbol": "CCC", "amount_per_share": 2.0},
    ])
    tr = compute_total_return_index(adj, divs, withholding=0.15)
    row1 = tr[tr["date"] == date(2020, 4, 2)].iloc[0]
    gross = row1["tr_index_gross"]
    net = row1["tr_index_net"]
    # gross ret = (10+2)/10=1.2; net ret = (10+1.7)/10=1.17
    assert abs(gross - 1.2) < 1e-9
    assert abs(net - 1.17) < 1e-9


def test_total_return_empty_adj_panel():
    adj = pd.DataFrame(columns=["date", "symbol", "adjusted_close"])
    divs = pd.DataFrame(columns=["ex_date", "symbol", "amount_per_share"])
    tr = compute_total_return_index(adj, divs)
    assert tr.empty


# ---------------------------------------------------------------------------
# 5. content_hash
# ---------------------------------------------------------------------------

def test_content_hash_deterministic():
    df = pd.DataFrame([
        {"date": date(2020, 1, 2), "symbol": "A", "close": 10.0},
        {"date": date(2020, 1, 3), "symbol": "B", "close": 5.0},
    ])
    assert content_hash(df) == content_hash(df)


def test_content_hash_sensitive():
    df1 = pd.DataFrame([{"date": date(2020, 1, 2), "symbol": "A", "close": 10.0}])
    df2 = pd.DataFrame([{"date": date(2020, 1, 2), "symbol": "A", "close": 10.001}])
    assert content_hash(df1) != content_hash(df2)


def test_content_hash_order_independent():
    df1 = pd.DataFrame([
        {"date": date(2020, 1, 2), "symbol": "A", "close": 10.0},
        {"date": date(2020, 1, 2), "symbol": "B", "close": 5.0},
    ])
    df2 = df1.iloc[::-1].reset_index(drop=True)
    assert content_hash(df1) == content_hash(df2)


# ---------------------------------------------------------------------------
# 6. extract_pit_membership
# ---------------------------------------------------------------------------

def test_pit_membership_counts():
    rows = [
        {"date": date(2020, 1, 2), "symbol": f"S{i:03d}", "close": 10.0,
         "bist100": 1 if i < 100 else 0, "bist30": 1 if i < 30 else 0}
        for i in range(200)
    ]
    raw = _raw_panel_df(rows)
    mem = extract_pit_membership(raw)
    day = mem[mem["date"] == date(2020, 1, 2)]
    assert day["in_bist100"].sum() == 100
    assert day["in_bist30"].sum() == 30


def test_pit_membership_columns():
    raw = _raw_panel_df([
        {"date": date(2020, 1, 2), "symbol": "A", "close": 10.0, "bist100": 1, "bist30": 0},
    ])
    mem = extract_pit_membership(raw)
    assert set(mem.columns) >= {"date", "symbol", "in_bist100", "in_bist30"}
    assert bool(mem.iloc[0]["in_bist100"]) is True
    assert bool(mem.iloc[0]["in_bist30"]) is False


# ---------------------------------------------------------------------------
# 7. parse_corp_actions (synthetic zip)
# ---------------------------------------------------------------------------

def _make_corp_action_zip(tmp_path: Path, filename: str, csv_content: str) -> Path:
    zf_path = tmp_path / filename
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("data.csv", csv_content)
    zf_path.write_bytes(buf.getvalue())
    return zf_path


def test_parse_corp_actions_bedelsiz(tmp_path):
    csv = "KOD;TARIH;ORAN\nKOZAA;2020-03-15;1.0\nGARAN;2021-06-10;0.5\n"
    _make_corp_action_zip(tmp_path, "100460_2020.zip", csv)
    price_actions, dividends = parse_corp_actions(tmp_path)
    assert len(price_actions) == 2
    assert dividends.empty
    kozaa = price_actions[price_actions["symbol"] == "KOZAA"].iloc[0]
    assert kozaa["action_type"] == "BEDELSIZ"
    assert abs(float(kozaa["ratio"]) - 1.0) < 1e-9


def test_parse_corp_actions_dividends(tmp_path):
    csv = "KOD;TARIH;NET TEMETTÜ\nAKBNK;2021-04-05;0.50\nTHYAO;2021-05-10;0.30\n"
    _make_corp_action_zip(tmp_path, "100471_2021.zip", csv)
    price_actions, dividends = parse_corp_actions(tmp_path)
    assert price_actions.empty
    assert len(dividends) == 2
    akbnk = dividends[dividends["symbol"] == "AKBNK"].iloc[0]
    assert abs(float(akbnk["amount_per_share"]) - 0.50) < 1e-9


def test_parse_corp_actions_missing_dir():
    with pytest.raises(RuntimeError, match="bulunamadi"):
        parse_corp_actions(Path("/nonexistent/ca_dir"))


def test_parse_corp_actions_empty_dir(tmp_path):
    with pytest.raises(RuntimeError, match="zip"):
        parse_corp_actions(tmp_path)


# ---------------------------------------------------------------------------
# 8. build_and_freeze_adjusted_panel — idempotency + meta schema
# ---------------------------------------------------------------------------

def _make_prices_dir(tmp_path: Path) -> tuple[Path, Path, Path]:
    prices_dir = tmp_path / "prices_official"
    prices_dir.mkdir()
    ca_dir = tmp_path / "corporate_actions"
    ca_dir.mkdir()
    output_dir = tmp_path / "clean_universe"

    csv = _make_3196_csv([
        {"date": "2019-01-02", "ticker": "KOZAA.E", "close": "3.52",
         "bist100": 1, "bist30": 0},
        {"date": "2019-01-03", "ticker": "AKBNK.E", "close": "10.50",
         "bist100": 1, "bist30": 1},
        {"date": "2019-01-02", "ticker": "IPEKE.E", "close": "1.20",
         "bist100": 0, "bist30": 0},
    ])
    f = prices_dir / "PP_GUNSONUFIYATHACIM.M.201901.csv"
    f.write_text(csv, encoding="utf-8")

    ca_csv = "KOD;TARIH;ORAN\nAKBNK;2019-01-10;0.5\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("data.csv", ca_csv)
    (ca_dir / "100460_2019.zip").write_bytes(buf.getvalue())

    return prices_dir, ca_dir, output_dir


def test_build_panel_creates_meta(tmp_path):
    prices_dir, ca_dir, output_dir = _make_prices_dir(tmp_path)
    panel, meta = build_and_freeze_adjusted_panel(
        prices_dir=prices_dir,
        ca_dir=ca_dir,
        output_root=output_dir,
        start_date=date(2019, 1, 1),
        end_date=date(2019, 12, 31),
    )
    assert not panel.empty
    assert "schema_version" in meta
    assert meta["directive"] == "D-200"
    assert "content_hash_prices" in meta
    assert "content_hash_membership" in meta
    assert (output_dir / "adjusted_prices_2019_2026.parquet").exists()
    assert (output_dir / "_meta.json").exists()


def test_build_panel_idempotent(tmp_path, capsys):
    prices_dir, ca_dir, output_dir = _make_prices_dir(tmp_path)
    panel1, meta1 = build_and_freeze_adjusted_panel(
        prices_dir=prices_dir, ca_dir=ca_dir, output_root=output_dir,
        start_date=date(2019, 1, 1), end_date=date(2019, 12, 31),
    )
    capsys.readouterr()
    panel2, meta2 = build_and_freeze_adjusted_panel(
        prices_dir=prices_dir, ca_dir=ca_dir, output_root=output_dir,
        start_date=date(2019, 1, 1), end_date=date(2019, 12, 31),
    )
    out = capsys.readouterr().out
    assert "yeniden kurma yok" in out
    assert meta1["content_hash_prices"] == meta2["content_hash_prices"]


def test_build_panel_force_rebuild(tmp_path, capsys):
    prices_dir, ca_dir, output_dir = _make_prices_dir(tmp_path)
    build_and_freeze_adjusted_panel(
        prices_dir=prices_dir, ca_dir=ca_dir, output_root=output_dir,
        start_date=date(2019, 1, 1), end_date=date(2019, 12, 31),
    )
    capsys.readouterr()
    build_and_freeze_adjusted_panel(
        prices_dir=prices_dir, ca_dir=ca_dir, output_root=output_dir,
        start_date=date(2019, 1, 1), end_date=date(2019, 12, 31),
        force_rebuild=True,
    )
    out = capsys.readouterr().out
    assert "yeniden kurma yok" not in out


def test_build_panel_survivorship_present(tmp_path, capsys):
    prices_dir, ca_dir, output_dir = _make_prices_dir(tmp_path)
    build_and_freeze_adjusted_panel(
        prices_dir=prices_dir, ca_dir=ca_dir, output_root=output_dir,
        start_date=date(2019, 1, 1), end_date=date(2019, 12, 31),
    )
    out = capsys.readouterr().out
    assert "KOZAA" in out and "D185-OK" in out
    assert "IPEKE" in out and "D185-OK" in out


def test_build_panel_meta_ascii(tmp_path):
    prices_dir, ca_dir, output_dir = _make_prices_dir(tmp_path)
    _, meta = build_and_freeze_adjusted_panel(
        prices_dir=prices_dir, ca_dir=ca_dir, output_root=output_dir,
        start_date=date(2019, 1, 1), end_date=date(2019, 12, 31),
    )
    meta_text = (output_dir / "_meta.json").read_text(encoding="utf-8")
    meta_text.encode("ascii")


def test_build_panel_excluded_in_meta(tmp_path):
    prices_dir, ca_dir, output_dir = _make_prices_dir(tmp_path)
    excl_csv = "KOD;TARIH;ORAN\nKOZAA;2019-02-01;0.5\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("data.csv", excl_csv)
    (ca_dir / "100461_2019.zip").write_bytes(buf.getvalue())
    _, meta = build_and_freeze_adjusted_panel(
        prices_dir=prices_dir, ca_dir=ca_dir, output_root=output_dir,
        start_date=date(2019, 1, 1), end_date=date(2019, 12, 31),
        force_rebuild=True,
    )
    assert "excluded_symbols_count" in meta
    assert "excluded_symbols" in meta


# ---------------------------------------------------------------------------
# 9. thresholds constants
# ---------------------------------------------------------------------------

def test_thresholds_clean_universe_constants():
    from src.signals.thresholds import (
        CLEAN_UNIVERSE_ROOT,
        CLEAN_UNIVERSE_START,
        CLEAN_UNIVERSE_END,
        CLEAN_UNIVERSE_CORP_ACTION_TYPES,
        CLEAN_UNIVERSE_PRICE_TYPE,
        CLEAN_UNIVERSE_DIVIDEND_WITHHOLDING,
        COL_3196_EXPECTED_COUNT,
    )
    assert isinstance(CLEAN_UNIVERSE_ROOT, str)
    assert date.fromisoformat(CLEAN_UNIVERSE_START)
    assert date.fromisoformat(CLEAN_UNIVERSE_END)
    assert isinstance(CLEAN_UNIVERSE_CORP_ACTION_TYPES, tuple)
    assert CLEAN_UNIVERSE_PRICE_TYPE == 3196
    assert 0 < CLEAN_UNIVERSE_DIVIDEND_WITHHOLDING < 1
    assert COL_3196_EXPECTED_COUNT == 52
