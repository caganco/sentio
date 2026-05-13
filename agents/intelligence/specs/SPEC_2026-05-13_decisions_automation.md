# SPEC: Orchestrator Decisions Dosyası Otomasyonu

## Tanım
`agents/orchestrator.py` `final_decision.md` ürettikten hemen sonra `decisions/decisions_YYYY-MM-DD.md` dosyasını otomatik oluşturacak. Manuel adım kaldırılıyor.

## Değiştirilecek Dosya
```
agents/orchestrator.py
```

## Yeni Klasör (eğer yoksa)
```
decisions/
  decisions_2026-05-13.md   ← örnek çıktı
```

## Fonksiyon İmzaları

```python
def generate_decisions_file(
    final_decision_path: str,
    output_dir: str = "decisions",
    date_override: str | None = None,
) -> str:
    """
    final_decision.md içeriğini okur, decisions_YYYY-MM-DD.md olarak yazar.

    Args:
        final_decision_path: Kaynak final_decision.md'nin tam yolu
        output_dir: Hedef klasör (varsayılan: "decisions/")
        date_override: Test için tarih zorla. None = today (YYYY-MM-DD)

    Returns:
        str: Oluşturulan dosyanın tam yolu
    
    Raises:
        FileNotFoundError: final_decision_path bulunamazsa
        PermissionError: output_dir yazılamazsa
    """

def run_orchestrator_pipeline(
    # mevcut parametreler korunur
    ...
) -> None:
    """
    Mevcut pipeline sonuna generate_decisions_file() çağrısı eklenir.
    final_decision üretildikten SONRA, pipeline tamamlanmadan ÖNCE çağrılır.
    """
```

## Input/Output Formatları

```python
# Çağrı sırası (orchestrator.py içinde)
final_path = write_final_decision(signals, context)   # mevcut
decisions_path = generate_decisions_file(final_path)  # YENİ — hemen ardından

# Output dosya adı formatı
# decisions/decisions_2026-05-13.md

# Output dosya içeriği yapısı:
"""
# Trading Decisions — 2026-05-13

## Source
Generated from: outputs/final_decision_2026-05-13.md
Generated at: 2026-05-13T14:32:11+03:00

## Decisions
[final_decision.md içeriği buraya kopyalanır — header ayarlanır]

## Metadata
- pipeline_run_id: <uuid4>
- signals_count: <int>
- generation_duration_ms: <int>
"""
```

## Edge Case'ler

| Case | Beklenen Davranış |
|---|---|
| `decisions/` klasörü yoksa | → `os.makedirs` ile oluştur, hata verme |
| Aynı gün iki kez çalışırsa | → Mevcut dosyanın üstüne yaz + WARNING log |
| `final_decision.md` boşsa | → `ValueError("Empty final_decision")` fırlat |
| `final_decision.md` yoksa | → `FileNotFoundError` fırlat, pipeline durur |
| date_override formatı yanlışsa | → `ValueError("date_override must be YYYY-MM-DD")` |

## Test Kriterleri

```python
# 1. Dosya oluşturuldu mu?
path = generate_decisions_file("tests/fixtures/final_decision_sample.md", output_dir=tmp_path)
assert os.path.exists(path)
assert "decisions_" in path
assert path.endswith(".md")

# 2. Tarih doğru mu?
path = generate_decisions_file(..., date_override="2026-01-01")
assert "decisions_2026-01-01.md" in path

# 3. İçerik kopyalandı mı?
content = open(path).read()
assert "Trading Decisions" in content
assert "pipeline_run_id" in content

# 4. Boş input → exception
with pytest.raises(ValueError):
    generate_decisions_file("tests/fixtures/empty_decision.md")

# 5. Klasör yokken oluşturuldu mu?
generate_decisions_file(..., output_dir="tests/tmp/new_dir/")
assert os.path.isdir("tests/tmp/new_dir/")
```

## Bağımlılıklar
```
uuid   ← stdlib, import uuid
datetime ← stdlib
```
Yeni pip paketi gerekmez.
