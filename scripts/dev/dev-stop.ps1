#Requires -Version 5.1
<#
.SYNOPSIS
  Stop Fair CRM local runtime processes (backend, frontend, optional worker).

.DESCRIPTION
  Does not stop Docker infrastructure by default. Pass -StopInfra to run docker compose stop.

.PARAMETER StopInfra
  Also stop Docker Compose infrastructure services (PostgreSQL, etc.).

.EXAMPLE
  .\scripts\dev\dev-stop.ps1

.EXAMPLE
  .\scripts\dev\dev-stop.ps1 -StopInfra
#>
[CmdletBinding()]
param(
    [switch]$StopInfra
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-lib.ps1")

Write-DevStep "Fair CRM dev-stop"
Write-Host "Repository root: $script:DevRepoRoot"

$cleared = @(Stop-DevRuntimeProcesses -IncludeAltFrontendPorts)
if ($cleared.Count -gt 0) {
    Write-Host "Stopped $($cleared.Count) runtime listener(s)."
} else {
    Write-Host "No Fair CRM runtime listeners found on standard ports."
}

if ($StopInfra) {
    Write-DevStep "Stopping Docker infrastructure (docker compose stop)"
    Push-Location $script:DevRepoRoot
    try {
        Invoke-DevDockerCompose -ComposeArgs @("stop")
    } finally {
        Pop-Location
    }
    Show-DevDockerStatus
} else {
    Write-Host "Docker infrastructure left running (use -StopInfra to stop containers)."
}

Write-Host "dev-stop complete."
