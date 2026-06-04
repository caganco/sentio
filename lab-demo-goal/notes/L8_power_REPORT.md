# L8 -- POWER / SAMPLE-SIZE analysis (HUKUM: DESCRIPTIVE-POWER-VIEW; sayisal power-bottleneck + reachability siralamasi)

Stage-0: `lab-demo-goal/stage0/STAGE0_L8_power.json` (sayilari okumadan ONCE donduruldu).
Sonuc: `lab-demo-goal/results/l8_power_results.json`. ASCII. SENTEZ -- yeni-edge YOK, yeni-veri YOK.
Yalniz donmus L1/L6 sonuc-JSON'larini okur; L7'nin "likit-killer = ANLAMLILIK/POWER" bulgusunu
SAYIYA cevirir: |t|=2 (ve %80 guc) icin kac BAGIMSIZ gozlem gerekir, gozlemle fark, ve gercekci
BIST olay-gelis-hizinda bu kac YIL surer.

## Yontem (Stage-0'da donmus)
Sabit-etki + sabit-birim-varyans altinda t = etki * sqrt(n) -> `n_required(hedef_t) = n_obs *
(hedef_t/|t_obs|)^2`. sd-yeniden-kurmaya GEREK YOK (saglam-headline). Hedefler: |t|=2.0
(anlamlilik) ve t=2.8016 (%80 guc, iki-yonlu alpha=0.05). t kaynagi: L1 -> nw_t (date-clustered
HAC, keep-bar gate); L6 -> clustered_t (event-clustered, keep-bar gate). nw_t TAM sqrt(n) olarak
olceklenmez (HAC duzeltmesi n ile kayar) -> birinci-derece tahmin, ACIK-beyan; nitel-siralama
(on-yillar vs yillar) buna dayanikli.

## Ledger -- 4 right-signed likit event-leg (hepsi anlamlilik-gate'inde SADECE power'dan dusuyor)
| leg | pencere | mean(bp) | n_obs | t | n_req(\|t\|=2) | gap | ileri-yil(\|t\|=2) | regime-sign-stable |
|---|---|---:|---:|---:|---:|---:|---:|---|
| L1 BIST30-add LIQUID | post_[+1,+5]  | +33.2 | 12 | 0.25 | 758.6 | 63.2x | 373 | false |
| L1 BIST30-add LIQUID | post_[+1,+10] | +82.4 | 12 | 0.71 |  94.9 |  7.9x |  41 | true  |
| L6 XU100 post-CPI    | [+1,+5]       | +61.1 | 87 | 1.48 | 159.3 |  1.8x |   6 | **false** |
| L6 XU100 post-CPI    | [+1,+10]      | +55.0 | 87 | 0.93 | 398.9 |  4.6x |  26 | false |

(ileri-yil = (n_req - n_obs) / yillik-olay-hizi; hizlar Stage-0'da sabit: CPI=12/yil tek-endeks;
BIST30-rekonstituasyon ~2 tarih/yil.)

## KRITIK okuma
1. **Index-rebalance power-acisindan UMITSIZ.** BIST30-add likit'te yilda ~2 bagimsiz tarih
   uretir; +82bp legi bile |t|=2 icin ~95 tarih = ~41 YIL, +33bp legi ~373 yil ister. Olay-kitligi
   sabit-tavan; beklemekle cozulmez. (L7 "dusuk-turnover event-driven dogru-arketip" dedi -- L8
   gosteriyor ki BU event-sinifi icin arketip-dogru-ama-olay-yok.)
2. **CPI-kosulsuz en-yakin AMA aldatici.** L6 post_tight (+61bp, t=1.48) yalniz ~1.8x daha-cok
   olay (= ~6 yil daha CPI) gerektiriyor -- en-dusuk gap. ANCAK ayni legin `regime.sign_stable =
   FALSE`: isaret rejim-bolunmesinde tutarli DEGIL. Yani "6 yil bekle, t=2 olur" hesabi, verinin
   DESTEKLEMEDIGI sabit-pozitif-etki varsayar. Bu, kosulsuz-CPI beklemenin SERAP oldugunu, gercek
   levyenin SURPRIZ-KOSULLANDIRMA (olay-sayisini buyutmek degil, olay-basi etkiyi keskinlestirmek)
   oldugunu sayisal-olarak gosterir.
3. **Power darbogazi = olay-GELIS-HIZI, orneklem-uzunlugu DEGIL.** 1 CPI/ay ve ~2 BIST30-tarih/yil
   sert-tavanlardir. Levye: ya intrinsik-olarak COK bagimsiz-olayli bir sinif (kazanc-ifsalari),
   ya da olay-basi-etkiyi-artiran kosullandirma (makro-surpriz).

## PEAD reachability (asil karar-degistiren kontrast)
Gozlenen-etki-bandinda |t|=2 icin gereken n_req = [94.9 .. 758.6]. Daily-PEAD ~120 bagimsiz
ifsa-TARIHI/yil uretirse (kazanc-sezonu kumelenmesi icin haircut'li; ~200 likit-isim x 4 ceyrek,
ayri-tarih sayilarak), bu band ~**0.8 .. 6.3 YIL**da birikir. Karsilastir:
- index-rebalance (~2 tarih/yil) -> on-yillar (41-373 yil) = ULASILAMAZ
- CPI-kosulsuz (12/yil) -> ~6-26 yil (ve sign-unstable -> serap)
- **daily-PEAD (~120/yil) -> ~1-6 yil = TEK ulasilabilir-sinif**

Yani daily-PEAD, gelis-hizi nedeniyle |t|=2'yi insan-anlamli-ufukta ULASILABILIR kilan TEK
event-sinifi. Bu, FORWARD_DATA_SPEC siralamasinin SAYISAL gerekcesi:
**#1 DAILY-PEAD (tek power-ulasilabilir) >> #2 SURPRIZ-KOSULLU-MAKRO (etkiyi artirir, n'i degil)
>> index-rebalance-tek-basina (power-umitsiz).**

## Hukum: DESCRIPTIVE-POWER-VIEW
Yeni-edge iddiasi YOK. Power-hesabi bir KARAR-ARACI. DURUST-beklenti (Stage-0: kit-event-siniflari
ulasilamaz; daily-PEAD tek-ulasilabilir; CPI'da levye surpriz-kosullandirma) OLCUMLE dogrulandi.
Kutlama-yok. N<=1. L8 ARSIVLENDI -> SYNTHESIS-VIEW. FORWARD_DATA_SPEC #1/#2 onceligi sayisal-olarak
pekistirildi; #1 (daily-PEAD KAP gun-damgasi) en-yuksek power-kazanci olarak teyit edildi.
