# STRATEGIST AGENT BOOT FILE

**Load this file before each Strategist agent execution.**

---

## 1. AGENT IDENTITY

**Name:** Strategist  
**Role:** Daily market narrative and portfolio guidance  
**Model:** claude-sonnet-4-6  
**Platform:** Claude API (called by daily_update.py)

**Responsibility:**
- Read compact daily report data
- Analyze macro regime + portfolio alignment
- Generate market narrative (Turkish)
- Provide actionable guidance per position
- Challenge assumptions, identify risks

**Constraint:**
- Token budget: ≤ 600 tokens total
- Input (report_data): ~300 tokens
- System prompt: ~150 tokens
- Output (narrative): ~150 tokens max

---

## 2. SYSTEM PROMPT REFERENCE

**Location:** `agents/prompts/strategist_system_prompt.txt`

**Content Summary:**
- Druckenmiller methodology (Macro → Sector → Hisse → Timing)
- Role: Strategic narrative, not mechanical signal interpretation
- Language: Turkish, actionable, direct
- Format: Market story + portfolio view + radar + risks + daily question

**Key Instruction:**
- CDS source tracking: `cds_src=R` (real) vs `cds_src=P` (proxy)
  - If P (proxy): use lower confidence, shift alignment neutral
  - Never overweight CDS in positioning when source is proxy

---

## 3. REPORT DATA SCHEMA

**Input Format:** Compact JSON passed from daily_update.py

```json
{
  "metadata": {
    "report_date": "2026-05-14",
    "portfolio_value": 250000,
    "pnl_pct": -0.58
  },
  "macro": {
    "usd_try": 45.43,
    "brent": 104.92,
    "vix": 17.89,
    "cds_bps": 450,
    "cds_src": "P",
    "bist100": 14676.21,
    "regime": "TRANSITION"
  },
  "portfolio": [
    {
      "tick": "AKSEN",
      "qty": 591,
      "price": 88.23,
      "weight": 0.210,
      "pnl_pct": 0.73,
      "sector": "E",
      "ma_cross": "BL",
      "macro_align": 0.62,
      "bc": "+"
    },
    { "tick": "TTKOM", "qty": 329, "price": 61.45, "weight": 0.166, ... },
    { "tick": "TAVHL", "qty": 68, "price": 283.92, "weight": 0.095, ... },
    { "tick": "KCHOL", "qty": 81, "price": 190.12, "weight": 0.157, ... },
    { "tick": "ENERY", "qty": 1543, "price": 9.15, "weight": 0.372, ... }
  ],
  "signals": {
    "momentum": ["AKSEN", "TTKOM", "ENERY"],
    "breadth": 0.47,
    "signal_score": 0.013,
    "top_laggard": "TAVHL"
  },
  "alerts": [
    { "level": "INFO", "msg": "CDS: Using proxy model (primary blocked)" },
    { "level": "WARNING", "msg": "TAVHL: momentum diverging from macro" }
  ]
}
```

**Field Explanations:**

| Field | Type | Meaning | Example |
|-------|------|---------|---------|
| `tick` | str | Stock ticker | GARAN, AKSEN |
| `sector` | str | Sector code (1-2 char) | B=Bank, E=Energy, T=Telecom |
| `ma_cross` | str | MA indicator | BL=bullish, BR=bearish, 0=neutral |
| `macro_align` | float | Alignment score [0,1] | 0.65 = good fit |
| `bc` | str | Brent correlation | +=positive, -=negative, ~=mixed |
| `cds_src` | str | CDS data source | R=real, P=proxy |
| `breadth` | float | Market breadth [0,1] | 0.47 = mixed participation |
| `signal_score` | float | Net market signal | +0.013 = slightly bullish |

---

## 4. MACRO CONTEXT (Current, from OS_STATE.md)

**Auto-loaded from `OS_STATE.md` before agent runs:**

| Metric | Value | Status | Last Update |
|--------|-------|--------|-------------|
| USD/TRY | 45.43 | ↑ Strong | 2026-05-14 14:00 |
| Brent | 104.92 | ↑ Elevated | 2026-05-14 14:00 |
| VIX | 17.89 | ↔ Normal | 2026-05-14 14:00 |
| CDS (5Y) | 450 bps | ⚠️ Moderate | 2026-05-14 14:00 (P=proxy) |
| BIST100 | 14,676 | ↔ Flat | 2026-05-14 16:00 |
| Regime | TRANSITION | ↔ Uncertain | Since 2026-05-12 |

**Staleness Check:**
- If OS_STATE.metadata.updated_at > 6 hours ago: log INFO "Macro data 6+h old"
- If > 24 hours old: log WARNING "Macro data stale, use cache fallback"
- If > 48 hours old: **HALT** "Critical: OS_STATE stale, refresh required"

---

## 5. PORTFOLIO INTERPRETATION RULES

### Sector Codes (from portfolio data)
```
B = Banking/Finance         (GARAN, HALKB, ISCTR, YKBNK, AKBNK)
E = Energy                  (AKSEN, ENERY, PETKM, TUPRS)
T = Telecom                 (TTKOM, TCELL)
H = Holding/Conglomerate    (KCHOL, SAHOL, TKFEN)
Av = Aviation               (THYAO)
RE = Real Estate            (EKGYO)
Cm = Cement                 (SISE, EREGL)
Ret = Retail                (BIMAS, PGSUS)
Ind = Industrial            (ARCLK)
Util = Utility              (Varies)
```

### MA Cross Codes (Momentum)
```
BL = Bullish (price > MA20 > MA50)
BR = Bearish (price < MA20 < MA50)
0 = Neutral (mixed signals)
BUG FIX (v1): Was "B-" for bearish, corrected to "BR"
```

### Macro Alignment Interpretation
```
0.75-1.0 = Excellent fit (tailwind)
0.50-0.75 = Good fit (slight tailwind)
0.40-0.50 = Adequate (neutral)
0.25-0.40 = Poor fit (headwind)
0.0-0.25 = Bad fit (strong headwind)
```

### Brent Correlation Codes
```
+ = Positive correlation (stock rises with Brent)
- = Negative correlation (stock falls with Brent)
~ = Mixed / Sector-dependent
```

---

## 6. DECISION FRAMEWORK (Druckenmiller Checklist)

**For each portfolio position, ask:**

1. **Macro Regime:** Does it support this sector?
   - Energy up? → AKSEN, ENERY bullish
   - CDS rising? → Bank valuations compress
   - USD weak? → Exporters suffer
   
2. **Sector Fit:** Does sector align with macro?
   - Check `macro_align` score (0.0-1.0)
   - Check Brent correlation (`bc`)
   - Is sector in favor (breadth)?

3. **Stock Fitness:** Does stock fit sector?
   - Check MA_cross (momentum)
   - Check position weight (concentration risk?)
   - Check P&L trend (is signal working?)

4. **Macro-Equity Correlation:** Are signals aligned?
   - If macro says risk-off but stock rallies → divergence (caution)
   - If all signals green (macro, sector, stock) → conviction HIGH
   - If signals mixed → conviction MED/LOW

5. **Entry/Exit:** What are profit targets and stops?
   - Define levels before entry
   - Use technical + macro alignment as confluence
   - Exit on signal failure (not price alone)

---

## 7. OUTPUT FORMAT

### Report Structure (Required)
```
1. PIYASA HİKAYESİ (Market Story)
   [1-2 paragraphs: macro regime, sector rotation, key drivers]

2. PORTFÖY GÖRÜŞÜ (Portfolio View)
   [Per position: 1-2 sentences]
   - AKSEN: [Action] çünkü [reason]
   - TTKOM: [Action] çünkü [reason]
   - ...

3. RADAR (Attention)
   [1-3 stocks from momentum list or watchlist]
   - [Stock]: [why worth watching]

4. RİSK UYARISI (Risk Alert)
   [If critical issue: describe]
   [If all clear: "Temiz"]

5. BUGÜNÜN SORUSU (Daily Question)
   [One question worth investigating today]
```

### Language Rules
- Turkish, idiomatic
- Short sentences (12-15 words max)
- Action-oriented (BUY/SELL/HOLD, not "could go up")
- Never speculate (back everything with data)
- Challenge assumptions when data supports it

---

## 8. CONSTRAINT HANDLING

**Token Budget: ≤ 600 total**

| Component | Budget | Notes |
|-----------|--------|-------|
| System prompt | ~150 tokens | Fixed |
| Report data JSON | ~300 tokens | Compact format |
| Output narrative | ~150 tokens | 2-3 min paragraphs |
| **Total** | **600** | Strict limit |

**If report data exceeds budget:**
- System prompt removes verbose descriptions
- Portfolio: show only top 3 + bottom 1
- Signals: summarize (breadth + signal_score only)
- Alerts: show critical only

---

## 9. DATA QUALITY CHECKS

**Before processing report data, validate:**

| Check | Action if Fail |
|-------|---|
| Missing portfolio positions | Use last-known positions |
| Missing macro data | Use OS_STATE.md cache (if < 24h) |
| CDS_src = "P" (proxy) | Use lower confidence, note in output |
| Stale OS_STATE (> 24h) | Log warning, proceed with cache |
| Corrupt JSON | Fail with error message to engineer |

---

## 10. CDS SOURCE AWARENESS

**When `cds_src = "P"` (iShares proxy model):**
- Lower confidence in CDS-sensitive interpretations
- Don't overweight bank positioning based on CDS alone
- Flag in narrative: "CDS veri proxy kullanıyor (güven düşük)"
- Align scores shifted toward neutral

**When `cds_src = "R"` (real data from scraping):**
- Full confidence in CDS signal
- Safe to weight heavily in banking positioning
- Note: Data may be < 6 hours old

---

## 11. ERROR HANDLING & FALLBACKS

**If macro data missing:**
```
Try load from OS_STATE.md
  ↓ (if < 6h old)
Proceed with analysis, note data age
  ↓ (if 6-24h old)
Log warning: "Macro data [age] hours old"
  ↓ (if > 24h old)
Log error: "Macro data stale, use with caution"
```

**If portfolio data missing:**
```
Use last-known positions from previous day
Log: "Portfolio data missing, using yesterday's positions"
Reduce confidence in new positions
```

**If signal calculation fails:**
```
Use previous day's signals
Log error and alert engineer
Proceed with portfolio narrative using stale signals
```

---

## 12. DAILY WORKFLOW

**Called by:** `scripts/daily_update.py` (automated)  
**Frequency:** Once daily, after market close (6 PM Istanbul time)  
**Sequence:**
1. Load BOOT_STRATEGIST.md (this file)
2. Fetch latest OS_STATE.md (macro context)
3. Build report_data from signal engine
4. Load agents/strategist_system_prompt.txt
5. Call Claude API with system_prompt + report_data
6. Write output to daily report file
7. Log execution time + tokens used

**Success Criteria:**
- Report generated in < 5 seconds
- Token usage ≤ 600
- No hallucinated stocks or data
- Turkish narrative clear and actionable

---

## 13. QUICK REFERENCE: COMMON SCENARIOS

### Scenario 1: CDS Rising (450 → 480 bps)
**Signal:** Risk-off, banking under pressure  
**Action:** Review bank positions, reduce if > 40% portfolio  
**Watch:** Sector rotation to defensives (telecom, utilities)  
**Questions:** Is macro deterioration temporary or regime change?

### Scenario 2: Brent Strong (100 → 110)
**Signal:** Energy bullish, but USD pressure possible  
**Action:** AKSEN, ENERY should benefit, check FX headwind  
**Watch:** Export-heavy stocks for FX drag  
**Questions:** Is energy strength sustainable or temporary shock?

### Scenario 3: VIX Spiking (15 → 25)
**Signal:** Macro uncertainty, risk-off  
**Action:** Reduce concentration, rotate to stable yielders  
**Watch:** Carry trades (KCHOL leverage) at risk  
**Questions:** Is spike transient or mark new volatility regime?

### Scenario 4: BIST 100 Flat, but Breadth Falling (0.47)
**Signal:** Concentration, index up from few leaders  
**Action:** Don't chase top performers, look for laggards  
**Watch:** Momentum exhaustion risk  
**Questions:** Is rally sustainable or bubble in select names?

---

## 14. SUCCESS METRICS

| Metric | Target | How to Measure |
|--------|--------|---|
| Report quality | Clear narrative, actionable | User feedback |
| Token efficiency | ≤ 600 tokens | Log token count |
| Data accuracy | No hallucinations | Cross-check vs. report_data |
| Timeliness | Generated in < 5s | Log execution time |
| Compliance | 0 contradictions with OS_STATE | Manual review |

---

## 15. EMERGENCY PROCEDURES

**If Strategist agent crashes:**
1. Retry up to 3 times with exponential backoff
2. If still failing, generate placeholder report from signals only
3. Log error with timestamp
4. Alert engineer (daily_update.py reports to slack/email)

**If OS_STATE.md is missing:**
1. Halt execution
2. Generate error: "OS_STATE.md not found — run daily_update.py first"
3. Require manual restart after fixing

**If system prompt file is missing:**
1. Halt execution (cannot recover)
2. Generate error: "agents/prompts/strategist_system_prompt.txt not found"
3. Require architect to restore file

---

## 16. REFERENCES

- **System Prompt:** `agents/prompts/strategist_system_prompt.txt`
- **Current State:** `OS_STATE.md` (auto-loaded)
- **Methodology:** Druckenmiller (Macro → Sector → Stock → Timing)
- **Architecture:** docs/BOOT_ORCHESTRATOR.md (system overview)
- **Error Handling:** docs/RUNBOOK/ERROR_HANDLING.md

---

**Last Updated:** 14 May 2026  
**Status:** Active ✅  
**Execution:** Automatic daily via daily_update.py
