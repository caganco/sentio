# Operasyonel Runbook — BIST Trading System

Üretim/günlük operasyonda arıza anında **ne yapılacağı**. Her senaryo:
**Belirti → Teşhis → Kurtarma** sırasıyla. Komutlar PowerShell içindir.

İlgili dokümanlar: [PRE_COMMIT_SETUP.md](PRE_COMMIT_SETUP.md) ·
[SIGNAL_ALERT_USAGE.md](SIGNAL_ALERT_USAGE.md) · [DEPENDENCY_MAP.md](DEPENDENCY_MAP.md)

---

## 1. `daily_update.py` fail — Günlük rapor üretilmiyor / bozuk

**Belirti**
- `reports/report_{tarih}.md` hiç oluşmadı, **veya**
- Rapor yanlış formatta: `## Macro Snapshot` ve `## STRATEGIST NOTES` bölümleri eksik
  (yalnızca momentum tablosu var). Bu, pipeline'ın `_write_daily_report()`
  (son adım) öncesinde çöktüğünün işaretidir.
- `agents/intelligence/daily_briefing.json` güncel tarihte değil.

**Teşhis**
```powershell
# Son hataları gör
Get-Content logs/errors.log -Tail 40

# Manuel çalıştır, tam traceback'i yakala
python scripts/daily_update.py --scan --generate-report

# briefing.json güncel mi?
Get-Content agents/intelligence/daily_briefing.json | Select-String '"date"' | Select-Object -First 1
```

**Kurtarma**
1. Traceback'teki **uncaught exception**'ı bul. En sık sebep: bir fonksiyonun
   imza/şema kayması (örn. bir çağıran eski kwarg ile çağırıyor → `TypeError`).
   Pipeline'ın çoğu adımı `try/except` ile graceful; çöküyorsa sarmalanmamış
   bir çağrı vardır.
2. Düzelt → yeniden çalıştır → `report_{tarih}.md` içinde Macro Snapshot +
   Strategist Notes göründüğünü ve `daily_briefing.json` tarihinin bugün
   olduğunu doğrula.
3. Regresyon kontrolü: `python -m pytest tests/ -q --tb=short`.

---

## 2. OS_STATE staleness — Durum dosyası eskimiş

**Belirti**
- `OS_STATE.md` saatlerce güncellenmemiş. `OSStateManager.check_staleness()`
  döndürür: **>24h → WARNING**, **>48h → CRITICAL**.
- Normalde `scripts/daily_update.py` her ~6 saatte bir `update_metadata()` çağırır.

**Teşhis**
```powershell
# OS_STATE son güncelleme damgası
Get-Content OS_STATE.md | Select-String "auto-updated|updated" | Select-Object -First 3

# Zamanlanmış görev kayıtlı/çalışıyor mu?
python scripts/setup_scheduler.py query
```

**Kurtarma**
1. Scheduler kayıtlı değilse oluştur: `python scripts/setup_scheduler.py create`.
2. Manuel tetikle:
   ```powershell
   python -c "from src.utils.os_state_manager import OSStateManager; OSStateManager().update_metadata()"
   ```
   veya tam pipeline: `python scripts/daily_update.py --scan --generate-report`.
3. `check_staleness()` artık `None` (taze) döndürmeli.

---

## 3. KAP scraper down — Bildirim kaynağı erişilemez

**Belirti**
- `logs/errors.log`'da tekrarlayan `src.scrapers.kap_scraper: Invalid JSON` /
  `Request failed` satırları.
- Rapor "KAP News 0 item" gösteriyor.

**Teşhis**
- Fallback zinciri çalışıyor mu? Sıra: **`kap_api` (birincil) → Google News RSS
  (`gnews`) fallback**. `kap_api` başarısızsa rapor "via gnews" yazmalı.
- Pipeline KAP hatasında **graceful boş liste** ile devam etmeli; raporun geri
  kalanını (Macro Snapshot + Strategist) öldürmemeli.

**Kurtarma**
- KAP API geçici/kalıcı down ise **manuel aksiyon gerekmez**: `gnews` fallback
  otomatik devreye girer, `fetch_kap_news_full()` çağrısı `try/except` ile
  sarılıdır → rapor bütünlüğü korunur.
- Hem `kap_api` hem `gnews` susarsa: ağ/DNS kontrol et; KAP haberi olmadan
  rapor yine de tam üretilir (yalnızca KAP bölümü boş kalır).

---

## 4. Signal alerting susarsa — Stop-loss / drawdown uyarıları gelmiyor

**Kontrol listesi** (sırayla)
- [ ] `src/portfolio/monitor.py` günlük pipeline'da çağrılıyor mu
      (`check_portfolio_alerts` / stop-loss approach).
- [ ] Eşikler doğru mu: `src/signals/thresholds.py` →
      `STOP_APPROACH_BUFFER` (0.03), `EXIT_STOP_LOSS` (0.92),
      `EXIT_PROFIT_TARGET` (1.20). Tüm sabitler yalnızca burada tanımlı.
- [ ] Pozisyon fiyatları güncel mi: `get_prices()` taze veri döndürüyor mu,
      yoksa son fiyat eski mi (uyarı tetiklenmez).
- [ ] `agents/intelligence/daily_briefing.json` içindeki `alerts` dizisi /
      her pozisyonun `alerts` alanı dolu mu.
- [ ] Format/kullanım: [SIGNAL_ALERT_USAGE.md](SIGNAL_ALERT_USAGE.md)
      (ACTION/PRICE/DEADLINE/OVERRIDE alanları).
- [ ] Drawdown circuit breaker: `logs` içinde "Drawdown alerts" satırı var mı.

**Kurtarma**
- Fiyat eskiyse veri fetch'ini yenile (`daily_update.py`).
- Eşik yanlışsa yalnızca `thresholds.py`'de düzelt (başka dosyada hardcoded sayı yasak).
- Monitor çağrılmıyorsa pipeline akışını ve `daily_briefing.json` üretimini doğrula.
