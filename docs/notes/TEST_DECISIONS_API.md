# Testing Trading Decisions & API Integration

## Quick Test (5 minutes)

### 1. Start the API Server

```bash
cd path/to/bist-trading-system
python server.py
```

**Expected output:**
```
 * Running on http://127.0.0.1:5000
 * Debug mode: off
```

### 2. Test the /decisions Endpoint (New Terminal)

```bash
# List all endpoints
curl http://localhost:5000

# Get latest decisions file
curl http://localhost:5000/decisions | jq '.'

# Just the decisions content
curl http://localhost:5000/decisions | jq -r '.content' | head -100
```

**Expected response:**
```json
{
  "filename": "decisions_2026-05-13.md",
  "modified": 1778630861.99,
  "content": "# Trading Decisions — May 13, 2026\n\n## Market Regime: TRANSITION (-0.169)\n..."
}
```

### 3. Open Chat UI

```bash
# In browser: file:///path/to/bist-trading-system/chat.html
# Or double-click chat.html
```

**Expected behavior on startup:**
1. API key modal appears (if no key saved)
2. Enter your Anthropic API key (sk-ant-...)
3. "Yenile" button shows loading (spinning green dot)
4. After ~2 seconds, loading finishes (green checkmark)
5. Welcome screen shows

### 4. Verify Context Loaded

**Browser console (F12 → Console tab):**

```javascript
// Check if decisions are in the system prompt
if (SYSTEM_PROMPT.includes("TRADING DECISIONS")) {
  console.log("✓ Decisions loaded!");
  // Show the decisions section
  const start = SYSTEM_PROMPT.indexOf("=== TRADING DECISIONS");
  const end = SYSTEM_PROMPT.indexOf("===", start + 50);
  console.log(SYSTEM_PROMPT.substring(start, end));
} else {
  console.log("✗ Decisions not found in SYSTEM_PROMPT");
}
```

**Expected output:**
```
✓ Decisions loaded!

=== TRADING DECISIONS (decisions_2026-05-13.md) ===

# Trading Decisions — May 13, 2026

## Market Regime: TRANSITION (-0.169)
...
```

### 5. Test Chat with Decisions Context

**Ask in chat:**
```
Bugün hangi aksiyonları almalıyım?
```

**Expected response (maintainer cites decisions):**
```
Günlük kararlar:

1. TAVHL SAT @ ₺279
   - Gerekçe: TRANSITION rejimi dikkat gerektiriyor, havacılık sektörü zayıf
   - VIX yüksek (-0.424), risk-off eğilimi
   - Pozisyon -2.6%, MA20'nin 7.5% altında

2. AKSEN HOLD
   - Gerekçe: Enerji sektörü güçlü (BRENT +0.628)
   - Pozisyon +0.7%, MA20'nin +5.7% üstünde
   - Momentum uygun (RSI 65.3)

3. ENERY İZLE @ ₺9.50
   - Gerekçe: Enerji rüzgarı devam ediyor ama makro iyileşmeyi bekle
   - Hedef: ₺9.50 (0.6% kazanç potansiyeli)
   - Makro RISK_ON'a dönerseniz hızlanabilir

4. TTKOM HOLD
   - Gerekçe: Savunma sektörü TRANSITION'da koruma sağlıyor
   - Pozisyon +10.2%, güçlü teknikler (RSI 62.1)

5. KCHOL HOLD
   - Gerekçe: Diversifiye holding, sektör rotasyonu riskini yönetiyor
   - En iyi pozisyon: +12.4% P&L
   - BRENT güçlü + BIST zayıf = holding faydalı

Yeni pozisyonlara kapalı verin, tee zaman belirsizdir.
```

---

## API Endpoints Summary

After integration, your system has these endpoints:

| Endpoint | Purpose | Auto-sync |
|----------|---------|-----------|
| GET `/report` | Latest daily report | Daily after daily_update.py |
| GET `/masterplan` | Strategy document | Manual edit |
| GET `/decisions` | **New:** Latest trading decisions | Daily after daily_update.py ✨ |
| GET `/files` | List memory files | As you save |
| GET `/file?path=<name>` | Read specific memory file | As you save |

---

## Integration Flow

### Daily Workflow

1. **19:00 - Market closes**
   ```bash
   python scripts/daily_update.py --generate-report
   ```
   Generates:
   - Daily report (portfolio snapshot, signals)
   - Daily briefing JSON (for agents)
   - Macro signal (regime: TRANSITION -0.169)
   - **decisions_2026-05-13.md** ← New!

2. **19:10 - Start server**
   ```bash
   python server.py &
   ```
   API ready on http://localhost:5000

3. **19:15 - Open chat**
   - Browser: file:///path/to/chat.html
   - Auto-fetches:
     * `/report` (latest daily report)
     * `/masterplan` (strategy)
     * `/decisions` (today's decisions) ✨
   - Merges into SYSTEM_PROMPT
   - maintainer agent ready

4. **19:20 onwards - Chat**
   - Ask about today's decisions
   - Agent cites decision document
   - Actions consistent with macro regime
   - Multi-agent coherence

---

## File Locations Reference

| Purpose | File |
|---------|------|
| Decisions (today) | `agents/intelligence/decisions_2026-05-13.md` |
| Decisions (API) | `GET /decisions` → auto finds latest |
| Server code | `server.py` (port 5000) |
| Chat UI | `chat.html` |
| Decisions endpoint code | `server.py` lines 86-98 |
| Chat integration code | `chat.html` lines 551-590 |

---

## Troubleshooting

### Problem: Chat doesn't fetch decisions

**Solution:**
1. Check server is running: `curl http://localhost:5000`
2. Check endpoint works: `curl http://localhost:5000/decisions`
3. Open browser console (F12) and check for errors
4. Click "Yenile" button to retry

### Problem: SYSTEM_PROMPT doesn't include decisions

**Solution:**
1. Check `decisions_2026-05-13.md` exists in `agents/intelligence/`
2. Check filename matches pattern `decisions_*.md`
3. Refresh page in browser
4. Check browser console for fetch errors

### Problem: Decisions API returns 404

**Solution:**
1. Check directory exists: `agents/intelligence/`
2. Check file exists: `decisions_2026-05-13.md`
3. Check server.py has INTELLIGENCE_DIR and /decisions endpoint
4. Restart server: `python server.py`

---

## Code References

### server.py - /decisions endpoint
- Lines 18: `INTELLIGENCE_DIR = ROOT / "agents" / "intelligence"`
- Lines 86-98: `@app.get("/decisions")` handler
- Lines 105: Updated index() with `/decisions` endpoint

### chat.html - Decisions integration
- Lines 555: `fetch(/decisions)` added to parallel fetches
- Lines 574-577: Decisions content added to parts array
- Result: Decisions merged into SYSTEM_PROMPT on startup

### Decisions document
- Location: `agents/intelligence/decisions_2026-05-13.md`
- Size: 7.5 KB
- Format: Markdown (readable, git-friendly)
- Content: Position actions grounded in macro regime

---

## Next Steps

1. **Test the integration** (5 min above)
2. **Create tomorrow's decisions** at 19:00 with new macro signal
3. **Optional:** Automate decisions generation (see TRADING_DECISIONS_AND_API.md)
4. **Optional:** Add decision history analysis

---

**Status:** ✅ Ready to test  
**Server:** python server.py  
**Chat:** file:///path/to/chat.html  
**Endpoint:** http://localhost:5000/decisions
