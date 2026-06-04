# L10 -- DAILY-PEAD EFFECT-SIZE RECOVERY BOUND (sign + magnitude) (HUKUM: MAGNITUDE-FEASIBILITY-VIEW)

Stage-0: `lab-demo-goal/stage0/STAGE0_L10_pead_effect.json` (sonuclari okumadan ONCE donduruldu).
Sonuc: `lab-demo-goal/results/l10_pead_effect_results.json`. ASCII. SENTEZ/feasibility -- yeni-edge
YOK, yeni-veri-CEKIMI YOK, optimizasyon YOK. Forward-data #1 (daily-PEAD) feasibility-dongusunu
KAPATIR: L8 = n_required bandi, L9 = gercek likit-hacim/hiz, L10 = gun-damgali bir testin
GEREKTIRECEGI per-olay ETKI-BUYUKLUGU (monthly-etkiye gore recovery-carpani) + ISARET-engeli.

## Yontem (Stage-0'da donmus)
- Pencere: fiscal_year>=2019, SUE non-null (L9 ile ayni testable-altkume).
- Per-olay forward getiri: olayin consume_from_month'undaki (look-ahead-safe ilk-islenebilir-ay)
  TAKVIM-AYI toplam getirisi `adjusted_close[ay-son]/adjusted_close[onceki-ay-son]-1`. MARKET-RELATIVE:
  ayni consume-ay LIKIT-evrenin EW-ortalama getirisi cikarilir (carry-immune PRIMARY, L2/L3/H2b ile tutarli).
- Likidite: per (sembol, consume_month) trailing-63g-medyan value_tl >= 1e7 TL, GIRIS'te-bilinen
  (onceki-ay-sonu) -> look-ahead-safe. LIKIT-altkume birincil mercek (L7: tek guc-ilgili evren).
- SUE-isaret etkisi: olaylar SUE-isaretine bolunur (pos-SUE sue>0 vs neg-SUE sue<0). AYLIK olay-seviyesi
  SUE-etkisi = mean(rel | pos-SUE) - mean(rel | neg-SUE); ALL ve LIKIT icin. Welch iki-ornek t.
- sd_event: LIKIT market-relative per-olay getirilerin kesitsel sd'si (t = etki*sqrt(n)/sd_event'in gurultu-terimi).
- Gereken etki: n in {L9 bounded-date-cluster-hizi (~95/yil) * H}, H in {1,3,5,8} yil icin
  eff_req(n) = 2.0 * sd_event / sqrt(n). Recovery-carpani = eff_req / |aylik-LIKIT-etki|.

## Olculen (GERCEK panel)
| metrik | deger |
|---|---:|
| getiri-eslesen olay (2019+) | 5726 |
| LIKIT getiri-eslesen olay | 1091 (**%19**) |
| aylik SUE-etki pos-neg (ALL) | **+1.12%** |
| aylik SUE-etki pos-neg (LIKIT) | **+0.69%** (Welch t=**0.64**, ANLAMSIZ) |
| sd_event (LIKIT, aylik kesitsel) | **18.5%** |
| L3 aylik LIKIT long-tercile costfree | -1.32%/ay (t=-3.24) |

Gereken per-olay etki (|t|=2, ~95/yil hizda) ve recovery-carpani:
| ufuk | n | eff_req | recovery (aylik-LIKIT-etkiye gore) |
|---:|---:|---:|---:|
| 1 yil | 95 | ~379bp | 5.46x |
| 3 yil | 286 | ~219bp | 3.15x |
| 5 yil | 477 | ~169bp | 2.44x |
| 8 yil | 763 | ~134bp | 1.93x |

## Okuma (DURUST -- beklentiden SAPTI, Stage-0'da onceden-isaretlendi)
- **ISARET-engeli YOK (surpriz)**: Stage-0 beklentisi olay-seviyesi LIKIT etkinin L3-tercile gibi
  NEGATIF cikmasiydi. Cikmadi: pos-neg yari-bolme LIKIT'te **+0.69%** (dogru-isaretli) ama
  ANLAMSIZ (t=0.64). L3-tercile (-1.32%) ile celiski DEGIL -- farkli kontrast (ust-tercile vs
  EW-full benchmark) ve farkli benchmark (EW-LIKIT). Stage-0 bu dali ACIK-onceden-kaydetti
  ("possible surprise: ... reverts to a pure magnitude/recovery question").
- **GERCEK kisit = GURULTU**: sd_event ~ **%18.5/ay** kesitsel. Sinyal (~69bp) gurultuye gore
  minicik -> aylik-cozunurlukte anlamsiz. Gun-damgasi iki-yonlu yardim eder: (a) etkiyi
  yogunlastirir (pay buyur), (b) pencereyi kisaltir (gunluk/birkac-gun sd << aylik %18.5).
- **Recovery makul-mertebede**: gun-damgali pencere-etkisi aylik yari-bolme-etkisinin ~2-5.5x'i
  olursa |t|=2 1-8 yilda gecer. PEAD-literaturu driftin ilk birkac-gunde yogunlastigini soyler ->
  birkac-x recovery MANTIKLI. Ama payda (aylik-etki) anlamsiz oldugu icin carpan gurultulu-tabanli.
- **KONSERVATIF caveat**: sd_event burada AYLIK (%18.5); gercek gunluk/birkac-gun penceresi cok
  daha-dusuk gurultulu (sd ~ sqrt(gun/21)). Yani gercekte gereken gunluk-etki bu bound'dan
  KUCUK -- eff_req ve recovery-carpani daily-PEAD icin KOTUMSER (yukari-yanli). Gercek-test daha-kolay.

## Hukum: MAGNITUDE-FEASIBILITY-VIEW
Yeni-edge iddiasi YOK. Forward-data #1 dongusu kapandi: **hacim (L9) yeterli**, **isaret
dogru ama anlamsiz**, **buyukluk-gereksinimi makul ve bound'u konservatif**. Baglayan
belirsizlik = gun-damgali pencerede yogunlasmis pozitif-driftin VAR-olup-olmadigi -- ki bu
OFFLINE OLCULEMEZ. L10 boylece forward-data #1'in NEDEN onayli-fetch ile karara-baglandigini
keskinlestirir: fetch, aylik-gurultu altinda gizli olabilecek gunluk-pencere etkisini test eder.
Kutlama-yok. N<=1 (sentez). L10 ARSIVLENDI -> SYNTHESIS-VIEW. SONUC: L8(n)+L9(hacim)+L10(etki)
ucusu birlikte FORWARD_DATA_SPEC #1'i tam-cevreler -- onayli day-stamp fetch artik teorik-power
+ gercek-hacim + makul-magnitude ile UC-yonden gerekceli; tek-kalan bilinmeyen gunluk-isaret/buyukluk.
