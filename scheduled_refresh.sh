#!/bin/bash
#
# Wrapper for macOS launchd scheduling.
# Calls refresh_and_deploy.sh (refresh -> validate -> commit public/data -> push -> firebase deploy)
# and appends all output to logs/scheduled-refresh.log
#
# Install: see deploy/launchd/README.md
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

mkdir -p logs
LOG_FILE="$ROOT_DIR/logs/scheduled-refresh.log"

# launchd gets a minimal PATH; firebase lives under nvm on this machine.
export PATH="/Users/tamilla/.nvm/versions/node/v20.20.2/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

{
  echo "=================================================================="
  echo "Scheduled refresh start: $(date)"
  echo "Branch: $(git branch --show-current)"
  echo "---"

  # refresh_and_deploy.sh refuses to run unless we are on main.
  if [[ "$(git branch --show-current)" != "main" ]]; then
    echo "ERROR: scheduled refresh runs from main; currently on $(git branch --show-current)."
    echo "Checkout main before enabling the schedule."
    exit 1
  fi

  ./refresh_and_deploy.sh

  echo "---"
  echo "Scheduled refresh end: $(date) (exit 0)"
} >> "$LOG_FILE" 2>&1
