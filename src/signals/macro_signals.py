"""Macro signals: Risk regime detection and macro environment scoring."""
import json
import pandas as pd
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from src.utils.logger import setup_logger
from src.utils.config import get_db_path
from src.data.macro_feed import load_from_db, get_latest_snapshot

logger = setup_logger(__name__)


@dataclass
class MacroSignal:
    """Macro signal with regime and environment score."""

    timestamp: str  # ISO format
    regime: Literal["RISK_ON", "RISK_OFF", "TRANSITION"]

    # Component scores [-1, +1]
    vix_score: float
    usdtry_score: float
    brent_score: float
    bist100_score: float

    # Weighted average
    macro_environment_score: float

    # Meta
    data_date: str
    symbols: dict


def score_macro_component(
    symbol: str,
    current_close: float,
    prev_close: float,
    is_inverse: bool = False,
) -> float:
    """
    Score a macro component [-1, +1].

    Logic:
    - pct_change = (current - prev) / prev * 100
    - normal: pct_change > +2% → +1, < -2% → -1
    - inverse (USDTRY): -pct_change (TRY strengthening is positive)

    Clamps result to [-1, +1].
    """
    if prev_close == 0 or pd.isna(current_close) or pd.isna(prev_close):
        return 0.0

    pct_change = ((current_close - prev_close) / prev_close) * 100

    if is_inverse:
        pct_change = -pct_change

    # Linear scale: ±5% = ±1
    score = max(-1.0, min(1.0, pct_change / 5.0))

    logger.debug(f"{symbol}: pct_change={pct_change:.2f}%, score={score:.3f}")

    return score


def calculate_macro_environment_score(
    vix_score: float,
    usdtry_score: float,
    brent_score: float,
    bist100_score: float,
    weights: dict = None,
) -> float:
    """
    Weighted average macro environment score.

    Default weights favor BIST100 (40% — primary market) and VIX (25% — volatility).
    Returns: [-1, +1]
    """
    if weights is None:
        weights = {
            "vix": 0.25,
            "usdtry": 0.15,
            "brent": 0.20,
            "bist100": 0.40,
        }

    weighted = (
        vix_score * weights["vix"]
        + usdtry_score * weights["usdtry"]
        + brent_score * weights["brent"]
        + bist100_score * weights["bist100"]
    )

    return max(-1.0, min(1.0, weighted))


def detect_regime(
    vix_score: float,
    usdtry_score: float,
    brent_score: float,
    bist100_score: float,
    macro_score: float,
    vix_threshold_low: float = 15.0,
    vix_threshold_high: float = 25.0,
) -> Literal["RISK_ON", "RISK_OFF", "TRANSITION"]:
    """
    Detect macro regime from component scores.

    Rules:
    - RISK_ON: macro_score >= 0.3 (positive macro environment)
    - RISK_OFF: macro_score <= -0.3 (negative macro environment)
    - TRANSITION: else
    """
    if macro_score >= 0.3:
        return "RISK_ON"
    elif macro_score <= -0.3:
        return "RISK_OFF"
    else:
        return "TRANSITION"


def generate_macro_signal(
    db_path: str = None,
    weights: dict = None,
) -> MacroSignal:
    """
    Generate current macro signal from latest feed data.

    Process:
    1. Load latest snapshot (most recent date per symbol)
    2. Get previous day data for each symbol
    3. Calculate pct_change and score each component
    4. Calculate weighted macro environment score
    5. Detect regime
    6. Return MacroSignal object
    """
    if db_path is None:
        db_path = get_db_path()

    logger.info("Generating macro signal...")

    # Load latest snapshot
    latest = get_latest_snapshot(db_path=db_path)
    if latest.empty:
        logger.error("No latest snapshot data available")
        raise ValueError("Cannot generate signal: no macro data")

    logger.debug(f"Latest snapshot: {len(latest)} symbols")

    # Extract symbols and latest date
    data_date = latest["date"].max()
    symbols_dict = {}

    # Load recent history (last 5 days) for 1-day % change calculation
    from datetime import datetime, timedelta

    try:
        hist_start = (
            datetime.strptime(data_date, "%Y-%m-%d") - timedelta(days=5)
        ).strftime("%Y-%m-%d")
    except Exception:
        hist_start = "2026-05-08"

    hist = load_from_db(db_path=db_path, start=hist_start)
    if hist.empty:
        logger.warning("No historical data for comparison")
        hist = latest.copy()

    # Calculate component scores
    scores = {"vix": 0.0, "usdtry": 0.0, "brent": 0.0, "bist100": 0.0}

    for symbol in ["USDTRY", "BRENT", "VIX", "BIST100"]:
        symbol_data = latest[latest["symbol"] == symbol].sort_values("date", ascending=False)
        if symbol_data.empty:
            logger.warning(f"No data for {symbol}")
            continue

        current_close = symbol_data.iloc[0]["close"]
        symbols_dict[symbol] = float(current_close)

        # Get previous close (1 day before if available)
        hist_symbol = (
            hist[hist["symbol"] == symbol]
            .sort_values("date", ascending=False)
            .drop_duplicates()
        )

        prev_close = None
        if len(hist_symbol) > 1:
            prev_close = hist_symbol.iloc[1]["close"]
        elif len(hist_symbol) == 1:
            # Only one data point, use current as baseline (0% change)
            prev_close = current_close

        if prev_close is None or prev_close == 0:
            score = 0.0
        else:
            # USDTRY is inverse: TRY strength (USDTRY down) is positive
            is_inverse = symbol == "USDTRY"
            score = score_macro_component(
                symbol, current_close, prev_close, is_inverse=is_inverse
            )

        key = symbol.lower()
        scores[key] = score
        logger.info(f"{symbol}: score={score:.3f}, current={current_close:.2f}")

    # Calculate macro environment score
    macro_env_score = calculate_macro_environment_score(
        vix_score=scores["vix"],
        usdtry_score=scores["usdtry"],
        brent_score=scores["brent"],
        bist100_score=scores["bist100"],
        weights=weights,
    )

    # Detect regime
    regime = detect_regime(
        vix_score=scores["vix"],
        usdtry_score=scores["usdtry"],
        brent_score=scores["brent"],
        bist100_score=scores["bist100"],
        macro_score=macro_env_score,
    )

    # Create signal
    signal = MacroSignal(
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        regime=regime,
        vix_score=scores["vix"],
        usdtry_score=scores["usdtry"],
        brent_score=scores["brent"],
        bist100_score=scores["bist100"],
        macro_environment_score=macro_env_score,
        data_date=data_date,
        symbols=symbols_dict,
    )

    logger.info(
        f"Signal generated: regime={regime}, "
        f"macro_score={macro_env_score:.3f}, data_date={data_date}"
    )

    return signal


def save_signal_json(
    signal: MacroSignal,
    output_dir: str = "agents/intelligence",
) -> str:
    """
    Save MacroSignal to JSON file.

    Output: agents/intelligence/macro_signal_YYYY-MM-DD.json

    Returns: File path
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    filename = f"macro_signal_{signal.data_date}.json"
    filepath = output_path / filename

    signal_dict = asdict(signal)
    signal_dict["symbols"] = {
        k: float(v) if isinstance(v, (int, float)) else v
        for k, v in signal_dict["symbols"].items()
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(signal_dict, f, indent=2, ensure_ascii=False)

    logger.info(f"Signal saved: {filepath}")
    return str(filepath)
