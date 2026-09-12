#!/bin/bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [[ "$(git branch --show-current)" != "main" ]]; then
  echo "ERROR: refresh must run from the main branch."
  exit 1
fi

if [[ ! -x "$(command -v firebase || true)" ]]; then
  echo "ERROR: Firebase CLI is not installed or is not on PATH."
  echo "Install it with: npm install -g firebase-tools"
  exit 1
fi

if [[ ! -f config.json ]]; then
  echo "ERROR: config.json is missing. Add CMC_API_KEY first."
  exit 1
fi

if ! python3 - <<'PY'
import json
from pathlib import Path

config = json.loads(Path('config.json').read_text())
if not config.get('CMC_API_KEY'):
    raise SystemExit(1)
PY
then
  echo "ERROR: config.json does not contain CMC_API_KEY."
  exit 1
fi

non_data_changes="$(git status --short | awk '$2 != "error.log" && $2 !~ /^public\/data\// {print}')"
if [[ -n "$non_data_changes" ]]; then
  echo "ERROR: uncommitted non-data changes found:"
  printf '%s\n' "$non_data_changes"
  echo "Commit or stash them before running the refresh."
  exit 1
fi

echo "Refreshing all datasets..."
python3 public/src/main.py

echo "Validating generated datasets..."
python3 public/src/validate_data.py

git add public/data
if git diff --cached --quiet; then
  echo "No data changes detected."
else
  git commit -m "Refresh market data"
  git push origin main
fi

echo "Deploying to Firebase Hosting..."
firebase deploy --only hosting
echo "Refresh, Git push, and Firebase deployment complete."