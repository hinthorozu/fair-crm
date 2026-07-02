# Shared helpers for Fair CRM PostgreSQL backup/restore dev utilities.
Set-StrictMode -Version Latest

$script:DefaultDockerContainer = "kyrox-postgres-dev"

function Get-FairCrmRepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Get-FairCrmBackupsDir {
    param([string]$RepoRoot = (Get-FairCrmRepoRoot))
    return (Join-Path $RepoRoot "backups")
}

function Get-FairCrmEnvFilePath {
    param([string]$RepoRoot = (Get-FairCrmRepoRoot))
    $candidates = @(
        (Join-Path $RepoRoot "backend\.env"),
        (Join-Path $RepoRoot ".env")
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }
    throw "No .env file found. Expected backend\.env or .env under repository root."
}

function Read-DatabaseUrlFromEnv {
    param([string]$RepoRoot = (Get-FairCrmRepoRoot))
    $envFile = Get-FairCrmEnvFilePath -RepoRoot $RepoRoot
    $line = Get-Content -Path $envFile -ErrorAction Stop |
        Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } |
        Select-Object -First 1
    if (-not $line) {
        throw "DATABASE_URL not found in $envFile"
    }
    $value = ($line -split '=', 2)[1].Trim().Trim('"').Trim("'")
    if (-not $value) {
        throw "DATABASE_URL is empty in $envFile"
    }
    return $value
}

function ConvertTo-PostgresConnection {
    param([Parameter(Mandatory = $true)][string]$DatabaseUrl)
    $pattern = '^(?<scheme>postgres(?:ql)?(?:\+\w+)?)://(?:(?<user>[^:@/]+)(?::(?<password>[^@]*))?@)?(?<host>[^:/]+)(?::(?<port>\d+))?/(?<database>[^?/#]+)'
    if ($DatabaseUrl -notmatch $pattern) {
        throw "Unsupported DATABASE_URL format. Expected postgresql://user:pass@host:port/dbname"
    }
    return [pscustomobject]@{
        User     = $Matches.user
        Password = $Matches.password
        Host     = $Matches.host
        Port     = if ($Matches.port) { [int]$Matches.port } else { 5432 }
        Database = $Matches.database
    }
}

function Test-LocalHostDatabase {
    param([Parameter(Mandatory = $true)]$Connection)
    return $Connection.Host -in @("localhost", "127.0.0.1", "::1")
}

function Get-PostgresDockerContainer {
    param([string]$PreferredName = $script:DefaultDockerContainer)
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        return $null
    }
    $running = docker ps --filter "name=^/${PreferredName}$" --filter "status=running" -q 2>$null
    if ($running) { return $PreferredName }
    return $null
}

function Resolve-PgTool {
    param([Parameter(Mandatory = $true)][string]$ToolName)
    $cmd = Get-Command $ToolName -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $searchRoots = @(
        ${env:ProgramFiles},
        ${env:ProgramFiles(x86)}
    ) | Where-Object { $_ -and (Test-Path $_) }

    foreach ($root in $searchRoots) {
        $pgRoot = Join-Path $root "PostgreSQL"
        if (-not (Test-Path $pgRoot)) { continue }
        $matches = Get-ChildItem -Path $pgRoot -Recurse -Filter "$ToolName.exe" -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending
        if ($matches) { return $matches[0].FullName }
    }

    return $null
}

function Get-PgToolchain {
    param([Parameter(Mandatory = $true)]$Connection)
    $pgDump = Resolve-PgTool -ToolName "pg_dump"
    $pgRestore = Resolve-PgTool -ToolName "pg_restore"
    if ($pgDump -and $pgRestore) {
        return [pscustomobject]@{
            Mode      = "local"
            PgDump    = $pgDump
            PgRestore = $pgRestore
        }
    }

    if (Test-LocalHostDatabase -Connection $Connection) {
        $container = Get-PostgresDockerContainer
        if ($container) {
            return [pscustomobject]@{
                Mode      = "docker"
                Container = $container
            }
        }
    }

    throw "pg_dump/pg_restore not found in PATH and Docker fallback unavailable. Install PostgreSQL client tools or start $script:DefaultDockerContainer."
}

function Write-DevStep([string]$Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Format-FileSize([long]$Bytes) {
    if ($Bytes -ge 1GB) { return "{0:N2} GB" -f ($Bytes / 1GB) }
    if ($Bytes -ge 1MB) { return "{0:N2} MB" -f ($Bytes / 1MB) }
    if ($Bytes -ge 1KB) { return "{0:N2} KB" -f ($Bytes / 1KB) }
    return "$Bytes bytes"
}

function Invoke-DockerPgTool {
    param(
        [Parameter(Mandatory = $true)][string]$Container,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    $output = docker exec $Container @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ("docker exec failed:`n{0}" -f ($output -join [Environment]::NewLine))
    }
    return $output
}

function Copy-DumpToDockerContainer {
    param(
        [Parameter(Mandatory = $true)][string]$Container,
        [Parameter(Mandatory = $true)][string]$LocalPath,
        [Parameter(Mandatory = $true)][string]$RemotePath
    )
    docker cp $LocalPath "${Container}:${RemotePath}" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "docker cp to container failed for $LocalPath"
    }
}

function Copy-DumpFromDockerContainer {
    param(
        [Parameter(Mandatory = $true)][string]$Container,
        [Parameter(Mandatory = $true)][string]$RemotePath,
        [Parameter(Mandatory = $true)][string]$LocalPath
    )
    docker cp "${Container}:${RemotePath}" $LocalPath | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "docker cp from container failed for $RemotePath"
    }
}

function Invoke-FairCrmPgDump {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$BackupPath
    )
    $backendDir = Join-Path $Context.RepoRoot "backend"
    Push-Location $backendDir
    try {
        python -m app.shared.database_backup backup --output $BackupPath
        if ($LASTEXITCODE -ne 0) {
            throw "Python backup engine failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
}

function Get-FairCrmPgRestoreListOutput {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$DumpPath
    )
    $backendDir = Join-Path $Context.RepoRoot "backend"
    $fileName = Split-Path -Leaf $DumpPath
    Push-Location $backendDir
    try {
        python -m app.shared.database_backup verify $fileName
        if ($LASTEXITCODE -ne 0) {
            throw "Python verify failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
    return @("verified")
}

function Invoke-FairCrmPgRestore {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$DumpPath
    )
    $backendDir = Join-Path $Context.RepoRoot "backend"
    $fileName = Split-Path -Leaf $DumpPath
    Push-Location $backendDir
    try {
        python -m app.shared.database_backup restore $fileName --confirm $($Context.Connection.Database)
        if ($LASTEXITCODE -ne 0) {
            throw "Python restore failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
}

function Test-BackupDumpFile {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$DumpPath
    )
    if (-not (Test-Path $DumpPath)) {
        throw "Backup file not found: $DumpPath"
    }
    $info = Get-Item $DumpPath
    if ($info.Length -le 0) {
        throw "Backup file is empty: $DumpPath"
    }

    $listOutput = Get-FairCrmPgRestoreListOutput -Context $Context -DumpPath $DumpPath
    $entryCount = if (@($listOutput).Count -gt 0) { @($listOutput).Count } else { 1 }
    return [pscustomobject]@{
        Path       = $DumpPath
        SizeBytes  = $info.Length
        SizeLabel  = (Format-FileSize $info.Length)
        Modified   = $info.LastWriteTime
        EntryCount = $entryCount
        ListOutput = $listOutput
    }
}

function Initialize-FairCrmDbContext {
    param([string]$RepoRoot = (Get-FairCrmRepoRoot))
    $databaseUrl = Read-DatabaseUrlFromEnv -RepoRoot $RepoRoot
    $conn = ConvertTo-PostgresConnection -DatabaseUrl $databaseUrl
    $toolchain = Get-PgToolchain -Connection $conn
    $script:PgPassword = $conn.Password
    return [pscustomobject]@{
        RepoRoot    = $RepoRoot
        EnvFile     = (Get-FairCrmEnvFilePath -RepoRoot $RepoRoot)
        DatabaseUrl = $databaseUrl
        Connection  = $conn
        Toolchain   = $toolchain
        BackupsDir  = (Get-FairCrmBackupsDir -RepoRoot $RepoRoot)
    }
}
