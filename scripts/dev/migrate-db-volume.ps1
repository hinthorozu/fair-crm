#Requires -Version 5.1
# File encoding: UTF-8 with BOM (required for Turkish output in Windows PowerShell 5.1).
<#
.SYNOPSIS
  Yerel PostgreSQL verisini eski konteyner/volume'dan yenisine taşır:
  kyrox-postgres-dev + fair-crm_kyrox_pg_data  ->  kyrox-db + kyrox-db-data

.DESCRIPTION
  Önce dev süreçlerini durdurur (dev-stop.ps1), güvenlik dump'ı alır, eski konteyneri
  durdurur (silmez), veriyi yeni volume'a kopyalar ve doğrular, kyrox-db'yi başlatır.
  Eski volume ve eski konteyner silinmez. Taşıma yapılmışsa bir şey yapmaz.
  Bitince dev ortamını yeniden başlatın: .\scripts\dev\reset-dev.ps1

.EXAMPLE
  .\scripts\dev\migrate-db-volume.ps1
#>
param(
    [string]$OldContainer = "kyrox-postgres-dev",
    [string]$OldVolume = "fair-crm_kyrox_pg_data",
    [string]$NewContainer = "kyrox-db",
    [string]$NewVolume = "kyrox-db-data",
    # Test için: başka bir docker-compose.yml klasörü ve dev süreçlerine dokunmama.
    [string]$ComposeDir = "",
    [switch]$SkipDevStop
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$PgUser = "postgres"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $ComposeDir) { $ComposeDir = $RepoRoot }
$ComposeFile = Join-Path $ComposeDir "docker-compose.yml"

function Write-Step([string]$Message) { Write-Host "[$(Get-Date -Format HH:mm:ss)] $Message" }

# Windows PowerShell 5.1: with ErrorActionPreference=Stop, anything a native command
# writes to stderr (docker compose progress, "No such container") becomes a terminating
# NativeCommandError. Run docker with Continue and judge by the exit code instead.
function Invoke-Docker {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & docker @args 2>&1 | ForEach-Object { "$_" }
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    if ($code -ne 0) { throw "docker $($args -join ' ') basarisiz: $($output -join ' ')" }
    return $output
}

function Test-DockerCommand {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & docker @args 2>&1 | Out-Null
        return ($LASTEXITCODE -eq 0)
    } finally {
        $ErrorActionPreference = $previous
    }
}

function Test-DockerObject([string]$Kind, [string]$Name) {
    return (Test-DockerCommand $Kind inspect $Name)
}

function Test-ContainerRunning([string]$Name) {
    if (-not (Test-DockerObject "container" $Name)) { return $false }
    return ((& docker inspect -f "{{.State.Running}}" $Name) -eq "true")
}

function Get-DbSnapshot([string]$Container) {
    $dbs = Invoke-Docker exec $Container psql -U $PgUser -d postgres -tAc "SELECT datname FROM pg_database WHERE NOT datistemplate ORDER BY 1"
    $lines = foreach ($db in ($dbs | Where-Object { $_ })) {
        $count = Invoke-Docker exec $Container psql -U $PgUser -d $db -tAc "SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')"
        "$db tablo=$(($count | Select-Object -First 1).ToString().Trim())"
    }
    return ($lines -join "`n")
}

function Write-Rollback {
    Write-Host ""
    Write-Host "Geri donmek icin (eski volume ve konteyner duruyor):"
    Write-Host "  docker stop $NewContainer"
    Write-Host "  docker start $OldContainer"
}

if (-not (Select-String -Path $ComposeFile -Pattern "container_name: $NewContainer" -Quiet) -or
    -not (Select-String -Path $ComposeFile -Pattern "name: $NewVolume" -Quiet)) {
    throw "$ComposeFile yeni adlari icermiyor; once repoyu guncelleyin (git pull)."
}

if ((Test-DockerObject "container" $NewContainer) -and -not (Test-ContainerRunning $OldContainer)) {
    Write-Step "Taşıma zaten yapılmış: $NewContainer var, $OldContainer çalışmıyor. Bir şey yapılmadı."
    exit 0
}
if (-not (Test-DockerObject "container" $OldContainer)) { throw "$OldContainer konteyneri yok." }
if (-not (Test-DockerObject "volume" $OldVolume)) { throw "$OldVolume volume'u yok." }
if (Test-DockerObject "volume" $NewVolume) { throw "$NewVolume zaten var; üzerine yazmamak için durduruldu." }
if (-not (Test-ContainerRunning $OldContainer)) { throw "$OldContainer çalışmıyor; önce Docker Desktop'ı ve konteyneri başlatın." }
$image = (Invoke-Docker inspect -f "{{.Config.Image}}" $OldContainer | Select-Object -First 1).ToString().Trim()

try {
    Write-Step "1) Öncesi: veritabanları ve tablo sayıları"
    $before = Get-DbSnapshot $OldContainer
    $before -split "`n" | ForEach-Object { Write-Host "   $_" }

    $dumpDir = Join-Path $ComposeDir ("backups\db-migration-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
    New-Item -ItemType Directory -Force -Path $dumpDir | Out-Null
    $dumpFile = Join-Path $dumpDir "pg_dumpall.sql"
    Write-Step "2) Güvenlik dump'ı: $dumpFile"
    $dumpErr = "$dumpFile.err"
    & cmd /c "docker exec $OldContainer pg_dumpall -U $PgUser > `"$dumpFile`" 2> `"$dumpErr`""
    if ($LASTEXITCODE -ne 0) { throw "pg_dumpall basarisiz: $(Get-Content $dumpErr -Raw)" }
    Remove-Item -LiteralPath $dumpErr -ErrorAction SilentlyContinue
    Write-Host ("   {0:N1} MB" -f ((Get-Item $dumpFile).Length / 1MB))

    if ($SkipDevStop) {
        Write-Step "3) Dev süreçleri durdurulmadı (-SkipDevStop)"
    } else {
        Write-Step "3) Dev süreçleri durduruluyor (dev-stop.ps1)"
        & (Join-Path $PSScriptRoot "dev-stop.ps1") | Out-Null
    }

    Write-Step "4) $OldContainer durduruluyor (silinmiyor)"
    Invoke-Docker stop $OldContainer | Out-Null

    Write-Step "5) Veri $OldVolume -> $NewVolume kopyalanıyor"
    Invoke-Docker volume create $NewVolume | Out-Null
    Invoke-Docker run --rm -v "${OldVolume}:/from:ro" -v "${NewVolume}:/to" $image sh -c "cp -a /from/. /to/" | Out-Null
    # No double quotes inside the sh script: Windows PowerShell 5.1 strips them from native arguments.
    $sizeScript = 'a=$(du -s /from | cut -f1); b=$(find /from | wc -l); c=$(du -s /to | cut -f1); d=$(find /to | wc -l); echo $a $b $c $d'
    $sizes = (Invoke-Docker run --rm -v "${OldVolume}:/from:ro" -v "${NewVolume}:/to:ro" $image sh -c $sizeScript | Select-Object -Last 1).ToString().Trim() -split '\s+'
    Write-Host "   eski: $($sizes[0]) KB / $($sizes[1]) dosya   yeni: $($sizes[2]) KB / $($sizes[3]) dosya"
    if ($sizes[0] -ne $sizes[2] -or $sizes[1] -ne $sizes[3]) { throw "Kopya eslesmiyor." }

    Write-Step "6) $NewContainer başlatılıyor"
    Push-Location $ComposeDir
    try { Invoke-Docker compose up -d postgres | Out-Null } finally { Pop-Location }
    $healthy = $false
    for ($i = 0; $i -lt 60; $i++) {
        if (Test-DockerCommand exec $NewContainer pg_isready -U $PgUser -q) { $healthy = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $healthy) { throw "$NewContainer sağlıklı açılmadı." }

    Write-Step "7) Sonrası: veritabanları ve tablo sayıları"
    $after = Get-DbSnapshot $NewContainer
    $after -split "`n" | ForEach-Object { Write-Host "   $_" }
    if ($before -ne $after) { throw "Öncesi ve sonrası farklı." }
}
catch {
    Write-Host "HATA: $($_.Exception.Message)" -ForegroundColor Red
    Write-Rollback
    exit 1
}

Write-Step "Tamam. Eski volume ($OldVolume) ve durdurulmuş $OldContainer yerinde duruyor."
Write-Host "Her şey çalışıyorsa sonra elle silinebilir: docker rm $OldContainer; docker volume rm $OldVolume"
Write-Host "Dev ortamını başlatmak için: .\scripts\dev\reset-dev.ps1"
Write-Rollback
