# Restore PostgreSQL default SCRAM-SHA-256 auth after legacy MD5 workaround (Navicat 11).
# Run after upgrading to Navicat 16+ / modern pgAdmin.

param(
    [string]$ContainerName = "kyrox-postgres-dev",
    [string]$Password = "postgres"
)

$ErrorActionPreference = "Stop"

function Assert-DockerContainerRunning {
    param([string]$Name)
    $running = docker ps --format "{{.Names}}" | Where-Object { $_ -eq $Name }
    if (-not $running) {
        throw "Container '$Name' is not running. Start it first: docker compose up -d"
    }
}

Write-Host "Restoring PostgreSQL SCRAM-SHA-256 auth (container: $ContainerName)..." -ForegroundColor Cyan
Assert-DockerContainerRunning -Name $ContainerName

Write-Host "  -> password_encryption = scram-sha-256"
docker exec $ContainerName psql -U postgres -d postgres -c "ALTER SYSTEM SET password_encryption = 'scram-sha-256';" | Out-Null

Write-Host "  -> pg_hba.conf: md5 -> scram-sha-256"
docker exec $ContainerName sh -c @"
sed -i 's/ md5\$/ scram-sha-256/g' /var/lib/postgresql/data/pg_hba.conf
"@ | Out-Null

Write-Host "  -> restarting container"
docker restart $ContainerName | Out-Null
Start-Sleep -Seconds 3

Assert-DockerContainerRunning -Name $ContainerName

Write-Host "  -> re-hash postgres user password with SCRAM"
docker exec $ContainerName psql -U postgres -d postgres -c "ALTER USER postgres WITH PASSWORD '$Password';" | Out-Null

Write-Host ""
Write-Host "Done. Default PostgreSQL 16 auth restored (SCRAM-SHA-256)." -ForegroundColor Green
Write-Host "Navicat 17+ connection: localhost:5432 / postgres / fair_crm"
