#Requires -Version 5.1
<#
.SYNOPSIS
  Create a PostgreSQL custom-format backup of the Fair CRM dev database.

.DESCRIPTION
  Reads DATABASE_URL from backend/.env (or repo-root .env), runs pg_dump -Fc,
  stores the dump under backups/ with a timestamp, and verifies with pg_restore -l.

.EXAMPLE
  .\scripts\dev\backup-db.ps1
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "db-backup-lib.ps1")

$ctx = Initialize-FairCrmDbContext
$conn = $ctx.Connection

Write-DevStep "Fair CRM database backup"
Write-Host "Repository root: $($ctx.RepoRoot)"
Write-Host "Env file:        $($ctx.EnvFile)"
Write-Host "Database:        $($conn.Database) @ $($conn.Host):$($conn.Port)"
Write-Host "Toolchain:       $($ctx.Toolchain.Mode)"

if (-not (Test-Path $ctx.BackupsDir)) {
    New-Item -ItemType Directory -Force -Path $ctx.BackupsDir | Out-Null
    Write-Host "Created backups directory: $($ctx.BackupsDir)"
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupName = "faircrm_backup_${timestamp}.dump"
$backupPath = Join-Path $ctx.BackupsDir $backupName

Write-DevStep "Running pg_dump (custom format)"
Invoke-FairCrmPgDump -Context $ctx -BackupPath $backupPath

Write-DevStep "Verifying backup"
$verified = Test-BackupDumpFile -Context $ctx -DumpPath $backupPath

Write-Host ""
Write-Host "Backup complete." -ForegroundColor Green
Write-Host "File:      $($verified.Path)"
Write-Host "Size:      $($verified.SizeLabel)"
Write-Host "Modified:  $($verified.Modified)"
Write-Host "TOC items: $($verified.EntryCount)"
Write-Host ""
Write-Host "Restore with:"
Write-Host "  .\scripts\dev\restore-db.ps1 .\backups\$backupName" -ForegroundColor Yellow
Write-Host ""
Write-Host "List backups:"
Write-Host "  .\scripts\dev\list-backups.ps1" -ForegroundColor Yellow
