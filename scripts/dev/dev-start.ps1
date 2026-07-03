#Requires -Version 5.1
<#
.SYNOPSIS
  Idempotent Fair CRM development runtime start (Docker infra + backend + frontend).

.DESCRIPTION
  Safe to run multiple times. Does not create duplicate backend/frontend processes when
  health checks already pass. Use reset-dev.ps1 to force-kill stale listeners first.

.EXAMPLE
  .\scripts\dev\dev-start.ps1

.EXAMPLE
  .\scripts\dev\dev-start.ps1 -SkipPull
#>
[CmdletBinding()]
param(
    [switch]$SkipPull
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-lib.ps1")

Write-DevStep "Fair CRM dev-start (idempotent)"
Write-Host "Repository root: $script:DevRepoRoot"

Invoke-DevPrepareRepository -SkipPull:$SkipPull
Test-DockerEngineReady
Start-DevDockerInfra
Wait-DevPostgresHealthy
$alembicStatus = Invoke-DevDatabaseMigrations
Wait-DevRedisHealthy

$backendStarted = $false
$frontendStarted = $false

if (Test-DevBackendHealthy) {
    Write-Host "Backend already healthy on port $script:DevBackendPort - skipping start."
} elseif (Test-DevPortListening -Port $script:DevBackendPort) {
    throw "Port $script:DevBackendPort is in use but /health is not OK. Run .\scripts\dev\reset-dev.ps1 to clear stale processes."
} else {
    Write-DevStep "Starting backend on port $script:DevBackendPort"
    $backend = Start-DevBackend
    $backendStarted = $true
    if (-not (Wait-DevHttpOk -Urls @("http://127.0.0.1:$script:DevBackendPort/health"))) {
        throw "Backend failed to start. See $($backend.Log) and $($backend.ErrLog)"
    }
}

if (Test-DevFrontendHealthy) {
    Write-Host "Frontend already healthy on port $script:DevFrontendPort - skipping start."
} elseif (Test-DevPortListening -Port $script:DevFrontendPort) {
    throw "Port $script:DevFrontendPort is in use but frontend is not responding. Run .\scripts\dev\reset-dev.ps1 to clear stale processes."
} else {
    Write-DevStep "Starting frontend on port $script:DevFrontendPort (strictPort)"
    $frontend = Start-DevFrontend
    $frontendStarted = $true
    $frontendBase = "http://127.0.0.1:$script:DevFrontendPort"
    if (-not (Wait-DevHttpOk -Urls @($frontendBase, "$frontendBase/index.html"))) {
        throw "Frontend failed to start. See $($frontend.Log) and $($frontend.ErrLog)"
    }
}

$workerProc = Start-DevWorkerIfConfigured

Write-Host ""
Write-Host "Runtime port status:" -ForegroundColor Yellow
Get-DevPortReport -Ports @($script:DevBackendPort, $script:DevFrontendPort) | Format-Table -AutoSize

Show-DevDockerStatus

Write-Host ""
if ($backendStarted) { Write-Host "Backend started." } else { Write-Host "Backend reused (already running)." }
if ($frontendStarted) { Write-Host "Frontend started." } else { Write-Host "Frontend reused (already running)." }
if ($null -eq $workerProc) { Write-Host "Worker: not configured." } else { Write-Host "Worker launcher PID: $($workerProc.Id)" }

Show-DevRuntimeSummary -AlembicRevision $alembicStatus.Raw
Write-Host "dev-start complete."
