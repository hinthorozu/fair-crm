# One-time fix: allow legacy SQL clients (Navicat 11, old pgAdmin) to connect.
# PostgreSQL 13+ defaults to SCRAM-SHA-256 (auth method 10), which Navicat 11 does not support.
# Switches dev Docker Postgres to MD5 password auth. Safe for local dev only.

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

Write-Host "Configuring PostgreSQL MD5 auth for legacy clients (container: $ContainerName)..." -ForegroundColor Cyan
Assert-DockerContainerRunning -Name $ContainerName

Write-Host "  -> password_encryption = md5"
docker exec $ContainerName psql -U postgres -d postgres -c "ALTER SYSTEM SET password_encryption = 'md5';" | Out-Null

Write-Host "  -> pg_hba.conf: scram-sha-256 -> md5"
docker exec $ContainerName sh -c @"
sed -i 's/scram-sha-256/md5/g' /var/lib/postgresql/data/pg_hba.conf
grep -q 'host all all all md5' /var/lib/postgresql/data/pg_hba.conf || echo 'host all all all md5' >> /var/lib/postgresql/data/pg_hba.conf
"@ | Out-Null

Write-Host "  -> restarting container"
docker restart $ContainerName | Out-Null
Start-Sleep -Seconds 3

Assert-DockerContainerRunning -Name $ContainerName

Write-Host "  -> re-hash postgres user password with MD5"
docker exec $ContainerName psql -U postgres -d postgres -c "ALTER USER postgres WITH PASSWORD '$Password';" | Out-Null

Write-Host ""
Write-Host "Done. Navicat connection settings:" -ForegroundColor Green
Write-Host "  Host: localhost | Port: 5432 | User: postgres | Database: fair_crm"
Write-Host "  Test Connection in Navicat should succeed now."
