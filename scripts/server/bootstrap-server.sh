#!/usr/bin/env bash
#
# Fresh Ubuntu server infrastructure bootstrap for KYROX Core + Fair CRM.
#
# Infrastructure only — does not deploy application code, run migrations,
# restore databases, or touch backup/restore file directories.
# After restore work, run deploy-all.sh (upgrade head + restart only).
#
# Usage:
#   sudo bash /opt/fair-crm/scripts/server/bootstrap-server.sh
#
# Fresh Ubuntu (empty server):
#   sudo apt update && sudo apt install -y git
#   sudo git clone -b main https://github.com/hinthorozu/fair-crm.git /opt/fair-crm
#   sudo bash /opt/fair-crm/scripts/server/bootstrap-server.sh
#   sudo nano /opt/fair-crm/backend/.env
#   sudo bash /opt/fair-crm/scripts/server/deploy-all.sh
#   sudo bash /opt/fair-crm/scripts/server/check-server.sh
#
# Interactive fresh-server setup asks for missing operator-controlled values.
# Existing files/settings are preserved whenever possible.
#
# Optional environment overrides:
#   FAIR_CRM_DIR=/opt/fair-crm
#   FAIR_CRM_REPO=https://github.com/hinthorozu/fair-crm.git
#   FAIR_CRM_BRANCH=main
#   KYROX_CORE_DIR=/opt/kyrox-core
#   DEPLOY_SERVICE_USER=ubuntu
#   FAIR_CRM_DOMAIN=faircrm.domain.com
#   SERVER_PUBLIC_IP=203.0.113.10
#   LETSENCRYPT_EMAIL=admin@example.com
#   DEV_SEED_ENV_FILE=/etc/fair-crm/dev-seed.env
#   SKIP_APT=1
#   SKIP_DOCKER=1
#   SKIP_NODE=1
#   SKIP_NGINX=1
#   SKIP_FIREWALL=1
#   SKIP_SSL=1
#   SKIP_REPO_CLONE=1
#   SKIP_POSTGRES=1
#   SKIP_INTERACTIVE_SETUP=1
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

FAIR_CRM_DIR="${FAIR_CRM_DIR:-/opt/fair-crm}"
KYROX_CORE_DIR="${KYROX_CORE_DIR:-/opt/kyrox-core}"
FAIR_CRM_REPO="${FAIR_CRM_REPO:-https://github.com/hinthorozu/fair-crm.git}"
FAIR_CRM_BRANCH="${FAIR_CRM_BRANCH:-main}"
DEPLOY_SERVICE_USER="${DEPLOY_SERVICE_USER:-${SUDO_USER:-$(id -un)}}"
FAIR_CRM_DOMAIN="${FAIR_CRM_DOMAIN:-faircrm.domain.com}"
SERVER_PUBLIC_IP="${SERVER_PUBLIC_IP:-}"
LETSENCRYPT_EMAIL="${LETSENCRYPT_EMAIL:-}"
DEV_SEED_ENV_FILE="${DEV_SEED_ENV_FILE:-/etc/fair-crm/dev-seed.env}"

REPORT_APT="skipped"
REPORT_DOCKER="skipped"
REPORT_NODE="skipped"
REPORT_FIREWALL="skipped"
REPORT_NGINX="skipped"
REPORT_SSL="skipped"
REPORT_REPO="skipped"
REPORT_POSTGRES="skipped"
REPORT_ENV_FILES="not checked"
REPORT_DEV_SEED="not checked"

is_interactive_setup() {
  [[ "${SKIP_INTERACTIVE_SETUP:-0}" != "1" && -t 0 ]]
}

prompt_with_default() {
  local label="$1"
  local current="$2"
  local answer=""
  if ! is_interactive_setup; then
    printf '%s' "$current"
    return 0
  fi
  read -r -p "${label} [${current}]: " answer
  printf '%s' "${answer:-$current}"
}

prompt_optional() {
  local label="$1"
  local current="$2"
  local answer=""
  if ! is_interactive_setup; then
    printf '%s' "$current"
    return 0
  fi
  if [[ -n "$current" ]]; then
    read -r -p "${label} [${current}]: " answer
    printf '%s' "${answer:-$current}"
  else
    read -r -p "${label} (boş bırakılabilir): " answer
    printf '%s' "$answer"
  fi
}

detect_public_ipv4() {
  local detected=""
  if command -v curl >/dev/null 2>&1; then
    detected="$(curl -4 -fsS --connect-timeout 3 --max-time 6 https://api.ipify.org 2>/dev/null || true)"
  fi
  if [[ "$detected" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
    printf '%s' "$detected"
  fi
}

configure_interactive_settings() {
  step "Interactive server settings"

  FAIR_CRM_DOMAIN="$(prompt_with_default "Fair CRM domain" "$FAIR_CRM_DOMAIN")"

  local detected_ip=""
  if [[ -z "$SERVER_PUBLIC_IP" ]]; then
    detected_ip="$(detect_public_ipv4)"
    SERVER_PUBLIC_IP="$detected_ip"
  fi
  if is_interactive_setup; then
    if [[ -n "$SERVER_PUBLIC_IP" ]]; then
      SERVER_PUBLIC_IP="$(prompt_with_default "Server public IPv4 (DNS A record target)" "$SERVER_PUBLIC_IP")"
    else
      read -r -p "Server public IPv4 (DNS A record target): " SERVER_PUBLIC_IP
    fi
  fi

  LETSENCRYPT_EMAIL="$(prompt_optional "Let's Encrypt e-mail" "$LETSENCRYPT_EMAIL")"

  log "FAIR_CRM_DOMAIN=${FAIR_CRM_DOMAIN}"
  if [[ -n "$SERVER_PUBLIC_IP" ]]; then
    log "SERVER_PUBLIC_IP=${SERVER_PUBLIC_IP}"
  else
    warn "Public IPv4 could not be detected; set SERVER_PUBLIC_IP manually if DNS verification is needed"
  fi
}

ensure_dev_seed_password() {
  step "Prepare Core dev/admin seed password"

  local current=""
  if [[ -f "$DEV_SEED_ENV_FILE" ]]; then
    current="$(read_env_key "$DEV_SEED_ENV_FILE" DEV_USER_PASSWORD || true)"
  fi

  if [[ -n "$current" ]]; then
    REPORT_DEV_SEED="ready (existing root-only env preserved)"
    log "Preserving existing DEV_USER_PASSWORD in ${DEV_SEED_ENV_FILE}"
    return 0
  fi

  if ! is_interactive_setup; then
    REPORT_DEV_SEED="missing (deploy will require DEV_USER_PASSWORD)"
    warn "${DEV_SEED_ENV_FILE} has no DEV_USER_PASSWORD and interactive setup is disabled"
    return 0
  fi

  local password=""
  local confirm=""
  while true; do
    read -r -s -p "DEV admin şifresi (ekranda görünmez): " password
    echo ""
    if [[ ${#password} -lt 12 ]]; then
      echo "Şifre en az 12 karakter olmalı."
      continue
    fi
    read -r -s -p "DEV admin şifresini tekrar gir: " confirm
    echo ""
    if [[ "$password" != "$confirm" ]]; then
      echo "Şifreler eşleşmedi; tekrar deneyin."
      continue
    fi
    break
  done

  run_root mkdir -p "$(dirname "$DEV_SEED_ENV_FILE")"
  printf 'DEV_USER_PASSWORD=%s\n' "$password" | run_root tee "$DEV_SEED_ENV_FILE" >/dev/null
  run_root chown root:root "$DEV_SEED_ENV_FILE"
  run_root chmod 600 "$DEV_SEED_ENV_FILE"
  unset password confirm

  REPORT_DEV_SEED="ready (created interactively, chmod 600)"
  log "Created root-only dev seed env: ${DEV_SEED_ENV_FILE}"
}

ensure_fair_crm_checkout() {
  if [[ "${SKIP_REPO_CLONE:-0}" == "1" ]]; then
    REPORT_REPO="skipped (SKIP_REPO_CLONE=1)"
    return 0
  fi

  step "Ensure Fair CRM checkout at ${FAIR_CRM_DIR}"
  mkdir -p "$(dirname "$FAIR_CRM_DIR")"

  if [[ ! -d "${FAIR_CRM_DIR}/.git" ]]; then
    require_cmd git
    git clone --branch "$FAIR_CRM_BRANCH" "$FAIR_CRM_REPO" "$FAIR_CRM_DIR"
    REPORT_REPO="cloned (${FAIR_CRM_BRANCH})"
    return 0
  fi

  local repo_root
  repo_root="$(cd "${SCRIPT_DIR}/../.." && pwd)"
  if [[ "${FAIR_CRM_DIR}" != "${repo_root}" ]]; then
    ensure_git_ff_pull "$FAIR_CRM_DIR" "$FAIR_CRM_BRANCH" \
      "docker-compose.yml" \
      "backend/.env" \
      "frontend/.env" \
      "frontend/.env.production" \
      "backups" \
      "data/restore_uploads" \
      "data/restore_logs"
    REPORT_REPO="updated (${FAIR_CRM_BRANCH})"
  else
    log "Using current working tree at ${FAIR_CRM_DIR}"
    REPORT_REPO="using working tree"
  fi
}

prepare_env_files() {
  step "Prepare env files (never overwrite existing)"
  copy_env_if_missing "${FAIR_CRM_DIR}/backend/.env.example" "${FAIR_CRM_DIR}/backend/.env"
  copy_env_if_missing "${FAIR_CRM_DIR}/frontend/.env.example" "${FAIR_CRM_DIR}/frontend/.env"
  write_frontend_production_env_if_missing "$FAIR_CRM_DIR"

  if [[ -d "${KYROX_CORE_DIR}" ]]; then
    ensure_core_backend_env "$KYROX_CORE_DIR" || warn "Core backend/.env not created yet (run deploy-all after kyrox-core clone)"
  else
    warn "Core checkout not present yet at ${KYROX_CORE_DIR}; Core backend/.env is created on first deploy-all run"
  fi

  REPORT_ENV_FILES="checked (existing files preserved)"
}

configure_nginx_domain() {
  local site="/etc/nginx/sites-available/fair-crm"
  [[ -f "$site" ]] || return 0
  run_root sed -i -E "s/^[[:space:]]*server_name[[:space:]].*;/    server_name ${FAIR_CRM_DOMAIN};/" "$site"
  run_root nginx -t
  run_root systemctl reload nginx
}

resolve_domain_ipv4() {
  if command -v getent >/dev/null 2>&1; then
    getent ahostsv4 "$FAIR_CRM_DOMAIN" 2>/dev/null | awk 'NR == 1 {print $1}'
  fi
}

ensure_ssl() {
  if [[ "${SKIP_SSL:-0}" == "1" ]]; then
    REPORT_SSL="skipped (SKIP_SSL=1)"
    return 0
  fi

  step "Install Certbot and enable HTTPS for ${FAIR_CRM_DOMAIN}"
  run_root apt-get update -y
  run_root apt-get install -y certbot python3-certbot-nginx

  if command -v ufw >/dev/null 2>&1; then
    run_root ufw allow 443/tcp >/dev/null
  fi

  local dns_ip=""
  dns_ip="$(resolve_domain_ipv4 || true)"
  if [[ -z "$dns_ip" ]]; then
    REPORT_SSL="pending (DNS A record missing)"
    warn "DNS A kaydı bulunamadı: ${FAIR_CRM_DOMAIN}. A kaydını ${SERVER_PUBLIC_IP:-this server IP} adresine yönlendirip bootstrap'ı tekrar çalıştırın."
    return 0
  fi
  if [[ -n "$SERVER_PUBLIC_IP" && "$dns_ip" != "$SERVER_PUBLIC_IP" ]]; then
    REPORT_SSL="pending (DNS points to ${dns_ip}, server is ${SERVER_PUBLIC_IP})"
    warn "DNS henüz bu sunucuya bakmıyor: ${FAIR_CRM_DOMAIN} -> ${dns_ip}; beklenen ${SERVER_PUBLIC_IP}. DNS düzeldikten sonra bootstrap'ı tekrar çalıştırın."
    return 0
  fi

  local -a certbot_args=(
    certbot --nginx
    -d "${FAIR_CRM_DOMAIN}"
    --non-interactive
    --agree-tos
    --redirect
  )

  if [[ -n "$LETSENCRYPT_EMAIL" ]]; then
    certbot_args+=(--email "${LETSENCRYPT_EMAIL}")
  else
    certbot_args+=(--register-unsafely-without-email)
  fi

  if run_root "${certbot_args[@]}"; then
    REPORT_SSL="ready (https://${FAIR_CRM_DOMAIN})"
    run_root systemctl enable --now certbot.timer >/dev/null 2>&1 || true
  else
    REPORT_SSL="pending (certificate issuance failed; rerun after DNS points to this server)"
    warn "Let's Encrypt certificate could not be issued yet. Confirm DNS for ${FAIR_CRM_DOMAIN} points to this server, then rerun bootstrap."
  fi
}

print_bootstrap_report() {
  echo ""
  echo "========== BOOTSTRAP REPORT =========="
  echo "Failed step: ${DEPLOY_FAILED_STEP:-none}"
  echo "APT packages: ${REPORT_APT}"
  echo "Docker: ${REPORT_DOCKER}"
  echo "Node.js: ${REPORT_NODE}"
  echo "UFW firewall: ${REPORT_FIREWALL}"
  echo "Fair CRM repo: ${REPORT_REPO}"
  echo "Postgres container: ${REPORT_POSTGRES}"
  echo "Env files: ${REPORT_ENV_FILES}"
  echo "Dev/admin seed: ${REPORT_DEV_SEED}"
  echo "Nginx site: ${REPORT_NGINX}"
  echo "SSL: ${REPORT_SSL}"
  echo "FAIR_CRM_DOMAIN: ${FAIR_CRM_DOMAIN}"
  echo "SERVER_PUBLIC_IP: ${SERVER_PUBLIC_IP:-unknown}"
  echo "FAIR_CRM_DIR: ${FAIR_CRM_DIR}"
  echo "KYROX_CORE_DIR: ${KYROX_CORE_DIR}"
  echo ""
  echo "Next steps:"
  echo "  1) Review /opt/fair-crm/backend/.env (JWT, DATABASE_URL, KYROX_CORE_BASE_URL)"
  echo "  2) sudo bash ${FAIR_CRM_DIR}/scripts/server/deploy-all.sh"
  echo "  3) sudo bash ${FAIR_CRM_DIR}/scripts/server/check-server.sh"
  echo "======================================"
}

main() {
  step "Preflight"
  require_linux
  require_root_or_sudo
  resolve_deploy_service_user
  log "FAIR_CRM_DIR=${FAIR_CRM_DIR}"
  log "KYROX_CORE_DIR=${KYROX_CORE_DIR}"
  log "DEPLOY_SERVICE_USER=${DEPLOY_SERVICE_USER}"

  if [[ "${SKIP_APT:-0}" != "1" ]]; then
    install_apt_packages
    REPORT_APT="installed/verified"
  fi

  configure_interactive_settings
  ensure_dev_seed_password
  ensure_fair_crm_checkout

  if [[ "${SKIP_DOCKER:-0}" != "1" ]]; then
    ensure_docker
    REPORT_DOCKER="ready"
  fi

  if [[ "${SKIP_NODE:-0}" != "1" ]]; then
    ensure_nodejs
    REPORT_NODE="$(get_installed_node_version) (required >=${REQUIRED_NODEJS_VERSION})"
  fi

  prepare_env_files

  if [[ "${SKIP_POSTGRES:-0}" != "1" ]]; then
    ensure_compose_localhost_postgres_bind "$FAIR_CRM_DIR" || true
    ensure_postgres_container "$FAIR_CRM_DIR"
    REPORT_POSTGRES="started/verified (127.0.0.1:5432)"
  fi

  if [[ "${SKIP_NGINX:-0}" != "1" ]]; then
    install_nginx_site "${SCRIPT_DIR}/nginx/fair-crm.conf" "fair-crm"
    configure_nginx_domain
    REPORT_NGINX="installed/verified (${FAIR_CRM_DOMAIN})"
  fi

  if [[ "${SKIP_FIREWALL:-0}" != "1" ]]; then
    ensure_ufw_firewall
    if command -v ufw >/dev/null 2>&1; then
      run_root ufw allow 443/tcp >/dev/null
    fi
    REPORT_FIREWALL="configured (SSH + 80/tcp + 443/tcp)"
  fi

  if [[ "${SKIP_NGINX:-0}" != "1" ]]; then
    ensure_ssl
  fi

  print_bootstrap_report
}

trap 'if [[ $? -ne 0 ]]; then echo ""; print_bootstrap_report; fi' EXIT

main "$@"
