#Requires -Version 5.1
<#
.SYNOPSIS
  List Fair CRM PostgreSQL backup files in backups/.

.EXAMPLE
  .\scripts\dev\list-backups.ps1
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "db-backup-lib.ps1")

$ctx = Initialize-FairCrmDbContext
$backupsDir = $ctx.BackupsDir

Write-DevStep "Fair CRM database backups"
Write-Host "Directory: $backupsDir"
Write-Host "Database:  $($ctx.Connection.Database) @ $($ctx.Connection.Host):$($ctx.Connection.Port)"
Write-Host ""

if (-not (Test-Path $backupsDir)) {
    Write-Host "No backups directory yet. Run .\scripts\dev\backup-db.ps1 first." -ForegroundColor Yellow
    exit 0
}

$files = @(Get-ChildItem -Path $backupsDir -Filter "*.dump" -File | Sort-Object LastWriteTime -Descending)
if (@($files).Count -eq 0) {
    Write-Host "No .dump backup files found." -ForegroundColor Yellow
    exit 0
}

$rows = foreach ($file in $files) {
    [pscustomobject]@{
        Name       = $file.Name
        Modified   = $file.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
        Size       = (Format-FileSize $file.Length)
        SizeBytes  = $file.Length
        FullPath   = $file.FullName
    }
}

$rows | Format-Table Name, Modified, Size -AutoSize
Write-Host "Total backups: $(@($rows).Count)"
Write-Host ""
Write-Host "Restore example:"
Write-Host "  .\scripts\dev\restore-db.ps1 .\backups\$($rows[0].Name)" -ForegroundColor Yellow
