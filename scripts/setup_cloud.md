# Sentio Cloud Setup — GitHub Actions Production

**Tahmini kurulum suresi:** ~20 dakika

---

## 1. GitHub Secrets (5 adet)

Repo → Settings → Secrets and variables → Actions → New repository secret

| Secret | Deger | Nereden |
|--------|-------|---------|
| `EVDS_API_KEY` | TCMB EVDS API anahtari | Zaten var — `.env`'den kopyala | ok
| `ANTHROPIC_API_KEY` | Claude API anahtari | Zaten var (CI'da mevcut) |  ok
| `POSITIONS_YAML_B64` | `positions.yaml` base64 | Asagiya bak |  ok
| `TELEGRAM_BOT_TOKEN` | Bot token | Asagiya bak (§3) | OK
| `TELEGRAM_CHAT_ID` | Chat ID | Asagiya bak (§3) | ok
| `HEALTHCHECK_URL` | Ping URL | Asagiya bak (§4) | ok

### positions.yaml → Base64 encode

**Windows PowerShell:**
```powershell
[Convert]::ToBase64String([System.IO.File]::ReadAllBytes("positions.yaml")) | Set-Clipboard
```
Ciktisi `POSITIONS_YAML_B64` secret degeri olarak yapistir.  ### OK

**Linux/Mac:**
```bash
base64 positions.yaml | tr -d '\n'
```

---

## 2. FMP_API_KEY (Opsiyonel)

Eger Financial Modeling Prep API anahtari varsa secret olarak ekle.
Yoksa `daily_update.py` graceful devam eder (FMP adimi atlanir).

---

## 3. Telegram Bot Kurma (~5 dakika) ok

1. Telegram'da `@BotFather`'a yaz → `/newbot`
2. Bot ismi: `Sentio Alerts` → username: `bist_os_bot` (benzersiz olmali)
3. Aldigin token → `TELEGRAM_BOT_TOKEN` secret
4. Chat ID almak icin:
   - Bota bir mesaj gonder
   - `https://api.telegram.org/bot<TOKEN>/getUpdates` URL'ini ac
   - `"chat":{"id":XXXXXXX}` degerini al → `TELEGRAM_CHAT_ID` secret

---

## 4. healthchecks.io Check Kurma (~5 dakika)   ok

1. https://healthchecks.io → Sign up / Login
2. "Add Check" → Name: `BIST Daily Production`
3. Ayarlar:
   - Period: `1 day`
   - Grace time: `30 minutes`
   - Schedule: `30 15 * * 1-5` (Mon-Fri 15:30 UTC = 18:30 Istanbul) 
4. "Copy URL" → `HEALTHCHECK_URL` secret
   - Format: `https://hc-ping.com/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

**Start/Finish ping pattern:**
- Workflow basinda: `HEALTHCHECK_URL/start`
- Workflow bitisinde: `HEALTHCHECK_URL` (success sinyal)
- Fail durumunda: curl atilmaz → healthchecks.io timeout → SMS/Email alert

---

## 5. Ilk Manual Dispatch Test

1. GitHub → Actions → `BIST Daily Production` → `Run workflow`
2. Beklenen sure: ~10 dakika
3. Kontrol listesi:
   - [ ] Health check step: sari (uyari) veya yesil — workflow kesilmez (`continue-on-error`)
   - [ ] Daily update step yesil
   - [ ] IC state commit step: "nothing to commit" veya yeni commit
   - [ ] Heartbeat SUCCESS step: curl 200
   - [ ] healthchecks.io dashboard → yesil
4. Fail olursa: Actions → run → step loglarinin kirmizi adimina bak

### Telegram failure testi

`health_check.py` artik `continue-on-error: true` ile calisiyor — workflow'u fail ettirmiyor.
Telegram bildirimini test etmek icin:
1. `daily_production.yml`'de gecici olarak `run daily update` adimina `exit 1` ekle
2. Manuel dispatch → Telegram mesaji gelmeli
3. Degisikligini geri al

---

## 6. IC State Persistence — Nasil Calisir

```
Ilk run:
  checkout (parquet yok) → daily_update (parquet olusturur) →
  git add -f (gitignore override) → commit + push

Sonraki runlar:
  checkout (parquet var, repo'dan gelir) → daily_update (append eder) →
  git add -f → commit + push
```

**NOT:** `data/analytics/ic_history.parquet` artik repo'da yasiyor
(gitignore override ile `git add -f`). Local gelistirmede `git pull`
sonrasi bu dosya gelir — local IC gecmisinizle cakisabilir.
Local copy'yi korumak istersen:
```bash
git update-index --skip-worktree data/analytics/ic_history.parquet
```

---

## 7. keep_alive.yml — Neden Gerekli

`daily_production.yml` Pazar calismaz. `keep_alive.yml` Pazar 13:00'da
healthchecks.io'ya ping atar; check'in "stale" durumuna dusmesini engeller.

---

## Troubleshooting

| Belirti | Neden | Cozum |
|---------|-------|-------|
| `positions.yaml` decode hatasi | B64 yanlis | PowerShell encode komutunu tekrarla |
| `health_check.py` sari uyari | OS_STATE.md 48h+ eski | `continue-on-error` ile gecilir — normaldir |
| IC commit "nothing to commit" | daily_update parquet uretmedi | Signal log yoksa beklenir |
| Telegram mesaji gelmedi | Token/chat_id yanlis | getUpdates URL ile test et |
| Workflow 25 dakika sonra kesildi | Timeout | `daily_update.py` takildi — log'a bak |
