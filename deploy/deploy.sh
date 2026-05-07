#!/usr/bin/env bash
# Deploy the latest main branch to the running EC2 instance.
# Idempotent — safe to re-run. Invoked by the GitHub Actions workflow.
#
# Pre-conditions: deploy/install.sh has been run once on this host.

set -euo pipefail

APP_DIR="/opt/tsa-kpi"
cd "${APP_DIR}"

echo "[deploy] Fetching latest..."
git fetch --quiet origin main
git reset --hard origin/main

echo "[deploy] Updating Python deps..."
"${APP_DIR}/.venv/bin/pip" install --quiet -r scripts/kpi/requirements.txt

echo "[deploy] Re-installing systemd units (in case they changed)..."
sudo cp "${APP_DIR}/deploy/tsa-kpi.service"         /etc/systemd/system/
sudo cp "${APP_DIR}/deploy/tsa-kpi-refresh.service" /etc/systemd/system/
sudo cp "${APP_DIR}/deploy/tsa-kpi-refresh.timer"   /etc/systemd/system/
sudo cp "${APP_DIR}/deploy/nginx.conf"              /etc/nginx/conf.d/tsa-kpi.conf
sudo systemctl daemon-reload
sudo nginx -t
sudo systemctl reload nginx

echo "[deploy] Restarting HTTP server..."
sudo systemctl restart tsa-kpi.service

echo "[deploy] Triggering one-shot rebuild..."
sudo systemctl start tsa-kpi-refresh.service || echo "[deploy] (refresh failed — likely missing LINEAR_API_KEY; HTTP server is still serving last known build)"

echo "[deploy] Done."
