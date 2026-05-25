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
  - Tüm testler pass olmalı (regresyon kabul edilmez). Güncel sayı için:
    `python -m pytest tests/ -q | tail -3`

- **Direktif enforcement:** Direktifte ETKİLENEN DOSYALAR listesinde yer
  almayan bir dosyaya dokunmadan önce Orchestrator'a sor ve onay al.
  Kapsam kayması (scope creep) sessizce yapılmaz.

## Branch Workflow

- **Her direktif kendi branch'inde geliştirilir:** `feature/d{N}-{kisa-isim}`
  - Örnek: `feature/d117-pyproject-merge`, `feature/d113-kap-signature-fix`
  - `{N}` direktif numarası (D-XXX) ile eşleşir, `{kisa-isim}` kebab-case.

- **Master'a doğrudan commit YASAK.** Tüm değişiklik PR (pull request) üzerinden
  merge edilir. `master` korunan daldır.

- **Merge ön-koşulları — İKİSİ DE zorunlu:**
  1. **pytest yeşil:** `python -m pytest tests/ -q --tb=short` → tamamen geçer
     (regresyon kabul edilmez; güncel sayı: `python -m pytest tests/ -q | tail -3`).
  2. **Cagan onayı:** PR review onaylanmadan merge edilmez.

- **Conflict → Orchestrator'a eskalasyon.** Builder, `master` ile çakışan bir
  merge ile karşılaşırsa conflict'i sessizce çözmez; Orchestrator'a bildirir
  ve çözüm kararını ona bırakır. (Direktif enforcement prensibinin uzantısı.)

- **CI hizalaması:** PR açıldığında [.github/workflows/ci.yml](.github/workflows/ci.yml)
  otomatik koşar — sırayla architecture → integration → lint → full-regression.
  CI tier'ları yeşil olmadan merge edilmez. PR şablonu:
  [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md).
  Operasyonel arıza kurtarması: [docs/RUNBOOK.md](docs/RUNBOOK.md).

## MULTI-INSTANCE BUILDER KURALLARI

**PARALEL DİREKTİF KURALI (Orchestrator zorunlu):**
Yeni direktif vermeden önce ETKİLENEN DOSYALAR listesi kontrol edilir.
Aktif direktiflerle aynı dosyaya dokunan yeni direktif → sırayla ver, paralel değil.
İhlal: aynı dosyaya 2 Builder aynı anda dokunursa shared working tree çakışır.

## BUILDER PR KURALI (Zorunlu)

Her direktif tamamlandığında Builder şunu söyler:
  Branch: feature/d-XXX
  Commit: abc1234
  PR açıyorum...
  PR #XX açıldı: [URL]

Builder push + PR açma işlemini kendisi yapar.
Cagan sadece merge komutunu çalıştırır:
  gh pr merge XX --merge

Merge conflict çıkarsa Builder çözer, Cagan görmez.
Cagan terminal açmaz — sadece merge komutunu yapıştırır.

PARALEL BUILDER ÇAKIŞMA KURALI:
- Her Builder kendi feature branch'inde çalışır
- Master'a doğrudan commit yasak
- PR olmadan merge yasak

## PARALEL CALISMA KURALI (AYRI CLONE'LAR)

Her Builder kendi BAGIMSIZ clone'unda calisir (tam izolasyon, ayri .git):
- Builder 1: C:\Users\cagan\bist-clone-builder1
- Builder 2: C:\Users\cagan\bist-clone-builder2
- Builder 3: C:\Users\cagan\bist-clone-builder3

Her clone bagimsizdir; biri branch degistirince digeri etkilenmez
(eski paylasimli-worktree cakismalari artik imkansiz).

Clone'da yeni is — SIRADA YAP (atlamak stale koddan branch açar):
  git checkout master
  git pull origin master        # ← ZORUNLU: en güncel master'dan başla
  git checkout -b feature/d-XXX
  ... geliştir ...
  git push origin feature/d-XXX
  gh pr create ...

Ana repo (bist-trading-system) sadece Cagan: merge, PR review.
Research raporu (RR-XXX) da clone'dan commit edilir — ana repo'dan değil.

master KORUMALI: direct push + force-push reddedilir; merge icin
PR + yesil CI (Tier 1/2/3 + Ruff) zorunlu. Admin dahil kimse master'a
dogrudan yazamaz.

## Test Yazım Kuralları

Test davranışı test eder, implementasyonu değil. Private metodlara
(`_method`) doğrudan test yazılmaz. Refactor sonrası test kırılıyorsa
bu test hatalı yazılmış demektir.

## TEST ÇALIŞTIRMA

**Üç katmanlı strateji — her katman farklı amaca hizmet eder:**

**Katman 1 — Geliştirme sırasında (her değişiklik sonrası):**
```powershell
python -m pytest tests/test_ETKILENEN.py -q
```
Sadece dokunulan modülle ilgili test — hızlı feedback (<10sn).

**Katman 2 — Her commit'te (otomatik, Builder müdahalesi gerekmez):**
Pre-commit hook Tier1 (Architecture) + Tier2 (Integration) + Ruff'ı çalıştırır.
Builder ayrıca çalıştırmaz — hook halleder.

**Katman 3 — Full regression:**
- **Basit direktif** (1–3 dosya, izole değişiklik): CI'a bırak, Builder çalıştırmaz.
  CI merge blocker — yeşil olmadan merge edilemez, güvenlik ağı var.
- **Karmaşık direktif** (5+ dosya, cross-module, mimari değişiklik): Builder PR öncesi çalıştırır:
  ```powershell
  python -m pytest tests/ -q --tb=short
  ```
  Neden: CI'da hata çıkınca yeni commit + yeni CI döngüsü gerekir (ekstra 3–5dk + fail geçmişi).

**Özet kural:**
```
geliştirme  → pytest tests/test_xxx.py          (sen çalıştır)
commit      → pre-commit hook                   (otomatik)
PR — basit  → CI yeterli                        (sen çalıştırma)
PR — karmaşık → pytest tests/ -q --tb=short    (sen çalıştır)
merge       → CI yeşil zorunlu                  (otomatik blocker)
```

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

## RESEARCH REGISTRY (D-122)

- **Her yeni SPEC/direktif, ilgili RR-XXX raporlarına `§section_number` ile referans vermek zorundadır.**
  - Ham research raporları [`docs/research/`](docs/research/) altında **kalıcıdır** (silinmez).
  - Master index: [`docs/RESEARCH_REGISTRY.md`](docs/RESEARCH_REGISTRY.md) — ID / başlık / tarih / bağlı CB-SPEC / status.
  - Örnek: bir SPEC L5 mimarisini değiştiriyorsa → "Dayanak: RR-001 §4" satırı zorunlu.
  - CB ↔ RR eşlemesi RESEARCH_REGISTRY.md'de tutulur (örn. CB-002 → RR-003 §3, CB-010 → RR-003 §1-2/§4).

- **Yeni RR dosyası eklendiğinde RESEARCH_REGISTRY.md ZORUNLU güncellenir.**
  - `docs/research/RR-XXX-{isim}.md` → PR açılmadan önce `docs/RESEARCH_REGISTRY.md`'ye satır eklenir.
  - Status başlangıçta `⏳ Uygulanmadı`; direktife dönüştüğünde `✅ Applied` + D-XXX yazılır.
  - Registry güncellemesi RR commit'iyle aynı branch'te olur — ayrı PR açılmaz.

## Session Bootstrap — Her Yeni Chat'te İlk Yap

Yeni chat açtığında token tasarrufu için bu **30 saniyelik kontrol listesi**ni çalıştır:

### STEP 1: Konteksti Yükle (10 saniye)
```powershell
# Thresholds dosyasını kontrol et (constants manifest — tek doğru kaynak)
Get-Content src/signals/thresholds.py | Select-Object -First 30
```

### STEP 2: Kritik Dosyaları Oku (Sırayla)
1. **[docs/DECISIONS.md](docs/DECISIONS.md)** — Karar geçmişi, neden/neden olmadı (context + anti-patterns)
2. **[src/signals/thresholds.py](src/signals/thresholds.py)** — ALL constants (hardcoded value yok)
3. **[src/signals/engine.py](src/signals/engine.py)** — Signal composition logic
4. **[tests/test_architecture.py](tests/test_architecture.py)** — design invariant'ları (executable, CI-enforced)
5. **[FEATURE_INDEX.md](FEATURE_INDEX.md)** — aktif feature'lar, faz durumu, neye dokunma özeti
   (Büyük direktif vermeden önce ilgili `docs/features/FEATURE_NAME.md` de okunur)
6. **Bu bölüm:** Dokunulmaz Prensipler + Her Session Başında Oku bölümleri

### STEP 3: Sistem Sağlığı — Daily Bootstrap (~12 sn)
```powershell
# Tier 1 (Architecture) + Tier 2 (Integration) — tek komut
python -m pytest tests/test_architecture.py tests/test_signal_alert.py tests/test_backtest.py -v --tb=no 2>&1 | Select-String "passed"
# Tier 1 (Architecture) + Tier 2 (Integration) tümü pass olmalı
```

### STEP 4: Eğer Fail Oldu
```
❌ Herhangi bir test fail → STOP
Context kayıp veya regresyon var, commit'e bakılır
```

### STEP 5: Eğer Yeşil
```
✅ Tier 1 (Architecture): design invariants OK
✅ Tier 2 (Integration): signals + backtest OK
→ BAŞLA (fully connected)
```

### Pre-Commit / Haftalık Full Regression (40 sn)
```powershell
# Commit öncesi veya haftada 1x çalıştır
python -m pytest tests/ -q | tail -3
# Tümü pass + sıfır regresyon olmalı (güncel sayıyı bu komut gösterir)
```

### Quick Reference (Memorize)
- **Constant single source:** `src/signals/thresholds.py`
- **Signal engine:** `src/signals/engine.py` (no hardcoded thresholds)
- **Composite formula (Phase 4.5, D-052):** `L1 tech*0.25 + L2 macro*0.20 + L3 kap*0.30 + L4 sent*(0.12×conf) + L5 smart*(0.10×conf) + L6 risk*0.03`, dinamik normalizer (Σ ∈ [0.78,1.00], DEC-009)
- **Conviction:** `(composite/100) × macro_mult`; ≥0.68 BUY-STRONG · 0.55-0.67 BUY-MEDIUM · <0.55 WATCH
- **Macro gate:** L2-step soft scaling × CDS overlay + hard-exits (CB-002); tek kaynak `macro_regime_gate.py`
- **Staged TP:** TP1 %50 / TP2 %30 / TP3 %20
- **Stop-loss:** entry × 0.92 (-8%)
- **Profit target:** entry × 1.20 (+20%)
- **Stop approach:** warning when price ≤ (stop × 1.03)
- **Test count:** güncel sayı → `python -m pytest tests/ -q | tail -3` (sıfır regresyon zorunlu)

---

## Token Saving Strategy

Yeni session açarken:
1. `src/signals/thresholds.py` — sabitlerin tek kaynağı (context restore)
2. `docs/DECISIONS.md` auto-load — karar geçmişi, anti-patterns
3. `memory/MEMORY.md` auto-load — session state recap
4. `CLAUDE.md` bu bölümü — bootstrap checklist
5. Architecture tests — sanity check

**Result:** Full context, no recompilation, token efficiency ✅
