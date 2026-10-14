#!/usr/bin/env bash
#
# Kyrox günlük yedeğini bir Linux sunucuya kurar: rclone, Google Drive bağlantısı,
# /etc/kyrox-backup.env, /usr/local/sbin/kyrox-backup, cron ve logrotate.
# Tekrar çalıştırılabilir; var olan ayar dosyasının ve Drive bağlantısının üzerine yazmaz.
#
# Kullanım:
#   sudo bash /opt/fair-crm/scripts/server/backup/install-backup.sh
#
# Seçenekler:
#   --time 03:30              Her gün çalışma saati (varsayılan 03:30)
#   --remote-name gdrive      rclone bağlantı adı (varsayılan gdrive)
#   --drive-folder NAME       Drive'daki kök klasör (varsayılan Kyrox-Yedek)
#   --skip-drive              Drive bağlantısı kurma; yalnız yerel yedek
#   --no-test                 Kurulum sonunda deneme yedeği alma
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RUN_TIME="03:30"
REMOTE_NAME="gdrive"
DRIVE_FOLDER="Kyrox-Yedek"
SKIP_DRIVE=0
RUN_TEST=1

CONFIG_FILE="/etc/kyrox-backup.env"
BIN_PATH="/usr/local/sbin/kyrox-backup"
CRON_FILE="/etc/cron.d/kyrox-backup"
LOGROTATE_FILE="/etc/logrotate.d/kyrox-backup"
LOG_FILE="/var/log/kyrox-backup.log"
RCLONE_CONFIG_PATH="/root/.config/rclone/rclone.conf"

log() {
  echo "[install-backup] $*"
}

die() {
  echo "[install-backup] HATA: $*" >&2
  exit 1
}

usage() {
  sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --time) RUN_TIME="${2:-}"; shift 2 ;;
    --remote-name) REMOTE_NAME="${2:-}"; shift 2 ;;
    --drive-folder) DRIVE_FOLDER="${2:-}"; shift 2 ;;
    --skip-drive) SKIP_DRIVE=1; shift ;;
    --no-test) RUN_TEST=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Bilinmeyen seçenek: $1 (--help)" ;;
  esac
done

[[ "$(uname -s)" == "Linux" ]] || die "Yalnız Linux sunucular desteklenir"
[[ "$(id -u)" -eq 0 ]] || die "root olarak çalıştırın (sudo bash $0)"
[[ "$RUN_TIME" =~ ^([01][0-9]|2[0-3]):([0-5][0-9])$ ]] || die "--time SS:DD biçiminde olmalı, ör. 03:30"
CRON_HOUR="$((10#${BASH_REMATCH[1]}))"
CRON_MINUTE="$((10#${BASH_REMATCH[2]}))"
[[ "$REMOTE_NAME" =~ ^[A-Za-z0-9_-]+$ ]] || die "--remote-name yalnız harf, rakam, - ve _ içerebilir"
[[ -n "$DRIVE_FOLDER" && "$DRIVE_FOLDER" != /* ]] || die "--drive-folder boş olamaz ve / ile başlayamaz"
[[ -f "${SCRIPT_DIR}/kyrox-backup.sh" ]] || die "${SCRIPT_DIR}/kyrox-backup.sh bulunamadı"

HOST_NAME="$(hostname -f 2>/dev/null || hostname)"

# 1) Paketler
missing_packages=()
command -v rclone >/dev/null 2>&1 || missing_packages+=(rclone)
command -v flock >/dev/null 2>&1 || missing_packages+=(util-linux)
command -v gzip >/dev/null 2>&1 || missing_packages+=(gzip)
if (( ${#missing_packages[@]} > 0 )); then
  log "Paketler kuruluyor: ${missing_packages[*]}"
  command -v apt-get >/dev/null 2>&1 || die "apt-get yok; şu paketleri elle kurun: ${missing_packages[*]}"
  DEBIAN_FRONTEND=noninteractive apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${missing_packages[@]}"
fi
log "rclone: $(rclone version 2>/dev/null | head -1)"

# 2) Yedeklenecekleri bul
discovered_apps=()
for dir in /opt/*/; do
  dir="${dir%/}"
  [[ -d "${dir}/.git" ]] && discovered_apps+=("$dir")
done
discovered_pg=()
if command -v docker >/dev/null 2>&1; then
  while read -r name image; do
    [[ "$image" == postgres* || "$image" == */postgres* ]] && discovered_pg+=("$name")
  done < <(docker ps --format '{{.Names}} {{.Image}}')
fi
log "Bulunan projeler: ${discovered_apps[*]:-(yok)}"
log "Bulunan PostgreSQL konteynerleri: ${discovered_pg[*]:-(yok)}"

# 3) Ayar dosyası
if [[ -f "$CONFIG_FILE" ]]; then
  log "${CONFIG_FILE} zaten var, değiştirilmedi"
else
  remote_value=""
  if (( SKIP_DRIVE == 0 )); then
    remote_value="${REMOTE_NAME}:${DRIVE_FOLDER}/${HOST_NAME}"
  fi
  cat > "$CONFIG_FILE" <<EOF
# Kyrox günlük yedek ayarları. Değiştirdikten sonra ek işlem gerekmez;
# bir sonraki çalıştırmada geçerli olur. Elle deneme: sudo kyrox-backup

BACKUP_ROOT="/var/backups/kyrox"

# Yedeklenecek proje klasörleri (boşlukla ayrılmış).
APP_DIRS="${discovered_apps[*]:-}"

# Her derinlikte atlanan, yeniden kurulabilen klasörler.
EXCLUDE_NAMES=".venv node_modules dist"

# Atlanacak belirli yollar, /opt'a göre. fair-crm/backups uygulamanın kendi dump'larıdır;
# veritabanları zaten aşağıda ayrıca yedeklenir.
EXCLUDE_PATHS="fair-crm/backups"

# Dump alınacak PostgreSQL Docker konteynerleri.
PG_CONTAINERS="${discovered_pg[*]:-}"
PG_USER="postgres"

# Google Drive hedefi. Boş bırakılırsa yalnız yerel yedek alınır.
RCLONE_REMOTE="${remote_value}"
RCLONE_CONFIG="${RCLONE_CONFIG_PATH}"

LOCAL_RETENTION_DAYS=3
REMOTE_RETENTION_DAYS=14
MIN_FREE_MB=2048
EOF
  chmod 600 "$CONFIG_FILE"
  log "${CONFIG_FILE} oluşturuldu"
fi

# 4) Yedek betiği
install -m 750 "${SCRIPT_DIR}/kyrox-backup.sh" "$BIN_PATH"
log "${BIN_PATH} kuruldu"

# 5) Google Drive bağlantısı
if (( SKIP_DRIVE == 0 )); then
  export RCLONE_CONFIG="$RCLONE_CONFIG_PATH"
  mkdir -p "$(dirname "$RCLONE_CONFIG_PATH")"
  if rclone listremotes | grep -qx "${REMOTE_NAME}:"; then
    log "rclone bağlantısı '${REMOTE_NAME}' zaten var, değiştirilmedi"
  else
    [[ -r /dev/tty ]] || die "Drive bağlantısı için etkileşimli terminal gerekir; --skip-drive ile kurup sonra tekrar çalıştırın"
    cat <<'EOF'

=== Google Drive bağlantısı (kurulum başına bir kez) ===
Tarayıcısı olan bilgisayarınızda:
  1. rclone kurun.  Windows: winget install Rclone.Rclone   macOS: brew install rclone
  2. Şu komutu çalıştırın:  rclone authorize "drive"
  3. Açılan sayfada yedeklerin gideceği Google hesabıyla giriş yapıp izin verin.
  4. Terminalde çıkan {"access_token": ... } ile başlayan tek satırı kopyalayın.

EOF
    token=""
    read -r -p "Token satırını buraya yapıştırın: " token < /dev/tty
    [[ "$token" == \{*\} ]] || die "Token { ile başlayıp } ile bitmeli; kurulumu tekrar çalıştırın"
    rclone config create "$REMOTE_NAME" drive scope=drive token="$token" --non-interactive >/dev/null
    chmod 600 "$RCLONE_CONFIG_PATH"
    log "rclone bağlantısı '${REMOTE_NAME}' oluşturuldu"
  fi
  rclone mkdir "${REMOTE_NAME}:${DRIVE_FOLDER}/${HOST_NAME}"
  rclone lsd "${REMOTE_NAME}:${DRIVE_FOLDER}" >/dev/null
  log "Drive erişimi doğrulandı: ${REMOTE_NAME}:${DRIVE_FOLDER}/${HOST_NAME}"
else
  log "--skip-drive: Drive bağlantısı kurulmadı"
fi

# 6) Cron ve log döndürme
cat > "$CRON_FILE" <<EOF
# Kyrox günlük yedek (install-backup.sh tarafından oluşturuldu)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
${CRON_MINUTE} ${CRON_HOUR} * * * root ${BIN_PATH} >> ${LOG_FILE} 2>&1
EOF
chmod 644 "$CRON_FILE"
log "Cron kuruldu: her gün ${RUN_TIME} (${CRON_FILE})"

cat > "$LOGROTATE_FILE" <<EOF
${LOG_FILE} {
  weekly
  rotate 8
  compress
  missingok
  notifempty
}
EOF
log "Log: ${LOG_FILE} (haftalık döndürülür)"

# 7) Deneme yedeği
if (( RUN_TEST == 1 )); then
  log "Deneme yedeği alınıyor..."
  "$BIN_PATH" 2>&1 | tee -a "$LOG_FILE"
  log "Deneme yedeği tamamlandı"
else
  log "--no-test: deneme yedeği atlandı. Elle denemek için: sudo kyrox-backup"
fi

log "Kurulum bitti. Ayarlar: ${CONFIG_FILE}"
