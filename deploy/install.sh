#!/usr/bin/env bash
# One-time bootstrap of the TSA KPI Dashboard on a fresh Amazon Linux 2023 EC2.
# Run as ec2-user (the script will sudo where needed).
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/thiagotbx123/tsa-kpi-dashboard/main/deploy/install.sh | bash
#   # or after cloning:
#   bash /opt/tsa-kpi/deploy/install.sh

set -euo pipefail

REPO_URL="https://github.com/thiagotbx123/tsa-kpi-dashboard.git"
APP_DIR="/opt/tsa-kpi"
OUTPUT_DIR="${APP_DIR}/output"
APP_USER="ec2-user"

echo "==> [1/7] Installing system packages (git, python3, nginx)..."
sudo dnf install -y git python3 python3-pip nginx >/dev/null

echo "==> [2/7] Cloning repo to ${APP_DIR}..."
if [ ! -d "${APP_DIR}/.git" ]; then
    sudo git clone "${REPO_URL}" "${APP_DIR}"
fi
sudo chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

echo "==> [3/7] Creating Python venv + installing deps..."
sudo -u "${APP_USER}" python3 -m venv "${APP_DIR}/.venv"
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install --quiet --upgrade pip
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install --quiet -r "${APP_DIR}/scripts/kpi/requirements.txt"

echo "==> [4/7] Creating output dir..."
sudo -u "${APP_USER}" mkdir -p "${OUTPUT_DIR}"

echo "==> [5/7] Installing systemd units..."
sudo cp "${APP_DIR}/deploy/tsa-kpi.service"         /etc/systemd/system/
sudo cp "${APP_DIR}/deploy/tsa-kpi-refresh.service" /etc/systemd/system/
sudo cp "${APP_DIR}/deploy/tsa-kpi-refresh.timer"   /etc/systemd/system/
sudo systemctl daemon-reload

echo "==> [6/7] Installing nginx config..."
sudo cp "${APP_DIR}/deploy/nginx.conf" /etc/nginx/conf.d/tsa-kpi.conf
# Disable default server block to avoid conflict.
sudo sed -i 's/^\(\s*listen\s*\(80\|\[::\]:80\)\s*\)default_server;/\1;/' /etc/nginx/nginx.conf || true
sudo nginx -t
sudo systemctl enable --now nginx

echo "==> [7/7] Building initial dashboard from cached data (--build-only)..."
sudo -u "${APP_USER}" bash -c "cd '${APP_DIR}' && KPI_OUTPUT_DIR='${OUTPUT_DIR}' '${APP_DIR}/.venv/bin/python' scripts/kpi/orchestrate.py --build-only"

cat <<EOF

============================================
 Bootstrap complete.

 NEXT STEPS:
 1. Add LINEAR_API_KEY to ${APP_DIR}/.env:
      sudo -u ${APP_USER} tee ${APP_DIR}/.env <<'ENV'
      LINEAR_API_KEY=lin_api_xxxxxxxxxxxx
      ENV
      sudo chmod 600 ${APP_DIR}/.env

 2. Enable services:
      sudo systemctl enable --now tsa-kpi.service
      sudo systemctl enable --now tsa-kpi-refresh.timer

 3. Verify:
      sudo systemctl status tsa-kpi.service
      sudo systemctl list-timers tsa-kpi-refresh.timer
      curl -I http://localhost/KPI_DASHBOARD.html

 4. Open dashboard:
      http://<ec2-public-ip>/KPI_DASHBOARD.html
============================================
EOF
