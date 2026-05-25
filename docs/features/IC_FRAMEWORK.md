# Feature Guide: IC Framework (Information Coefficient)
**Son güncelleme:** 25 Mayıs 2026 — D-139/D-140
**Durum:** Faz 1+2 production ✅ | Faz 3 Bayesian ~Temmuz 2026 (D-141)
**Sorumlu specler:** D-139, D-140, D-141(bekliyor), D-142(bekliyor)

---

## Ne Yapar

Her sinyal layer'ının (L1-L6) ne kadar öngörü gücü olduğunu ölçer.
IC = Spearman rank correlation(sinyal skoru, gerçekleşen getiri).
Zamanla IC düşüyorsa (decay) layer'ın sinyali bozulmuş demektir.

**Uzun vadeli amaç:** IC datasına dayalı Bayesian weight update — CB-002 çözümü.

---

## Mimari

```
daily_update.py
    → ICHistoryWriter.run_daily(today)
        → ICCalculator.compute_fdr_panel()   ← BH-FDR 12 test
        → ICCalculator.compute_decay()        ← OLS slope 30/60/120d
        → ic_history.parquet                  ← append-only
```

```
data/analytics/
├── ic_history.parquet        ← IC zaman serisi (21 May'den birikyor)
├── weight_history.parquet    ← Bayesian öneri (Faz 3'te dolacak)
└── delisted_tickers.json     ← 25 BIST ticker (survivorship bias)
```

---

## Önemli Sabitler (thresholds.py)

| Sabit | Değer | Anlam |
|-------|-------|-------|
| `IC_BAYESIAN_TAU_MIN_DAYS` | 60 | Weight update için minimum OOS gün |
| `IC_INVESTABLE_MONTHS_MIN` | 6 | Dashboard "INVEST" etiketi için |
| `IC_FDR_ALPHA` | 0.10 | BH-FDR anlamlılık eşiği |
| `IC_DECAY_SLOPE_WARN` | -0.001 | Decay uyarı eşiği |
| `IC_DECAY_SLOPE_REVIEW` | -0.002 | Decay inceleme eşiği |
| `IC_NEW_LAYER_TSTAT_HURDLE` | 3.0 | Yeni layer için minimum t-stat |

---

## Nasıl İzlenir

```bash
# IC dashboard çalıştır
python src/reporting/ic_dashboard.py

# Decay durumu görüntüle (Decay30d sütunu)
# WARN → sinyal zayıflıyor
# REVIEW → sinyal ciddi şekilde bozuluyor
```

---

## Aktivasyon Takvimi

| Faz | Ne | Ne Zaman |
|-----|----|---------| 
| Faz 1+2 | IC ölçüm + decay | ✅ Production |
| Faz 3 | Bayesian weight update | ~Temmuz 2026 (60 gün OOS) |
| Faz 4 | analytics import-linter | D-141 sonrası |

**AG-001 gate:** `ENABLE_HMM_WEIGHTS=False` — 180 gün OOS + CB-013 kapalı koşulu (CB-013 artık kapalı ✅). Kasım 2026 hedef.

---

## Neye Dokunma

| Yasak | Neden |
|-------|-------|
| `IC_INVESTABLE_MONTHS_MIN`'i artırma | 6 ay the maintainer kararı (DEC-024) |
| `analytics/*.py`'den engine import | K-08 ihlali — `test_analytics_not_importing_engine` yakalar |
| `ic_history.parquet`'i silme | 21 May'den biriken OOS veri — geri getirilmez |
| Weight'leri manuel güncelleme | DEC-023: WeightCalibrator → Orchestrator onay → ayrı spec |
