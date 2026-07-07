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
#   sudo git clone -b feat/dev-auto-start-v1 https://github.com/hinthorozu/fair-crm.git /opt/fair-crm
#   sudo bash /opt/fair-crm/scripts/server/bootstrap-server.sh
#   sudo nano /opt/fair-crm/backend/.env
#   sudo bash /opt/fair-crm/scripts/server/deploy-all.sh
#   sudo bash /opt/fair-crm/scripts/server/check-server.sh
#
# Optional environment overrides:
#   FAIR_CRM_DIR=/opt/fair-crm
#   FAIR_CRM_REPO=https://github.com/hinthorozu/fair-crm.git
#   FAIR_CRM_BRANCH=feat/dev-auto-start-v1
#   KYROX_CORE_DIR=/opt/kyrox-core
#   DEPLOY_SERVICE_USER=ubuntu
#   SERVER_PUBLIC_URL=http://203.0.113.10
#   SKIP_APT=1
#   SKIP_DOCKER=1
#   SKIP_NODE=1
#   SKIP_NGINX=1
#   SKIP_FIREWALL=1
#   SKIP_REPO_CLONE=1
#   SKIP_POSTGRES=1
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

FAIR_CRM_DIR="${FAIR_CRM_DIR:-/opt/fair-crm}"
KYROX_CORE_DIR="${KYROX_CORE_DIR:-/opt/kyrox-core}"
FAIR_CRM_REPO="${FAIR_CRM_REPO:-https://github.com/hinthorozu/fair-crm.git}"
FAIR_CRM_BRANCH="${FAIR_CRM_BRANCH:-feat/dev-auto-start-v1}"
DEPLOY_SERVICE_USER="${DEPLOY_SERVICE_USER:-${SUDO_USER:-$(id -un)}}"
SERVER_PUBLIC_URL="${SERVER_PUBLIC_URL:-$(detect_server_public_url)}"

REPORT_APT="skipped"
REPORT_DOCKER="skipped"
REPORT_NODE="skipped"
REPORT_FIREWALL="skipped"
REPORT_NGINX="skipped"
REPORT_REPO="skipped"
REPORT_POSTGRES="skipped"
REPORT_ENV_FILES="not checked"

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

  if [[ -d "${KYROX_CORE_DIR}/backend" ]]; then
    copy_env_if_missing "${KYROX_CORE_DIR}/backend/.env.example" "${KYROX_CORE_DIR}/backend/.env"
    copy_env_if_missing "${KYROX_CORE_DIR}/.env.example" "${KYROX_CORE_DIR}/.env"
  else
    warn "Core checkout not present yet at ${KYROX_CORE_DIR}; Core .env is created on first deploy-all run"
  fi

  REPORT_ENV_FILES="checked (existing files preserved)"
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
  echo "Nginx site: ${REPORT_NGINX}"
  echo "FAIR_CRM_DIR: ${FAIR_CRM_DIR}"
  echo "KYROX_CORE_DIR: ${KYROX_CORE_DIR}"
  echo "SERVER_PUBLIC_URL: ${SERVER_PUBLIC_URL}"
  echo ""
  echo "Next steps:"
  echo "  1) Edit /opt/fair-crm/backend/.env (JWT, DATABASE_URL, KYROX_CORE_BASE_URL)"
  echo "  2) sudo bash ${FAIR_CRM_DIR}/scripts/server/deploy-all.sh"
  echo "  3) sudo bash ${FAIR_CRM_DIR}/scripts/server/check-server.sh"
  echo "======================================"
}

main() {
  step "Preflight"
  require_linux
  require_root_or_sudo
  log "FAIR_CRM_DIR=${FAIR_CRM_DIR}"
  log "KYROX_CORE_DIR=${KYROX_CORE_DIR}"
  log "DEPLOY_SERVICE_USER=${DEPLOY_SERVICE_USER}"
  log "SERVER_PUBLIC_URL=${SERVER_PUBLIC_URL}"

  if [[ "${SKIP_APT:-0}" != "1" ]]; then
    install_apt_packages
    REPORT_APT="installed/verified"
  fi

  ensure_fair_crm_checkout

  if [[ "${SKIP_DOCKER:-0}" != "1" ]]; then
    ensure_docker
    REPORT_DOCKER="ready"
  fi

  if [[ "${SKIP_NODE:-0}" != "1" ]]; then
    ensure_nodejs
    REPORT_NODE="ready"
  fi

  prepare_env_files

  if [[ "${SKIP_POSTGRES:-0}" != "1" ]]; then
    ensure_compose_localhost_postgres_bind "$FAIR_CRM_DIR" || true
    ensure_postgres_container "$FAIR_CRM_DIR"
    REPORT_POSTGRES="started/verified (127.0.0.1:5432)"
  fi

  if [[ "${SKIP_NGINX:-0}" != "1" ]]; then
    install_nginx_site "${SCRIPT_DIR}/nginx/fair-crm.conf" "fair-crm"
    REPORT_NGINX="installed/verified"
  fi

  if [[ "${SKIP_FIREWALL:-0}" != "1" ]]; then
    ensure_ufw_firewall
    REPORT_FIREWALL="configured"
  fi

  print_bootstrap_report
}

trap 'if [[ $? -ne 0 ]]; then echo ""; print_bootstrap_report; fi' EXIT

main "$@"
