"""D-188 -- orchestrator: per-event-type confluence test + Holm + DEC-046 verdict.

Network-free core (run_event_confluence_test): all data injected -> synthetic-testable.
main() wires the live (token/auth-dependent) data path and degrades to data_pending
when sources are unavailable -- it does NOT fabricate measurement.

Holm-Bonferroni is applied SEPARATELY PER EVENT TYPE (across horizons), never pooled
across types. No composite/engine imports.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.screening.event_config import (
    DECISION_HOLM_ALPHA,
    EVENT_CONFIG_VERSION,
    EVENT_HORIZONS,
    MIN_EVENTS_PER_TYPE,
    TOTAL_COST_BPS,
)
from src.screening.event_null import (
    event_conditional_null,
    no_event_null,
    sample_noevent_technical_returns,
)
from src.screening.event_study import build_event_returns, split_confluence


def holm_per_event_type(pvalues: dict, alpha: float = DECISION_HOLM_ALPHA) -> dict:
    """Holm-Bonferroni step-down across the horizons of ONE event type.

    pvalues: {horizon: p_value|None}. Returns per-horizon reject flags + any_significant.
    """
    items = [(h, float(p)) for h, p in pvalues.items() if p is not None and np.isfinite(p)]
    reject = {h: False for h in pvalues}
    m = len(items)
    if m == 0:
        return {"reject": reject, "any_significant": False, "m": 0, "alpha": alpha}
    for rank, (h, p) in enumerate(sorted(items, key=lambda x: x[1])):
        if p <= alpha / (m - rank):
            reject[h] = True
        else:
            break  # step-down: once it fails, all larger p-values fail
    return {"reject": reject, "any_significant": any(reject.values()), "m": m, "alpha": alpha}


def _verdict(per_horizon: dict, holm: dict, n_confluence: int,
             min_events: int = MIN_EVENTS_PER_TYPE) -> dict:
    """Apply frozen DEC-046 across horizons for one event type."""
    if n_confluence < min_events:
        return {"status": "undetermined", "passes": False,
                "reason": f"n_confluence={n_confluence} < MIN_EVENTS_PER_TYPE={min_events} "
                          "-> sample accruing (not pass/fail)"}
    passing = []
    for h, cell in per_horizon.items():
        if (cell["null1"]["beats_95"] and cell["null2"]["beats_95"]
                and np.isfinite(cell["confluence_mean"]) and cell["confluence_mean"] > 0
                and holm["reject"].get(h, False)):
            passing.append(h)
    return {"status": "pass" if passing else "fail", "passes": bool(passing),
            "passing_horizons": passing,
            "rule": "DEC-046: NULL-1>=0.95 AND NULL-2>=0.95 AND XU100-relative>0 AND Holm(per-type)"}


def run_event_confluence_test(
    events_by_type: dict,
    prices: dict,
    xu100: pd.Series,
    tufe: pd.Series | None = None,
    horizons: tuple = EVENT_HORIZONS,
    cost_bps: float = TOTAL_COST_BPS,
    data_pending: dict | None = None,
) -> dict:
    """Per-event-type confluence test (network-free; all inputs injected).

    events_by_type: {event_type: [event_dict, ...]} (event_dict from event_detect).
    data_pending:   {event_type: bool} marking types with no usable data this run.
    """
    data_pending = data_pending or {}
    results: dict = {}
    for etype, events in events_by_type.items():
        enriched = build_event_returns(events, prices, xu100, horizons, cost_bps)
        event_keys = {(e["ticker"], e["event_date"]) for e in enriched}
        per_horizon: dict = {}
        pvals: dict = {}
        n_conf_max = 0
        for h in horizons:
            sp = split_confluence(enriched, h)
            n_conf_max = max(n_conf_max, sp["n_confluence"])
            pool = np.concatenate([sp["confluence_returns"], sp["event_only_returns"]]) \
                if (sp["n_confluence"] + sp["n_event_only"]) else np.array([], dtype=float)
            null1 = event_conditional_null(pool, sp["n_confluence"], sp["confluence_mean"])
            noevent = sample_noevent_technical_returns(prices, xu100, event_keys, h, cost_bps)
            null2 = no_event_null(noevent, sp["n_confluence"], sp["confluence_mean"])
            # primary confluence p-value for Holm = the event-conditional (NULL-1) p
            pvals[h] = null1["p_value"]
            per_horizon[h] = {
                "n_confluence": sp["n_confluence"], "n_event_only": sp["n_event_only"],
                "confluence_mean": _r(sp["confluence_mean"]),
                "event_only_mean": _r(sp["event_only_mean"]),
                "noevent_pool_size": int(noevent.size),
                "null1_event_conditional": null1, "null2_no_event": null2,
                # convenience aliases for the verdict
                "null1": null1, "null2": null2,
            }
        holm = holm_per_event_type(pvals)
        verdict = _verdict(per_horizon, holm, n_conf_max)
        # strip the verdict-only aliases before serialising
        for cell in per_horizon.values():
            cell.pop("null1", None)
            cell.pop("null2", None)
        results[etype] = {
            "n_events": len(enriched),
            "data_pending": bool(data_pending.get(etype, False)),
            "per_horizon": {str(h): per_horizon[h] for h in horizons},
            "holm_per_type": {**holm, "reject": {str(k): v for k, v in holm["reject"].items()}},
            "verdict_DEC046": verdict,
        }
    return {
        "directive": "D-188",
        "config_version": EVENT_CONFIG_VERSION,
        "cost_bps": cost_bps,
        "horizons": list(horizons),
        "results": results,
    }


def _r(x, nd: int = 6):
    return round(float(x), nd) if (x is not None and np.isfinite(x)) else None


def main(out_path: str = "docs/event_test/event_confluence_results.json") -> dict:  # pragma: no cover
    """Live entrypoint: probe + best-effort run. Degrades to data_pending; no fabrication."""
    from src.screening.event_detect import (
        detect_index_inclusion,
        detect_material_kap,
        probe_data_availability,
    )
    probe = probe_data_availability()
    # Historical backtest data is currently unprovisioned (token / no source). We do NOT
    # fabricate events; E2/E3 are explicit data_pending stubs and E1 stays empty without data.
    _idx, idx_pending = detect_index_inclusion()
    _kap, kap_pending = detect_material_kap()
    payload = {
        "directive": "D-188",
        "config_version": EVENT_CONFIG_VERSION,
        "status": "no_measurement_this_round",
        "reason": "Historical event data unprovisioned (backtest data_pending). Forward "
                  "recorder accrues clean samples from FORWARD_RECORDING_START; verdict "
                  "deferred until a sufficient sample exists.",
        "probe": probe,
        "data_pending": {"E1_earnings": True, "E2_index_inclusion": idx_pending,
                         "E3_material_kap": kap_pending},
    }
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


if __name__ == "__main__":  # pragma: no cover
    main()
