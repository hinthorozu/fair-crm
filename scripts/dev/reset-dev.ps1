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

Write-Step "Clearing stale listeners on ports: $($AllPorts -join ', ')"
$cleared = @(Stop-PortListeners -Ports $AllPorts)
if ($cleared.Count -gt 0) {
    Start-Sleep -Seconds 2
    Write-Host "Cleared $($cleared.Count) process(es)."
} else {
    Write-Host "No listeners found on target ports."
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

Write-Step "Verifying services"
$backendHealth = "http://127.0.0.1:$BackendPort/health"
$swaggerUrl = "http://127.0.0.1:$BackendPort/docs"
$frontendUrl = "http://127.0.0.1:$FrontendPort/"

$backendOk = Wait-HttpOk -Urls @($backendHealth)
$swaggerOk = Wait-HttpOk -Urls @($swaggerUrl)
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
