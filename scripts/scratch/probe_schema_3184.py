"""RR-Y1-011-B — DataStore 3184 Schema Probe (READ-ONLY).

Amac: ZIP sema yoklamasi - ilan-tarihi ve olay-tipi sütunlari var mi?
Kapsam: Sadece 1 temsilci ZIP indir + ac + sutun isimleri + örnek satirlar.
Sinyal/getiri/istatistik/panel URETILMEZ.

Kullanim:
    python scripts/scratch/probe_schema_3184.py
    python scripts/scratch/probe_schema_3184.py --year 2024
    python scripts/scratch/probe_schema_3184.py --keep   # ZIP'i silme
"""
from __future__ import annotations

import argparse
import io
import json
import logging
import sys
import zipfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger("probe_schema_3184")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

_PRODUCT_ID = 3184
_SCRATCH_DIR = REPO_ROOT / "data" / "bist_datastore_archive" / "index_components"
_REPORT_PATH = REPO_ROOT / "docs" / "research" / "RR-Y1-011-B-schema-probe.md"

# Ilan-tarihi adayi sütun anahtar kelimeleri (kucuk harf)
_ANNOUNCE_KEYWORDS = [
    "ilan", "bildirim", "duyuru", "announce", "declaration",
    "karar", "decision", "notification",
]
# Olay tipi adayi sütun anahtar kelimeleri
_EVENT_TYPE_KEYWORDS = [
    "islem_tip", "event_type", "olay_tip", "degisim_neden", "change_reason",
    "acil", "emergency", "planlı", "planned", "action_type", "eylemi",
]
# Efektif tarih adayi sütun anahtar kelimeleri
_EFFECTIVE_KEYWORDS = [
    "yururluk", "yurur", "gecerli", "effective", "tarih", "date",
    "baslangic", "giris", "cikis", "entry", "exit",
]


def _banner(msg: str) -> None:
    print(f"\n{'='*65}")
    print(f"  {msg}")
    print("=" * 65)


def _kw_match(col, keywords: list[str]) -> bool:
    c = str(col).lower()
    return any(kw in c for kw in keywords)


def _inspect_zip(zip_path: Path) -> dict:
    """ZIP aci + tum CSV/XLSX dosyalarinin sema yoklamasi."""
    result: dict = {
        "zip_name": zip_path.name,
        "zip_size_kb": round(zip_path.stat().st_size / 1024, 1),
        "inner_files": [],
        "columns_by_file": {},
        "announce_candidates": {},
        "event_type_candidates": {},
        "effective_candidates": {},
        "sample_rows": {},
        "verdict": {},
    }

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        result["inner_files"] = names
        logger.info("ZIP icerigi (%d dosya): %s", len(names), names)

        for inner_name in names:
            ext = Path(inner_name).suffix.lower()
            if ext not in (".csv", ".xlsx", ".xls"):
                logger.info("Atlandi (uzanti %s): %s", ext, inner_name)
                continue

            logger.info("Okunuyor: %s", inner_name)
            raw = zf.read(inner_name)

            try:
                cols, sample = _read_tabular(raw, ext, inner_name)
            except Exception as exc:
                logger.warning("Okuma hatasi %s: %s", inner_name, exc)
                result["columns_by_file"][inner_name] = f"HATA: {exc}"
                continue

            result["columns_by_file"][inner_name] = cols
            result["sample_rows"][inner_name] = sample

            ann = [c for c in cols if _kw_match(c, _ANNOUNCE_KEYWORDS)]
            evt = [c for c in cols if _kw_match(c, _EVENT_TYPE_KEYWORDS)]
            eff = [c for c in cols if _kw_match(c, _EFFECTIVE_KEYWORDS)]

            result["announce_candidates"][inner_name] = ann
            result["event_type_candidates"][inner_name] = evt
            result["effective_candidates"][inner_name] = eff

    # Genel hüküm
    any_announce = any(v for v in result["announce_candidates"].values())
    any_event_type = any(v for v in result["event_type_candidates"].values())
    result["verdict"] = {
        "announce_date_present": any_announce,
        "event_type_present": any_event_type,
        "lookahead_safe_feasible": any_announce,
        "planned_filter_feasible": any_event_type,
    }
    return result


def _read_tabular(raw: bytes, ext: str, name: str) -> tuple[list[str], list[dict]]:
    """Ham bytes -> (column_list, sample_rows[:5])."""
    import pandas as pd

    buf = io.BytesIO(raw)
    if ext == ".csv":
        # Türkçe CSV genellikle UTF-8 veya cp1254
        for enc in ("utf-8-sig", "utf-8", "cp1254", "latin-1"):
            try:
                buf.seek(0)
                df = pd.read_csv(buf, encoding=enc, sep=None, engine="python", nrows=10)
                break
            except Exception:
                continue
        else:
            buf.seek(0)
            df = pd.read_csv(buf, encoding="latin-1", nrows=10)
    else:
        # exsrk formatı: satır 0-2 meta, satır 3 = gerçek başlık
        # Önce ham oku ve başlık satırını bul
        buf.seek(0)
        raw_df = pd.read_excel(buf, header=None, nrows=15)
        # Başlık satırı: "PAY KODU" veya "CODE" içeren satır
        header_row = 0
        for i, row in raw_df.iterrows():
            vals = " ".join(str(v) for v in row.values if str(v) != "nan")
            if "PAY" in vals.upper() or "CODE" in vals.upper() or "KOD" in vals.upper():
                header_row = i
                break
        buf.seek(0)
        df = pd.read_excel(buf, header=header_row, nrows=10)

    # Sütun adlarını string'e zorla (Timestamp vs. int header'lar JSON'a serialize edilemiyor)
    df.columns = [str(c) for c in df.columns]
    cols = list(df.columns)
    sample = df.head(5).to_dict(orient="records")
    return cols, sample


def _list_library_files(session) -> list:
    from src.data.bist_datastore_client import DatastoreFileIndex
    idx = DatastoreFileIndex(session)
    return idx.list_files(_PRODUCT_ID)


def _list_catalog_products(session, year: int | None) -> list:
    from datetime import date
    from src.data.bist_datastore_client import DatastoreCatalog
    cat = DatastoreCatalog(session)
    since = date(year, 1, 1) if year else None
    until = date(year, 12, 31) if year else None
    return cat.list_products(_PRODUCT_ID, since_date=since, until_date=until)


def _try_acquire(session, products) -> int:
    from src.data.bist_datastore_client import (
        DatastoreAcquirer,
        DatastoreProductTypeMismatchError,
    )
    to_add = [p for p in products if not p.in_library]
    if not to_add:
        return 0
    try:
        acq = DatastoreAcquirer(session)
        return acq.add_free_to_library(to_add)
    except DatastoreProductTypeMismatchError as exc:
        logger.warning("ProductTypeMismatch (beklenen): %s", exc)
        return -1
    except Exception as exc:
        logger.error("add_free_to_library hatasi: %s", exc)
        return -1


def _download_one(session, file_obj, dest: Path) -> Path | None:
    from src.data.bist_datastore_client import DatastoreDownloader, DatastoreSessionExpiredError
    dl = DatastoreDownloader(session)
    try:
        return dl.download_file(file_obj.file_id, dest)
    except DatastoreSessionExpiredError:
        raise
    except Exception as exc:
        logger.error("Indirme hatasi (%s): %s", file_obj.name, exc)
        return None


def _write_report(result: dict, year: int | None, out_path: Path) -> None:
    v = result["verdict"]
    lines: list[str] = []
    lines.append("# RR-Y1-011-B — DataStore 3184 Sema Yoklama Raporu")
    lines.append("")
    lines.append("| Alan | Deger |")
    lines.append("|------|-------|")
    lines.append("| **ID** | RR-Y1-011-B |")
    lines.append("| **Tur** | Yalnizca-sema-yoklama (Edge/sinyal/istatistik YOK) |")
    lines.append("| **Tarih** | 2026-06-09 |")
    lines.append("| **Kaynak ZIP** | `" + result["zip_name"] + "` |")
    lines.append("| **ZIP boyutu** | " + str(result["zip_size_kb"]) + " KB |")
    lines.append("| **Iliskili RR** | RR-Y1-011 |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Iki Kritik Sorunun Yaniti")
    lines.append("")
    lines.append("| Soru | Yanit | Kaynagi |")
    lines.append("|------|-------|---------|")
    ann_yn = "**EVET**" if v["announce_date_present"] else "**HAYIR**"
    evt_yn = "**EVET**" if v["event_type_present"] else "**HAYIR**"
    las_yn = "**ACIK**" if v["lookahead_safe_feasible"] else "**BLOKE**"
    pf_yn = "**ACIK**" if v["planned_filter_feasible"] else "**BLOKE**"
    lines.append(f"| (a) Ilan-tarihi yururluk-tarihinden AYRI mi? | {ann_yn} | Sutun sema yoklamasi |")
    lines.append(f"| (b) Olay-tipi ayirt-edilebilir mi? | {evt_yn} | Sutun sema yoklamasi |")
    lines.append(f"| Look-ahead-safe panel | {las_yn} | (a) sorusundan turetildi |")
    lines.append(f"| Planli-rekon alt-kumesi filtresi | {pf_yn} | (b) sorusundan turetildi |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. ZIP Icerigi")
    lines.append("")
    lines.append("```")
    for f in result["inner_files"]:
        lines.append(f"  {f}")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. Sutun Listesi (dosya bazli)")
    lines.append("")
    for fname, cols in result["columns_by_file"].items():
        lines.append(f"### `{fname}`")
        if isinstance(cols, list):
            for i, c in enumerate(cols, 1):
                ann_flag = " <- **ILAN-TARIHI ADAYI**" if c in result["announce_candidates"].get(fname, []) else ""
                evt_flag = " <- **OLAY-TIPI ADAYI**" if c in result["event_type_candidates"].get(fname, []) else ""
                eff_flag = " <- *efektif-tarih adayi*" if c in result["effective_candidates"].get(fname, []) else ""
                lines.append(f"  {i}. `{c}`{ann_flag}{evt_flag}{eff_flag}")
        else:
            lines.append(f"  HATA: {cols}")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 4. Ornek Satirlar (ilk 5 satir)")
    lines.append("")
    for fname, rows in result["sample_rows"].items():
        lines.append(f"### `{fname}`")
        if rows:
            headers = list(rows[0].keys())
            lines.append("| " + " | ".join(str(h) for h in headers) + " |")
            lines.append("| " + " | ".join("---" for _ in headers) + " |")
            for row in rows[:5]:
                vals = [str(row.get(h, ""))[:40].replace("|", "/") for h in headers]
                lines.append("| " + " | ".join(vals) + " |")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 5. Genel Hüküm")
    lines.append("")
    if v["lookahead_safe_feasible"] and v["planned_filter_feasible"]:
        lines.append("> **SONUC: Ilan-tarihi + Olay-tipi ayrimi MEVCUT.**")
        lines.append("> Look-ahead-safe panel kurulabilir; planli-rekon alt-kumesi ayristirilebilir.")
        lines.append("> F-1 ve F-2 engelleri KALKAR. Stage-0 kararini besler (vermez).")
    elif v["lookahead_safe_feasible"] and not v["planned_filter_feasible"]:
        lines.append("> **SONUC: Ilan-tarihi MEVCUT; Olay-tipi ayrimi YOK (veya belirsiz).**")
        lines.append("> Look-ahead-safe panel kurulabilir; planli-rekon filtresi icin ek kaynak gerekir.")
        lines.append("> F-2 engeli kalkar (kismi); F-3/F-4 icin KAP takvimi gerekebilir.")
    elif not v["lookahead_safe_feasible"] and v["planned_filter_feasible"]:
        lines.append("> **SONUC: Olay-tipi ayrimi MEVCUT; Ilan-tarihi YOK.**")
        lines.append("> Look-ahead-safe panel icin ilan-tarihi kaynagi gerekir (KAP/BIST arsivi).")
        lines.append("> F-3/F-4 engelleri kalkar; F-2 (look-ahead-safe) BLOKEDIR.")
    else:
        lines.append("> **SONUC: Ilan-tarihi YOK; Olay-tipi ayrimi YOK.**")
        lines.append("> ZIP yalnizca efektif-tarih + sembol bilgisi icerir.")
        lines.append("> F-2 ve F-3 engelleri DEVAM EDER — KAP/BIST arsivi alternatif.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 6. Kapsam-Uyum Beyani")
    lines.append("")
    lines.append("Bu raporda sinyal / getiri / IC / NW-t / Sharpe / edge hukmu URETILMEMISTIR.")
    lines.append("Committed pipeline dokuulmamistir. Yeni committed artefakt yoktur.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Rapor yazildi: %s", out_path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int, default=2024,
                    help="Indirilen temsili yil (varsayilan: 2024)")
    ap.add_argument("--keep", action="store_true",
                    help="Indirilen ZIP'i sildirme")
    ap.add_argument("--skip-download", action="store_true",
                    help="Indirme atlayip mevcut ZIP'i kullan (--zip-path gerekir)")
    ap.add_argument("--zip-path", type=Path, default=None,
                    help="Hazir ZIP dosyasinin yolu (--skip-download ile kullan)")
    args = ap.parse_args()

    _banner("RR-Y1-011-B: DataStore 3184 Sema Yoklama")
    print("KAPSAM: Yalnizca sutun/sema envanteri. Sinyal/getiri URETILMEZ.")
    print(f"Hedef yil: {args.year}")

    # --- Hazir ZIP varsa direkt kullan ---
    if args.skip_download:
        if args.zip_path and args.zip_path.exists():
            zip_path = args.zip_path
            logger.info("Hazir ZIP kullaniliyor: %s", zip_path)
        else:
            # Archive dizininde ZIP ara
            existing = list(_SCRATCH_DIR.glob("*.zip"))
            if not existing:
                logger.error("--skip-download verildi ama archive dizininde ZIP yok.")
                return 1
            zip_path = sorted(existing)[-1]
            logger.info("Archive'den ZIP secildi: %s", zip_path)
    else:
        # --- Session yukle ---
        try:
            from src.data.bist_datastore_client import (
                DatastoreSession,
                DatastoreSessionExpiredError,
            )
            session = DatastoreSession()
            if not session.is_valid():
                logger.error("Session suresi dolmus — python scripts/capture_datastore_session.py")
                return 1
            logger.info("Session gecerli.")
        except FileNotFoundError:
            logger.error("datastore_session.json bulunamadi — once login yap.")
            return 1

        # --- Once library'de var mi? ---
        _banner("Adim 1: Library'de mevcut dosyalar")
        try:
            lib_files = _list_library_files(session)
        except DatastoreSessionExpiredError:
            logger.error("Session suresi dolmus. Yenile.")
            return 1

        year_lib = [f for f in lib_files if f.data_date and f.data_date.year == args.year]
        logger.info("Library'de type=%d dosyasi: %d (yil=%d: %d)",
                    _PRODUCT_ID, len(lib_files), args.year, len(year_lib))

        # --- Catalog'dan listele ---
        _banner("Adim 2: Catalog'dan urunler")
        try:
            products = _list_catalog_products(session, args.year)
        except DatastoreSessionExpiredError:
            logger.error("Session suresi dolmus. Yenile.")
            return 1
        logger.info("Catalog'da %d urun (yil=%d)", len(products), args.year)
        for p in products[:5]:
            logger.info("  %s | %s | in_library=%s | free=%s",
                        p.reference_id, p.data_date, p.in_library, p.is_free)

        # --- Add to library (ProductTypeMismatch bekleniyor olabilir) ---
        _banner("Adim 3: Library'e ekle (type-mismatch olabilir)")
        added = _try_acquire(session, products)
        if added == -1:
            logger.warning("ProductTypeMismatch: add-library calismadi. "
                           "Library'deki mevcut dosyalarla devam.")
        elif added > 0:
            logger.info("%d dosya eklendi.", added)

        # --- Indirilecek hedef: library veya katalogdan ---
        _banner("Adim 4: Indirme")
        _SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

        # Library dosyalarindan yil esleseni al
        target_lib = year_lib or lib_files[:1]
        zip_path: Path | None = None

        if target_lib:
            f = target_lib[0]
            dest = _SCRATCH_DIR / f.name
            if dest.exists():
                logger.info("Mevcut: %s", dest)
                zip_path = dest
            else:
                logger.info("Indiriliyor: %s", f.name)
                try:
                    zip_path = _download_one(session, f, dest)
                except DatastoreSessionExpiredError:
                    logger.error("Session suresi dolmus.")
                    return 1

        if zip_path is None:
            # Katalogdan referenceId ile dene
            year_products = [p for p in products if p.data_date and
                             (isinstance(p.data_date, str) and str(args.year) in p.data_date
                              or hasattr(p.data_date, 'year') and p.data_date.year == args.year)]
            if not year_products:
                year_products = products[:1]

            if not year_products:
                logger.error("Indirilebilir urun bulunamadi.")
                return 1

            p = year_products[0]
            fname = f"exsrk{args.year}.zip"
            dest = _SCRATCH_DIR / fname

            # DatastoreFile benzeri nesne olustur
            class _FakeFile:
                file_id = p.reference_id
                name = fname

            if dest.exists():
                logger.info("Mevcut: %s", dest)
                zip_path = dest
            else:
                logger.info("Katalog referenceId ile indiriliyor: %s", p.reference_id)
                try:
                    zip_path = _download_one(session, _FakeFile(), dest)
                except DatastoreSessionExpiredError:
                    logger.error("Session suresi dolmus.")
                    return 1

        if zip_path is None or not zip_path.exists():
            logger.error("ZIP indirilemedi. Session gecerli ama dosya erisilemez.")
            logger.error("Manuel indirme icin: DataStore sitesinde 3184 numarali "
                         "urunu indir, data/bist_datastore_archive/index_components/ "
                         "klasorune koy, tekrar calistir: --skip-download")
            return 1

    # --- Sema Yoklama ---
    _banner("Adim 5: Sema Yoklama")
    logger.info("ZIP: %s (%.1f KB)", zip_path.name, zip_path.stat().st_size / 1024)

    if not zipfile.is_zipfile(zip_path):
        logger.error("Gecersiz ZIP dosyasi: %s", zip_path)
        return 1

    result = _inspect_zip(zip_path)

    # Konsol ozeti
    _banner("SONUC")
    v = result["verdict"]
    print(f"  ZIP       : {result['zip_name']} ({result['zip_size_kb']} KB)")
    print(f"  Ic dosya  : {result['inner_files']}")
    for fname, cols in result["columns_by_file"].items():
        if isinstance(cols, list):
            print(f"\n  [{fname}] {len(cols)} sutun:")
            for c in cols:
                tags = []
                if c in result["announce_candidates"].get(fname, []):
                    tags.append("ILAN-TARIHI?")
                if c in result["event_type_candidates"].get(fname, []):
                    tags.append("OLAY-TIPI?")
                if c in result["effective_candidates"].get(fname, []):
                    tags.append("efektif-tarih?")
                tag_str = "  [" + " | ".join(tags) + "]" if tags else ""
                print(f"    - {c}{tag_str}")

    print(f"\n  Ilan-tarihi MEVCUT   : {v['announce_date_present']}")
    print(f"  Olay-tipi MEVCUT     : {v['event_type_present']}")
    print(f"  Look-ahead-safe      : {v['lookahead_safe_feasible']}")
    print(f"  Planli-filtre        : {v['planned_filter_feasible']}")

    # JSON ozeti
    json_out = _SCRATCH_DIR.parent / "schema_probe_3184_result.json"
    json_out.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    logger.info("JSON ozeti: %s", json_out)

    # Markdown raporu
    _write_report(result, args.year, _REPORT_PATH)
    print(f"\n  Rapor: {_REPORT_PATH}")

    # ZIP temizle (--keep yoksa)
    if not args.keep and not args.skip_download:
        try:
            zip_path.unlink()
            logger.info("ZIP silindi: %s", zip_path.name)
        except Exception as exc:
            logger.warning("ZIP silinemedi: %s", exc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
