## Summary

<!-- State what changes and why, for a reviewer. Describe the change itself and its
     impact, not the editing or formatting process. Keep it factual. 1-3 bullets. -->
-

## Affected files

<!-- List the key files modified. -->
-

## Test result

```
pytest: X passed, 0 failed
```

## Checklist

- [ ] No merge conflict with master
- [ ] CI tiers passing (architecture → integration → lint → regression)
- [ ] No hardcoded thresholds - all constants in `src/signals/thresholds.py`
- [ ] No look-ahead violations - signals at `t`, actions at `t+1`
