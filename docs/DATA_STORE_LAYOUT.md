# Veri Deposu ve Junction Mimarisi (Yerel)

Bu doküman, dört repo (ana + üç klon) arasında paylaşılan büyük veri dizinlerinin
nasıl tek kaynaktan servis edildiğini ve `data/clean_universe` temiz-evren panelinin
kaynağını/şemasını açıklar. Veri dosyaları **git'e commit edilmez** (lokal kalır);
bu doküman onların nerede durduğunu ve nasıl erişildiğini kayıt altına alır.

## 1. Junction mimarisi — tek kaynak, sıfır sync

Gerçek veri **yalnızca ana repoda** durur; klonlar Windows directory junction ile
oraya bakar. Bir klonda veri üretildiğinde junction üzerinden gerçek dizine yazılır,
böylece **anında tüm repolara yansır** — kopyalama/sync gerekmez.

```
C:\Users\cagan\bist-trading-system\data\         <- GERCEK veri (~2.9 GB)
    bist_datastore_archive\   (REAL, ~2.8 GB)
    clean_universe\           (REAL, ~40 MB)
    snapshots\                (REAL, git-tracked  -> junction YOK)

C:\Users\cagan\bist-clone-builder1\data\
    bist_datastore_archive\   --> Junction -> ...\bist-trading-system\data\bist_datastore_archive
    clean_universe\           --> Junction -> ...\bist-trading-system\data\clean_universe
    snapshots\                (REAL, kendi git'i)

builder2, builder3: builder1 ile ayni (ayni iki junction).
```

- **Disk tasarrufu:** 4× kopya (~11 GB) yerine tek kaynak (~2.9 GB).
- **`snapshots/` bilerek junction'lanmadı:** git-tracked dosyalar içerir; her repo
  kendi git geçmişine sahip olmalı, paylaşılmaz.

### Junction'ı doğrula
```powershell
foreach ($d in 'bist-trading-system','bist-clone-builder1','bist-clone-builder2','bist-clone-builder3') {
  $p = "C:\Users\cagan\$d\data\clean_universe"
  $it = Get-Item $p -Force
  "{0,-22} {1,-10} {2}" -f $d, ($it.LinkType ?? 'REAL-DIR'), ($it.Target -join ';')
}
```
Beklenen: ana repo `REAL-DIR`, üç klon `Junction` -> ana repo.

### Junction'ı yeniden kur (kazara silinirse)
Bir klonda junction kaybolursa (gerçek dizin değil, sadece link), klonda:
```powershell
$tgt = 'C:\Users\cagan\bist-trading-system\data\clean_universe'
$lnk = "$PWD\data\clean_universe"
if (Test-Path $lnk) { Remove-Item $lnk -Recurse -Force }   # DIKKAT: gercek dizin DEGILSE
cmd /c mklink /J "$lnk" "$tgt"
```
> UYARI: Komutu **klon repoda** çalıştır. Ana repodaki gerçek dizine asla
> `Remove-Item` uygulama — gerçek veri silinir, dört repo birden bozulur.

## 2. `clean_universe` paneli — D-202 temiz-evren

Survivorship-clean, corp-action-adjusted BIST fiyat paneli (2019–2026). Backtest'lerin
(D-203+) tükettiği donmuş (frozen) evren. Direktif: **D-202**.

### Dosyalar
| Dosya | İçerik |
|---|---|
| `adjusted_prices_2019_2026.parquet` | Adjusted fiyat paneli (681 sembol × 1848 gün) |
| `pit_membership_2019_2026.parquet`  | Point-in-time BIST endeks üyeliği (in_bist100 vb.) |
| `_meta.json` | Provenance: content-hash, kaynak dağılımı, self-validate sayıları, dışlananlar |

### Üretim — dört katmanlı factor çözümleme
Fiyat backbone'u **3196 raw** kalır; yalnızca adjustment **factor kaynağı** katmanlıdır:
- **L1 yfinance** (birincil, ücretsiz): `.splits` -> factor `1/R`, `.dividends` -> total-return.
- **L2 col-14 join**: 3196 col-14 (`01`=bedelsiz, `03`=mixed/capital, `06`=temettü) tüm
  semboller (delisted dahil) için yetkili event takvimi.
- **L3 price-implied + self-validate**: L1'in kapatamadığı `03` residual'lar için aday
  factor = `close[t]/close[t-1]`; raw sıçramayla **≤%2** eşleşirse kabul, değilse flag.
  Tolerans `thresholds.py::CLEAN_UNIVERSE_SELF_VALIDATE_TOL` (Stage-0-öncesi sabit).
- **L4 KAP residual** (opt-in, **varsayılan KAPALI**, ≤40 çağrı hard bütçe, IP rate-limit
  koruması): yalnızca self-validate-fail + erişilebilir semboller.

### Yeniden üret (rebuild)
Herhangi bir repodan (junction sayesinde çıktı merkeze yazılır):
```powershell
PYTHONPATH=. python scripts/build_clean_universe.py --force-rebuild
# KAP L4 dahil (dikkat: IP rate-limit, ≤40 cagri):
PYTHONPATH=. python scripts/build_clean_universe.py --force-rebuild --enable-kap
```
`--verify-only` mevcut parquet'i `_meta.json` content-hash'ine karşı doğrular.

### Son freeze — D-185 doğrulama (KAP kapalı)
- `adjusted_close <= 0` count: **0**
- BIST100 günlük üye: 96–100 (eski bozuk YOL-2: sabit 101; %100 bant içinde)
- 681 sembol × 1848 gün; content-hash `fd207550…`
- Kaynak dağılımı: yfinance 59 / price-implied 305 / kap 0 / none 317
- self-validate pass/fail: 638/277
- `residual_excluded`: **1** (HLGYO, true-bedelli-uncertain) — hedef 0–3
- unresolved_drops: 1 (FENER 2025-07-01, CA-kodsuz büyük düşüş, düzeltilmedi)
- Survivorship-clean: delisted KOZAA/IPEKE/KOZAL panelde mevcut

> Veri lokal (gitignore: `data/clean_universe/*.parquet`). Repo'lar arası paylaşım
> kopyayla değil §1'deki junction ile yapılır.
