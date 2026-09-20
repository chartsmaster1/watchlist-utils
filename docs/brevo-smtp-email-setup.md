# Brevo SMTP email notifications — setup and reuse

Audience: an agent or maintainer wiring run notifications for any project, and
the reusable recipe for doing it on a second process.

Status in this repo: implemented and working. `public/src/notify_run.py` emails a
summary of every scheduled refresh (success or failure), and
`/Users/tamilla/watchlist-utils/config.json` holds live Brevo credentials.

## 1. How it is wired here

| Piece | Role |
| --- | --- |
| `public/src/notify_run.py` | Builds the summary and sends it over SMTP. Stdlib only. |
| `scheduled_refresh.sh` | Captures `refresh_and_deploy.sh`'s exit status, then calls the notifier; emails on success, failure, and branch-guard refusal. |
| `logs/last-run-summary.txt` | The same text, always written to disk (gitignored) even when email is off. |
| `config.json` (repo root) | Credentials. Gitignored. |

Notifier exit codes: `0` sent (or `--dry-run`), `2` not configured, `3` send
failed. **A notification problem never changes a run's status** — email failure
cannot make a good refresh look failed (that would trigger pointless retries).

## 2. Credential model

Environment variables take precedence over `config.json`, and the names are the
same in both.

| Key | Mandatory | Brevo value / note |
| --- | --- | --- |
| `SMTP_HOST` | yes | `smtp-relay.brevo.com` |
| `SMTP_USER` | yes | The **Login** from the dashboard's SMTP tab — a generated `<id>@smtp-brevo.com`, **not** the account email |
| `SMTP_PASS` | yes | An **SMTP key** (`xsmtpsib-…`), never the v3 REST API key |
| `EMAIL_TO` | yes | Recipient(s), comma-separated |
| `EMAIL_FROM` | in practice | A validated sender; code falls back to `SMTP_USER`, which Brevo rejects as a sender |
| `SMTP_PORT` | no | Defaults to `587` (or `465` when `SMTP_TLS=ssl`) |
| `SMTP_TLS` | no | Defaults to `starttls`; also accepts `ssl` or `none` |
| `EMAIL_SUBJECT_PREFIX` | no | Defaults to `[watchlist-utils]` |

Minimum working set for any process: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`,
`EMAIL_FROM`, `EMAIL_TO`.

## 3. One-time Brevo setup (a human does this part)

An agent cannot do these steps: they need a browser signup, an email
confirmation, and — for a key — the dashboard.

1. Create the free account: <https://app.brevo.com/account/register>
   (or <https://www.brevo.com/pricing/> → *Sign up free*). Use a mailbox the
   operator can actually read; it becomes a validated sender. Free plan sends up
   to 300 emails/day, no card required.
2. Open **SMTP & API**: <https://app.brevo.com/settings/keys/smtp> → **SMTP** tab.
   Copy the **Login** (e.g. `1234567@smtp-brevo.com`) → `SMTP_USER`.
3. On the same tab, **generate an SMTP key** and copy it → `SMTP_PASS`.
   It is shown once; the *key name* is only a label and is never used for auth.
4. Sender identity — one of:
   - **Validated sender** (fast): <https://app.brevo.com/senders/list> → *Add a
     sender* → click the emailed confirmation link. Then use that address as
     `EMAIL_FROM`. Requires the address to be able to receive mail.
   - **Domain authentication** (better deliverability, works for a domain with
     no mailboxes): <https://app.brevo.com/senders/domain/create> → publish the
     DKIM/SPF (`include:spf.brevo.com`)/DMARC records at the DNS host. Any address
     on that domain becomes a valid sender.
5. Note: new accounts may sit in a short sending-approval review. If
   authentication or sending fails while the dashboard shows a review banner,
   the fix is approval, not configuration.

## 4. Storing the credentials (secret-safe)

Rules:

- Never print, log, echo, or paste an SMTP key. Classify by *shape*, not value.
- Never commit credentials. `config.json` is gitignored in this repo; verify
  with `git check-ignore -v config.json` before writing to it. Anything named
  `config.json.bak` is **not** covered — do not leave copies behind.
- Keep the file `chmod 600`.
- Writing via a script keeps the secret out of the shell history; prefer that
  over `SMTP_PASS=… command`, because environment variables are visible in the
  process table and shell history.

Merge without clobbering existing keys (e.g. a project's `CMC_API_KEY`):

```python
import json
from pathlib import Path

config = Path('config.json')
data = json.loads(config.read_text())          # preserve what is already there
data.update({
    'SMTP_HOST': 'smtp-relay.brevo.com',
    'SMTP_PORT': 587,
    'SMTP_TLS': 'starttls',
    'SMTP_USER': '<id>@smtp-brevo.com',        # dashboard Login
    'SMTP_PASS': '<xsmtpsib-... SMTP key>',    # entered by the operator
    'EMAIL_FROM': '<validated sender>',
    'EMAIL_TO': '<recipient>',
})
config.write_text(json.dumps(data, indent=2) + '\n')
```

Then `chmod 600 config.json`. Report only key **names** back to the operator,
never values.

## 5. Verification procedure

Run these in order. Stop at the first failure and use section 6.

**Step 1 — config is complete (prints names only, never secrets):**

```bash
python3 - <<'PY'
import json
from pathlib import Path
c = json.loads(Path('config.json').read_text())
need = ('SMTP_HOST', 'SMTP_USER', 'SMTP_PASS', 'EMAIL_FROM', 'EMAIL_TO')
print('present :', sorted(c))
print('missing :', [k for k in need if not c.get(k)] or 'none')
for k in ('SMTP_PASS', 'CMC_API_KEY'):
    if k in c:
        print(f'{k}: set, {len(str(c[k]))} chars')   # length only, never the value
PY
```

**Step 2 — the key has the right shape** (Brevo SMTP keys are
`xsmtpsib-` + 64 hex + 16 chars = 90; anything else is a wrong credential type):

```bash
python3 -c "import json,pathlib; k=json.loads(pathlib.Path('config.json').read_text())['SMTP_PASS']; \
print('len', len(k), 'prefix', k.split('-')[0], 'segments', [len(s) for s in k.split('-')])"
```

**Step 3 — authentication only** (no email sent; catches the 535 cases):

```bash
python3 - <<'PY'
import json, smtplib, ssl
from pathlib import Path
c = json.loads(Path('config.json').read_text())
try:
    with smtplib.SMTP(c.get('SMTP_HOST', 'smtp-relay.brevo.com'),
                      int(c.get('SMTP_PORT', 587)), timeout=20) as s:
        s.ehlo()
        s.starttls(context=ssl.create_default_context())
        s.ehlo()
        s.login(str(c['SMTP_USER']).strip(), str(c['SMTP_PASS']))
        print('auth OK for login:', c['SMTP_USER'])
except smtplib.SMTPAuthenticationError as exc:
    print('auth REFUSED ->', exc.args[0], exc.args[1], '(see troubleshooting)')
except Exception as exc:
    print('transport error:', type(exc).__name__, exc)
PY
```

**Step 4 — render the message without sending** (`watchlist-utils` only):

```bash
python3 public/src/notify_run.py --dry-run --exit-code 0   # success wording
python3 public/src/notify_run.py --dry-run --exit-code 1   # failure wording
```

**Step 5 — live send and confirm delivery:**

```bash
python3 public/src/notify_run.py --exit-code 0 --tail-lines 3
```

Expect `Email sent to <recipient> via smtp-relay.brevo.com:587 (starttls).` Then
confirm with the human that the mail arrived, and ask them to check Spam /
Promotions — mail sent via a relay "on behalf of" a mailbox is often filtered the
first time. Marking it *not spam* once is enough for future runs.

## 6. Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `535 5.7.8 Authentication failed` | `SMTP_USER` is the **account email** instead of the generated relay login | Copy the **Login** from the SMTP tab (`<id>@smtp-brevo.com`) into `SMTP_USER`. Three different usernames were tried before discovering this in `watchlist-utils`. |
| Same `535` with the correct login | Key is stale, or a v3 REST API key was used | Regenerate an **SMTP** key (regenerating invalidates the previous one) and update `SMTP_PASS` |
| `403` / "from address does not match a verified Sender Identity" | `EMAIL_FROM` is not a validated sender | Validate it in *Senders & IPs*, or authenticate the domain |
| `421` / throttle | Too many auth attempts in a short window | Wait a few minutes; stop retrying in a loop |
| Connection refused / timeout | Wrong host or port blocked on the network | Confirm `smtp-relay.brevo.com`, try `465` with `SMTP_TLS=ssl` |
| Auth works, mail "sent", human sees nothing | Filtered as spam | Check Spam/Promotions; mark *not spam* once |
| Worked before, silent now | Key revoked/rotated, or the free cap | Check `logs/scheduled-refresh.log` for `SMTP send failed`; the run itself still succeeds |

Diagnosing: a `535` means the relay was reached and the **username/key pair** was
rejected — it is an authentication-stage failure, not DNS, sender or content. Keep
host/port/TLS fixed while testing credentials so you change one variable at a time.

## 7. Reusing this for another process

Three options, cheapest first.

**Option A — copy `notify_run.py`** (keeps the rich summary: run status, git
commit, per-dataset counts, warnings, log tail). Copy the file, then:

```bash
python3 notify_run.py --exit-code "$?" --log-file /path/to/process.log
```

Adjust `SUMMARY_PATH`, `DEFAULT_LOG` and `dataset_rows()` — the dataset table is
the only `watchlist-utils`-specific part. Everything else (settings loading,
`--dry-run`, exit codes) is generic.

**Option B — minimal self-contained sender** (~20 lines, no repo coupling):

```python
import os
import smtplib
import ssl
from email.message import EmailMessage


def send(subject, body):
    host = os.environ['SMTP_HOST']                      # smtp-relay.brevo.com
    port = int(os.environ.get('SMTP_PORT', 587))        # 587 = starttls
    tls = os.environ.get('SMTP_TLS', 'starttls').lower()
    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = os.environ['EMAIL_FROM']          # validated sender
    message['To'] = os.environ['EMAIL_TO']              # comma-separated
    message.set_content(body)
    if tls == 'ssl':
        with smtplib.SMTP_SSL(host, port, timeout=30,
                              context=ssl.create_default_context()) as server:
            server.login(os.environ['SMTP_USER'], os.environ['SMTP_PASS'])
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            if tls == 'starttls':
                server.starttls(context=ssl.create_default_context())
            server.login(os.environ['SMTP_USER'], os.environ['SMTP_PASS'])
            server.send_message(message)
```

Wrap the call in `try/except` and never let a notification failure change the
exit status of the job being reported.

**Option C — Brevo REST API** (if you prefer HTTP over SMTP):
`POST https://api.brevo.com/v3/smtp/email` with header `api-key: <v3 API key>`.
Note the credential split: the REST API needs a **v3 API key** from
<https://app.brevo.com/settings/keys/api>, which is *not* the SMTP key. Keep both
straight — mixing them is the most common Brevo failure.

## 8. Operational notes

- Free plan: ~300 emails/day; test sends count toward the cap.
- The relay is for transactional mail to yourself/operators. Do not send
  marketing or bulk mail through it.
- Rotation is invisible: if the key is revoked the job keeps succeeding while
  summaries silently stop (`SMTP send failed` in the log). Periodically confirm a
  real message arrives, or check `logs/last-run-summary.txt` timestamps.
- Never paste a key into a chat, ticket, screenshot, or commit. If a key is
  exposed, regenerate it in the dashboard — the old one dies instantly.

## 9. Checklist

- [ ] Brevo account created and email confirmed
- [ ] **Login** copied from the SMTP tab → `SMTP_USER`
- [ ] SMTP key generated → `SMTP_PASS` (shape: `xsmtpsib-` + 64 hex + 16)
- [ ] Sender validated (or domain authenticated) → `EMAIL_FROM`
- [ ] Recipient(s) → `EMAIL_TO`
- [ ] Credentials merged into the gitignored config; `chmod 600`
- [ ] Step 3 auth test passes
- [ ] Live send arrives, not in spam
- [ ] Wired into the job's wrapper so it fires on success **and** failure