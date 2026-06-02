"""Behavior tests for the D-203 FAZ-0 universal fundamentals freeze.

Synthetic degoran archive (modern + legacy layouts), no network. Verifies dual-layout
parsing, '.E'-suffix stripping, VY/HY -> NaN coercion, derived value signals, universe
alignment, and content-hash idempotency.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data import clean_universe_fundamentals as cf


def _write_modern_zip(path: Path, ym: str, rows: list[tuple]) -> None:
    """rows: (ticker_with_E, mktval, net_profit, equity, net_div, pe, pbv, dy)."""
    data = []
    for r in rows:
        tick, mv, npf, eq, nd, pe, pbv, dy = r
        rec = [0] * 13
        rec[1], rec[6], rec[7], rec[8], rec[9], rec[10], rec[11], rec[12] = \
            tick, mv, npf, eq, nd, pe, pbv, dy
        data.append(rec)
    df = pd.DataFrame(data)
    _zip_excel(path, f"oran{ym}.xlsx", df)


def _write_legacy_zip(path: Path, ym: str, rows: list[tuple]) -> None:
    """rows: (bare_ticker, mktval, net_profit, net_div, equity, pe, dy, pbv)."""
    data = []
    for r in rows:
        tick, mv, npf, nd, eq, pe, dy, pbv = r
        rec = [0] * 15
        rec[0], rec[3], rec[4], rec[6], rec[7], rec[10], rec[12], rec[14] = \
            tick, mv, npf, nd, eq, pe, dy, pbv
        data.append(rec)
    df = pd.DataFrame(data)
    _zip_excel(path, f"oran{ym}.xlsx", df)


def _zip_excel(zip_path: Path, inner_name: str, df: pd.DataFrame) -> None:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, header=False, index=False)
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr(inner_name, buf.getvalue())


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    fr = tmp_path / "fr"
    fr.mkdir()
    # modern layout, 2020-01: AKBNK.E + a VY net_profit row
    _write_modern_zip(fr / "degoran_M_202001.zip", "202001", [
        ("AKBNK.E", 1000.0, 100.0, 500.0, 10.0, 10.0, 2.0, 5.0),
        ("THYAO.E", 2000.0, "VY", 800.0, 0.0, "HY", 2.5, 0.0),
    ])
    # legacy layout, 2020-02: bare codes
    _write_legacy_zip(fr / "degoran_M_202002.zip", "202002", [
        ("AKBNK", 1100.0, 110.0, 12.0, 520.0, 9.0, 6.0, 2.1),
        ("GARAN", 3000.0, 300.0, 30.0, 1500.0, 8.0, 4.0, 2.0),
    ])
    return fr


def test_modern_layout_strips_e_and_parses(archive: Path):
    df = cf.load_degoran_fundamentals(archive, "2020-01", "2020-01")
    syms = set(df["symbol"])
    assert "AKBNK" in syms and "THYAO" in syms       # '.E' stripped to bare code
    assert not any("." in s for s in syms)


def test_legacy_layout_parses_bare_codes(archive: Path):
    df = cf.load_degoran_fundamentals(archive, "2020-02", "2020-02")
    assert {"AKBNK", "GARAN"} <= set(df["symbol"])


def test_vy_hy_coerced_to_nan(archive: Path):
    df = cf.load_degoran_fundamentals(archive, "2020-01", "2020-01")
    thy = df[df["symbol"] == "THYAO"].iloc[0]
    assert np.isnan(thy["net_profit"])     # 'VY' -> NaN
    assert np.isnan(thy["pe"])             # 'HY' -> NaN
    assert np.isnan(thy["ey"])             # derived from NaN net_profit


def test_derived_value_signals(archive: Path):
    df = cf.load_degoran_fundamentals(archive, "2020-01", "2020-01")
    ak = df[df["symbol"] == "AKBNK"].iloc[0]
    assert ak["ey"] == pytest.approx(100.0 / 1000.0)     # net_profit / mktval
    assert ak["bm"] == pytest.approx(500.0 / 1000.0)     # equity / mktval
    assert ak["dyld"] == pytest.approx(5.0 / 100.0)      # dy / 100


def test_freeze_alignment_and_hash_idempotent(archive: Path, tmp_path: Path):
    clean = tmp_path / "clean"
    clean.mkdir()
    # universe = 3 symbols; GARAN absent from 2020-01, present 2020-02; ZZZZ never
    px = pd.DataFrame({"symbol": ["AKBNK", "GARAN", "ZZZZ"] * 2})
    prices_pq = clean / "adjusted_prices_2019_2026.parquet"
    px.to_parquet(prices_pq, index=False)

    df, meta = cf.build_and_freeze_fundamentals(
        clean_root=clean, archive_fr_dir=archive, prices_parquet=prices_pq,
        start="2020-01", end="2020-02")
    assert set(df["symbol"]) <= {"AKBNK", "GARAN"}        # ZZZZ has no fundamentals
    assert "ZZZZ" in meta["missing_symbols"]
    assert meta["covered_n"] == 2 and meta["universe_n"] == 3

    # idempotent: re-freeze loads frozen panel; verify recomputes same hash
    assert cf.verify_frozen_fundamentals(clean) is True
    h1 = meta["content_hash_fundamentals"]
    h2 = cf.content_hash_fundamentals(df)
    assert h1 == h2
