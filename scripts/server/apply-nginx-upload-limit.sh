#!/usr/bin/env bash
set -euo pipefail

SITE="${NGINX_FAIR_CRM_SITE:-/etc/nginx/sites-available/fair-crm}"
LIMIT="${FAIR_CRM_NGINX_UPLOAD_LIMIT:-256m}"

[[ -f "$SITE" ]] || exit 0

if grep -Eq '^[[:space:]]*client_max_body_size[[:space:]]+' "$SITE"; then
  sed -i -E "s|^[[:space:]]*client_max_body_size[[:space:]]+[^;]+;|    client_max_body_size ${LIMIT};|" "$SITE"
else
  sed -i -E "/^[[:space:]]*server_name[[:space:]].*;/a\\
    client_max_body_size ${LIMIT};" "$SITE"
fi
