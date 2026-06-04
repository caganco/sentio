# L13 -- DAILY-PEAD TWO-GATE FEASIBILITY BAR (HUKUM: DESCRIPTIVE-FEASIBILITY-VIEW)

Stage-0: `lab-demo-goal/stage0/STAGE0_L13_daily_pead_feasibility.json` (sonuc-ONCESI donduruldu).
Sonuc: `lab-demo-goal/results/l13_daily_pead_feasibility_results.json`. ASCII. SENTEZ/feasibility --
yeni-edge YOK, yeni-veri-CEKIMI YOK, optimizasyon YOK, RE-TEST YOK. L8 (power) + L9 (gelis-hizi) +
L10 (aylik likit SUE etkisi + olay sd) + committed D-208 (gercekci maliyet) okur; daily-PEAD icin
COST-duvari ile POWER-duvarini TEK ileri-bara katlar: karar-veren deney, net-|t|=2 icin (gercekci
round-trip maliyet sonrasi) hangi MINIMUM brut ilan-penceresi-CAR'i saglamali, hangi duvar baglar,
ve bu bar olculmus aylik sinyale gore nerede durur? Daily-pencere etkisi offline-OLCULEMEZ; L13
GEREKSINIMI (bar) sinirlar, etkiyi degil -- yalniz donmus olculmus girdiler + standart
random-walk varyans-olcekleme (sigma_window = sigma_month * sqrt(H_hold/21)).

## Olculen girdiler (donmus L8/L9/L10 + D-208)
- sigma_month (likit olay sd) = **18.51%/ay** (L10).
- aylik likit long-only high-SUE market-rel ortalama = **+37.7bp** (L10 mean_pos).
- aylik likit long-short SUE half-split = **+69.4bp** (L10 effect_pos_minus_neg, t=0.64 ANLAMSIZ).
- gelis-hizi: konservatif (bounded date-cluster) **95.4/yil**, iyimser (likit-olay) **136.4/yil** (L9).
- likit round-trip maliyet = **38.0bp** (D-208 selected_picks mean_round_trip_roll), effective-flat 41.75bp.

## Iki-kapi bar (konservatif 95.4/yil; brut ilan-penceresi-CAR, bp)
**Cost FLOOR (n->inf) = round-trip maliyet**: long-only 1x=38.0bp, long-short 2x=76.1bp.

| leg / hold | H=1yr | H=3yr | H=5yr | H=8yr | baglayan-duvar (kisa->uzun) |
|---|---:|---:|---:|---:|---|
| long-only 5d | 223 | 145 | 121 | 103 | POWER butun-ufukta |
| long-only 10d | 300 | 189 | 155 | 131 | POWER butun-ufukta |
| long-short 5d | 261 | 183 | 159 | 142 | POWER -> COST (H=8yr'de coster) |
| long-short 10d | 338 | 227 | 193 | 169 | POWER butun-ufukta |

Concentration-orani (bar / aylik-etki = pencerenin TUM aylik-spread'in kac-katini saglamasi gerek):
long-only 5d **5.9x (1yr) -> 2.7x (8yr)**; long-short 5d **3.8x -> 2.0x**. Hicbiri <=1 degil ->
tam-konsantrasyon bile (tum aylik spread pencereye dusse) yetmez; pencere aylik-ortalamanin USTUNDE
etki ister (ya konsantrasyon+amplifikasyon, ya da sqrt-altinda dusuk pencere-gurultusu).

## Okuma (beklenti DOGRULANDI -- AYIK)
- **Aylik sinyal maliyet-tabanini ANCAK-ANCAK karsilamiyor** (en-carpici bulgu):
  long-only 37.7bp < tek round-trip 38.0bp (orani 0.99); long-short 69.4bp < cift round-trip 76.1bp
  (orani 0.91). Yani **olculmus aylik PEAD sinyali, POWER gereksinimi BIR-YANA, maliyet-tabanini
  bile gecmiyor**. `both_legs_margin_thin = True`.
- **Baglayan duvar**: kisa-ufukta POWER (sigma_window/sqrt(n) buyuk), uzun-ufukta sabit COST FLOOR
  (power-bileseni sqrt(n) ile kuculur, round-trip maliyet kalir). long-short 5d'de COST H=8yr'de coster.
- **Daily-PEAD'in tum-umudu ilan-penceresi KONSANTRASYONU**: net-|t|=2, ancak post-ilan drift'i
  birkac-gunluk pencerede maliyet-tabanin uzerine konsantre olursa (kanonik-PEAD hipotezi) VE gercek
  pencere-gurultusu sqrt-olceklemenin altindaysa mumkun. **IKISI de offline-OLCULEMEZ** -- tam-olarak
  onayli KAP gun-damgasi fetch'inin cozecegi sey.
- **DURUST karsi-not**: (a) L10 caveat'i gercek pencere-gurultusunun sqrt-altinda olabilecegini soyler
  (post-ilan drift random-walk'tan duzgun) -> bar DUSER, concentration-orani duser; (b) aylik half-split
  zaten anlamsiz (gurultu olabilir); (c) kanonik-PEAD gelismis-piyasalarda post-ilan KONSANTRE olur,
  ama BIST likit-isimlerde OLCULMEMIS. Bar konservatif (ust-sinir); fetch hem konsantrasyonu hem
  gercek-gurultuyu cozer.

## Siralamaya etki: #1 TEMPER edildi (devrilmedi)
- Daily-PEAD HALA tek power-ulasilabilir sinif (L8). AMA L13 net-deploy barini gosterir: yuksek, ve
  olculmus aylik sinyalin maliyet-tabani uzerinde MARJI YOK. -> fetch NULL donebilir (gercek olasilik).
- Bu #1'i "kesin-kazanc" degil "tek-makul-bahis, ince-marj" yapar. FORWARD_DECISION_CARD'a iki-kapi
  bar + maliyet-taban + concentration-gereksinimi eklenir; go/no-go DAHA-DURUST cerceveye oturur.

## Hukum: DESCRIPTIVE-FEASIBILITY-VIEW
Yeni-edge iddiasi YOK. Daily-PEAD significance-only cerceveden (L8-L11) IKI-KAPI bara yukseltildi:
karar-veren deney hem gercekci maliyet-tabanini hem power-barini gecmeli; baglayan-duvar kisa-ufukta
POWER, uzun-ufukta COST-FLOOR; olculmus aylik likit SUE sinyali maliyet-tabanini ancak-ancak karsilar
-> viabilite tamamen (offline-olculemez) ilan-penceresi-konsantrasyonuna baglidir. N<=1 (sentez).
L13 ARSIVLENDI. Forward-#1 hala en-ust ama AYIK marjla.
