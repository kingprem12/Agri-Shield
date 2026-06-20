#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <s3-bucket-name>"
  exit 1
fi

BUCKET="$1"
cd frontend
npm install
npm run build
aws s3 sync dist "s3://$BUCKET" --delete

