#!/usr/bin/env bash
# Run on the Pi from the repo root: bash deploy/install-service.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="$(whoami)"
SERVICE_NAME="camera"
TEMPLATE="$APP_DIR/deploy/camera.service"
TARGET="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ ! -x "$APP_DIR/venv/bin/uvicorn" ]]; then
  echo "Missing venv. On the Pi run: cd $APP_DIR && python3 -m venv venv --copies && source venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

if [[ ! -f "$APP_DIR/.env" ]]; then
  echo "Missing $APP_DIR/.env (OPENAI_API_KEY and SYSTEM_PROMPT)"
  exit 1
fi

echo "Installing systemd service for user $USER_NAME at $APP_DIR"
sed "s|__USER__|$USER_NAME|g; s|__APP_DIR__|$APP_DIR|g" "$TEMPLATE" | sudo tee "$TARGET" > /dev/null

sudo usermod -aG video "$USER_NAME" 2>/dev/null || true

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo ""
echo "Installed. Status:"
sudo systemctl status "$SERVICE_NAME" --no-pager || true
echo ""
echo "Phone URL: http://ryanhermespi.local:8000"
echo "Logs:      journalctl -u $SERVICE_NAME -f"
