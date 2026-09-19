#!/usr/bin/env bash
set -euo pipefail
# Pin systemd 8001 to this Fair CRM checkout instead of /opt/fair-crm.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$(cd "$SCRIPT_DIR/../.." && pwd)"
DROP="/etc/systemd/system/fair-crm-backend.service.d"
mkdir -p "$DROP"
cat > "$DROP/local-workspace.conf" <<EOF
# Local-dev override: 8001 serves the Kyrox workspace Fair CRM, not /opt/fair-crm.
[Service]
WorkingDirectory=$WS/backend
Environment=PYTHONPATH=$WS/backend
EnvironmentFile=-$WS/backend/.env
ExecStart=
ExecStart=/opt/fair-crm/backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
EOF
systemctl daemon-reload
systemctl enable fair-crm-backend.service
systemctl restart fair-crm-backend.service
sleep 2
systemctl is-enabled fair-crm-backend.service
systemctl is-active fair-crm-backend.service
echo "---drop-in---"
cat "$DROP/local-workspace.conf"
echo "---show---"
systemctl show fair-crm-backend.service -p WorkingDirectory -p EnvironmentFiles -p Environment -p FragmentPath -p DropInPaths
systemctl show fair-crm-backend.service -p ExecStart
PID="$(systemctl show -p MainPID --value fair-crm-backend.service)"
echo "PID=$PID"
readlink -f "/proc/${PID}/cwd" || true
tr '\0' '\n' < "/proc/${PID}/environ" | grep -E '^(PYTHONPATH|PWD)=' || true
ss -ltnp | grep 8001 || true
