#!/usr/bin/env bash
# Patch the live nginx site in place (do not replace the file: certbot SSL stays).
# - client_max_body_size for backup/restore uploads
# - /api/v1/fair-stand/ -> 127.0.0.1:8002 ahead of /api/ -> 8001
# - /api/v1/fair-stand/live-shares upgrades WebSocket without a trailing-slash redirect
# A failed nginx -t restores the previous site file.
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

BACKUP="$(mktemp)"
cp "$SITE" "$BACKUP"

python3 - "$SITE" <<'PY'
import re
import sys
from pathlib import Path

site = Path(sys.argv[1])
text = site.read_text(encoding="utf-8")
original = text
map_block = """map $http_upgrade $fair_stand_connection_upgrade {
    default upgrade;
    ''      close;
}

"""
live_block = """    location ^~ /api/v1/fair-stand/live-shares {
        proxy_pass http://127.0.0.1:8002;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $fair_stand_connection_upgrade;
        proxy_buffering off;
        proxy_read_timeout 120s;
    }

"""
stand_block = """    location ^~ /api/v1/fair-stand/ {
        proxy_pass http://127.0.0.1:8002;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

"""

def drop_locations(body: str, token: str) -> str:
    lines = body.splitlines(keepends=True)
    out = []
    index = 0
    while index < len(lines):
        stripped = lines[index].lstrip()
        if stripped.startswith("location") and token in stripped:
            depth = lines[index].count("{") - lines[index].count("}")
            index += 1
            while index < len(lines) and depth > 0:
                depth += lines[index].count("{") - lines[index].count("}")
                index += 1
            if index < len(lines) and lines[index].strip() == "":
                index += 1
            continue
        out.append(lines[index])
        index += 1
    return "".join(out)

def insert_before(body: str, predicate, block_text: str) -> str:
    lines = body.splitlines(keepends=True)
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if not predicate(stripped):
            continue
        indent = line[: len(line) - len(stripped)]
        piece = "".join(
            indent + part[4:] if part.startswith("    ") else indent + part
            for part in block_text.strip("\n").splitlines(keepends=True)
        )
        if not piece.endswith("\n"):
            piece += "\n"
        piece += "\n"
        return "".join(lines[:index]) + piece + "".join(lines[index:])
    return body

def is_stand_location(stripped: str) -> bool:
    return stripped.startswith("location ^~ /api/v1/fair-stand/") and "live-shares" not in stripped

def is_api_location(stripped: str) -> bool:
    return stripped.startswith("location /api/") or stripped.startswith("location /api {")

def patch_server(body: str) -> str:
    had_stand = any(is_stand_location(line.lstrip()) for line in body.splitlines())
    had_api = any(is_api_location(line.lstrip()) for line in body.splitlines())
    if not had_stand and not had_api:
        return body
    body = drop_locations(body, "/api/v1/fair-stand/live-shares")
    if had_stand or had_api:
        anchor = is_stand_location if had_stand else is_api_location
        body = insert_before(body, anchor, live_block)
    if not had_stand and had_api:
        body = insert_before(body, is_api_location, stand_block)
    return body

def split_servers(src: str):
    matches = list(re.finditer(r"^[ \t]*server[ \t]*\{", src, re.M))
    if not matches:
        return src, []
    chunks = []
    cursor = 0
    for match in matches:
        brace = match.end() - 1
        depth = 1
        index = brace + 1
        while index < len(src) and depth:
            if src[index] == "{":
                depth += 1
            elif src[index] == "}":
                depth -= 1
            index += 1
        chunks.append((src[cursor:brace + 1], src[brace + 1:index - 1], src[index - 1:index]))
        cursor = index
    return src[cursor:], chunks

if "map $http_upgrade $fair_stand_connection_upgrade" not in text:
    text = map_block + text

tail, servers = split_servers(text)
rebuilt = []
for prefix, body, closer in servers:
    rebuilt.append(prefix)
    rebuilt.append(patch_server(body))
    rebuilt.append(closer)
rebuilt.append(tail)
patched = "".join(rebuilt)
if patched != original:
    site.write_text(patched, encoding="utf-8")
PY

if command -v nginx >/dev/null 2>&1; then
  if ! nginx -t >/dev/null 2>&1; then
    cp "$BACKUP" "$SITE"
    echo "nginx live-share patch failed nginx -t; previous site restored" >&2
  fi
fi
rm -f "$BACKUP"
