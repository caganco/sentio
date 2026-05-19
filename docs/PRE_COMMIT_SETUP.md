# Pre-commit Setup

## Kurulum (tek seferlik)

```bash
pip install pre-commit ruff
pre-commit install
```

## Manuel çalıştır

```bash
pre-commit run --all-files
```

## Tier 1 tek başına

```bash
pytest tests/test_architecture.py -q
```

## Bypass (ACİL DURUM — istisnai)

```bash
git commit --no-verify -m "..."
```

⚠️ ORCHESTRATOR ONAY GEREKTİRİR
