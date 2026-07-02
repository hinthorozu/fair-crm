#Requires -Version 5.1
<#
.SYNOPSIS
  Restore a PostgreSQL custom-format backup into the Fair CRM dev database.

.DESCRIPTION
  Reads DATABASE_URL from backend/.env (or repo-root .env). Requires explicit
  confirmation before overwriting the target database. Pass -DryRun to validate
  the dump without making changes.

.PARAMETER BackupFile
  Path to a .dump file (relative to repo root or absolute).

.PARAMETER DryRun
  Validate the dump with pg_restore -l only; do not restore.

.EXAMPLE
  .\scripts\dev\restore-db.ps1 .\backups\fair_crm_20260702_120000.dump -DryRun

.EXAMPLE
  .\scripts\dev\restore-db.ps1 .\backups\fair_crm_20260702_120000.dump
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$BackupFile,

    [switch]$DryRun
)

$restoreDryRun = $DryRun.IsPresent

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "db-backup-lib.ps1")

$ctx = Initialize-FairCrmDbContext
$conn = $ctx.Connection

$resolvedBackup = if ([System.IO.Path]::IsPathRooted($BackupFile)) {
    $BackupFile
} else {
    Join-Path $ctx.RepoRoot $BackupFile
}
$resolvedBackup = (Resolve-Path $resolvedBackup -ErrorAction Stop).Path

if ($resolvedBackup -notlike "*.dump") {
    throw "Backup file must use PostgreSQL custom format (.dump): $resolvedBackup"
}

Write-DevStep "Fair CRM database restore"
Write-Host "Repository root: $($ctx.RepoRoot)"
Write-Host "Env file:        $($ctx.EnvFile)"
Write-Host "Backup file:     $resolvedBackup"
Write-Host "Target database: $($conn.Database) @ $($conn.Host):$($conn.Port)"
Write-Host "Toolchain:       $($ctx.Toolchain.Mode)"
if ($restoreDryRun) {
    Write-Host "Mode:            validate-only (dry-run)"
}

$verified = Test-BackupDumpFile -Context $ctx -DumpPath $resolvedBackup

Write-Host ""
Write-Host "Backup validation OK"
Write-Host "Size:      $($verified.SizeLabel)"
Write-Host "TOC items: $($verified.EntryCount)"

if ($restoreDryRun) {
    Write-Host ""
    Write-Host "Dry-run only - no database changes were made." -ForegroundColor Yellow
    Write-Host "To restore, rerun without -DryRun and confirm when prompted."
    exit 0
}

Write-Host ""
Write-Warning "This will OVERWRITE schema and data in database '$($conn.Database)' on $($conn.Host):$($conn.Port)."
Write-Host "All current contents of that database will be replaced by the backup."
Write-Host ""
Write-Host "Type the database name '$($conn.Database)' to continue, or anything else to cancel:" -ForegroundColor Yellow
$typedDbName = Read-Host "Confirm"
if ($typedDbName -ne $conn.Database) {
    Write-Host "Restore cancelled - confirmation did not match." -ForegroundColor Red
    exit 1
}

Write-DevStep "Running pg_restore"
Invoke-FairCrmPgRestore -Context $ctx -DumpPath $resolvedBackup

Write-Host ""
Write-Host "Restore complete." -ForegroundColor Green
Write-Host "Database '$($conn.Database)' was restored from:"
Write-Host "  $resolvedBackup"
