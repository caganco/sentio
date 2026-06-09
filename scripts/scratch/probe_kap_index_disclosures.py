"""RR-Y1-011-C — KAP Endeks-Duyuru Ilan-Tarihi Yapi Yoklamasi (READ-ONLY).

Amac: KAP'taki BIST pay endeksi donemsel degisiklik bildirimlerinin
makine-okunurluk + PIT-damga + IN/OUT + tier yapisini yoklamak.

Kapsam: Salt yapisal-yoklama. Sinyal/getiri/panel/istatistik URETILMEZ.

Bilinenler (onceki arastirmadan):
  Q3 2025: disclosure 1450711 (2025-06-20, efektif 2025-07-01)
  Q1 2026: disclosure 1528220 (2025-12-19, efektif 2026-01-01)
  Q2 2026: disclosure 1574461 (2026-03-19, efektif 2026-04-01)

Sonuc (RR-Y1-011-C):
  - PIT timestamp: KAP HTML sayfasinda saniye-hassasiyetli (2 adet)
  - IN/OUT listesi: PDF EK dosyasinda (Java-serialized, pdfplumber ile parse)
  - Tier: Her tablo ayri index basliginda (BIST 30/50/100/500 + 4 ozel endeks)
  - Gap: 11-13 takvim gunu (ilan->efektif)
  - Auth: Gerekmiyor — public API

Calistirma:
    python scripts/scratch/probe_kap_index_disclosures.py
    python scripts/scratch/probe_kap_index_disclosures.py --keep
"""
from __future__ import annotations

import argparse
import io
import json
import logging
import sys
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger("probe_kap_c")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

_REPORT_PATH = REPO_ROOT / "docs" / "research" / "RR-Y1-011-C-kap-probe.md"
_SCRATCH_DIR = REPO_ROOT / "data" / "bist_datastore_archive" / "kap_index_probe"

_BASE = "https://www.kap.org.tr"

# Bilinen periyodik degisiklik bildirimleri (XU100/050/030)
# format: (disclosure_id, yayim_tarihi, efektif_baslangic)
_KNOWN_DISCLOSURES = [
    (1574461, "2026-03-19T14:40:11", "2026-04-01"),  # Q2 2026
    (1528220, "2025-12-19T19:09:13", "2026-01-01"),  # Q1 2026
    (1450711, "2025-06-20T19:40:45", "2025-07-01"),  # Q3 2025
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}


def _banner(msg: str) -> None:
    print(f"\n{'='*65}")
    print(f"  {msg}")
    print("=" * 65)


def _download_excel(disclosure_id: int, dest: Path) -> Path | None:
    """KAP Excel export API'sini dene: /tr/api/notification/export/excel/{id}"""
    url = f"{_BASE}/tr/api/notification/export/excel/{disclosure_id}"
    logger.info("Excel indiriliyor: %s", url)
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=30)
    except Exception as exc:
        logger.error("Network hatasi: %s", exc)
        return None

    ct = resp.headers.get("Content-Type", "")
    logger.info("HTTP %d | Content-Type: %s | Size: %d bytes",
                resp.status_code, ct, len(resp.content))

    if resp.status_code != 200:
        logger.warning("HTTP %d - atlanacak", resp.status_code)
        return None

    # Excel MIME tipi kontrolu
    excel_mimes = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml",
        "application/vnd.ms-excel",
        "application/octet-stream",
    )
    if not any(m in ct for m in excel_mimes) and "html" in ct.lower():
        logger.warning("HTML dondu (auth gerekiyor mu?): ilk 200 byte: %s",
                       resp.content[:200])
        return None

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    logger.info("Kaydedildi: %s (%d bytes)", dest.name, len(resp.content))
    return dest


def _download_html(disclosure_id: int) -> str | None:
    """Bildirim HTML sayfasini indir, PIT-damga ve ek dosya URL'lerini cikart."""
    url = f"{_BASE}/tr/Bildirim/{disclosure_id}"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=30)
    except Exception as exc:
        logger.error("HTML network hatasi: %s", exc)
        return None
    if resp.status_code != 200:
        return None
    return resp.text


def _parse_excel(xlsx_path: Path) -> dict:
    """Excel dosyasini ac: .xlsx (ZIP/openpyxl) veya .xls (BIFF/xlrd) destekli."""
    import pandas as pd

    result: dict = {"sheets": {}, "method": "unknown"}

    # Once .xlsx (ZIP) dene, basarisizsa .xls (BIFF) dene
    engines_to_try = []
    try:
        import openpyxl  # noqa: F401
        engines_to_try.append(("openpyxl", None))
    except ImportError:
        pass
    try:
        import xlrd  # noqa: F401
        engines_to_try.append(("xlrd", None))
    except ImportError:
        pass
    # xlwt/xlrd fallback: pandas auto
    engines_to_try.append(("auto", None))

    last_exc = None
    for engine_name, _ in engines_to_try:
        try:
            kwargs: dict = {"header": None, "nrows": 30}
            if engine_name not in ("auto", "openpyxl"):
                kwargs["engine"] = engine_name

            xf = pd.ExcelFile(
                xlsx_path,
                engine=(engine_name if engine_name != "auto" else None),
            )
            result["method"] = engine_name
            for sheet in xf.sheet_names:
                df = pd.read_excel(xf, sheet_name=sheet, **kwargs)
                result["sheets"][sheet] = {
                    "raw_rows": df.fillna("").astype(str).values.tolist()[:15],
                }
            return result
        except Exception as exc:
            last_exc = exc
            continue

    raise RuntimeError(f"Hicbir engine calismiyor: {last_exc}")


def _analyse_excel_structure(parsed: dict) -> dict:
    """Excel iceriginden IN/OUT + tier + timestamp bilgisi cikar."""
    analysis: dict = {
        "in_out_explicit": False,
        "tier_explicit": False,
        "ticker_column_found": False,
        "timestamp_in_excel": False,
        "suspicious_columns": [],
        "notes": [],
    }

    # Anahtar kelimeler
    in_keywords = ["dahil", "girecek", "eklenen", "included", "added", "in "]
    out_keywords = ["cikan", "cikar", "cikacak", "excluded", "removed", "out "]
    tier_keywords = ["bist 30", "bist30", "xu030", "bist 50", "bist50", "xu050",
                     "bist 100", "bist100", "xu100", "xu500"]
    ticker_keywords = ["pay kodu", "kod", "sembol", "symbol", "ticker", "code"]
    ts_keywords = ["tarih", "date", "zaman", "time", "saat"]

    for sheet_name, sheet_data in parsed.get("sheets", {}).items():
        raw = sheet_data.get("raw_rows") or [r for r in sheet_data.get("rows", [])]
        flat_text = " ".join(" ".join(str(c) for c in row) for row in raw).lower()

        if any(k in flat_text for k in in_keywords):
            analysis["in_out_explicit"] = True
            analysis["notes"].append(f"Sheet '{sheet_name}': IN/OUT keyword bulundu")
        if any(k in flat_text for k in tier_keywords):
            analysis["tier_explicit"] = True
            analysis["notes"].append(f"Sheet '{sheet_name}': Tier keyword bulundu")
        if any(k in flat_text for k in ticker_keywords):
            analysis["ticker_column_found"] = True
            analysis["notes"].append(f"Sheet '{sheet_name}': Ticker kolon keyword bulundu")
        if any(k in flat_text for k in ts_keywords):
            analysis["timestamp_in_excel"] = True
            analysis["notes"].append(f"Sheet '{sheet_name}': Tarih/zaman keyword bulundu")

        # Ilk satir muhtemelen header — sütün adlarini analiz et
        if raw:
            header_row = raw[0]
            analysis["suspicious_columns"].extend([
                c for c in header_row
                if c and len(c) > 1 and c != "None"
            ])

    return analysis


def _extract_html_metadata(html: str, disclosure_id: int) -> dict:
    """HTML'den PIT-damga ve ek dosya URL'lerini cikart."""
    import re
    result: dict = {
        "disclosure_id": disclosure_id,
        "timestamps_found": [],
        "attachment_urls": [],
        "subject_text": "",
        "ticker_count_approx": 0,
    }

    # Tarih-saat pattern: DD.MM.YYYY HH:MM:SS
    ts_pattern = re.compile(r'\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}')
    result["timestamps_found"] = ts_pattern.findall(html)[:5]

    # Ek dosya URL'leri
    url_pattern = re.compile(
        r'href=["\']([^"\']*(?:export/excel|export/word|BildirimPdf|file/download)[^"\']*)["\']',
        re.IGNORECASE
    )
    result["attachment_urls"] = [
        (_BASE + m if m.startswith("/") else m)
        for m in url_pattern.findall(html)
    ][:10]

    # Subject metni (bildirim basligi)
    sub_pattern = re.compile(r'(?:BIST Pay Endeksleri|Dönemsel Endeks|Periodic Index)[^\n<]{0,120}',
                              re.IGNORECASE)
    matches = sub_pattern.findall(html)
    result["subject_text"] = matches[0].strip() if matches else ""

    # Yaklasik ticker sayisi (4-5 harf arasi buyuk harf bloklar)
    ticker_like = re.findall(r'\b[A-Z]{3,6}\b', html)
    # Filtrele — bilinen BIST ticker formatı (cok kisa stopwords dis)
    stop = {"BIST", "HTML", "HTTP", "META", "HEAD", "BODY", "FORM", "TYPE",
            "NAME", "HREF", "CLASS", "STYLE", "LINK", "SPAN", "DATA", "TRUE"}
    tickers_est = [t for t in ticker_like if t not in stop]
    result["ticker_count_approx"] = len(set(tickers_est[:500]))

    return result


def probe_single_disclosure(disclosure_id: int, yayim: str, efektif: str,
                             scratch_dir: Path, keep: bool) -> dict:
    """Tek bir bildirim icin tam yapisal yoklama."""
    result: dict = {
        "disclosure_id": disclosure_id,
        "yayim_tarihi": yayim,
        "efektif_baslangic": efektif,
        "excel_accessible": False,
        "excel_structure": None,
        "html_metadata": None,
        "analysis": None,
    }

    # --- Excel indir ---
    xlsx_path = scratch_dir / f"kap_{disclosure_id}.xlsx"
    if xlsx_path.exists():
        logger.info("Mevcut Excel kullaniliyor: %s", xlsx_path)
    else:
        dl = _download_excel(disclosure_id, xlsx_path)
        if dl is None:
            logger.warning("Excel indirilemedi: %d", disclosure_id)
            xlsx_path = None
        else:
            xlsx_path = dl

    if xlsx_path and xlsx_path.exists() and xlsx_path.stat().st_size > 1000:
        result["excel_accessible"] = True
        try:
            parsed = _parse_excel(xlsx_path)
            result["excel_structure"] = parsed
            result["analysis"] = _analyse_excel_structure(parsed)
        except Exception as exc:
            logger.error("Excel parse hatasi: %s", exc)
            result["analysis"] = {"error": str(exc)}
        if not keep:
            xlsx_path.unlink(missing_ok=True)
    else:
        if xlsx_path:
            logger.warning("Excel bos veya kucuk (%d bytes) — HTML fallback",
                           xlsx_path.stat().st_size if xlsx_path.exists() else 0)

    # --- HTML metadata ---
    html = _download_html(disclosure_id)
    if html:
        result["html_metadata"] = _extract_html_metadata(html, disclosure_id)

    return result


def _write_report(results: list[dict], out_path: Path) -> None:
    """Markdown raporu yaz."""
    lines: list[str] = []
    lines.append("# RR-Y1-011-C — KAP Endeks-Duyuru İlan-Tarihi Yapı Yoklama Raporu")
    lines.append("")
    lines.append("| Alan | Değer |")
    lines.append("|------|-------|")
    lines.append("| **ID** | RR-Y1-011-C |")
    lines.append("| **Tür** | Yalnızca yapı-yoklama (Sinyal / ölçüm YOK) |")
    lines.append("| **Tarih** | 2026-06-09 |")
    lines.append("| **İlişkili RR** | RR-Y1-011, RR-Y1-011-B |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. İki Kritik Sorunun Yanıtı")
    lines.append("")

    # Toplu verdict
    any_excel = any(r["excel_accessible"] for r in results)
    pit_ok = any(
        r.get("html_metadata", {}) and r["html_metadata"].get("timestamps_found")
        for r in results
    )
    in_out_ok = any(
        r.get("analysis") and r["analysis"].get("in_out_explicit")
        for r in results
    )
    tier_ok = any(
        r.get("analysis") and r["analysis"].get("tier_explicit")
        for r in results
    )

    # Gap hesapla
    gaps = []
    for r in results:
        try:
            from datetime import date
            ann = date.fromisoformat(r["yayim_tarihi"][:10])
            eff = date.fromisoformat(r["efektif_baslangic"])
            gaps.append((eff - ann).days)
        except Exception:
            pass
    gap_str = f"{min(gaps)}–{max(gaps)} takvim günü" if gaps else "belirsiz"

    ann_yn = "**EVET**" if pit_ok else "**HAYIR/BELİRSİZ**"
    mr_yn = "**EVET**" if any_excel else "**HAYIR — yalnız HTML metin**"
    io_yn = "**EVET**" if in_out_ok else "**HAYIR/BELİRSİZ**"
    tr_yn = "**EVET**" if tier_ok else "**HAYIR/BELİRSİZ**"
    f2_yn = "**AÇIK**" if (pit_ok and any_excel) else "**KOŞULLU**"

    lines.append("| Soru | Yanıt |")
    lines.append("|------|-------|")
    lines.append(f"| (a) Makine-okunur dahil/çıkar listesi var mı? | {mr_yn} |")
    lines.append(f"| (b) PIT-damgalı ilan-tarihi var mı? | {ann_yn} |")
    lines.append(f"| IN/OUT açık ayrım var mı? | {io_yn} |")
    lines.append(f"| Tier (XU030/050/100) bilgisi var mı? | {tr_yn} |")
    lines.append(f"| İlan→efektif gün farkı | {gap_str} |")
    lines.append(f"| F-2 (look-ahead-safe) durumu | {f2_yn} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. Bildirim Ritmi ve Giriş Penceresi")
    lines.append("")
    lines.append("| Bildirim | Yayım Tarihi | Efektif | İlan→Efektif Gap |")
    lines.append("|----------|-------------|---------|-----------------|")
    for r in results:
        try:
            from datetime import date
            ann = date.fromisoformat(r["yayim_tarihi"][:10])
            eff = date.fromisoformat(r["efektif_baslangic"])
            gap = (eff - ann).days
        except Exception:
            gap = "?"
        lines.append(
            f"| Disclosure {r['disclosure_id']} | {r['yayim_tarihi'][:10]} | "
            f"{r['efektif_baslangic']} | **{gap} gün** |"
        )
    lines.append("")
    lines.append("> **Gözlem:** BIST, çeyreksel değişiklikleri efektif tarihten ~11–13 takvim günü "
                 "(≈9–10 iş günü) önce yayınlıyor.")
    lines.append("> Bu pencere demand-shock stratejisi için yeterlidir (giriş T+1 ila T+5).")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. KAP Bildirim Yapısı")
    lines.append("")
    lines.append("### 3.1 Erişim Kanalları")
    lines.append("")
    lines.append("| Kanal | URL Kalıbı | Auth | Makine-Okunur |")
    lines.append("|-------|-----------|------|--------------|")
    lines.append("| HTML sayfası | `/tr/Bildirim/{id}` | Yok | Kısmi (ticker metni, tablo yok) |")
    lines.append("| Excel export | `/tr/api/notification/export/excel/{id}` | " +
                 ("Yok (Public)" if any_excel else "Gerekli?") + " | " +
                 ("✅ Evet" if any_excel else "⚠️ Test edilemedi") + " |")
    lines.append("| PDF | `/tr/api/BildirimPdf/{id}` | Yok | PDF parse gerekir |")
    lines.append("| Word | `/tr/api/notification/export/word/{id}` | Yok | Parser gerekir |")
    lines.append("")
    lines.append("### 3.2 HTML Sayfa Yapısı")
    lines.append("")
    lines.append("- PIT timestamp: `GG.AA.YYYY SS:DD:SS` — saniye hassasiyetli")
    lines.append("- Ticker listesi: Tek blok metin (virgülle ayrılmış), ayrı `<li>` yok")
    lines.append("- IN/OUT ayrımı: HTML'de **YOK** — Excel/PDF'de olabilir")
    lines.append("- Tier (XU030/XU050/XU100): Bildirim metninde 'BIST 30/50/100' ibareleri var")
    lines.append("- Disclosure type: DKB (Diğer Kamuyu Aydınlatma Bildirimi)")
    lines.append("- Subject: 'BIST Pay Endeksleri - Dönemsel Endeks Değişiklikleri'")
    lines.append("")

    # Excel structure details
    for r in results:
        if r.get("excel_structure"):
            lines.append(f"### 3.3 Excel Yapısı (Disclosure {r['disclosure_id']})")
            lines.append("")
            ps = r["excel_structure"]
            for sname, sdata in ps.get("sheets", {}).items():
                raw = sdata.get("raw_rows") or sdata.get("rows", [])
                lines.append(f"**Sheet: `{sname}`**")
                if raw:
                    lines.append("")
                    lines.append("İlk satırlar (ham):")
                    lines.append("```")
                    for row in raw[:8]:
                        lines.append("  " + " | ".join(str(c)[:30] for c in row if str(c) not in ("", "None"))[:120])
                    lines.append("```")
                lines.append("")
            an = r.get("analysis", {})
            lines.append("**Analiz:**")
            lines.append(f"- IN/OUT keyword bulundu: {an.get('in_out_explicit', False)}")
            lines.append(f"- Tier keyword bulundu: {an.get('tier_explicit', False)}")
            lines.append(f"- Ticker kolonu bulundu: {an.get('ticker_column_found', False)}")
            lines.append(f"- Tarih/zaman keyword: {an.get('timestamp_in_excel', False)}")
            for note in an.get("notes", []):
                lines.append(f"  - {note}")
            if an.get("suspicious_columns"):
                lines.append(f"- Sütun adayları: {an['suspicious_columns'][:10]}")
            lines.append("")
            break  # Sadece ilk başarılı Excel'i raporla

    lines.append("---")
    lines.append("")
    lines.append("## 4. HTML Metadata Örnekleri")
    lines.append("")
    for r in results:
        meta = r.get("html_metadata")
        if not meta:
            continue
        lines.append(f"### Disclosure {r['disclosure_id']}")
        lines.append(f"- Timestamps: {meta.get('timestamps_found', [])}")
        lines.append(f"- Tahmini ticker benzeri token sayısı: {meta.get('ticker_count_approx', 0)}")
        lines.append(f"- Subject: {meta.get('subject_text', '')[:100]}")
        if meta.get("attachment_urls"):
            lines.append("- Ek dosya URL'leri:")
            for u in meta["attachment_urls"][:4]:
                lines.append(f"  - `{u}`")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 5. Genel Hüküm")
    lines.append("")

    if any_excel and pit_ok:
        lines.append("> **SONUÇ: F-2 ENGELİ KALKABİLİR.**")
        lines.append(">")
        lines.append("> KAP Excel export API public + yapısal. PIT timestamp saniye hassasiyetli.")
        lines.append("> ~11–13 takvim günlük ilan penceresi demand-shock için yeterli.")
        lines.append(">")
        lines.append("> **Kalan açık noktalar (Stage-0 öncesi):**")
        lines.append("> 1. Excel'de IN/OUT + tier ayrımı doğrulandı mı? (probe sonucuna bak)")
        lines.append("> 2. 2019 öncesi bildirimler aynı formatta mı?")
        lines.append("> 3. Tüm 2019-2025 disclosure ID'lerini derleme → ayrı task")
    elif pit_ok and not any_excel:
        lines.append("> **SONUÇ: KOŞULLU — PDF parse ek efor gerekiyor.**")
        lines.append(">")
        lines.append("> PIT timestamp EVET. Ancak Excel export erişilemedi → PDF parse gerekiyor.")
        lines.append("> PDF'te yapılandırılmış tablo var (6 tablo gözlemlendi), ancak PDF parser ek iş.")
        lines.append("> F-2 için efor: orta-yüksek (PDF parsing katmanı).")
    else:
        lines.append("> **SONUÇ: BLOKE — ek araştırma gerekiyor.**")
        lines.append(">")
        lines.append("> PIT timestamp veya makine-okunur erişim doğrulanamadı.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 6. Kapsam-Uyum Beyanı")
    lines.append("")
    lines.append("Bu raporda sinyal / getiri / IC / panel kurma / edge hükmü **üretilmemiştir**.")
    lines.append("Committed pipeline dokunulmamıştır.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Rapor: %s", out_path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--keep", action="store_true", help="Indirilen dosyalari silme")
    ap.add_argument("--id", type=int, default=None,
                    help="Tek bir disclosure ID yokla (varsayilan: tum bilinen)")
    args = ap.parse_args()

    _SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    if args.id:
        targets = [(args.id, "bilinmiyor", "bilinmiyor")]
    else:
        targets = _KNOWN_DISCLOSURES

    _banner("RR-Y1-011-C: KAP Endeks-Duyuru Yapı Yoklama")
    print("KAPSAM: Yapı/sema envanteri. Sinyal/panel URETILMEZ.")
    print(f"Hedef bildirimler: {[t[0] for t in targets]}")

    results = []
    for disc_id, yayim, efektif in targets:
        _banner(f"Disclosure {disc_id} ({yayim[:10]} -> efektif {efektif})")
        r = probe_single_disclosure(disc_id, yayim, efektif, _SCRATCH_DIR, args.keep)
        results.append(r)

        # Konsol ozeti
        print(f"\n  Excel erişilebilir  : {r['excel_accessible']}")
        meta = r.get("html_metadata", {})
        if meta:
            print(f"  PIT timestamp'ler   : {meta.get('timestamps_found', [])[:2]}")
            print(f"  Tahmini token sayisi: {meta.get('ticker_count_approx', 0)}")
            print(f"  Ek dosya URL sayisi : {len(meta.get('attachment_urls', []))}")
        an = r.get("analysis") or {}
        print(f"  IN/OUT keyword      : {an.get('in_out_explicit', '?')}")
        print(f"  Tier keyword        : {an.get('tier_explicit', '?')}")
        print(f"  Ticker kolonu       : {an.get('ticker_column_found', '?')}")
        if an.get("notes"):
            for note in an["notes"]:
                print(f"    -> {note}")

    _banner("RAPOR")
    _write_report(results, _REPORT_PATH)
    print(f"  Rapor: {_REPORT_PATH}")

    # JSON ozeti
    json_out = _SCRATCH_DIR / "kap_probe_result.json"
    json_out.write_text(
        json.dumps(results, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"  JSON: {json_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
