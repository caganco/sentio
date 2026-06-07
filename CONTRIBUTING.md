# Contributing

This is a solo research project. External contributions are not actively solicited,
but the codebase, methodology, and findings are documented publicly for transparency
and reproducibility.

---

## Running the system locally

**Requirements:** Python 3.11+

```bash
git clone https://github.com/caganco/sentio
cd sentio
pip install -r requirements.txt
cp .env.example .env   # fill in API keys (all optional for offline runs)
```

**Run the test suite:**

```bash
python -m pytest tests/ -q --tb=short
# Expected: 2,088 passed, 4 skipped (C12 golden gate — requires local data snapshot)
```

**Run the red-team example (no external data required):**

```bash
python examples/rry1008/run_part1_known_answer.py
```

**Environment variables** (see `.env.example`):
- `EVDS_API_KEY` — TCMB EVDS3 macro data (free registration at evds2.tcmb.gov.tr)
- `FMP_API_KEY` — supplementary market data
- `ANTHROPIC_API_KEY` — optional; enables the Strategist narrative layer

---

## Research discipline

Every hypothesis in this system is tested under the following constraints:

- **Pre-registration before results.** Stage-0 JSON is frozen before any backtest
  runs. The engine refuses to proceed without it. Post-hoc parameter relaxation is
  structurally prevented.
- **N≤3 measurement rule.** Each research thread is allowed at most three
  independent measurements before a verdict is recorded. Repeated testing
  without a verdict is not permitted.
- **Survivorship-bias-clean data.** Tests run on the full BIST universe including
  delisted tickers. Survivor-only analysis is not accepted as evidence.
- **Realistic costs.** Round-trip costs use quoted spreads + Kyle impact, not flat
  assumptions. The cost model is calibrated to EOD quoted spreads (D-207).

Methodology references are in [`docs/RESEARCH_REGISTRY.md`](docs/RESEARCH_REGISTRY.md)
and the engine design in [`docs/engine/OPERATOR_GUIDE.md`](docs/engine/OPERATOR_GUIDE.md).

---

## Code standards

| Tool | Config | Status |
|------|--------|--------|
| mypy | strict | configured; CI tracking |
| ruff | default + E/W rules | CI blocking |
| import-linter | contracts in `pyproject.toml` | CI blocking |
| pytest | 2,088 tests | CI blocking (zero regression) |

All constants are defined in `src/signals/thresholds.py` — no hardcoded values
elsewhere. Architecture invariants are enforced by `tests/test_architecture.py` and
run as CI Tier 1.

---

## CI tiers

Pull requests must pass all four CI tiers before merge:

1. **Tier 1 — Architecture:** import contracts, design invariants (`test_architecture.py`)
2. **Tier 2 — Integration:** signal alert, backtest, engine integration tests
3. **Lint:** ruff clean across `src/` and `tests/`
4. **Tier 3 — Full regression:** all 2,088 tests

---

## Issue reporting

Use [GitHub Issues](https://github.com/caganco/sentio/issues) to report
bugs or ask questions about methodology. For questions about BIST data sources or
research findings, reference the relevant report in `docs/research/`.
