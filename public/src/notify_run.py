#!/usr/bin/env python3
"""Email a summary of a scheduled refresh run (success or failure).

Recipients and SMTP credentials come from the gitignored root ``config.json``
and/or environment variables of the same name (environment wins), so no secret
is ever committed:

    SMTP_HOST             e.g. smtp.gmail.com
    SMTP_PORT             587 for starttls, 465 for ssl (defaults per SMTP_TLS)
    SMTP_USER             login user (leave unset for an unauthenticated relay)
    SMTP_PASS             app password / API key
    EMAIL_FROM            defaults to SMTP_USER
    EMAIL_TO              comma-separated recipients; required to send
    SMTP_TLS              starttls (default) | ssl | none
    EMAIL_SUBJECT_PREFIX  defaults to [watchlist-utils]

Usage (see scheduled_refresh.sh):

    python3 public/src/notify_run.py --exit-code 0 --log-file logs/scheduled-refresh.log
    python3 public/src/notify_run.py --exit-code 1 --dry-run   # print, send nothing

Exit codes: 0 = sent (or dry-run), 2 = not configured, 3 = send failed.
"""

import argparse
import json
import os
import re
import smtplib
import socket
import ssl
import subprocess
import sys
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
REPO_ROOT = SRC_DIR.parent.parent
CONFIG_PATH = REPO_ROOT / 'config.json'
SUMMARY_PATH = REPO_ROOT / 'logs' / 'last-run-summary.txt'
DEFAULT_LOG = REPO_ROOT / 'logs' / 'scheduled-refresh.log'

SETTING_KEYS = (
    'SMTP_HOST',
    'SMTP_PORT',
    'SMTP_USER',
    'SMTP_PASS',
    'EMAIL_FROM',
    'EMAIL_TO',
    'SMTP_TLS',
    'EMAIL_SUBJECT_PREFIX',
)
DEFAULT_SUBJECT_PREFIX = '[watchlist-utils]'


def load_settings():
    """Collect SMTP/email settings; key names only, secrets are never printed."""
    try:
        config = json.loads(CONFIG_PATH.read_text())
    except (OSError, ValueError):
        config = {}
    if not isinstance(config, dict):
        config = {}

    settings = {}
    for key in SETTING_KEYS:
        value = os.environ.get(key) or config.get(key)
        if value is None:
            continue
        value = str(value).strip()
        if value:
            settings[key] = value
    return settings


def git(*args):
    """Run a read-only git command in the repo; return stdout or ''."""
    try:
        result = subprocess.run(
            ['git', *args],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return ''
    return result.stdout.strip() if result.returncode == 0 else ''


def after(line, prefix):
    return line.split(prefix, 1)[1].strip()


def build_subject(status, exit_code, entries, log, settings):
    prefix = settings.get('EMAIL_SUBJECT_PREFIX') or DEFAULT_SUBJECT_PREFIX
    stamp = datetime.now().astimezone().strftime('%Y-%m-%d')
    total = sum(e['json'] for e in entries if e['json'] is not None)
    if status == 'SUCCESS':
        commit = log['commit'] or git('rev-parse', '--short', 'HEAD') or 'no commit'
        return f'{prefix} data refresh OK - {total} rows, {commit} ({stamp})'
    return f'{prefix} data refresh FAILED - exit {exit_code} ({stamp})'


def build_body(status, exit_code, log, entries, problems):
    now = datetime.now().astimezone()
    total_rows = sum(e['json'] for e in entries if e['json'] is not None)
    commit = log['commit'] or git('rev-parse', '--short', 'HEAD')
    changed = []
    if log['commit']:
        changed = [p for p in git('show', '--name-only', '--format=', log['commit']).splitlines() if p.strip()]
    ahead = git('rev-list', '--count', 'origin/main..HEAD')
    duration = duration_from_log(log)

    lines = [f'watchlist-utils scheduled refresh: {status}', '']
    lines.append('Run')
    lines.append(f'  Exit code     : {exit_code}')
    lines.append(f'  Started       : {log["started"] or "unknown"}')
    lines.append(f'  Finished      : {log["finished"] or "not reported (run did not finish)"}')
    if duration:
        lines.append(f'  Duration      : {duration}')
    lines.append(f'  Host / branch : {socket.gethostname()} / {git("branch", "--show-current") or "unknown"}')
    lines.append(f'  Reported at   : {now.strftime("%Y-%m-%d %H:%M:%S %Z")}')
    if log['reason']:
        lines.append(f'  Trigger       : {log["reason"]}')
    lines.append(f'  Next run      : {next_occurrence().strftime("%Y-%m-%d %H:%M %Z")} (monthly)')

    lines.append('')
    lines.append('Git')
    if commit:
        lines.append(f'  Commit        : {git("log", "-1", "--format=%h %s (%ci)", commit) or commit}')
    if log['no_changes']:
        lines.append('  Data changes  : none detected (no commit needed)')
    elif changed:
        lines.append(f'  Files changed : {len(changed)}')
        for path in changed:
            lines.append(f'                  {path}')
    else:
        lines.append('  Data changes  : not reported in the log')
    if log['pushed'] or (ahead == '0' and not log['no_changes']):
        lines.append('  Push          : pushed to origin/main (in sync)' if ahead == '0'
                     else f'  Push          : NOT in sync - {ahead} commit(s) ahead of origin/main')
    elif ahead:
        lines.append(f'  Push          : not pushed - {ahead} commit(s) ahead of origin/main')

    lines.append('')
    lines.append(f'Data ({total_rows} JSON rows total)')
    for entry in entries:
        json_count = entry['json'] if entry['json'] is not None else 'error'
        csv_count = entry['csv'] if entry['csv'] is not None else 'error'
        lines.append(f'  {entry["name"]:<22} {json_count:>6} JSON / {csv_count:>6} CSV')
    if problems:
        lines.append(f'  Validation    : FAILED ({len(problems)} problem(s))')
        for problem in problems:
            lines.append(f'                  {problem}')
    else:
        lines.append('  Validation    : passed (all datasets)')

    if log['warnings']:
        lines.append('')
        lines.append('Warnings')
        for warning in log['warnings']:
            lines.append(f'  {warning}')

    lines.append('')
    lines.append('Deploy')
    if log['deployed']:
        lines.append('  Firebase      : released' + (f' ({log["deploy_url"]})' if log['deploy_url'] else ''))
    elif 'firebase' in log['tail']:
        lines.append('  Firebase      : not confirmed in the log')
    else:
        lines.append('  Firebase      : no release recorded for this run')

    if status != 'SUCCESS':
        lines.append('')
        lines.append('Next steps')
        lines.append('  The success marker was left unchanged, so the hourly launchd check')
        lines.append('  retries this refresh automatically. Inspect the log tail below;')
        lines.append(f'  full log: {log["path"]}')

    lines.append('')
    lines.append('Log tail')
    for line in log['tail']:
        lines.append(f'  {line}')
    return '\n'.join(lines)
def parse_log(path, tail_lines=14):
    """Pull the run facts out of the wrapper's log section."""
    info = {
        'path': str(path),
        'exists': False,
        'started': '',
        'finished': '',
        'reason': '',
        'commit': '',
        'warnings': [],
        'deploy_url': '',
        'deployed': False,
        'pushed': False,
        'no_changes': False,
        'tail': [],
    }
    try:
        text = Path(path).read_text(errors='replace')
    except OSError:
        return info

    info['exists'] = True
    lines = text.splitlines()
    for line in lines:
        if line.startswith('Scheduled refresh start:'):
            info['started'] = after(line, 'Scheduled refresh start:')
        elif line.startswith('Scheduled refresh end:'):
            info['finished'] = after(line, 'Scheduled refresh end:')
        elif line.startswith('Catch-up reason:'):
            info['reason'] = after(line, 'Catch-up reason:')
        elif line.startswith('Warning:'):
            info['warnings'].append(line.strip())
        elif line.startswith('Hosting URL:'):
            info['deploy_url'] = after(line, 'Hosting URL:')
        elif 'release complete' in line:
            info['deployed'] = True
        elif 'No data changes detected' in line:
            info['no_changes'] = True
        elif 'main -> main' in line:
            info['pushed'] = True
        match = re.match(r'^\[main ([0-9a-f]{7,40})\] ', line)
        if match:
            info['commit'] = match.group(1)

    info['tail'] = lines[-tail_lines:]
    return info


def duration_from_log(info):
    """Wall-clock duration from the HH:MM:SS stamps in the wrapper's lines."""
    stamps = []
    for field in ('started', 'finished'):
        match = re.search(r'(\d{2}):(\d{2}):(\d{2})', info.get(field, ''))
        if match:
            stamps.append(
                int(match.group(1)) * 3600 + int(match.group(2)) * 60 + int(match.group(3))
            )
        else:
            stamps.append(None)
    if stamps[0] is None or stamps[1] is None:
        return ''
    seconds = stamps[1] - stamps[0]
    if seconds < 0:
        seconds += 24 * 3600
    minutes, seconds = divmod(seconds, 60)
    return f'{minutes}m {seconds}s'


def next_occurrence():
    """Next monthly scheduled occurrence (1st, 05:30 local)."""
    now = datetime.now().astimezone()
    occurrence = now.replace(day=1, hour=5, minute=30, second=0, microsecond=0)
    if now < occurrence:
        return occurrence
    return (occurrence.replace(day=28) + timedelta(days=4)).replace(
        day=1, hour=5, minute=30, second=0, microsecond=0
    )


def dataset_rows():
    """Reuse validate_data so the email reports the numbers the run checked."""
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
    entries = []
    problems = []
    try:
        import validate_data
    except Exception as exc:
        return entries, [f'could not load validate_data: {exc}']

    for filename, ticker_field in validate_data.LIST_FILES.items():
        csv_name = 'CompaniesMarketCap.csv' if filename == 'stocks.json' else filename.replace('.json', '.csv')
        entry = {'name': filename, 'csv_name': csv_name, 'json': None, 'csv': None}
        try:
            entry['json'] = validate_data.validate_json(filename, ticker_field)
        except Exception as exc:
            problems.append(f'{filename}: {exc}')
        try:
            entry['csv'] = validate_data.validate_csv(csv_name)
        except Exception as exc:
            problems.append(f'{csv_name}: {exc}')
        entries.append(entry)
    return entries, problems


def send_email(subject, body, settings):
    """Send via SMTP; returns (outcome, detail) without ever echoing secrets."""
    host = settings.get('SMTP_HOST')
    recipients = [a.strip() for a in settings.get('EMAIL_TO', '').split(',') if a.strip()]
    if not host or not recipients:
        return 'not-configured', 'Email not configured (SMTP_HOST and EMAIL_TO are required).'

    tls = (settings.get('SMTP_TLS') or 'starttls').lower()
    if tls not in ('starttls', 'ssl', 'none'):
        return 'error', f'SMTP_TLS must be starttls, ssl or none (got {tls!r}).'
    try:
        port = int(settings.get('SMTP_PORT') or (465 if tls == 'ssl' else 587))
    except ValueError:
        return 'error', 'SMTP_PORT is not a number.'

    user = settings.get('SMTP_USER') or ''
    password = settings.get('SMTP_PASS') or ''
    sender = settings.get('EMAIL_FROM') or user or 'watchlist-utils@localhost'

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = ', '.join(recipients)
    message.set_content(body)

    try:
        if tls == 'ssl':
            with smtplib.SMTP_SSL(host, port, timeout=30,
                                  context=ssl.create_default_context()) as server:
                if user:
                    server.login(user, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                if tls == 'starttls':
                    server.ehlo()
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                if user:
                    server.login(user, password)
                server.send_message(message)
    except (smtplib.SMTPException, ssl.SSLError, socket.error, OSError) as exc:
        return 'error', f'SMTP send failed: {type(exc).__name__}: {exc}'

    return 'sent', f'Email sent to {", ".join(recipients)} via {host}:{port} ({tls}).'


def main():
    parser = argparse.ArgumentParser(description='Email a summary of a scheduled refresh run.')
    parser.add_argument('--exit-code', type=int, default=0,
                        help='exit status of refresh_and_deploy.sh (0 = success)')
    parser.add_argument('--log-file', default=str(DEFAULT_LOG),
                        help='wrapper log to summarize')
    parser.add_argument('--dry-run', action='store_true',
                        help='print the email and skip sending')
    parser.add_argument('--to', help='override EMAIL_TO recipients')
    parser.add_argument('--tail-lines', type=int, default=14,
                        help='log lines to include in the email')
    args = parser.parse_args()

    settings = load_settings()
    if args.to:
        settings['EMAIL_TO'] = args.to

    status = 'SUCCESS' if args.exit_code == 0 else 'FAILURE'
    log = parse_log(args.log_file, args.tail_lines)
    entries, problems = dataset_rows()
    subject = build_subject(status, args.exit_code, entries, log, settings)
    body = build_body(status, args.exit_code, log, entries, problems)

    try:
        SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY_PATH.write_text(f'Subject: {subject}\n\n{body}\n')
        print(f'Run summary written to {SUMMARY_PATH}')
    except OSError as exc:
        print(f'Could not write {SUMMARY_PATH}: {exc}')

    print(f'Subject: {subject}')
    if args.dry_run:
        print('--- dry run: email not sent ---')
        print(body)
        return 0

    outcome, detail = send_email(subject, body, settings)
    print(detail)
    if outcome == 'sent':
        return 0
    if outcome == 'not-configured':
        print(f'Add SMTP_HOST, SMTP_USER, SMTP_PASS and EMAIL_TO to {CONFIG_PATH}')
        print('(gitignored) or export them in the job environment to enable email.')
        print('The refresh run is unaffected; the summary above is always written to disk.')
        return 2
    print('The refresh run is unaffected; see the message above.')
    return 3


if __name__ == '__main__':
    sys.exit(main())