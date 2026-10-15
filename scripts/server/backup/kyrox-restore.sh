#!/usr/bin/env bash
#
# Kyrox geri yükleme sihirbazı.
# kyrox-backup yedeğinden (sunucudaki klasör ya da Google Drive) projeleri, PostgreSQL
# veritabanlarını, WordPress'i (MariaDB + dosyalar) ve sunucu ayarlarını geri yükler.
# Adım adım sorar. Üzerine yazılan her şeyin önce bir kopyası alınır.
#
# Kullanım:
#   sudo bash /opt/kyrox/kyrox-fair-crm/scripts/server/backup/kyrox-restore.sh
#   sudo bash .../kyrox-restore.sh --deneme
#
# Seçenekler:
#   --deneme   Tatbikat: hiçbir şeye dokunmadan yedeğin geri yüklenebildiğini sınar.
#              Veritabanları geçici kapsayıcılara açılır, tablolar sayılır, sonra silinir.
#   -h, --help Bu yardımı göster
#
# Yeni sunucuda sıra: bootstrap-server.sh → bu sihirbaz → (sihirbaz sorar) deploy-all.sh
# → install-backup.sh. Ayrıntı: scripts/server/backup/README.md
#
set -Eeuo pipefail

KYROX_ROOT="${KYROX_ROOT:-/opt/kyrox}"
BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/kyrox}"
CONFIG_FILE="${KYROX_BACKUP_CONFIG:-/etc/kyrox-backup.env}"
RCLONE_CONFIG_PATH="${RCLONE_CONFIG:-/root/.config/rclone/rclone.conf}"
PROMPT_INPUT="${PROMPT_INPUT:-/dev/tty}"
PG_USER="${PG_USER:-postgres}"
PG_IMAGE="${PG_IMAGE:-postgres:18-alpine}"
MARIADB_IMAGE="${MARIADB_IMAGE:-mariadb:11.8}"
SERVISLER=(fair-crm-backend fair-crm-mail-worker fair-stand kyrox-core)
STAMP="$(date +%Y%m%d-%H%M%S)"
DENEME=0

log() { echo "[geri-yükleme] $*"; }
die() { echo "[geri-yükleme] HATA: $*" >&2; exit 1; }
trap 'echo "[geri-yükleme] HATA: satır ${LINENO}: ${BASH_COMMAND}" >&2' ERR

usage() { sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --deneme) DENEME=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Bilinmeyen seçenek: $1 (--help)" ;;
  esac
done

# Sihirbaz proje klasörünün içinden çalışır ve o klasörü yedekten yeniden açabilir;
# bash betiği okurken değişmesin diye önce geçici bir kopyaya geçilir.
if [[ -z "${KYROX_RESTORE_KOPYA:-}" ]]; then
  kopya="$(mktemp /tmp/kyrox-restore.XXXXXX.sh)"
  cp "${BASH_SOURCE[0]}" "$kopya"
  secenekler=()
  (( DENEME == 0 )) || secenekler+=(--deneme)
  KYROX_RESTORE_KOPYA="$kopya" exec bash "$kopya" "${secenekler[@]}"
fi
trap 'rm -f "$KYROX_RESTORE_KOPYA"' EXIT

if (( DENEME == 1 )); then TOTAL_STEPS=5; else TOTAL_STEPS=9; fi

step_title() {
  echo
  echo "────────────────────────────────────────────────────────────"
  echo " ADIM $1/${TOTAL_STEPS}: $2"
  echo "────────────────────────────────────────────────────────────"
}

ask() {
  local label="$1" current="$2" answer=""
  read -r -p "${label} [${current}]: " answer < "$PROMPT_INPUT" || die "Cevap okunamadı; ssh ile bağlanırken -t kullanın"
  printf '%s' "${answer:-$current}"
}

ask_yes_no() {
  local label="$1" default="$2" answer="" hint
  if [[ "$default" == "E" ]]; then hint="E/h"; else hint="e/H"; fi
  while true; do
    read -r -p "${label} [${hint}]: " answer < "$PROMPT_INPUT" || die "Cevap okunamadı; ssh ile bağlanırken -t kullanın"
    answer="${answer:-$default}"
    case "${answer,,}" in
      e|evet|y|yes) return 0 ;;
      h|hayır|hayir|n|no) return 1 ;;
      *) echo "  Lütfen e (evet) ya da h (hayır) yazın." ;;
    esac
  done
}

# ask_choice "Soru" sayı -> 1..sayı arası seçim (Enter = 1)
ask_choice() {
  local label="$1" max="$2" secim
  while true; do
    secim="$(ask "$label" 1)"
    if [[ "$secim" =~ ^[0-9]+$ ]] && (( secim >= 1 && secim <= max )); then
      printf '%s' "$secim"
      return 0
    fi
    echo "  1 ile ${max} arasında bir sayı yazın." >&2
  done
}

boyut() { du -sh "$1" 2>/dev/null | cut -f1; }

# Kapsayıcı sağlıklı ya da (sağlık kontrolü yoksa) çalışır olana kadar bekler.
bekle_kapsayici() {
  local ad="$1" durum
  for _ in $(seq 1 60); do
    durum="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$ad" 2>/dev/null || true)"
    [[ "$durum" == "healthy" || "$durum" == "running" ]] && return 0
    sleep 2
  done
  die "${ad} hazır olmadı (durum: ${durum:-yok}); docker logs ${ad} ile bakın"
}

pg_hazir() {
  local ad="$1"
  for _ in $(seq 1 60); do
    docker exec "$ad" pg_isready -U "$PG_USER" >/dev/null 2>&1 && return 0
    sleep 2
  done
  die "${ad} içindeki PostgreSQL hazır olmadı"
}

# Dump içindeki tablo sayısı (pg_restore --list'teki TABLE satırları; TABLE DATA hariç).
dump_tablo_sayisi() {
  docker exec -i "$1" pg_restore --list < "$2" | grep -E '^[0-9]+; [0-9]+ [0-9]+ TABLE ' | grep -vc ' TABLE DATA ' || true
}
db_tablo_sayisi() {
  docker exec "$1" psql -U "$PG_USER" -d "$2" -tAc \
    "SELECT count(*) FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema')"
}

# ─────────────────────────────────────────────────────────────
step_title 1 "Ön kontroller"
[[ "$(id -u)" -eq 0 ]] || die "root olarak çalıştırın: sudo bash $0"
{ : < "$PROMPT_INPUT"; } 2>/dev/null || die "Soru sorulabilecek bir terminal yok. ssh ile bağlanırken -t kullanın."
for komut in tar gzip sha256sum docker; do
  command -v "$komut" >/dev/null || die "${komut} kurulu değil (yeni sunucuda önce bootstrap-server.sh çalıştırın)"
done
docker info >/dev/null 2>&1 || die "Docker çalışmıyor"
if (( DENEME == 1 )); then
  log "Tatbikat modu: canlı projelere, veritabanlarına ve ayarlara dokunulmaz."
else
  aktif=()
  for s in "${SERVISLER[@]}"; do systemctl is-active --quiet "$s" 2>/dev/null && aktif+=("$s"); done
  if (( ${#aktif[@]} > 0 )); then
    echo "  DİKKAT: Bu sunucuda çalışan Kyrox servisleri var: ${aktif[*]}"
    echo "  Geri yükleme bunları durdurur ve verileri yedektekiyle değiştirir (sitelerde kesinti olur)."
    echo "  Yalnız sınamak istiyorsanız iptal edip --deneme ile çalıştırın."
    ask_yes_no "Bu sunucuya geri yükleme yapılsın mı?" "H" || die "İptal edildi; hiçbir şey değiştirilmedi"
  fi
fi
log "Tamam."

# ─────────────────────────────────────────────────────────────
step_title 2 "Yedeği seç"
mkdir -p "$BACKUP_ROOT"; chmod 700 "$BACKUP_ROOT"
mapfile -t yerel < <(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name '20??-??-??_??????' -printf '%f\n' | sort -r)
KAYNAK="yerel"
if (( ${#yerel[@]} > 0 )); then
  echo "  Bu sunucudaki yedekler (${BACKUP_ROOT}):"
  i=1; for y in "${yerel[@]:0:10}"; do printf '    %2d) %s  (%s)\n' "$i" "$y" "$(boyut "${BACKUP_ROOT}/${y}")"; i=$((i + 1)); done
  ask_yes_no "Bunlardan biri kullanılsın mı? (hayır: Google Drive'dan indir)" "E" || KAYNAK="drive"
else
  echo "  Bu sunucuda yedek yok; Google Drive'dan indirilecek."
  KAYNAK="drive"
fi

if [[ "$KAYNAK" == "yerel" ]]; then
  secim="$(ask_choice "Yedek numarası (1 = en yeni)" "$(( ${#yerel[@]} < 10 ? ${#yerel[@]} : 10 ))")"
  YEDEK="${BACKUP_ROOT}/${yerel[$((secim - 1))]}"
else
  command -v rclone >/dev/null || { log "rclone kuruluyor"; DEBIAN_FRONTEND=noninteractive apt-get install -y -qq rclone >/dev/null; }
  export RCLONE_CONFIG="$RCLONE_CONFIG_PATH"
  remote_ad="gdrive"; klasor="Kyrox-Yedek"
  if [[ -r "$CONFIG_FILE" ]]; then
    onceki_remote="$(grep -E '^RCLONE_REMOTE=' "$CONFIG_FILE" | cut -d= -f2- | tr -d '"' || true)"
    [[ "$onceki_remote" =~ ^([A-Za-z0-9_-]+):([^/]+) ]] && { remote_ad="${BASH_REMATCH[1]}"; klasor="${BASH_REMATCH[2]}"; }
  fi
  if ! rclone lsd "${remote_ad}:" >/dev/null 2>&1; then
    cat <<'EOF'

  Google Drive'a bağlanmak için bir kerelik izin gerekiyor. KENDİ BİLGİSAYARINIZDA:
    1) PowerShell'de (bir kez):  winget install Rclone.Rclone   (sonra PowerShell'i yeniden açın)
    2) rclone authorize "drive"
    3) Tarayıcıda yedeklerin olduğu Google hesabıyla izin verin.
    4) {"access_token": ile başlayıp } ile biten satırın TAMAMINI buraya yapıştırın.

EOF
    while true; do
      token=""
      read -r -p "Token (vazgeçmek için boş): " token < "$PROMPT_INPUT" || die "Cevap okunamadı"
      [[ -n "$token" ]] || die "Drive bağlantısı olmadan devam edilemez"
      mkdir -p "$(dirname "$RCLONE_CONFIG_PATH")"
      rclone config delete "$remote_ad" >/dev/null 2>&1 || true
      if rclone config create "$remote_ad" drive scope=drive token="$token" --non-interactive >/dev/null 2>&1 \
        && rclone lsd "${remote_ad}:" >/dev/null 2>&1; then
        chmod 600 "$RCLONE_CONFIG_PATH"; log "Google Drive bağlandı."; break
      fi
      rclone config delete "$remote_ad" >/dev/null 2>&1 || true
      echo "  Bu token ile bağlanılamadı; tekrar deneyin."
    done
    unset token
  fi
  klasor="$(ask "Drive'daki yedek klasörü" "$klasor")"
  mapfile -t sunucular < <(rclone lsf --dirs-only "${remote_ad}:${klasor}" | sed 's#/$##' | sort)
  (( ${#sunucular[@]} > 0 )) || die "${klasor} içinde sunucu klasörü yok"
  echo "  Drive'daki sunucular:"; i=1; for s in "${sunucular[@]}"; do printf '    %2d) %s\n' "$i" "$s"; i=$((i + 1)); done
  sunucu="${sunucular[$(( $(ask_choice "Sunucu numarası" "${#sunucular[@]}") - 1 ))]}"
  mapfile -t tarihler < <(rclone lsf --dirs-only "${remote_ad}:${klasor}/${sunucu}" | sed 's#/$##' | grep -E '^20..-..-.._......$' | sort -r)
  (( ${#tarihler[@]} > 0 )) || die "${sunucu} için yedek yok"
  echo "  ${sunucu} yedekleri:"; i=1; for t in "${tarihler[@]:0:10}"; do printf '    %2d) %s\n' "$i" "$t"; i=$((i + 1)); done
  tarih="${tarihler[$(( $(ask_choice "Yedek numarası (1 = en yeni)" "$(( ${#tarihler[@]} < 10 ? ${#tarihler[@]} : 10 ))") - 1 ))]}"
  YEDEK="${BACKUP_ROOT}/${tarih}"
  if [[ -d "$YEDEK" ]]; then
    log "${YEDEK} zaten sunucuda; indirilmedi."
  else
    log "İndiriliyor: ${remote_ad}:${klasor}/${sunucu}/${tarih} → ${YEDEK}"
    rclone copy "${remote_ad}:${klasor}/${sunucu}/${tarih}" "${YEDEK}.partial" --transfers 2 --retries 5
    mv "${YEDEK}.partial" "$YEDEK"; chmod -R go-rwx "$YEDEK"
  fi
fi
[[ -f "${YEDEK}/SHA256SUMS" ]] || die "${YEDEK} bir kyrox-backup yedeği değil (SHA256SUMS yok)"
sed 's/^/    /' "${YEDEK}/MANIFEST.txt" 2>/dev/null || true

# ─────────────────────────────────────────────────────────────
step_title 3 "Yedeğin sağlamlığı"
(cd "$YEDEK" && sha256sum --quiet -c SHA256SUMS) || die "Sağlama toplamı tutmuyor; yedek bozuk ya da eksik"
log "Bütün dosyaların sağlama toplamı doğru."
for f in "$YEDEK"/app/*.tar.gz "$YEDEK"/volume/*.tar.gz "$YEDEK"/system/*.tar.gz "$YEDEK"/db/*.sql.gz; do
  [[ -f "$f" ]] || continue
  gzip -t "$f" || die "${f} açılamıyor"
done
log "Bütün arşivler açılabiliyor."
mapfile -t PROJELER < <(find "$YEDEK/app" -maxdepth 1 -name '*.tar.gz' -printf '%f\n' 2>/dev/null | sed 's/\.tar\.gz$//' | sort)
mapfile -t PG_DUMPLAR < <(find "$YEDEK/db" -maxdepth 1 -name '*.dump' -printf '%f\n' 2>/dev/null | sort)
mapfile -t PG_ROLLER < <(find "$YEDEK/db" -maxdepth 1 -name '*__globals.sql' -printf '%f\n' 2>/dev/null | sort)
mapfile -t MY_DUMPLAR < <(find "$YEDEK/db" -maxdepth 1 -name '*__all.sql.gz' -printf '%f\n' 2>/dev/null | sort)
mapfile -t VOLUMELER < <(find "$YEDEK/volume" -maxdepth 1 -name '*.tar.gz' -printf '%f\n' 2>/dev/null | sed 's/\.tar\.gz$//' | sort)
SISTEM="$YEDEK/system/system-config.tar.gz"
echo "  Projeler       : ${PROJELER[*]:-(yok)}"
echo "  PostgreSQL     : ${PG_DUMPLAR[*]:-(yok)}"
echo "  MariaDB        : ${MY_DUMPLAR[*]:-(yok)}"
echo "  Docker volume  : ${VOLUMELER[*]:-(yok)}"
echo "  Sunucu ayarları: $( [[ -f "$SISTEM" ]] && echo var || echo yok )"

# ═════════════════════════════════════════════════════════════
# Tatbikat: geçici kapsayıcılara aç, say, sil.
if (( DENEME == 1 )); then
  TMP_PG="kyrox-restore-deneme-pg"; TMP_MY="kyrox-restore-deneme-mariadb"
  # shellcheck disable=SC2329  # trap ile çağrılır
  temizle() { docker rm -f "$TMP_PG" "$TMP_MY" >/dev/null 2>&1 || true; rm -f "${KYROX_RESTORE_KOPYA:-}"; }
  trap temizle EXIT
  HATA=0

  step_title 4 "PostgreSQL tatbikatı (geçici kapsayıcı)"
  if (( ${#PG_DUMPLAR[@]} > 0 )); then
    docker rm -f "$TMP_PG" >/dev/null 2>&1 || true
    docker run -d --name "$TMP_PG" -e POSTGRES_PASSWORD=deneme "$PG_IMAGE" >/dev/null
    pg_hazir "$TMP_PG"
    for g in "${PG_ROLLER[@]}"; do
      docker exec -i "$TMP_PG" psql -U "$PG_USER" -q -v ON_ERROR_STOP=0 < "$YEDEK/db/$g" >/dev/null 2>&1 || true
    done
    for d in "${PG_DUMPLAR[@]}"; do
      db="${d#*__}"; db="${db%.dump}"
      beklenen="$(dump_tablo_sayisi "$TMP_PG" "$YEDEK/db/$d")"
      if docker exec -i "$TMP_PG" pg_restore -U "$PG_USER" -d postgres --create --exit-on-error < "$YEDEK/db/$d" >/dev/null 2>"/tmp/kyrox-restore-${db}.log"; then
        bulunan="$(db_tablo_sayisi "$TMP_PG" "$db")"
        if [[ "$bulunan" == "$beklenen" ]]; then
          log "TAMAM  ${db}: ${bulunan}/${beklenen} tablo"
        else
          log "UYARI  ${db}: ${bulunan}/${beklenen} tablo"; HATA=1
        fi
      else
        log "HATA   ${db}: açılamadı (ayrıntı /tmp/kyrox-restore-${db}.log)"; HATA=1
      fi
    done
    docker rm -f "$TMP_PG" >/dev/null
  else
    log "PostgreSQL dökümü yok; atlandı."
  fi

  step_title 5 "MariaDB ve dosya tatbikatı"
  for d in "${MY_DUMPLAR[@]}"; do
    docker rm -f "$TMP_MY" >/dev/null 2>&1 || true
    docker run -d --name "$TMP_MY" -e MARIADB_ROOT_PASSWORD=deneme "$MARIADB_IMAGE" >/dev/null
    for _ in $(seq 1 60); do docker exec "$TMP_MY" mariadb -uroot -pdeneme -e 'SELECT 1' >/dev/null 2>&1 && break; sleep 2; done
    # Döküm kullanıcı tablolarını da içerir; yetkiler yeniden yüklenmediği için bu oturum şifresi geçerli kalır.
    if zcat "$YEDEK/db/$d" | docker exec -i "$TMP_MY" mariadb -uroot -pdeneme 2>"/tmp/kyrox-restore-mariadb.log"; then
      ozet="$(docker exec "$TMP_MY" mariadb -uroot -pdeneme -N -e "SELECT table_schema, count(*) FROM information_schema.tables WHERE table_schema NOT IN ('mysql','information_schema','performance_schema','sys') GROUP BY table_schema" | tr '\t' ' ' | paste -sd',' -)"
      yazilar="$(docker exec "$TMP_MY" mariadb -uroot -pdeneme -N -e "SELECT CONCAT(table_schema,'.',table_name) FROM information_schema.tables WHERE table_name LIKE '%\\_posts' LIMIT 1" || true)"
      [[ -n "$yazilar" ]] && ozet="${ozet}; ${yazilar}: $(docker exec "$TMP_MY" mariadb -uroot -pdeneme -N -e "SELECT count(*) FROM ${yazilar}") kayıt"
      log "TAMAM  ${d%__all.sql.gz}: ${ozet:-tablo yok}"
    else
      log "HATA   ${d}: açılamadı (ayrıntı /tmp/kyrox-restore-mariadb.log)"; HATA=1
    fi
    docker rm -f "$TMP_MY" >/dev/null
  done
  (( ${#MY_DUMPLAR[@]} > 0 )) || log "MariaDB dökümü yok; atlandı."
  for p in "${PROJELER[@]}"; do
    log "TAMAM  proje ${p}: $(tar tzf "$YEDEK/app/${p}.tar.gz" | wc -l) dosya, .env: $(tar tzf "$YEDEK/app/${p}.tar.gz" | grep -cE '(^|/)\.env$' || true)"
  done
  for v in "${VOLUMELER[@]}"; do log "TAMAM  volume ${v}: $(tar tzf "$YEDEK/volume/${v}.tar.gz" | wc -l) dosya"; done
  [[ -f "$SISTEM" ]] && log "TAMAM  sunucu ayarları: $(tar tzf "$SISTEM" | wc -l) dosya"
  echo
  if (( HATA == 0 )); then
    log "Tatbikat başarılı: ${YEDEK} geri yüklenebilir. Canlı sisteme dokunulmadı."
  else
    die "Tatbikatta sorun çıktı; yukarıdaki HATA/UYARI satırlarına bakın. Canlı sisteme dokunulmadı."
  fi
  exit 0
fi

# ═════════════════════════════════════════════════════════════
# Gerçek geri yükleme
GUVENLIK="${BACKUP_ROOT}/geri-yukleme-oncesi-${STAMP}"
mkdir -p "$GUVENLIK"; chmod 700 "$GUVENLIK"
DURDURULAN=()
YAPILAN=()

step_title 4 "Neler geri yüklensin"
P_PROJE=0; P_PG=0; P_WP=0; P_SISTEM=0
(( ${#PROJELER[@]} > 0 )) && ask_yes_no "Proje dosyaları (.env dahil): ${PROJELER[*]}?" "E" && P_PROJE=1
(( ${#PG_DUMPLAR[@]} > 0 )) && ask_yes_no "PostgreSQL veritabanları?" "E" && P_PG=1
(( ${#MY_DUMPLAR[@]} + ${#VOLUMELER[@]} > 0 )) && ask_yes_no "WordPress (MariaDB + dosyalar)?" "E" && P_WP=1
[[ -f "$SISTEM" ]] && ask_yes_no "Sunucu ayarları (nginx, SSL, servis tanımları, cron)?" "E" && P_SISTEM=1
(( P_PROJE + P_PG + P_WP + P_SISTEM > 0 )) || die "Hiçbir şey seçilmedi"
echo "  Üzerine yazılan her şeyin kopyası: ${GUVENLIK}"
ask_yes_no "Başlansın mı?" "E" || die "İptal edildi; hiçbir şey değiştirilmedi"
if (( P_PROJE + P_PG > 0 )); then
  for s in "${SERVISLER[@]}"; do
    if systemctl is-active --quiet "$s" 2>/dev/null; then systemctl stop "$s"; DURDURULAN+=("$s"); fi
  done
  (( ${#DURDURULAN[@]} == 0 )) || log "Durduruldu: ${DURDURULAN[*]}"
fi

# ─────────────────────────────────────────────────────────────
step_title 5 "Proje dosyaları"
if (( P_PROJE == 1 )); then
  mkdir -p "$KYROX_ROOT"
  for p in "${PROJELER[@]}"; do
    # Eski düzenin yedekleri (fair-crm, fair-stand) yeni adlarla açılır.
    hedef_ad="$p"; [[ "$p" == kyrox-* ]] || hedef_ad="kyrox-${p}"
    hedef="${KYROX_ROOT}/${hedef_ad}"
    if [[ -e "$hedef" && ! -L "$hedef" ]]; then
      mv "$hedef" "${GUVENLIK}/${hedef_ad}"
      log "Mevcut ${hedef} kenara alındı: ${GUVENLIK}/${hedef_ad}"
    fi
    tar -C "$KYROX_ROOT" --transform "s#^${p}#${hedef_ad}#" -xzpf "$YEDEK/app/${p}.tar.gz"
    log "Açıldı: ${hedef}"
  done
  YAPILAN+=("projeler")
else
  log "Atlandı."
fi

# ─────────────────────────────────────────────────────────────
step_title 6 "PostgreSQL veritabanları"
if (( P_PG == 1 )); then
  PG_HEDEF="$(ask "Hedef PostgreSQL kapsayıcısı" "kyrox-db")"
  if ! docker ps --format '{{.Names}}' | grep -qx "$PG_HEDEF"; then
    if docker ps -a --format '{{.Names}}' | grep -qx "$PG_HEDEF"; then
      docker start "$PG_HEDEF" >/dev/null
    elif [[ "$PG_HEDEF" == "kyrox-db" && -f "${KYROX_ROOT}/kyrox-fair-crm/docker-compose.yml" ]]; then
      docker compose -f "${KYROX_ROOT}/kyrox-fair-crm/docker-compose.yml" up -d postgres
    else
      die "${PG_HEDEF} kapsayıcısı yok; önce bootstrap-server.sh çalıştırın"
    fi
  fi
  pg_hazir "$PG_HEDEF"
  mevcut="$(docker exec "$PG_HEDEF" psql -U "$PG_USER" -d postgres -tAc "SELECT datname FROM pg_database WHERE NOT datistemplate AND datname <> 'postgres'" | paste -sd' ' -)"
  if [[ -n "$mevcut" ]]; then
    echo "  ${PG_HEDEF} içinde var olan veritabanları: ${mevcut}"
    echo "  Yedekte olanlar silinip yedektekiyle değiştirilecek (önce kopyaları alınır)."
    ask_yes_no "Devam edilsin mi?" "H" || die "İptal edildi. Durdurulan servisler: ${DURDURULAN[*]:-(yok)} (systemctl start ile başlatın)"
  fi
  for g in "${PG_ROLLER[@]}"; do
    # Var olan roller hata verir; yalnız eksikler eklenir.
    docker exec -i "$PG_HEDEF" psql -U "$PG_USER" -q -v ON_ERROR_STOP=0 < "$YEDEK/db/$g" >/dev/null 2>&1 || true
  done
  for d in "${PG_DUMPLAR[@]}"; do
    db="${d#*__}"; db="${db%.dump}"
    if [[ " ${mevcut} " == *" ${db} "* ]]; then
      docker exec "$PG_HEDEF" pg_dump -U "$PG_USER" -Fc "$db" > "${GUVENLIK}/${PG_HEDEF}__${db}.dump"
      docker exec "$PG_HEDEF" psql -U "$PG_USER" -d postgres -qtAc \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${db}' AND pid <> pg_backend_pid()" >/dev/null
    fi
    beklenen="$(dump_tablo_sayisi "$PG_HEDEF" "$YEDEK/db/$d")"
    docker exec -i "$PG_HEDEF" pg_restore -U "$PG_USER" -d postgres --create --clean --if-exists --exit-on-error < "$YEDEK/db/$d" \
      || die "${db} geri yüklenemedi. Önceki hali: ${GUVENLIK}/${PG_HEDEF}__${db}.dump"
    log "Geri yüklendi: ${db} ($(db_tablo_sayisi "$PG_HEDEF" "$db")/${beklenen} tablo)"
  done
  YAPILAN+=("PostgreSQL")
else
  log "Atlandı."
fi

# ─────────────────────────────────────────────────────────────
step_title 7 "WordPress (MariaDB ve dosyalar)"
if (( P_WP == 1 )); then
  WEB_SUNUCU="${KYROX_ROOT}/kyrox-web/sunucu"
  web_compose() { docker compose --project-directory "$WEB_SUNUCU" -f "${WEB_SUNUCU}/docker-compose.yml" "$@"; }
  for d in "${MY_DUMPLAR[@]}"; do
    kap="${d%__all.sql.gz}"
    if ! docker ps --format '{{.Names}}' | grep -qx "$kap"; then
      if docker ps -a --format '{{.Names}}' | grep -qx "$kap"; then
        docker start "$kap" >/dev/null
      elif [[ -f "${WEB_SUNUCU}/docker-compose.yml" && -f "${WEB_SUNUCU}/.env" ]]; then
        web_compose up -d db
      else
        die "${kap} kapsayıcısı yok ve ${WEB_SUNUCU}/.env bulunamadı; önce proje dosyalarını geri yükleyin"
      fi
    fi
    bekle_kapsayici "$kap"
    # shellcheck disable=SC2016
    docker exec "$kap" sh -c 'exec mariadb-dump -uroot -p"${MARIADB_ROOT_PASSWORD:-$MYSQL_ROOT_PASSWORD}" --all-databases --single-transaction' \
      | gzip > "${GUVENLIK}/${kap}__all.sql.gz" || log "UYARI: ${kap} için önceki halin kopyası alınamadı (boş olabilir)"
    docker ps --format '{{.Names}}' | grep -qx kyrox-web && docker stop kyrox-web >/dev/null
    # shellcheck disable=SC2016
    zcat "$YEDEK/db/$d" | docker exec -i "$kap" sh -c 'exec mariadb -uroot -p"${MARIADB_ROOT_PASSWORD:-$MYSQL_ROOT_PASSWORD}"' \
      || die "${kap} geri yüklenemedi. Önceki hali: ${GUVENLIK}/${kap}__all.sql.gz"
    log "Geri yüklendi: ${kap} (MariaDB, tümü)"
  done
  for v in "${VOLUMELER[@]}"; do
    docker volume create "$v" >/dev/null
    yol="$(docker volume inspect -f '{{.Mountpoint}}' "$v")"
    mapfile -t kullanan < <(docker ps -q --filter "volume=${v}")
    (( ${#kullanan[@]} == 0 )) || docker stop "${kullanan[@]}" >/dev/null
    if [[ -n "$(ls -A "$yol")" ]]; then
      tar -C "$yol" --numeric-owner -czpf "${GUVENLIK}/volume-${v}.tar.gz" .
      find "$yol" -mindepth 1 -delete
    fi
    tar -C "$yol" --numeric-owner -xzpf "$YEDEK/volume/${v}.tar.gz"
    log "Geri yüklendi: volume ${v}"
  done
  if [[ -f "${WEB_SUNUCU}/docker-compose.yml" && -f "${WEB_SUNUCU}/.env" ]]; then
    web_compose up -d db wordpress
  elif docker ps -a --format '{{.Names}}' | grep -qx kyrox-web; then
    docker start kyrox-web >/dev/null
  fi
  YAPILAN+=("WordPress")
else
  log "Atlandı."
fi

# ─────────────────────────────────────────────────────────────
step_title 8 "Sunucu ayarları"
if (( P_SISTEM == 1 )); then
  icerik="$(tar tzf "$SISTEM")"
  secilen=()
  grup() { # grup "Soru" kalıp... : yedekte varsa sorar, seçilirse kalıpları ekler
    local soru="$1"; shift
    local k var=0
    for k in "$@"; do grep -qE "^${k}" <<< "$icerik" && var=1; done
    (( var == 1 )) || return 0
    ask_yes_no "$soru" "E" && secilen+=("$@")
    return 0
  }
  grup "nginx site ayarları?" "etc/nginx/"
  grup "SSL sertifikaları (Let's Encrypt)?" "etc/letsencrypt/"
  grup "Kyrox servis tanımları (systemd)?" "etc/systemd/system/fair-" "etc/systemd/system/kyrox-"
  grup "Zamanlanmış işler (cron)?" "etc/cron.d/kyrox-" "etc/cron.d/fair-"
  grup "Fair CRM sunucu ayarları (/etc/fair-crm)?" "etc/fair-crm/"
  grup "Yedek ayarı (/etc/kyrox-backup.env)?" "etc/kyrox-backup.env"
  if (( ${#secilen[@]} > 0 )); then
    mapfile -t dosyalar < <(grep -E "^($(IFS='|'; echo "${secilen[*]}"))" <<< "$icerik")
    onceki=()
    for f in "${dosyalar[@]}"; do [[ -e "/${f}" && ! -d "/${f}" ]] && onceki+=("$f"); done
    (( ${#onceki[@]} == 0 )) || tar -C / -czpf "${GUVENLIK}/sistem-onceki.tar.gz" "${onceki[@]}"
    tar -C / -xzpf "$SISTEM" "${dosyalar[@]}"
    log "Geri yüklendi: ${#dosyalar[@]} dosya"
    systemctl daemon-reload
    if command -v nginx >/dev/null; then
      if nginx -t 2>/dev/null; then
        systemctl reload nginx 2>/dev/null || systemctl restart nginx
        log "nginx ayarı geçerli, yeniden yüklendi."
      else
        nginx -t || true
        log "UYARI: nginx ayarı hatalı; nginx yeniden yüklenmedi. Önceki dosyalar: ${GUVENLIK}/sistem-onceki.tar.gz"
      fi
    fi
    YAPILAN+=("sunucu ayarları")
  else
    log "Hiçbir grup seçilmedi."
  fi
else
  log "Atlandı."
fi

# ─────────────────────────────────────────────────────────────
step_title 9 "Uygulamaları başlat"
DEPLOY="${KYROX_ROOT}/kyrox-fair-crm/scripts/server/deploy-all.sh"
if (( P_PROJE == 1 )) && [[ -f "$DEPLOY" ]]; then
  echo "  deploy-all.sh bağımlılıkları kurar (.venv, node_modules), veritabanı şemasını günceller"
  echo "  ve servisleri başlatır. Kodu GitHub'daki son haline de çeker."
fi
if [[ -f "$DEPLOY" ]] && (( P_PROJE + P_PG > 0 )) && ask_yes_no "deploy-all.sh çalıştırılsın mı?" "E"; then
  bash "$DEPLOY" || log "UYARI: deploy-all.sh hata verdi; yukarıya bakın"
elif (( ${#DURDURULAN[@]} > 0 )); then
  systemctl start "${DURDURULAN[@]}" || log "UYARI: servisler başlatılamadı: ${DURDURULAN[*]}"
  log "Yeniden başlatıldı: ${DURDURULAN[*]}"
fi
sleep 3
echo "  Sağlık: core=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/v1/health || true)" \
  "crm=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/health || true)" \
  "stand=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8002/health || true)" \
  "wordpress=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8090/wp-login.php || true)"

echo
log "Geri yükleme bitti: ${YAPILAN[*]:-(hiçbiri)}"
log "Yedek: ${YEDEK}"
log "Üzerine yazılanların kopyası: ${GUVENLIK}"
cat <<'EOF'

  Sonraki adımlar (yeni sunucuya taşınırken):
    1) Bilgisayarınızın hosts dosyasına yeni IP ile alan adlarını yazıp siteleri deneyin
       (C:\Windows\System32\drivers\etc\hosts). Eski sunucu bu sırada çalışmaya devam eder.
    2) Her şey doğruysa Natro'da A kayıtlarını yeni IP'ye çevirin (MX kayıtlarına dokunmayın).
    3) Gece yedeğini yeni sunucuda kurun:
         sudo bash /opt/kyrox/kyrox-fair-crm/scripts/server/backup/install-backup.sh
    4) DNS yayıldıktan sonra SSL yenilemesini sınayın: sudo certbot renew --dry-run
EOF
