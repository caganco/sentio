# L1 -- BIST100/BIST30 index-rebalance event study (HUKUM: INDEX-EFFECT-VIEW)

Stage-0: `lab-demo-goal/stage0/STAGE0_L1_index_rebalance.json` (sonuctan ONCE donduruldu).
Sonuc: `lab-demo-goal/results/l1_index_rebalance_results.json`. ASCII. Olcum-only, look-ahead-safe.

## Kurulum
POINT-IN-TIME `pit_membership` panelinde uyelik-flip'leri (add: False->True, del: True->False)
tespit edildi; her olay efektif-tarihe (tau0) hizalandi. Flip'ler ceyrek-baslarinda
(Oca/Nis/Tem/Eki 1) kumeleniyor = BIST endeks-revizyon efektif-gunleri (32 farkli olay-gunu).
AR = r_i - r_mkt(EW-full gunluk, durust-bar); CAR = pencere boyunca AR toplami.
PRIMARY istatistik = olay-gunu-clustered t (~32 tarihe collapse, ayni-gun-sok korelasyonuna
karsi muhafazakar). ALL + LIQUID (>=1e7 TL trailing-63g-medyan). Maliyet = D-207 gercekci
round-trip (olay-basi TEK tur; quoted-primary, ~%61 quoted).

## Olay sayilari (BIREBIR reproduce)
BIST100: 249 ekleme / 245 cikarma. BIST30: 28 ekleme / 26 cikarma. (2020-01-02'de 23/23
buyuk-rekonstruksiyon kumesi -- DISLANMADI, raporlandi.)

## Bulgular (LIQUID, date-clustered t; tradeable=[+1,+K] gercekci-maliyet-sonrasi NET)
| grup | pencere | ne | tradeable? |
|---|---|---|---|
| BIST100-add | pre[-10,-1] | ALL +0.91% (t=0.66), LIQ -1.4% | descriptive, anlamsiz |
| BIST100-add | event[0] | +0.22%..+0.42% (t<=1.5) | kucuk pop, anlamsiz |
| BIST100-add | post[+1,+10] | LIQ net -2.8% (t=-1.85) | REVERSAL, long-degil, |t|<2 |
| BIST100-del | post[+1,+10] | LIQ net -1.8% | anlamsiz |
| BIST30-add | pre[-10,-1] | ALL +2.1% / LIQ +3.2% (t=1.57) | en-buyuk run-up AMA pre (descriptive), n=13, anlamsiz |
| BIST30-del | pre[-10,-1] | LIQ -4.1% (t=-1.55) | mirror, anlamsiz |
| TUM tradeable [+1,+K] LIQ | net-after-cost | HEPSI < 0 | long-edge YOK |

## Hukum: INDEX-EFFECT-VIEW (deploy-edilebilir-edge DEGIL)
Niteliksel endeks-etkisi imzasi VAR (ekleme pre-efektif run-up + post-efektif reversal;
cikarma ayna) -- literaturle (Bildik-Gulay 2008: hacim>fiyat, efektif-gun-zirve, sonra reversal)
ve agent'in "ORTA-ama-global-zayifliyor" notuyla TUTARLI. AMA:
- look-ahead-safe TEK-tradeable pencere [+1,+K]: TUM gruplarda gercekci-maliyet (~28-46bp
  round-trip) sonrasi NET < 0 -> pozitif long-edge YOK.
- date-clustered |t| hicbir tradeable-likit pencerede >=2 DEGIL (anlamlilik-duvari; N ince:
  ~250 ekleme / 32 tarih, BIST30 ~28/13).
- regime-sign-stable cogunlukla HAYIR.
keep-bar 3/3 KALDI. Pre-efektif run-up (en-ilginc: BIST30-add +3.2% likit) ilan-tarihi-olmadan
temiz-tradeable DEGIL (descriptive); zaten anlamli da degil.

## Ana ders (graveyard-ile-tutarli)
Gorunur endeks-etkisi var ama likit-evren + gercekci-maliyet + anlamlilik suzgecinden GECMIYOR.
DURUST-beklenti (Stage-0'da ONCEDEN: descriptive-VIEW, deploy-edilemez) OLCUMLE dogrulandi.
Kutlama-yok. 2.tur/grid-supurme YOK. L1 ARSIVLENDI -> VIEW. Sonraki: L3 PEAD (agent en-iyi
event-driven aday dedi, FIYAT-DISI sinyal, bizde veri var).
