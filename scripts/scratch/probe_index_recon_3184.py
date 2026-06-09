"""RR-Y1-011 — Index Reconstitution Feasibility Probe (READ-ONLY).

KAPSAM: Yalnizca envanter/sayim. Sinyal, getiri, performans, IC, edge hukmü URETILMEZ.
Committed pipeline'a dokunulmaz.

Uc soruyu cevaplar:
  (a) Panel kurulabilir mi?
  (b) N kac (kirilimlı)?
  (c) Look-ahead-safe mi (ilan/yururluk ayrimi var mi)?

Calistirilmasi:
    python scripts/scratch/probe_index_recon_3184.py
    python scripts/scratch/probe_index_recon_3184.py --check-datastore
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

PRICES_PATH = REPO_ROOT / "data" / "clean_universe" / "adjusted_prices_2019_2026.parquet"
ARCHIVE_INDEX_DIR = REPO_ROOT / "data" / "bist_datastore_archive" / "index_components"
SESSION_PATH = REPO_ROOT / "datastore_session.json"

MEMBERSHIP_COLS = ("bist100", "bist30")


# ---------------------------------------------------------------------------
# Yardimci
# ---------------------------------------------------------------------------

def _banner(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def _check_datastore_catalog() -> dict:
    """DataStore katalog 3184 urun listesini sorgular (session gerektir)."""
    if not SESSION_PATH.exists():
        return {"status": "session_absent", "products": []}
    try:
        from src.data.bist_datastore_client import (
            DatastoreSession,
            DatastoreCatalog,
        )
        session = DatastoreSession.load(SESSION_PATH)
        if not session.is_valid():
            return {"status": "session_expired", "products": []}
        catalog = DatastoreCatalog(session)
        products = catalog.list_products(3184)
        return {
            "status": "ok",
            "count": len(products),
            "products": [
                {
                    "reference_id": p.reference_id,
                    "data_date": p.data_date,
                    "description": getattr(p, "description", ""),
                    "in_library": getattr(p, "in_library", None),
                }
                for p in products
            ],
        }
    except Exception as exc:
        return {"status": f"error: {exc}", "products": []}


# ---------------------------------------------------------------------------
# Ana analiz: clean_universe membership degisiklikleri
# ---------------------------------------------------------------------------

def analyse_membership_changes() -> dict:
    """bist100/bist30 flag degisimlerinden efektif rekonstitusyon olaylarini cikar."""
    if not PRICES_PATH.exists():
        return {"error": f"Prices parquet not found: {PRICES_PATH}"}

    px = pd.read_parquet(PRICES_PATH, columns=["date", "symbol", "bist100", "bist30"])
    px["date"] = pd.to_datetime(px["date"])

    results = {}

    for idx_col, idx_label in [("bist100", "XU100"), ("bist30", "XU030")]:
        if idx_col not in px.columns:
            results[idx_label] = {"error": f"Column '{idx_col}' absent in parquet"}
            continue

        wide = (
            px[["date", "symbol", idx_col]]
            .pivot(index="date", columns="symbol", values=idx_col)
            .sort_index()
        )

        # Membership degisimi: gun-uzerine-gun diff
        delta = wide.diff()

        additions = (delta == 1).copy()
        removals  = (delta == -1).copy()

        # Olay listesi: (tarih, sembol, yon)
        add_events = [
            {"effective_date": str(d.date()), "symbol": sym, "direction": "IN",
             "index": idx_label}
            for d, row in additions.iterrows()
            for sym in row[row].index.tolist()
        ]
        rem_events = [
            {"effective_date": str(d.date()), "symbol": sym, "direction": "OUT",
             "index": idx_label}
            for d, row in removals.iterrows()
            for sym in row[row].index.tolist()
        ]
        all_events = sorted(add_events + rem_events, key=lambda x: x["effective_date"])

        # Yillik dagılım
        yearly: dict[int, dict[str, int]] = {}
        for ev in all_events:
            y = int(ev["effective_date"][:4])
            yearly.setdefault(y, {"IN": 0, "OUT": 0})
            yearly[y][ev["direction"]] += 1

        # Join edilebilirlik: clean_universe'de fiyat var mi?
        all_syms = {ev["symbol"] for ev in all_events}
        panel_syms = set(px["symbol"].unique())
        in_panel = all_syms & panel_syms
        missing = all_syms - panel_syms

        results[idx_label] = {
            "n_total": len(all_events),
            "n_in": sum(1 for e in all_events if e["direction"] == "IN"),
            "n_out": sum(1 for e in all_events if e["direction"] == "OUT"),
            "yearly_breakdown": yearly,
            "date_range": {
                "first": all_events[0]["effective_date"] if all_events else None,
                "last":  all_events[-1]["effective_date"] if all_events else None,
            },
            "joinability": {
                "total_symbols": len(all_syms),
                "in_clean_universe": len(in_panel),
                "missing_from_panel": len(missing),
                "missing_symbols": sorted(missing),
            },
            "events_sample_first10": all_events[:10],
        }

    return results


# ---------------------------------------------------------------------------
# Archive durum kontrolu
# ---------------------------------------------------------------------------

def check_archive_status() -> dict:
    if not ARCHIVE_INDEX_DIR.exists():
        return {"status": "directory_absent", "files": []}
    files = list(ARCHIVE_INDEX_DIR.iterdir())
    return {
        "status": "empty" if not files else "has_files",
        "file_count": len(files),
        "files": [f.name for f in files[:20]],
    }


# ---------------------------------------------------------------------------
# Rapor yazici
# ---------------------------------------------------------------------------

def print_report(membership: dict, archive: dict, catalog: dict | None) -> None:
    _banner("RR-Y1-011 — Index Recon Feasibility Probe")
    print("KAPSAM: Salt envanter/sayim. Edge/sinyal/performans URETILMEZ.")

    _banner("A) DataStore 3184 Archive Durumu")
    print(f"  Archive dir : {ARCHIVE_INDEX_DIR}")
    print(f"  Durum       : {archive['status']}")
    print(f"  Dosya sayisi: {archive['file_count']}")
    if archive["files"]:
        print(f"  Dosyalar    : {archive['files'][:5]}")

    if catalog is not None:
        _banner("B) DataStore Katalog 3184 (API)")
        print(f"  Durum    : {catalog['status']}")
        if catalog.get("count"):
            print(f"  Urun adedi: {catalog['count']}")
            for p in catalog.get("products", [])[:5]:
                print(f"    - {p.get('data_date','?')} | {p.get('description','')[:60]}")
            # Ilan tarihi var mi?
            has_announce = any(
                "ilan" in str(p.get("description","")).lower()
                or "announce" in str(p.get("description","")).lower()
                or "bildirim" in str(p.get("description","")).lower()
                for p in catalog.get("products", [])
            )
            print(f"  Ilan-tarihi alani: {'BULUNDU' if has_announce else 'BELIRSIZ — ZIP incelenmeli'}")

    _banner("C) Efektif Rekonstitusyon Olaylari (clean_universe flags)")
    print("  KAYNAK: bist100/bist30 PIT membership flag degisimleri")
    print("  NOT: Bu EFEKTIF tarihlerdir. ILAN tarihleri bu kaynakta YOK.")
    print()

    for idx_label, res in membership.items():
        if "error" in res:
            print(f"  [{idx_label}] HATA: {res['error']}")
            continue
        print(f"  [{idx_label}]")
        print(f"    N toplam   : {res['n_total']}  (IN={res['n_in']} | OUT={res['n_out']})")
        print(f"    Tarih aral.: {res['date_range']['first']} .. {res['date_range']['last']}")
        print(f"    Joinability: {res['joinability']['in_clean_universe']}/{res['joinability']['total_symbols']} "
              f"sembol clean_universe'de mevcut "
              f"(eksik={res['joinability']['missing_from_panel']})")
        if res["joinability"]["missing_symbols"]:
            print(f"    Eksik semb.: {res['joinability']['missing_symbols'][:10]}")
        print(f"    Yillik dagılım:")
        for yr in sorted(res["yearly_breakdown"]):
            row = res["yearly_breakdown"][yr]
            print(f"      {yr}: IN={row['IN']:3d}  OUT={row['OUT']:3d}  "
                  f"toplam={row['IN']+row['OUT']:3d}")
        print()

    _banner("D) Look-Ahead-Safe Panel Degerlendirmesi")
    print("""
  EFEKTIF tarih mevcut  : EVET  (clean_universe PIT flags)
  ILAN tarihi mevcut    : HAYIR (clean_universe bu bilgiyi icermez)
  DataStore 3184 zip'i  : INCELENMEDI (archive bos; zip yapisi bilinmiyor)

  Look-ahead-safe panel icin ILAN tarihi ZORUNLUDUR.
  Sadece efektif tarih kullanilirsa strateji fiyat-duyarsiz alis/satis
  mekanizmasi baslamadan ONCE giris yapamaz — bu ilan-tarihini presuppose eder.

  FIZIBILITE ENGELI DURUMU:
    - Eger DataStore 3184 zip'leri ILAN tarihini iceriyorsa: KALKAR
    - Eger yalnizca efektif tarih varsa: LOOK-AHEAD-SAFE PANEL KURULAMAZ
      (yalnizca gercek-zamanli kullanim veya gecikme-kabul-eden strateji mumkun)

  Sonraki adim: 3184'ten 1 yillik zip indir, icerigini incele.
""")

    _banner("E) N-Yeterlilik On-Degerlendirmesi")
    for idx_label, res in membership.items():
        if "error" in res:
            continue
        n = res["n_total"]
        flag = "Stage-0 ADAYI (N>=20)" if n >= 20 else "C9-TIPI DUSUK-N RISKI (N<20)"
        print(f"  [{idx_label}] N={n} -> {flag}")
    print("""
  NOT: Bu N sayisi Stage-0'da kirilimlı kullanilacak (dahil/cikar, XU030/XU100 ayri).
  Yeterlilik hukmunu VERMEZ; yalnizca Stage-0 acilip acilmayacagini besler.
""")


# ---------------------------------------------------------------------------
# Calistir
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="RR-Y1-011 Index Recon Probe")
    ap.add_argument("--check-datastore", action="store_true",
                    help="DataStore API'yi sorgula (session gerekir)")
    ap.add_argument("--json", dest="out_json", type=Path, default=None,
                    help="Sonuclari JSON olarak kaydet (opsiyonel)")
    args = ap.parse_args()

    membership = analyse_membership_changes()
    archive    = check_archive_status()
    catalog    = _check_datastore_catalog() if args.check_datastore else None

    print_report(membership, archive, catalog)

    if args.out_json:
        out = {"membership": membership, "archive": archive, "catalog": catalog}
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(
            json.dumps(out, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        print(f"\nJSON kayit: {args.out_json}")


if __name__ == "__main__":
    main()
