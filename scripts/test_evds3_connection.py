"""EVDS3 live connection + series inventory test (RR-021).

Probes every series code listed in RR-021 against the live TCMB EVDS3 API,
records active/dead status + last observation date, and writes a markdown
report to docs/research/RR-021-live-test-results.md.

Usage:
    python scripts/test_evds3_connection.py

Env:
    EVDS_API_KEY — required. Read from .env at repo root.

Notes (RR-021 invariants):
    - Base URL: https://evds3.tcmb.gov.tr/igmevdsms-dis/  (no /service/evds/)
    - Params are appended to the URL string directly (NO requests params=,
      NO leading '?') — EVDS3 rejects real query-strings with 404.
    - Date format DD-MM-YYYY (YYYY-MM-DD → 400 Bad Request).
    - Auth header is ambiguous (brief says x-auth-token, community says key).
      We probe 'key' first, fall back to 'x-auth-token' on 401.
    - Series value column is named after the code with dots → underscores
      (TP.DK.USD.A → TP_DK_USD_A). Weekend/holiday rows come back null.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

_BASE_URL = "https://evds3.tcmb.gov.tr/igmevdsms-dis/"
_TIMEOUT = 15
_LOOKBACK_DAYS = 400  # wide enough to guarantee data for monthly/weekly series
_REPORT_PATH = Path(__file__).resolve().parents[1] / "docs" / "research" / "RR-021-live-test-results.md"
_PROBE_SERIES = "TP.DK.USD.A"  # known-good series used for auth-header detection


@dataclass
class Series:
    code: str
    desc: str
    group: str
    freq: str
    note: str = ""


# RR-021 §3 — full series inventory
CATALOG: list[Series] = [
    # §3.1 Policy & money market
    Series("TP.APIFON4", "TCMB ağırlıklı ort. fonlama maliyeti (AOFM)", "Politika Faizi", "Günlük"),
    Series("TP.API.REP.ORT.G1", "Repo ortalama oranı (gecelik)", "Politika Faizi", "Günlük", "aktiflik teyit edilmeli"),
    Series("TP.BISTTLREF.ORAN", "TLREF (TL gecelik referans faiz) — oran", "Politika Faizi", "Günlük"),
    Series("TP.BISTTLREF.KAPANIS", "TLREF — kapanış variant", "Politika Faizi", "Günlük", "community variant"),
    Series("TP.FAIZ.PYUVDL", "Eski TLREF kodu", "Politika Faizi", "—", "RR-009: deprecated, dead bekleniyor"),
    # §3.2 FX
    Series("TP.DK.USD.A", "USD/TRY Alış (gösterge)", "Döviz", "Günlük"),
    Series("TP.DK.USD.S", "USD/TRY Satış", "Döviz", "Günlük"),
    Series("TP.DK.EUR.A", "EUR/TRY Alış", "Döviz", "Günlük"),
    Series("TP.DK.EUR.S", "EUR/TRY Satış", "Döviz", "Günlük"),
    Series("TP.DK.USD.A.YTL", "USD alış — eski .YTL suffix variant", "Döviz", "Günlük", "community variant"),
    # §3.3 Inflation
    Series("TP.FE.OKTG01", "TÜFE Genel (2003=100, TÜİK yeni seri)", "Enflasyon", "Aylık"),
    Series("TP.FG.J0", "TÜFE alternatif kodu", "Enflasyon", "Aylık", "OKTG01 daha yaygın"),
    Series("TP.FG01", "Yİ-ÜFE", "Enflasyon", "Aylık", "veri grubu üzerinden teyit"),
    Series("TP.ENFBEK.PKA12ENF", "12-ay ileri enflasyon beklentisi", "Enflasyon", "Aylık", "nice-to-have"),
    # §3.4 Markets / investor behaviour
    Series("TP.MKNETHAR.M7", "BIST net işlem (genel)", "Borsa", "Haftalık", "datagroups ile tam tanım doğrula"),
    Series("TP.MKNETHAR.M1", "Yabancı net işlem", "Borsa", "Haftalık"),
]


@dataclass
class Result:
    series: Series
    status: str                      # ACTIVE | DEAD | ERROR
    http: int | None = None
    last_date: str | None = None
    last_value: str | None = None
    n_obs: int = 0
    detail: str = ""


def _build_url(code: str, start: str, end: str) -> str:
    """RR-021: params concatenated to the URL string, no '?', no params dict."""
    return f"{_BASE_URL}series={code}&startDate={start}&endDate={end}&type=json"


def _extract(obs: dict) -> tuple[str | None, str | None]:
    """Return (date, value) from an EVDS item, skipping metadata fields."""
    skip = {"Tarih", "tarih", "UNIXTIME", "YEARWEEK"}
    date = obs.get("Tarih") or obs.get("tarih")
    value = None
    for k, v in obs.items():
        if k in skip:
            continue
        if v in (None, "", "ND"):
            continue
        value = str(v)
        break
    return date, value


def _detect_auth_header(api_key: str, start: str, end: str) -> tuple[str | None, str]:
    """Probe TP.DK.USD.A to find which header name authenticates.

    Returns (header_name | None, detail). None means neither worked.
    """
    url = _build_url(_PROBE_SERIES, start, end)
    for header in ("key", "x-auth-token"):
        try:
            resp = requests.get(url, headers={header: api_key}, timeout=_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            return None, f"probe network error ({header}): {exc}"
        if resp.status_code == 200 and "json" in resp.headers.get("Content-Type", "").lower():
            return header, f"auth header = '{header}' (HTTP 200 on {_PROBE_SERIES})"
        if resp.status_code == 401:
            continue  # try next header
        # Non-401 non-200 (404/403/5xx) — auth not the issue; assume this header
        return header, f"auth header = '{header}' (probe returned HTTP {resp.status_code}, not 401)"
    return None, "both 'key' and 'x-auth-token' returned 401 — key invalid/frozen?"


def _test_series(s: Series, api_key: str, header: str, start: str, end: str) -> Result:
    url = _build_url(s.code, start, end)
    try:
        resp = requests.get(url, headers={header: api_key}, timeout=_TIMEOUT)
    except requests.exceptions.Timeout:
        return Result(s, "ERROR", None, detail="timeout")
    except requests.exceptions.RequestException as exc:
        return Result(s, "ERROR", None, detail=f"network: {exc}")

    if resp.status_code != 200:
        return Result(s, "DEAD" if resp.status_code in (400, 404) else "ERROR",
                      resp.status_code, detail=f"HTTP {resp.status_code}")

    ct = resp.headers.get("Content-Type", "").lower()
    if "json" not in ct:
        return Result(s, "ERROR", 200, detail=f"non-JSON body ({ct}) — migration signal?")

    try:
        body = resp.json()
    except ValueError:
        return Result(s, "ERROR", 200, detail="JSON parse failed (HTML SPA?)")

    items = body.get("items") or body.get("data") or []
    rows = [(_extract(o)) for o in items]
    rows = [(d, v) for d, v in rows if d and v is not None]
    if not rows:
        return Result(s, "DEAD", 200, n_obs=len(items),
                      detail="200 ama numerik gözlem yok — deprecated/boş")

    rows.sort(key=lambda dv: _date_key(dv[0]))
    last_date, last_value = rows[-1]
    return Result(s, "ACTIVE", 200, last_date=last_date, last_value=last_value, n_obs=len(rows))


def _date_key(raw: str) -> str:
    """Sort key: normalise DD-MM-YYYY → YYYY-MM-DD; leave others as-is."""
    raw = (raw or "").strip()
    if len(raw) == 10 and raw[2] == "-" and raw[5] == "-":
        d, m, y = raw.split("-")
        return f"{y}-{m}-{d}"
    return raw


def _write_report(results: list[Result], header: str, header_detail: str,
                  start: str, end: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    n_active = sum(1 for r in results if r.status == "ACTIVE")
    n_dead = sum(1 for r in results if r.status == "DEAD")
    n_err = sum(1 for r in results if r.status == "ERROR")

    lines: list[str] = []
    lines.append("# RR-021 — EVDS3 Canlı Test Sonuçları")
    lines.append("")
    lines.append(f"**Test zamanı:** {now}  ")
    lines.append(f"**Tarih aralığı:** {start} → {end} (lookback {_LOOKBACK_DAYS} gün)  ")
    lines.append(f"**Base URL:** `{_BASE_URL}`  ")
    lines.append(f"**Auth header:** {header_detail}  ")
    lines.append(f"**Özet:** ✅ {n_active} aktif · ❌ {n_dead} dead · ⚠️ {n_err} hata "
                 f"(toplam {len(results)})")
    lines.append("")
    lines.append("> Üretildi: `scripts/test_evds3_connection.py`. RR-021 §3 envanterini "
                 "canlı API'ye karşı doğrular.")
    lines.append("")

    icon = {"ACTIVE": "✅", "DEAD": "❌", "ERROR": "⚠️"}
    by_group: dict[str, list[Result]] = {}
    for r in results:
        by_group.setdefault(r.series.group, []).append(r)

    for group, items in by_group.items():
        lines.append(f"## {group}")
        lines.append("")
        lines.append("| Durum | Seri Kodu | Açıklama | Frekans | Son Veri | Son Değer | Gözlem | Not |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in items:
            note = r.detail or r.series.note
            lines.append(
                f"| {icon[r.status]} {r.status} | `{r.series.code}` | {r.series.desc} | "
                f"{r.series.freq} | {r.last_date or '—'} | {r.last_value or '—'} | "
                f"{r.n_obs} | {note} |"
            )
        lines.append("")

    lines.append("## Aksiyon Notları")
    lines.append("")
    dead = [r for r in results if r.status == "DEAD"]
    err = [r for r in results if r.status == "ERROR"]
    if dead:
        lines.append("**Dead seriler (kullanma / koddan çıkar):**")
        for r in dead:
            lines.append(f"- `{r.series.code}` — {r.detail}")
        lines.append("")
    if err:
        lines.append("**Hatalı seriler (tekrar dene / araştır):**")
        for r in err:
            lines.append(f"- `{r.series.code}` — {r.detail}")
        lines.append("")
    if not dead and not err:
        lines.append("Tüm seriler aktif — koddaki seri kodları RR-021 ile uyumlu.")
        lines.append("")

    _REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    # Windows console defaults to cp1254 which can't encode some output chars.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    load_dotenv()
    api_key = os.getenv("EVDS_API_KEY")
    if not api_key:
        print("HATA: EVDS_API_KEY .env'de bulunamadı.", file=sys.stderr)
        return 1

    end = datetime.now(timezone.utc).strftime("%d-%m-%Y")
    start = (datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)).strftime("%d-%m-%Y")

    print(f"EVDS3 canli test -- {start} -> {end}")
    print(f"Base: {_BASE_URL}\n")

    header, header_detail = _detect_auth_header(api_key, start, end)
    print(f"[auth] {header_detail}")
    if header is None:
        print("HATA: Auth başarısız, test durduruldu.", file=sys.stderr)
        # Still write a minimal report so the failure is recorded.
        _write_report([], "—", header_detail, start, end)
        return 2

    results: list[Result] = []
    for s in CATALOG:
        r = _test_series(s, api_key, header, start, end)
        results.append(r)
        icon = {"ACTIVE": "OK ", "DEAD": "DEAD", "ERROR": "ERR "}[r.status]
        last = f"son={r.last_date} ({r.last_value})" if r.status == "ACTIVE" else r.detail
        print(f"  [{icon}] {s.code:<24} {last}")

    _write_report(results, header, header_detail, start, end)
    n_active = sum(1 for r in results if r.status == "ACTIVE")
    print(f"\nRapor yazıldı: {_REPORT_PATH}")
    print(f"Özet: {n_active}/{len(results)} aktif")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
