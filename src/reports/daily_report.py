from datetime import date, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.analysis.portfolio import PositionAnalysis, portfolio_summary
from src.risk.transaction_cost import round_trip_cost_pct
from src.signals.thresholds import (
    EXECUTION_WINDOW_AFTERNOON_END,
    EXECUTION_WINDOW_AFTERNOON_START,
    EXECUTION_WINDOW_MORNING_END,
    EXECUTION_WINDOW_MORNING_START,
    MIN_NET_EXPECTED_VALUE_PCT,
)
from src.utils.config import get_reports_dir
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _jinja_env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=False)
    env.filters["signed"] = lambda v: f"+{v:.1f}" if v >= 0 else f"{v:.1f}"
    env.filters["tl"] = lambda v: f"{v:+,.0f}"
    env.filters["pct"] = lambda v: f"{v:+.1f}%"
    env.filters["thou"] = lambda v: f"{v:,.0f}"
    return env


def _build_context(
    analyses: list[PositionAnalysis],
    momentum_df,
    report_date: date,
) -> dict:
    summ = portfolio_summary(analyses)

    positions = []
    for a in analyses:
        ma20_diff = None
        if a.ma20:
            ma20_diff = (a.current_price - a.ma20) / a.ma20 * 100
        # D-146: Net EV debug log (proxy: profit_target as expected return)
        if a.avg_cost and a.profit_target_price and a.avg_cost > 0:
            _gross_ev = a.profit_target_price / a.avg_cost - 1.0
            _rt_cost = round_trip_cost_pct(a.ticker)
            _net_ev = _gross_ev - _rt_cost
            _tradeable = _net_ev >= MIN_NET_EXPECTED_VALUE_PCT
            logger.debug(
                "%s: gross=%.2f%%, cost=%.2f%%, net=%.2f%%, tradeable=%s",
                a.ticker,
                _gross_ev * 100,
                _rt_cost * 100,
                _net_ev * 100,
                _tradeable,
            )
        positions.append({
            "ticker": a.ticker,
            "quantity": a.quantity,
            "avg_cost": a.avg_cost,
            "current_price": a.current_price,
            "pnl_pct": a.unrealized_pnl_pct,
            "pnl_tl": a.unrealized_pnl,
            "stop_loss": a.stop_loss_price,
            "target": a.profit_target_price,
            "rsi": a.rsi,
            "ma20": a.ma20,
            "ma20_diff": ma20_diff,
            "alerts": a.alerts,
        })

    candidates = []
    if momentum_df is not None and not momentum_df.empty:
        for _, row in momentum_df.iterrows():
            candidates.append({
                "ticker": row["ticker"],
                "close": row["close"],
                "daily_chg": row["daily_chg_pct"],
                "ret_1m": row["ret_1m_pct"],
                "vol_surge": row["vol_surge"],
                "proximity_52w": row["proximity_52w_high_pct"],
                "rsi": row["rsi"],
                "score": row["momentum_score"],
            })

    all_alerts = summ["alerts"]

    return {
        "report_date": report_date.strftime("%d %B %Y"),
        "generated_at": datetime.now().strftime("%H:%M"),
        "positions": positions,
        "total_cost": summ["total_cost"],
        "total_value": summ["total_value"],
        "total_pnl": summ["total_pnl"],
        "total_pnl_pct": summ["total_pnl_pct"],
        "candidates": candidates,
        "alerts": all_alerts,
        "has_high_alerts": bool(summ["high_alerts"]),
        # D-145: Ekinci (2003) BIST intraday execution timing note (rapor notu)
        "execution_window": (
            f"{EXECUTION_WINDOW_MORNING_START}–{EXECUTION_WINDOW_MORNING_END}"
            f" veya "
            f"{EXECUTION_WINDOW_AFTERNOON_START}–{EXECUTION_WINDOW_AFTERNOON_END}"
        ),
    }


def generate_markdown_report(
    analyses: list[PositionAnalysis],
    momentum_df,
    report_date: date | None = None,
) -> Path:
    report_date = report_date or date.today()
    ctx = _build_context(analyses, momentum_df, report_date)
    env = _jinja_env()
    tmpl = env.get_template("markdown.jinja2")
    content = tmpl.render(**ctx)

    out_dir = get_reports_dir()
    out_path = out_dir / f"report_{report_date.strftime('%Y-%m-%d')}.md"
    out_path.write_text(content, encoding="utf-8")
    logger.info("Markdown report saved: %s", out_path)
    return out_path


def generate_html_report(
    analyses: list[PositionAnalysis],
    momentum_df,
    report_date: date | None = None,
) -> Path:
    report_date = report_date or date.today()
    ctx = _build_context(analyses, momentum_df, report_date)
    env = _jinja_env()
    tmpl = env.get_template("html.jinja2")
    content = tmpl.render(**ctx)

    out_dir = get_reports_dir()
    out_path = out_dir / f"report_{report_date.strftime('%Y-%m-%d')}.html"
    out_path.write_text(content, encoding="utf-8")
    logger.info("HTML report saved: %s", out_path)
    return out_path
