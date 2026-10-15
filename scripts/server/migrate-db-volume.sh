#!/usr/bin/env bash
#
# PostgreSQL verisini eski konteyner/volume'dan yenisine taşır:
#   kyrox-postgres-dev + fair-crm_kyrox_pg_data  ->  kyrox-db + kyrox-db-data
#
# Eski volume ve eski konteyner silinmez (konteyner durdurulmuş kalır); geri dönüş
# talimatı sonda yazdırılır. Tekrar çalıştırılırsa taşıma yapılmışsa bir şey yapmaz.
#
# Kullanım:
#   sudo bash /opt/kyrox/kyrox-fair-crm/scripts/server/migrate-db-volume.sh
#
# Ortam değişkenleri (isteğe bağlı):
#   SERVICES="kyrox-core fair-crm-backend fair-crm-mail-worker fair-stand"
#   OLD_CONTAINER=kyrox-postgres-dev  OLD_VOLUME=fair-crm_kyrox_pg_data
#   DUMP_ROOT=/var/backups/kyrox
#
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
COMPOSE_FILE="${REPO_DIR}/docker-compose.yml"

OLD_CONTAINER="${OLD_CONTAINER:-kyrox-postgres-dev}"
OLD_VOLUME="${OLD_VOLUME:-fair-crm_kyrox_pg_data}"
NEW_CONTAINER="${NEW_CONTAINER:-kyrox-db}"
NEW_VOLUME="${NEW_VOLUME:-kyrox-db-data}"
PG_USER="${PG_USER:-postgres}"
# Boş bırakılırsa (SERVICES="") hiçbir servis durdurulmaz.
SERVICES="${SERVICES-kyrox-core fair-crm-backend fair-crm-mail-worker fair-stand}"
DUMP_ROOT="${DUMP_ROOT:-/var/backups/kyrox}"
BACKUP_ENV="${BACKUP_ENV:-/etc/kyrox-backup.env}"

log() { echo "[$(date +%T)] $*"; }
die() { echo "[$(date +%T)] HATA: $*" >&2; exit 1; }
trap 'echo "[$(date +%T)] HATA: satır ${LINENO}: ${BASH_COMMAND}" >&2; print_rollback >&2' ERR

STOPPED_SERVICES=""

print_rollback() {
  cat <<EOF

Geri dönmek için (eski volume ve konteyner duruyor):
  docker stop ${NEW_CONTAINER} 2>/dev/null || true
  docker start ${OLD_CONTAINER}
  sed -i 's/\b${NEW_CONTAINER}\b/${OLD_CONTAINER}/' ${BACKUP_ENV}   # varsa
  systemctl start ${SERVICES}
Uygulamalar veritabanına localhost:5432 ile bağlandığı için başka ayar gerekmez.
EOF
}

# Veritabanı listesi ve her veritabanındaki tablo sayısı.
db_snapshot() {
  local container="$1" db
  for db in $(docker exec "$container" psql -U "$PG_USER" -d postgres -tAc \
      "SELECT datname FROM pg_database WHERE NOT datistemplate ORDER BY 1"); do
    printf '%s tablo=%s\n' "$db" "$(docker exec "$container" psql -U "$PG_USER" -d "$db" -tAc \
      "SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')")"
  done
}

wait_healthy() {
  local container="$1" i
  for i in $(seq 1 60); do
    if docker exec "$container" pg_isready -U "$PG_USER" -q 2>/dev/null; then
      return 0
    fi
    sleep 2
  done
  return 1
}

[[ "$(id -u)" -eq 0 ]] || die "root olarak çalıştırın"
command -v docker >/dev/null || die "docker yok"
grep -q "container_name: ${NEW_CONTAINER}" "$COMPOSE_FILE" && grep -q "name: ${NEW_VOLUME}" "$COMPOSE_FILE" \
  || die "${COMPOSE_FILE} yeni adları içermiyor; önce repoyu güncelleyin (git pull)"

container_exists() { docker container inspect "$1" >/dev/null 2>&1; }
volume_exists() { docker volume inspect "$1" >/dev/null 2>&1; }

if container_exists "$NEW_CONTAINER" && ! { container_exists "$OLD_CONTAINER" && [[ "$(docker inspect -f '{{.State.Running}}' "$OLD_CONTAINER")" == true ]]; }; then
  log "Taşıma zaten yapılmış: ${NEW_CONTAINER} var, ${OLD_CONTAINER} çalışmıyor. Bir şey yapılmadı."
  exit 0
fi
container_exists "$OLD_CONTAINER" || die "${OLD_CONTAINER} konteyneri yok"
volume_exists "$OLD_VOLUME" || die "${OLD_VOLUME} volume'u yok"
volume_exists "$NEW_VOLUME" && die "${NEW_VOLUME} zaten var; üzerine yazmamak için durduruldu"
[[ "$(docker inspect -f '{{.State.Running}}' "$OLD_CONTAINER")" == true ]] || die "${OLD_CONTAINER} çalışmıyor; önce başlatın"
IMAGE="$(docker inspect -f '{{.Config.Image}}' "$OLD_CONTAINER")"

log "1) Öncesi: veritabanları ve tablo sayıları"
BEFORE="$(db_snapshot "$OLD_CONTAINER")"
echo "$BEFORE" | sed 's/^/   /'

DUMP_DIR="${DUMP_ROOT}/db-migration-$(date +%Y%m%d-%H%M%S)"
log "2) Güvenlik dump'ı: ${DUMP_DIR}/pg_dumpall.sql.gz"
mkdir -p "$DUMP_DIR"; chmod 700 "$DUMP_DIR"
docker exec "$OLD_CONTAINER" pg_dumpall -U "$PG_USER" | gzip > "${DUMP_DIR}/pg_dumpall.sql.gz"
log "   $(du -h "${DUMP_DIR}/pg_dumpall.sql.gz" | cut -f1)"

log "3) Uygulama servisleri durduruluyor (kesinti başlar)"
T0=$(date +%s)
# Çalışanlar durdurmadan önce kaydedilir: bir servis durunca ona bağlı olanlar
# (ör. fair-crm-backend Requires=kyrox-core) da durur ve sonra yeniden başlatılmalıdır.
for svc in $SERVICES; do
  if systemctl is-active -q "$svc" 2>/dev/null; then
    STOPPED_SERVICES="${STOPPED_SERVICES} ${svc}"
  fi
done
if [[ -n "$STOPPED_SERVICES" ]]; then
  # shellcheck disable=SC2086
  systemctl stop $STOPPED_SERVICES
fi
log "   durdurulan:${STOPPED_SERVICES:- (yok)}"

log "4) ${OLD_CONTAINER} durduruluyor (silinmiyor)"
docker stop "$OLD_CONTAINER" >/dev/null

log "5) Veri ${OLD_VOLUME} -> ${NEW_VOLUME} kopyalanıyor"
docker volume create "$NEW_VOLUME" >/dev/null
docker run --rm -v "${OLD_VOLUME}:/from:ro" -v "${NEW_VOLUME}:/to" "$IMAGE" sh -c 'cp -a /from/. /to/'
SIZES="$(docker run --rm -v "${OLD_VOLUME}:/from:ro" -v "${NEW_VOLUME}:/to:ro" "$IMAGE" sh -c \
  'echo "$(du -s /from | cut -f1) $(find /from | wc -l) $(du -s /to | cut -f1) $(find /to | wc -l)"')"
read -r from_kb from_n to_kb to_n <<<"$SIZES"
log "   eski: ${from_kb} KB / ${from_n} dosya   yeni: ${to_kb} KB / ${to_n} dosya"
[[ "$from_kb" == "$to_kb" && "$from_n" == "$to_n" ]] || die "kopya eşleşmiyor"

log "6) ${NEW_CONTAINER} başlatılıyor"
(cd "$REPO_DIR" && docker compose up -d postgres)
wait_healthy "$NEW_CONTAINER" || die "${NEW_CONTAINER} sağlıklı açılmadı"

log "7) Sonrası: veritabanları ve tablo sayıları"
AFTER="$(db_snapshot "$NEW_CONTAINER")"
echo "$AFTER" | sed 's/^/   /'
[[ "$BEFORE" == "$AFTER" ]] || die "öncesi ve sonrası farklı"

if [[ -f "$BACKUP_ENV" ]] && grep -q "\b${OLD_CONTAINER}\b" "$BACKUP_ENV"; then
  sed -i "s/\b${OLD_CONTAINER}\b/${NEW_CONTAINER}/" "$BACKUP_ENV"
  log "8) Yedek ayarı güncellendi: ${BACKUP_ENV}"
fi

if [[ -n "$STOPPED_SERVICES" ]]; then
  log "9) Servisler başlatılıyor:${STOPPED_SERVICES}"
  # shellcheck disable=SC2086
  systemctl start $STOPPED_SERVICES
fi
log "Kesinti: $(( $(date +%s) - T0 )) sn"

log "Tamam. Eski volume (${OLD_VOLUME}) ve durdurulmuş ${OLD_CONTAINER} yerinde duruyor."
log "Her şey çalışıyorsa sonra elle silinebilir: docker rm ${OLD_CONTAINER}; docker volume rm ${OLD_VOLUME}"
trap - ERR
print_rollback
