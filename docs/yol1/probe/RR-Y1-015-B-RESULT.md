# RR-Y1-015-B — PEAD İllikit-Dilim Harvest-Fizibilite Probu — Sonuç

> RR-Y1-015 (negatif-bilgi registry + mezarlık konsolidasyonu) **eklentisi**.
> Fizibilite probu — Stage-0 ölçümü DEĞİL, edge-testi DEĞİL, mezar-açma/diriltme DEĞİL.
> Performans-metriği **SIFIR** (CAR / getiri / drift-büyüklüğü / Sharpe / t-istatistiği
> HESAPLANMADI). Motor + maliyet-modeli **READ-ONLY** (src/engine + realistic_cost'a
> sıfır-yazım). Stage-0 kararı / graveyard-kaydı ayrı bir değerlendirme adımıdır ve bu
> raporun kapsamı dışındadır.

## Bağlam ve Tek Soru

RR-Y1-014 (PEAD Stage-0) yüksek-SUE-tercile long-bacağını BIST **likit** evreninde ölçtü
→ KEEP-BAR **FAIL** (tam-panel NW-t −0.029, gross ~sıfır). Ölçüm ön-kayıtlı olarak
SADECE likit dilimi kapsadı; SUE-tanımlı olayların ~%81'i likit-evren dışındaydı ve
"harvest-edilemez olduğu için ölçüm-evreni dışında" diye **ön-deklare-dışlanmıştı**.

Bu prob o ön-deklare-dışlamayı **niceler**: illikit tamamlayıcı gerçekten harvest-edilemez
mi? Soru yalnızca **veri/işlem-fizibilitesidir** — performans değil.

## Olay-Seti Bölmesi

| Aşama | N |
|---|---|
| fy2019–2025 olay-penceresi | 11.373 |
| SUE-tanımlı (mktval-ölçekli, donmuş RR-Y1-014 §3 formu; ≥8-çeyrek geçmiş) | 7.890 |
| + gün-damgalı (RR-Y1-013-B T+2) | 7.620 |
| + giriş panel-takviminde & fiyat-panelinde | 7.594 |
| **likit @D0** (RR-Y1-014 ölçüm-evreni) | **1.473** |
| **illikit @D0** (bu probun hedefi) | **6.121 (%80,6)** |

Likidite tanımı = motor `liquid_names` (recon B7; RR-Y1-008 parite): trailing-63g medyan
işlem-değeri ≥ 10M TL, asof = duyuru-günü D0 (point-in-time). İllikit-pay %80,6 →
RR-Y1-013/014'teki "%81 likidite-dışlama" sayısının birebir doğrulaması.

## Üç Kapı

### H1 — COST-WALL (event-hold tek round-trip) → **CONDITIONAL**

D-207 `round_trip_cost` (Roll close-only spread + Kyle √-impact + yeniden-ölçekli
tier-floor), girişte (T+2) bilinen bilgiyle PIT; emir-değeri 20.000 TL/pozisyon (donmuş
D-204, 300K/top-15). Panel close-only → quoted-spread yok (kaynak roll/tier).
Event-hold = **TEK** round-trip / 60-gün (RR-Y1-014'ün günlük-tercile-churn'ü DEĞİL).

| | İllikit (n=6.110) | Likit-taban (n=1.473) |
|---|---|---|
| round-trip medyan | **%2,27** | %1,13 |
| p25 / p75 | %1,06 / %4,16 | %0,31 / %2,71 |
| p90 | **%6,54** | %4,07 |
| ortalama (kuyruk) | **%13,87** | %1,69 |
| emir/ADV medyan · p90 | %1,81 · **%22,8** | %0,07 · %0,17 |

İllikit/likit medyan oranı **2,0×**. Bar (yapısal/dış-referans, ölçülen-edge'e tunlu
DEĞİL): PASS < %1,5 · FAIL > %4,0 → medyan %2,27 **CONDITIONAL**.

**Yorum:** Bu bir KNOCKOUT değil, bir maliyet-**KAPISI**. Medyan illikit isim, 60-gün
event-hold long-bacağının net-pozitif olması için **>%2,27 gross drift** gerektirir;
p75+ isimler %4+; kuyruk fiilen **alınamaz** (ortalama %13,9 Kyle-impact-domine; ince
isimde 20K'lık emir günlük ADV'nin ~%23'ü). RR-Y1-014 LİKİT gross'u zaten ~sıfır ölçtü
(decay-karşı-prior); illikit gross için POZİTİF prior **yok**.

### H2 — STALE / PHANTOM + GİRİŞ-İŞLENEBİLİRLİĞİ → **PASS** (ön-yargı çürütüldü)

Tutuş-penceresinde sıfır-hacim & sıfır-getiri (stale-print) gün-payı + giriş/D0
işlenebilirliği. *Not: sıfır-getiri-gün-payı bir veri-stale ölçütüdür (fiyat-değişim
VAR/YOK); kümülatif-getiri/drift/CAR HESAPLANMADI.*

| | İllikit | Likit-taban |
|---|---|---|
| sıfır-hacim gün-payı medyan · p90 | %0 · %3,3 | %0 · %0 |
| sıfır-getiri gün-payı medyan · p90 | %3,3 · %10,0 | %3,3 · %13,3 |
| giriş-günü (T+2) işlenebilir | **%98,6** | %99,8 |
| D0 işlenebilir | %97,9 | %99,8 |

**Yorum:** "Stale-price hayaleti illikit-PEAD'in baskın antagonistidir" **ön-yargısı bu
bantta DESTEKLENMEDİ.** İllikit dilim hâlâ neredeyse-her-gün işlem görüyor; giriş-günü
%98,6 işlenebilir — likit-tabana yakın. Sebep yapısal: 10M-TL likidite-tabanı + fiyat-
paneli-mevcudiyeti şartı, ölü-mikrocapları zaten ölçüm-bandının dışında bırakıyor. Yani
bu prob "ölü-kuyruğu" değil, **likidite-tabanı-altı-ama-hâlâ-aktif** bandı ölçüyor (dürüst
kapsam-notu). Ön-yargının gözleme göre güncellenmesi gerekti.

### H3 — KAPASİTE / ETKİN-N → **PASS**

| Ölçüt | Değer |
|---|---|
| illikit isim-havuzu | 432 |
| illikit olay | 6.121 |
| illikit SUE / çeyrek (medyan) | 229,5 (min 134, maks 327) |
| tercile-tepe isim / çeyrek (medyan) | 76,5 (min 45) |
| uç-dilimlerin ≥5 olduğu çeyrek-payı | **%100** |

**Yorum:** İllikit evren büyük (olay-kütlesinin ~%81'i) → kesitsel-genişlik beklenen
darboğaz **değil**. Bağlayıcı kısıt H1.

## Genel Hüküm: **CONDITIONAL-NEGATİF** (harvest-fizibilite)

| Kapı | Hüküm |
|---|---|
| H1 cost-wall | CONDITIONAL (maliyet-kapısı, knockout değil) |
| H2 stale/phantom | PASS (ön-yargı çürütüldü) |
| H3 kapasite | PASS |
| **harvest_feasibility** | **CONDITIONAL-NEGATIVE** |

Kesitsel-genişlik bol ve dilim hâlâ işler; ama harvest H1∧H2 ile belirlenir ve H1
medyan ~2×-likit + kuyruk-uninvestable. Sonuç: **illikit dilim "bedava öğün" değil.**
Üç bulgu birlikte:

1. **Kapasite kısıt değil** (H3) — illikit evren büyük.
2. **Slice hâlâ işler** (H2) — stale/phantom ön-yargısı zayıf çıktı; dürüst prior-güncellemesi.
3. **Maliyet bağlayıcı ama temiz-kill değil** (H1) — medyan %2,27, kuyruk alınamaz.

Decay-karşı-prior (RR-Y1-014: likit gross ~sıfır) + illikit gross için pozitif-prior-
yokluğu + 2× maliyet-kapısı + uninvestable-kuyruk → **pesine düşmek düşük-beklenen-değer**
ve YENİ bir ön-kayıtlı Stage-0 gerektirir (post-hoc evren-genişletme YASAK, DISC-3). Bu
prob bir **performans-hükmü vermez**; RR-Y1-014 likit-FAIL'inin açtığı "ya illikit?"
sorusunu **fizibilite-tarafından** kapatır. Bu, RR-Y1-015 negatif-bilgi tabanının
PEAD-illikit tamamlayıcısıdır (graveyard-honesty: tempting "illikit-dene" düzeltmesinin
neden düşük-değerli olduğunu kayda geçirir — mezar açmadan, diriltmeden).

## Disiplin Uyum Kaydı

| Madde | Durum |
|---|---|
| Performans-metriği yok | ✓ maliyet/stale/kapasite ölçüldü; getiri/CAR/t-istatistiği HESAPLANMADI |
| Motor + maliyet-modeli READ-ONLY | ✓ src/engine + realistic_cost yalnız import (sıfır-yazım) |
| Mezar-açma/diriltme yok | ✓ RR-Y1-014 FAIL'ini değiştirmez; illikit-evren için YENİ Stage-0 gerektiğini söyler |
| Post-hoc evren-genişletme | ✓ bu bir FİZİBİLİTE probudur, ölçüm değil; barlar yapısal (ölçülen-edge'e tunlu değil) |
| Ön-yargı-gözlem çatışması | ✓ stale/phantom ön-yargısı çürütüldü ve **dürüstçe** raporlandı (gözleme göre güncelle) |

## Üretim Kaydı

- Prob: [`scripts/probe/pead_illiquid_feasibility.py`](../../../scripts/probe/pead_illiquid_feasibility.py)
- Kanıt: `data/probe/pead_illiquid_feasibility_summary.{json,parquet}` (28 çeyrek-satırı)
- Girdiler (read-only): `data/snapshots/earnings_dates.parquet`,
  `data/probe/pead_announcement_daydated.parquet` (RR-Y1-013-B), degoran fundamentals
  (mktval → SUE1 paydası), `data/clean_universe/adjusted_prices_2019_2026.parquet`.
- SUE1 = donmuş RR-Y1-014 §3 formu burada yeniden-üretildi (prob self-contained); yalnız
  olay-sınıflama/sıralama için — SUE-değeriyle getiri ÖLÇÜLMEDİ.
