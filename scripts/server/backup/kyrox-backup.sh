#!/usr/bin/env bash
#
# Kyrox günlük yedek: proje dosyaları + PostgreSQL + sunucu ayarları.
# Yedek önce sunucuya (BACKUP_ROOT) yazılır, sonra rclone ile Google Drive'a yüklenir.
#
# Kurulum (cron, rclone, ayar dosyası):
#   sudo bash /opt/kyrox/fair-crm/scripts/server/backup/install-backup.sh
#
# Elle çalıştırma:
#   sudo kyrox-backup
#
# Ayarlar: /etc/kyrox-backup.env (install-backup.sh oluşturur). Her değer ortam
# değişkeniyle de verilebilir.
#
set -Eeuo pipefail

CONFIG_FILE="${KYROX_BACKUP_CONFIG:-/etc/kyrox-backup.env}"
if [[ -r "$CONFIG_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
fi

BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/kyrox}"
# Yedeklenecek proje klasörleri (boşlukla ayrılmış mutlak yollar).
APP_DIRS="${APP_DIRS:-}"
# Her derinlikte atlanacak, yeniden kurulabilen klasör adları.
EXCLUDE_NAMES="${EXCLUDE_NAMES:-.venv node_modules dist}"
# Atlanacak belirli yollar, proje klasörünün üst dizinine göre (ör. fair-crm/backups).
EXCLUDE_PATHS="${EXCLUDE_PATHS:-}"
# Dump alınacak PostgreSQL Docker konteynerleri.
PG_CONTAINERS="${PG_CONTAINERS:-}"
PG_USER="${PG_USER:-postgres}"
SYSTEM_PATHS="${SYSTEM_PATHS:-/etc/nginx /etc/letsencrypt /etc/systemd/system /etc/cron.d /etc/fair-crm /etc/kyrox-backup.env}"
# rclone hedefi, ör. gdrive:Kyrox-Yedek/srv.example.com. Boşsa yalnız yerel yedek alınır.
RCLONE_REMOTE="${RCLONE_REMOTE:-}"
RCLONE_CONFIG="${RCLONE_CONFIG:-/root/.config/rclone/rclone.conf}"
LOCAL_RETENTION_DAYS="${LOCAL_RETENTION_DAYS:-3}"
REMOTE_RETENTION_DAYS="${REMOTE_RETENTION_DAYS:-14}"
MIN_FREE_MB="${MIN_FREE_MB:-2048}"
export RCLONE_CONFIG

log() {
  printf '%s [kyrox-backup] %s\n' "$(date '+%F %T')" "$*"
}

die() {
  log "HATA: $*"
  exit 1
}

trap 'log "HATA: satır ${LINENO} başarısız oldu: ${BASH_COMMAND}"' ERR

[[ "$(id -u)" -eq 0 ]] || die "root olarak çalıştırın (sudo kyrox-backup)"
[[ "$LOCAL_RETENTION_DAYS" =~ ^[1-9][0-9]*$ ]] || die "LOCAL_RETENTION_DAYS pozitif tam sayı olmalı"
[[ "$REMOTE_RETENTION_DAYS" =~ ^[1-9][0-9]*$ ]] || die "REMOTE_RETENTION_DAYS pozitif tam sayı olmalı"
if [[ -n "$RCLONE_REMOTE" && ! "$RCLONE_REMOTE" =~ ^[A-Za-z0-9_-]+:.+ ]]; then
  # Saklama temizliği bu hedefte çalışır; Drive kökünü hedef almasın.
  die "RCLONE_REMOTE bir klasör içermeli (ör. gdrive:Kyrox-Yedek/sunucu), şu an: ${RCLONE_REMOTE}"
fi

exec 9>/run/kyrox-backup.lock
flock -n 9 || die "Başka bir yedek zaten çalışıyor"

mkdir -p "$BACKUP_ROOT"
chmod 700 "$BACKUP_ROOT"

free_mb="$(df -Pm "$BACKUP_ROOT" | awk 'NR==2 {print $4}')"
(( free_mb >= MIN_FREE_MB )) || die "${BACKUP_ROOT} üzerinde yeterli yer yok: ${free_mb} MB boş, en az ${MIN_FREE_MB} MB gerekli"

STAMP="$(date +%Y-%m-%d_%H%M%S)"
DEST="${BACKUP_ROOT}/${STAMP}"
PARTIAL="${DEST}.partial"
[[ ! -e "$DEST" ]] || die "${DEST} zaten var"

cleanup_partial() {
  if [[ -d "$PARTIAL" ]]; then
    rm -rf -- "$PARTIAL"
  fi
}
trap cleanup_partial EXIT

mkdir -p "$PARTIAL/app" "$PARTIAL/db" "$PARTIAL/system"
chmod 700 "$PARTIAL"
log "Yedek başladı: ${DEST}"

# tar 1 ile çıkarsa (okunurken değişen dosya) uyarı sayılır; 2 ve üstü hatadır.
run_tar() {
  local rc=0
  tar --warning=no-file-changed "$@" || rc=$?
  (( rc <= 1 )) || return "$rc"
}

# 1) Proje dosyaları
tar_excludes=()
for name in $EXCLUDE_NAMES; do
  tar_excludes+=("--exclude=${name}")
done
for path in $EXCLUDE_PATHS; do
  tar_excludes+=("--exclude=${path}")
done

for dir in $APP_DIRS; do
  dir="${dir%/}"
  if [[ ! -d "$dir" ]]; then
    log "UYARI: ${dir} bulunamadı, atlandı"
    continue
  fi
  name="$(basename "$dir")"
  run_tar -C "$(dirname "$dir")" --numeric-owner -czpf "$PARTIAL/app/${name}.tar.gz" \
    "${tar_excludes[@]}" "$name"
  log "Proje: ${name} ($(du -h "$PARTIAL/app/${name}.tar.gz" | cut -f1))"
done

# 2) Veritabanları
for container in $PG_CONTAINERS; do
  docker exec "$container" pg_dumpall -U "$PG_USER" --globals-only > "$PARTIAL/db/${container}__globals.sql"
  databases="$(docker exec "$container" psql -U "$PG_USER" -d postgres -tAc \
    "SELECT datname FROM pg_database WHERE NOT datistemplate AND datname <> 'postgres' ORDER BY 1")"
  for db in $databases; do
    docker exec "$container" pg_dump -U "$PG_USER" -Fc "$db" > "$PARTIAL/db/${container}__${db}.dump"
    log "Veritabanı: ${container}/${db} ($(du -h "$PARTIAL/db/${container}__${db}.dump" | cut -f1))"
  done
done

# 3) Sunucu ayarları
system_paths=()
for path in $SYSTEM_PATHS; do
  if [[ -e "$path" ]]; then
    system_paths+=("${path#/}")
  fi
done
if (( ${#system_paths[@]} > 0 )); then
  run_tar -C / --numeric-owner -czpf "$PARTIAL/system/system-config.tar.gz" "${system_paths[@]}"
fi
crontab -l > "$PARTIAL/system/root-crontab.txt" 2>/dev/null || echo "(boş)" > "$PARTIAL/system/root-crontab.txt"
if command -v dpkg >/dev/null 2>&1; then
  dpkg --get-selections > "$PARTIAL/system/packages.txt"
fi
if command -v docker >/dev/null 2>&1; then
  docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' > "$PARTIAL/system/docker-containers.txt"
  docker volume ls > "$PARTIAL/system/docker-volumes.txt"
fi
systemctl list-units --type=service --state=running --no-pager --no-legend > "$PARTIAL/system/running-services.txt" 2>/dev/null || true

{
  echo "host=$(hostname -f 2>/dev/null || hostname)"
  echo "created=$(date -Iseconds)"
  echo "app_dirs=${APP_DIRS}"
  echo "exclude_names=${EXCLUDE_NAMES}"
  echo "exclude_paths=${EXCLUDE_PATHS}"
  echo "pg_containers=${PG_CONTAINERS}"
} > "$PARTIAL/MANIFEST.txt"

(cd "$PARTIAL" && find . -type f ! -name SHA256SUMS -exec sha256sum {} + > SHA256SUMS)
chmod -R go-rwx "$PARTIAL"
mv "$PARTIAL" "$DEST"
log "Yerel yedek hazır: ${DEST} ($(du -sh "$DEST" | cut -f1))"

# 4) Google Drive
if [[ -n "$RCLONE_REMOTE" ]]; then
  remote_dir="${RCLONE_REMOTE%/}/${STAMP}"
  log "Drive'a yükleniyor: ${remote_dir}"
  rclone copy "$DEST" "$remote_dir" --transfers 2 --retries 5 --low-level-retries 10
  rclone check "$DEST" "$remote_dir" --one-way
  log "Drive yüklemesi doğrulandı"
  # Çöp kutusu Drive kotasından yer; eski yedekler doğrudan silinir.
  rclone delete "${RCLONE_REMOTE%/}" --min-age "${REMOTE_RETENTION_DAYS}d" --drive-use-trash=false
  rclone rmdirs "${RCLONE_REMOTE%/}" --leave-root
  log "Drive'da ${REMOTE_RETENTION_DAYS} günden eski yedekler temizlendi"
else
  log "RCLONE_REMOTE boş; Drive'a yükleme atlandı"
fi

# 5) Yerel saklama
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name '20??-??-??_??????' \
  -mmin +$(( LOCAL_RETENTION_DAYS * 1440 )) -exec rm -rf -- {} +
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name '*.partial' -mmin +1440 -exec rm -rf -- {} +
log "Yerelde ${LOCAL_RETENTION_DAYS} günden eski yedekler temizlendi"

log "Yedek tamamlandı"
