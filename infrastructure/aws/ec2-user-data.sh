#!/usr/bin/env bash
set -euo pipefail

apt-get update
apt-get install -y docker.io docker-compose-plugin nginx certbot python3-certbot-nginx git
systemctl enable --now docker nginx
usermod -aG docker ubuntu
mkdir -p /opt/agrishield-ai

