# Architectural Health Check Script
# Weekly safety checks for design principles

Write-Host "=== Architectural Health Check ===" -ForegroundColor Cyan

# Check 1: Hardcoded weights in engine.py
Write-Host "`n[1/3] Checking for hardcoded weights in engine.py..." -ForegroundColor Yellow
$enginePath = "src\signals\engine.py"
$hardcodedWeights = Select-String -Path $enginePath -Pattern '0\.20|0\.35|0\.15|0\.05|0\.25' -ErrorAction SilentlyContinue | `
    Where-Object { $_.Line -notmatch '#|import|MASTER_WEIGHTS|kelly_fraction' }

if ($hardcodedWeights) {
    Write-Host "  FAIL: Found hardcoded weights:" -ForegroundColor Red
    $hardcodedWeights | ForEach-Object { Write-Host "    Line $($_.LineNumber): $($_.Line.Trim())" }
    exit 1
} else {
    Write-Host "  PASS: No hardcoded weights found" -ForegroundColor Green
}

# Check 2: General "hardcoded" strings
Write-Host "`n[2/3] Scanning for hardcoded constants in src/..." -ForegroundColor Yellow
$hardcodedStrings = Get-ChildItem -Path "src" -Include "*.py" -Recurse | Select-String -Pattern 'hardcoded' -ErrorAction SilentlyContinue

if ($hardcodedStrings) {
    Write-Host "  WARNING: Found 'hardcoded' references:" -ForegroundColor Yellow
    $hardcodedStrings | ForEach-Object { Write-Host "    $($_.Filename):$($_.LineNumber)" }
} else {
    Write-Host "  PASS: No hardcoded markers found" -ForegroundColor Green
}

# Check 3: Run architecture tests
Write-Host "`n[3/3] Running architecture tests..." -ForegroundColor Yellow
python -m pytest tests\test_architecture.py -v

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=== All checks passed ===" -ForegroundColor Green
} else {
    Write-Host "`n=== Some checks failed ===" -ForegroundColor Red
    exit 1
}
