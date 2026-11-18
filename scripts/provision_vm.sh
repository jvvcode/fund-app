#!/usr/bin/env bash
set -euo pipefail
sudo apt-get update && sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
echo "Docker installed. Log out/in, then: git clone <repo> && cd fund-app && docker compose up -d"
