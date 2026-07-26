#!/usr/bin/env bash
#
# Configure FAIR CRM public domain + Nginx + UFW 80/443 + Let's Encrypt SSL.
#
# Run after bootstrap-server.sh and application deploy are complete.
#
# Usage:
#   sudo bash /opt/fair-crm/scripts/server/setup-domain-ssl.sh \
#     --domain faircrm.umaay.com \
#     --email admin@umaay.com
#
# Optional:
#   --server-ip 64.226.110.223
#   --fair-crm-dir /opt/fair-crm
#   --skip-renewal-dry-run
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

DOMAIN="${DOMAIN:-}"
ADMIN_EMAIL="${ADMIN_EMAIL:-}"
SERVER_PUBLIC_IP="${SERVER_PUBLIC_IP:-}"
FAIR_CRM_DIR="${FAIR_CRM_DIR:-/opt/fair-crm}"
NGINX_SITE_NAME="${NGINX_SITE_NAME:-fair-crm}"
SKIP_RENEWAL_DRY_RUN="${SKIP_RENEWAL_DRY_RUN:-0}"

NGINX_AVAILABLE="/etc/nginx/sites-available/${NGINX_SITE_NAME}"
NGINX_ENABLED="/etc/nginx/sites-enabled/${NGINX_SITE_NAME}"
NGINX_BACKUP=""

REPORT_DNS="not checked"
REPORT_SERVICES="not checked"
REPORT_NGINX="not checked"
REPORT_FIREWALL="not checked"
REPORT_SSL="not checked"
REPORT_RENEWAL="not checked"
REPORT_HTTPS="not checked"

usage() {
  cat <<'USAGE'
Usage:
  sudo bash scripts/server/setup-domain-ssl.sh --domain <domain> --email <admin-email> [options]

Required:
  --domain <domain>             Public domain, e.g. faircrm.umaay.com
  --email <admin-email>        Let's Encrypt notification email

Optional:
  --server-ip <ipv4>           Expected server public IPv4. Auto-detected if omitted.
  --fair-crm-dir <path>        FAIR CRM checkout. Default: /opt/fair-crm
  --skip-renewal-dry-run       Skip `certbot renew --dry-run`
  -h, --help                   Show this help

Environment equivalents:
  DOMAIN, ADMIN_EMAIL, SERVER_PUBLIC_IP, FAIR_CRM_DIR,
  NGINX_SITE_NAME, SKIP_RENEWAL_DRY_RUN
USAGE
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --domain)
        [[ $# -ge 2 ]] || die "--domain requires a value"
        DOMAIN="$2"
        shift 2
        ;;
      --email)
        [[ $# -ge 2 ]] || die "--email requires a value"
        ADMIN_EMAIL="$2"
        shift 2
        ;;
      --server-ip)
        [[ $# -ge 2 ]] || die "--server-ip requires a value"
        SERVER_PUBLIC_IP="$2"
        shift 2
        ;;
      --fair-crm-dir)
        [[ $# -ge 2 ]] || die "--fair-crm-dir requires a value"
        FAIR_CRM_DIR="$2"
        shift 2
        ;;
      --skip-renewal-dry-run)
        SKIP_RENEWAL_DRY_RUN=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Unknown argument: $1"
        ;;
    esac
  done
}

validate_inputs() {
  [[ -n "$DOMAIN" ]] || die "--domain is required"
  [[ -n "$ADMIN_EMAIL" ]] || die "--email is required"

  if [[ ! "$DOMAIN" =~ ^([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$ ]]; then
    die "Invalid domain: ${DOMAIN}"
  fi
  if [[ ! "$ADMIN_EMAIL" =~ ^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$ ]]; then
    die "Invalid admin email: ${ADMIN_EMAIL}"
  fi
  if [[ -n "$SERVER_PUBLIC_IP" && ! "$SERVER_PUBLIC_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
    die "Invalid --server-ip IPv4: ${SERVER_PUBLIC_IP}"
  fi
}

detect_public_ipv4() {
  if [[ -n "$SERVER_PUBLIC_IP" ]]; then
    printf '%s' "$SERVER_PUBLIC_IP"
    return 0
  fi

  local detected
  detected="$(curl -4fsS --connect-timeout 5 --max-time 10 https://api.ipify.org 2>/dev/null || true)"
  if [[ ! "$detected" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
    die "Could not auto-detect server public IPv4. Re-run with --server-ip <IPv4>."
  fi
  printf '%s' "$detected"
}

resolve_domain_ipv4s() {
  getent ahostsv4 "$DOMAIN" 2>/dev/null \
    | awk '{print $1}' \
    | grep -E '^([0-9]{1,3}\.){3}[0-9]{1,3}$' \
    | sort -u
}

check_dns_points_here() {
  step "Check DNS points to this server"
  SERVER_PUBLIC_IP="$(detect_public_ipv4)"

  local resolved
  resolved="$(resolve_domain_ipv4s || true)"
  [[ -n "$resolved" ]] || die "${DOMAIN} has no IPv4 DNS result yet"

  if ! grep -Fxq "$SERVER_PUBLIC_IP" <<<"$resolved"; then
    die "DNS mismatch: ${DOMAIN} resolves to [$(paste -sd ',' <<<"$resolved")], server public IP is ${SERVER_PUBLIC_IP}"
  fi

  REPORT_DNS="OK (${DOMAIN} -> ${SERVER_PUBLIC_IP})"
  log "$REPORT_DNS"
}

check_local_services() {
  step "Check FAIR CRM services and frontend build"

  [[ -f "${FAIR_CRM_DIR}/frontend/dist/index.html" ]] \
    || die "Frontend build missing: ${FAIR_CRM_DIR}/frontend/dist/index.html"

  is_port_listening 8001 127.0.0.1 \
    || die "FAIR CRM backend is not listening on port 8001"
  is_port_listening 8000 127.0.0.1 \
    || die "KYROX Core is not listening on port 8000"

  REPORT_SERVICES="OK (frontend + 8001 + 8000)"
  log "$REPORT_SERVICES"
}

ensure_nginx_site_exists() {
  if [[ -f "$NGINX_AVAILABLE" ]]; then
    return 0
  fi

  local template="${SCRIPT_DIR}/nginx/fair-crm.conf"
  [[ -f "$template" ]] || die "Nginx site missing and template not found: ${template}"
  install_nginx_site "$template" "$NGINX_SITE_NAME"
}

backup_nginx_config() {
  local stamp
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  NGINX_BACKUP="${NGINX_AVAILABLE}.backup.${stamp}"
  run_root cp "$NGINX_AVAILABLE" "$NGINX_BACKUP"
  log "Nginx backup: ${NGINX_BACKUP}"
}

restore_nginx_backup() {
  [[ -n "$NGINX_BACKUP" && -f "$NGINX_BACKUP" ]] || return 0
  warn "Restoring Nginx config from ${NGINX_BACKUP}"
  run_root cp "$NGINX_BACKUP" "$NGINX_AVAILABLE"
  run_root nginx -t
  run_root systemctl reload nginx
}

configure_nginx_domain() {
  step "Configure Nginx server_name"
  ensure_nginx_site_exists
  backup_nginx_config

  if grep -Eq "^[[:space:]]*server_name[[:space:]]+${DOMAIN//./\\.}([[:space:]]|;).*" "$NGINX_AVAILABLE"; then
    log "Nginx server_name already contains ${DOMAIN}"
  else
    local tmp
    tmp="$(mktemp)"
    sed -E "0,/^[[:space:]]*server_name[[:space:]]+[^;]+;/s//    server_name ${DOMAIN};/" \
      "$NGINX_AVAILABLE" >"$tmp"

    if cmp -s "$NGINX_AVAILABLE" "$tmp"; then
      rm -f "$tmp"
      die "Could not find a server_name directive in ${NGINX_AVAILABLE}"
    fi

    run_root cp "$tmp" "$NGINX_AVAILABLE"
    run_root chmod 644 "$NGINX_AVAILABLE"
    rm -f "$tmp"
  fi

  if [[ ! -L "$NGINX_ENABLED" ]]; then
    run_root ln -sf "$NGINX_AVAILABLE" "$NGINX_ENABLED"
  fi

  if ! run_root nginx -t; then
    restore_nginx_backup
    die "Nginx config failed after domain update; backup restored"
  fi

  run_root systemctl enable nginx >/dev/null
  run_root systemctl reload nginx
  REPORT_NGINX="OK (server_name=${DOMAIN})"
}

configure_firewall() {
  step "Configure UFW ports 80/443"

  if ! command -v ufw >/dev/null 2>&1; then
    require_cmd apt-get
    run_root apt-get update -qq
    run_root apt-get install -y -qq ufw
  fi

  run_root ufw allow OpenSSH >/dev/null
  run_root ufw allow 80/tcp comment 'Fair CRM HTTP' >/dev/null
  run_root ufw allow 443/tcp comment 'Fair CRM HTTPS' >/dev/null

  if run_root ufw status 2>/dev/null | grep -q "Status: inactive"; then
    run_root ufw --force enable >/dev/null
  fi

  local status
  status="$(run_root ufw status 2>/dev/null || true)"
  grep -E '80/tcp.*ALLOW|80 .*ALLOW' <<<"$status" >/dev/null \
    || die "UFW port 80 rule is missing"
  grep -E '443/tcp.*ALLOW|443 .*ALLOW' <<<"$status" >/dev/null \
    || die "UFW port 443 rule is missing"

  REPORT_FIREWALL="OK (80/tcp + 443/tcp)"
}

http_code() {
  local url="$1"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' \
    --connect-timeout 5 --max-time 20 "$url" 2>/dev/null || true)"
  if [[ ! "$code" =~ ^[0-9]{3}$ ]]; then
    code="000"
  fi
  printf '%s' "$code"
}

require_http_ready() {
  step "Check public HTTP before Certbot"
  local code
  code="$(http_code "http://${DOMAIN}/")"
  if [[ "$code" == "000" || "$code" -ge 400 ]]; then
    die "HTTP check failed for http://${DOMAIN}/ (status=${code}); Certbot will not run"
  fi
  log "HTTP ready: http://${DOMAIN}/ -> ${code}"
}

ensure_certbot() {
  step "Ensure Certbot + Nginx plugin"
  if command -v certbot >/dev/null 2>&1; then
    log "Certbot already installed: $(certbot --version 2>/dev/null || true)"
    return 0
  fi

  require_cmd apt-get
  run_root apt-get update -qq
  run_root apt-get install -y -qq certbot python3-certbot-nginx
  require_cmd certbot
}

certificate_is_valid() {
  local cert="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
  [[ -f "$cert" ]] || return 1
  run_root openssl x509 -checkend 86400 -noout -in "$cert" >/dev/null 2>&1
}

nginx_uses_domain_certificate() {
  grep -Fq "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" "$NGINX_AVAILABLE" 2>/dev/null
}

ensure_ssl_certificate() {
  step "Ensure Let's Encrypt SSL certificate"

  if certificate_is_valid && nginx_uses_domain_certificate; then
    REPORT_SSL="OK (existing valid certificate preserved)"
    log "$REPORT_SSL"
    return 0
  fi

  run_root certbot --nginx \
    -d "$DOMAIN" \
    --non-interactive \
    --agree-tos \
    --email "$ADMIN_EMAIL" \
    --redirect

  run_root nginx -t
  run_root systemctl reload nginx

  certificate_is_valid || die "Certificate was not created or is not valid for at least 24 hours"
  REPORT_SSL="OK (Let's Encrypt certificate installed)"
}

configure_auto_renewal() {
  step "Enable Certbot automatic renewal"
  run_root systemctl enable --now certbot.timer >/dev/null
  run_root systemctl is-active --quiet certbot.timer \
    || die "certbot.timer is not active"

  if [[ "$SKIP_RENEWAL_DRY_RUN" == "1" ]]; then
    REPORT_RENEWAL="OK (timer active; dry-run skipped)"
    log "$REPORT_RENEWAL"
    return 0
  fi

  run_root certbot renew --dry-run
  REPORT_RENEWAL="OK (timer active + dry-run passed)"
}

require_routed_url() {
  local label="$1"
  local url="$2"
  local code
  code="$(http_code "$url")"

  if [[ "$code" == "000" || "$code" -ge 500 ]]; then
    die "${label} failed: ${url} -> ${code}"
  fi
  log "${label}: ${url} -> ${code}"
}

final_https_checks() {
  step "Final HTTPS checks"

  local root_code
  root_code="$(http_code "https://${DOMAIN}/")"
  if [[ "$root_code" == "000" || "$root_code" -ge 400 ]]; then
    die "HTTPS root failed: https://${DOMAIN}/ -> ${root_code}"
  fi

  require_routed_url "Public API route" "https://${DOMAIN}/api/"
  require_routed_url "Public KYROX Core route" "https://${DOMAIN}/kyrox-core/"

  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | grep -Eq '(:|\])443[[:space:]]' \
      || die "Nginx is not listening on port 443"
  fi

  REPORT_HTTPS="OK (HTTPS + routes)"
}

print_report() {
  echo ""
  echo "========== DOMAIN + SSL REPORT =========="
  echo "Failed step: ${DEPLOY_FAILED_STEP:-none}"
  echo "Domain: ${DOMAIN:-n/a}"
  echo "Server public IP: ${SERVER_PUBLIC_IP:-n/a}"
  echo "DNS: ${REPORT_DNS}"
  echo "Services: ${REPORT_SERVICES}"
  echo "Nginx: ${REPORT_NGINX}"
  echo "Firewall: ${REPORT_FIREWALL}"
  echo "SSL: ${REPORT_SSL}"
  echo "Renewal: ${REPORT_RENEWAL}"
  echo "HTTPS: ${REPORT_HTTPS}"
  [[ -n "$NGINX_BACKUP" ]] && echo "Nginx backup: ${NGINX_BACKUP}"
  echo "========================================="
}

main() {
  parse_args "$@"

  step "Preflight"
  require_linux
  require_root_or_sudo
  validate_inputs
  require_cmd curl
  require_cmd getent
  require_cmd awk
  require_cmd grep
  require_cmd sed
  require_cmd sort
  require_cmd nginx
  require_cmd systemctl
  require_cmd openssl

  check_dns_points_here
  check_local_services
  configure_nginx_domain
  configure_firewall
  require_http_ready
  ensure_certbot
  ensure_ssl_certificate
  configure_auto_renewal

  step "Final Nginx validation"
  run_root nginx -t
  run_root systemctl reload nginx
  final_https_checks

  print_report
}

trap 'rc=$?; if [[ $rc -ne 0 ]]; then echo ""; print_report; fi' EXIT

main "$@"
