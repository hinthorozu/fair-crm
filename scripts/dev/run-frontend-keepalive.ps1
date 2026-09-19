#Requires -Version 5.1
# Detached Fair CRM Vite loop so localhost:5173 stays up after the chat terminal exits.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"
$frontendDir = Join-Path (Split-Path -Parent $PSScriptRoot) "frontend"
Set-Location $frontendDir
while ($true) {
    & npm.cmd run dev -- --host --port 5173 --strictPort
    Start-Sleep -Seconds 2
}
