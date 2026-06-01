#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/train_agrishield_x.py --limit-files "${1:-36}"

