# YOL 2 — Reusable-vs-Yeni Haritası (D-190)

**Tarih:** 1 Haziran 2026 — D-190 envanter  
**Dayanak:** SPEC_YOL2.md v3.0 + kod-gerçeği doğrulama (D-190)  
**Kural:** Kod-gerçeği > strateji-varsayımı (DEC-039). "Şu çalışıyor sanıyordum ama yok" bulguları buraya yazılır.

---

## Reusable-vs-Yeni Tablosu (SPEC_YOL2 Katmanlarına)

| Katman | SPEC_YOL2 Hedef | Mevcut Kod | Durum | Notlar |
|--------|----------------|-----------|-------|--------|
| **K0 Maliyet/Vergi** | Komisyon + vergi tam modeli | `src/risk/transaction_cost.py` | KISMI REUSABLE | Komisyon tier A/B/C + bid-ask var. **Vergi-katmanı YOK** → YENİ yazılmalı. |
| **K1 Risk-Prim Zemini** | Statik maruziyet zeminini ölç (equity/TLREF) | `src/screening/exposure_*.py` (D-187) | REUSABLE | Veri pipeline (`exposure_data.py`) + metrikler REUSABLE. Sonuç: rejim-timing marjinal → statik zemin kullan. |
| **K2 Faktör-Tilt** | Quality tilt (kasıtlı-mütevazı; momentum DIŞLANDI) | `src/screening/factors.py` (RS, lowvol, P/B, EV/EBITDA) | KISMI REUSABLE | value/lowvol REUSABLE. **Momentum kasıtlı dışlandı (Yol 2 kararı).** Quality faktörü (ROE/ROA/gross-margin) **YENİ** gerekli. |
| **K3 İllikidite/Contrarian** | Amihud/küçük-lot premium + short-term reversal | Yok | YENİ | Design-flagged (CRITIC_BACKLOG); hiç kod yok. Amihud illikidite + reversal anomalisi tamamen yeni. |
| **K4 İnsan-Testi** | Forward-recorder ile gerçek-dünya veri birikimi | `src/screening/event_forward_recorder.py` (D-188) | REUSABLE PATTERN | Mimari REUSABLE (look-ahead-free append-only). `data/event_logs/` henüz YOK (ilk `capture_once()` çalışınca auto-mkdir). |
| **Execution (Fikir A)** | Disiplinli giriş/çıkış mekaniği | `src/order_engine/staged_exit_manager.py` | KISMI | Sadece çıkış merdiveni (TP1/TP2/TP3). **Canlı broker entegrasyonu YOK** → YENİ. Backtest motoru simülasyon-only. |

---

## D-188 Forward-Recorder Durum Raporu

| Kriter | Durum |
|--------|-------|
| Kod tamamlandı mı? | ✅ `src/screening/event_forward_recorder.py` (300+ satır) |
| Giriş noktası | ✅ `scripts/event_forward_capture.py` (thin wrapper) |
| `data/event_logs/` var mı? | ❌ HENÜZ YOK — ilk `capture_once()` çalışınca auto-mkdir |
| Scheduler/otomatik çalışma | ❌ BAĞLI DEĞİL — the maintainer ~haftalık `scripts/event_forward_capture.py` ile elle |
| Canlı sinyal motoruna bağlantı | ❌ YOK (izole; engine/conviction import etmiyor — kasıtlı) |
| Veri birikimini başlatmak için | `python scripts/event_forward_capture.py` — bir kez çalıştırmak yeterli |

**Öneri:** `data/event_logs/` dizinini başlatmak için the maintainer'ın bir kez scripti elle çalıştırması gerekiyor. İlk çalışma sonrası haftalık rutin oluşturulabilir.

---

## Kayıp / YENİ Gereken Bileşenler Özeti

1. **Vergi-katmanı** (K0) — Türk hisse alım-satım vergileri (Damga vergisi vb.)
2. **Quality faktörü** (K2) — ROE, ROA, Gross Margin cross-sectional rank  
3. **İllikidite faktörü** (K3) — Amihud (|R|/TurnoverTL), rolling illiquidity ratio
4. **Reversal** (K3) — Short-term reversal anomalisi (1-4 hafta)
5. **Canlı broker** (Execution) — Gerçek order placement (şu an backtest-only)

---

## Strangler Notu

`src/screening/trend_*.py`, `exposure_*.py`, `event_*.py`, `factor_ic_*.py` ve
`src/signals/engine.py` (composite) **SILINMEZ** — pivot=evrim, git-history korunur.
Yeni Yol 2 modülleri bunların yanında inşa edilir (strangler pattern).
