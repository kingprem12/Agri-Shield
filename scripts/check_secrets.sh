#!/usr/bin/env bash
set -euo pipefail

scan_root="${1:-.}"

high_risk_pattern='AKIA[0-9A-Z]{16}|aws_secret_access_key[[:space:]]*=|AWS_SECRET_ACCESS_KEY[[:space:]]*=|-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----|terraform\.tfstate'
review_pattern='AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|PRIVATE KEY|BEGIN RSA|BEGIN OPENSSH|\.pem|token|password|credentials|\.env'

exclude_args=(
  --hidden
  --glob '!.git/**'
  --glob '!frontend/node_modules/**'
  --glob '!backend/.venv/**'
  --glob '!backend/.pytest_cache/**'
  --glob '!**/__pycache__/**'
  --glob '!**/.terraform/**'
  --glob '!frontend/dist/**'
  --glob '!*.png'
  --glob '!*.jpg'
  --glob '!*.jpeg'
  --glob '!*.joblib'
  --glob '!*.pt'
  --glob '!*.sqlite3'
  --glob '!scripts/check_secrets.sh'
)

echo "Running high-risk secret scan..."
if rg -l "${exclude_args[@]}" "$high_risk_pattern" "$scan_root" >/tmp/agrishield_secret_hits.txt; then
  echo "High-risk secret patterns were found in these files:" >&2
  sed 's#^\./##' /tmp/agrishield_secret_hits.txt >&2
  exit 1
fi

echo "Running review scan for placeholder-sensitive words..."
if rg -l "${exclude_args[@]}" "$review_pattern" "$scan_root" >/tmp/agrishield_secret_review_hits.txt; then
  echo "Review-only matches found. Confirm these are placeholders or documentation, not secrets:"
  sed 's#^\./##' /tmp/agrishield_secret_review_hits.txt
else
  echo "No review-only matches found."
fi

echo "No high-risk secrets detected."
