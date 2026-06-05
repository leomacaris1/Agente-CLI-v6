#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/leoprojects/agent-cli-v4-fresh}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "Installing system packages..."
sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip

echo "Creating app directory..."
sudo mkdir -p "$(dirname "$APP_DIR")"
sudo chown -R "$USER":"$USER" "$(dirname "$APP_DIR")"

if [ ! -d "$APP_DIR/.git" ]; then
  echo "Clone your repository into $APP_DIR before continuing."
  echo "Example: git clone <repo-url> $APP_DIR"
  exit 1
fi

cd "$APP_DIR"

echo "Creating virtual environment..."
"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
  echo "Creating .env from .env.example..."
  cp .env.example .env
  echo "Edit $APP_DIR/.env before starting services."
fi

echo "Bootstrap complete."
echo "Next:"
echo "  sudo cp deploy/systemd/agent-daemon.service /etc/systemd/system/"
echo "  sudo cp deploy/systemd/agent-telegram.service /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
