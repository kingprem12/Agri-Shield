#!/usr/bin/env bash
set -euo pipefail

TERRAFORM_DIR="${TERRAFORM_DIR:-infrastructure/terraform}"

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform is required." >&2
  exit 1
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required." >&2
  exit 1
fi

if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "AWS CLI is not authenticated. Configure a profile or environment variables first." >&2
  exit 1
fi

cd "$TERRAFORM_DIR"
terraform destroy
