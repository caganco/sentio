# RR-Y1-003: D-213 YAPISAL-FIX (total-return XU100) -- VERI-FIZIBILITE BULGUSU

**Tur:** ARASTIRMA / FIZIBILITE (olcum-DEGIL, edge-test-DEGIL, henuz Stage-0 yok)
**Tarih:** 4 Haziran 2026 | **Hazirlayan:** Builder (Yol-1-lab, thread RR-Y1-003)
**Baglam:** D-213 ilk-resmi-olcum TRADEABLE-DEGIL cikti (tek fail eden kistas: keep-bar[1]
NW|t|=1.82 < 2.0). Onerilen yapisal-fix = bagimli-tarafin fiyat-only XU100 handikapini
(temettu-drag ~%2-4/yil) gidermek, prediktoru (LEVEL ex-ante reel-faiz) AYNEN birakarak.
Bu dokuman dalmadan-once "yapilabilir mi, hangi veriyle, bizi yanltir mi" hukmudur.
**Cikti niteligi:** Kod-yok, test-yok, STAGE0-yok. Sadece hukum + Orch'a karar-secenekleri.
**Onceki:** [RR-Y1-003-asama0-veri.md](RR-Y1-003-asama0-veri.md) (D-212 veri-gercekleri),
[D-213-rapor.md](../research/D-213-rapor.md) (ilk-olcum verdict'i), STAGE0_d213.json.

---

## 0. TL;DR -- HUKUM

**Tam ve dogru bir total-return XU100 endeksi YEREL OLARAK KURULAMAZ.** Ama daha onemlisi:
yanitltmayan TEK fix bicimi (sabit temettu-getiri ekleme) PRIMARY anlamliligi MATEMATIKSEL
OLARAK DEGISTIREMEZ. Yani total-return-fix, fail eden keep-bar[1]'i kurtaramaz (yapisi
geregi), sadece deploy-bacak ekonomisini duzeltir -- ve o duzeltme kendi hipotezimizi
KAYIRAN bir on-yanliligi kaldirir (overfitting'in tersi).

| Soru | Hukum | Baglayici mi? |
|---|---|---|
| **S1** Hazir total-return XU100 endeksi yerelde var mi? | HAYIR. snapshot sadece fiyat-only (`exposure_d187_xu100`); meta.json'in kendi caveat'i: *"price-only, no dividends; equity disadvantaged ~2-4%/yr"*. | EVET (hazir-seri yok) |
| **S2** Per-hisse temettuden endeks-TR kurulabilir mi? | HAYIR temiz degil. `dividends/`, `index_components/`, `corporate_actions/` klasorleri **BOS (0 dosya)**. Kompozisyon (endeks-agirlik) serisi olmadan per-hisse temettuyu endeks-seviyesine toplamak cok-serbestlik-dereceli = yanltma araci. | EVET (kompozisyon yok) |
| **S3** EVDS'te hisse total-return endeksi var mi? | HAYIR. EVDS BIST endekslerini fiyat-endeksi olarak tasir (getiri-endeksi degil). | EVET |
| **S4** fundamental_ratios temettu verisi var mi? | KISMEN. 229 dosya, per-hisse NAKIT NET TEMETTU + TV% (getiri) + PIYASA DEGERI (2009-01..2026-04 surekli). Ama endeks-TR icin S2 kompozisyon-agirligi gerekir -> tek-basina yetmez. | -- (S2'ye bagli) |
| **S5** Sabit-ekleme primary-anlamliligi degistirir mi? | **HAYIR -- yapisi geregi.** Asagidaki invariyans-argumani (sec 2). | -- (kritik bulgu) |

**Sonuc:** Yapisal-fix'in yanltmayan tek bicimi = **sabit (flat) yillik temettu-getiri ekleme**.
Bu bir count=2 primary-prototip DEGILDIR (primary test invariant); deploy-bacak robustness
duzeltmesidir.

---

## 1. SORU VE AMAC

D-213 prediktoru: `r_ex_ante(t) = nominal(t) - 12a-beklenen-enflasyon(t)` (LEVEL, ~t+15g,
lag-1). Bagimli: `real_ret(t) = r_nom(t) - infl_MoM(t)`, r_nom = XU100 **fiyat-only** aylik
getiri. Yapisal handikap: fiyat-only seri temettuyu dusurur -> equity ~%2-4/yil cezalanir
(snapshot meta.json'da belgeli).

Amac (kullanici direktifi: *"yapisal fix i bizi yanltmayacak sekilde yap"*): tek-degisken
duzeltme -- SADECE bagimli fiyat-only -> total-return, prediktor=LEVEL AYNEN kalir. Temiz
atif icin baska hicbir knob oynamaz (lag, esik, pencere, rejim degismez).

---

## 2. KRITIK BULGU -- INVARIYANS ARGUMANI (neden "yanltmaz")

Yanltmayan tek dusuk-DOF total-return duzeltmesi: her aya **sabit** bir temettu getirisi ekle:

```
r_nom'(t) = r_nom(t) + d        d = yillik_getiri / 12   (tek, dondurulmus sabit)
real_ret'(t) = r_nom'(t) - infl_MoM(t) = real_ret(t) + d
```

Bagimliya **sabit eklemek**, `real_ret`'i her ay ayni `d` kadar kaydirir. OLS regresyonunda
bagimliya sabit eklemek **egimi (slope) ve onun NW-t'sini DEGISTIRMEZ** -- sadece kesisimi
(intercept) kaydirir. Dolayisiyla:

> **D-213'un fail eden keep-bar[1]'i (NW-OLS slope-t = 1.82 < 2.0) sabit-temettu-ekleme ile
> YAPISI GEREGI degisemez. Total-return-fix primary anlamliligi kurtaramaz.**

Bu, ozellikle **iyi haber**: fix bir "fail'i kurtarma araci"na donusemez. Sadece DEPLOY-bacak
ekonomisini (kumulatif reel getiri timing-vs-B&H) etkiler.

**Deploy-bacak etkisinin YONU (ek yanltma-kontrolu):** Temettu, B&H'i (her ay equity'de)
timing-stratejisinden (bazen cash'te) DAHA COK besler. Yani temettu eklemek B&H'i **yenmeyi
ZORLASTIRIR**. Onceki fiyat-only kurulum, always-in B&H'i fazla cezalandirarak timing-
stratejimizi **kayiriyordu** (bir kuyruk-ruzgari). Fix bu kuyruk-ruzgarini kaldirir =
kendi hipotezimiz aleyhine, overfitting'in tam tersi.

---

## 3. NEDEN "TAM TR ENDEKSI" YAPILMAZ (yanltma-riski)

Gercek BIST-100 getiri-endeksi temettuyu mevsimsel ve hisse-kompozisyonuna gore dagitir
(BIST temettuleri ilkbahar-yaz kumelenir). Mevsimsel/gercekci bir yeniden-kurulum egimi
DEGISTIREBILIR -- ve tam orada yanltma yasar: hangi-ay, ne-kadar, hangi-agirlik secimleri
cok-serbestlik-dereceli. Kompozisyon-agirligi yerelde YOK (index_components/ bos), bu yuzden
agirlik secmek zorunda kalirdik (EW mi mcap mi?) = kor-tuning. Eger boyle bir kurulum
keep-bar[1]'i 1.82'den >2.0'a itseydi, kendimizi kandirmis olurduk. Bu yol REDDEDILIR.

---

## 4. ORCH'A KARAR-SECENEKLERI

**Kapsam (hangi fix):**
- **(A) Sabit-ekleme, deploy-only [ONERILEN]:** Tek yillik temettu-getiri sabiti dondur;
  SADECE deploy-bacak kumulatif reel-getiri'yi (artik temettu-odeyen B&H'e karsi) yeniden-hesapla.
  D-213-rapor'a "primary slope/keep-bar'lar matematiksel olarak degismez" notunu ac. Dusuk-DOF,
  durust, fail'i kurtaramaz.
- **(B) Fix'i kurma, invariyans-notu yaz:** Sabit-fix keep-bar[1]'i ispatla oynatamadigi icin,
  D-213-rapor'a invariyans-ispatini ekle (fiyat-only handikap anlamlilik-verdict'ini etkilemez)
  ve dogrudan change-form tartismasina gec.
- **(C) Tam TR yeniden-kurulum [ONERILMEZ]:** fundamental_ratios'tan per-hisse temettu x mcap
  agirlik. Kompozisyon-agirligi eksik -> cok-serbestlik-dereceli = kacinmaya calistigimiz
  yanltma araci.

**Temettu sabiti d (eger A secilirse):**
- **3.0%/yil orta-nokta:** belgeli ~%2-4 araliginin ortasi (= %0.25/ay). Basit, savunulabilir.
- **4.0%/yil bize-karsi-muhafazakar:** ust-uc; kendi hipotezimizi en cok cezalar (B&H'i en cok
  zorlastirir). "Bizi kayirmama" ilkesiyle en tutarli.
- **2.0%/yil alt-uc:** en az equity-kredisi.

Builder tavsiyesi: **(A) + 4.0%/yil bize-karsi-muhafazakar** -- en yanltmayan kombinasyon;
ama karar Orch'ta. Hangisi secilirse STAGE0'a (sonuc-oncesi) dondurulur.

---

## 5. DISIPLIN NOTU

- Bu fix primary multiple-testing butcesini TUKETMEZ: primary test (slope-t) sabit-ekleme
  altinda invariant oldugu icin yeni bir prototip-denemesi degildir; deploy-bacak duzeltmesidir.
- Litmus ("sonuctan bagimsiz yapar miydim?"): EVET -- temettu-handikabi veri-kalitesi kusuru,
  hangi-aylar-zarar-ettirdi'den bagimsiz. Tek-degisken (yalniz bagimli), prediktor=LEVEL sabit.
- Change-form (delta r_ex_ante) tartismasi bu fix'ten SONRAYA ertelendi (kullanici direktifi).
