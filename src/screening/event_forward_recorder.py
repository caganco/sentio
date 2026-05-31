"""D-188 -- FORWARD (paper) recorder: accrue clean, look-ahead-free event samples.

the maintainer's insight: MKK_VYK_TOKEN may not arrive for a long time, so historical backtest
stays blocked. A forward recorder instead accrues UNBIASED samples from today: it
captures catalyst events in real time (auth-free KAP feed), records the pre-registered
signal BEFORE the forward outcome exists, and fills t+5/+20/+60 returns later. Look-ahead,
overfit, and survivorship are STRUCTURALLY impossible (slower, but bias-free).

Design mirrors src/data/signal_logger.py (proven): an IMMUTABLE, append-only,
idempotent SIGNAL log + a SEPARATE append-only RETURNS log filled retroactively. The
signal is never overwritten -> the pre-registration guarantee (as_of < fill time).

Storage (separate from the live signal_logs -- strangler):
  data/event_logs/event_signals.parquet   (immutable; idempotent on natural_key)
  data/event_logs/event_returns.parquet    (append-only; idempotent on (natural_key, horizon))

MANUAL-TRIGGER by default (the maintainer runs it ~weekly); cron wiring is deferred. No
composite/engine imports.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.screening.event_config import EVENT_HORIZONS, TOTAL_COST_BPS
from src.screening.event_confirm import technical_confirm
from src.screening.event_study import forward_window, relative_net

logger = logging.getLogger(__name__)

_DEFAULT_DIR = "data/event_logs"


def natural_key(event_date: str, ticker: str, event_type: str) -> str:
    """Stable identity for an event signal (idempotency key)."""
    return f"{event_date}|{ticker}|{event_type}"


# ---------------------------------------------------------------------------
# Disclosure -> event-type mapping (pure; Turkish keyword match, lower-cased)
# ---------------------------------------------------------------------------
# E1 earnings + E2 index by explicit keywords; E3 = any other CRITICAL/IMPORTANT
# disclosure (per kap_scraper.classify_disclosure severity). NOISE is dropped.
E1_EARNINGS_KEYWORDS = (
    "bilanco", "bilanço", "finansal sonuc", "finansal sonuç", "finansal rapor",
    "finansal tablo", "kar aciklandi", "kâr açıklandı", "zarar aciklandi",
    "zarar açıklandı", "earnings", "ara donem finansal", "ara dönem finansal",
)
E2_INDEX_KEYWORDS = (
    "endeks dahil", "endekse dahil", "endeks cikar", "endeks çıkar",
    "endeksten cikar", "endeksten çıkar", "bist 30", "bist30", "bist 100",
    "bist100", "endeks degisiklik", "endeks değişiklik",
)


def classify_event_type(title: str) -> str | None:
    """Map a disclosure title to E1/E2/E3, or None (NOISE / unmapped).

    E1/E2 by explicit keyword; E3 = any remaining CRITICAL/IMPORTANT disclosure
    (reuses kap_scraper.classify_disclosure as the single severity source).
    """
    if not title:
        return None
    low = title.lower()
    if any(k in low for k in E1_EARNINGS_KEYWORDS):
        return "E1_earnings"
    if any(k in low for k in E2_INDEX_KEYWORDS):
        return "E2_index_inclusion"
    from src.data.kap_scraper import classify_disclosure
    if classify_disclosure(title) in ("CRITICAL", "IMPORTANT"):
        return "E3_material_kap"
    return None


def events_from_news(news_items: list[dict]) -> list[dict]:
    """Map auth-free KAP/news items -> event dicts (pure, network-free).

    surprise_real is left None for E1 (the auth-free feed has no magnitude; it is
    filled later when fundamentals/token arrive -- the maintainer's chosen scope: capture the
    earnings DISCLOSURE + technical confirm now, magnitude later).
    """
    events: list[dict] = []
    for it in news_items or []:
        etype = classify_event_type(it.get("title", ""))
        if etype is None:
            continue
        try:
            ev_date = str(pd.Timestamp(it.get("published")).date())
        except (ValueError, TypeError):
            continue
        ticker = str(it.get("ticker", "")).upper()
        if not ticker:
            continue
        events.append({
            "ticker": ticker, "event_date": ev_date, "event_type": etype,
            "surprise_real": None, "title": it.get("title"), "source": it.get("source"),
        })
    return events


class EventForwardRecorder:
    """Append-only, idempotent IMMUTABLE signal log for forward event capture."""

    def __init__(self, base_dir: str = _DEFAULT_DIR) -> None:
        self._dir = Path(base_dir)
        self._signals = self._dir / "event_signals.parquet"

    def build_signal_records(
        self, events: list[dict], prices: dict, as_of: datetime | None = None,
    ) -> list[dict]:
        """One immutable signal record per event (forward fields intentionally absent).

        signal_fired = event AND technical_confirm (the confluence claim). The forward
        return is NOT computed here -- it does not exist yet (pre-registration guarantee).
        """
        as_of = as_of or datetime.now(timezone.utc)
        recs: list[dict] = []
        for ev in events:
            ohlcv = prices.get(ev["ticker"])
            confirm = bool(technical_confirm(ohlcv, ev["event_date"])) if ohlcv is not None else False
            recs.append({
                "natural_key": natural_key(ev["event_date"], ev["ticker"], ev["event_type"]),
                "event_date": ev["event_date"],
                "ticker": ev["ticker"],
                "event_type": ev["event_type"],
                "surprise_real": ev.get("surprise_real"),
                "technical_confirm": confirm,
                "signal_fired": confirm,   # confluence = event present AND technical confirmed
                "as_of_timestamp": as_of.isoformat(),
            })
        return recs

    def record(self, records: list[dict]) -> int:
        """Append new signal records; idempotent on natural_key. Returns rows added."""
        if not records:
            return 0
        new = pd.DataFrame(records)
        # Collapse within-batch duplicate identities: several distinct disclosures of
        # the same type for one ticker on one day = ONE event day (same t+1 forward
        # window) -> keep the first, avoid double-counting the same window.
        new = new.drop_duplicates(subset="natural_key", keep="first")
        self._dir.mkdir(parents=True, exist_ok=True)
        if self._signals.exists():
            existing = pd.read_parquet(self._signals)
            seen = set(existing["natural_key"].tolist())
            new = new[~new["natural_key"].isin(seen)]
            if new.empty:
                return 0
            combined = pd.concat([existing, new], ignore_index=True)
        else:
            combined = new
        combined.to_parquet(self._signals, index=False)
        return int(len(new))

    def record_events(self, events: list[dict], prices: dict,
                      as_of: datetime | None = None) -> int:
        return self.record(self.build_signal_records(events, prices, as_of))

    def load_signals(self) -> pd.DataFrame:
        return pd.read_parquet(self._signals) if self._signals.exists() else pd.DataFrame()


class EventReturnFiller:
    """Append-only RETURNS log filled retroactively once a horizon matures.

    A horizon matures when the t+1 entry and the t+1+horizon exit bars BOTH exist in
    `prices` and the exit date is on/before `today` -> the outcome is now observable.
    Returns never overwrite signals; idempotent on (natural_key, horizon).
    """

    def __init__(self, base_dir: str = _DEFAULT_DIR) -> None:
        self._dir = Path(base_dir)
        self._signals = self._dir / "event_signals.parquet"
        self._returns = self._dir / "event_returns.parquet"

    def _already(self) -> set[tuple[str, int]]:
        if not self._returns.exists():
            return set()
        df = pd.read_parquet(self._returns)
        if df.empty:
            return set()
        return set(zip(df["natural_key"], df["horizon"].astype(int)))

    def fill(self, today, prices: dict, xu100: pd.Series,
             horizons: tuple = EVENT_HORIZONS, cost_bps: float = TOTAL_COST_BPS) -> int:
        """Compute + append matured forward returns. Returns rows added."""
        if not self._signals.exists():
            return 0
        sigs = pd.read_parquet(self._signals)
        if sigs.empty:
            return 0
        today_s = str(pd.Timestamp(today).date())
        already = self._already()
        filled_at = datetime.now(timezone.utc).isoformat()
        rows: list[dict] = []
        for _, s in sigs.iterrows():
            ohlcv = prices.get(s["ticker"])
            if ohlcv is None or len(ohlcv) == 0:
                continue
            for h in horizons:
                if (s["natural_key"], int(h)) in already:
                    continue
                fw = forward_window(ohlcv, s["event_date"], h)
                if fw is None:
                    continue
                entry_date, exit_date, gross = fw
                if exit_date > today_s:        # not matured yet
                    continue
                rel = relative_net(gross, xu100, entry_date, exit_date, cost_bps)
                rows.append({
                    "natural_key": s["natural_key"], "ticker": s["ticker"],
                    "event_date": s["event_date"], "event_type": s["event_type"],
                    "horizon": int(h), "entry_date": entry_date, "exit_date": exit_date,
                    "gross_return": round(float(gross), 5), "rel_net_return": rel,
                    "filled_at": filled_at,
                })
        if not rows:
            return 0
        new = pd.DataFrame(rows)
        self._dir.mkdir(parents=True, exist_ok=True)
        if self._returns.exists():
            combined = pd.concat([pd.read_parquet(self._returns), new], ignore_index=True)
        else:
            combined = new
        combined.to_parquet(self._returns, index=False)
        return int(len(new))

    def load_returns(self) -> pd.DataFrame:
        return pd.read_parquet(self._returns) if self._returns.exists() else pd.DataFrame()


def capture_once(universe: list[str] | None = None, price_lookback_days: int = 180,
                 base_dir: str = _DEFAULT_DIR, today=None) -> dict:  # pragma: no cover (network)
    """LIVE forward pass: capture today's catalyst disclosures + fill matured returns.

    1. fetch_kap_news(universe) -- AUTH-FREE, no token (recent ~24h; WAF-fragile).
    2. map -> event dicts (events_from_news).
    3. fetch OHLCV for ALL signal-log tickers + today's event tickers (so OLD signals
       mature too, not just today's).
    4. record_events (immutable, pre-registration) + fill matured t+5/+20/+60 returns.
    Network/access failures degrade to a logged result; events are never fabricated.
    """
    from datetime import date, timedelta

    from src.backtest.data_loader import load_price_data
    from src.data.kap_scraper import fetch_kap_news

    if universe is None:
        from src.screening.trend_config import TREND_UNIVERSE
        universe = list(TREND_UNIVERSE)
    today = today or date.today()

    try:
        news = fetch_kap_news(universe)
    except Exception as exc:
        logger.warning("capture_once: fetch_kap_news failed: %s", exc)
        news = []
    events = events_from_news(news)

    rec = EventForwardRecorder(base_dir)
    fil = EventReturnFiller(base_dir)
    existing = rec.load_signals()
    sig_tickers = set(existing["ticker"].tolist()) if not existing.empty else set()
    price_tickers = sorted(sig_tickers | {e["ticker"] for e in events})

    start = (today - timedelta(days=price_lookback_days)).isoformat()
    end = (today + timedelta(days=1)).isoformat()
    prices = load_price_data(price_tickers, start, end) if price_tickers else {}
    xu = load_price_data(["XU100"], start, end).get("XU100")
    xu100 = xu["Close"] if xu is not None else pd.Series(dtype=float)

    n_rec = rec.record_events(events, prices, as_of=datetime.now(timezone.utc))
    n_fill = fil.fill(today, prices, xu100)

    by_type: dict[str, int] = {}
    for e in events:
        by_type[e["event_type"]] = by_type.get(e["event_type"], 0) + 1
    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "universe_n": len(universe), "news_n": len(news), "events_n": len(events),
        "events_by_type": by_type, "recorded_new": n_rec, "returns_filled": n_fill,
        "total_signals": int(len(rec.load_signals())),
        "total_returns": int(len(fil.load_returns())),
        "base_dir": str(base_dir),
    }
    logger.info("D-188 capture_once: %s", summary)
    return summary


# Manual entrypoint retained as an alias; daily automation calls capture_once.
def run_manual(base_dir: str = _DEFAULT_DIR) -> dict:  # pragma: no cover
    """MANUAL-TRIGGER forward pass -- now a thin alias over capture_once (full universe)."""
    return capture_once(base_dir=base_dir)


if __name__ == "__main__":  # pragma: no cover
    import json
    print(json.dumps(capture_once(), ensure_ascii=False, indent=2))
