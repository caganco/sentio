"""D-192 K3 Illiquidity + Reversal Backtest Runner.

Stage-0 pre-registration onCE yazilir, sonuc gorulmeden.
Sonra: veri yukle -> filtre -> olcum -> H1/H2 verdict -> JSON.

Kullanim:
    python scripts/run_k3_backtest.py

Stage-0 JSON once yazilir; varsa tekrar yazilmaz (post-hoc koruma).
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from src.screening import k3_config as cfg
from src.screening.k3_illiquid_reversal import (
    apply_quality_filter,
    build_portfolio_returns,
    compute_amihud_illiq,
    compute_forward_returns,
    compute_reversal,
    compute_turnover_proxy,
    decay_test,
    evaluate_h1,
    evaluate_h2,
    fair_random_null,
    lou_shu_test,
    portfolio_to_ann_real,
    xu100_relative_ann,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

K3_DIR = ROOT / "docs" / "k3_test"
STAGE0_PATH = K3_DIR / "STAGE0_illiquidity_reversal_preregistration.json"
RESULTS_PATH = K3_DIR / "illiquidity_reversal_results.json"


# ---------------------------------------------------------------------------
# Stage-0 pre-registration (sonuc gorulmeden once dondurulur)
# ---------------------------------------------------------------------------

def write_stage0() -> None:
    """Stage-0 JSON'u yazar. Varsa SKIP (post-hoc override YASAK)."""
    if STAGE0_PATH.exists():
        logger.info("Stage-0 zaten mevcut -- SKIP (post-hoc koruma). %s", STAGE0_PATH)
        return
    K3_DIR.mkdir(parents=True, exist_ok=True)
    stage0 = {
        "directive": cfg.DIRECTIVE,
        "config_version": cfg.CONFIG_VERSION,
        "title": "K3 Illiquidity + Reversal Test -- Stage-0 Pre-Registration",
        "preregistered_date": str(date.today()),
        "discipline_note": (
            "Committed BEFORE any backtest is run. DEC-039. "
            "No post-hoc relaxation permitted."
        ),
        "data": {
            "window": {"start": cfg.DATA_START, "end": cfg.DATA_END},
            "in_sample_end": cfg.IN_SAMPLE_END,
            "out_sample_start": cfg.OUT_SAMPLE_START,
            "decay_split": cfg.DECAY_SPLIT,
            "universe": "TUM-BIST + KNOWN_DELISTED; kuralli-veri-kalite-filtresi",
            "xu100": "yfinance XU100.IS (price-only, no dividends)",
            "tufe": "EVDS TP.FG.J0 (monthly CPI ffill to daily)",
        },
        "factors": {
            "H1_illiquidity": {
                "formula": "ILLIQ_daily = |ret| / (vol * close); rolling mean(20d); log(+eps); lag=2mo",
                "reference": "Amihud (2002), Brennan-Huh-Subrahmanyam (2013)",
                "portfolio": f"T1-T3 tercile spread (equal-weight), "
                             f"rebalance={cfg.ILLIQ_REBALANCE_DAYS}d, "
                             f"cost={cfg.COST_ILLIQUID_RT_BPS}bps RT",
                "lou_shu_control": "cross-sectional OLS: fwd_ret ~ illiq + log_vol_close",
            },
            "H2_reversal": {
                "lookbacks": [f"{cfg.REV_WEEK_DAYS}d", f"{cfg.REV_MONTH_DAYS}d"],
                "signal": "(-1) * past_return (contrarian: buy losers)",
                "reference": "Jegadeesh (1990), Bildik-Gulay (2007), Celik-Ulku (2017)",
                "portfolio": f"bottom-20% reversal long, "
                             f"rebalance={cfg.REV_REBALANCE_DAYS}d, "
                             f"cost={cfg.COST_LIQUID_RT_BPS}bps RT",
            },
        },
        "cost_model": {
            "liquid_rt_bps": cfg.COST_LIQUID_RT_BPS,
            "illiquid_rt_bps": cfg.COST_ILLIQUID_RT_BPS,
            "rationale": (
                "Agresif-slippage: RR-OMEGA uyarisi -- illikidite-primini yiyebilir. "
                "Optimistik-fill YASAK."
            ),
        },
        "decision_rule": {
            "H1_passes_if_ALL": [
                "T1-T3 net TL-reel > 0 annualized",
                f"beats_fair_random_null >= {cfg.NULL_PCTILE_THRESHOLD}",
                f"lou_shu_b_tstat > {cfg.LOU_SHU_TSTAT_MIN} (turnover kontrol sonrasi)",
                "in_sample_ann_real > 0 AND out_sample_ann_real > 0",
            ],
            "H2_passes_if_ALL": [
                "net TL-reel > 0 (yuksek-devir maliyet sonrasi)",
                f"beats_fair_random_null >= {cfg.NULL_PCTILE_THRESHOLD}",
                f"post_split_ann_real > 0 (decay yok, split={cfg.DECAY_SPLIT})",
            ],
            "no_post_hoc_relaxation": True,
        },
        "registered_caveats": [
            "survivorship-bias: yfinance delisted hisseler eksik; "
            "illikit=yuksek delisting-riski -> sonuclar iyimser-biasli olabilir",
            "XU100 price-only (no dividends) ~2-4%/yr benchmark handicap",
            "Lou-Shu proxy log(vol*close); shares-outstanding yok -> ideal degil",
            f"Reversal haftalik: {cfg.REV_REBALANCE_DAYS} gun rebalance, "
            f"yilda ~{52}x * {cfg.COST_LIQUID_RT_BPS}bps = "
            f"~{52*cfg.COST_LIQUID_RT_BPS}bps maliyet drag",
            "Kategori-3 not: out-of-sample (2020+) ve decay-split (2020) AYNI donem "
            "-- bagimsiz dogrulama degil; muhafazakar oku",
        ],
        "null_spec": {
            "method": "random equal-weight portfolio (ayni n_stocks, ayni maliyet, rastgele secim)",
            "seed": cfg.NULL_SEED,
            "n_resamples": cfg.NULL_N_RESAMPLES,
        },
    }
    STAGE0_PATH.write_text(
        json.dumps(stage0, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Stage-0 yazildi: %s", STAGE0_PATH)


# ---------------------------------------------------------------------------
# Veri yukleme
# ---------------------------------------------------------------------------

def _download_prices(
    tickers: list[str], start: str, end: str
) -> dict[str, pd.DataFrame]:
    """yfinance ile OHLCV indir. Hata -> bos dict."""
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance yuklu degil. pip install yfinance")
        return {}

    logger.info("yfinance indiriliyor: %d ticker, %s - %s", len(tickers), start, end)
    prices: dict[str, pd.DataFrame] = {}
    batch_size = 50
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        try:
            raw = yf.download(
                batch, start=start, end=end,
                auto_adjust=True, progress=False, group_by="ticker",
                threads=True,
            )
            if raw.empty:
                continue
            for t in batch:
                try:
                    if isinstance(raw.columns, pd.MultiIndex):
                        df_t = raw[t].copy() if t in raw.columns.get_level_values(0) else pd.DataFrame()
                    else:
                        df_t = raw.copy()
                    if df_t.empty or len(df_t) < 10:
                        continue
                    prices[t] = df_t
                except Exception:
                    continue
        except Exception as exc:
            logger.warning("Batch %d-%d indir hatasi: %s", i, i + batch_size, exc)
    logger.info("Indirilen: %d ticker", len(prices))
    return prices


def _load_xu100(start: str, end: str) -> pd.Series:
    """XU100.IS kapanış serisi."""
    try:
        import yfinance as yf
        df = yf.download(cfg.XU100_SYMBOL, start=start, end=end,
                         auto_adjust=True, progress=False)
        s = df["Close"].squeeze().dropna()
        s.index = pd.to_datetime(s.index)
        s.name = "xu100"
        return s
    except Exception as exc:
        logger.warning("XU100 indir hatasi: %s", exc)
        return pd.Series(dtype=float, name="xu100")


def _load_tufe() -> pd.Series:
    """TUFE compound-growth index (EVDS veya bos)."""
    try:
        from src.screening.exposure_data import freeze_tufe_series
        return freeze_tufe_series(
            start=cfg.DATA_START, end=cfg.DATA_END,
            tag="k3_d192",
        )
    except Exception as exc:
        logger.warning("TUFE yuklenemedi: %s. Real-return NaN olacak.", exc)
        return pd.Series(dtype=float, name="tufe_index")


# ---------------------------------------------------------------------------
# Portfoy metrik ozeti
# ---------------------------------------------------------------------------

def _port_metrics(
    port: pd.Series,
    tufe: pd.Series,
    xu100: pd.Series,
    start: str,
    end: str,
    label: str,
) -> dict:
    """Portfoy icin tam-donem metrikleri."""
    if port.empty:
        nan = float("nan")
        return {"label": label, "n_days": 0, "ann_real": nan,
                "xu100_relative": nan, "in_sample_ann_real": nan,
                "out_sample_ann_real": nan}

    sub = port[(port.index >= start) & (port.index <= end)]
    in_s = sub[sub.index <= cfg.IN_SAMPLE_END]
    out_s = sub[sub.index >= cfg.OUT_SAMPLE_START]

    return {
        "label": label,
        "n_days": len(sub),
        "ann_real": portfolio_to_ann_real(sub, tufe),
        "xu100_relative": xu100_relative_ann(sub, xu100),
        "in_sample_ann_real": portfolio_to_ann_real(in_s, tufe) if not in_s.empty else float("nan"),
        "out_sample_ann_real": portfolio_to_ann_real(out_s, tufe) if not out_s.empty else float("nan"),
    }


# ---------------------------------------------------------------------------
# Ana calisma
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=== D-192 K3 Backtest Basladi ===")

    # ADIM 1: Stage-0 pre-registration (sonuc onCE!)
    write_stage0()

    # ADIM 2: Veri yukle
    all_tickers = list(set(cfg.BIST_ALL_TICKERS + cfg.KNOWN_DELISTED))
    prices_raw = _download_prices(all_tickers, cfg.DATA_START, cfg.DATA_END)
    xu100 = _load_xu100(cfg.DATA_START, cfg.DATA_END)
    tufe = _load_tufe()

    # ADIM 3: Veri-kalite filtresi (kuralli-bolme, elle-secim YASAK)
    prices, quality_report = apply_quality_filter(
        prices_raw, cfg.DATA_START, cfg.DATA_END
    )
    logger.info("Kalite filtresi: %s", quality_report)

    if not quality_report["is_viable"]:
        logger.error(
            "INFEASIBLE: Filtre sonrasi %d hisse (<%d esik). "
            "D-192 bu veriyle gerceklestirilemiyor.",
            quality_report["n_passed"], cfg.UNIVERSE_MIN_STOCKS_VIABLE,
        )
        results = {
            "directive": cfg.DIRECTIVE,
            "status": "INFEASIBLE",
            "infeasible_reason": (
                f"Kalite filtresi sonrasi {quality_report['n_passed']} hisse "
                f"(< {cfg.UNIVERSE_MIN_STOCKS_VIABLE} esik). "
                "Tum-BIST yfinance verisi bu test icin yetersiz."
            ),
            "quality_report": quality_report,
            "lesson": "D-185: kirli-veriyle olcum yapma.",
        }
        K3_DIR.mkdir(parents=True, exist_ok=True)
        RESULTS_PATH.write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("INFEASIBLE sonucu yazildi: %s", RESULTS_PATH)
        return

    logger.info("Efektif evren: %d hisse", len(prices))

    # ADIM 4: H1 -- Amihud ILLIQ faktoru
    logger.info("H1: Amihud ILLIQ hesaplaniyor...")
    illiq = compute_amihud_illiq(prices)
    turnover = compute_turnover_proxy(prices)

    # Ileri getiri (H1 icin: ILLIQ_REBALANCE_DAYS ileriye)
    fwd_illiq = compute_forward_returns(prices, cfg.ILLIQ_REBALANCE_DAYS)

    # Lou-Shu kontrol (kritik: illikidite mi, hacim mi?)
    logger.info("H1: Lou-Shu OLS testi...")
    lou_shu = lou_shu_test(illiq, turnover, fwd_illiq)
    logger.info("Lou-Shu: b_tstat=%.3f, verdict=%s",
                lou_shu.get("b_tstat", float("nan")), lou_shu.get("verdict"))

    # T1-T3 portfoy (illikit long / likit long spread)
    logger.info("H1: T1-T3 portfoy getirisi hesaplaniyor...")
    port_illiq = build_portfolio_returns(
        illiq, prices,
        rebalance_days=cfg.ILLIQ_REBALANCE_DAYS,
        cost_bps_rt=cfg.COST_ILLIQUID_RT_BPS,
        top_pct=1.0 / cfg.ILLIQ_TERCILE_BINS,
        long_high=True,  # high ILLIQ (illikit) long
    )

    illiq_metrics = _port_metrics(
        port_illiq, tufe, xu100,
        cfg.DATA_START, cfg.DATA_END, "H1_illiq_T1_T3"
    )
    logger.info("H1 ann_real=%.3f, in=%.3f, out=%.3f",
                illiq_metrics["ann_real"],
                illiq_metrics["in_sample_ann_real"],
                illiq_metrics["out_sample_ann_real"])

    # Fair null (H1)
    n_illiq_stocks = max(
        1, round(len(prices) * (1.0 / cfg.ILLIQ_TERCILE_BINS))
    )
    logger.info("H1: Fair null testi (%d resample)...", cfg.NULL_N_RESAMPLES)
    null_h1 = fair_random_null(
        prices, illiq_metrics["ann_real"],
        n_illiq_stocks, cfg.ILLIQ_REBALANCE_DAYS,
        cfg.COST_ILLIQUID_RT_BPS, tufe,
        cfg.DATA_START, cfg.DATA_END,
    )
    logger.info("H1 null: pctile=%.3f, beats_95=%s",
                null_h1.get("strategy_pctile", float("nan")),
                null_h1.get("beats_95"))

    # H1 Verdict
    h1 = evaluate_h1(
        illiq_metrics["ann_real"],
        illiq_metrics["in_sample_ann_real"],
        illiq_metrics["out_sample_ann_real"],
        null_h1, lou_shu,
    )
    logger.info("H1 VERDICT: %s", h1["verdict"])

    # ADIM 5: H2 -- Reversal
    logger.info("H2: Short-term reversal hesaplaniyor...")
    rev_week = compute_reversal(prices, cfg.REV_WEEK_DAYS)
    rev_month = compute_reversal(prices, cfg.REV_MONTH_DAYS)

    # Haftalik reversal portfoy
    port_rev_wk = build_portfolio_returns(
        rev_week, prices,
        rebalance_days=cfg.REV_REBALANCE_DAYS,
        cost_bps_rt=cfg.COST_LIQUID_RT_BPS,
        top_pct=1.0 / cfg.REV_QUINTILE,
        long_high=True,  # high reversal skor (kaybedenler) long
    )

    # Aylik reversal portfoy
    port_rev_mo = build_portfolio_returns(
        rev_month, prices,
        rebalance_days=cfg.REV_REBALANCE_DAYS,
        cost_bps_rt=cfg.COST_LIQUID_RT_BPS,
        top_pct=1.0 / cfg.REV_QUINTILE,
        long_high=True,
    )

    rev_wk_metrics = _port_metrics(
        port_rev_wk, tufe, xu100,
        cfg.DATA_START, cfg.DATA_END, "H2_reversal_1wk"
    )
    rev_mo_metrics = _port_metrics(
        port_rev_mo, tufe, xu100,
        cfg.DATA_START, cfg.DATA_END, "H2_reversal_1mo"
    )
    logger.info("H2 1wk ann_real=%.3f | 1mo ann_real=%.3f",
                rev_wk_metrics["ann_real"], rev_mo_metrics["ann_real"])

    # Decay testi (haftalik reversal -- birincil)
    logger.info("H2: Decay testi...")
    decay_wk = decay_test(port_rev_wk, tufe, cfg.DECAY_SPLIT)
    decay_mo = decay_test(port_rev_mo, tufe, cfg.DECAY_SPLIT)
    logger.info("H2 decay 1wk: post=%.3f, decay=%s",
                decay_wk["post_split_ann_real"], decay_wk["decay_present"])

    # Fair null (H2, haftalik -- daha kritik)
    n_rev_stocks = max(1, round(len(prices) / cfg.REV_QUINTILE))
    logger.info("H2: Fair null testi (%d resample)...", cfg.NULL_N_RESAMPLES)
    null_h2 = fair_random_null(
        prices, rev_wk_metrics["ann_real"],
        n_rev_stocks, cfg.REV_REBALANCE_DAYS,
        cfg.COST_LIQUID_RT_BPS, tufe,
        cfg.DATA_START, cfg.DATA_END,
    )
    logger.info("H2 null: pctile=%.3f, beats_95=%s",
                null_h2.get("strategy_pctile", float("nan")),
                null_h2.get("beats_95"))

    # H2 Verdict (haftalik reversal birincil; aylik ikincil robustness)
    h2 = evaluate_h2(rev_wk_metrics["ann_real"], null_h2, decay_wk)
    logger.info("H2 VERDICT: %s", h2["verdict"])

    # ADIM 6: Sonuclari kaydet
    results = {
        "directive": cfg.DIRECTIVE,
        "config_version": cfg.CONFIG_VERSION,
        "run_date": str(date.today()),
        "status": "COMPLETE",
        "quality_report": quality_report,
        "universe_n": len(prices),
        "H1_illiquidity": {
            "metrics_full": illiq_metrics,
            "lou_shu": lou_shu,
            "null": null_h1,
            "verdict": h1,
        },
        "H2_reversal": {
            "metrics_1wk": rev_wk_metrics,
            "metrics_1mo": rev_mo_metrics,
            "decay_1wk": decay_wk,
            "decay_1mo": decay_mo,
            "null": null_h2,
            "verdict_1wk": h2,
        },
        "summary": {
            "H1_verdict": h1["verdict"],
            "H2_verdict": h2["verdict"],
            "conclusion": (
                "Her ikisi PASS -> K3 Yol 2'ye aday (the project karari)"
                if h1["verdict"] == "PASS" and h2["verdict"] == "PASS"
                else "En az biri FAIL -> ilgili nis Yol 2'ye GIRMEZ "
                "(Yol 1 lab ileri-donuk izleyebilir)"
            ),
        },
        "caveats": [
            "survivorship-bias: delisted hisseler eksik; sonuclar iyimser-biasli",
            "XU100 price-only (no dividends)",
            "Lou-Shu proxy (log vol*close); ideal degil",
            "Kategori-3: out-of-sample ve decay-split ayni 2020+ donemi -- bagimsiz degil",
        ],
    }

    K3_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Sonuclar yazildi: %s", RESULTS_PATH)
    logger.info(
        "=== OZET: H1=%s | H2=%s ===",
        h1["verdict"], h2["verdict"],
    )


if __name__ == "__main__":
    main()
