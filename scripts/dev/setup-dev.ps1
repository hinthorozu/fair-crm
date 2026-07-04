#Requires -Version 5.1
# File encoding: UTF-8 with BOM (required for Turkish output in Windows PowerShell 5.1).
<#
.SYNOPSIS
  Bootstrap checks for Fair CRM local development on a new machine.

.DESCRIPTION
  Verifies Python, Node.js, PostgreSQL, backend .env, Python/npm dependencies,
  and Playwright Chromium. Can install backend requirements, frontend packages,
  and Playwright browser — but does not install PostgreSQL. On Windows, missing or outdated
  Python/Node.js can be offered for installation via winget when available.

.PARAMETER CheckOnly
  Report missing items without running pip install, npm install, or playwright install.

.EXAMPLE
  .\scripts\dev\setup-dev.ps1

.EXAMPLE
  .\scripts\dev\setup-dev.ps1 -CheckOnly
#>
[CmdletBinding()]
param(
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# UTF-8 console output for Turkish messages (Windows PowerShell 5.1).
if ($env:OS -match 'Windows') {
    try { & "$env:SystemRoot\System32\chcp.com" 65001 | Out-Null } catch { }
}
$utf8Encoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = $utf8Encoding
[Console]::OutputEncoding = $utf8Encoding
$OutputEncoding = $utf8Encoding
if ($null -ne $Host -and $null -ne $Host.UI -and $null -ne $Host.UI.RawUI) {
    try { $Host.UI.RawUI.OutputEncoding = $utf8Encoding } catch { }
}

. (Join-Path $PSScriptRoot "dev-lib.ps1")

$script:SetupResults = [ordered]@{}
$script:SetupFailed = $false
$script:SetupMinNodeMajor = 18
$script:SetupMinPythonVersion = [version]"3.12.0"
$script:SetupNodeWingetId = "OpenJS.NodeJS.LTS"
$script:SetupPythonWingetId = "Python.Python.3.12"

function Write-SetupResult {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][ValidateSet("PASS", "FAIL", "SKIP", "WARN")]
        [string]$Status,
        [string]$Detail = ""
    )

    $script:SetupResults[$Name] = [pscustomobject]@{ Status = $Status; Detail = $Detail }
    if ($Status -eq "FAIL") {
        $script:SetupFailed = $true
    }

    $color = switch ($Status) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "WARN" { "Yellow" }
        "SKIP" { "DarkGray" }
        default { "White" }
    }
    Write-Host "[$Status] $Name" -ForegroundColor $color
    if ($Detail) {
        Write-Host "       $Detail"
    }
}

function Get-SetupCommandVersion {
    param(
        [Parameter(Mandatory)][string[]]$CommandCandidates,
        [Parameter(Mandatory)][string[]]$VersionArgs
    )

    foreach ($command in $CommandCandidates) {
        if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
            continue
        }
        try {
            $output = & $command @VersionArgs 2>&1 | Select-Object -First 1
            if ($LASTEXITCODE -ne 0 -and -not $?) {
                continue
            }
            $text = ($output | Out-String).Trim()
            if ($text) {
                return [pscustomobject]@{
                    Command = $command
                    Text    = $text
                }
            }
        } catch {
            continue
        }
    }

    return $null
}

function Get-SetupNodeMajorVersion {
    param([string]$VersionText)

    if ($VersionText -match 'v?(\d+)\.') {
        return [int]$matches[1]
    }
    return $null
}

function Convert-SetupNativeCommandLine {
    param([object]$Line)

    if ($null -eq $Line) {
        return ""
    }
    if ($Line -is [System.Management.Automation.ErrorRecord]) {
        $message = $Line.Exception.Message
        if ($message) {
            return $message.Trim()
        }
        return $Line.ToString().Trim()
    }
    return ($Line | Out-String).Trim()
}

function Get-SetupNodeVersionInfo {
    $commands = @()
    foreach ($name in @("node.exe", "node.cmd", "node")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command -and $commands -notcontains $command.Source) {
            $commands += $command.Source
        }
    }

    if ($commands.Count -eq 0) {
        return $null
    }

    $previousErrorAction = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        foreach ($command in $commands) {
            foreach ($versionArgs in @(@("-v"), @("--version"))) {
                $lines = @(& $command @versionArgs 2>&1 | Select-Object -First 3)
                foreach ($line in $lines) {
                    $text = Convert-SetupNativeCommandLine -Line $line
                    $match = [regex]::Match($text, 'v?\d+\.\d+\.\d+')
                    if ($match.Success) {
                        $version = $match.Value
                        if ($version -notmatch '^v') {
                            $version = "v$version"
                        }
                        return [pscustomobject]@{
                            Command = $command
                            Text    = $version
                        }
                    }
                }
            }
        }
    } finally {
        $ErrorActionPreference = $previousErrorAction
    }

    return $null
}

function Get-SetupPythonVersion {
    param([string]$VersionText)

    if ($VersionText -match 'Python\s+(\d+\.\d+\.\d+)') {
        return [version]$matches[1]
    }
    if ($VersionText -match '(\d+\.\d+\.\d+)') {
        return [version]$matches[1]
    }
    return $null
}

function Test-SetupWingetAvailable {
    if ($env:OS -notmatch 'Windows') {
        return $false
    }
    return $null -ne (Get-Command winget.exe -ErrorAction SilentlyContinue)
}

function Update-SetupPathEnvironment {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($machinePath -and $userPath) {
        $env:Path = "$machinePath;$userPath"
    } elseif ($machinePath) {
        $env:Path = $machinePath
    } elseif ($userPath) {
        $env:Path = $userPath
    }
}

function Test-SetupInstallConsent {
    param(
        [Parameter(Mandatory)][string]$Prompt
    )

    if ($CheckOnly) {
        return $false
    }

    Write-Host ""
    Write-Host $Prompt -ForegroundColor Yellow
    $answer = Read-Host "Devam etmek için E, iptal için H [E/H]"
    return ($answer -match '^(E|e|Y|y)$')
}

function Invoke-SetupWingetPackageInstall {
    param(
        [Parameter(Mandatory)][string]$PackageId,
        [Parameter(Mandatory)][string]$DisplayName
    )

    Write-DevStep "Installing $DisplayName via winget ($PackageId)"
    & winget.exe install --id $PackageId -e --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "winget install $PackageId failed with exit code $LASTEXITCODE"
    }
    Update-SetupPathEnvironment
}

function Resolve-SetupPythonPrerequisite {
    $info = Get-SetupCommandVersion -CommandCandidates @("python", "python3") -VersionArgs @("--version")
    if (-not $info) {
        return [pscustomobject]@{
            Ok             = $false
            VersionText    = $null
            ParsedVersion  = $null
            Issue          = "missing"
            ManualHint     = "Python bulunamadı. Python 3.12+ kurun: https://www.python.org/downloads/"
            WingetPrompt   = "Python 3.12 winget ile kurulsun mu? (winget install $($script:SetupPythonWingetId))"
        }
    }

    $parsed = Get-SetupPythonVersion -VersionText $info.Text
    if ($parsed -and $parsed -ge $script:SetupMinPythonVersion) {
        return [pscustomobject]@{
            Ok             = $true
            VersionText    = $info.Text
            ParsedVersion  = $parsed
            Issue          = "ok"
            ManualHint     = $null
            WingetPrompt   = $null
        }
    }

    $detail = if ($parsed) {
        "Python sürümü eski ($($info.Text)). Python $($script:SetupMinPythonVersion) veya üzeri gerekli."
    } else {
        "Python sürümü okunamadı ($($info.Text)). Python $($script:SetupMinPythonVersion) veya üzeri gerekli."
    }

    return [pscustomobject]@{
        Ok             = $false
        VersionText    = $info.Text
        ParsedVersion  = $parsed
        Issue          = "outdated"
        ManualHint     = "$detail Manuel: https://www.python.org/downloads/"
        WingetPrompt   = "Python 3.12 winget ile kurulsun mu? (winget install $($script:SetupPythonWingetId))"
    }
}

function Resolve-SetupNodePrerequisite {
    $info = Get-SetupNodeVersionInfo
    if (-not $info) {
        return [pscustomobject]@{
            Ok             = $false
            VersionText    = $null
            MajorVersion   = $null
            Issue          = "missing"
            ManualHint     = "Node.js bulunamadı. Node.js $($script:SetupMinNodeMajor)+ kurun: https://nodejs.org/"
            WingetPrompt   = "Node.js LTS winget ile kurulsun mu? (winget install $($script:SetupNodeWingetId))"
        }
    }

    $major = Get-SetupNodeMajorVersion -VersionText $info.Text
    if ($major -and $major -ge $script:SetupMinNodeMajor) {
        return [pscustomobject]@{
            Ok             = $true
            VersionText    = $info.Text
            MajorVersion   = $major
            Issue          = "ok"
            ManualHint     = $null
            WingetPrompt   = $null
        }
    }

    $detail = if ($major) {
        "Node.js eski: $($info.Text). Gerekli: $($script:SetupMinNodeMajor)+"
    } else {
        "Node.js sürümü okunamadı ($($info.Text)). Gerekli: $($script:SetupMinNodeMajor)+"
    }

    return [pscustomobject]@{
        Ok             = $false
        VersionText    = $info.Text
        MajorVersion   = $major
        Issue          = "outdated"
        ManualHint     = "$detail Manuel: https://nodejs.org/"
        WingetPrompt   = "Node.js LTS winget ile kurulsun mu? (winget install $($script:SetupNodeWingetId))"
    }
}

function Invoke-SetupOptionalWingetInstall {
    param(
        [Parameter(Mandatory)][string]$ToolName,
        [Parameter(Mandatory)][string]$PackageId,
        [Parameter(Mandatory)][string]$WingetPrompt,
        [Parameter(Mandatory)][string]$ManualHint,
        [Parameter(Mandatory)][scriptblock]$Recheck
    )

    if (-not (Test-SetupWingetAvailable)) {
        Write-SetupResult -Name $ToolName -Status "FAIL" -Detail (
            "$ManualHint winget bulunamadı; manuel kurulum gerekli."
        )
        return $Recheck.Invoke()
    }

    if ($CheckOnly) {
        Write-SetupResult -Name $ToolName -Status "FAIL" -Detail (
            "$ManualHint winget: winget install $PackageId"
        )
        return $Recheck.Invoke()
    }

    if (-not (Test-SetupInstallConsent -Prompt $WingetPrompt)) {
        Write-SetupResult -Name $ToolName -Status "FAIL" -Detail (
            "$ManualHint Kurulum iptal edildi."
        )
        return $Recheck.Invoke()
    }

    try {
        Invoke-SetupWingetPackageInstall -PackageId $PackageId -DisplayName $ToolName
        return $Recheck.Invoke()
    } catch {
        Write-SetupResult -Name $ToolName -Status "FAIL" -Detail (
            "$ManualHint winget kurulumu başarısız: $($_.Exception.Message)"
        )
        return $Recheck.Invoke()
    }
}

function Test-SetupTcpPort {
    param(
        [Parameter(Mandatory)][string]$HostName,
        [Parameter(Mandatory)][int]$Port,
        [int]$TimeoutMs = 3000
    )

    $client = $null
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $connect = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $connect.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
            return $false
        }
        $client.EndConnect($connect)
        return $true
    } catch {
        return $false
    } finally {
        if ($null -ne $client) {
            $client.Close()
        }
    }
}

function Get-SetupDatabaseEndpoint {
    param([string]$EnvFilePath)

    $hostName = "localhost"
    $port = 5432

    if (-not (Test-Path -LiteralPath $EnvFilePath)) {
        return [pscustomobject]@{
            Host    = $hostName
            Port    = $port
            FromEnv = $false
        }
    }

    $databaseUrl = $null
    foreach ($line in Get-Content -LiteralPath $EnvFilePath -ErrorAction SilentlyContinue) {
        if ($line -match '^\s*DATABASE_URL\s*=\s*(.+)\s*$') {
            $databaseUrl = $matches[1].Trim().Trim('"').Trim("'")
            break
        }
    }

    if ($databaseUrl -and $databaseUrl -match '@([^:/]+)(?::(\d+))?/') {
        $hostName = $matches[1]
        if ($matches[2]) {
            $port = [int]$matches[2]
        }
    }

    return [pscustomobject]@{
        Host    = $hostName
        Port    = $port
        FromEnv = $true
    }
}

function Test-SetupBackendRequirementsInstalled {
    Push-Location $script:DevBackendDir
    try {
        python -c "import fastapi, sqlalchemy, playwright" 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    } finally {
        Pop-Location
    }
}

function Test-SetupBackendRequirementsInstallable {
    Push-Location $script:DevBackendDir
    try {
        python -m pip install -r requirements.txt --dry-run --disable-pip-version-check 2>&1 | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    } finally {
        Pop-Location
    }
}

function Install-SetupBackendRequirements {
    Write-DevStep "Installing backend Python requirements (pip install -r requirements.txt)"
    Push-Location $script:DevBackendDir
    try {
        python -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            throw "pip install failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
}

function Test-SetupFrontendDependenciesInstalled {
    $vitePath = Join-Path $script:DevFrontendDir "node_modules\vite"
    return Test-Path -LiteralPath $vitePath
}

function Get-SetupNpmCommand {
    if (Get-Command npm.cmd -ErrorAction SilentlyContinue) {
        return "npm.cmd"
    }
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        return "npm"
    }
    return $null
}

function Test-SetupFrontendDependenciesInstallable {
    $npm = Get-SetupNpmCommand
    if (-not $npm) { return $false }
    Push-Location $script:DevFrontendDir
    try {
        & $npm install --dry-run 2>&1 | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    } finally {
        Pop-Location
    }
}

function Install-SetupFrontendDependencies {
    $npm = Get-SetupNpmCommand
    if (-not $npm) {
        throw "npm komutu bulunamadı."
    }
    Write-DevStep "Installing frontend dependencies (npm install)"
    Push-Location $script:DevFrontendDir
    try {
        & $npm install
        if ($LASTEXITCODE -ne 0) {
            throw "npm install failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
}

function Test-SetupPlaywrightChromiumInstalled {
    Push-Location $script:DevBackendDir
    try {
        python -c @"
from app.modules.scraper.core.playwright_availability import is_playwright_browser_installed
import sys
sys.exit(0 if is_playwright_browser_installed() else 1)
"@ 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    } finally {
        Pop-Location
    }
}

function Install-SetupPlaywrightChromium {
    Write-DevStep "Installing Playwright Chromium (python -m playwright install chromium)"
    Push-Location $script:DevBackendDir
    try {
        python -m playwright install chromium
        if ($LASTEXITCODE -ne 0) {
            throw "playwright install chromium failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
}

Write-DevStep "Fair CRM local development bootstrap"
Write-Host "Repository root: $script:DevRepoRoot"
if ($CheckOnly) {
    Write-Host "Mode: check only (no installs)."
} else {
    Write-Host "Mode: check and install missing Python/npm/Playwright artifacts."
}
Write-Host ""

$pythonOk = $false
$nodeOk = $false
$backendEnvPath = Join-Path $script:DevBackendDir ".env"
$backendEnvExamplePath = Join-Path $script:DevBackendDir ".env.example"

Write-DevStep "Checking prerequisites"

$pythonState = Resolve-SetupPythonPrerequisite
if ($pythonState.Ok) {
    $pythonOk = $true
    Write-SetupResult -Name "Python" -Status "PASS" -Detail $pythonState.VersionText
} else {
    $pythonState = Invoke-SetupOptionalWingetInstall `
        -ToolName "Python" `
        -PackageId $script:SetupPythonWingetId `
        -WingetPrompt $pythonState.WingetPrompt `
        -ManualHint $pythonState.ManualHint `
        -Recheck { Resolve-SetupPythonPrerequisite }
    if ($pythonState.Ok) {
        $pythonOk = $true
        Write-SetupResult -Name "Python" -Status "PASS" -Detail ($pythonState.VersionText + " (winget ile kuruldu)")
    } elseif (-not $script:SetupResults.Contains("Python")) {
        Write-SetupResult -Name "Python" -Status "FAIL" -Detail $pythonState.ManualHint
    }
}

$nodeState = Resolve-SetupNodePrerequisite
if ($nodeState.Ok) {
    $nodeOk = $true
    Write-SetupResult -Name "Node.js" -Status "PASS" -Detail $nodeState.VersionText
} else {
    $nodeState = Invoke-SetupOptionalWingetInstall `
        -ToolName "Node.js" `
        -PackageId $script:SetupNodeWingetId `
        -WingetPrompt $nodeState.WingetPrompt `
        -ManualHint $nodeState.ManualHint `
        -Recheck { Resolve-SetupNodePrerequisite }
    if ($nodeState.Ok) {
        $nodeOk = $true
        Write-SetupResult -Name "Node.js" -Status "PASS" -Detail ($nodeState.VersionText + " (winget ile kuruldu)")
    } elseif (-not $script:SetupResults.Contains("Node.js")) {
        Write-SetupResult -Name "Node.js" -Status "FAIL" -Detail $nodeState.ManualHint
    }
}

if (Test-Path -LiteralPath $backendEnvPath) {
    Write-SetupResult -Name "backend/.env" -Status "PASS" -Detail $backendEnvPath
} else {
    Write-SetupResult -Name "backend/.env" -Status "FAIL" -Detail (
        "backend/.env yok. Örnek: Copy-Item backend\.env.example backend\.env"
    )
}

$dbEndpoint = Get-SetupDatabaseEndpoint -EnvFilePath $backendEnvPath
if (Test-SetupTcpPort -HostName $dbEndpoint.Host -Port $dbEndpoint.Port) {
    Write-SetupResult -Name "PostgreSQL" -Status "PASS" -Detail (
        "Erişilebilir: $($dbEndpoint.Host):$($dbEndpoint.Port)"
    )
} else {
    Write-SetupResult -Name "PostgreSQL" -Status "FAIL" -Detail (
        "PostgreSQL erişilemiyor ($($dbEndpoint.Host):$($dbEndpoint.Port)). " +
        "Docker Desktop'ı başlatın ve repo kökünden 'docker compose up -d' çalıştırın."
    )
}

Write-Host ""
Write-DevStep "Checking dependencies"

if (-not $pythonOk) {
    Write-SetupResult -Name "Backend requirements" -Status "SKIP" -Detail "Python gerekli."
    Write-SetupResult -Name "Playwright Chromium" -Status "SKIP" -Detail "Python gerekli."
} else {
    $requirementsInstalled = Test-SetupBackendRequirementsInstalled
    if ($requirementsInstalled) {
        Write-SetupResult -Name "Backend requirements" -Status "PASS" -Detail "Temel paketler kurulu."
    } elseif ($CheckOnly) {
        if (Test-SetupBackendRequirementsInstallable) {
            Write-SetupResult -Name "Backend requirements" -Status "WARN" -Detail (
                "Kurulu değil; pip install -r backend/requirements.txt çalıştırılabilir."
            )
        } else {
            Write-SetupResult -Name "Backend requirements" -Status "FAIL" -Detail (
                "pip install -r backend/requirements.txt başarısız olur. Çıktı için komutu elle çalıştırın."
            )
        }
    } else {
        try {
            Install-SetupBackendRequirements
            if (Test-SetupBackendRequirementsInstalled) {
                Write-SetupResult -Name "Backend requirements" -Status "PASS" -Detail "pip install tamamlandı."
            } else {
                Write-SetupResult -Name "Backend requirements" -Status "FAIL" -Detail "Kurulum sonrası doğrulama başarısız."
            }
        } catch {
            Write-SetupResult -Name "Backend requirements" -Status "FAIL" -Detail $_.Exception.Message
        }
    }

    $playwrightInstalled = Test-SetupPlaywrightChromiumInstalled
    if ($playwrightInstalled) {
        Write-SetupResult -Name "Playwright Chromium" -Status "PASS" -Detail "Playwright Chromium kurulu."
    } elseif ($CheckOnly) {
        Write-SetupResult -Name "Playwright Chromium" -Status "WARN" -Detail (
            "Kurulu değil; backend dizininden: python -m playwright install chromium"
        )
    } else {
        try {
            Install-SetupPlaywrightChromium
            if (Test-SetupPlaywrightChromiumInstalled) {
                Write-SetupResult -Name "Playwright Chromium" -Status "PASS" -Detail "playwright install chromium tamamlandı."
            } else {
                Write-SetupResult -Name "Playwright Chromium" -Status "FAIL" -Detail "Kurulum sonrası doğrulama başarısız."
            }
        } catch {
            Write-SetupResult -Name "Playwright Chromium" -Status "FAIL" -Detail $_.Exception.Message
        }
    }
}

if (-not $nodeOk) {
    Write-SetupResult -Name "Frontend npm dependencies" -Status "SKIP" -Detail "Node.js gerekli."
} else {
    $frontendInstalled = Test-SetupFrontendDependenciesInstalled
    if ($frontendInstalled) {
        Write-SetupResult -Name "Frontend npm dependencies" -Status "PASS" -Detail "node_modules hazır."
    } elseif ($CheckOnly) {
        if (Test-SetupFrontendDependenciesInstallable) {
            Write-SetupResult -Name "Frontend npm dependencies" -Status "WARN" -Detail (
                "Kurulu değil; frontend dizininden npm install çalıştırılabilir."
            )
        } else {
            Write-SetupResult -Name "Frontend npm dependencies" -Status "FAIL" -Detail (
                "npm install başarısız olur. Çıktı için komutu elle çalıştırın."
            )
        }
    } else {
        try {
            Install-SetupFrontendDependencies
            if (Test-SetupFrontendDependenciesInstalled) {
                Write-SetupResult -Name "Frontend npm dependencies" -Status "PASS" -Detail "npm install tamamlandı."
            } else {
                Write-SetupResult -Name "Frontend npm dependencies" -Status "FAIL" -Detail "Kurulum sonrası doğrulama başarısız."
            }
        } catch {
            Write-SetupResult -Name "Frontend npm dependencies" -Status "FAIL" -Detail $_.Exception.Message
        }
    }
}

Write-Host ""
Write-Host "=== Bootstrap Summary ===" -ForegroundColor Cyan
$script:SetupResults.GetEnumerator() | ForEach-Object {
    Write-Host ("{0,-28} {1}" -f $_.Key, $_.Value.Status)
}

Write-Host ""
if ($script:SetupFailed) {
    Write-Host "Bootstrap tamamlanamadı. Yukarıdaki FAIL maddelerini düzeltin." -ForegroundColor Red
    if (-not (Test-Path -LiteralPath $backendEnvPath) -and (Test-Path -LiteralPath $backendEnvExamplePath)) {
        Write-Host "Örnek: Copy-Item backend\.env.example backend\.env" -ForegroundColor Yellow
    }
    exit 1
}

Write-Host "Bootstrap kontrolleri geçti." -ForegroundColor Green
Write-Host "Sonraki adım: .\scripts\dev\dev-start.ps1" -ForegroundColor Green
if (-not (Test-SetupTcpPort -HostName $dbEndpoint.Host -Port $dbEndpoint.Port)) {
    Write-Host "Not: PostgreSQL hâlâ erişilemiyor; dev-start öncesi Docker'ı başlatın." -ForegroundColor Yellow
}
exit 0
