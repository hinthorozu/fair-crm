#!/usr/bin/env bash
#
# Kyrox günlük yedek kurulum sihirbazı.
# Adım adım sorar, cevaplara göre /etc/kyrox-backup.env dosyasını oluşturur;
# yedek betiğini, cron'u ve logrotate'i kurar, Google Drive bağlantısını yapar.
# Tekrar çalıştırılabilir: önceki cevaplar varsayılan olarak gelir.
#
# Kullanım:
#   sudo bash /opt/kyrox/kyrox-fair-crm/scripts/server/backup/install-backup.sh
#
# Seçenekler:
#   --yes      Soru sormadan mevcut/varsayılan ayarlarla kur (Drive bağlantısı
#              önceden kurulmuş olmalı, yoksa yalnız yerel yedek kurulur)
#   -h, --help Bu yardımı göster
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CONFIG_FILE="${KYROX_BACKUP_CONFIG:-/etc/kyrox-backup.env}"
BIN_PATH="${KYROX_BACKUP_BIN:-/usr/local/sbin/kyrox-backup}"
CRON_FILE="${KYROX_BACKUP_CRON:-/etc/cron.d/kyrox-backup}"
LOGROTATE_FILE="${KYROX_BACKUP_LOGROTATE:-/etc/logrotate.d/kyrox-backup}"
LOG_FILE="${KYROX_BACKUP_LOG:-/var/log/kyrox-backup.log}"
RCLONE_CONFIG_PATH="${RCLONE_CONFIG:-/root/.config/rclone/rclone.conf}"
# Sorular bu kaynaktan okunur; testte /dev/stdin verilebilir.
PROMPT_INPUT="${PROMPT_INPUT:-/dev/tty}"

ASSUME_YES=0
TOTAL_STEPS=7

log() {
  echo "[kurulum] $*"
}

die() {
  echo "[kurulum] HATA: $*" >&2
  exit 1
}

usage() {
  sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) ASSUME_YES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Bilinmeyen seçenek: $1 (--help)" ;;
  esac
done

[[ "$(uname -s)" == "Linux" ]] || die "Yalnız Linux sunucular desteklenir"
[[ "$(id -u)" -eq 0 ]] || die "root olarak çalıştırın: sudo bash $0"
[[ -f "${SCRIPT_DIR}/kyrox-backup.sh" ]] || die "${SCRIPT_DIR}/kyrox-backup.sh bulunamadı"
if (( ASSUME_YES == 0 )) && ! { : < "$PROMPT_INPUT"; } 2>/dev/null; then
  die "Soru sorulabilecek bir terminal yok. ssh ile bağlanırken -t kullanın ya da --yes ile çalıştırın"
fi

step_title() {
  echo
  echo "────────────────────────────────────────────────────────────"
  echo " ADIM $1/${TOTAL_STEPS}: $2"
  echo "────────────────────────────────────────────────────────────"
}

# ask "Soru" "varsayılan" -> cevap (Enter = varsayılan)
ask() {
  local label="$1" current="$2" answer=""
  if (( ASSUME_YES == 1 )); then
    printf '%s' "$current"
    return 0
  fi
  read -r -p "${label} [${current}]: " answer < "$PROMPT_INPUT"
  printf '%s' "${answer:-$current}"
}

# ask_yes_no "Soru" E|H -> 0 (evet) / 1 (hayır)
ask_yes_no() {
  local label="$1" default="$2" answer="" hint
  if [[ "$default" == "E" ]]; then hint="E/h"; else hint="e/H"; fi
  if (( ASSUME_YES == 1 )); then
    [[ "$default" == "E" ]]
    return
  fi
  while true; do
    read -r -p "${label} [${hint}]: " answer < "$PROMPT_INPUT"
    answer="${answer:-$default}"
    case "${answer,,}" in
      e|evet|y|yes) return 0 ;;
      h|hayır|hayir|n|no) return 1 ;;
      *) echo "  Lütfen e (evet) ya da h (hayır) yazın." ;;
    esac
  done
}

ask_number() {
  local label="$1" current="$2" value
  while true; do
    value="$(ask "$label" "$current")"
    if [[ "$value" =~ ^[1-9][0-9]*$ ]]; then
      printf '%s' "$value"
      return 0
    fi
    echo "  Pozitif bir sayı girin, ör. ${current}." >&2
    (( ASSUME_YES == 0 )) || die "${label}: geçersiz değer ${value}"
  done
}

HOST_NAME="$(hostname -f 2>/dev/null || hostname)"

# Önceki kurulumun cevapları varsayılan olur.
APP_DIRS=""
EXCLUDE_NAMES=".venv node_modules dist"
EXCLUDE_PATHS="kyrox-fair-crm/backups fair-crm/backups"
PG_CONTAINERS=""
MYSQL_CONTAINERS=""
VOLUMES=""
PG_USER="postgres"
RCLONE_REMOTE=""
LOCAL_RETENTION_DAYS=3
REMOTE_RETENTION_DAYS=14
MIN_FREE_MB=2048
RUN_TIME="03:30"
BACKUP_ROOT="/var/backups/kyrox"
HAD_CONFIG=0
if [[ -r "$CONFIG_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
  HAD_CONFIG=1
fi
if [[ -r "$CRON_FILE" ]]; then
  cron_line="$(grep -E '^[0-9]+ [0-9]+ ' "$CRON_FILE" | head -1 || true)"
  if [[ "$cron_line" =~ ^([0-9]+)\ ([0-9]+)\  ]]; then
    printf -v RUN_TIME '%02d:%02d' "${BASH_REMATCH[2]}" "${BASH_REMATCH[1]}"
  fi
fi

echo
echo "Kyrox günlük yedek kurulumu"
echo "Her soruda köşeli parantezdeki değer varsayılandır; kabul etmek için Enter'a basın."
if (( HAD_CONFIG == 1 )); then
  echo "Önceki kurulum bulundu (${CONFIG_FILE}); önceki cevaplar varsayılan olarak geliyor."
fi

# ADIM 1: projeler
step_title 1 "Yedeklenecek proje klasörleri"
KYROX_ROOT="${KYROX_ROOT:-/opt/kyrox}"
discovered_apps=()
# Projeler ${KYROX_ROOT} altında; eski düzendeki sunucular için /opt de taranır.
for dir in "${KYROX_ROOT}"/*/ /opt/*/; do
  dir="${dir%/}"
  [[ -d "${dir}/.git" && ! -L "$dir" ]] && discovered_apps+=("$dir")
done
echo "Bulunan git projeleri (${KYROX_ROOT} ve /opt): ${discovered_apps[*]:-(yok)}"
echo "Klasörleri boşlukla ayırarak yazın. .venv, node_modules ve dist her zaman atlanır."
# Öneri: önceki cevaptan hâlâ var olan klasörler + sonradan eklenen yeni projeler
# (tekrarsız, sıralı). Taşınıp artık olmayan klasörler önerilmez.
existing_apps=()
for dir in $APP_DIRS; do
  [[ -d "$dir" ]] && existing_apps+=("${dir%/}")
done
new_apps=()
if [[ -n "$APP_DIRS" ]]; then
  for dir in "${discovered_apps[@]}"; do
    [[ " ${existing_apps[*]} " == *" ${dir} "* ]] || new_apps+=("$dir")
  done
fi
default_apps="$(printf '%s\n' "${existing_apps[@]}" "${discovered_apps[@]}" | sed '/^$/d' | sort -u | paste -sd' ' -)"
if (( ${#new_apps[@]} > 0 )); then
  echo "Önceki kurulumdan sonra eklenen yeni projeler (öneriye katıldı): ${new_apps[*]}"
fi
APP_DIRS="$(ask "Proje klasörleri" "$default_apps")"
for dir in $APP_DIRS; do
  [[ -d "$dir" ]] || echo "  UYARI: ${dir} şu an yok; yedek alınırken atlanır."
done

# Önceki cevaptaki adlardan hâlâ var olanlar; hiçbiri yoksa (ör. konteyner yeniden adlandırıldıysa) bulunanlar.
onceki_ya_da_bulunan() {
  local onceki="$1" bulunan="$2" tur="$3" ad var=()
  for ad in $onceki; do
    docker "$tur" inspect "$ad" >/dev/null 2>&1 && var+=("$ad")
  done
  if (( ${#var[@]} > 0 )); then printf '%s' "${var[*]}"; else printf '%s' "$bulunan"; fi
}

# ADIM 2: veritabanları ve Docker volume'ları
step_title 2 "Yedeklenecek veritabanları ve Docker volume'ları"
discovered_pg=()
discovered_mysql=()
discovered_vol=()
if command -v docker >/dev/null 2>&1; then
  while read -r name image; do
    case "$image" in
      postgres*|*/postgres*) discovered_pg+=("$name") ;;
      mariadb*|*/mariadb*|mysql*|*/mysql*) discovered_mysql+=("$name") ;;
      wordpress*|*/wordpress*)
        # WordPress dosyaları ve yüklenen görseller: konteynere bağlı adlandırılmış volume'lar.
        while read -r vol; do
          [[ -n "$vol" ]] && discovered_vol+=("$vol")
        done < <(docker inspect -f '{{range .Mounts}}{{if eq .Type "volume"}}{{.Name}}{{"\n"}}{{end}}{{end}}' "$name")
        ;;
    esac
  done < <(docker ps --format '{{.Names}} {{.Image}}')
fi
echo "Çalışan PostgreSQL konteynerleri: ${discovered_pg[*]:-(yok)}"
echo "Çalışan MariaDB/MySQL konteynerleri: ${discovered_mysql[*]:-(yok)}"
echo "WordPress volume'ları: ${discovered_vol[*]:-(yok)}"
echo "Her konteynerdeki bütün veritabanları yedeklenir. Olmayanı boş bırakın."
PG_CONTAINERS="$(ask "PostgreSQL konteynerleri" "$(onceki_ya_da_bulunan "$PG_CONTAINERS" "${discovered_pg[*]:-}" container)")"
MYSQL_CONTAINERS="$(ask "MariaDB/MySQL konteynerleri" "$(onceki_ya_da_bulunan "${MYSQL_CONTAINERS:-}" "${discovered_mysql[*]:-}" container)")"
VOLUMES="$(ask "Arşivlenecek Docker volume'ları" "$(onceki_ya_da_bulunan "${VOLUMES:-}" "${discovered_vol[*]:-}" volume)")"

# ADIM 3: saat
step_title 3 "Yedeğin her gün alınacağı saat"
while true; do
  RUN_TIME="$(ask "Saat (SS:DD)" "$RUN_TIME")"
  if [[ "$RUN_TIME" =~ ^([01][0-9]|2[0-3]):([0-5][0-9])$ ]]; then
    break
  fi
  echo "  Saat 03:30 biçiminde olmalı."
  (( ASSUME_YES == 0 )) || die "Geçersiz saat: ${RUN_TIME}"
done
CRON_HOUR="$((10#${BASH_REMATCH[1]}))"
CRON_MINUTE="$((10#${BASH_REMATCH[2]}))"

# ADIM 4: saklama
step_title 4 "Yedekler kaç gün saklansın"
LOCAL_RETENTION_DAYS="$(ask_number "Sunucuda kaç gün" "$LOCAL_RETENTION_DAYS")"

# ADIM 5: Google Drive
step_title 5 "Google Drive"
export RCLONE_CONFIG="$RCLONE_CONFIG_PATH"
USE_DRIVE=1
default_drive="E"
if (( HAD_CONFIG == 1 )) && [[ -z "$RCLONE_REMOTE" ]]; then
  default_drive="H"
fi
if ask_yes_no "Yedekler Google Drive'a da yüklensin mi?" "$default_drive"; then
  current_remote_name="gdrive"
  current_folder="Kyrox-Yedek"
  if [[ "$RCLONE_REMOTE" =~ ^([A-Za-z0-9_-]+):([^/]+) ]]; then
    current_remote_name="${BASH_REMATCH[1]}"
    current_folder="${BASH_REMATCH[2]}"
  fi
  DRIVE_FOLDER="$(ask "Drive'daki klasör adı" "$current_folder")"
  [[ -n "$DRIVE_FOLDER" && "$DRIVE_FOLDER" != */* ]] || die "Klasör adı boş olamaz ve / içeremez"
  REMOTE_RETENTION_DAYS="$(ask_number "Drive'da kaç gün" "$REMOTE_RETENTION_DAYS")"
  REMOTE_NAME="$current_remote_name"
else
  USE_DRIVE=0
  RCLONE_REMOTE=""
fi

# ADIM 6: özet ve onay
step_title 6 "Özet"
echo "  Proje klasörleri : ${APP_DIRS:-(yok)}"
echo "  PostgreSQL       : ${PG_CONTAINERS:-(yok)}"
echo "  MariaDB/MySQL    : ${MYSQL_CONTAINERS:-(yok)}"
echo "  Docker volume    : ${VOLUMES:-(yok)}"
echo "  Saat             : her gün ${RUN_TIME}"
echo "  Sunucuda         : ${BACKUP_ROOT}, ${LOCAL_RETENTION_DAYS} gün"
if (( USE_DRIVE == 1 )); then
  echo "  Google Drive     : ${DRIVE_FOLDER}/${HOST_NAME}, ${REMOTE_RETENTION_DAYS} gün"
else
  echo "  Google Drive     : kullanılmayacak"
fi
echo "  Log              : ${LOG_FILE}"
ask_yes_no "Bu ayarlarla kurulsun mu?" "E" || die "İptal edildi; hiçbir şey değiştirilmedi"

# Paketler
missing_packages=()
command -v flock >/dev/null 2>&1 || missing_packages+=(util-linux)
command -v gzip >/dev/null 2>&1 || missing_packages+=(gzip)
if (( USE_DRIVE == 1 )); then
  command -v rclone >/dev/null 2>&1 || missing_packages+=(rclone)
fi
if (( ${#missing_packages[@]} > 0 )); then
  log "Paketler kuruluyor: ${missing_packages[*]}"
  command -v apt-get >/dev/null 2>&1 || die "apt-get yok; şu paketleri elle kurun: ${missing_packages[*]}"
  DEBIAN_FRONTEND=noninteractive apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${missing_packages[@]}" >/dev/null
fi

# Drive bağlantısı
if (( USE_DRIVE == 1 )); then
  mkdir -p "$(dirname "$RCLONE_CONFIG_PATH")"
  need_token=1
  if rclone listremotes 2>/dev/null | grep -qx "${REMOTE_NAME}:"; then
    if rclone lsd "${REMOTE_NAME}:" >/dev/null 2>&1; then
      log "Google Drive bağlantısı zaten var ve çalışıyor."
      if ! ask_yes_no "Başka bir Google hesabına bağlamak ister misiniz?" "H"; then
        need_token=0
      fi
    else
      log "Kayıtlı Google Drive bağlantısı çalışmıyor; yeniden bağlanmak gerekiyor."
    fi
  fi
  if (( need_token == 1 && ASSUME_YES == 1 )); then
    log "--yes: Drive bağlantısı yok; yedek yalnız sunucuda tutulacak. Bağlamak için sihirbazı soru sorarak çalıştırın."
    USE_DRIVE=0
  elif (( need_token == 1 )); then
    cat <<'EOF'

  Google Drive'a bağlanmak için bir kerelik izin gerekiyor.
  Bu adımı SUNUCUDA DEĞİL, tarayıcısı olan KENDİ BİLGİSAYARINIZDA yapın:

    1) Bilgisayarınızda PowerShell açın ve rclone'u kurun (bir kez yeterli):
         winget install Rclone.Rclone
       Kurulum bitince PowerShell'i kapatıp yeniden açın.

    2) Şu komutu çalıştırın:
         rclone authorize "drive"

    3) Tarayıcı açılır. Yedeklerin gideceği Google hesabıyla giriş yapıp
       izin verin. Tarayıcıda "Success" yazısını görünce PowerShell'e dönün.

    4) PowerShell'de çıkan, {"access_token": ile başlayıp } ile biten
       uzun satırın TAMAMINI kopyalayın.

    5) Buraya yapıştırıp Enter'a basın.
       Vazgeçmek için boş bırakıp Enter'a basın; yedek yalnız sunucuda tutulur.

EOF
    while true; do
      token=""
      read -r -p "Token: " token < "$PROMPT_INPUT"
      if [[ -z "$token" ]]; then
        log "Drive atlandı; yedek yalnız sunucuda tutulacak. Sonra bağlamak için sihirbazı tekrar çalıştırın."
        USE_DRIVE=0
        break
      fi
      if [[ "$token" != \{*access_token*\} ]]; then
        echo "  Bu satır token gibi görünmüyor. { ile başlayıp } ile biten satırın tamamını yapıştırın."
        continue
      fi
      rclone config delete "$REMOTE_NAME" >/dev/null 2>&1 || true
      if rclone config create "$REMOTE_NAME" drive scope=drive token="$token" --non-interactive >/dev/null 2>&1 \
        && rclone lsd "${REMOTE_NAME}:" >/dev/null 2>&1; then
        chmod 600 "$RCLONE_CONFIG_PATH"
        log "Google Drive bağlantısı kuruldu."
        break
      fi
      rclone config delete "$REMOTE_NAME" >/dev/null 2>&1 || true
      echo "  Bu token ile Drive'a bağlanılamadı. 2. adımdan tekrar deneyin ya da boş bırakıp geçin."
    done
    unset token
  fi
  if (( USE_DRIVE == 1 )); then
    RCLONE_REMOTE="${REMOTE_NAME}:${DRIVE_FOLDER}/${HOST_NAME}"
    rclone mkdir "$RCLONE_REMOTE"
    log "Drive klasörü hazır: ${DRIVE_FOLDER}/${HOST_NAME}"
  else
    RCLONE_REMOTE=""
  fi
fi

# ADIM 7: kurulum
step_title 7 "Kurulum"
if [[ -f "$CONFIG_FILE" ]]; then
  cp -p "$CONFIG_FILE" "${CONFIG_FILE}.bak"
fi
cat > "$CONFIG_FILE" <<EOF
# Kyrox günlük yedek ayarları. install-backup.sh sihirbazı yazar; değiştirmek için
# sihirbazı tekrar çalıştırın ya da bu dosyayı düzenleyin. Elle deneme: sudo kyrox-backup

BACKUP_ROOT="${BACKUP_ROOT}"
APP_DIRS="${APP_DIRS}"
EXCLUDE_NAMES="${EXCLUDE_NAMES}"
EXCLUDE_PATHS="${EXCLUDE_PATHS}"
PG_CONTAINERS="${PG_CONTAINERS}"
PG_USER="${PG_USER}"

# Dump alınacak MariaDB/MySQL konteynerleri (root şifresi konteynerin kendi ortamından okunur).
MYSQL_CONTAINERS="${MYSQL_CONTAINERS}"
# Olduğu gibi arşivlenecek Docker volume'ları (ör. WordPress dosyaları).
VOLUMES="${VOLUMES}"
RCLONE_REMOTE="${RCLONE_REMOTE}"
RCLONE_CONFIG="${RCLONE_CONFIG_PATH}"
LOCAL_RETENTION_DAYS=${LOCAL_RETENTION_DAYS}
REMOTE_RETENTION_DAYS=${REMOTE_RETENTION_DAYS}
MIN_FREE_MB=${MIN_FREE_MB}
EOF
chmod 600 "$CONFIG_FILE"
log "Ayarlar yazıldı: ${CONFIG_FILE}"

install -m 750 "${SCRIPT_DIR}/kyrox-backup.sh" "$BIN_PATH"
log "Yedek komutu kuruldu: ${BIN_PATH}"

cat > "$CRON_FILE" <<EOF
# Kyrox günlük yedek (install-backup.sh tarafından oluşturuldu)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
${CRON_MINUTE} ${CRON_HOUR} * * * root ${BIN_PATH} >> ${LOG_FILE} 2>&1
EOF
chmod 644 "$CRON_FILE"
log "Her gün ${RUN_TIME} için zamanlandı: ${CRON_FILE}"

cat > "$LOGROTATE_FILE" <<EOF
${LOG_FILE} {
  weekly
  rotate 8
  compress
  missingok
  notifempty
}
EOF

echo
if ask_yes_no "Şimdi bir deneme yedeği alınsın mı? (birkaç dakika sürer)" "E"; then
  if KYROX_BACKUP_CONFIG="$CONFIG_FILE" "$BIN_PATH" 2>&1 | tee -a "$LOG_FILE"; then
    log "Deneme yedeği başarılı."
  else
    die "Deneme yedeği başarısız; ayrıntı yukarıda ve ${LOG_FILE} dosyasında"
  fi
else
  log "Deneme atlandı. Elle denemek için: sudo kyrox-backup"
fi

echo
log "Kurulum tamamlandı. Yedek her gün saat ${RUN_TIME} olduğunda kendiliğinden alınır."
log "Log: ${LOG_FILE}   Elle yedek: sudo kyrox-backup   Ayarları değiştirmek: bu sihirbazı tekrar çalıştırın"
