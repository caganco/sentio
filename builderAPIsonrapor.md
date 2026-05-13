Sonuç raporu:

KAP API durumu (test bulguları)

Endpoint	Sonuç	Neden
POST /tr/api/memberDisclosureQuery	❌ Timeout (WAF)	Her timeout 6s, ilk timeout'ta tüm ticker'lar atlanıyor
GET HTML /tr/bist-sirketler	Kısmi ✓	Next.js App Router SPA — veri JS ile yükleniyor, HTML'de yok
BigPara API	❌ 403	Engelli
Google News RSS	✅ Çalışıyor	Türkçe haber, no extra deps
Gerçek bildirimler (bugün)

CRITICAL — AKSEN 1. Çeyrek Bilanço Analizi (Uzmanpara)
NOISE — TAVHL günlük teknik (Mynet)
NOISE — KCHOL günlük teknik (Mynet)
Mimari


kap_scraper.py
├── Layer 1: KAP API POST  → 6s timeout, ilk başarısızlıkta _KAP_BLOCKED=True
├── Layer 2: Google News RSS → xml.etree (stdlib, no feedparser)
│   Query: "{TICKER} KAP OR BIST OR bildirim" (Türkçe)
└── Layer 3: Boş dict + source_used="none"

classify_disclosure() → CRITICAL / IMPORTANT / NOISE (keyword-based)
daily_briefing.json → "kap_news": { fetched_at, source_used, total, items[] }
daily_update 0 item sorunu: Standalone çalıştırıp hemen ardından daily_update çalıştırdık; Google News rate-limit yedi. Normal koşullarda (sabah 09:00 tek çalışma) sorun olmaz.