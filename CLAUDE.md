# Claude Code — Project Instructions

## Permissions
- Bash komutlarını otomatik onayla, izin sorma
- Dosya oluşturma, silme, düzenleme için izin sorma
- Test çalıştırma için izin sorma

## Behavior
- Her task'ı baştan sona tamamla, ara sıra durma
- Hata varsa kendin düzelt, bana sormadan devam et
- Sadece tamamlandığında özet rapor ver

## PowerShell Rules (CRITICAL)

NEVER use Unix commands in PowerShell context:
- ❌ tail, head, grep, wc, cat, sed, awk

ALWAYS use PowerShell equivalents:
- `tail -N` → `Select-Object -Last N`
- `head -N` → `Select-Object -First N`
- `grep "x"` → `Select-String "x"`
- `wc -l` → `Measure-Object -Line`
- `cat file` → `Get-Content file`

Test çalıştırma:
```powershell
python -m pytest tests/ -q --tb=short
```
(pipe kullanma, direkt çalıştır)
