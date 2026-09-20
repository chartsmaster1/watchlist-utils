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

> `refresh_and_deploy.sh` only runs on `main`. Keep this clone on `main`
> while the schedule is enabled; the refresh commits `public/data`
> directly to `main`.

## 1. Test the wrapper manually (once, from main)

```bash
cd /Users/tamilla/Desktop/watchlist-utils
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
