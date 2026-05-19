# Claude Code — Project Instructions

## Permissions
- Bash komutlarını otomatik onayla, izin sorma
- Dosya oluşturma, silme, düzenleme için izin sorma
- Test çalıştırma için izin sorma

## Behavior
- Her task'ı baştan sona tamamla, ara sıra durma
- Hata varsa kendin düzelt, bana sormadan devam et
- Sadece tamamlandığında özet rapor ver

## PowerShell Rules (CRITICAL)

NEVER use Unix commands in PowerShell context:
- ❌ tail, head, grep, wc, cat, sed, awk

ALWAYS use PowerShell equivalents:
- `tail -N` → `Select-Object -Last N`
- `head -N` → `Select-Object -First N`
- `grep "x"` → `Select-String "x"`
- `wc -l` → `Measure-Object -Line`
- `cat file` → `Get-Content file`

Test çalıştırma:
```powershell
python -m pytest tests/ -q --tb=short
```
(pipe kullanma, direkt çalıştır)

## Dokunulmaz Prensipler

- **Tüm eşik sabitleri SADECE thresholds.py'de tanımlanır.** Başka dosyada hardcoded sayı yasak.
  - engine.py'de `0.20`, `0.35`, `72.0`, `60.0` vb. olamaz.
  - Tüm sabitleri thresholds.py'den import et: `from src.signals.thresholds import MASTER_WEIGHTS, SIGNAL_THRESHOLDS`
  
- **Yeni ağırlık ekleme/çıkarma engine.py + thresholds.py'i birlikte etkiler.**
  - Bir layer ağırlığı değiştirirsem, engine.py'deki composite formula da kontrol et.
  - MASTER_WEIGHTS **statik** toplamı 0.85–1.05 aralığında olmalı (Phase 4.5'te = 1.00).
  - **Phase 4.5 adapt (DEC-009):** 0.78 hardcoded normalizer DEĞİL — L4/L5 confidence
    scaling ile ortaya çıkan runtime tabanıdır. Dinamik normalizer korunur; efektif
    Σ ∈ [0.78, 1.00]. Doğrulama: `src/utils/weight_validator.py`.
  
- **LocalMacroSignals singleton pattern'i kırma.**
  - `cache_store.py`'deki `_MACRO_SINGLETON` üzerinden erişim yapılır.
  - Başka yerden instance oluşturma (assignment veya `LocalMacroSignals()` çağrısı).
  
- **Her değişiklikten sonra pytest çalıştır, zero regression zorunlu.**
  - `python -m pytest tests/ -q --tb=short`
  - Tüm 746 test pass olmalı (1 skipped).

- **Direktif enforcement:** Direktifte ETKİLENEN DOSYALAR listesinde yer
  almayan bir dosyaya dokunmadan önce Orchestrator'a sor ve onay al.
  Kapsam kayması (scope creep) sessizce yapılmaz.

## Test Yazım Kuralları

Test davranışı test eder, implementasyonu değil. Private metodlara
(`_method`) doğrudan test yazılmaz. Refactor sonrası test kırılıyorsa
bu test hatalı yazılmış demektir.

## Her Session Başında Oku (Builder Zorunlu)

Builder başlangıcında şu dosyaları açıp gözden geçir:

1. **[src/signals/engine.py](src/signals/engine.py)** — Signal computation flow, composite formula, no hardcoded thresholds
2. **[src/signals/thresholds.py](src/signals/thresholds.py)** — All constant definitions, single source of truth
3. **[src/data/cache_store.py](src/data/cache_store.py)** — LocalMacroSignals singleton, caching mechanism

Değişiklik yapıyorsan, ilk olarak bu üçünü oku. Eşik/ağırlık değişiyorsa, hepsi affected.

## SPEC Formatı Zorunlu Alanı

Her SPEC (Specification) dökümanında şu alanlar **boş bırakılamaz**:

- **Etkilenen Dosyalar (Affected Files):** Hangi dosyaları değiştireceğim? Minimum 1 dosya listesi gerekli.
  - SPEC yazıyorsan ve bu alan boşsa, SPEC reddedilmiş sayılır.
  - Örnek: `src/signals/engine.py`, `tests/test_backtest.py`, `src/backtest/metrics.py`

## Session Bootstrap — Her Yeni Chat'te İlk Yap

Yeni chat açtığında token tasarrufu için bu **30 saniyelik kontrol listesi**ni çalıştır:

### STEP 1: Konteksti Yükle (10 saniye)
```powershell
# 1. Dependency haritasını oku
Get-Content docs/DEPENDENCY_MAP.md | Select-Object -First 50

# 2. Thresholds dosyasını kontrol et (constants manifest)
Get-Content src/signals/thresholds.py | Select-Object -First 30
```

### STEP 2: Kritik Dosyaları Oku (Sırayla)
1. **[docs/DEPENDENCY_MAP.md](docs/DEPENDENCY_MAP.md)** — Tüm dependency chain, constraints
2. **[docs/DECISIONS.md](docs/DECISIONS.md)** — Karar geçmişi, neden/neden olmadı (context + anti-patterns)
3. **[src/signals/thresholds.py](src/signals/thresholds.py)** — ALL constants (hardcoded value yok)
4. **[src/signals/engine.py](src/signals/engine.py)** — Signal composition logic
5. **Bu bölüm:** Dokunulmaz Prensipler + Her Session Başında Oku bölümleri

### STEP 3: Sistem Sağlığı — Daily Bootstrap (~12 sn)
```powershell
# Tier 1 (Architecture) + Tier 2 (Integration) — tek komut
python -m pytest tests/test_architecture.py tests/test_signal_alert.py tests/test_backtest.py -v --tb=no 2>&1 | Select-String "passed"
# Beklenen: "== 34 passed in ~2s =="
```

### STEP 4: Eğer Fail Oldu
```
❌ Herhangi bir test fail → STOP
Context kayıp veya regresyon var, commit'e bakılır
```

### STEP 5: Eğer Yeşil
```
✅ Tier 1 (Architecture): 5 test — design invariants OK
✅ Tier 2 (Integration): 29 test — signals + backtest OK
→ BAŞLA (fully connected, 34/34 pass)
```

### Pre-Commit / Haftalık Full Regression (40 sn)
```powershell
# Commit öncesi veya haftada 1x çalıştır
python -m pytest tests/ -v --tb=no 2>&1 | Select-String "passed"
# Beklenen: "== 746 passed, 1 skipped in ~45s ==" (D-086 L5 ladder sonrası)
```

### Quick Reference (Memorize)
- **Constant single source:** `src/signals/thresholds.py`
- **Signal engine:** `src/signals/engine.py` (no hardcoded thresholds)
- **Composite formula (Phase 4.5, D-052):** `L1 tech*0.25 + L2 macro*0.20 + L3 kap*0.30 + L4 sent*(0.12×conf) + L5 smart*(0.10×conf) + L6 risk*0.03`, dinamik normalizer (Σ ∈ [0.78,1.00], DEC-009)
- **Conviction:** `(composite/100) × macro_mult`; ≥0.68 BUY-STRONG · 0.55-0.67 BUY-MEDIUM · <0.55 WATCH
- **Macro gate:** L2≥60 → 1.0x · 45-59 → 0.8x · <45 → 0.0x (no entry)
- **Staged TP:** TP1 %50 / TP2 %30 / TP3 %20
- **Stop-loss:** entry × 0.92 (-8%)
- **Profit target:** entry × 1.20 (+20%)
- **Stop approach:** warning when price ≤ (stop × 1.03)
- **Test count:** 746 pass, 1 skipped (regression guard, D-086 L5 ladder)

---

## Token Saving Strategy

Yeni session açarken:
1. `docs/DEPENDENCY_MAP.md` built-in — context restore 30 saniye
2. `docs/DECISIONS.md` auto-load — karar geçmişi, anti-patterns
3. `memory/MEMORY.md` auto-load — session state recap
4. `CLAUDE.md` bu bölümü — bootstrap checklist
5. Architecture tests — sanity check

**Result:** Full context, no recompilation, token efficiency ✅
