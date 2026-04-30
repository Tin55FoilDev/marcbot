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
