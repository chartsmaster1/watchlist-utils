# Scheduling `watchlist-utils` refresh on macOS (launchd)

Yes, this machine can schedule it. On macOS 12 use **launchd**
(`~/Library/LaunchAgents`), not cron — cron works but is deprecated,
needs Full Disk Access edge cases, and won't wake a sleeping Mac either.

Files in this repo:

- `scheduled_refresh.sh` (repo root) — wrapper that sets `PATH`
  (firebase lives under nvm here), checks whether the latest monthly
  occurrence is still unrun, calls `./refresh_and_deploy.sh` when due,
  records success in `logs/last-successful-refresh`, and appends run
  output to `logs/scheduled-refresh.log`.
- `deploy/launchd/com.watchlist-utils.refresh.plist` — LaunchAgent:
  monthly target **1st, 05:30 local time**, plus catch-up triggers
  (`RunAtLoad` on login/boot and an hourly `StartInterval` check).
  Checks are no-ops unless the month's run is still unrun, so a missed
  run fires the first time the machine is awake afterwards.

> `refresh_and_deploy.sh` only runs on `main`. Keep this clone on `main`
> while the schedule is enabled; the refresh commits `public/data`
> directly to `main`.
>
> The repo lives at `~/watchlist-utils` (not `~/Desktop/...`) because
> macOS privacy controls (TCC) block LaunchAgents from executing scripts
> under `~/Desktop`, `~/Documents`, and `~/Downloads`.

## 1. Test the wrapper manually (once, from main)

```bash
cd /Users/tamilla/watchlist-utils
git checkout main
chmod +x scheduled_refresh.sh refresh_and_deploy.sh
./scheduled_refresh.sh
tail -50 logs/scheduled-refresh.log
git log --oneline -3          # expect "Refresh market data" if data changed
```

## 2. Install the schedule

```bash
mkdir -p ~/Library/LaunchAgents logs
cp deploy/launchd/com.watchlist-utils.refresh.plist ~/Library/LaunchAgents/
plutil -lint ~/Library/LaunchAgents/com.watchlist-utils.refresh.plist
launchctl load ~/Library/LaunchAgents/com.watchlist-utils.refresh.plist
launchctl list | grep watchlist-utils
```

## 3. Verify without waiting until 05:30

```bash
launchctl start com.watchlist-utils.refresh
tail -50 logs/scheduled-refresh.log
tail -20 logs/launchd-refresh.out.log logs/launchd-refresh.err.log
```

## 4. Day-to-day

```bash
launchctl list | grep watchlist-utils   # 0 = last check OK, nonzero = failed
tail -100 logs/scheduled-refresh.log   # real runs only; skips go to the launchd stdout log
cat logs/last-successful-refresh       # when the month's run last succeeded
tail -20 logs/launchd-refresh.out.log  # hourly skip lines live here
```

A failed monthly run does **not** mark success, so the next hourly check
retries it automatically — no manual reset needed.

## 5. Change time / disable / remove

```bash
launchctl unload ~/Library/LaunchAgents/com.watchlist-utils.refresh.plist  # pause
# edit deploy/launchd/*.plist Day/Hour/Minute, re-copy, load again
rm ~/Library/LaunchAgents/com.watchlist-utils.refresh.plist                # remove
```

## 6. Email notifications (success or failure)

Every real scheduled run (both success and failure) emails a summary via
`public/src/notify_run.py`: status, exit code, start/finish/duration, trigger
reason, commit + changed data files, push state, per-dataset JSON/CSV row
counts, validation result, market-cap warnings, Firebase release, and — on
failure — the log tail plus the fact that the run will be retried. The same
text is always written to `logs/last-run-summary.txt`.

Setup: add these keys to the gitignored root `config.json` (never commit it),
or export them in the job environment (environment wins):

```json
{
  "CMC_API_KEY": "...",
  "SMTP_HOST": "smtp.gmail.com",
  "SMTP_PORT": 587,
  "SMTP_TLS": "starttls",
  "SMTP_USER": "you@example.com",
  "SMTP_PASS": "<app password, not the account password>",
  "EMAIL_FROM": "you@example.com",
  "EMAIL_TO": "you@example.com,someone-else@example.com"
}
```

`SMTP_TLS` accepts `starttls` (default), `ssl` (port 465) or `none` (relay on
localhost). Gmail needs 2FA plus an App Password; any SMTP provider works.
`EMAIL_SUBJECT_PREFIX` defaults to `[watchlist-utils]`.

Check the message without sending anything (no credentials needed):

```bash
python3 public/src/notify_run.py --dry-run --exit-code 0   # success wording
python3 public/src/notify_run.py --dry-run --exit-code 1   # failure wording
```

Optional end-to-end test against a throwaway SMTP sink (Python 3.9 only), which
exercises the delivery path without needing real credentials:

```bash
python3 -u -m smtpd -n -c DebuggingServer 127.0.0.1:8025 &
SMTP_HOST=127.0.0.1 SMTP_PORT=8025 SMTP_TLS=none EMAIL_TO=you@example.com \
  python3 public/src/notify_run.py --exit-code 0
```

Notification problems never change a run's outcome: if email is not
configured the script prints a hint and exits 2, and the refresh still counts
as successful. The wrapper also emails when it refuses to run (for example on
a non-`main` branch), and returns the refresh's own exit status to launchd.

## Caveats

- Mac must be **awake + logged in** at some point after the 1st for the
  catch-up to fire (login/boot, wake, or the hourly check). A month where
  the Mac never wakes after the 1st stays unrun until the next wake —
  then it runs immediately.
- First scheduled run needs `firebase login` already done for your macOS user
  (it is: firebase 15.30.0 present), `config.json` with `CMC_API_KEY`
  (present), and a clean tree except `public/data` + `error.log`.
- `logs/` is covered by the existing `logs` entry in `.gitignore`, so
  scheduled-run logs stay local-only.
