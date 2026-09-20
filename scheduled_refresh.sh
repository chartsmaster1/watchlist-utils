#!/bin/bash
#
# Wrapper for macOS launchd scheduling.
# Runs refresh_and_deploy.sh (refresh -> validate -> commit public/data -> push -> firebase deploy)
# once per month, with catch-up: if the scheduled run was missed (Mac asleep/off),
# the next agent trigger (login/boot, hourly check, wake-while-running) runs it.
#
# Install: see deploy/launchd/README.md
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

mkdir -p logs
LOG_FILE="$ROOT_DIR/logs/scheduled-refresh.log"
STATE_FILE="$ROOT_DIR/logs/last-successful-refresh"

# launchd gets a minimal PATH; firebase lives under nvm on this machine.
export PATH="/Users/tamilla/.nvm/versions/node/v20.20.2/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Prints the DUE / NOT DUE reason on stdout.
# Exits 0 when the most recent scheduled occurrence (1st of month, 05:30
# local) has passed without a recorded successful run.
is_due() {
  python3 - "$STATE_FILE" <<'PY'
import sys
from datetime import datetime, timedelta

state_path = sys.argv[1]
now = datetime.now().astimezone()

occ = now.replace(day=1, hour=5, minute=30, second=0, microsecond=0)
if now < occ:
    # This month's occurrence hasn't happened yet; the relevant one
    # is last month's 1st at 05:30.
    occ = (occ - timedelta(days=1)).replace(day=1, hour=5, minute=30,
                                            second=0, microsecond=0)

try:
    with open(state_path) as f:
        last = datetime.strptime(f.read().strip(), "%Y-%m-%dT%H:%M:%S%z")
except (OSError, ValueError):
    print("DUE: no recorded successful run")
    sys.exit(0)

if last < occ <= now:
    print(f"DUE: last success {last.isoformat()}, missed occurrence {occ.isoformat()}")
    sys.exit(0)

print(f"NOT DUE: last success {last.isoformat()}, latest occurrence {occ.isoformat()}")
sys.exit(1)
PY
}

if ! CHECK_OUT=$(is_due); then
  # Not due: keep the main log for real runs only. This line lands in the
  # launchd stdout log (hourly checks would otherwise spam the main log).
  echo "$(date '+%Y-%m-%d %H:%M:%S') skip: $CHECK_OUT"
  exit 0
fi

run_status=0

{
  echo "=================================================================="
  echo "Scheduled refresh start: $(date)"
  echo "Branch: $(git branch --show-current)"
  echo "Catch-up reason: $CHECK_OUT"
  echo "---"

  # refresh_and_deploy.sh refuses to run unless we are on main.
  if [[ "$(git branch --show-current)" != "main" ]]; then
    echo "ERROR: scheduled refresh runs from main; currently on $(git branch --show-current)."
    echo "Checkout main before enabling the schedule."
    python3 public/src/notify_run.py --exit-code 1 --log-file "$LOG_FILE" \
      || echo "Notification email was not sent (see the message above)."
    exit 1
  fi

  # Capture the refresh status without tripping `set -e`, so that both the
  # success and the failure path can be reported by email.
  set +e
  ./refresh_and_deploy.sh
  run_status=$?
  set -e

  if [[ $run_status -eq 0 ]]; then
    # Record success only after everything above passed; a failure leaves the
    # state untouched so the next check retries automatically.
    date +%Y-%m-%dT%H:%M:%S%z > "$STATE_FILE"

    echo "---"
    echo "Scheduled refresh end: $(date) (exit 0)"
  else
    echo "---"
    echo "Scheduled refresh FAILED: $(date) (exit $run_status)"
    echo "Success state left unchanged; the next hourly check will retry."
  fi
} >> "$LOG_FILE" 2>&1

# Email the run summary after the log section is complete so the message can
# include its tail. A notification problem never changes the run's status.
{
  echo "---"
  echo "Notification:"
  python3 public/src/notify_run.py --exit-code "$run_status" --log-file "$LOG_FILE" \
    || echo "Notification email was not sent (see the message above)."
} >> "$LOG_FILE" 2>&1

exit "$run_status"
