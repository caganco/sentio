# L7 -- FEASIBILITY-FRONTIER ledger (HUKUM: DESCRIPTIVE-SYNTHESIS; iki-kapi cercevesi + ileri go/no-go kurali)

Stage-0: `lab-demo-goal/stage0/STAGE0_L7_feasibility.json` (sayilari okumadan ONCE donduruldu).
Sonuc: `lab-demo-goal/results/l7_feasibility_frontier_results.json`. ASCII. SENTEZ -- yeni-edge YOK,
yeni-veri YOK. Yalniz donmus L1/L2/L3/L6 sonuc-JSON'larini okur ve her deploy-leg'i on-beyan-edilen
iki-kapiya gore siniflar.

## Iki kapi (Stage-0'da donmus)
- **SIGNIFICANCE/SIGN kapisi**: gross (maliyet-siz) DOGRU-isaretli (long-edge icin pozitif) VE |t|>=2.
  Gecmezse -> SIGNIFICANCE-or-SIGN-WALL (sifir-maliyette bile edge yok).
- **COST kapisi**: significance gecmis-iken, gercekci-maliyet sonrasi NET pozitif VE |t|>=2 kalir.
  Gecmezse -> COST-WALL (gercek-gross-edge, maliyet yer).
- BOTH = significance dusuyor VE gross zaten maliyetin altinda (face-value'da cost da baglardi).

## Ledger ozeti -- 20 deploy-leg, 0 NO-WALL
| scope | siniflama dagilimi |
|---|---|
| LIQUID (10 leg) | 6 BOTH, 4 SIGNIFICANCE-or-SIGN-WALL, 0 COST-WALL, **0 NO-WALL** |
| ALL/microcap (10 leg) | 10 BOTH, 0 NO-WALL |

## KRITIK INCE-BULGU -- LIKIT'TE BAGLAYAN KAPI = ANLAMLILIK/POWER, MALIYET DEGIL
Likit-leg'leri ikiye ayir:
1. **Cross-sectional tercile (L2 reversal, L3 PEAD) likit**: gross YANLIS-ISARETLI veya anlamsiz
   (L2 long-loser -125bp/-36bp t<-3; L3 long-tercile -151bp/-132bp t=-1.9/-3.2). Bunlar
   sign/significance-wall; maliyet zaten teferruat.
2. **Dusuk-turnover EVENT-DRIVEN (L1 inclusion, L6 CPI) likit**: gross DOGRU-ISARETLI ve
   maliyetin USTUNDE -- BIST30-add [+1,+10] LIQ +82bp (cost ~28bp), post-CPI [+1,+5] XU100 +61bp
   (cost 40bp), [+1,+10] +55bp. Bunlar COST kapisini face-value'da GECER. AMA hepsi SIGNIFICANCE
   kapisinda dusuyor: |t| = 0.25 / 0.71 / 1.48 / 0.93. Yani gross POZITIF ama 2-sigma DEGIL.

-> Survivable-arketip (dusuk-turnover, event-driven, likit, dogru-isaret) DOGRU teshis edildi;
ama elimizdeki olaylar 2-sigma'yi gececek istatistiksel GUCE (bagimsiz gozlem-sayisi) sahip degil
(BIST30-add likit n~13-17 olay; CPI n~87 ama proxy-tarih smear + tek-piyasa). Cross-sectional
taraf ise YANLIS-isaret/anlamsiz. Iki-yandan da likit NET-edge cikmiyor.

## Refine edilmis meta-bulgu (eski "cost-wall" ifadesinin kesinlestirilmesi)
- **MICROCAP killer = COST**: ALL-evrende gross-buyuklugu daha-buyuk olabilir ama turnover-suruklu
  realized-cost (~46-140bp) her-seyi yer (10/10 BOTH).
- **LIQUID killer = SIGNIFICANCE/POWER**: likit'te cost-magnitude dusuyor (~28-46bp event,
  ~46-62bp tercile) ama gross-edge'in kendisi ya yanlis-isaret (tercile) ya da 2-sigma-alti
  (event-driven). Gorunur-edge microcap'te yasar; likite gecince gross-edge buharlasir.

## Ileri GO/NO-GO kurali (yeniden-kullanilabilir karar-araci)
Yeni bir adayi TAM-disiplinli test etmeye DEGER ancak ucuz-on-kontrol her-iki-kapiyi likit'te
makul-gecebiliyorsa:
1. DOGRU-isaretli gross + 2-sigma icin yeterli BAGIMSIZ gozlem (overlap-sismesiz; dusuk-turnover/
   event-driven tercih et ki n sahte-sismez), VE
2. turnover-ima-edilen breakeven < gercekci ~28-46bp likit round-trip.
Adayin tek-gorunur-edge'i microcap'teyse, ya da turnover-breakeven'i makul-gross'u asiyorsa -> ATLA;
iki-duvardan birine carpacak.

Pratik sonuc: mevcut-veride kalan en-umutlu hamle yeni cross-sectional faktor DEGIL; dusuk-turnover
event-driven uzayda DAHA-COK BAGIMSIZ OLAY + KESIN-ZAMANLAMA (power'i artirip pencereyi daraltmak).
Bu, L6'nin "surpriz-kosullu + kesin-tarih + PPK-tam-gecmis" ve SUMMARY'nin "deger YENI-VERI-TURUNDE"
onerisine SAYISAL gerekce verir: bottleneck = likit dusuk-turnover olaylarda gozlem-sayisi/power.

## Hukum: DESCRIPTIVE-SYNTHESIS
Yeni-edge iddiasi YOK. Iki-kapi cercevesi + go/no-go kurali bir KARAR-ARACIdir. DURUST-beklenti
(Stage-0: iki-gate yapisi, likit'te significance baglar) OLCUMLE dogrulandi. Kutlama-yok. N<=1.
L7 ARSIVLENDI -> SYNTHESIS-VIEW.
