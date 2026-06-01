#!/usr/bin/env bash
set -euo pipefail

required_vars=(S3_BUCKET VITE_API_BASE_URL)
for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required environment variable: ${var_name}" >&2
    exit 1
  fi
done

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required." >&2
  exit 1
fi

if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "AWS CLI is not authenticated. Configure a profile or environment variables first." >&2
  exit 1
fi

echo "Building frontend for ${VITE_API_BASE_URL}"
cd frontend
npm install
npm run build
aws s3 sync dist "s3://${S3_BUCKET}" --delete
echo "Frontend uploaded to s3://${S3_BUCKET}"
