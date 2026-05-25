"""BacktestEngine: simulate daily trading using 3-layer signal stack."""
from __future__ import annotations

import logging

import pandas as pd

from src.backtest.data_loader import build_macro_data, build_technical_data

# KellySizer is not used in the backtest loop (conviction mapping incompatible
# with the backtest signal range); direct Kelly formula is used instead.
from src.signals.layers.risk_layer import score_risk
from src.signals.layers.technical_layer import score_technical
from src.signals.calculator import compute_composite_score, kelly_win_prob
from src.signals.thresholds import (
    ASSET_DIRECTIONS,
    BACKTEST_KELLY_VIX_HAIRCUT,
    BACKTEST_KELLY_VIX_THRESHOLD,
    BACKTEST_MACRO_MIN_SCORE,
    BACKTEST_MAX_POSITION_FRAC,
    BACKTEST_USDTRY_SPIKE_THRESHOLD,
    BACKTEST_VIX_MAX,
    DD_HARD_THRESHOLD,
    EXIT_PROFIT_TARGET,
    EXIT_STOP_LOSS,
    MASTER_WEIGHTS,
    SIGNAL_THRESHOLDS,
)

logger = logging.getLogger(__name__)

# Loggers that spam TCMB/CDS "missing data" warnings during backtest
_NOISY_LOGGERS = [
    "src.signals.layers.macro_layer",
    "src.signals.local_macro_signals",
    "src.signals.local",
    "src.signals.local.cds_fallback",
    "src.data.tcmb_client",
    "src.data.cds_client",
]


class BacktestEngine:
    """Simulate daily BIST trading using Technical + Macro + Risk signals.

    KAP, Smart Money, and Sentiment are hardcoded to 50 (neutral) because
    historical data is not available for these layers.
    """

    def __init__(
        self,
        initial_capital: float = 120_000.0,
        commission_pct: float = 0.001,
        kelly_fraction: float = 0.25,
        start_date: str = "2025-11-01",
        end_date: str = "2026-05-31",
        quiet_warnings: bool = True,
    ):
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.kelly_fraction = kelly_fraction
        self.start_date = start_date
        self.end_date = end_date
        self.quiet_warnings = quiet_warnings

        # Simulation state — reset at start of each run()
        self.cash = initial_capital
        self.portfolio_value = initial_capital
        self.positions: dict[str, dict] = {}
        self.trades: list[dict] = []
        self.equity_curve: list[float] = []
        self.daily_dates: list[pd.Timestamp] = []
        self.drawdown_curve: list[float] = []
        self.audit_trail: list[dict] = []
        self.peak_equity = initial_capital
        self.max_dd = 0.0
        self.circuit_breaker_active = False

    # ── Public API ───────────────────────────────────────────────────────────

    def run(
        self,
        price_data: dict[str, pd.DataFrame],
        macro_ts: pd.DataFrame,
        benchmark_series: pd.Series | None = None,
    ) -> "BacktestEngine":
        """Run backtest simulation. Returns self for chaining."""
        self._reset_state()
        if self.quiet_warnings:
            saved = {n: logging.getLogger(n).level for n in _NOISY_LOGGERS}
            for n in _NOISY_LOGGERS:
                logging.getLogger(n).setLevel(logging.ERROR)
        try:
            self._run_loop(price_data, macro_ts)
        finally:
            if self.quiet_warnings:
                for n, lvl in saved.items():
                    logging.getLogger(n).setLevel(lvl)
        return self

    # ── Internal simulation loop ─────────────────────────────────────────────

    def _reset_state(self) -> None:
        self.cash = self.initial_capital
        self.portfolio_value = self.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.daily_dates = []
        self.drawdown_curve = []
        self.audit_trail = []
        self.peak_equity = self.initial_capital
        self.max_dd = 0.0
        self.circuit_breaker_active = False

    def _run_loop(
        self,
        price_data: dict[str, pd.DataFrame],
        macro_ts: pd.DataFrame,
    ) -> None:
        all_dates: set[pd.Timestamp] = set()
        for df in price_data.values():
            all_dates.update(df.index.tolist())

        start = pd.Timestamp(self.start_date)
        end = pd.Timestamp(self.end_date)
        trading_dates = sorted(d for d in all_dates if start <= d <= end)

        logger.info(
            f"Backtest: {len(trading_dates)} days, {self.start_date} → {self.end_date}, "
            f"{len(price_data)} tickers, capital={self.initial_capital:,.0f} TL"
        )

        for current_date in trading_dates:
            macro_snap = self._safe_macro(macro_ts, current_date)

            for symbol, df in price_data.items():
                if current_date not in df.index:
                    continue
                close_price = float(df.loc[current_date, "Close"])
                volume = float(df.loc[current_date, "Volume"])
                if volume == 0 or pd.isna(close_price) or close_price <= 0:
                    continue

                tech_data = build_technical_data(df, current_date)
                if tech_data is None:
                    continue

                composite, macro_score = self._compute_composite(tech_data, macro_snap, symbol)
                signal = self._composite_to_signal(composite)
                vix_level = macro_snap.get("vix_level", 17.0)
                already_holding = symbol in self.positions

                # Macro-gated entry: block entry if risk-off regime detected
                entry_gated = self._is_entry_gated_by_macro(macro_snap, macro_score)

                if signal in ("BUY-STRONG", "BUY-WEAK") and not already_holding and not self.circuit_breaker_active and not entry_gated:
                    self._execute_buy(symbol, current_date, close_price, composite, vix_level)
                elif signal in ("SELL-WEAK", "SELL-STRONG") and already_holding:
                    self._execute_sell(symbol, current_date, close_price)

                self.audit_trail.append({
                    "date": current_date,
                    "symbol": symbol,
                    "composite": round(composite, 2),
                    "macro_score": round(macro_score, 2),
                    "signal": signal,
                    "entry_gated": entry_gated,
                    "vix_level": macro_snap.get("vix_level"),
                    "USDTRY_1d_change": macro_snap.get("USDTRY_1d_change"),
                    "action": "BUY" if (signal in ("BUY-STRONG", "BUY-WEAK") and not already_holding and not self.circuit_breaker_active and not entry_gated)
                              else ("SELL" if (signal in ("SELL-WEAK", "SELL-STRONG") and already_holding) else "HOLD"),
                })

            self._update_portfolio(price_data, current_date)

            if len(self.daily_dates) % 25 == 0 and self.daily_dates:
                logger.info(
                    f"  Day {len(self.daily_dates)}: {current_date.date()}, "
                    f"portfolio={self.portfolio_value:,.0f} TL, "
                    f"DD={self.max_dd:.1%}, open={len(self.positions)}"
                )

        logger.info(
            f"Backtest complete: {len(self.trades)} trades, "
            f"final={self.portfolio_value:,.0f} TL, max_dd={self.max_dd:.1%}"
        )

    # ── Signal computation ────────────────────────────────────────────────────

    def _compute_composite(
        self,
        technical_data: dict,
        macro_data: dict,
        symbol: str,
    ) -> tuple[float, float]:
        """Compute 3-layer composite score (0-100) and return (composite, macro_score).

        Weights from thresholds.py; L3/L4/L5 stuck at 50.0 neutral stub (D-149d).
        KAP/sentiment/smart_money have no backtest history — contribute their neutral
        50.0 score. Since MASTER_WEIGHTS sum=1.00, neutral inputs give 50.0 composite.
        Delegated to calculator.compute_composite_score() (D-149d).

        Uses _global_macro_score() instead of score_macro() to bypass the
        LOCAL_MACRO compositing that halves macro scores when TCMB/CDS are missing.

        Returns (composite, macro_score) tuple for gating logic.
        """
        try:
            tech_score = score_technical(technical_data).score
        except Exception:
            tech_score = 50.0
        try:
            macro_score = self._global_macro_score(macro_data)
        except Exception:
            macro_score = 50.0
        try:
            risk_score = score_risk(symbol, technical_data, macro_data).score
        except Exception:
            risk_score = 50.0

        composite = compute_composite_score(
            {
                "technical": tech_score,
                "macro": macro_score,
                "risk": risk_score,
                "kap": 50.0,          # neutral stub — veri kisiti, Faz 2 (D-150)'de kaldirilir
                "sentiment": 50.0,    # neutral stub
                "smart_money": 50.0,  # neutral stub
            }
        )
        return composite, macro_score

    @staticmethod
    def _global_macro_score(macro_data: dict) -> float:
        """Compute global macro score (0-100) using only ASSET_DIRECTIONS formula.

        Replicates macro_layer.py global calculation WITHOUT the LOCAL_MACRO
        compositing step (which halves the score when TCMB/CDS are unavailable).
        This is intentional for backtesting: TCMB/CDS historical data is not
        available, and the 50% weighting discount would bias all macro scores low.
        """
        weighted_sum = 0.0
        total_weight = 0.0

        for asset, direction in ASSET_DIRECTIONS.items():
            raw = macro_data.get(asset, macro_data.get(asset.lower()))
            if raw is None:
                continue
            raw_f = max(-1.0, min(1.0, float(raw)))
            adjusted = raw_f * direction
            weight = abs(direction)
            weighted_sum += adjusted * weight
            total_weight += weight

        if total_weight == 0:
            return 50.0

        normalized = weighted_sum / total_weight
        return max(0.0, min(100.0, (normalized + 1.0) / 2.0 * 100.0))

    def _composite_to_signal(self, score: float) -> str:
        if score >= SIGNAL_THRESHOLDS["buy_strong"]:
            return "BUY-STRONG"
        if score >= SIGNAL_THRESHOLDS["buy_weak"]:
            return "BUY-WEAK"
        if score >= SIGNAL_THRESHOLDS["hold_lower"]:
            return "HOLD"
        if score >= SIGNAL_THRESHOLDS["sell_weak"]:
            return "SELL-WEAK"
        return "SELL-STRONG"

    def _is_entry_gated_by_macro(self, macro_data: dict, macro_score: float) -> bool:
        """Check if macro conditions block entry (risk-off regime).

        Returns True if entry is BLOCKED (risk-off).

        Blocks entry if:
        - macro_score < BACKTEST_MACRO_MIN_SCORE (bearish macro)
        - VIX > BACKTEST_VIX_MAX (extreme volatility)
        - USDTRY daily change > BACKTEST_USDTRY_SPIKE_THRESHOLD (EM stress)
        """
        # Macro score gate
        if macro_score < BACKTEST_MACRO_MIN_SCORE:
            return True

        # VIX gate (extreme volatility)
        vix_level = macro_data.get("vix_level")
        if vix_level is not None and vix_level > BACKTEST_VIX_MAX:
            return True

        # USDTRY spike gate (EM outflow stress)
        usdtry_1d_change = macro_data.get("USDTRY_1d_change")
        if usdtry_1d_change is not None and usdtry_1d_change > BACKTEST_USDTRY_SPIKE_THRESHOLD:
            return True

        return False

    # ── Trade execution ───────────────────────────────────────────────────────

    def _get_kelly_allocation_tl(self, composite: float, vix_level: float) -> float:
        """Return TL amount to allocate for a new BUY order.

        Direct Kelly formula: win_prob derived linearly from composite score.
        composite=50 (neutral) -> p=0.50, composite=72 -> p=0.61, composite=100 -> p=0.75.
        VIX haircut ve position cap thresholds.py'den okunur (D-149d).
        """
        win_prob = kelly_win_prob(composite)           # calculator: BASE + SLOPE*(c-50)
        kelly_raw = max(0.0, 2.0 * win_prob - 1.0)    # Kelly criterion (b=1 even-odds)
        position_frac = min(kelly_raw * self.kelly_fraction, BACKTEST_MAX_POSITION_FRAC)
        if vix_level and vix_level > BACKTEST_KELLY_VIX_THRESHOLD:
            position_frac *= BACKTEST_KELLY_VIX_HAIRCUT
        return position_frac * self.portfolio_value

    def _execute_buy(
        self,
        symbol: str,
        current_date: pd.Timestamp,
        close_price: float,
        composite: float,
        vix_level: float,
    ) -> bool:
        """Open a long position. Returns True if executed."""
        allocation_tl = self._get_kelly_allocation_tl(composite, vix_level)
        shares = int(allocation_tl / close_price)
        if shares <= 0:
            return False

        cost = shares * close_price
        commission = cost * self.commission_pct
        total_cost = cost + commission

        if total_cost > self.cash:
            return False

        self.cash -= total_cost
        self.positions[symbol] = {
            "shares": shares,
            "entry_price": close_price,
            "last_price": close_price,
            "entry_date": current_date,
            "composite": composite,
        }
        self.trades.append({
            "symbol": symbol,
            "type": "BUY",
            "date": current_date,
            "price": close_price,
            "shares": shares,
            "composite": composite,
            "commission": commission,
        })
        return True

    def _execute_sell(
        self,
        symbol: str,
        current_date: pd.Timestamp,
        close_price: float,
        reason: str = "signal",
    ) -> bool:
        """Close an existing position. Returns True if executed.

        reason: "signal" (default), "stop_loss", or "profit_target"
        """
        pos = self.positions.get(symbol)
        if pos is None:
            return False

        proceeds = pos["shares"] * close_price
        commission = proceeds * self.commission_pct
        net_proceeds = proceeds - commission

        entry_cost = pos["shares"] * pos["entry_price"]
        pnl = net_proceeds - entry_cost
        pnl_pct = pnl / entry_cost if entry_cost > 0 else 0.0

        self.cash += net_proceeds
        del self.positions[symbol]

        self.trades.append({
            "symbol": symbol,
            "type": "SELL",
            "date": current_date,
            "price": close_price,
            "shares": pos["shares"],
            "entry_price": pos["entry_price"],
            "entry_date": pos["entry_date"],
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "commission": commission,
            "reason": reason,
        })
        return True

    # ── Portfolio tracking ────────────────────────────────────────────────────

    def _update_portfolio(
        self,
        price_data: dict[str, pd.DataFrame],
        current_date: pd.Timestamp,
    ) -> None:
        """Mark-to-market positions and update drawdown state."""
        position_value = 0.0
        for sym, pos in self.positions.items():
            if sym in price_data and current_date in price_data[sym].index:
                price = float(price_data[sym].loc[current_date, "Close"])
                if price > 0:
                    pos["last_price"] = price  # keep last known price for gap days
                    position_value += pos["shares"] * price
            else:
                # Trading halt or data gap — carry forward last known price
                position_value += pos["shares"] * pos.get("last_price", pos["entry_price"])

        self.portfolio_value = self.cash + position_value
        self.equity_curve.append(self.portfolio_value)
        self.daily_dates.append(current_date)

        if self.portfolio_value > self.peak_equity:
            self.peak_equity = self.portfolio_value

        dd = (self.portfolio_value - self.peak_equity) / self.peak_equity
        self.drawdown_curve.append(dd)
        if dd < self.max_dd:
            self.max_dd = dd

        self.circuit_breaker_active = dd <= -DD_HARD_THRESHOLD

        # Check stop-loss and profit-target exits for remaining positions
        symbols_to_exit = []
        for sym in list(self.positions.keys()):
            pos = self.positions[sym]
            entry_price = pos["entry_price"]
            current_price = pos.get("last_price", entry_price)

            # Stop-loss: EXIT_STOP_LOSS below entry
            stop_loss_price = entry_price * EXIT_STOP_LOSS
            if current_price <= stop_loss_price:
                symbols_to_exit.append((sym, current_price, "stop_loss"))
                continue

            # Profit-target: EXIT_PROFIT_TARGET above entry
            profit_target_price = entry_price * EXIT_PROFIT_TARGET
            if current_price >= profit_target_price:
                symbols_to_exit.append((sym, current_price, "profit_target"))
                continue

        # Execute exits
        for sym, exit_price, reason in symbols_to_exit:
            self._execute_sell(sym, current_date, exit_price, reason=reason)

    # ── Export ────────────────────────────────────────────────────────────────

    def export_audit_trail_csv(self, filepath: str) -> None:
        """Export audit_trail to CSV for macro gate analysis.

        Includes: date, symbol, composite, macro_score, signal, entry_gated, vix_level, USDTRY_1d_change.
        """
        import csv

        with open(filepath, "w", newline="") as f:
            if not self.audit_trail:
                f.write("# No audit trail data (backtest did not run or no trades generated)\n")
                return

            fieldnames = [
                "date",
                "symbol",
                "composite",
                "macro_score",
                "signal",
                "entry_gated",
                "vix_level",
                "USDTRY_1d_change",
                "action",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for entry in self.audit_trail:
                writer.writerow({
                    "date": entry.get("date"),
                    "symbol": entry.get("symbol"),
                    "composite": entry.get("composite"),
                    "macro_score": entry.get("macro_score"),
                    "signal": entry.get("signal"),
                    "entry_gated": entry.get("entry_gated", False),
                    "vix_level": entry.get("vix_level"),
                    "USDTRY_1d_change": entry.get("USDTRY_1d_change"),
                    "action": entry.get("action"),
                })

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _safe_macro(macro_ts: pd.DataFrame, as_of: pd.Timestamp) -> dict:
        try:
            return build_macro_data(macro_ts, as_of)
        except Exception:
            return {}
