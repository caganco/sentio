# OS_STATE.md — System State Snapshot

**This file is auto-updated every 6 hours by `scripts/daily_update.py`**

---

## Metadata

```yaml
version: "1.0"
updated_at: "2026-05-14T20:30:00Z"
update_interval_hours: 6
next_update: "2026-05-15T02:30:00Z"
staleness_warning_hours: 24
staleness_critical_hours: 48
```

---

## Macro Data (Current)

```yaml
usd_try:
  value: 45.43
  trend: "↑ Strong"
  updated_at: "2026-05-14T14:00:00Z"
  age_hours: 6.5

brent:
  value: 104.92
  trend: "↑ Elevated"
  updated_at: "2026-05-14T14:00:00Z"
  age_hours: 6.5

vix:
  value: 17.89
  trend: "↔ Normal"
  updated_at: "2026-05-14T14:00:00Z"
  age_hours: 6.5

cds_turkey_5y_bps:
  value: 450
  trend: "⚠️ Moderate"
  source: "proxy"  # "primary" | "proxy" | "cache"
  confidence: 0.7
  updated_at: "2026-05-14T14:00:00Z"
  age_hours: 6.5

bist100:
  value: 14676.21
  trend: "↔ Flat"
  updated_at: "2026-05-14T16:00:00Z"
  age_hours: 4.5
```

---

## Regime (Macro Environment)

```yaml
current: "TRANSITION"
confidence: 0.65
signal_score: 0.013
breadth: 0.47
last_changed: "2026-05-12T09:00:00Z"
description: "Mixed signals. Risk-on macro (USD up, Brent up) but BIST breadth weak (47%). Concentration in energy + holding."
```

---

## Portfolio Status

```yaml
total_value: 250000
positions_count: 5
pnl_pct: -0.58
top_position: "ENERY"  # by weight
worst_performer: "TAVHL"  # by PnL
last_rebalance: "2026-05-14T00:00:00Z"
```

---

## System Health (Data Sources)

```yaml
local_macro:
  status: "OK"
  last_success: "2026-05-14T14:00:00Z"
  failures_since_update: 0
  data_freshness: "< 6h"

kap_pipeline:
  status: "OK"
  last_success: "2026-05-14T14:20:00Z"
  queue_depth: 3
  data_freshness: "< 1h"

strategist_agent:
  status: "OK"
  last_run: "2026-05-14T14:00:00Z"
  runtime_seconds: 4.2
  tokens_used: 587
  data_freshness: "< 1h"

signal_engine:
  status: "OK"
  last_run: "2026-05-14T14:00:00Z"
  layers_active: 4
  coverage: "60 tickers"
  data_freshness: "< 1h"
```

---

## Active Alerts

```yaml
alerts:
  - level: "INFO"
    message: "CDS: Using iShares proxy model (primary scraping blocked by WAF)"
    timestamp: "2026-05-14T14:00:00Z"
    
  - level: "WARNING"
    message: "BIST holidays: May 19 (Commemoration Day) upcoming — fetch will skip"
    timestamp: "2026-05-14T00:00:00Z"
    
  - level: "INFO"
    message: "TAVHL: momentum diverging from macro alignment (watch for reversal)"
    timestamp: "2026-05-14T14:00:00Z"
```

---

## Configuration (Active)

```yaml
model: "claude-sonnet-4-6"

signal_weights:
  tech: 0.20
  macro: 0.333
  kap: 0.267
  risk: 0.067

report_token_budget: 600

data_refresh_intervals:
  macro: 6  # hours
  kap: 1
  market_data: 1
  os_state: 6

cache_policies:
  macro_ttl_hours: 24
  macro_ttl_incident_hours: 72
  kap_ttl_hours: 24
  kap_ttl_incident_hours: 72
  signal_ttl_hours: 1

portfolio:
  tickers:
    - AKSEN
    - TTKOM
    - TAVHL
    - KCHOL
    - ENERY
  watch_list:
    - BIMAS
    - THYAO
```

---

## Backlog & Blockers

| Priority | Task | Status | Est. Time |
|----------|------|--------|-----------|
| 🔴 HIGH | Kelly Criterion position sizing | 🟡 Pending SPEC | 1-2 days |
| 🔴 HIGH | Drawdown management (-10% risk-off) | 🟡 Pending | 1 day |
| 🟠 MED | EVDS batch call optimization | 🟡 Pending | 2-3 hours |
| 🟠 MED | News sentiment NLP (Layer 4) | 🟡 Pending SPEC | 3-5 days |
| 🟡 LOW | Smart money tracking (Layer 5) | 🟡 Pending | TBD |

---

## Test Suite Status

```yaml
total_tests: 372
passed: 372
failed: 0
skipped: 1
regression: "ZERO ✅"

recent_additions:
  - "42 KAP edge case tests (SPEC_KAP)"
  - "25 macro alignment tests (SPEC_MACRO_EQUITY)"
  - "14 CDS fallback tests (SPEC_CDS)"

coverage_percent: 87
```

---

**Last Auto-Update:** 2026-05-14T20:30:00Z (by daily_update.py)  
**Next Auto-Update:** 2026-05-15T02:30:00Z  
**Manual Edit Status:** ✅ Ready for architect edits (config_active section)
