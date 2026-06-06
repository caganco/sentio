"""D-192 K3 Illiquidity + Short-Term Reversal backtest (OLCUM ONLY).

Hipotezler:
  H1: Amihud-illikit hisseler net (agresif-slippage) TL-reel bazda likit +
      adil-null'i gecer VE bu price-impact'ten (Lou-Shu ayrimi).
  H2: Kisa-vade kaybedenler net bazda kazananlar + adil-null'i gecer VE
      2020-sonrasi hala var (decay yok).

Literatur: Amihud (2002), Lou & Shu (2016),
           Jegadeesh (1990), Bildik-Gulay (2007), Celik-Ulku (2017).

Reuse:
  - block_bootstrap_ci: factor_ic_harness.py
  - Real-deflation pattern: exposure_backtest.py:222-229
  - XU100-relative pattern: trend_d186.py:41-52

DOKUNULMAZ: src/signals/, thresholds.py, calculator.py, engine.py.
"""
from __future__ import annotations

import logging
import math
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from src.screening import k3_config as cfg
from src.screening.factor_ic_harness import block_bootstrap_ci

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Evren yonetimi + veri-kalite filtresi
# ---------------------------------------------------------------------------

def apply_quality_filter(
    prices: dict[str, pd.DataFrame],
    start: str,
    end: str,
) -> tuple[dict[str, pd.DataFrame], dict]:
    """Kuralli-veri-kalite-filtresi: %80 islem-gunu, <%10 sifir-hacim, >=252 gun.

    Elle-secim YASAK. Filtre OBJEKTiF esik uygular (maintainer Other-karari).
    Returns: (filtered_prices, quality_report).
    """
    s = pd.Timestamp(start)
    e = pd.Timestamp(end)
    total_days = len(pd.bdate_range(s, e))

    passed: dict[str, pd.DataFrame] = {}
    rejected: dict[str, str] = {}

    for ticker, df in prices.items():
        if df is None or df.empty:
            rejected[ticker] = "empty_dataframe"
            continue

        # Zaman penceresine kırp
        mask = (df.index >= s) & (df.index <= e)
        sub = df.loc[mask]

        # Minimum tarih koşulu
        if len(sub) < cfg.UNIVERSE_MIN_HISTORY_DAYS:
            rejected[ticker] = f"too_short:{len(sub)}"
            continue

        # %80 islem-gunu (Close NaN degil)
        close_ok = sub["Close"].notna().sum()
        if total_days > 0 and (close_ok / total_days) < cfg.UNIVERSE_MIN_TRADING_DAYS_PCT:
            rejected[ticker] = (
                f"low_coverage:{close_ok/total_days:.2f}"
            )
            continue

        # <%10 sifir-hacim
        vol = sub["Volume"].fillna(0)
        zero_pct = (vol == 0).mean()
        if zero_pct >= cfg.UNIVERSE_MAX_ZERO_VOL_PCT:
            rejected[ticker] = f"high_zero_vol:{zero_pct:.2f}"
            continue

        passed[ticker] = sub

    report = {
        "n_input": len(prices),
        "n_passed": len(passed),
        "n_rejected": len(rejected),
        "pass_pct": round(len(passed) / max(len(prices), 1), 3),
        "rejection_reasons": {
            r: sum(1 for v in rejected.values() if v.startswith(r))
            for r in ["empty_dataframe", "too_short", "low_coverage", "high_zero_vol"]
        },
        "is_viable": len(passed) >= cfg.UNIVERSE_MIN_STOCKS_VIABLE,
    }
    logger.info(
        "Quality filter: %d/%d passed (viable=%s)",
        len(passed), len(prices), report["is_viable"],
    )
    return passed, report


# ---------------------------------------------------------------------------
# Amihud ILLIQ
# ---------------------------------------------------------------------------

def compute_amihud_illiq(
    prices: dict[str, pd.DataFrame],
    window: int = cfg.ILLIQ_WINDOW_DAYS,
    min_obs: int = cfg.ILLIQ_MIN_OBS,
    eps: float = cfg.ILLIQ_EPSILON,
    lag_months: int = cfg.ILLIQ_LAG_MONTHS,
) -> pd.DataFrame:
    """Amihud (2002) ILLIQ = rolling_mean(|ret| / (vol * close)); log-donusum.

    Returns (date x ticker) panel, log(ILLIQ). NaN = yetersiz veri.
    look-ahead guard: lag_months uygulanir (t-2 ay olcum -> t ay getiri).
    """
    panels: dict[str, pd.Series] = {}
    for ticker, df in prices.items():
        try:
            close = df["Close"].astype(float)
            volume = df["Volume"].astype(float)

            # Gunluk getiri (log)
            ret = np.log(close / close.shift(1)).abs()
            # TL ciro = volume * close
            ciro = volume * close
            # Amihud gunluk: |ret| / ciro (sifir ciro -> NaN)
            illiq_daily = ret / ciro.replace(0, np.nan)
            # Rolling ortalama
            illiq_roll = illiq_daily.rolling(window, min_periods=min_obs).mean()
            # Log donusum
            panels[ticker] = np.log(illiq_roll + eps)
        except Exception:
            logger.debug("Amihud compute error for %s", ticker)
            continue

    if not panels:
        return pd.DataFrame()

    panel = pd.DataFrame(panels)

    # Look-ahead guard: lag_months ay ileriye kaydır (t-lag -> t getiri)
    # Offset yaklaşık (21 * lag_months işlem günü)
    lag_days = 21 * lag_months
    panel = panel.shift(lag_days)

    return panel


# ---------------------------------------------------------------------------
# Lou-Shu turnover proxy
# ---------------------------------------------------------------------------

def compute_turnover_proxy(prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Turnover proxy: log(Volume * Close).

    Lou-Shu (2016): Amihud = price-impact x turnover. Turnover ayri faktör.
    Shares-outstanding yok yfinance BIST -> bu en iyi proxy. Raporda caveat.
    """
    panels: dict[str, pd.Series] = {}
    for ticker, df in prices.items():
        try:
            close = df["Close"].astype(float)
            volume = df["Volume"].astype(float)
            ciro = (volume * close).replace(0, np.nan)
            panels[ticker] = np.log(ciro)
        except Exception:
            logger.debug("Turnover proxy error for %s", ticker)
            continue

    return pd.DataFrame(panels) if panels else pd.DataFrame()


# ---------------------------------------------------------------------------
# Lou-Shu testi: cross-sectional OLS kontrol
# ---------------------------------------------------------------------------

def lou_shu_test(
    illiq_panel: pd.DataFrame,
    turnover_panel: pd.DataFrame,
    fwd_ret_panel: pd.DataFrame,
    min_xsection: int = 10,
) -> dict:
    """Her gun cross-sectional OLS: fwd_ret = a + b*illiq + c*turnover + e.

    H1 guclu: b t-stat > LOU_SHU_TSTAT_MIN turnover kontrol sonrasinda.
    H1 zayif: b sifira dusuyor -> prime turnover/volume bileseni.

    Returns: {n_days, mean_b_coef, b_tstat, mean_c_coef, verdict}.
    """
    b_list: list[float] = []
    c_list: list[float] = []
    common_dates = illiq_panel.index.intersection(
        turnover_panel.index.intersection(fwd_ret_panel.index)
    )

    for date in common_dates:
        try:
            illiq_row = illiq_panel.loc[date].dropna()
            turn_row = turnover_panel.loc[date].dropna()
            fwd_row = fwd_ret_panel.loc[date].dropna()
            common = illiq_row.index.intersection(
                turn_row.index.intersection(fwd_row.index)
            )
            if len(common) < min_xsection:
                continue
            y = fwd_row[common].to_numpy(float)
            X = np.column_stack([
                np.ones(len(common)),
                illiq_row[common].to_numpy(float),
                turn_row[common].to_numpy(float),
            ])
            # OLS: lstsq
            coef, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            b_list.append(float(coef[1]))
            c_list.append(float(coef[2]))
        except Exception:
            continue

    if not b_list:
        return {
            "n_days": 0, "mean_b_coef": float("nan"), "b_tstat": float("nan"),
            "mean_c_coef": float("nan"), "verdict": "insufficient_data",
        }

    b_arr = np.array(b_list)
    mean_b = float(np.mean(b_arr))
    std_b = float(np.std(b_arr, ddof=1)) if len(b_arr) > 1 else float("nan")
    b_tstat = (
        mean_b / (std_b / math.sqrt(len(b_arr)))
        if (std_b > 0 and len(b_arr) > 1) else float("nan")
    )
    passes = (
        not math.isnan(b_tstat) and abs(b_tstat) > cfg.LOU_SHU_TSTAT_MIN
    )
    return {
        "n_days": len(b_list),
        "mean_b_coef": round(mean_b, 6),
        "b_tstat": round(b_tstat, 4) if not math.isnan(b_tstat) else float("nan"),
        "mean_c_coef": round(float(np.mean(c_list)), 6),
        "verdict": "price_impact" if passes else "volume_driven",
        "passes_lou_shu": passes,
    }


# ---------------------------------------------------------------------------
# Short-term reversal
# ---------------------------------------------------------------------------

def compute_reversal(
    prices: dict[str, pd.DataFrame],
    lookback: int,
    skip: int = cfg.REV_SKIP_DAYS,
) -> pd.DataFrame:
    """Reversal = (-1) * past_{lookback}-day return.

    Contrarian: kaybeden hisse yuksek skor alir.
    look-ahead guard: sinyal t, aksiyon t+skip'den.
    """
    panels: dict[str, pd.Series] = {}
    for ticker, df in prices.items():
        try:
            close = df["Close"].astype(float)
            # past return: close[t-skip] / close[t-skip-lookback] - 1
            past_ret = close.shift(skip) / close.shift(skip + lookback) - 1.0
            # Reversal = negatif past return (kaybedenler pozitif skor)
            panels[ticker] = -past_ret
        except Exception:
            logger.debug("Reversal compute error for %s", ticker)
            continue

    return pd.DataFrame(panels) if panels else pd.DataFrame()


# ---------------------------------------------------------------------------
# Forward return panel
# ---------------------------------------------------------------------------

def compute_forward_returns(
    prices: dict[str, pd.DataFrame],
    horizon: int,
) -> pd.DataFrame:
    """close[t+horizon] / close[t] - 1 (her gün, her hisse)."""
    panels: dict[str, pd.Series] = {}
    for ticker, df in prices.items():
        try:
            close = df["Close"].astype(float)
            panels[ticker] = close.shift(-horizon) / close - 1.0
        except Exception:
            continue
    return pd.DataFrame(panels) if panels else pd.DataFrame()


# ---------------------------------------------------------------------------
# Portfoy olusturma + getiri
# ---------------------------------------------------------------------------

def build_portfolio_returns(
    factor: pd.DataFrame,
    prices: dict[str, pd.DataFrame],
    rebalance_days: int,
    cost_bps_rt: int,
    top_pct: float = 1.0 / 3.0,   # tercile=1/3, quintile=1/5
    long_high: bool = True,        # high factor = long; False = low factor = long
) -> pd.Series:
    """Equal-weight portfoy (long-high minus long-low) gunluk getiri serisi.

    cost_bps_rt / 10000 ödenir her rebalance'da (round-trip, iki yöne).
    long-short spread: invariant #4 (equal-weight, composite-optimize YASAK).
    """
    if factor.empty:
        return pd.Series(dtype=float)

    # Tum hisseler icin close paneli
    close_dict: dict[str, pd.Series] = {}
    for ticker, df in prices.items():
        if ticker in factor.columns:
            close_dict[ticker] = df["Close"].astype(float)
    if not close_dict:
        return pd.Series(dtype=float)

    close = pd.DataFrame(close_dict).sort_index()
    factor_aligned = factor.reindex(close.index)[list(close_dict.keys())]

    cost_frac = cost_bps_rt / 10_000.0
    returns_list: list[tuple] = []

    dates = close.index
    rebal_dates = dates[::rebalance_days]

    for i, rebal_date in enumerate(rebal_dates[:-1]):
        next_rebal = rebal_dates[i + 1]
        factor_row = factor_aligned.loc[rebal_date].dropna()
        if len(factor_row) < 4:   # en az 4 hisse gerekli
            continue

        n = len(factor_row)
        n_select = max(1, round(n * top_pct))
        sorted_f = factor_row.sort_values()

        # Long: high (veya low) factor hisseler
        long_tickers = (
            sorted_f.index[-n_select:] if long_high else sorted_f.index[:n_select]
        )
        # Short (karsilastirma): ters taraf
        short_tickers = (
            sorted_f.index[:n_select] if long_high else sorted_f.index[-n_select:]
        )

        # Rebalance donemi (rebal_date -> next_rebal)
        period_idx = (dates >= rebal_date) & (dates < next_rebal)
        period_close = close.loc[period_idx]
        if len(period_close) < 2:
            continue

        def _port_return(tickers) -> float:
            sub = period_close[
                [t for t in tickers if t in period_close.columns]
            ].dropna(how="all", axis=0)
            if sub.empty or len(sub) < 2:
                return float("nan")
            period_rets = (sub.iloc[-1] / sub.iloc[0] - 1.0).dropna()
            if period_rets.empty:
                return float("nan")
            # Equal-weight; cost çıkar
            return float(period_rets.mean()) - cost_frac

        long_ret = _port_return(long_tickers)
        short_ret = _port_return(short_tickers)

        if not math.isfinite(long_ret) or not math.isfinite(short_ret):
            continue

        spread_ret = long_ret - short_ret
        # Gün başına getiri dönüştür (zincirlenmiş seri için)
        n_days = period_idx.sum()
        if n_days > 0:
            daily_spread = (1.0 + spread_ret) ** (1.0 / n_days) - 1.0
        else:
            continue

        for d in dates[period_idx]:
            returns_list.append((d, daily_spread))

    if not returns_list:
        return pd.Series(dtype=float)

    result = (
        pd.Series(dict(returns_list))
        .sort_index()
        .groupby(level=0)
        .first()
    )
    result.name = "spread_daily"
    return result


# ---------------------------------------------------------------------------
# Fair random null (adil-null)
# ---------------------------------------------------------------------------

def fair_random_null(
    prices: dict[str, pd.DataFrame],
    strategy_ann_real: float,
    n_stocks: int,
    rebalance_days: int,
    cost_bps_rt: int,
    tufe: pd.Series,
    start: str,
    end: str,
    seed: int = cfg.NULL_SEED,
    n_resamples: int = cfg.NULL_N_RESAMPLES,
) -> dict:
    """Rastgele esit-agirlikli long portföy (ayni n_stocks, ayni maliyet).

    Adil-null: strateji tarama-zamanlamasini mi yoksa rassal'i mi seciyor?
    Pattern: trend_d186.py::fair_random_null() yapisi.
    """
    rng = np.random.default_rng(seed)
    tickers = sorted(prices.keys())
    if len(tickers) < n_stocks:
        return {
            "null_mean_ann_real": float("nan"),
            "null_p95_ann_real": float("nan"),
            "strategy_pctile": float("nan"),
            "beats_95": False,
            "n_resamples": 0,
        }

    null_ann_reals: list[float] = []
    for _ in range(n_resamples):
        chosen = rng.choice(tickers, size=n_stocks, replace=False).tolist()
        sub_prices = {t: prices[t] for t in chosen}
        # Basit equal-weight buy-and-hold (tum pencerenin getirisi)
        cum_rets: list[float] = []
        cost = cost_bps_rt / 10_000.0
        for t, df in sub_prices.items():
            try:
                close = df["Close"].astype(float)
                s_s = close.loc[close.index >= start]
                s_e = s_s.loc[s_s.index <= end].dropna()
                if len(s_e) < 2:
                    continue
                n_rebal = max(1, len(s_e) // rebalance_days)
                gross = float(s_e.iloc[-1] / s_e.iloc[0] - 1.0)
                net = gross - n_rebal * cost
                cum_rets.append(net)
            except Exception:
                continue
        if not cum_rets:
            continue
        total_nom = float(np.mean(cum_rets))
        # Real deflation
        ann_real = _to_ann_real(total_nom, tufe, start, end)
        if math.isfinite(ann_real):
            null_ann_reals.append(ann_real)

    if len(null_ann_reals) < 10:
        return {
            "null_mean_ann_real": float("nan"),
            "null_p95_ann_real": float("nan"),
            "strategy_pctile": float("nan"),
            "beats_95": False,
            "n_resamples": len(null_ann_reals),
        }

    null_arr = np.array(null_ann_reals)
    null_p95 = float(np.percentile(null_arr, 95))
    null_mean = float(np.mean(null_arr))

    if not math.isfinite(strategy_ann_real):
        pctile = float("nan")
        beats = False
    else:
        pctile = float(np.mean(null_arr <= strategy_ann_real))
        beats = pctile >= cfg.NULL_PCTILE_THRESHOLD

    return {
        "null_mean_ann_real": round(null_mean, 4),
        "null_p95_ann_real": round(null_p95, 4),
        "strategy_pctile": round(pctile, 3) if not math.isnan(pctile) else float("nan"),
        "beats_95": beats,
        "n_resamples": len(null_ann_reals),
    }


# ---------------------------------------------------------------------------
# Real return yardimcilari
# ---------------------------------------------------------------------------

def _to_ann_real(
    total_nom: float,
    tufe: pd.Series,
    start: str,
    end: str,
) -> float:
    """total_nom -> annualized TL-reel.

    Pattern: exposure_backtest.py:222-229.
    """
    try:
        t_start = pd.Timestamp(start)
        t_end = pd.Timestamp(end)
        years = (t_end - t_start).days / 365.25
        if years <= 0:
            return float("nan")
        tl_s = tufe.reindex(
            pd.date_range(t_start, t_end, freq="D"), method="ffill"
        )
        v0 = tl_s.dropna().iloc[0] if not tl_s.dropna().empty else float("nan")
        v1 = tl_s.dropna().iloc[-1] if not tl_s.dropna().empty else float("nan")
        if not (math.isfinite(v0) and math.isfinite(v1) and v0 > 0):
            return float("nan")
        tufe_ratio = v1 / v0
        total_real = (1.0 + total_nom) / tufe_ratio - 1.0
        ann_real = (1.0 + total_real) ** (1.0 / years) - 1.0
        return float(ann_real)
    except Exception:
        return float("nan")


def portfolio_to_ann_real(
    port_series: pd.Series,
    tufe: pd.Series,
) -> float:
    """Portfoy gunluk getiri serisi -> annualized TL-reel donusum."""
    if port_series.empty:
        return float("nan")
    try:
        equity = (1.0 + port_series.fillna(0)).cumprod()
        total_nom = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
        start = str(port_series.index[0].date())
        end = str(port_series.index[-1].date())
        return _to_ann_real(total_nom, tufe, start, end)
    except Exception:
        return float("nan")


def xu100_relative_ann(
    port_series: pd.Series,
    xu100: pd.Series,
) -> float:
    """Portfoy annualized XU100-relative return.

    Pattern: trend_d186.py:41-52 (geometric excess).
    """
    try:
        if port_series.empty:
            return float("nan")
        start = port_series.index[0]
        end = port_series.index[-1]
        years = (end - start).days / 365.25
        if years <= 0:
            return float("nan")
        xu_s = xu100.reindex(
            pd.date_range(start, end, freq="D"), method="ffill"
        ).dropna()
        if len(xu_s) < 2:
            return float("nan")
        xu_total = float(xu_s.iloc[-1] / xu_s.iloc[0] - 1.0)
        equity = (1.0 + port_series.fillna(0)).cumprod()
        port_total = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
        rel_total = (1.0 + port_total) / (1.0 + xu_total) - 1.0
        ann_rel = (1.0 + rel_total) ** (1.0 / years) - 1.0
        return float(ann_rel)
    except Exception:
        return float("nan")


# ---------------------------------------------------------------------------
# Decay testi
# ---------------------------------------------------------------------------

def decay_test(
    port_series: pd.Series,
    tufe: pd.Series,
    split_date: str = cfg.DECAY_SPLIT,
) -> dict:
    """Tam-donem vs split_date-sonrasi: H2 reversal hala var mi?

    Bildik-Gulay 1991-2000 eski. split_date-sonrasi AYRI olculmeli.
    """
    if port_series.empty:
        return {
            "full_ann_real": float("nan"),
            "pre_split_ann_real": float("nan"),
            "post_split_ann_real": float("nan"),
            "decay_present": True,
        }

    split = pd.Timestamp(split_date)
    pre = port_series[port_series.index < split]
    post = port_series[port_series.index >= split]

    full_ann = portfolio_to_ann_real(port_series, tufe)
    pre_ann = portfolio_to_ann_real(pre, tufe) if not pre.empty else float("nan")
    post_ann = portfolio_to_ann_real(post, tufe) if not post.empty else float("nan")

    decay = not (math.isfinite(post_ann) and post_ann > 0)
    return {
        "full_ann_real": round(full_ann, 4) if math.isfinite(full_ann) else float("nan"),
        "pre_split_ann_real": round(pre_ann, 4) if math.isfinite(pre_ann) else float("nan"),
        "post_split_ann_real": round(post_ann, 4) if math.isfinite(post_ann) else float("nan"),
        "split_date": split_date,
        "decay_present": decay,
    }


# ---------------------------------------------------------------------------
# Bootstrap t-stat yardimcisi
# ---------------------------------------------------------------------------

def _port_tstat(port_series: pd.Series) -> float:
    """Gunluk getiri serisi -> t-stat (block-bootstrap ile anlamlilik)."""
    arr = port_series.dropna().to_numpy(float)
    if len(arr) < 10:
        return float("nan")
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    if std == 0:
        return float("nan")
    return mean / (std / math.sqrt(len(arr)))


def _port_ci(port_series: pd.Series) -> tuple[float, float]:
    """Block-bootstrap 95% CI (factor_ic_harness.block_bootstrap_ci reuse)."""
    arr = port_series.dropna().to_numpy(float)
    return block_bootstrap_ci(
        arr,
        block=cfg.NULL_BOOTSTRAP_BLOCK,
        n_boot=cfg.NULL_BOOTSTRAP_N,
        seed=cfg.NULL_SEED,
    )


# ---------------------------------------------------------------------------
# H1 + H2 karar kurali
# ---------------------------------------------------------------------------

def evaluate_h1(
    t1_t3_ann_real: float,
    t1_t3_in_sample: float,
    t1_t3_out_sample: float,
    null_result: dict,
    lou_shu_result: dict,
) -> dict:
    """H1 illikidite -- dort kosul AND gerekli.

    (1) net TL-reel > 0 annualized
    (2) fair-null >= 0.95 pctile
    (3) Lou-Shu: b t-stat > 1.96 (turnover kontrol sonrasi)
    (4) in-sample > 0 AND out-of-sample > 0
    """
    c1 = math.isfinite(t1_t3_ann_real) and t1_t3_ann_real > 0
    c2 = bool(null_result.get("beats_95", False))
    c3 = bool(lou_shu_result.get("passes_lou_shu", False))
    c4 = (
        math.isfinite(t1_t3_in_sample) and t1_t3_in_sample > 0
        and math.isfinite(t1_t3_out_sample) and t1_t3_out_sample > 0
    )
    verdict = "PASS" if (c1 and c2 and c3 and c4) else "FAIL"
    return {
        "verdict": verdict,
        "ann_real": round(t1_t3_ann_real, 4) if math.isfinite(t1_t3_ann_real) else float("nan"),
        "in_sample_ann_real": round(t1_t3_in_sample, 4) if math.isfinite(t1_t3_in_sample) else float("nan"),
        "out_sample_ann_real": round(t1_t3_out_sample, 4) if math.isfinite(t1_t3_out_sample) else float("nan"),
        "c1_net_real_positive": c1,
        "c2_beats_null": c2,
        "c3_lou_shu": c3,
        "c4_in_out_both_positive": c4,
        "null_pctile": null_result.get("strategy_pctile"),
        "lou_shu_b_tstat": lou_shu_result.get("b_tstat"),
    }


def evaluate_h2(
    rev_ann_real: float,
    null_result: dict,
    decay_result: dict,
) -> dict:
    """H2 reversal -- uc kosul AND gerekli.

    (1) net TL-reel > 0 (yuksek-devir maliyet sonrasi)
    (2) fair-null >= 0.95 pctile
    (3) decay testi: post_split > 0 (2020-sonrasi hala var)
    """
    c1 = math.isfinite(rev_ann_real) and rev_ann_real > 0
    c2 = bool(null_result.get("beats_95", False))
    c3 = not bool(decay_result.get("decay_present", True))
    verdict = "PASS" if (c1 and c2 and c3) else "FAIL"
    return {
        "verdict": verdict,
        "ann_real": round(rev_ann_real, 4) if math.isfinite(rev_ann_real) else float("nan"),
        "c1_net_real_positive": c1,
        "c2_beats_null": c2,
        "c3_no_decay": c3,
        "null_pctile": null_result.get("strategy_pctile"),
        "post_split_ann_real": decay_result.get("post_split_ann_real"),
        "decay_present": decay_result.get("decay_present"),
    }
