# RR-Y1-019 — VBTS tedbir-olayı edge-adayı **Faz-1 fizibilite probu** (betimsel)

**Sınıf:** Veri-erişilebilirlik + evren-kesişim probu. **Stage-0-DEĞİL**, ölçüm-DEĞİL,
edge-iddiası-DEĞİL, hipotez-testi-DEĞİL. Hiçbir getiri/CAR/sinyal/backtest hesaplanmadı —
yalnız (a) olay-akışının erişilebilirliği, (b) erişilebilirse evren-kesişiminin nasıl
ölçüleceği, (c) negatif-görüş ifadesinin yapısal-fizibilitesi. Span **sonuca-bakılmadan
ex-ante donduruldu: 2024-06 → 2026-06 (son 24 ay, takvim-bazlı)**.

**Kapsam-ayrımı (ZORUNLU):** Go/no-go ve Stage-0 kararı bu rapora ait değildir —
maintainer'a aittir. Faz-2 (dual-layer ölçüm) yalnız *belirtilir*, KOŞULMAZ. Hiçbir frozen
pencere tüketilmedi. Tedbir tetik-eşiği (non-public) fiyattan geri-türetilmedi: **olay =
açıklamadır.**

**Aday (literatür-çıpalı, Autore vd.):** VBTS (Volatilite Bazlı Tedbir Sistemi) anormal
fiyat/hacim gösteren paylara 1 ay süreyle kademeli tedbir uygular — (1) Açığa Satış & Kredili
İşlem Yasağı → (2) Brüt Takas → (3) Emir Paketi → (4) Tek Fiyat Yöntemi → (5) Emir İletim
Kanalı Kısıtı; her alt-kademe üst-kademe uygulanırken sürer. Mekanizma: kaldıraç-ve-netleşme
yakıtıyla yukarı-itilen paylar, yakıt mekanik-çekilince (brüt takas aynı-gün-netleşmeyi,
marj-yasağı kaldıracı kaldırır) geri-döner. Karşı-taraf: de-leverage'a zorlanan perakende
momentum/pump kalabalığı. Tedbirler KAP'ta seans-sonu, PIT-damgalı, makine-okunur ilan edilir.

---

## A. Offline envanter (mevcut repo/disk)

### A.1 — VBTS olay-paneli — **YOK (repo'da hiçbir biçimde)**
Tedbir olay-akışı repo'da hiçbir yerde tutulmuyor: `kap_parser.py` `EventCategory` enum'ında
tedbir/measure sınıfı yok; `flow_intel` DB yalnız içeriden-işlem (insider) içerir; yerel
`DATASTORE_ARCHIVE_LAYOUT` (thresholds.py) `short_selling` **pozisyon**-verisi (ürün 3155)
taşır ama tedbir **ilanı** taşımaz. → Olay-paneli **yeni read-only edinim** gerektirir.

### A.2 — Kesişim paydası (iki liste) — **HAZIR**
- Survivorship-clean panel: `data/clean_universe/adjusted_prices_2019_2026.parquet`
  (681 sembol, 2019-01-02 → 2026-05-26 günlük; back-adjusted; `bist30`/`bist100` PIT-flag).
- PIT üyelik: `data/clean_universe/pit_membership_2019_2026.parquet`
  (`in_bist30`/`in_bist100` bool, günlük, **2019-01-02 → 2026-05-26**).
- Investable liste (statik): `config.yaml → portfolio.tickers` = **57 isim** (satır-içi "58"
  yorumu bayat; gerçek sayım 57). BIST30 + seçili BIST100.

### A.3 — Kesişim harness'ı — **KURULDU (counts-only, getiri-YOK)**
`scripts/probe/rr_y1_019_vbts_universe_intersection.py`: bir olay-tablosu
(ticker, level, start_date, end_date, announce_ts, is_escalation) verildiği an,
**PIT üyeliği olay-tarihine-göre** (start_date ≤ son panel-günü; **look-ahead-safe**, bugünkü
üyeliğe-DEĞİL) join'ler ve sayımları üretir: toplam-olay, distinct-ticker, yıl/seviye-dağılımı,
seviye-bazlı kesişim (clean-panel-içi / investable-57-içi / BIST30 / BIST100⊃30 / dışarı).
Getiri/CAR/fiyat-tepkisi **okunmaz** (Faz-2). Olay-tablosu yoksa erişim-durumunu basıp 0-çıkar
(CI-güvenli; ağ-çağrısı içermez).

---

## B. Online erişim haritası (READ-ONLY; hesap/auth/satın-alma/indirme YOK; 2026-06-13)

Tedbir akışı kanonik olarak **KAP** disclosure'larında (paya özgü, günlük, PIT-damgalı) yaşar.
Erişilebilir-ücretsiz-public yollar tek-tek prob edildi:

| Yol | Yöntem | Sonuç |
|---|---|---|
| KAP legacy `memberDisclosureQuery` | cookie-warmed POST (Chrome-UA) | **ReadTimeout** (WAF tarpit; endpoint emekli) |
| KAP yeni frontend backend host | tam-tarayıcı-header GET | **DNS getaddrinfo failed** — public-DNS'te çözülmüyor (split-horizon/iç-host) |
| Borsa sitesi kök + `/duyurular` (bare-path) | GET | 200 OK, ama **yalnız kural-düzeyi** duyuru; paya-özgü tedbir satırı SIFIR |
| Borsa sitesi `www` derin-link | GET | server disconnect (RemoteProtocolError) |
| Üçüncü-taraf agregatör disclosure data endpoint | GET + XHR header | **401 Unauthorized** (auth-gated) |
| Borsa geçmişe-dönük tedbir arşivi | (n/a) | **ücretli veri ürünü** — no-purchase kısıtıyla dışlandı |

**Önemli ayrım:** Bu bir *erişim* duvarı, veri-*yokluğu* değil. Tedbir akışı KAP'ta gerçekten
var, PIT-damgalı ve makine-okunur — ama **bu makineden erişilebilir ücretsiz/auth-suz/public
read-only yollarla edinilemiyor**: KAP'ın programatik yüzeyi relaunch-sonrası WAF/CORS-duvarlı,
agregatör auth-gated, geçmiş-arşivi ücretli. Maintainer kılavuzu uyarınca **duvar bir bulgudur,
aşmak için hack uygulanmadı** (paket-kurulumu yok, auth-bypass yok, paywall-aşımı yok,
paya-özgü HTML kazıma cobbling'i yapılmadı — düşük-bütünlüklü kısmi-panel üretmektense
dürüst-erişim-duvarı raporlandı).

---

## C. Step-bazlı bulgular (hüküm-değil — olgu)

**Step-1 (veri-fizibilitesi):** Span ex-ante donduruldu (2024-06 → 2026-06). Edinim **upstream
bloke** — yukarıdaki erişilebilir yolların hiçbiri paya-özgü (ticker, level, tarih) tedbir
satırı vermedi. Span sonuç-bağımlı hiç-tüketilmedi (result-driven genişletme/daraltma olmadı;
edinim daha-başlamadan duvara-çarptı). Kapsam-notu: PIT üyelik paneli 2026-05-26'da biter →
span'ın son ~2 haftası üyelik-flag'siz kalırdı (edinilebilseydi raporlanacak coverage-kenarı).

**Step-2 (evren-kesişimi — *karar-verici*):** **ÖLÇÜLMEDİ** (Step-1 erişim-duvarı yüzünden
upstream-bloke). **Varsayılmadı da** — kesişim-oranı için gerçek olay gerekir; harness hazır,
paydalar hazır, ama olay-tablosu yok. Pozitif fizibilite-olgusu: paydalar (clean-panel + 57
investable) + PIT-join harness'ı KURULU → olay-paneli edinildiği **an** kesişim tek-komutla
çıkar. BIST50 ayrımı PIT-panelde yok (yalnız BIST30/BIST100); sınıflama BIST30 / BIST100(⊃30) /
dışarı.

**Step-3 (tradability — negatif-görüş mümkün mü):** Yerleşik düzenleyici olgulardan **tam
değerlendirilebilir** (yeni-ölçüm gerektirmez):
- **Açığa satış perakende için fiilen kapalı.** Piyasa-geneli yasak (Şub-2023→Oca-2025 tam;
  Oca-2025 BIST-50 istisnası; Mar-2025 yeniden-sıkılaştırma). Repo'nun kendi `RR-Y1.md` kaydı
  bunu doğrular ("bireysel açığa satış pratikte İMKANSIZ").
- **VBTS Kademe-1'in kendisi** tam-tedbir-isimlerinde açığa-satışı yasaklar → mekanizma-açısından
  en-güçlü adayların *üstünde* short yapısal olarak imkansız (tedbir devredeyken).
- **SSF/warrant rotası yok:** Tedbire-giren isimler ezici-çoğunlukla düşük-likidite spekülatif
  paylar; tek-hisse-futures/warrant'ları (perakende hesabın yegâne negatif-görüş yolu) bu
  isimlerde genelde mevcut-değil.
- **Brüt takas maliyeti:** Tedbirli isme long-girişte T+2 ön-finanse nakit zorunluluğu → long
  tarafa ek-sürtünme.
- **Hüküm:** Negatif-görüş ifadesi **yapısal olarak kapalı** → aday **inşa-gereği yalnız
  long-only avoid/exit ekranı**. (Negatif-bulgu yumuşatılmadı.)

**Step-4 (Faz-2 çerçevesi — *belirtildi, KOŞULMADI, hiçbir-şey-DONDURULMADI*):** Onaylanırsa
Faz-2 dual-layer iki-paralel-rapor üretir:
- **Realistic katman (verdict katmanı):** tam işlem-maliyeti + slippage + spread + brüt-takas
  maliyeti + sonraki-seans-açılış execution-zamanlaması; **long-only** ifade.
- **Ideal/frictionless katman (concept-ledger, ASLA-verdict):** maliyet=slippage=spread=0,
  AMA look-ahead-safe + survivorship-clean + t→t+1 zamanlama **korunur** (sıfır-sürtünme yalnız
  *para*-sürtünmesi; zaman-oku/nedensellik fiziksel-yasa, gevşetilmez). Frictionless katman
  "olgu var-mı / temiz yönsel-sinyal veriyor-mu"yu tradability'den bağımsız yanıtlar.
- Olay-çalışması yapısı: tedbir-girişi etrafında kümülatif anormal getiri (CAR), temiz
  total-return endeksine-göre, **tedbir-seviyesi kesit** (üst-kademe-girişleri en-güçlü
  mekanizma-vakaları). Keep-bar adayları + embargo/holdout yapısı Stage-0 öncesi belirlenir.
- **Eşleme kuralı:** güçlü ideal-katman sinyali + ölümcül tradability-duvarı → **save/wait +
  concept-ledger**, mezarlık-DEĞİL. (Ön-kayıt ve mod-seçimi sonra, herhangi aday görülmeden.)

---

## D. Karar-kapısı (probun yegâne çıktısı) — üç-dal

- **DATA-INFEASIBLE:** panel-sığ/olaylar-kurtarılamaz → save/wait, Faz-2-yok.
- **UNIVERSE-DISJOINT + ideal-katman-ilgisi-yok:** olaylar held-evrene-değmez ve kataloglanacak
  olgu-yok → save/wait.
- **PHENOMENON-MEASURABLE:** temiz olay-paneli var ve Faz-2 etkiyi yanıtlayabilir → Faz-2-öner
  (ayrı soğuk-karara bağlı).

### Gözlenen-duruma göre hüküm: **🟡 DATA-INFEASIBLE (erişilebilir-ücretsiz-yollarla) → save/wait**

Edinilebilir read-only public yollarla bir örnek-VBTS-paneli bile çıkarılamadı (B-tablosu).
Bu **erişim** duvarıdır, veri-yokluğu değil — olaylar KAP'ta PIT-damgalı/makine-okunur olarak
var. Dolayısıyla:
- **save/wait** (mezarlık-DEĞİL): hiçbir frozen-Stage-0 koşulmadı, hiçbir getiri ölçülmedi,
  X₂ kavramı hiç açılmadı. Ölçülmüş-negatif yok → graveyard yanlış-sınıflama olurdu.
- **Yeniden-açma somut-edinim-rotasına bağlı:** (a) tek-seferlik ücretli geçmiş tedbir-arşivi,
  (b) auth'lu vendor/agregatör feed'i, veya (c) server-side KAP fetch. Bunlardan biri gelince
  harness kesişimi (Step-2) anında ölçer.
- **Bağımsız ikinci-kapı (Step-3):** edinim çözülse-bile tradability **realistic katmanı
  yapısal olarak long-only-ekrana indirger** (short yapısal-kapalı). Aday'ın realistic-değeri,
  *en-iyi-ihtimalle*, tedbirli-isimleri held-evrende avoid/exit eden bir ekran; bunun
  non-vacuous-luğu held-evren-kesişimine bağlı (ölçülmedi). Faz-2'nin asıl bilimsel-değeri
  **ideal-katman olgu-kataloğu** olur (olgu gerçek mi), ve o da yalnız bir edinim-rotası
  finanse-edilirse anlamlı.

**Beklenti-kalibrasyonu (yorum, hüküm-değil):** VBTS tasarımı-gereği anormal-volatilite
isimlerini hedefler — bunlar ezici-çoğunlukla BIST30/100-dışı spekülatif mikro-kaplar. Bu,
held-evren-kesişiminin düşük (UNIVERSE-DISJOINT-eğilimli) olacağına dair *önsel* beklentidir;
ama bu prob onu **ölçmedi, varsaymıyor** — edinim açıldığında ölçülecek.

---

## Caveat'lar
- **Yalnız fizibilite — getiri/CAR/fiyat-tepkisi ölçülmedi** (Faz-2 kapsamı; counts-only harness
  bile getiri okumaz).
- Erişim-probları read-only/public/auth-suz; ham-bülten artefaktı disk-dışına commit-edilmedi
  (yalnız erişim-durumu özeti + harness + bu rapor kalıcıdır).
- Kesişim paydası **bugünkü statik investable liste** (`config.yaml`, 57 isim); span-içi
  üyelik-değişimi modellenmedi — düzeltme-değil, dürüstlük-kaydı.
- PIT üyelik paneli 2026-05-26'da biter; frozen span'ın son-iki-haftası üyelik-flag'siz olurdu.
- BIST50 PIT-panelde yok; sınıflama BIST30 / BIST100(⊃30) / dışarı.
- Tradability hükmü (Step-3) yerleşik düzenleyici-olgulara dayanır (task + repo `RR-Y1.md`);
  yeni-ölçüm değildir.
- "DATA-INFEASIBLE" *erişilebilir-ücretsiz-yollar* için geçerlidir; ücretli/auth'lu/server-side
  rota bunu değiştirir → save/wait (PERMANENT-değil).

Harness: [`scripts/probe/rr_y1_019_vbts_universe_intersection.py`](../../scripts/probe/rr_y1_019_vbts_universe_intersection.py).
