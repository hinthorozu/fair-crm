#Requires -Version 5.1
<#
.SYNOPSIS
  Force-reset Fair CRM local dev runtime (kill stale listeners, restart backend + frontend).

.DESCRIPTION
  Unlike dev-start.ps1, this always stops existing listeners on standard ports before
  starting fresh processes. Use when ports are stuck or stale uvicorn/vite reloaders remain.

.EXAMPLE
  .\scripts\dev\reset-dev.ps1

.EXAMPLE
  .\scripts\dev\reset-dev.ps1 -SkipPull
#>
[CmdletBinding()]
param(
    [switch]$SkipPull
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-lib.ps1")

Write-DevStep "Fair CRM dev runtime reset (force)"
Write-Host "Repository root: $script:DevRepoRoot"

if (-not (Test-Path $script:DevBackendDir)) {
    throw "Backend directory not found: $script:DevBackendDir"
}
if (-not (Test-Path $script:DevFrontendDir)) {
    throw "Frontend directory not found: $script:DevFrontendDir"
}

Invoke-DevPrepareRepository -SkipPull:$SkipPull
Test-DockerEngineReady
Start-DevDockerInfra
Wait-DevPostgresHealthy
$alembicStatus = Invoke-DevDatabaseMigrations
Wait-DevRedisHealthy

Write-DevStep "Stopping stale Fair CRM dev processes"
$cleared = @(Stop-DevRuntimeProcesses -IncludeAltFrontendPorts)
if ($cleared.Count -gt 0) {
    Start-Sleep -Seconds 2
    Write-Host "Cleared $($cleared.Count) port listener(s)."
} else {
    Write-Host "No listeners found on target ports."
}

foreach ($port in @($script:DevBackendPort, $script:DevFrontendPort)) {
    if (Test-DevPortListening -Port $port) {
        throw "Port $port is still in use after cleanup. Stop remaining listeners manually."
    }
}

Write-DevStep "Starting backend on port $script:DevBackendPort"
$backend = Start-DevBackend

Write-DevStep "Starting frontend on port $script:DevFrontendPort (strictPort)"
$frontend = Start-DevFrontend

function Test-ParticipantsSearchOpenApi([int]$Port) {
    try {
        $openapi = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/openapi.json" -TimeoutSec 10
        $params = @($openapi.paths.'/api/v1/fairs/{fair_id}/participants'.get.parameters | ForEach-Object { $_.name })
        $required = @('search', 'page', 'page_size', 'sort', 'direction')
        foreach ($name in $required) {
            if ($params -notcontains $name) {
                Write-Warning "OpenAPI missing parameter '$name' on fair participants list (found: $($params -join ', '))"
                return $false
            }
        }
        return $true
    } catch {
        Write-Warning "OpenAPI verification failed: $($_.Exception.Message)"
        return $false
    }
}

Write-DevStep "Verifying services"
$backendHealth = "http://127.0.0.1:$($script:DevBackendPort)/health"
$swaggerUrl = "http://127.0.0.1:$($script:DevBackendPort)/docs"
$frontendUrl = "http://127.0.0.1:$($script:DevFrontendPort)/"

$backendOk = Wait-DevHttpOk -Urls @($backendHealth)
$swaggerOk = Wait-DevHttpOk -Urls @($swaggerUrl)
$openapiOk = Test-ParticipantsSearchOpenApi -Port $script:DevBackendPort
$frontendOk = Wait-DevHttpOk -Urls @($frontendUrl, "$frontendUrl/index.html")

$escapedPorts = @()
foreach ($port in $script:DevFrontendAltPorts) {
    if (Test-DevPortListening -Port $port) {
        $escapedPorts += $port
    }
}

Write-Host ""
Write-Host "Port status:" -ForegroundColor Yellow
Get-DevPortReport -Ports $script:DevAllRuntimePorts | Format-Table -AutoSize

if (-not $backendOk) {
    throw "Backend failed to start on port $($script:DevBackendPort). See $($backend.Log) and $($backend.ErrLog)"
}
if (-not $swaggerOk) {
    throw "Swagger is not reachable at $swaggerUrl"
}
if (-not $openapiOk) {
    throw "Backend OpenAPI on port $($script:DevBackendPort) is missing Sprint 08.0 list params. A stale uvicorn worker may still be serving old code."
}
if (-not $frontendOk) {
    throw "Frontend failed to start on port $($script:DevFrontendPort). See $($frontend.Log) and $($frontend.ErrLog)"
}
if ($escapedPorts.Count -gt 0) {
    throw "Vite escaped to alternate port(s): $($escapedPorts -join ', '). Expected only $($script:DevFrontendPort)."
}

Write-Host ""
Write-Host "Backend PID:  $($backend.Process.Id) (log: $($backend.Log))"
Write-Host "Frontend PID: $($frontend.Process.Id) (log: $($frontend.Log))"

Show-DevRuntimeSummary -AlembicRevision $alembicStatus.Raw
Write-Host "Dev runtime reset complete."
