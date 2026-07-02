#Requires -Version 5.1
<#
.SYNOPSIS
  Shared helpers for Fair CRM development runtime scripts.
#>
Set-StrictMode -Version Latest

$script:DevBackendPort = 8001
$script:DevFrontendPort = 5173
$script:DevFrontendAltPorts = @(5174, 5175, 5176, 5177)
$script:DevAllRuntimePorts = @($script:DevBackendPort) + $script:DevFrontendPort + $script:DevFrontendAltPorts
$script:DevRepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$script:DevBackendDir = Join-Path $script:DevRepoRoot "backend"
$script:DevFrontendDir = Join-Path $script:DevRepoRoot "frontend"
$script:DevLogDir = Join-Path $script:DevRepoRoot "scripts\dev\logs"
$script:DevPostgresContainer = "kyrox-postgres-dev"

function Write-DevStep([string]$Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-DevPortListenerPids([int]$Port) {
    $pids = @()

    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        $connections = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
        if ($connections.Count -gt 0) {
            $pids += $connections | Select-Object -ExpandProperty OwningProcess -Unique
        }
    } else {
        $pattern = ":\s*$Port\s"
        $netstat = netstat -ano | Select-String -Pattern $pattern
        foreach ($line in $netstat) {
            $parts = ($line -replace '\s+', ' ').Trim().Split(' ')
            if ($parts.Length -ge 5) {
                $pidValue = [int]$parts[-1]
                if ($pidValue -gt 0) { $pids += $pidValue }
            }
        }
    }

    return @($pids | Select-Object -Unique)
}

function Test-DevPortListening([int]$Port) {
    return @(Get-DevPortListenerPids -Port $Port).Count -gt 0
}

function Test-DevHttpOk([string]$Url, [int]$TimeoutSec = 5) {
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
        return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400)
    } catch {
        return $false
    }
}

function Wait-DevHttpOk([string[]]$Urls, [int]$TimeoutSec = 60) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        foreach ($Url in $Urls) {
            if (Test-DevHttpOk -Url $Url) { return $true }
        }
        Start-Sleep -Milliseconds 750
    }
    return $false
}

function Test-DockerEngineReady {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker CLI not found on PATH. Install Docker Desktop and ensure 'docker' is available."
    }
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        docker info *> $null
        if ($LASTEXITCODE -ne 0) {
            throw "Docker Engine is not running. Start Docker Desktop and wait until it reports Ready."
        }
    } catch {
        if ($_.Exception.Message -match "Docker Engine is not running") { throw }
        throw "Docker Engine is not running. Start Docker Desktop and wait until it reports Ready."
    } finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Get-ComposeServices {
    Push-Location $script:DevRepoRoot
    try {
        $services = @(docker compose config --services 2>$null)
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose config failed in $script:DevRepoRoot"
        }
        return $services
    } finally {
        Pop-Location
    }
}

function Test-ComposeServiceDefined([string]$ServiceName) {
    return (Get-ComposeServices) -contains $ServiceName
}

function Invoke-DevDockerCompose {
    param([Parameter(Mandatory)][string[]]$ComposeArgs)
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & docker compose @ComposeArgs 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose $($ComposeArgs -join ' ') failed with exit code $LASTEXITCODE"
        }
    } finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Start-DevDockerInfra {
    Write-DevStep "Starting Docker infrastructure (docker compose up -d)"
    Push-Location $script:DevRepoRoot
    try {
        Invoke-DevDockerCompose -ComposeArgs @("up", "-d")
    } finally {
        Pop-Location
    }
}

function Wait-DevPostgresHealthy([int]$TimeoutSec = 120) {
    if (-not (Test-ComposeServiceDefined -ServiceName "postgres")) {
        Write-Host "Compose service 'postgres' not defined - skipping PostgreSQL wait."
        return
    }

    Write-DevStep "Waiting for PostgreSQL to become healthy"
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $health = $null
        try {
            $health = docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' $script:DevPostgresContainer 2>$null
        } catch {
            $health = $null
        }

        if ($health -eq "healthy") {
            Write-Host "PostgreSQL is healthy ($script:DevPostgresContainer)."
            return
        }

        if ($health -eq "none") {
            $running = docker inspect --format '{{.State.Running}}' $script:DevPostgresContainer 2>$null
            if ($running -eq "true") {
                Write-Host "PostgreSQL container is running (no healthcheck reported)."
                return
            }
        }

        Start-Sleep -Seconds 2
    }

    throw "PostgreSQL did not become healthy within ${TimeoutSec}s. Check: docker compose ps"
}

function Wait-DevRedisHealthy([int]$TimeoutSec = 60) {
    if (-not (Test-ComposeServiceDefined -ServiceName "redis")) {
        Write-Host "Compose service 'redis' not defined - skipping Redis wait."
        return
    }

    Write-DevStep "Waiting for Redis to become healthy"
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $containerId = docker compose ps -q redis 2>$null
        if ($containerId) {
            $health = docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}running{{end}}' $containerId 2>$null
            if ($health -in @("healthy", "running")) {
                Write-Host "Redis is ready."
                return
            }
        }
        Start-Sleep -Seconds 2
    }

    throw "Redis did not become healthy within ${TimeoutSec}s. Check: docker compose ps"
}

function Stop-DevOrphanedUvicornWorkers {
    $stopped = @()
    $processes = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue)
    foreach ($proc in $processes) {
        $cmd = $proc.CommandLine
        if (-not $cmd) { continue }
        if ($cmd -notmatch 'multiprocessing\.spawn') { continue }
        if ($cmd -notmatch 'spawn_main') { continue }
        try {
            Write-Host "Stopping orphaned uvicorn worker PID $($proc.ProcessId)"
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
            $stopped += $proc.ProcessId
        } catch {
            Write-Warning "Could not stop orphaned worker PID $($proc.ProcessId): $($_.Exception.Message)"
        }
    }
    return @($stopped | Select-Object -Unique)
}

function Stop-DevFairCrmUvicornProcesses([int]$Port = $script:DevBackendPort) {
    $stopped = @()
    $processes = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue)
    foreach ($proc in $processes) {
        $cmd = $proc.CommandLine
        if (-not $cmd) { continue }
        if ($cmd -notmatch 'uvicorn') { continue }
        if ($cmd -notmatch 'app\.main:app') { continue }
        if ($cmd -notmatch "--port\s+$Port") { continue }
        try {
            Write-Host "Stopping uvicorn PID $($proc.ProcessId)"
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
            $stopped += $proc.ProcessId
        } catch {
            Write-Warning "Could not stop uvicorn PID $($proc.ProcessId): $($_.Exception.Message)"
        }
    }
    return @($stopped | Select-Object -Unique)
}

function Stop-DevFairCrmViteProcesses([int]$Port = $script:DevFrontendPort) {
    $stopped = @()
    $processes = @(Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue)
    foreach ($proc in $processes) {
        $cmd = $proc.CommandLine
        if (-not $cmd) { continue }
        if ($cmd -notmatch 'vite') { continue }
        if ($cmd -notmatch "--port\s+$Port") { continue }
        try {
            Write-Host "Stopping vite PID $($proc.ProcessId)"
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
            $stopped += $proc.ProcessId
        } catch {
            Write-Warning "Could not stop vite PID $($proc.ProcessId): $($_.Exception.Message)"
        }
    }
    return @($stopped | Select-Object -Unique)
}

function Stop-DevPortListeners([int[]]$Ports) {
    $stopped = @()
    foreach ($port in $Ports) {
        $pids = Get-DevPortListenerPids -Port $port
        foreach ($procId in $pids) {
            if ($procId -le 4) { continue }
            try {
                $proc = Get-Process -Id $procId -ErrorAction Stop
                Write-Host "Stopping PID $($proc.Id) ($($proc.ProcessName)) on port $port"
                Stop-Process -Id $procId -Force -ErrorAction Stop
                $stopped += [pscustomobject]@{ Port = $port; PID = $procId; Name = $proc.ProcessName }
            } catch {
                Write-Warning "Could not stop PID $procId on port ${port}: $($_.Exception.Message)"
            }
        }
    }
    return @($stopped)
}

function Test-DevBackendHealthy {
    return Test-DevHttpOk -Url "http://127.0.0.1:$($script:DevBackendPort)/health"
}

function Test-DevFrontendHealthy {
    $base = "http://127.0.0.1:$($script:DevFrontendPort)"
    return (Test-DevHttpOk -Url $base) -or (Test-DevHttpOk -Url "$base/index.html")
}

function Start-DevBackend {
    if (-not (Test-Path $script:DevBackendDir)) {
        throw "Backend directory not found: $script:DevBackendDir"
    }
    New-Item -ItemType Directory -Force -Path $script:DevLogDir | Out-Null
    $backendLog = Join-Path $script:DevLogDir "backend-$($script:DevBackendPort).log"
    $backendErr = Join-Path $script:DevLogDir "backend-$($script:DevBackendPort).err.log"
    $backendArgs = @("-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "$($script:DevBackendPort)")
    $proc = Start-Process -FilePath "python" -ArgumentList $backendArgs -WorkingDirectory $script:DevBackendDir `
        -RedirectStandardOutput $backendLog -RedirectStandardError $backendErr -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 2
    return [pscustomobject]@{ Process = $proc; Log = $backendLog; ErrLog = $backendErr }
}

function Start-DevFrontend {
    if (-not (Test-Path $script:DevFrontendDir)) {
        throw "Frontend directory not found: $script:DevFrontendDir"
    }
    New-Item -ItemType Directory -Force -Path $script:DevLogDir | Out-Null
    $frontendLog = Join-Path $script:DevLogDir "frontend-$($script:DevFrontendPort).log"
    $frontendErr = Join-Path $script:DevLogDir "frontend-$($script:DevFrontendPort).err.log"
    $frontendArgs = @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$($script:DevFrontendPort)", "--strictPort")
    $proc = Start-Process -FilePath "npm.cmd" -ArgumentList $frontendArgs -WorkingDirectory $script:DevFrontendDir `
        -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErr -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 2
    return [pscustomobject]@{ Process = $proc; Log = $frontendLog; ErrLog = $frontendErr }
}

function Start-DevWorkerIfConfigured {
    $workerScript = Join-Path $script:DevRepoRoot "scripts\dev\start-worker.ps1"
    if (-not (Test-Path $workerScript)) {
        Write-Host "No local worker script configured (scripts/dev/start-worker.ps1) - skipping."
        return $null
    }
    Write-DevStep "Starting worker via start-worker.ps1"
    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile", "-File", $workerScript) `
        -WorkingDirectory $script:DevRepoRoot -PassThru -WindowStyle Hidden
    return $proc
}

function Stop-DevWorkerIfRunning {
    $workerScript = Join-Path $script:DevRepoRoot "scripts\dev\start-worker.ps1"
    if (-not (Test-Path $workerScript)) { return @() }

    $stopped = @()
    $processes = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue)
    foreach ($proc in $processes) {
        $cmd = $proc.CommandLine
        if (-not $cmd) { continue }
        if ($cmd -notmatch [regex]::Escape($workerScript)) { continue }
        try {
            Write-Host "Stopping worker launcher PID $($proc.ProcessId)"
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
            $stopped += $proc.ProcessId
        } catch {
            Write-Warning "Could not stop worker PID $($proc.ProcessId): $($_.Exception.Message)"
        }
    }
    return @($stopped)
}

function Stop-DevRuntimeProcesses([switch]$IncludeAltFrontendPorts) {
    $ports = @($script:DevBackendPort, $script:DevFrontendPort)
    if ($IncludeAltFrontendPorts) {
        $ports += $script:DevFrontendAltPorts
    }

    $null = @(Stop-DevOrphanedUvicornWorkers)
    $null = @(Stop-DevFairCrmUvicornProcesses)
    $null = @(Stop-DevFairCrmViteProcesses)
    $null = @(Stop-DevWorkerIfRunning)
    return @(Stop-DevPortListeners -Ports $ports)
}

function Get-DevPortReport([int[]]$Ports) {
    $rows = @()
    foreach ($port in $Ports) {
        $pids = @(Get-DevPortListenerPids -Port $port)
        if ($pids.Count -eq 0) {
            $rows += [pscustomobject]@{ Port = $port; PID = "-"; Process = "(free)" }
            continue
        }
        foreach ($procId in $pids) {
            $name = "(unknown)"
            try { $name = (Get-Process -Id $procId -ErrorAction Stop).ProcessName } catch {}
            $rows += [pscustomobject]@{ Port = $port; PID = $procId; Process = $name }
        }
    }
    return $rows
}

function Show-DevServiceUrls {
    Write-Host ""
    Write-Host "Backend:  http://localhost:$($script:DevBackendPort)" -ForegroundColor Green
    Write-Host "Swagger:  http://localhost:$($script:DevBackendPort)/docs" -ForegroundColor Green
    Write-Host "Frontend: http://localhost:$($script:DevFrontendPort)" -ForegroundColor Green
    Write-Host "Health:   http://localhost:$($script:DevBackendPort)/health" -ForegroundColor Green
}

function Show-DevDockerStatus {
    Push-Location $script:DevRepoRoot
    try {
        Write-Host ""
        Write-Host "Docker compose status:" -ForegroundColor Yellow
        docker compose ps
    } finally {
        Pop-Location
    }
}
