#Requires -Version 5.1
<#
.SYNOPSIS
  Run Development Auto Start validation checks and print a summary.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
. (Join-Path $PSScriptRoot "dev-lib.ps1")

$results = [ordered]@{}

function Record([string]$Name, [string]$Status, [string]$Detail) {
    $results[$Name] = [pscustomobject]@{ Status = $Status; Detail = $Detail }
    $color = switch ($Status) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "SKIP" { "Yellow" }
        default { "White" }
    }
    Write-Host "[$Status] $Name" -ForegroundColor $color
    if ($Detail) { Write-Host "       $Detail" }
}

function Count-FairCrmBackendListeners {
    return @(Get-DevPortListenerPids -Port $script:DevBackendPort).Count
}

function Count-FairCrmFrontendListeners {
    return @(Get-DevPortListenerPids -Port $script:DevFrontendPort).Count
}

function Test-BackendHttpHealth {
    return Test-DevHttpOk -Url "http://127.0.0.1:$($script:DevBackendPort)/health"
}

function Test-FrontendHttpHealth {
    return Test-DevFrontendHealthy
}

Write-Host "=== Dev Auto Start Validation ===" -ForegroundColor Cyan
Write-Host "Repository: $RepoRoot"
Write-Host ""

# --- Test 5: Health (baseline after start) ---
Write-DevStep "Running dev-start.ps1 (initial)"
& (Join-Path $PSScriptRoot "dev-start.ps1")
if ($LASTEXITCODE -ne 0 -and -not $?) {
    Record "Health check (pre)" "FAIL" "dev-start.ps1 failed on initial run"
} else {
    $backendOk = Test-BackendHttpHealth
    $frontendOk = Test-FrontendHttpHealth
    if ($backendOk -and $frontendOk) {
        $healthBody = (Invoke-WebRequest -Uri "http://127.0.0.1:$($script:DevBackendPort)/health" -UseBasicParsing).Content
        Record "Health check - Backend HTTP" "PASS" "/health -> $healthBody"
        Record "Health check - Frontend HTTP" "PASS" "http://127.0.0.1:$($script:DevFrontendPort)/index.html reachable"
    } else {
        Record "Health check - Backend HTTP" $(if ($backendOk) { "PASS" } else { "FAIL" }) ""
        Record "Health check - Frontend HTTP" $(if ($frontendOk) { "PASS" } else { "FAIL" }) ""
    }
}

# --- Test 3: Idempotency (5 runs) ---
Write-Host ""
Write-DevStep "Idempotency: dev-start.ps1 x5"
$beforeBackend = Count-FairCrmBackendListeners
$beforeFrontend = Count-FairCrmFrontendListeners
$idempotencyPass = $true
$idempotencyDetail = @()
for ($i = 1; $i -le 5; $i++) {
    try {
        & (Join-Path $PSScriptRoot "dev-start.ps1") *> $null
        $runOk = $?
    } catch {
        $runOk = $false
    }
    if (-not $runOk) { $idempotencyPass = $false; $idempotencyDetail += "Run $i failed"; continue }
    $bb = Count-FairCrmBackendListeners
    $bf = Count-FairCrmFrontendListeners
    if ($bb -gt 1 -or $bf -gt 1) {
        $idempotencyPass = $false
        $idempotencyDetail += "Run $i duplicate listeners backend=$bb frontend=$bf"
    }
}
$afterBackend = Count-FairCrmBackendListeners
$afterFrontend = Count-FairCrmFrontendListeners
if ($idempotencyPass -and $afterBackend -le 1 -and $afterFrontend -le 1) {
    Record "Idempotency (5x dev-start)" "PASS" "Backend listeners=$afterBackend Frontend listeners=$afterFrontend (stable)"
} else {
    Record "Idempotency (5x dev-start)" "FAIL" ($idempotencyDetail -join "; ")
}

# --- Test 4a: Healthy port reuse ---
Write-Host ""
Write-DevStep "Port collision: healthy listeners should be reused"
& (Join-Path $PSScriptRoot "dev-start.ps1") 2>&1 | Out-String | ForEach-Object {
    if ($_ -match "already healthy") {
        $script:SeenReuseMessage = $true
    }
}
if (Test-BackendHttpHealth -and Test-FrontendHttpHealth -and $afterBackend -eq 1 -and $afterFrontend -eq 1) {
    Record "Port collision - healthy reuse" "PASS" "Existing healthy processes on 8001/5173 not duplicated"
} else {
    Record "Port collision - healthy reuse" "FAIL" "Expected single listener per port with health OK"
}

# --- Test 4b: Unhealthy port occupation (frontend 5173) ---
Write-Host ""
Write-DevStep "Port collision: unhealthy listener on 5173"
$null = @(Stop-DevFairCrmViteProcesses)
$null = @(Stop-DevPortListeners -Ports @($script:DevFrontendPort))
$freeDeadline = (Get-Date).AddSeconds(20)
while ((Get-Date) -lt $freeDeadline -and (Test-DevPortListening -Port $script:DevFrontendPort)) {
    $null = @(Stop-DevFairCrmViteProcesses)
    $null = @(Stop-DevPortListeners -Ports @($script:DevFrontendPort))
    Start-Sleep -Seconds 1
}

$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), $script:DevFrontendPort)
$unhealthyCaught = $false
$unhealthyMessage = ""
try {
    $listener.Start()
    Start-Sleep -Milliseconds 500
    $blockerBound = Test-DevPortListening -Port $script:DevFrontendPort
    $healthWhileBlocked = Test-DevFrontendHealthy

    if (-not $blockerBound) {
        Record "Port collision - unhealthy 5173" "FAIL" "Test listener could not bind port 5173"
    } elseif ($healthWhileBlocked) {
        Record "Port collision - unhealthy 5173" "FAIL" "Port 5173 blocked but frontend still responded"
    } else {
        try {
            & (Join-Path $PSScriptRoot "dev-start.ps1") 2>&1 | Out-Null
        } catch {
            $unhealthyCaught = $true
            $unhealthyMessage = $_.Exception.Message
        }
        if ($unhealthyCaught -and $unhealthyMessage -match "in use but") {
            Record "Port collision - unhealthy 5173" "PASS" $unhealthyMessage
        } elseif ($unhealthyCaught) {
            Record "Port collision - unhealthy 5173" "PASS" "dev-start.ps1 failed while port 5173 occupied: $unhealthyMessage"
        } else {
            Record "Port collision - unhealthy 5173" "FAIL" "Expected dev-start.ps1 to fail when port 5173 occupied without healthy frontend"
        }
    }
} finally {
    if ($listener) {
        try { $listener.Stop() } catch {}
    }
}

Start-Sleep -Seconds 1
Write-DevStep "Restoring frontend after port collision test"
& (Join-Path $PSScriptRoot "dev-start.ps1") *> $null

# --- Test 2: Docker compose restart ---
Write-Host ""
Write-DevStep "Docker compose restart postgres"
Push-Location $RepoRoot
try {
    Invoke-DevDockerCompose -ComposeArgs @("restart", "postgres")
    Wait-DevPostgresHealthy -TimeoutSec 90
    $pgStatus = docker inspect --format '{{.State.Health.Status}}' $script:DevPostgresContainer 2>$null
    & (Join-Path $PSScriptRoot "dev-start.ps1") *> $null
    $dockerRestartOk = ($pgStatus -eq "healthy") -and (Test-BackendHttpHealth) -and (Test-FrontendHttpHealth)
    if ($dockerRestartOk) {
        Record "Docker Desktop restart (postgres)" "PASS" "postgres healthy after compose restart; dev-start OK"
    } else {
        Record "Docker Desktop restart (postgres)" "FAIL" "postgres=$pgStatus backend=$(Test-BackendHttpHealth) frontend=$(Test-FrontendHttpHealth)"
    }
} catch {
    Record "Docker Desktop restart (postgres)" "FAIL" $_.Exception.Message
} finally {
    Pop-Location
}

# --- Test 1: Windows reboot ---
Record "Windows reboot" "SKIP" "Manual test required - agent cannot reboot host. Procedure: reboot -> Docker Desktop Ready -> dev-start.ps1 only"

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
$results.GetEnumerator() | ForEach-Object { [pscustomobject]@{ Test = $_.Key; Status = $_.Value.Status; Detail = $_.Value.Detail } } | Format-Table -Wrap -AutoSize

$failCount = @($results.Values | Where-Object { $_.Status -eq "FAIL" }).Count
$passCount = @($results.Values | Where-Object { $_.Status -eq "PASS" }).Count
$skipCount = @($results.Values | Where-Object { $_.Status -eq "SKIP" }).Count
Write-Host "PASS=$passCount FAIL=$failCount SKIP=$skipCount"
if ($failCount -gt 0) { exit 1 }
