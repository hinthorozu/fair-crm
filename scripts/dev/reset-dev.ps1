#Requires -Version 5.1
<#
.SYNOPSIS
  Reset Fair CRM local dev runtime (backend + frontend) on standard ports.

.DESCRIPTION
  Clears stale listeners on backend port 8001 and frontend ports 5173-5177,
  then starts uvicorn (backend) and Vite (frontend with --strictPort 5173).
  Safe to run repeatedly from repository root.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$BackendPort = 8001
$FrontendPort = 5173
$FrontendAltPorts = @(5174, 5175, 5176, 5177)
$AllPorts = @($BackendPort) + $FrontendPort + $FrontendAltPorts

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"
$LogDir = Join-Path $RepoRoot "scripts\dev\logs"

function Write-Step([string]$Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-PortListenerPids([int]$Port) {
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

function Stop-PortListeners([int[]]$Ports) {
    $stopped = @()
    foreach ($port in $Ports) {
        $pids = Get-PortListenerPids -Port $port
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

function Test-PortBindable([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect("127.0.0.1", $Port)
        $client.Close()
        return $false
    } catch {
        return $true
    } finally {
        if ($client.Connected) { $client.Close() }
    }
}

function Ensure-PortFree([int]$Port, [int]$MaxAttempts = 5) {
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        if (Test-PortBindable -Port $Port) { return $true }
        Write-Host "Port $Port still accepting connections (attempt $attempt/$MaxAttempts)"
        $null = @(Stop-OrphanedUvicornWorkers)
        $null = @(Stop-FairCrmUvicornProcesses -Port $Port)
        $null = @(Stop-PortListeners -Ports @($Port))
        Start-Sleep -Seconds 2
    }
    return (Test-PortBindable -Port $Port)
}

function Stop-OrphanedUvicornWorkers() {
    # uvicorn --reload uses multiprocessing.spawn workers. When the reloader parent dies,
    # worker children can keep port 8001 and serve stale code while netstat shows dead PIDs.
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

function Stop-FairCrmUvicornProcesses([int]$Port) {
    # uvicorn --reload leaves parent reloader processes alive without holding the port.
    # Stopping only the port listener leaves stale reloaders serving old code on the next bind.
    $stopped = @()
    $processes = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue)
    foreach ($proc in $processes) {
        $cmd = $proc.CommandLine
        if (-not $cmd) { continue }
        if ($cmd -notmatch 'uvicorn') { continue }
        if ($cmd -notmatch 'app\.main:app') { continue }
        if ($cmd -notmatch "--port\s+$Port") { continue }
        try {
            Write-Host "Stopping stale uvicorn PID $($proc.ProcessId)"
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
            $stopped += $proc.ProcessId
        } catch {
            Write-Warning "Could not stop uvicorn PID $($proc.ProcessId): $($_.Exception.Message)"
        }
    }
    return @($stopped | Select-Object -Unique)
}

function Stop-FairCrmViteProcesses([int]$Port) {
    $stopped = @()
    $processes = @(Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue)
    foreach ($proc in $processes) {
        $cmd = $proc.CommandLine
        if (-not $cmd) { continue }
        if ($cmd -notmatch 'vite') { continue }
        if ($cmd -notmatch "--port\s+$Port") { continue }
        try {
            Write-Host "Stopping stale vite PID $($proc.ProcessId)"
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
            $stopped += $proc.ProcessId
        } catch {
            Write-Warning "Could not stop vite PID $($proc.ProcessId): $($_.Exception.Message)"
        }
    }
    return @($stopped | Select-Object -Unique)
}

function Wait-HttpOk([string[]]$Urls, [int]$TimeoutSec = 60) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        foreach ($Url in $Urls) {
            try {
                $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
                if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
                    return $true
                }
            } catch {
                # try next URL
            }
        }
        Start-Sleep -Milliseconds 750
    }
    return $false
}

function Get-PortReport([int[]]$Ports) {
    $rows = @()
    foreach ($port in $Ports) {
        $pids = @(Get-PortListenerPids -Port $port)
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

Write-Step "Fair CRM dev runtime reset"
Write-Host "Repository root: $RepoRoot"

if (-not (Test-Path $BackendDir)) {
    throw "Backend directory not found: $BackendDir"
}
if (-not (Test-Path $FrontendDir)) {
    throw "Frontend directory not found: $FrontendDir"
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Write-Step "Stopping stale Fair CRM dev processes (uvicorn/vite reloaders)"
$orphanWorkersStopped = @(Stop-OrphanedUvicornWorkers)
$uvicornStopped = @(Stop-FairCrmUvicornProcesses -Port $BackendPort)
$viteStopped = @(Stop-FairCrmViteProcesses -Port $FrontendPort)
if ($orphanWorkersStopped.Count -gt 0) {
    Write-Host "Stopped $($orphanWorkersStopped.Count) orphaned uvicorn worker(s)."
}
if ($uvicornStopped.Count -gt 0) {
    Write-Host "Stopped $($uvicornStopped.Count) uvicorn process(es)."
}
if ($viteStopped.Count -gt 0) {
    Write-Host "Stopped $($viteStopped.Count) vite process(es)."
}

Write-Step "Clearing stale listeners on ports: $($AllPorts -join ', ')"
$cleared = @(Stop-PortListeners -Ports $AllPorts)
if ($cleared.Count -gt 0) {
    Start-Sleep -Seconds 2
    Write-Host "Cleared $($cleared.Count) port listener(s)."
} else {
    Write-Host "No listeners found on target ports."
}
Start-Sleep -Seconds 1
if (-not (Ensure-PortFree -Port $BackendPort)) {
    throw "Port $BackendPort is still in use after cleanup. Stop remaining listeners manually."
}
if (-not (Ensure-PortFree -Port $FrontendPort)) {
    throw "Port $FrontendPort is still in use after cleanup. Stop remaining listeners manually."
}

Write-Step "Starting backend on port $BackendPort"
$backendLog = Join-Path $LogDir "backend-$BackendPort.log"
$backendErr = Join-Path $LogDir "backend-$BackendPort.err.log"
$backendArgs = @("-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "$BackendPort")
$backendProc = Start-Process -FilePath "python" -ArgumentList $backendArgs -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $backendLog -RedirectStandardError $backendErr -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2

Write-Step "Starting frontend on port $FrontendPort (strictPort)"
$frontendLog = Join-Path $LogDir "frontend-$FrontendPort.log"
$frontendErr = Join-Path $LogDir "frontend-$FrontendPort.err.log"
$frontendArgs = @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$FrontendPort", "--strictPort")
$frontendProc = Start-Process -FilePath "npm.cmd" -ArgumentList $frontendArgs -WorkingDirectory $FrontendDir `
    -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErr -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2

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

Write-Step "Verifying services"
$backendHealth = "http://127.0.0.1:$BackendPort/health"
$swaggerUrl = "http://127.0.0.1:$BackendPort/docs"
$frontendUrl = "http://127.0.0.1:$FrontendPort/"

$backendOk = Wait-HttpOk -Urls @($backendHealth)
$swaggerOk = Wait-HttpOk -Urls @($swaggerUrl)
$openapiOk = Test-ParticipantsSearchOpenApi -Port $BackendPort
$frontendOk = Wait-HttpOk -Urls @($frontendUrl, "$frontendUrl/index.html")

$escapedPorts = @()
foreach ($port in $FrontendAltPorts) {
    $pids = @(Get-PortListenerPids -Port $port)
    if ($pids.Count -gt 0) {
        $escapedPorts += $port
    }
}

Write-Host ""
Write-Host "Port status:" -ForegroundColor Yellow
Get-PortReport -Ports $AllPorts | Format-Table -AutoSize

Write-Host ""
if (-not $backendOk) {
    Write-Error "Backend failed to start on port $BackendPort. See $backendLog and $backendErr"
}
if (-not $swaggerOk) {
    Write-Error "Swagger is not reachable at $swaggerUrl"
}
if (-not $openapiOk) {
    Write-Error "Backend OpenAPI on port $BackendPort is missing Sprint 08.0 list params (search/pageSize/sort/direction). A stale uvicorn worker may still be serving old code."
}
if (-not $frontendOk) {
    Write-Error "Frontend failed to start on port $FrontendPort. See $frontendLog and $frontendErr"
}
if ($escapedPorts.Count -gt 0) {
    Write-Error "Vite escaped to alternate port(s): $($escapedPorts -join ', '). Expected only $FrontendPort."
}

Write-Host "Backend:  http://127.0.0.1:$BackendPort" -ForegroundColor Green
Write-Host "Swagger:  http://127.0.0.1:$BackendPort/docs" -ForegroundColor Green
Write-Host "Frontend: http://127.0.0.1:$FrontendPort" -ForegroundColor Green
Write-Host ""
Write-Host "Backend PID:  $($backendProc.Id) (log: $backendLog)"
Write-Host "Frontend PID: $($frontendProc.Id) (log: $frontendLog)"
Write-Host "Dev runtime reset complete."
