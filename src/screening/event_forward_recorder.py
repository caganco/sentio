"""D-188 -- FORWARD (paper) recorder: accrue clean, look-ahead-free event samples.

Cagan's insight: MKK_VYK_TOKEN may not arrive for a long time, so historical backtest
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

MANUAL-TRIGGER by default (Cagan runs it ~weekly); cron wiring is deferred. No
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


def run_manual(base_dir: str = _DEFAULT_DIR) -> dict:  # pragma: no cover
    """MANUAL-TRIGGER forward pass (Cagan runs ~weekly). Cron wiring deferred.

    Scaffold: capture today's catalyst disclosures via the AUTH-FREE KAP feed
    (src/data/kap_scraper.fetch_kap_news -> no token), record pre-registered signals,
    then fill any matured forward returns. Network/access failures degrade to a logged
    no-op (data_pending) -- never fabricated. Wiring the disclosure->structured-event
    mapping + universe is completed when forward capture is activated.
    """
    logger.info("D-188 forward recorder: manual pass (auth-free KAP feed). base=%s", base_dir)
    return {
        "status": "scaffold_ready",
        "trigger": "manual (cron deferred)",
        "source": "src/data/kap_scraper.fetch_kap_news (auth-free, no token)",
        "note": "Activate disclosure->event mapping + universe to begin capture; "
                "misses are logged, never fabricated.",
    }


if __name__ == "__main__":  # pragma: no cover
    print(run_manual())
