#!/usr/bin/env bash
# Deploy from your Mac: ./deploy/deploy.sh
# Optional: PI_HOST=10.0.0.140 INSTALL_DEPS=1 ./deploy/deploy.sh
set -euo pipefail

PI_USER="${PI_USER:-ryanhermes}"
PI_HOST="${PI_HOST:-ryanhermespi.local}"
PI_DIR="${PI_DIR:-Camera}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "→ Syncing to ${PI_USER}@${PI_HOST}:~/${PI_DIR}/"
rsync -av \
  --exclude venv \
  --exclude __pycache__ \
  --exclude .env \
  --exclude .git \
  "${REPO_ROOT}/" "${PI_USER}@${PI_HOST}:~/${PI_DIR}/"

if [[ "${INSTALL_DEPS:-}" == "1" ]]; then
  echo "→ Installing Python deps on Pi"
  ssh "${PI_USER}@${PI_HOST}" "cd ~/${PI_DIR} && source venv/bin/activate && pip install -r requirements.txt"
fi

echo "→ Restarting camera service"
if [[ -t 0 ]]; then
  ssh -t "${PI_USER}@${PI_HOST}" "sudo systemctl restart camera"
else
  ssh "${PI_USER}@${PI_HOST}" "sudo systemctl restart camera"
fi

echo "Done. http://${PI_HOST}:8000"
