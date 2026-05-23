# SPEC: Local Macro Fetcher – fetch_and_store() Implementation

## 1. Genel Bakış

Üç stub client (`TCMBClient`, `CDSClient`, `BistForeignClient`) gerçek veri kaynakları ile konekte edilecek. Her birine `fetch_and_store()` metodu eklenerek:
- Macro veri otomatik çekilecek
- Yerel cache'e yazılacak
- `daily_update.py` entry point'inde market açılmadan önce tetiklenecek

**Scope:**
- Sadece `fetch_and_store()` metodu eklemesi
- Existing `score()` ve cache metodları untouched
- Error handling: exception throw'lamaz, log + bool döndür
- Async/concurrent işlem yok – sequential, sync fetch'ler

---

## 2. Mimari Kararlar & Rationale

### 2.1 Method Return Type: `bool` (vs Exception)

**Karar:** `fetch_and_store()` → `bool` döndür (success/failure)

**Rationale:**
- Market açılış öncesi scheduler işlem – critical service downtime avoid edilmeli
- Partial veri (1 client fail, diğerleri OK) sistemin çalışmasını engellememeli
- Caller (`daily_update.py`) her client'ın status'unu log edip continue edebilir
- Exception'la fail-fast yerine graceful degradation tercih edildi

**Alternative Rejected:**
- Exception throw: Bir client fail ederse tüm update işlemi crash – 3 seri çekilemiyor

### 2.2 Error Handling: Logger + Silent Fail

**Karar:** Exception'ı catch – structured log + `False` return

**Rationale:**
- Ağ hatası, API timeout, parse error – expected edge case
- Task scheduler'a crash sıralamak yok
- Operational visibility: her failure'ın timestamp + error message'ı log'da
- Dashboard/alerting: ayrı monitoring layer log'ları parse edebilir

**Logger Format:** `logger.error(f"TCMBClient.fetch_and_store failed: {e.__class__.__name__}: {str(e)}")` + stack trace

### 2.3 Data Source Selection

#### TCMBClient – EVDS API Tercih Edildi

**Karar:** EVDS (TCMB Electronic Data Distribution System) direct API vs. scraping

**Rationale:**
- TCMB official, structured API endpoint
- JSON response → parsing reliable, no regex brittle
- Rate limit clear (header'larda documented)
- Series TP.MK.IE.BSP = Interest Expectations/Policy Rate Change – policy decision input

**Alternative Rejected:**
- Scraping TCMB.gov.tr: HTML structure değişebilir, fragile

#### CDSClient – Scraping (No JSON API)

**Karar:** `worldgovernmentbonds.com/country/turkey` scraping

**Rationale:**
- Public, reliable veri source – çoğu CDS provider'dan
- JSON API yok; HTML parse gerekli
- BeautifulSoup4 + regex – standard Python stack
- Selector brittle olabilir – version control (.selector_map in config?)

**Risk:** Site UI değişirse breaking. Mitigation: fallback veri kaynağı dokumentasyon gerekli (e.g., Bloomberg terminal, market data provider).

#### BistForeignClient – EVDS API

**Karar:** EVDS series (haftalık foreign exchange oranı) kullan

**Rationale:**
- EVDS consistently reliable (2. TCMB API client ile same infra)
- Haftalık granularity: daily rebalance'a yetmiyor, ama weekly trend – signal yeterli
- Series ID TBD (implementation phase: doğru seri confirm et)

---

## 3. Implementation Details

### 3.1 TCMBClient.fetch_and_store()

**Signature:**
```
def fetch_and_store(self) -> bool
```

**Input:**
- Env var: `EVDS_API_KEY` (must exist, no fallback)
- Series ID (hard-coded): `TP.MK.IE.BSP`
- Fixed: sonuncu 2 data point (current, previous-1)

**Process:**
1. API key'i env'den oku
2. EVDS endpoint'e GET request:
   ```
   GET https://evds2.tcmb.gov.tr/service/series/{TP.MK.IE.BSP}?startDate=YYYY-01-01&endDate=YYYY-MM-DD&type=json
   ```
3. Response parse: `data.observations` – sorted by date (descending), latest 2 fetch
4. Current vs previous-1 karşılaştır:
   - `current < previous-1` → "cut" (interest cut)
   - `current > previous-1` → "hike" (rate hike)
   - `current == previous-1` → "hold"
5. `self.cache.store_tcmb(decision="cut"|"hike"|"hold", value=current, timestamp=now)` çağır
6. Exception'ı catch, log, return `False`; success → `True`

**Edge Cases:**
- API key missing: log `"EVDS_API_KEY env var not set"` → `False`
- API HTTP error (401, 403, 5xx): log status + body → `False`
- Timeout (5s default): log + `False`
- Response parse error (missing `observations`): log + `False`
- < 2 data point'in response: log `"insufficient historical data"` → `False` (can't compare)
- API rate limit hit (check response header): log + `False`

**Dependencies:**
- `requests` library
- `self.cache` object (existing)
- Env: `EVDS_API_KEY`

**Test Criteria:**
- ✓ Valid API key + normal response → `True`, cache store verified
- ✓ Invalid/missing API key → `False`, error logged
- ✓ API 500 error → `False`, logged
- ✓ Timeout → `False`, logged
- ✓ Malformed JSON → `False`, logged
- ✓ Hike/cut/hold decision doğru encode ediliyor → cache'te verify

---

### 3.2 CDSClient.fetch_and_store()

**Signature:**
```
def fetch_and_store(self) -> bool
```

**Input:**
- URL (hard-coded): `https://www.worldgovernmentbonds.com/country/turkey/`
- User-Agent header (scraper detection avoid, standard header set)

**Process:**
1. GET request URL'ye (timeout: 10s)
2. HTML parse (BeautifulSoup)
3. CSS selector/regex ile CDS bps değerini extract:
   - Selector: TBD implementation phase – site structure'ı inspect
   - Target: "CDS 5Y" bps value (numeric parse)
4. `self.cache.store_cds(bps_value=float, timestamp=now)` çağır
5. Exception catch, log, return `False`; success → `True`

**Edge Cases:**
- Network error (DNS, connection refused): log + `False`
- Timeout (10s exceeded): log + `False`
- HTTP non-200: log status → `False`
- Selector not found / page structure changed: log + `False`
- CDS value parse error (non-numeric): log + `False`
- Stale/cached page served: no indicator – risk (mitigation: cache TTL + freshness check)

**Dependencies:**
- `requests`, `beautifulsoup4` libraries
- Site structure knowledge (selector/regex fragile)
- `self.cache` object

**Test Criteria:**
- ✓ Valid page + CDS parse → `True`, numeric value stored
- ✓ Network error → `False`, logged
- ✓ Timeout → `False`, logged
- ✓ Page structure changed (selector mismatch) → `False`, logged
- ✓ Non-numeric value in CDS field → `False`, logged
- ✓ Cache store call validated

**Risk:** HIGH – scraper brittle. Mitigation: 
- Selector'ları config file'a externalize
- Monthly validation: parsed value range check (e.g., 0-1000 bps realistic)
- Fallback source (Bloomberg, CME) dokumentasyon yap

---

### 3.3 BistForeignClient.fetch_and_store()

**Signature:**
```
def fetch_and_store(self) -> bool
```

**Input:**
- Env var: `EVDS_API_KEY` (same as TCMBClient)
- Series ID (hard-coded): `TP.DNYBNK.ADBK` (TBD: confirm correct series in implementation)
- Frequency: weekly (automatic EVDS parameter)

**Process:**
1. API key'i env'den oku
2. EVDS endpoint'e GET request:
   ```
   GET https://evds2.tcmb.gov.tr/service/series/{SERIES_ID}?startDate=YYYY-01-01&endDate=YYYY-MM-DD&frequency=weekly&type=json
   ```
3. Response parse: latest week's data point
4. Value store:
   - `self.cache.store_bist_foreign(value=float, week_end_date=date, timestamp=now)`
5. Exception catch, log, return `False`; success → `True`

**Edge Cases:**
- API key missing: log + `False`
- HTTP error (401, 5xx): log + `False`
- Timeout: log + `False`
- Parse error: log + `False`
- < 1 data point: log "no recent weekly data" + `False`
- Series ID wrong/deprecated: API 400 error – log + `False`

**Dependencies:**
- `requests` library
- `self.cache` object
- Env: `EVDS_API_KEY`
- **TBD:** Correct EVDS series ID for foreign bank transaction ratio (needs TCMB doc confirmation)

**Test Criteria:**
- ✓ Valid API key + weekly data available → `True`, numeric stored
- ✓ Missing API key → `False`
- ✓ API error → `False`, logged
- ✓ Timeout → `False`, logged
- ✓ Cache store call verified

---

## 4. Integration Point: daily_update.py

**Location:** `scripts/daily_update.py` (entry point)

**Caller Logic:**
```python
# Pseudo-code
def daily_update():
    # Pre-market (< 08:30 UTC+3)
    tcmb_ok = tcmb_client.fetch_and_store()
    cds_ok = cds_client.fetch_and_store()
    bist_ok = bist_foreign_client.fetch_and_store()
    
    logger.info(f"Daily macro fetch: TCMB={tcmb_ok}, CDS={cds_ok}, BIST={bist_ok}")
    
    # Continue regardless of individual failures
    # (signal computation uses cache, which may be stale if fetch failed)
    
    # ... rest of daily update
```

**Timing:** Must run before market open (~08:30 Turkey time). Scheduler/cron configuration OUTSIDE this SPEC.

**Error Handling:** All-or-nothing NOT required. 1-2 failures don't block rest of pipeline.

---

## 5. Test Kriterleri

### Unit Tests

**TCMBClient.fetch_and_store():**
- `test_fetch_and_store_valid_api_key()` – mock EVDS response, verify cache call, return `True`
- `test_fetch_and_store_missing_api_key()` – no env var, return `False`, error logged
- `test_fetch_and_store_api_error()` – mock 500 response, return `False`
- `test_fetch_and_store_timeout()` – mock timeout exception, return `False`
- `test_fetch_and_store_parse_error()` – mock malformed JSON, return `False`
- `test_fetch_and_store_hike_decision()` – current > prev-1, verify "hike" in cache
- `test_fetch_and_store_cut_decision()` – current < prev-1, verify "cut" in cache
- `test_fetch_and_store_hold_decision()` – current == prev-1, verify "hold" in cache

**CDSClient.fetch_and_store():**
- `test_fetch_and_store_valid_page()` – mock HTML response, parse CDS, return `True`
- `test_fetch_and_store_network_error()` – mock connection error, return `False`
- `test_fetch_and_store_timeout()` – mock timeout, return `False`
- `test_fetch_and_store_selector_not_found()` – mock page (stale structure), return `False`
- `test_fetch_and_store_invalid_bps_value()` – mock page with non-numeric CDS, return `False`
- `test_fetch_and_store_valid_bps_value()` – verify numeric stored in cache

**BistForeignClient.fetch_and_store():**
- `test_fetch_and_store_valid_weekly_data()` – mock EVDS response, return `True`
- `test_fetch_and_store_missing_api_key()` – return `False`
- `test_fetch_and_store_api_error()` – mock 5xx, return `False`
- `test_fetch_and_store_timeout()` – return `False`
- `test_fetch_and_store_parse_error()` – malformed JSON, return `False`

### Integration Tests

- `test_daily_update_all_clients_success()` – all 3 clients return `True`, log verified
- `test_daily_update_one_client_fails()` – 1 fail, 2 OK, pipeline continues
- `test_daily_update_all_clients_fail()` – all fail, log warnings, no exception thrown
- `test_daily_update_cache_consistency()` – after fetch, cache lookup confirms stored values

---

## 6. Dependencies & Risks

### Dependencies

| Dependency | Type | Mitigation |
|-----------|------|-----------|
| `EVDS_API_KEY` env var | External config | Document requirement, validate at startup |
| TCMB EVDS API availability | Network | ⚠️ **Currently unavailable (2026-05-14)**: All `/service/evds/*` endpoints return HTML SPA instead of JSON. Fallback YAML data active. Monitor for API stabilization. |
| `worldgovernmentbonds.com` structure | Web scraping | Selector mapping in config, monthly validation |
| `requests`, `beautifulsoup4` | Python libs | Already in requirements.txt (assumed) |
| Cache layer (`self.cache.*`) | Internal | Existing, no changes required |

### Risks

| Risk | Severity | Mitigation |
|-----|----------|-----------|
| **EVDS API rate limit hit** | MEDIUM | Log + graceful fail; monitor rate limit headers |
| **CDS selector breaks** (site UI change) | HIGH | Externalize selector, fallback source strategy |
| **API key rotation** (security) | MEDIUM | Document rotation procedure, test with "old key expired" scenario |
| **Timezone issues** (cache timestamp) | LOW | All timestamps UTC, document conversion in cache layer |
| **Network latency** (10s timeout too short?) | MEDIUM | Monitor actual fetch times; adjust timeout if > 8s p95 |
| **Partial data stale cache** (1 client fails) | LOW | Document that stale data used if fetch fails; provide TTL cache invalidation strategy |

---

## 7. Summary

| Component | Method | Status |
|-----------|--------|--------|
| TCMBClient | `fetch_and_store()` | **SPEC'd** – EVDS API – policy decision (hike/cut/hold) |
| CDSClient | `fetch_and_store()` | **SPEC'd** – Web scrape CDS bps (risk: brittle) |
| BistForeignClient | `fetch_and_store()` | **SPEC'd** – EVDS API weekly foreign exchange |
| daily_update.py | Caller integration | **SPEC'd** – pre-market macro fetch, graceful error handling |

**Next Step:** Builder implements all 3 clients + integration following this SPEC. No code deviation; all edge cases covered above.

---

**SPEC Owner:** Senior Architect  
**Date:** 2026-05-14  
**Status:** Ready for Implementation
