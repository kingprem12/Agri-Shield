#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <ec2-user@host> <repo-url>"
  exit 1
fi

EC2_TARGET="$1"
REPO_URL="$2"

ssh "$EC2_TARGET" "sudo mkdir -p /opt/agrishield-ai && sudo chown \$USER:\$USER /opt/agrishield-ai"
ssh "$EC2_TARGET" "if [ ! -d /opt/agrishield-ai/.git ]; then git clone $REPO_URL /opt/agrishield-ai; fi"
ssh "$EC2_TARGET" "cd /opt/agrishield-ai && git pull && docker compose up -d --build postgres backend"

