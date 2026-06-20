#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TF_DIR="$ROOT_DIR/infrastructure/terraform"

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform is required but was not found."
  exit 1
fi

if [ ! -f "$TF_DIR/terraform.tfvars" ]; then
  echo "Missing $TF_DIR/terraform.tfvars. Create it from terraform.tfvars.example before destroying."
  exit 1
fi

cd "$TF_DIR"
terraform destroy
