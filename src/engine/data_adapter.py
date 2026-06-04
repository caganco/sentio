"""Data adapter (Section 9, recon S1): load the clean_universe + snapshots
parquet layer into a typed ``Panel``.

This generalizes clib's ``load_panels``: it additionally surfaces the
total-return indices (``tr_index_gross`` / ``tr_index_net``) and PIT membership
flags, which the math-spec (Section 3.5 / 8) requires for forward returns and
survivorship. All I/O is lazy (inside functions) so the import graph builds on
data-less CI; ``data_root`` is injectable so synthetic panels can be tested.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config
from .contracts import Frequency, Panel

_MEMBERSHIP_COLS = ("bist100", "bist30")


def _pivot(df: pd.DataFrame, value: str) -> pd.DataFrame:
    return df.pivot(index="date", columns="symbol", values=value).sort_index()


def _load_series(snapshots_dir: Path, name: str) -> pd.Series:
    """Load a long-form snapshot series (columns: date, value) as a sorted Series."""
    df = pd.read_parquet(snapshots_dir / f"{name}.parquet")
    s = pd.Series(df["value"].to_numpy(dtype=float), index=pd.to_datetime(df["date"]))
    return s.sort_index()


def load_panel(
    data_root: str | Path | None = None,
    *,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
    frequency: Frequency = Frequency.DAILY,
) -> Panel:
    """Load the price panel + macro/index snapshots into a ``Panel``.

    ``data_root`` defaults to the repo root; pass a temp dir (containing
    ``data/clean_universe`` and ``data/snapshots``) to load a synthetic panel.
    """
    root = Path(data_root) if data_root is not None else config.REPO_ROOT
    cu = root / "data" / "clean_universe"
    snap = root / "data" / "snapshots"

    px = pd.read_parquet(cu / config.PRICES_FILENAME)
    px["date"] = pd.to_datetime(px["date"])

    close = _pivot(px, "adjusted_close")
    tr_gross = _pivot(px, "tr_index_gross")
    tr_net = _pivot(px, "tr_index_net")
    value_tl = _pivot(px, "value_tl")
    membership = {m: _pivot(px, m) for m in _MEMBERSHIP_COLS if m in px.columns}

    market = _load_series(snap, config.MARKET_SERIES)
    tufe = _load_series(snap, config.TUFE_SERIES)
    tlref = _load_series(snap, config.TLREF_SERIES)

    s = pd.Timestamp(start if start is not None else config.PANEL_START)
    e = pd.Timestamp(end if end is not None else config.PANEL_END)
    win = (close.index >= s) & (close.index <= e)
    close, tr_gross, tr_net, value_tl = (
        close.loc[win],
        tr_gross.loc[win],
        tr_net.loc[win],
        value_tl.loc[win],
    )
    membership = {k: v.loc[v.index.isin(close.index)] for k, v in membership.items()}

    return Panel(
        close=close,
        tr_gross=tr_gross,
        tr_net=tr_net,
        value_tl=value_tl,
        membership=membership,
        market=market,
        tufe=tufe,
        tlref=tlref,
        frequency=frequency,
    )


def liquid_names(
    panel: Panel,
    asof: pd.Timestamp,
    *,
    min_tl: float | None = None,
    trailing: int | None = None,
) -> set[str]:
    """Names whose trailing median traded value clears the liquidity floor (recon B7)."""
    floor = config.LIQUID_ADV_MIN_TL if min_tl is None else min_tl
    days = config.LIQUID_TRAILING_DAYS if trailing is None else trailing
    window = panel.value_tl.loc[panel.value_tl.index <= asof].tail(days)
    med = window.median(skipna=True)
    return set(med[med >= floor].index)


def continuous_basket(
    panel: Panel,
    d0: pd.Timestamp,
    d1: pd.Timestamp,
    names: list[str] | None = None,
    *,
    min_cov: float = 1.0,
) -> list[str]:
    """Names present (non-NaN close) for >= ``min_cov`` of [d0, d1].

    Survivorship-honest: delisted names are kept for the window they actually
    traded, so a basket built here does not silently drop in-sample casualties.
    """
    sub = panel.close.loc[(panel.close.index >= d0) & (panel.close.index <= d1)]
    cols = list(sub.columns) if names is None else [c for c in names if c in sub.columns]
    if sub.empty or not cols:
        return []
    cov = sub[cols].notna().mean()
    return sorted(cov[cov >= min_cov].index)


def forward_return(
    panel: Panel,
    h: int,
    *,
    basis: str = config.FORWARD_RETURN_BASIS,
) -> pd.DataFrame:
    """Knowable-lag forward total return r_{t -> t+h} from the tr_index (Section 3.5).

    Uses the total-return index (dividends reinvested) to avoid the price-only
    bias that bit D-211/213. Returns are NaN in the last ``h`` rows (no future).
    """
    tr = panel.tr_gross if basis == "tr_index_gross" else panel.tr_net
    return tr.shift(-h) / tr - 1.0
