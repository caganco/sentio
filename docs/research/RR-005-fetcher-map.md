# RR-005: BIST Veri Kaynakları Fetcher Haritası — robots.txt / auth / format / rate-limit / ToS

> **Tip:** Operasyonel fetcher haritası (scraping mekaniği).
> **Tarih:** 22 May 2026
> **Yöntem:** Read-only canlı kanıt — robots.txt verbatim okuma + tek-atış endpoint probe (2026-05-22).
> **İlişki:** Bu rapor [RR-001](RR-001-fintables-takas-scraper.md) (veri mevcudiyeti) ve
> [RR-002](RR-002-akd-terminalleri-python.md) (terminal/fiyat envanteri) raporlarını **tekrarlamaz**;
> onları yalnızca *fetch mekaniği* (robots, auth wall, canlı format, rate-limit, ToS) açısından
> günceller ve doğrular. Veri kullanımı/alpha kararları için RR-001/RR-002'ye bakın.

---

## TL;DR

- **En kritik bulgu — İş Yatırım'ın tüm JSON veri endpoint'leri kendi robots.txt'i tarafından yasaklı.**
  Sitenin canlı robots.txt'i `Disallow: /_layouts/` içeriyor; tüm Python kütüphanelerinin kullandığı
  `…/_layouts/15/Isyatirim.Website/Common/Data.aspx/HisseTekil` endpoint'i bu dizinin altında →
  **teknik olarak robots-disallowed.** HTML analiz sayfaları (`/tr-tr/analiz/…`) ise robots-serbest.
  "Hangi endpoint robots-güvenli?" sorusunun net cevabı: **JSON endpoint'leri DEĞİL, HTML sayfaları EVET.**
- **RR-001'deki İş Yatırım URL formatı artık bozuk (stale).** Eski `…&enddate={DD-MM-YYYY}.json`
  formatı bugün backend'de Java date-parse hatası veriyor (`Failed to convert … to java.time.LocalDate`).
  **Çalışan format `.json` ekini DROP ediyor:** `…&enddate=22-05-2026` (sonek yok). Backend SharePoint
  `.aspx` path'inin arkasında Java/Spring'e taşınmış görünüyor. Ayrıca `HAO_PD` alanı = **halka açık
  piyasa değeri (free-float), yabancı oran DEĞİL** — yabancı oran ayrı kaynaktan gelir (RR-001 §E).
- **Terminaller (Gedik, Ak Yatırım) fetch'lenemez; kapalı SPA + lisanslı feed.** Gedik Trader =
  **dxFeed/Devexperts** backend (Matriks değil — RR-002 gruplamasının düzeltmesi); Ak Yatırım = **TradeAll**,
  Matriks/Foreks/DirectFN kanalları. İkisinde de public REST yok, web app auth-walled SPA. BIST/MKK'da
  hisse-bazlı *günlük* takas hâlâ lisanslı (Duyuru 631); **ücretsiz olan yalnızca aggregate/aylık** seri
  (`borsaistanbul.com` Foreign Investor Transactions = aylık, Short Sales = haftalık) ve datastore CSV bültenleri.

---

## Kaynak bazlı fetcher analizi

### 1) mkk.com.tr (Merkezi Kayıt İstanbul)

| Boyut | Bulgu (2026-05-22) |
|---|---|
| **robots.txt** | Drupal varsayılanı. `User-agent: *`. Disallow: `/core/`, `/profiles/`, `/admin/`, `/comment/reply/`, `/filter/tips`, `/node/add/`, `/search/`, `/user/register`, `/user/password`, `/user/login`, `/user/logout`, `/media/oembed`, `/*/media/oembed` (+ `/index.php/…` varyantları). Allow: `/core/`,`/profiles/` altındaki .css/.js/.gif/.jpg/.png/.svg. **Crawl-delay YOK, Sitemap YOK.** → `/veri-hizmetleri/…` (PDF bültenler) **robots-serbest.** |
| **Auth** | Public PDF bültenler: auth YOK. PUSULA / e-VERİ / `apiportal.mkk.com.tr`: **üyelik + sözleşme wall** (aracı kurum/banka). |
| **Format** | Aylık Piyasa Bülteni & Borsa Trendleri = **PDF** (statik `<a href>` link, `requests`+`pdfplumber` yeterli, Selenium gereksiz — RR-001 §3A). Hisse-bazlı = vendor feed (lisanslı). |
| **Rate-limit** | Empirik ölçülmedi (read-only). Statik PDF host; saldırgan limit gözlenmedi. Nazik davran (≤1 req/s). |
| **ToS** | Public bülten = ücretsiz. **Hisse-bazlı günlük yerli/yabancı saklama 2013 Duyuru No. 631 ile 10 iş günü gecikmeli + yalnızca veri dağıtım sözleşmeli kuruluşlara** (RR-001 §1A verbatim). KVKK/telif dikkat. |
| **Public takas/AKD endpoint var mı?** | **HAYIR.** Ücretsiz JSON/CSV takas endpoint'i yok; en zengin metrikler (saklayıcı kurum sayısı) vendor arkasında. |
| **Fetch verdict** | 🟢 PDF bültenler (aggregate). 🔴 Hisse-bazlı günlük takas (lisans). |

### 2) borsaistanbul.com + datastore.borsaistanbul.com

| Boyut | Bulgu (2026-05-22) |
|---|---|
| **robots.txt** | `www.borsaistanbul.com`: **tamamen açık** — `User-agent: *` / `Allow: /`. Crawl-delay yok. |
| **Auth** | Ana site sayfaları auth yok. `datastore.borsaistanbul.com`: aggregate CSV/captcha gibi public uçlar anonim; **dosya indirme + kişisel uçlar login gerektirir** → custom `x-auth-token` header + captcha-gated login (tam akış **§2.1**'de, eski VERIFY çözüldü). |
| **Format** | Tarihsel dosyalar **2015-08-01'den itibaren yalnızca datastore'da**, ana siteden kaldırılmış. **CSV** (ondalık `.`/binlik `,` regional ayar gerekir). Spec: `datastore.borsaistanbul.com/assets/files/DataStore_Veri_Bildirim_ve_Kabul_Formatlari.pdf`. |
| **Free vs licensed** | `/en/data/equity-market-data` ürün listesi: **ücretsiz/yayınlanan** → Foreign Investor Transactions (**Aylık**/Historical), Short Sales (**Haftalık**), Most Active Equities & Members (Haftalık), Member rankings, Off-Exchange (Aylık). **Lisanslı** → real-time / Level-2+ / hisse-bazlı günlük takas ("Data Distribution Agreement" bölümü). |
| **Rate-limit** | Empirik ölçülmedi. Statik CSV/ZIP host. |
| **ToS** | robots açık olsa da **veri redistribüsyonu Veri Dağıtım Sözleşmesi gerektirir** ("borsa istanbul verileri üçüncü şahıslara dağıtılamıyor" — RR-002 r10.net). Kişisel kullanım için ücretsiz bülten indirme uygun. |
| **Public data API/CSV var mı?** | **EVET, sınırlı:** datastore CSV (EOD/bülten, aggregate). Resmi REST API yok; gerçek-zamanlı/derin veri lisanslı. |
| **Fetch verdict** | 🟢 datastore CSV (aggregate/EOD). 🟡 login: captcha-gated `x-auth-token` (bkz §2.1, çözüldü). 🔴 real-time/Level-2 takas (lisans). |

#### 2.1) DataStore Auth Akışı — login endpoint tespiti (takip araştırması, 2026-05-22)

**Stack:** Ember.js SPA (`data-market-client`) + Node/Express backend + önde **F5 BIG-IP ASM WAF** (`TS…` cookie). API namespace same-origin: **`/api`** (CSP `connect-src 'self'`). Kanıt: app bundle (`assets/data-market-client-*.js`) statik analizi + 2 yetkisiz GET probe.

**Auth modeli:** Custom `authentication` Ember service. **Bearer = `x-auth-token` HTTP header**, değeri client-okunabilir `token` cookie'sinden gelir (`$.cookie("token")`). Tüm yetkili çağrılar `utils/api.__ajax` üzerinden `beforeSend → setRequestHeader("x-auth-token", $.cookie("token"))` ekler. **JWT-in-body değil; header-token + cookie ikilisi.** Ayrıca server her yanıtta Express `sid` (HttpOnly, signed `s:` prefix) + F5 `TS…` cookie set eder.

| Akış | Endpoint | Method | İçerik / Not |
|---|---|---|---|
| **Login** | `/api/register-login` | **POST** | `{email, password, rememberUser, captcha, uacChecked, pditChecked}`. jQuery `$.post` default → **`application/x-www-form-urlencoded`** (wire content-type = VERIFY). |
| Captcha | `/api/get-captcha?<ts>` | GET | **JPEG** (doğrulandı: `200 image/jpeg` 2502B). Login'de zorunlu alan. |
| Session doğrulama | `/api/login-control` | GET | `x-auth-token` ile; init+1sn'de + işlem sonrası çağrılır. Tokensız → **`401 "Authorization required."`** (doğrulandı). **"Refresh"e en yakın mekanizma — token ROTASYONU YOK.** |
| **Logout** | `/api/logout` | **PUT** | `x-auth-token` ile; `204` → client `token`+`datastoreCurrentUser` cookie'lerini siler (`deleteAuthCookie`). |
| Şifre/aktivasyon | `/forgot-password`{email,captcha}, `/reset-password`{key,password}, `/expire-password`, `/send-email-password-forget`, `/change-password`, `/send-activation`{email,captcha} | POST | Hepsi `/api` altında. |
| Profil/sepet/dosya | `/change-email`,`/change-name`,`/get-basket-items`,`/save-basket-items`,`/update-basket-items`,`/university-list`; indirme `/api/file/<referenceId>` | GET/POST | `x-auth-token` header. |

**Login başarısında** (`creatAuthCookie`): `token` + `datastoreCurrentUser` (JSON user) cookie set edilir — path=`/`, domain=`borsaistanbul.com`, secure. **`rememberUser=true` → cookie 30 gün; aksi halde session cookie** (tarayıcı kapanınca silinir).

**Token ömrü:** Cookie tarafı **30 gün (rememberUser) / session**. Server-side token geçerlilik süresi JS'ten görünmüyor → **CANLI login ile doğrulanmalı** (token JWT ise `exp` decode; değilse `login-control` 401 dönene kadar gözlem). **Refresh/rotation endpoint YOK** — uzun oturum tek yolu rememberUser + periyodik `login-control`.

**Rate-limit / bot koruması:** (1) **CAPTCHA** her login denemesinde zorunlu (insan-döngüde) → düz `requests` ile scriptli login **mümkün değil**. (2) Önde **F5 BIG-IP ASM** → muhtemel IP-bazlı edge limiting; standart `x-ratelimit-*` header expose edilmiyor (401 yanıtında yok). Sayısal eşik **kasıtlı tetiklenmedi** (hesap kilidi/abuse riski; read-only ilke).

**Playwright mı requests mı? → İkisi birden, sıralı:**
1. **Playwright (headful) / manuel tarayıcı** ile *tek seferlik* login — captcha insan tarafından çözülür — sonra `token`+`datastoreCurrentUser`(+`sid`) cookie'leri bir **session dosyasına** kaydedilir (mevcut `fintables_session.json` pattern'iyle birebir).
2. Sonrasında **düz `requests` yeterli:** `headers={"x-auth-token": <kayıtlı token>}` ile `/api/...` ve `/api/file/<id>`. `rememberUser=true` → yeniden login ~ayda bir.

→ Captcha nedeniyle **tam-otomatik headless login YOK**; bootstrap insan-destekli, fetch otomatik. Mevcut [bist_datastore_connector.py](../../src/signals/layers/connectors/bist_datastore_connector.py) bu auth'u hiç yapmıyor (`GET /` → `read_csv`, x-auth-token yok) — gerçek dosya indirme için yeniden yazım gerekir (ayrı SPEC).

> **⚠ Güvenlik (aksiyon gerektirir):** `.gitignore:29` `.fintables_session.json` (başta nokta) yazıyor, ama repo'daki dosya `fintables_session.json` (**noktasız**) — `git check-ignore` **ignore EDİLMİYOR** doğruladı. Auth cookie içeren bu dosya `git add -A` ile yanlışlıkla commit'lenebilir. DataStore için oluşturulacak `datastore_session.json` dahil, `.gitignore`'a `*_session.json` pattern'i eklenmeli. (Bu görev read-only — düzeltme ayrı onay bekliyor.)

### 3) Gedik Yatırım — Gedik Trader terminali

| Boyut | Bulgu (2026-05-22) |
|---|---|
| **robots.txt** | `web.gediktrader.com/robots.txt` → **HTTP 404** (robots yok; SPA app shell). |
| **Auth** | Web app **auth-walled** trading SPA. Hesap + canlı veri lisansı gerekir. |
| **Veri backend** | **dxFeed (Devexperts iştiraki)** — Devexperts case study + Google Play `com.devexperts.dxmobile.gedik` doğruluyor. Forex tarafı Foreks CDN (`gedik-cdn.foreks.com`) + MT4. **RR-002 düzeltmesi:** Gedik = Matriks değil, Devexperts/dxFeed altyapısı. |
| **Format / API** | Public REST **YOK**. dxFeed WebSocket/feed lisanslı ve auth'lu; tarayıcıdan token'lı. BIST verisi BIST-lisanslı dağıtıcı üzerinden (real-time/delayed/EOD). |
| **Rate-limit / ToS** | N/A (erişilemez). ToS kişisel-olmayan otomasyonu + redistribüsyonu yasaklıyor (RR-002). Network reverse-engineering toplulukta kayıtlı değil. |
| **Fetch verdict** | 🔴 Programatik fetch için **uygun değil** (auth + lisans + ToS). Network trafiği analizi **VERIFY/handoff** — canlı oturum + DevTools gerektirir, bu read-only taramada yapılamadı. |

### 4) Ak Yatırım — TradeAll terminali

| Boyut | Bulgu (2026-05-22) |
|---|---|
| **robots.txt** | `tradeall.com/robots.txt` → yalnızca `User-agent: iisbot/1.0 (+http://www.iis.net/iisbot.html)` / `Allow: /`. **`User-agent: *` bloğu YOK, hiçbir Disallow yok** → genel crawler için kısıtlama tanımlanmamış (kural yok = serbest), ama bu bir *veri* endpoint'i değil kurumsal site. |
| **Auth** | İşlem platformu auth-walled. `veri-yayin-platformlari.aspx` body JS-render (WebFetch yalnızca başlık gördü). |
| **Veri backend** | **TradeAll** markası; veri kanalları **Matriks / Foreks / DirectFN** (arama sonucu doğruladı). Public REST API **yok**. |
| **Format / API** | Programatik veri yok; terminal GUI. dxFeed ilişkisi bu kaynakta görülmedi. |
| **Rate-limit / ToS** | N/A (erişilemez). Terminal ToS otomasyon/redistribüsyon kısıtlı (RR-002 — tüm aracı kurum terminalleri için ortak). |
| **Fetch verdict** | 🔴 Programatik fetch için **uygun değil**. Network trafiği analizi **VERIFY/handoff** (canlı login gerekir). |

### 5) isyatirim.com.tr (+ arastirma.isyatirim.com.tr)

| Boyut | Bulgu (2026-05-22) |
|---|---|
| **robots.txt — www** | Verbatim: `User-agent: *` / `Disallow: /_layouts/` / `Disallow: /_vti_bin/` / `Disallow: /_catalogs/` / `Disallow: /uyelik-islemleri` / `Disallow: /membership-procedures` / `Disallow: /arama-sonuclari` / `Disallow: /search-results` / `Sitemap: https://www.isyatirim.com.tr:443/sitemap.xml`. **Crawl-delay yok.** |
| **robots.txt — arastirma** | WordPress/Yoast. Disallow: `/wp-admin/` (+ woocommerce upload dizinleri, `/*?add-to-cart=`). Allow: `/wp-admin/admin-ajax.php`. Sitemap: `sitemap_index.xml`. → "Günlük Yabancı Oranları" kategori sayfaları **robots-serbest.** |
| **Robots-SAFE haritası** | 🔴 **`/_layouts/15/Isyatirim.Website/Common/Data.aspx/*`** (HisseTekil ve tüm JSON data endpoint'leri) → `/_layouts/` Disallow altında, **robots-DISALLOWED.** 🟢 `/tr-tr/analiz/hisse/…` HTML analiz/şirket kartı sayfaları → disallow listesinde yok, **robots-serbest** (borsapy `foreign_ratio` bu HTML'i parse eder). 🟢 `arastirma.…/category/gunluk-raporlar/gunluk-yabanci-oranlari/` → serbest. |
| **Auth** | JSON endpoint kayıt gerektirmiyor ("yarı-public"); ama robots-disallowed. |
| **Format (canlı doğrulandı)** | `HisseTekil` JSON: top-level `{ok, errorCode, errorDescription, transactionId, value:[…]}`. `value[]` alanları: `HGDG_HS_KODU, HGDG_TARIH, HGDG_KAPANIS, HGDG_AOF, HGDG_MIN, HGDG_MAX, HGDG_HACIM, END_*, DD_* (döviz), DOLAR_BAZLI_*, SERMAYE, PD, HAO_PD, HG_*`. **= fiyat/hacim/değerleme. Yabancı oran YOK** (`HAO_PD` = free-float piyasa değeri, foreign DEĞİL). |
| **⚠ Format değişikliği** | **Eski `.json` sonekli format (RR-001) artık BOZUK:** `…enddate=22-05-2026.json` → `Failed to convert value of type 'java.lang.String' to required type 'java.time.LocalDate'`. **Çalışan: `…enddate=22-05-2026` (sonek yok).** Backend `.aspx` path'inin arkasında Java/Spring. |
| **Rate-limit** | Empirik ölçülmedi (read-only, hammering yapılmadı). RR-001 §3E: Cloudflare benzeri "Please wait while your request is being verified" challenge gözlemi → **≤1-2 req/s + User-Agent rotation + 24h cache (requests-cache)** önerisi geçerli. |
| **ToS** | `isyatirimhisse` PyPI README verbatim: *"yalnızca kişisel kullanım amaçları için tasarlanmıştır"* (RR-001 §1E). + robots `/_layouts/` disallow → JSON endpoint scraping **gri-kırmızı**; HTML sayfaları gri. Ticari kullanımda lisans. |
| **Fetch verdict** | 🟡 HTML analiz sayfaları (robots-serbest, kişisel kullanım). 🔴/🟡 JSON `/_layouts/` endpoint'leri (robots-disallowed ama auth'suz çalışıyor — kişisel kullanım gri zon). |

---

## Konsolide Fetcher Karar Matrisi

| Kaynak | robots.txt | Auth | Format | Rate-limit (gözlem) | ToS | Fetch verdict |
|---|---|---|---|---|---|---|
| **mkk.com.tr** (PDF bülten) | 🟢 `/veri-hizmetleri/` serbest | Yok | PDF (statik) | Ölçülmedi | Ücretsiz; hisse-bazlı lisanslı | 🟢 aggregate / 🔴 hisse-bazlı |
| **mkk PUSULA/e-VERİ/apiportal** | — | Üyelik wall | — | — | Sözleşme | 🔴 |
| **borsaistanbul.com** | 🟢 `Allow: /` | Yok | HTML | Ölçülmedi | Açık (sayfa) | 🟢 |
| **datastore.borsaistanbul.com** | n/a (SPA) | VERIFY (Giriş?) | CSV/ZIP (2015-08-01+) | Ölçülmedi | Redistribüsyon = sözleşme | 🟢 EOD/aggregate / 🟡 login |
| **Gedik Trader** | 🔴 404 (SPA) | Auth-walled | dxFeed feed (lisanslı) | n/a | Otomasyon yasak | 🔴 (network = VERIFY) |
| **Ak Yatırım TradeAll** | iisbot-only | Auth-walled | Matriks/Foreks/DirectFN GUI | n/a | Otomasyon yasak | 🔴 (network = VERIFY) |
| **isyatirim `/_layouts/` JSON** | 🔴 Disallow | Yok (yarı-public) | JSON (fiyat/hacim) | ≤1-2 req/s öner | "kişisel kullanım" | 🟡/🔴 robots-disallowed |
| **isyatirim HTML analiz** | 🟢 serbest | Yok | HTML (foreign_ratio dahil) | ≤1-2 req/s öner | "kişisel kullanım" | 🟡 |
| **arastirma.isyatirim** | 🟢 serbest (kategori) | Yok | HTML rapor | Ölçülmedi | Kişisel kullanım | 🟡 |

🟢 robots-güvenli + erişilebilir · 🟡 gri zon (kişisel kullanım, dikkatli) · 🔴 yasak/erişilemez

---

## RR-001/RR-002'ye Göre Düzeltme & Güncellemeler (Delta)

1. **İş Yatırım URL formatı stale →** `.json` soneki backend'de date-parse hatası veriyor; çalışan format soneki dropluyor. Fetcher kodu güncellenmeli (RR-001 §4D pseudo-code `HisseTekil?…enddate={end}.json` satırı artık çalışmaz).
2. **`HAO_PD` ≠ foreign ratio.** Free-float piyasa değeri. Yabancı oran için ayrı kaynak (HTML şirket kartı / arastirma günlük rapor).
3. **Gedik backend = dxFeed/Devexperts**, RR-002'nin "Matriks/Foreks/İdeal tabanlı" toplu gruplamasının istisnası.
4. **İş Yatırım robots.txt'i veri endpoint'lerini açıkça yasaklıyor** (`/_layouts/`) — RR-001 bunu "gri zon" derken bu rapor robots düzeyinde **disallowed** olduğunu netleştiriyor.

---

## Caveats / VERIFY (Canlı Doğrulama Gerektiren)

1. **Rate-limit'ler empirik ölçülmedi.** Read-only ilke gereği hiçbir host'a yük testi yapılmadı; sayılar RR-001 gözlemine + sağduyuya dayalı öneridir, ölçüm değildir.
2. ~~datastore.borsaistanbul.com login modeli VERIFY.~~ **ÇÖZÜLDÜ (§2.1, 2026-05-22):** auth = captcha-gated `POST /api/register-login` → `x-auth-token` header + `token` cookie (30g/session). Kalan VERIFY yalnızca **server-side token TTL** ve **login wire content-type** — canlı login gerektirir (captcha + creds).
3. **Gedik & Ak Yatırım network trafiği analizi yapılamadı (handoff).** İkisi de auth-walled SPA; gerçek network endpoint envanteri için **canlı login + tarayıcı DevTools** gerekir — bu read-only WebFetch taramasında erişilemez. Backend kimliği (dxFeed / Matriks-Foreks-DirectFN) public kaynaktan doğrulandı; endpoint-seviye trafiği VERIFY olarak işaretli.
4. **İş Yatırım backend geçişi** (`.aspx` path → Java/Spring) hata mesajından çıkarıldı; resmi duyuru bulunamadı. Format'ın ileride tekrar değişme riski yüksek; fetcher defensive yazılmalı.
5. **robots.txt anlık görüntü.** Tüm robots.txt içerikleri 2026-05-22 itibarıyladır; siteler güncelleyebilir, fetcher öncesi yeniden okunmalı.
6. **ToS yorumu hukuki tavsiye değil.** "Kişisel kullanım için scraping" Türk hukukunda net değil (RR-001/RR-002 caveat). Ticari sistemde lisans değerlendirilmeli.

---

## Kaynaklar (canlı doğrulanmış, 2026-05-22)

- robots.txt verbatim: `mkk.com.tr/robots.txt`, `borsaistanbul.com/robots.txt`, `isyatirim.com.tr/robots.txt`, `arastirma.isyatirim.com.tr/robots.txt`, `web.gediktrader.com/robots.txt` (404), `tradeall.com/robots.txt`
- Endpoint probe: `isyatirim.com.tr/_layouts/15/Isyatirim.Website/Common/Data.aspx/HisseTekil` (canlı JSON, format doğrulandı)
- Backend kimliği: devexperts.com case study (Gedik/dxFeed); Google Play `com.devexperts.dxmobile.gedik`; tradeall.com (Ak Yatırım veri kanalları)
- BIST veri ürünleri: `borsaistanbul.com/en/data/equity-market-data`, `datastore.borsaistanbul.com` (+ `/library`, spec PDF)
- Çapraz referans: [RR-001](RR-001-fintables-takas-scraper.md) §1,§3,§4 · [RR-002](RR-002-akd-terminalleri-python.md) §3,§4
