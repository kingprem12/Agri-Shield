#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <domain> <email>"
  exit 1
fi

DOMAIN="$1"
EMAIL="$2"
sudo sed "s/api.example.com/$DOMAIN/g" infrastructure/nginx/agrishield.conf | sudo tee /etc/nginx/sites-available/agrishield
sudo ln -sf /etc/nginx/sites-available/agrishield /etc/nginx/sites-enabled/agrishield
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL"

