# DEC-013 — L5 Progressive Confidence Ramp

**Tarih:** 2026-05-19
**Spec:** D-086
**Status:** Implemented

## Karar

L5 confidence flat 0.8 yerine üç fazlı ladder:

- Day 1–9:   confidence = 0.0
- Day 10–19: confidence = 0.5 (momentum-only faz)
- Day 20+:   confidence = 0.8 (full composite)

## Gerekçe

DEC-009 emergent normalizer mantığıyla tutarlı.
Olgunlaşmamış sinyal düşük confidence ile katkı yapar.
Day 10-19 fazında percentile context yok — 0.5 ile gir.

## Etkilenen Dosyalar

- src/signals/engine.py
- src/signals/layers/smart_money_layer.py
