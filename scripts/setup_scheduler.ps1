# Windows Task Scheduler 등록 스크립트
# PowerShell을 관리자 권한으로 실행 후 이 스크립트를 실행하세요

$PythonPath = (Get-Command python).Source
$ScriptDir = "D:\business\STOCK\scripts"

# ── Task 1: 일간 리서치 (매일 오전 6:30 — 미장 마감 후)
$action1 = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "run_daily.py" `
    -WorkingDirectory $ScriptDir

$trigger1 = New-ScheduledTaskTrigger -Daily -At "06:30AM"

$settings1 = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName "StockResearch_DailyReport" `
    -Action $action1 `
    -Trigger $trigger1 `
    -Settings $settings1 `
    -Description "매일 오전 6:30 미장 마감 후 시장 감시 + 기술적 분석 + 섹터 분석 실행" `
    -RunLevel Highest `
    -Force

Write-Host "[완료] StockResearch_DailyReport 등록됨 (매일 06:30)" -ForegroundColor Green

# ── Task 2: Discord 봇 (부팅 시 자동 시작)
$action2 = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "discord_bot.py" `
    -WorkingDirectory $ScriptDir

$trigger2 = New-ScheduledTaskTrigger -AtLogOn

$settings2 = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Days 365) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName "StockResearch_DiscordBot" `
    -Action $action2 `
    -Trigger $trigger2 `
    -Settings $settings2 `
    -Description "로그인 시 Discord 봇 자동 시작 (충돌 시 5분 후 재시작)" `
    -RunLevel Highest `
    -Force

Write-Host "[완료] StockResearch_DiscordBot 등록됨 (로그인 시 자동시작)" -ForegroundColor Green
Write-Host ""
Write-Host "등록된 작업 목록:" -ForegroundColor Cyan
Get-ScheduledTask | Where-Object { $_.TaskName -like "StockResearch_*" } | Format-Table TaskName, State
