#!/usr/bin/env bash
# Patch the live nginx site in place (do not replace the file: certbot SSL stays).
# - client_max_body_size for backup/restore uploads
# - /api/v1/fair-stand/ -> 127.0.0.1:8002 ahead of /api/ -> 8001
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

python3 - "$SITE" <<'PY'
from pathlib import Path
import sys

site = Path(sys.argv[1])
text = site.read_text(encoding="utf-8")
block = """    location ^~ /api/v1/fair-stand/ {
        proxy_pass http://127.0.0.1:8002;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

"""
marker = "location /api/"
needle = "location ^~ /api/v1/fair-stand/"

def patch_server(body: str) -> str:
    if marker not in body or needle in body:
        return body
    idx = body.find(marker)
    line_start = body.rfind("\n", 0, idx) + 1
    indent = body[line_start:idx]
    insertion = "\n".join(
        (indent + line[4:] if line.startswith("    ") else indent + line)
        for line in block.splitlines()
    ) + "\n\n"
    return body[:line_start] + insertion + body[line_start:]

out = []
rest = text
while True:
    start = rest.find("server")
    if start < 0:
        out.append(rest)
        break
    brace = rest.find("{", start)
    if brace < 0:
        out.append(rest)
        break
    out.append(rest[: brace + 1])
    depth = 1
    i = brace + 1
    while i < len(rest) and depth:
        if rest[i] == "{":
            depth += 1
        elif rest[i] == "}":
            depth -= 1
        i += 1
    out.append(patch_server(rest[brace + 1 : i - 1]))
    out.append("}")
    rest = rest[i:]

patched = "".join(out)
if patched != text:
    site.write_text(patched, encoding="utf-8")
PY
