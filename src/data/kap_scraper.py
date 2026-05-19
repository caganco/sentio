"""KAP (Kamuyu Aydınlatma Platformu) disclosure scraper.

Katman 1 — KAP API  : POST memberDisclosureQuery (kısa timeout, sıkça engelleniyor)
Katman 2 — Google News RSS: Türkçe haber özeti, no extra deps
Katman 3 — Boş placeholder: Her şey başarısız olursa loglama
"""
import logging
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Literal
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

# ── Source-type constants ─────────────────────────────────────────────────────

SOURCE_TYPE = Literal["kap_official", "news_media", "unknown"]

KAP_OFFICIAL_DOMAINS: set[str] = {
    "kap.org.tr",
    "www.kap.org.tr",
}

NEWS_MEDIA_DOMAINS: set[str] = {
    "bloomberght.com",
    "ekonomim.com",
    "haberturk.com",
    "hurriyet.com.tr",
    "sabah.com.tr",
    "milliyet.com.tr",
    "dunya.com",
    "paraanaliz.com",
}


@dataclass
class NewsItem:
    title: str
    url: str
    published: datetime
    symbol: str
    source_type: SOURCE_TYPE
    source_domain: str
    summary: str | None = None


def classify_source_type(url: str) -> SOURCE_TYPE:
    """Extract domain from url and return the matching SOURCE_TYPE."""
    if not url:
        return "unknown"
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if not domain:
            return "unknown"
    except Exception:
        logger.warning("classify_source_type: could not parse URL '%s'", url)
        return "unknown"

    # KAP official: exact match or subdomain ending in kap.org.tr
    if domain in KAP_OFFICIAL_DOMAINS or domain.endswith(".kap.org.tr"):
        return "kap_official"

    # Strip leading www. for media domain matching
    bare = domain[4:] if domain.startswith("www.") else domain
    if bare in NEWS_MEDIA_DOMAINS or domain in NEWS_MEDIA_DOMAINS:
        return "news_media"

    return "unknown"


def parse_rss_item(raw_item: dict, symbol: str = "") -> NewsItem:
    """Parse a Google News RSS raw dict into a NewsItem with source tagging."""
    title = raw_item.get("title", "")
    url = raw_item.get("link", "")
    published_str = raw_item.get("published", raw_item.get("pubDate", ""))

    try:
        published = parsedate_to_datetime(published_str)
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
    except Exception:
        published = datetime.now(timezone.utc)

    try:
        source_domain = urlparse(url).netloc.lower() if url else ""
    except Exception:
        source_domain = ""

    source_type = classify_source_type(url)

    return NewsItem(
        title=title,
        url=url,
        published=published,
        symbol=symbol,
        source_type=source_type,
        source_domain=source_domain,
        summary=raw_item.get("summary"),
    )

# ── Sabitler ─────────────────────────────────────────────────────────────────
PORTFOLIO_TICKERS = ["AKSEN", "TTKOM", "TAVHL", "KCHOL", "ENERY"]
WATCHLIST_TICKERS: list[str] = []          # daily_update tarafından doldurulabilir
KAP_TIMEOUT = 6           # saniye — WAF genellikle bağlantıyı bu süreden sonra düşürüyor
NEWS_LOOKBACK_HOURS = 24  # son X saatteki haberler
MAX_NEWS_PER_TICKER = 5

KAP_API_URL = "https://www.kap.org.tr/tr/api/memberDisclosureQuery"
KAP_BASE    = "https://www.kap.org.tr"

GNEWS_URL = (
    "https://news.google.com/rss/search"
    "?q={query}&hl=tr&gl=TR&ceid=TR:tr"
)

_KAP_BLOCKED = False   # ilk timeout sonrası diğer ticker'ları atla

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9",
})

# ── Sınıflandırma ─────────────────────────────────────────────────────────────

CRITICAL_KEYWORDS = [
    "birleşme", "devralma", "m&a", "özel durum", "halka arz", "iflas",
    "sermaye azaltımı", "önemli sözleşme", "bilanço", "finansal sonuç",
    "kâr açıklandı", "zarar açıklandı", "earnings", "acquisition", "merger",
    "zorunlu pay alım",
]
IMPORTANT_KEYWORDS = [
    "temettü", "sermaye artırımı", "bedelsiz", "yönetim kurulu",
    "genel kurul", "yönetici değişikliği", "CEO", "CFO", "ihraç",
    "sukuk", "tahvil", "bono", "borç", "kredi",
]
NOISE_KEYWORDS = [
    "faaliyet raporu", "yıllık rapor", "kurumsal yönetim", "bilgi formu",
    "e-GKS", "EK-1", "ek bilgi", "düzeltme", "güncelleme",
]


def classify_disclosure(text: str) -> str:
    """CRITICAL / IMPORTANT / NOISE döndürür."""
    lower = text.lower()
    if any(k in lower for k in CRITICAL_KEYWORDS):
        return "CRITICAL"
    if any(k in lower for k in IMPORTANT_KEYWORDS):
        return "IMPORTANT"
    return "NOISE"


# ── KAP API denemesi ──────────────────────────────────────────────────────────

def _kap_api_warmup() -> None:
    """KAP session cookie al; POST öncesi gerekli."""
    try:
        SESSION.get(f"{KAP_BASE}/tr/bildirim-sorgu", timeout=6)
    except Exception:
        pass


def _fetch_kap_api(ticker: str) -> list[dict]:
    """KAP memberDisclosureQuery POST — başarısız olursa [] döner.
    İlk timeout'ta global _KAP_BLOCKED flag'ini set ederek diğer ticker'ları atlar.
    """
    global _KAP_BLOCKED
    if _KAP_BLOCKED:
        return []

    SESSION.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Referer": f"{KAP_BASE}/tr/bildirim-sorgu",
        "Origin": KAP_BASE,
    })
    payload = {
        "year": str(datetime.now().year),
        "pbType": "",
        "disclosureCategory": "",
        "member": ticker,
        "isLate": "",
    }
    try:
        r = SESSION.post(KAP_API_URL, json=payload, timeout=KAP_TIMEOUT)
        r.raise_for_status()
        raw = r.json()
    except requests.exceptions.Timeout:
        _KAP_BLOCKED = True   # WAF engeli — diğer ticker'ları atla
        return []
    except Exception:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=NEWS_LOOKBACK_HOURS)
    results = []
    for item in (raw if isinstance(raw, list) else []):
        # KAP yanıtı farklı field isimlerine sahip olabilir
        title = item.get("title") or item.get("subject") or item.get("disclosureType") or ""
        date_str = item.get("publishDate") or item.get("disclosureDate") or ""
        try:
            pub = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
        except Exception:
            pub = datetime.now(timezone.utc)

        if pub < cutoff:
            continue

        results.append({
            "source": "kap_api",
            "ticker": ticker,
            "title": title,
            "published": pub.isoformat(),
            "category": classify_disclosure(title),
            "url": item.get("url") or f"https://www.kap.org.tr/tr/bildirim/{item.get('id','')}",
        })
    return results[:MAX_NEWS_PER_TICKER]


# ── Google News RSS fallback ───────────────────────────────────────────────────

def _parse_rss_date(date_str: str) -> datetime:
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


def _fetch_gnews(ticker: str, company_name: str | None = None) -> list[dict]:
    """Google News RSS üzerinden son 24 saatteki haberleri çeker."""
    query_terms = [ticker]
    if company_name:
        query_terms.append(company_name)
    query_terms.append("KAP OR BIST OR bildirim")
    query = " ".join(query_terms)

    url = GNEWS_URL.format(query=requests.utils.quote(query))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=NEWS_LOOKBACK_HOURS)

    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception:
        return []

    results = []
    ns = {"media": "http://search.yahoo.com/mrss/"}
    for item in root.findall(".//item"):
        title_el  = item.find("title")
        link_el   = item.find("link")
        pubdate_el = item.find("pubDate")
        source_el  = item.find("source")

        title = title_el.text if title_el is not None else ""
        link  = link_el.text if link_el is not None else ""
        pub   = _parse_rss_date(pubdate_el.text if pubdate_el is not None else "")
        source_name = source_el.text if source_el is not None else "Google News"

        if pub < cutoff:
            continue

        results.append({
            "source": f"gnews:{source_name}",
            "ticker": ticker,
            "title": title,
            "published": pub.isoformat(),
            "category": classify_disclosure(title),
            "url": link,
        })

        if len(results) >= MAX_NEWS_PER_TICKER:
            break

    return results


# ── Ana fonksiyon ─────────────────────────────────────────────────────────────

def fetch_kap_news(
    portfolio_tickers: list[str] | None = None,
    watchlist_tickers: list[str] | None = None,
    *,
    company_names: dict[str, str] | None = None,
) -> dict:
    """
    KAP bildirimlerini toplar.

    Returns:
        {
          "fetched_at": ISO str,
          "source_used": "kap_api" | "gnews" | "none",
          "coverage_hours": 24,
          "total": int,
          "items": [ {source, ticker, title, published, category, url} ]
        }
    """
    tickers = list({*(portfolio_tickers or PORTFOLIO_TICKERS),
                    *(watchlist_tickers or WATCHLIST_TICKERS)})
    company_names = company_names or {}

    all_items: list[dict] = []
    source_used = "none"

    # ── Katman 1: KAP API ──────────────────────────────────────────────────
    _kap_api_warmup()
    kap_hits: list[dict] = []
    for ticker in tickers:
        items = _fetch_kap_api(ticker)
        kap_hits.extend(items)
        if items:
            time.sleep(0.3)   # polite delay

    if kap_hits:
        all_items = kap_hits
        source_used = "kap_api"

    # ── Katman 2: Google News RSS ──────────────────────────────────────────
    if not all_items:
        gnews_hits: list[dict] = []
        for ticker in tickers:
            items = _fetch_gnews(ticker, company_names.get(ticker))
            gnews_hits.extend(items)
            time.sleep(0.5)

        if gnews_hits:
            all_items = gnews_hits
            source_used = "gnews"

    # CRITICAL → IMPORTANT → NOISE, aynı kategoride yeniden eskiye
    _priority = {"CRITICAL": 0, "IMPORTANT": 1, "NOISE": 2}
    all_items.sort(key=lambda x: (_priority.get(x["category"], 3), x["published"]), reverse=False)

    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source_used": source_used,
        "coverage_hours": NEWS_LOOKBACK_HOURS,
        "total": len(all_items),
        "items": all_items,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    SEP = "=" * 65

    print(SEP)
    print("  KAP SCRAPER — Bildirim Tarama")
    print(SEP)
    print(f"  Portföy  : {', '.join(PORTFOLIO_TICKERS)}")
    print(f"  Lookback : Son {NEWS_LOOKBACK_HOURS} saat")
    print(SEP)

    result = fetch_kap_news()

    print(f"\n  Kaynak   : {result['source_used']}")
    print(f"  Toplam   : {result['total']} bildirim/haber")
    print(f"  Zaman    : {result['fetched_at'][:19]}")

    if result["items"]:
        print()
        print(f"  {'CAT':<10} {'TICKER':<8} {'KAYNAK':<20} BAŞLIK")
        print("-" * 65)
        for item in result["items"]:
            src_short = item["source"][:18]
            title_short = item["title"][:55]
            print(f"  {item['category']:<10} {item['ticker']:<8} {src_short:<20} {title_short}")
    else:
        print("\n  Son 24 saatte bildirim bulunamadı.")
        print("  → KAP API: WAF engeli (timeout)")
        print("  → Google News: Sonuç yok")

    print(f"\n{SEP}")
    print("  Tamamlandı.")
    print(SEP)
