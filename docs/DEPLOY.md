# MarcBot Deploy and Operations Runbook

This document captures the current operational baseline for MarcBot.

MarcBot is a personal-only Telegram automation bot running on the Ubuntu server `marcbot01`.

## Current baseline

- Project root: `/srv/marcbot`
- Application repository: `/srv/marcbot/app`
- Runtime state: `/srv/marcbot/state`
- Workspace: `/srv/marcbot/workspace`
- Logs: `/srv/marcbot/logs`
- Local config: `/srv/marcbot/config/marcbot.toml`
- Systemd service: `marcbot-telegram.service`
- Runtime user: `marc`
- Admin/operator user: `adminuser`
- Python virtual environment: `/srv/marcbot/app/.venv`
- GitHub remote: `git@github.com:Tin55FoilDev/marcbot.git`

## Telegram commands

Current supported Telegram commands:

    /ping     - check whether MarcBot is responding
    /version  - show MarcBot and Python version
    /status   - show basic MarcBot service status
    /health   - run local MarcBot health checks
    /logs     - show recent MarcBot application logs
    /help     - show command list

## Configuration

The real config file lives outside Git:

    /srv/marcbot/config/marcbot.toml

It should be owned by `marc` and readable only by `marc`:

    sudo chown marc:marc /srv/marcbot/config/marcbot.toml
    sudo chmod 600 /srv/marcbot/config/marcbot.toml

Expected shape:

    [app]
    name = "MarcBot"
    environment = "development"

    [telegram]
    enabled = true
    bot_token = "REDACTED"
    allowed_chat_ids = [123456789]

Never commit the real config file or Telegram bot token.

## Service management

Check service status:

    sudo systemctl status marcbot-telegram.service --no-pager

Start service:

    sudo systemctl start marcbot-telegram.service

Stop service:

    sudo systemctl stop marcbot-telegram.service

Restart service:

    sudo systemctl restart marcbot-telegram.service

Check whether the service is enabled at boot:

    sudo systemctl is-enabled marcbot-telegram.service

Enable service at boot:

    sudo systemctl enable marcbot-telegram.service

## Logs

MarcBot writes rotating application logs here:

    /srv/marcbot/logs/marcbot.log

Because `/srv/marcbot` is owned by `marc`, inspect logs as `marc`:

    sudo -u marc tail -n 80 /srv/marcbot/logs/marcbot.log
    sudo -u marc ls -lh /srv/marcbot/logs/

Systemd journal:

    sudo journalctl -u marcbot-telegram.service -n 80 --no-pager

Follow live service logs:

    sudo journalctl -u marcbot-telegram.service -f

## Standard validation

Run after every code change:

    sudo -u marc bash -lc '
    cd /srv/marcbot/app
    ./scripts/check.sh
    '

This currently checks:

- MarcBot version command
- MarcBot doctor
- pytest
- Ruff linting

If Ruff reports fixable formatting issues:

    sudo -u marc bash -lc '
    cd /srv/marcbot/app
    . .venv/bin/activate
    ruff check . --fix
    ./scripts/check.sh
    '

## Version bump deployment check

After every MarcBot revision/version bump:

1. Commit and push the version bump.
2. Restart the deployed Telegram service:

```bash
sudo systemctl restart marcbot-telegram.service
```

3. Verify Telegram reports the new version with both commands:

```text
/about
/version
```

4. If Telegram still reports the old version, treat the service as not
   restarted or not running the expected checkout, then inspect service
   status and logs before continuing.
## Post-change deploy check

After a code change and successful validation:

    sudo systemctl restart marcbot-telegram.service
    sudo systemctl status marcbot-telegram.service --no-pager

Then test from Telegram:

    /version
    /health
    /logs

Then inspect local logs:

    sudo -u marc tail -n 80 /srv/marcbot/logs/marcbot.log

Expected `/health` output:

    🤖 MarcBot health
    OK: required runtime directories found
    OK: logs directory writable
    OK: config loads
    Overall: healthy

Expected `/version` output shape:

    🤖 MarcBot version
    MarcBot: 0.1.0
    Python: <current venv Python version>
    Executable: /srv/marcbot/app/.venv/bin/python

## Git workflow

Check status:

    sudo -u marc bash -lc '
    cd /srv/marcbot/app
    git status --short
    '

Commit and push a completed change:

    sudo -u marc bash -lc '
    cd /srv/marcbot/app

    git status --short
    git add <FILES>
    git commit -m "<COMMIT MESSAGE>"
    git push

    git status
    git log --oneline --decorate -10
    '

## Pull latest code

For a future restore or second machine checkout:

    sudo -u marc bash -lc '
    cd /srv/marcbot/app
    git pull --ff-only
    ./scripts/check.sh
    '

Then restart:

    sudo systemctl restart marcbot-telegram.service
    sudo systemctl status marcbot-telegram.service --no-pager

## Virtual environment

The Python virtual environment lives at:

    /srv/marcbot/app/.venv

Install or refresh dependencies:

    sudo -u marc bash -lc '
    cd /srv/marcbot/app
    . .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements-dev.txt
    '

## Systemd unit

Primary service file:

    /etc/systemd/system/marcbot-telegram.service

Repository copy:

    /srv/marcbot/app/systemd/marcbot-telegram.service

After changing the systemd unit:

    sudo cp /srv/marcbot/app/systemd/marcbot-telegram.service /etc/systemd/system/marcbot-telegram.service
    sudo systemctl daemon-reload
    sudo systemctl restart marcbot-telegram.service
    sudo systemctl status marcbot-telegram.service --no-pager

## Restore checklist

After restoring the VM or server from backup:

1. Confirm the service is active:

       sudo systemctl status marcbot-telegram.service --no-pager

2. Confirm service starts at boot:

       sudo systemctl is-enabled marcbot-telegram.service

3. Confirm config exists and has safe permissions:

       sudo -u marc test -f /srv/marcbot/config/marcbot.toml && echo "config exists"
       sudo stat -c "%U:%G %a %n" /srv/marcbot/config/marcbot.toml

   Expected:

       marc:marc 600 /srv/marcbot/config/marcbot.toml

4. Run validation:

       sudo -u marc bash -lc '
       cd /srv/marcbot/app
       ./scripts/check.sh
       '

5. Restart service:

       sudo systemctl restart marcbot-telegram.service

6. Test Telegram:

       /version
       /health
       /logs

## Security notes

- MarcBot is personal-only.
- Telegram access is restricted to configured `allowed_chat_ids`.
- If `allowed_chat_ids` is empty, no Telegram chats are authorized.
- The bot token is stored outside Git.
- `/logs` reads only the MarcBot application log.
- `/logs` redacts obvious Telegram bot tokens before sending output.
- No arbitrary shell execution exists in the Telegram command path.
- No arbitrary file read command exists in the Telegram command path.

## Long pasted code blocks

For long pasted shell/Python changes, prefer writing Python to a temporary file with a quoted heredoc and then executing that script from the repo.

Recommended pattern:

    cat > /tmp/marcbot_patch_example.py <<'PY'
    from pathlib import Path

    path = Path("example.txt")
    path.write_text("example\n", encoding="utf-8")
    PY

    sudo -u marc env \
      HOME=/home/marc \
      PATH="/srv/marcbot/app/.venv/bin:/usr/local/bin:/usr/bin:/bin" \
      bash -lc '
    set -e
    cd /srv/marcbot/app
    python /tmp/marcbot_patch_example.py
    '

This avoids failures from nested shell quoting, editor wrapping, or pasted code being interpreted by Bash before Python receives it.

Prefer this over embedding complex Python directly inside a nested `bash -lc '...'` command.

## Current operational standard

Before adding new features:

1. Make a small code change.
2. Add or update tests where practical.
3. Run `./scripts/check.sh`.
4. Restart the service.
5. Test the Telegram command.
6. Inspect logs.
7. Commit and push.
8. Consider a VM backup after major milestones.

## App-level backups

MarcBot has a daily app-level backup timer in addition to any Proxmox VM backups.

Backup script:

    /srv/marcbot/app/scripts/backup_marcbot.sh

Systemd units:

    /etc/systemd/system/marcbot-backup.service
    /etc/systemd/system/marcbot-backup.timer

Repo copies:

    /srv/marcbot/app/systemd/marcbot-backup.service
    /srv/marcbot/app/systemd/marcbot-backup.timer

Backup output:

    /srv/marcbot/backups/marcbot-backup-YYYYMMDD-HHMMSS.tar.gz
    /srv/marcbot/backups/marcbot-backup-YYYYMMDD-HHMMSS.tar.gz.sha256
    /srv/marcbot/backups/latest-backup.txt

The backup includes:

    /srv/marcbot/app
    /srv/marcbot/config
    /srv/marcbot/state
    /srv/marcbot/workspace
    /srv/marcbot/logs

The backup excludes:

    /srv/marcbot/app/.venv
    /srv/marcbot/backups
    /srv/marcbot/tmp

Manual backup run:

    sudo -u marc bash -lc '
    cd /srv/marcbot
    /srv/marcbot/app/scripts/backup_marcbot.sh
    '

Manual systemd service run:

    sudo systemctl start marcbot-backup.service
    sudo systemctl status marcbot-backup.service --no-pager
    sudo journalctl -u marcbot-backup.service -n 80 --no-pager

Timer inspection:

    sudo systemctl status marcbot-backup.timer --no-pager
    sudo systemctl list-timers --all | grep -E 'marcbot-backup|NEXT'

Telegram status check:

    /backup_status

## AI source monitor systemd timer

MarcBot can generate local AI source monitor reports through a systemd service and timer.

Tracked template files:

    /srv/marcbot/app/systemd/marcbot-source-monitor-ai.service
    /srv/marcbot/app/systemd/marcbot-source-monitor-ai.timer

Installed unit files:

    /etc/systemd/system/marcbot-source-monitor-ai.service
    /etc/systemd/system/marcbot-source-monitor-ai.timer

Service behavior:

    User=marc
    Group=marc
    WorkingDirectory=/srv/marcbot/app
    ExecStart=/srv/marcbot/app/.venv/bin/python -m marcbot source-monitor run ai

Timer behavior:

    OnCalendar=*-*-* 07:35:00 America/New_York
    Persistent=true
    RandomizedDelaySec=2m
    Unit=marcbot-source-monitor-ai.service

Manual service run:

    sudo systemctl start marcbot-source-monitor-ai.service
    sudo systemctl status marcbot-source-monitor-ai.service --no-pager
    sudo journalctl -u marcbot-source-monitor-ai.service -n 80 --no-pager

Timer inspection:

    sudo systemctl status marcbot-source-monitor-ai.timer --no-pager
    sudo systemctl list-timers --all | grep -E 'source-monitor-ai|NEXT'

Install or refresh source monitor units from Git templates:

    sudo cp /srv/marcbot/app/systemd/marcbot-source-monitor-ai.service /etc/systemd/system/marcbot-source-monitor-ai.service
    sudo cp /srv/marcbot/app/systemd/marcbot-source-monitor-ai.timer /etc/systemd/system/marcbot-source-monitor-ai.timer
    sudo chmod 644 /etc/systemd/system/marcbot-source-monitor-ai.service
    sudo chmod 644 /etc/systemd/system/marcbot-source-monitor-ai.timer
    sudo systemd-analyze verify /etc/systemd/system/marcbot-source-monitor-ai.service /etc/systemd/system/marcbot-source-monitor-ai.timer

Enable timer:

    sudo systemctl daemon-reload
    sudo systemctl enable --now marcbot-source-monitor-ai.timer

Telegram checks:

    /timer_status
    /report_status source ai

The timer writes local reports only. Telegram reads the latest local summary and does not trigger source fetching.

Compare tracked source monitor units against installed units:

    diff -u /srv/marcbot/app/systemd/marcbot-source-monitor-ai.service /etc/systemd/system/marcbot-source-monitor-ai.service
    diff -u /srv/marcbot/app/systemd/marcbot-source-monitor-ai.timer /etc/systemd/system/marcbot-source-monitor-ai.timer

No output from `diff` means the tracked template and installed unit match.

## Telegram service LLM environment

If Telegram chat or another Telegram-facing provider-contacting command is
enabled, the deployed `marcbot-telegram.service` system unit must load the local
LLM secret environment file:

    EnvironmentFile=/srv/marcbot/config/llm.env

The file should exist outside Git at:

    /srv/marcbot/config/llm.env

It should be readable by the `marc` runtime user and contain provider secret
environment variables such as:

    MARCBOT_LMSTUDIO_API_KEY

After editing the deployed unit:

    sudo systemctl daemon-reload
    sudo systemctl restart marcbot-telegram.service

Verify without printing secrets:

    sudo systemctl show marcbot-telegram.service -p EnvironmentFiles -p Environment

Provider-contacting Telegram chat may return an HTTP 401 provider error if this
environment file is missing from the service runtime environment.

## Optional local chat context files

Telegram chat may use local Markdown context files under:

    /srv/marcbot/config/chat/

Planned files:

    system.md
    agent.md
    user.md
    project.md

These files are local runtime configuration and should not be committed to Git.
Git-tracked examples live under:

    docs/examples/chat/

The local files may define MarcBot's chat name, role, tone, humor level,
enthusiasm level, slang preference, user preferences, and project context.

They must not contain secrets such as API keys, Telegram tokens, OAuth tokens,
passwords, private keys, or copied `.env` contents.

## Weather report systemd timer

MarcBot can generate and send the daily Westfield weather report through a
systemd service and timer.

Repo unit files:

    /srv/marcbot/app/systemd/marcbot-weather-report.service
    /srv/marcbot/app/systemd/marcbot-weather-report.timer

Deployed unit files:

    /etc/systemd/system/marcbot-weather-report.service
    /etc/systemd/system/marcbot-weather-report.timer

The service runs:

    ExecStart=/srv/marcbot/app/.venv/bin/python -m marcbot weather-report run-send-text

The timer runs daily at:

    OnCalendar=*-*-* 07:15:00 America/New_York

Install:

    sudo cp /srv/marcbot/app/systemd/marcbot-weather-report.service /etc/systemd/system/marcbot-weather-report.service
    sudo cp /srv/marcbot/app/systemd/marcbot-weather-report.timer /etc/systemd/system/marcbot-weather-report.timer
    sudo chmod 644 /etc/systemd/system/marcbot-weather-report.service
    sudo chmod 644 /etc/systemd/system/marcbot-weather-report.timer
    sudo systemd-analyze verify /etc/systemd/system/marcbot-weather-report.service /etc/systemd/system/marcbot-weather-report.timer
    sudo systemctl daemon-reload
    sudo systemctl enable --now marcbot-weather-report.timer

Manual service test:

    sudo systemctl start marcbot-weather-report.service
    sudo systemctl status marcbot-weather-report.service --no-pager
    sudo journalctl -u marcbot-weather-report.service -n 80 --no-pager

Timer check:

    sudo systemctl status marcbot-weather-report.timer --no-pager
    sudo systemctl list-timers --all | grep -E 'weather-report|NEXT'

The weather report requires local runtime config at:

    /srv/marcbot/config/weather-report.toml

and Telegram config in MarcBot's normal local config.

## Backup memory integration

The app-level backup script includes `/srv/marcbot/memory` in the archive.

After a successful backup, the script records a low-risk `backup_completed`
memory event using:

    python -m marcbot memory event add

This event is written after the archive, checksum, and latest marker are
created. The event itself will therefore be included in a later backup.
