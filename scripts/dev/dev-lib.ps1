#Requires -Version 5.1
<#
.SYNOPSIS
  Shared helpers for Fair CRM development runtime scripts.
#>
Set-StrictMode -Version Latest

$script:DevCorePort = 8000
$script:DevBackendPort = 8001
$script:DevFairStandPort = 8002
$script:DevFrontendPort = 5173
$script:DevFrontendAltPorts = @(5174, 5175, 5176, 5177)
$script:DevAllRuntimePorts = @(
    $script:DevCorePort,
    $script:DevBackendPort,
    $script:DevFairStandPort
) + $script:DevFrontendPort + $script:DevFrontendAltPorts
$script:DevRepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$script:DevBackendDir = Join-Path $script:DevRepoRoot "backend"
$script:DevFrontendDir = Join-Path $script:DevRepoRoot "frontend"
$script:DevLogDir = Join-Path $script:DevRepoRoot "scripts\dev\logs"
$script:DevPostgresContainer = "kyrox-postgres-dev"
$script:DevCoreHealthUrl = "http://127.0.0.1:$($script:DevCorePort)/api/v1/health"

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

function Get-DevAlembicOutputLines {
    param([string]$Text)
    return @($Text -split "`r?`n" | Where-Object {
            $_ -match '\S' -and
            $_ -notmatch '^\s*INFO\s+\[' -and
            $_ -notmatch '^\s*WARNING\s+\[' -and
            $_ -notmatch '^python(\.exe)?\s*:'
        })
}

function Invoke-DevAlembicCommand {
    param([Parameter(Mandatory)][string[]]$AlembicArgs)
    Push-Location $script:DevRepoRoot
    try {
        $stdoutFile = New-TemporaryFile
        $stderrFile = New-TemporaryFile
        try {
            $proc = Start-Process -FilePath "python" -ArgumentList (@("-m", "alembic") + $AlembicArgs) `
                -WorkingDirectory $script:DevRepoRoot `
                -RedirectStandardOutput $stdoutFile.FullName `
                -RedirectStandardError $stderrFile.FullName `
                -Wait -PassThru -NoNewWindow
            $exitCode = $proc.ExitCode
            $stdout = (Get-Content -LiteralPath $stdoutFile.FullName -Raw -ErrorAction SilentlyContinue)
            $stderr = (Get-Content -LiteralPath $stderrFile.FullName -Raw -ErrorAction SilentlyContinue)
            if ($null -eq $stdout) { $stdout = "" }
            if ($null -eq $stderr) { $stderr = "" }
            $combined = ($stdout + [Environment]::NewLine + $stderr).Trim()
            return [pscustomobject]@{
                Output   = $combined
                StdOut   = $stdout.Trim()
                StdErr   = $stderr.Trim()
                ExitCode = $exitCode
            }
        } finally {
            Remove-Item -LiteralPath $stdoutFile.FullName, $stderrFile.FullName -Force -ErrorAction SilentlyContinue
        }
    } finally {
        Pop-Location
    }
}

function Get-DevGitBranch {
    Push-Location $script:DevRepoRoot
    try {
        return (git rev-parse --abbrev-ref HEAD).Trim()
    } finally {
        Pop-Location
    }
}

function Get-DevGitCommit {
    Push-Location $script:DevRepoRoot
    try {
        return (git rev-parse --short HEAD).Trim()
    } finally {
        Pop-Location
    }
}

function Assert-DevGitWorkingTreeClean {
    Push-Location $script:DevRepoRoot
    try {
        $status = @(git status --porcelain)
        if ($status.Count -gt 0) {
            Write-Host ($status -join [Environment]::NewLine)
            throw "Working tree is not clean. Commit or stash changes before pushing."
        }
    } finally {
        Pop-Location
    }
}

function Invoke-DevGitPull {
    Write-DevStep "Pulling latest changes for current branch"
    Push-Location $script:DevRepoRoot
    try {
        if (-not (Test-Path (Join-Path $script:DevRepoRoot ".git"))) {
            throw "Not a git repository: $script:DevRepoRoot"
        }

        $branch = git rev-parse --abbrev-ref HEAD
        if ($branch -eq "HEAD") {
            throw "Detached HEAD - checkout a branch before running the dev workflow."
        }

        git fetch origin 2>&1 | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) {
            throw "git fetch origin failed with exit code $LASTEXITCODE"
        }

        $upstream = git rev-parse --abbrev-ref "@{u}" 2>$null
        if ($LASTEXITCODE -eq 0 -and $upstream) {
            git pull --ff-only 2>&1 | ForEach-Object { Write-Host $_ }
        } else {
            Write-Host "No upstream configured - pulling origin/$branch"
            git pull --ff-only origin $branch 2>&1 | ForEach-Object { Write-Host $_ }
        }
        if ($LASTEXITCODE -ne 0) {
            throw "git pull failed with exit code $LASTEXITCODE"
        }

        Write-Host "Git pull complete on branch $branch (commit $(Get-DevGitCommit))."
    } finally {
        Pop-Location
    }
}

function Get-DevAlembicCurrentRevision {
    $result = Invoke-DevAlembicCommand -AlembicArgs @("current")
    if ($result.ExitCode -ne 0) {
        throw "alembic current failed: $($result.Output)"
    }

    $line = @(Get-DevAlembicOutputLines -Text $result.StdOut)
    if ($line.Count -eq 0) {
        $line = @(Get-DevAlembicOutputLines -Text $result.Output)
    }
    $line = $line | Select-Object -First 1
    if (-not $line) {
        return [pscustomobject]@{ Revision = "(none)"; IsHead = $false; Raw = "(none)" }
    }

    $isHead = $line -match '\(head\)'
    $revision = ($line -replace '\s*\(head\).*$', '').Trim()
    if (-not $revision) { $revision = $line.Trim() }

    return [pscustomobject]@{
        Revision = $revision
        IsHead   = [bool]$isHead
        Raw      = $line.Trim()
    }
}

function Get-DevAlembicHeadRevision {
    $result = Invoke-DevAlembicCommand -AlembicArgs @("heads")
    if ($result.ExitCode -ne 0) {
        throw "alembic heads failed: $($result.Output)"
    }

    $line = @(Get-DevAlembicOutputLines -Text $result.StdOut)
    if ($line.Count -eq 0) {
        $line = @(Get-DevAlembicOutputLines -Text $result.Output)
    }
    $line = $line | Select-Object -First 1
    if ($line -match '^([^\s\(]+)') {
        return $matches[1].Trim()
    }
    return $line.Trim()
}

function Test-DevAlembicSchemaUpToDate {
    $current = Get-DevAlembicCurrentRevision
    $head = Get-DevAlembicHeadRevision
    $upToDate = $current.IsHead -or ($current.Revision -eq $head)
    return [pscustomobject]@{
        UpToDate = $upToDate
        Current  = $current.Revision
        Head     = $head
        Raw      = $current.Raw
    }
}

function Invoke-DevAlembicUpgrade {
    Write-DevStep "Applying pending schema migrations (alembic upgrade head)"
    $result = Invoke-DevAlembicCommand -AlembicArgs @("upgrade", "head")
    if ($result.ExitCode -ne 0) {
        throw "alembic upgrade head failed: $($result.Output)"
    }
    $upgradeLines = @(Get-DevAlembicOutputLines -Text $result.StdOut)
    if ($upgradeLines.Count -gt 0) {
        Write-Host ($upgradeLines -join [Environment]::NewLine)
    }
}

function Get-DevBackendEnvValue {
    param([Parameter(Mandatory)][string]$Name)

    $envFile = Join-Path $script:DevBackendDir ".env"
    if (-not (Test-Path $envFile)) {
        return $null
    }

    foreach ($line in Get-Content -LiteralPath $envFile) {
        if ($line -match '^\s*#' -or $line -notmatch '\S') { continue }
        if ($line -match "^\s*$([regex]::Escape($Name))\s*=\s*(.+?)\s*$") {
            return $matches[1].Trim().Trim('"').Trim("'")
        }
    }

    return $null
}

function Get-DevDatabaseConnectionInfo {
    $databaseUrl = Get-DevBackendEnvValue -Name "DATABASE_URL"
    if (-not $databaseUrl) {
        $databaseUrl = "postgresql+psycopg2://postgres:postgres@localhost:5432/fair_crm"
    }

    if ($databaseUrl -notmatch '^[^:]+://([^:]+):([^@]+)@([^:/]+):(\d+)/([^?]+)$') {
        throw "Cannot parse DATABASE_URL for dev bootstrap: $databaseUrl"
    }

    $databaseName = $matches[5]
    if ($databaseName -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
        throw "Invalid database name in DATABASE_URL: $databaseName"
    }

    return [pscustomobject]@{
        User     = $matches[1]
        Password = $matches[2]
        Host     = $matches[3]
        Port     = $matches[4]
        Database = $databaseName
    }
}

function Ensure-DevPostgresDatabaseNamed {
    param([Parameter(Mandatory)][string]$DatabaseName)

    if (-not (Test-ComposeServiceDefined -ServiceName "postgres")) {
        Write-Host "Compose service 'postgres' not defined - skipping database ensure."
        return
    }

    if ($DatabaseName -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
        throw "Invalid database name: $DatabaseName"
    }

    Write-DevStep "Ensuring PostgreSQL database exists ($DatabaseName)"

    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $existsOutput = docker exec $script:DevPostgresContainer `
            psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DatabaseName'" 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to query PostgreSQL for database '$DatabaseName': $existsOutput"
        }

        $existsValue = (($existsOutput | Out-String).Trim())
        if ($existsValue -eq "1") {
            Write-Host "Database '$DatabaseName' already exists."
            return
        }

        $createOutput = docker exec $script:DevPostgresContainer `
            psql -U postgres -c "CREATE DATABASE $DatabaseName;" 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "CREATE DATABASE $DatabaseName failed: $createOutput"
        }

        Write-Host "Created database '$DatabaseName'."
    } finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Ensure-DevPostgresDatabase {
    if (-not (Test-ComposeServiceDefined -ServiceName "postgres")) {
        Write-Host "Compose service 'postgres' not defined - skipping database ensure."
        return
    }

    $conn = Get-DevDatabaseConnectionInfo
    Ensure-DevPostgresDatabaseNamed -DatabaseName $conn.Database
}

function Invoke-DevDatabaseMigrations {
    Ensure-DevPostgresDatabase

    Write-DevStep "Checking current Alembic revision"
    $before = Get-DevAlembicCurrentRevision
    $head = Get-DevAlembicHeadRevision
    Write-Host "Current revision: $($before.Raw)"
    Write-Host "Head revision:    $head"

    if ($before.Revision -ne $head -and -not $before.IsHead) {
        Write-Host "Pending migrations detected - upgrade required."
    } else {
        Write-Host "Database schema already at head."
    }

    Invoke-DevAlembicUpgrade

    Write-DevStep "Verifying database schema is up to date"
    $status = Test-DevAlembicSchemaUpToDate
    if (-not $status.UpToDate) {
        throw "Schema verification failed: current=$($status.Current) head=$($status.Head)"
    }

    Write-Host "Schema verified at head: $($status.Raw)"
    return $status
}

function Invoke-DevCoreIdentitySeed {
    $seedScript = Join-Path $script:DevRepoRoot "scripts\seed_core_dev_identity.py"
    if (-not (Test-Path -LiteralPath $seedScript)) {
        throw "Core dev identity seed script not found: $seedScript"
    }

    $devPassword = $env:DEV_USER_PASSWORD
    if (-not $devPassword) {
        $devPassword = Get-DevBackendEnvValue -Name "DEV_USER_PASSWORD"
    }
    if (-not $devPassword) {
        throw "DEV_USER_PASSWORD is missing. Add it to backend\.env before running dev-start.ps1."
    }

    Write-DevStep "Checking and synchronizing Core development identity seed"
    $previousPassword = $env:DEV_USER_PASSWORD
    try {
        $env:DEV_USER_PASSWORD = $devPassword
        Push-Location $script:DevRepoRoot
        try {
            & python $seedScript
            if ($LASTEXITCODE -ne 0) {
                throw "Core development identity seed failed with exit code $LASTEXITCODE"
            }
        } finally {
            Pop-Location
        }
    } finally {
        if ($null -eq $previousPassword) {
            Remove-Item Env:\DEV_USER_PASSWORD -ErrorAction SilentlyContinue
        } else {
            $env:DEV_USER_PASSWORD = $previousPassword
        }
        $devPassword = $null
    }
}

function Invoke-DevPrepareRepository {
    param([switch]$SkipPull)

    if (-not $SkipPull) {
        Invoke-DevGitPull
    } else {
        Write-Host "Skipping git pull (-SkipPull)."
    }
}

function Get-DevKyroxCoreRoot {
    $candidates = @()
    if ($env:KYROX_CORE_ROOT) {
        $candidates += $env:KYROX_CORE_ROOT
    }
    $candidates += (Join-Path (Split-Path $script:DevRepoRoot -Parent) "kyrox-core")
    $candidates += (Join-Path $script:DevRepoRoot "kyrox-core")

    foreach ($candidate in $candidates) {
        if (-not $candidate) { continue }
        if (Test-Path (Join-Path $candidate "backend\app\main.py")) {
            return (Resolve-Path $candidate).Path
        }
    }
    return $null
}

function Get-DevFairStandRoot {
    $candidates = @()
    if ($env:FAIR_STAND_ROOT) {
        $candidates += $env:FAIR_STAND_ROOT
    }
    $candidates += (Join-Path (Split-Path $script:DevRepoRoot -Parent) "fair-stand")
    $candidates += (Join-Path $script:DevRepoRoot "fair-stand")

    foreach ($candidate in $candidates) {
        if (-not $candidate) { continue }
        if (Test-Path (Join-Path $candidate "backend\app\main.py")) {
            return (Resolve-Path $candidate).Path
        }
    }
    return $null
}

function Get-DevFairStandBackendDir {
    $root = Get-DevFairStandRoot
    if (-not $root) { return $null }
    return (Join-Path $root "backend")
}

function Get-DevFairStandEnvValue {
    param([Parameter(Mandatory)][string]$Name)

    $backendDir = Get-DevFairStandBackendDir
    if (-not $backendDir) { return $null }
    $envFile = Join-Path $backendDir ".env"
    if (-not (Test-Path $envFile)) {
        return $null
    }

    foreach ($line in Get-Content -LiteralPath $envFile) {
        if ($line -match '^\s*#' -or $line -notmatch '\S') { continue }
        if ($line -match "^\s*$([regex]::Escape($Name))\s*=\s*(.+?)\s*$") {
            return $matches[1].Trim().Trim('"').Trim("'")
        }
    }

    return $null
}

function Get-DevFairStandDatabaseName {
    $databaseUrl = Get-DevFairStandEnvValue -Name "FAIR_STAND_DATABASE_URL"
    if (-not $databaseUrl) {
        $databaseUrl = "postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/fair_stand"
    }
    if ($databaseUrl -notmatch '/([^/?]+)(?:\?.*)?$') {
        throw "Cannot parse FAIR_STAND_DATABASE_URL for database name: $databaseUrl"
    }
    $databaseName = $matches[1]
    if ($databaseName -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
        throw "Invalid Fair Stand database name: $databaseName"
    }
    return $databaseName
}

function Invoke-DevFairStandAlembicCommand {
    param([Parameter(Mandatory)][string[]]$AlembicArgs)

    $backendDir = Get-DevFairStandBackendDir
    if (-not $backendDir) {
        throw "Fair Stand repository not found. Clone fair-stand as a sibling of fair-crm (../fair-stand) or set FAIR_STAND_ROOT."
    }

    $stdoutFile = New-TemporaryFile
    $stderrFile = New-TemporaryFile
    try {
        $proc = Start-Process -FilePath "python" -ArgumentList (@("-m", "alembic") + $AlembicArgs) `
            -WorkingDirectory $backendDir `
            -RedirectStandardOutput $stdoutFile.FullName `
            -RedirectStandardError $stderrFile.FullName `
            -Wait -PassThru -NoNewWindow
        $exitCode = $proc.ExitCode
        $stdout = (Get-Content -LiteralPath $stdoutFile.FullName -Raw -ErrorAction SilentlyContinue)
        $stderr = (Get-Content -LiteralPath $stderrFile.FullName -Raw -ErrorAction SilentlyContinue)
        if ($null -eq $stdout) { $stdout = "" }
        if ($null -eq $stderr) { $stderr = "" }
        $combined = ($stdout + [Environment]::NewLine + $stderr).Trim()
        return [pscustomobject]@{
            Output   = $combined
            StdOut   = $stdout.Trim()
            StdErr   = $stderr.Trim()
            ExitCode = $exitCode
        }
    } finally {
        Remove-Item -LiteralPath $stdoutFile.FullName, $stderrFile.FullName -Force -ErrorAction SilentlyContinue
    }
}

function Get-DevFairStandAlembicCurrentRevision {
    $result = Invoke-DevFairStandAlembicCommand -AlembicArgs @("current")
    if ($result.ExitCode -ne 0) {
        throw "Fair Stand alembic current failed: $($result.Output)"
    }

    $line = @(Get-DevAlembicOutputLines -Text $result.StdOut)
    if ($line.Count -eq 0) {
        $line = @(Get-DevAlembicOutputLines -Text $result.Output)
    }
    $line = $line | Select-Object -First 1
    if (-not $line) {
        return [pscustomobject]@{ Revision = "(none)"; IsHead = $false; Raw = "(none)" }
    }

    $isHead = $line -match '\(head\)'
    $revision = ($line -replace '\s*\(head\).*$', '').Trim()
    if (-not $revision) { $revision = $line.Trim() }

    return [pscustomobject]@{
        Revision = $revision
        IsHead   = [bool]$isHead
        Raw      = $line.Trim()
    }
}

function Get-DevFairStandAlembicHeadRevision {
    $result = Invoke-DevFairStandAlembicCommand -AlembicArgs @("heads")
    if ($result.ExitCode -ne 0) {
        throw "Fair Stand alembic heads failed: $($result.Output)"
    }

    $line = @(Get-DevAlembicOutputLines -Text $result.StdOut)
    if ($line.Count -eq 0) {
        $line = @(Get-DevAlembicOutputLines -Text $result.Output)
    }
    $line = $line | Select-Object -First 1
    if ($line -match '^([^\s\(]+)') {
        return $matches[1].Trim()
    }
    return $line.Trim()
}

function Invoke-DevFairStandDatabaseMigrations {
    if (-not (Get-DevFairStandRoot)) {
        throw "Fair Stand repository not found. Clone fair-stand as a sibling of fair-crm (../fair-stand) or set FAIR_STAND_ROOT."
    }

    Ensure-DevPostgresDatabaseNamed -DatabaseName (Get-DevFairStandDatabaseName)

    Write-DevStep "Checking Fair Stand Alembic revision"
    $before = Get-DevFairStandAlembicCurrentRevision
    $head = Get-DevFairStandAlembicHeadRevision
    Write-Host "Fair Stand current revision: $($before.Raw)"
    Write-Host "Fair Stand head revision:    $head"

    $upgrade = Invoke-DevFairStandAlembicCommand -AlembicArgs @("upgrade", "head")
    if ($upgrade.ExitCode -ne 0) {
        throw "Fair Stand alembic upgrade head failed: $($upgrade.Output)"
    }

    $after = Get-DevFairStandAlembicCurrentRevision
    $upToDate = $after.IsHead -or ($after.Revision -eq $head)
    if (-not $upToDate) {
        throw "Fair Stand schema verification failed: current=$($after.Revision) head=$head"
    }

    Write-Host "Fair Stand schema verified at head: $($after.Raw)"
    return $after
}

function Show-DevRuntimeSummary {
    param(
        [string]$AlembicRevision = "",
        [string]$FairStandAlembicRevision = ""
    )

    if (-not $AlembicRevision) {
        try {
            $AlembicRevision = (Get-DevAlembicCurrentRevision).Raw
        } catch {
            $AlembicRevision = "(unknown)"
        }
    }
    if (-not $FairStandAlembicRevision) {
        try {
            $FairStandAlembicRevision = (Get-DevFairStandAlembicCurrentRevision).Raw
        } catch {
            $FairStandAlembicRevision = "(unknown)"
        }
    }

    Write-Host ""
    Write-Host "=== Dev Runtime Summary ===" -ForegroundColor Cyan
    Write-Host "Git branch:            $(Get-DevGitBranch)"
    Write-Host "Git commit:            $(Get-DevGitCommit)"
    Write-Host "CRM alembic:           $AlembicRevision"
    Write-Host "Fair Stand alembic:    $FairStandAlembicRevision"
    Write-Host "Core URL:              http://localhost:$($script:DevCorePort)"
    Write-Host "CRM backend URL:       http://localhost:$($script:DevBackendPort)"
    Write-Host "Fair Stand API:        http://localhost:$($script:DevFairStandPort)"
    Write-Host "Frontend URL:          http://localhost:$($script:DevFrontendPort)"
    Write-Host "Fair Stand UI:         http://localhost:$($script:DevFrontendPort)/fair-stand"
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

function Test-DevCoreHealthy {
    return Test-DevHttpOk -Url $script:DevCoreHealthUrl
}

function Test-DevBackendHealthy {
    return Test-DevHttpOk -Url "http://127.0.0.1:$($script:DevBackendPort)/health"
}

function Test-DevFairStandHealthy {
    return Test-DevHttpOk -Url "http://127.0.0.1:$($script:DevFairStandPort)/health"
}

function Test-DevFrontendHealthy {
    $base = "http://127.0.0.1:$($script:DevFrontendPort)"
    return (Test-DevHttpOk -Url $base) -or (Test-DevHttpOk -Url "$base/index.html")
}

function Start-DevCore {
    $coreRoot = Get-DevKyroxCoreRoot
    if (-not $coreRoot) {
        throw @"
KYROX Core repository not found. Clone kyrox-core as a sibling of fair-crm (../kyrox-core) or set KYROX_CORE_ROOT to the repository path.
"@
    }
    $coreBackendDir = Join-Path $coreRoot "backend"
    if (-not (Test-Path $coreBackendDir)) {
        throw "KYROX Core backend directory not found: $coreBackendDir"
    }

    New-Item -ItemType Directory -Force -Path $script:DevLogDir | Out-Null
    $coreLog = Join-Path $script:DevLogDir "core-$($script:DevCorePort).log"
    $coreErr = Join-Path $script:DevLogDir "core-$($script:DevCorePort).err.log"
    $coreArgs = @("-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "$($script:DevCorePort)")
    # Avoid inheriting Fair CRM DATABASE_URL into Core process; let Core backend/.env load.
    if (Test-Path Env:DATABASE_URL) {
        Remove-Item Env:DATABASE_URL
    }
    Write-Host "Starting KYROX Core from: $coreRoot"
    $proc = Start-Process -FilePath "python" -ArgumentList $coreArgs -WorkingDirectory $coreBackendDir `
        -RedirectStandardOutput $coreLog -RedirectStandardError $coreErr -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 2
    return [pscustomobject]@{ Process = $proc; Log = $coreLog; ErrLog = $coreErr; Root = $coreRoot }
}

function Start-DevBackend {
    if (-not (Test-Path $script:DevBackendDir)) {
        throw "Backend directory not found: $script:DevBackendDir"
    }
    New-Item -ItemType Directory -Force -Path $script:DevLogDir | Out-Null
    $backendLog = Join-Path $script:DevLogDir "backend-$($script:DevBackendPort).log"
    $backendErr = Join-Path $script:DevLogDir "backend-$($script:DevBackendPort).err.log"
    $backendArgs = @("-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "$($script:DevBackendPort)")
    # Avoid inheriting KYROX Core DATABASE_URL into Fair CRM backend process.
    if (Test-Path Env:DATABASE_URL) {
        Remove-Item Env:DATABASE_URL
    }
    $proc = Start-Process -FilePath "python" -ArgumentList $backendArgs -WorkingDirectory $script:DevBackendDir `
        -RedirectStandardOutput $backendLog -RedirectStandardError $backendErr -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 2
    return [pscustomobject]@{ Process = $proc; Log = $backendLog; ErrLog = $backendErr }
}

function Start-DevFairStand {
    $backendDir = Get-DevFairStandBackendDir
    if (-not $backendDir) {
        throw "Fair Stand repository not found. Clone fair-stand as a sibling of fair-crm (../fair-stand) or set FAIR_STAND_ROOT."
    }
    New-Item -ItemType Directory -Force -Path $script:DevLogDir | Out-Null
    $standLog = Join-Path $script:DevLogDir "fair-stand-$($script:DevFairStandPort).log"
    $standErr = Join-Path $script:DevLogDir "fair-stand-$($script:DevFairStandPort).err.log"
    $standArgs = @("-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "$($script:DevFairStandPort)")
    if (Test-Path Env:DATABASE_URL) {
        Remove-Item Env:DATABASE_URL
    }
    Write-Host "Starting Fair Stand from: $backendDir"
    $proc = Start-Process -FilePath "python" -ArgumentList $standArgs -WorkingDirectory $backendDir `
        -RedirectStandardOutput $standLog -RedirectStandardError $standErr -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 2
    return [pscustomobject]@{ Process = $proc; Log = $standLog; ErrLog = $standErr }
}

function Start-DevFrontend {
    if (-not (Test-Path $script:DevFrontendDir)) {
        throw "Frontend directory not found: $script:DevFrontendDir"
    }
    New-Item -ItemType Directory -Force -Path $script:DevLogDir | Out-Null
    $frontendLog = Join-Path $script:DevLogDir "frontend-$($script:DevFrontendPort).log"
    $frontendErr = Join-Path $script:DevLogDir "frontend-$($script:DevFrontendPort).err.log"
    $frontendArgs = @("run", "dev", "--", "--host", "--port", "$($script:DevFrontendPort)", "--strictPort")
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
    $ports = @($script:DevCorePort, $script:DevBackendPort, $script:DevFairStandPort, $script:DevFrontendPort)
    if ($IncludeAltFrontendPorts) {
        $ports += $script:DevFrontendAltPorts
    }

    $null = @(Stop-DevOrphanedUvicornWorkers)
    $null = @(Stop-DevFairCrmUvicornProcesses -Port $script:DevCorePort)
    $null = @(Stop-DevFairCrmUvicornProcesses -Port $script:DevBackendPort)
    $null = @(Stop-DevFairCrmUvicornProcesses -Port $script:DevFairStandPort)
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
    Write-Host "Core:     http://localhost:$($script:DevCorePort)" -ForegroundColor Green
    Write-Host "Core health: $($script:DevCoreHealthUrl)" -ForegroundColor Green
    Write-Host "Backend:  http://localhost:$($script:DevBackendPort)" -ForegroundColor Green
    Write-Host "Swagger:  http://localhost:$($script:DevBackendPort)/docs" -ForegroundColor Green
    Write-Host "Fair Stand: http://localhost:$($script:DevFairStandPort)" -ForegroundColor Green
    Write-Host "Stand UI:  http://localhost:$($script:DevFrontendPort)/fair-stand" -ForegroundColor Green
    Write-Host "Frontend: http://localhost:$($script:DevFrontendPort)" -ForegroundColor Green
    Write-Host "Health:   http://localhost:$($script:DevBackendPort)/health" -ForegroundColor Green
    Write-Host "Stand health: http://localhost:$($script:DevFairStandPort)/health" -ForegroundColor Green
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
