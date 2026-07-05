# Prod-path E2E gate for Fair CRM auth/RBAC (bypass disabled).
param(
    [switch]$SkipServiceCheck
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$env:FAIR_CRM_DEV_BYPASS_CORE = "false"

Write-Host "Prod-path E2E gate (FAIR_CRM_DEV_BYPASS_CORE=false)" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"
Write-Host ""

if (-not $SkipServiceCheck) {
    $coreOk = $false
    $fairOk = $false
    try {
        $coreResp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/health" -UseBasicParsing -TimeoutSec 3
        $coreOk = $coreResp.StatusCode -eq 200
    } catch { }
    try {
        $fairResp = Invoke-WebRequest -Uri "http://127.0.0.1:8001/health" -UseBasicParsing -TimeoutSec 3
        $fairOk = $fairResp.StatusCode -eq 200
    } catch { }

    if (-not $coreOk -or -not $fairOk) {
        Write-Host "Services not healthy — starting via reset-dev.ps1" -ForegroundColor Yellow
        & "$RepoRoot\scripts\dev\reset-dev.ps1"
        Start-Sleep -Seconds 5
    }
}

python "$RepoRoot\scripts\e2e_validation.py" --prod-path
exit $LASTEXITCODE
