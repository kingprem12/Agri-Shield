#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

patterns='AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|AKIA|PRIVATE KEY|BEGIN RSA|BEGIN OPENSSH|\.pem|terraform\.tfstate|(^|/)\.env($|[^.]|/)'

echo "Scanning tracked-safe project files for secret patterns..."
if grep -RInE "$patterns" . \
  --exclude-dir=.git \
  --exclude-dir=node_modules \
  --exclude-dir=.venv \
  --exclude-dir=.terraform \
  --exclude-dir=dist \
  --exclude-dir='Data Sets' \
  --exclude-dir=.secrets \
  --exclude-dir=deployment-state \
  --exclude-dir=docs \
  --exclude-dir=.github \
  --exclude='check_secrets.sh' \
  --exclude='README.md' \
  --exclude='DEPLOYMENT.md' \
  --exclude='.gitignore' \
  --exclude='*.png' \
  --exclude='*.jpg' \
  --exclude='*.jpeg' \
  --exclude='*.joblib' \
  --exclude='*.sqlite3'; then
  echo "Potential secret-like strings were found. Review the output above before committing."
  exit 1
fi

echo "Secret scan passed."
