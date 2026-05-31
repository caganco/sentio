<#
D-188 forward-capture -- register a DAILY Windows Scheduled Task.

Runs scripts/event_forward_capture.py once per day (auth-free KAP feed is recent-only
~24h, so daily is required -- weekly would miss most events). No token needed.

Paths are computed relative to this script, so it works wherever the repo lives
(clone3 now; main repo after merge). Re-run to update; it is idempotent (-Force).

To inspect : Get-ScheduledTask -TaskName 'BIST-D188-EventForwardCapture'
To remove  : Unregister-ScheduledTask -TaskName 'BIST-D188-EventForwardCapture' -Confirm:$false
Output log : data/event_logs/capture.log
#>
$ErrorActionPreference = "Stop"

$repo   = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$py     = (Get-Command python).Source
$script = Join-Path $repo "scripts\event_forward_capture.py"
$logDir = Join-Path $repo "data\event_logs"
$log    = Join-Path $logDir "capture.log"
$taskName = "BIST-D188-EventForwardCapture"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# cmd wrapper so stdout/stderr append to the daily log
$cmdArgs = "/c `"`"$py`" `"$script`" >> `"$log`" 2>&1`""
$action  = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $cmdArgs -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At 7:00PM   # ~1h after BIST close
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "D-188 olay-confluence ileri-donuk kayit (gunluk, auth-suz)" `
    -Force | Out-Null

Write-Output "Registered '$taskName' -> daily 19:00"
Write-Output "  python : $py"
Write-Output "  script : $script"
Write-Output "  log    : $log"
