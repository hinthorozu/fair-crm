#Requires -Version 5.1
<#
.SYNOPSIS
  Execute a persisted Fair CRM restore job via the maintenance runner.

.DESCRIPTION
  Loads a restore job from the CRM database and runs destructive pg_restore against
  an explicitly provided target database URL. This script is intentionally guarded:

  - ALLOW_RESTORE=true is required
  - TARGET_DATABASE_URL must be set explicitly (not inferred from backend .env by default)

  Manual smoke test:
  1. Create a restore job from Admin -> System -> Database Backups (restore request).
  2. Note the job id from the Restore Jobs table.
  3. Run:
       $env:ALLOW_RESTORE = "true"
       $env:TARGET_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/fair_crm"
       .\scripts\dev\run-restore-job.ps1 -RestoreJobId "<job-id>"
  4. Verify job status becomes completed and log path is populated.

.PARAMETER RestoreJobId
  UUID of the persisted restore job.

.EXAMPLE
  $env:ALLOW_RESTORE = "true"
  $env:TARGET_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/fair_crm"
  .\scripts\dev\run-restore-job.ps1 -RestoreJobId "00000000-0000-4000-8000-000000000099"
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$RestoreJobId
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "db-backup-lib.ps1")

$ctx = Initialize-FairCrmDbContext
$allowRestore = $env:ALLOW_RESTORE
$targetDatabaseUrl = $env:TARGET_DATABASE_URL

Write-DevStep "Fair CRM restore job runner"
Write-Host "Repository root:      $($ctx.RepoRoot)"
Write-Host "Restore job id:       $RestoreJobId"
Write-Host "ALLOW_RESTORE:        $(if ($allowRestore) { $allowRestore } else { '(not set)' })"
Write-Host "TARGET_DATABASE_URL:  $(if ($targetDatabaseUrl) { $targetDatabaseUrl } else { '(not set)' })"

if ($allowRestore -notin @("1", "true", "TRUE", "yes", "YES")) {
    throw "Destructive restore blocked. Set ALLOW_RESTORE=true before running this script."
}
if (-not $targetDatabaseUrl) {
    throw "TARGET_DATABASE_URL is required. Set it explicitly to the database that should be overwritten."
}

Push-Location (Join-Path $ctx.RepoRoot "backend")
try {
    $args = @(
        "-m", "app.modules.system_admin.maintenance.run_restore_job",
        "--job-id", $RestoreJobId,
        "--database-url", $targetDatabaseUrl,
        "--allow-restore"
    )
    & python @args
    if ($LASTEXITCODE -ne 0) {
        throw "Restore job runner failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Restore job execution finished." -ForegroundColor Green
