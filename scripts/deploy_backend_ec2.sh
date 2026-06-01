#!/usr/bin/env bash
set -euo pipefail

required_vars=(EC2_HOST SSH_KEY_PATH REPO_URL POSTGRES_PASSWORD)
for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required environment variable: ${var_name}" >&2
    exit 1
  fi
done

EC2_USER="${EC2_USER:-ec2-user}"
BRANCH="${BRANCH:-safe-terraform-deployment}"
REMOTE_APP_DIR="${REMOTE_APP_DIR:-/opt/agrishield-x}"
CORS_ORIGINS="${CORS_ORIGINS:-[\"*\"]}"
MODEL_PATH="${MODEL_PATH:-/app/models/best_model.joblib}"
SSH_OPTS=(-o StrictHostKeyChecking=accept-new -i "$SSH_KEY_PATH")

if [[ ! -f "$SSH_KEY_PATH" ]]; then
  echo "SSH key file not found: $SSH_KEY_PATH" >&2
  exit 1
fi

echo "Deploying backend to ${EC2_USER}@${EC2_HOST} on branch ${BRANCH}"

ssh "${SSH_OPTS[@]}" "${EC2_USER}@${EC2_HOST}" "sudo mkdir -p '${REMOTE_APP_DIR}' && sudo chown '${EC2_USER}:${EC2_USER}' '${REMOTE_APP_DIR}'"
ssh "${SSH_OPTS[@]}" "${EC2_USER}@${EC2_HOST}" "if [ ! -d '${REMOTE_APP_DIR}/.git' ]; then git clone --branch '${BRANCH}' '${REPO_URL}' '${REMOTE_APP_DIR}'; fi"
ssh "${SSH_OPTS[@]}" "${EC2_USER}@${EC2_HOST}" "cd '${REMOTE_APP_DIR}' && git fetch origin '${BRANCH}' && git checkout '${BRANCH}' && git pull --ff-only origin '${BRANCH}'"

{
  printf 'POSTGRES_PASSWORD=%s\n' "$POSTGRES_PASSWORD"
  printf 'CORS_ORIGINS=%s\n' "$CORS_ORIGINS"
  printf 'MODEL_PATH=%s\n' "$MODEL_PATH"
  printf 'ENVIRONMENT=docker\n'
} | ssh "${SSH_OPTS[@]}" "${EC2_USER}@${EC2_HOST}" "umask 077 && cat > '${REMOTE_APP_DIR}/.env'"

ssh "${SSH_OPTS[@]}" "${EC2_USER}@${EC2_HOST}" "cd '${REMOTE_APP_DIR}' && sudo docker compose up -d --build postgres backend"
ssh "${SSH_OPTS[@]}" "${EC2_USER}@${EC2_HOST}" "cd '${REMOTE_APP_DIR}' && sudo docker compose ps"

echo "Backend deployment command completed."
