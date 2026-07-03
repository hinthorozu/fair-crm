#Requires -Version 5.1
<#
.SYNOPSIS
  Validate, verify a clean working tree, and push the current branch to origin.

.DESCRIPTION
  One-command push workflow:
  1. Verify the working tree is clean
  2. Run project quality checks (compile, import, pytest)
  3. Push the current branch to origin
  4. Display the pushed branch and commit hash

.EXAMPLE
  .\scripts\dev\dev-push.ps1
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "dev-lib.ps1")

Write-DevStep "Fair CRM dev-push (validate + push)"
Write-Host "Repository root: $script:DevRepoRoot"

Write-DevStep "Verifying working tree is clean"
Assert-DevGitWorkingTreeClean
Write-Host "Working tree is clean."

Write-DevStep "Running project quality checks"
$qualityScript = Join-Path $script:DevRepoRoot "scripts\quality_check.py"
if (-not (Test-Path $qualityScript)) {
    throw "Quality check script not found: $qualityScript"
}

Push-Location $script:DevRepoRoot
try {
    & python $qualityScript
    if ($LASTEXITCODE -ne 0) {
        throw "Quality check failed. Fix issues before pushing."
    }
} finally {
    Pop-Location
}

$branch = Get-DevGitBranch
$commit = Get-DevGitCommit

Write-DevStep "Pushing branch '$branch' to origin"
Push-Location $script:DevRepoRoot
try {
    git push -u origin HEAD 2>&1 | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) {
        throw "git push failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "=== Push Complete ===" -ForegroundColor Green
Write-Host "Branch: $branch"
Write-Host "Commit: $commit"
