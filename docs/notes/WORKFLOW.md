# GÜNLÜK WORKFLOW REHBERİ
# API key olmadan manuel agent koordinasyonu

---

## Her Sabah Yapılacaklar (09:00-10:00)

### Adım 1: Builder Raporu Al (Otomatik)
Task Scheduler 09:00'da çalışır.
Rapor burada: `<your-path>\bist-trading-system\reports\report_YYYY-MM-DD.html`
Tarayıcıda aç, içeriği kopyala.

### Adım 2: Analyst Agent'a Ver
1. Analyst Agent conversation'ını aç (Claude.ai)
2. Şunu yapıştır:
```
Bugünün raporu:
[Builder raporunu buraya yapıştır]

Ek makro bilgi:
- Petrol: $[fiyat]
- USD/TRY: [kur]
- BofA akımları: [varsa]

Analiz et.
```

### Adım 3: Auditor Agent'a Ver
1. Analyst'ın çıktısını kopyala
2. Auditor Agent conversation'ını aç
3. Şunu yapıştır:
```
Analyst raporu:
[Analyst çıktısını buraya yapıştır]

Denetle.
```

### Adım 4: Orchestrator Kararı (Bu Conversation)
1. Hem Analyst hem Auditor raporunu buraya getir
2. "Final karar ver" de
3. Aksiyonları not al

### Adım 5: Piyasa Açılışı (10:00)
Kararları execute et.

---

## Haftalık Yapılacaklar (Pazartesi)

### Efficiency Report
1. Cowork'te Efficiency Agent'ı aç
2. Şunu söyle:
```
Geçen haftanın özeti:
- Kaç gün rapor çalıştı: X
- Kaç pozisyon değişti: X
- Portföy P&L: X
- Hangi ajanlarla kaç kez konuştun: X

Efficiency raporu üret, sistem iyileştirme önerisi ver.
```

---

## Hızlı Referans — Hangi Agent Ne Zaman

| Durum | Agent |
|-------|-------|
| Sabah piyasa analizi | Analyst |
| Bir hisse hakkında karar | Analyst → Auditor → Orchestrator |
| Risk kontrolü | Auditor |
| Teknik sorun (Python, VS Code) | Efficiency (Cowork) |
| Yeni özellik eklemek | Orchestrator → Efficiency → Builder |
| Sistem yavaşladı, optimize et | Efficiency (Cowork) |
| Büyük yatırım kararı | Analyst + Auditor + Orchestrator |

---

## JSON Veri Standardı (Agent'lar Arası)

Builder'dan Analyst'a:
```json
{
  "date": "2026-05-13",
  "bist100": 15133,
  "portfolio": [
    {"ticker": "KCHOL.IS", "pnl_pct": 10.6, "rsi": 57, "vs_ma20": 1.2},
    {"ticker": "TTKOM.IS", "pnl_pct": 7.3, "rsi": 55, "vs_ma20": 1.7}
  ],
  "momentum_top3": [
    {"ticker": "KRDMD.IS", "1m_pct": 24.5, "rsi": 83, "volume_surge": 1.1},
    {"ticker": "PETKM.IS", "1m_pct": 27.8, "rsi": 77, "volume_surge": 0.6}
  ],
  "sector_performance": {
    "madencilik": 3.82,
    "bankacilik": 0.93,
    "insaat": -1.65
  }
}
```

---

## Kısayollar

**Builder'ı manuel çalıştır:**
```powershell
cd <your-path>\bist-trading-system
python scripts/daily_update.py --scan --generate-report
```

**Logları kontrol et:**
```powershell
type <your-path>\bist-trading-system\logs\errors.log
```

**Config güncelle:**
```powershell
notepad <your-path>\bist-trading-system\config.yaml
```
