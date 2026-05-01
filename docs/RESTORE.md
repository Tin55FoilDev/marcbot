# MarcBot Restore Drill

This document describes how to recover MarcBot from the current known-good baseline.

Current baseline:

    MarcBot 0.2.0

Primary recovery layers:

    1. Proxmox VM backup
    2. MarcBot app-level backup tarball
    3. GitHub repository

The preferred recovery path depends on what failed.

---

## 1. Recovery decision guide

### Use Proxmox restore when

Use the full Proxmox VM backup if the VM itself is damaged, missing, badly misconfigured, or the fastest safe recovery is to roll the whole server back.

Examples:

    - failed OS upgrade
    - broken Python/systemd environment
    - damaged filesystem
    - accidental deletion of /srv/marcbot
    - unknown system-level damage

This should restore:

    - Ubuntu server state
    - users and permissions
    - systemd services/timers
    - MarcBot app
    - local config
    - workspace
    - logs
    - backups that existed at backup time

### Use MarcBot app-level backup when

Use the app-level tarball if the VM is healthy but MarcBot files need to be restored.

Examples:

    - damaged /srv/marcbot/app
    - damaged /srv/marcbot/config
    - damaged /srv/marcbot/state
    - damaged /srv/marcbot/workspace
    - need to roll MarcBot back without restoring the whole VM

The app-level backup includes:

    /srv/marcbot/app
    /srv/marcbot/config
    /srv/marcbot/state
    /srv/marcbot/workspace
    /srv/marcbot/logs

The app-level backup excludes:

    /srv/marcbot/app/.venv
    /srv/marcbot/backups
    /srv/marcbot/tmp

### Use GitHub restore when

Use GitHub when only the source tree needs to be recovered or compared.

Examples:

    - source file accidentally changed
    - docs accidentally changed
    - need clean source checkout
    - app-level backup unavailable

GitHub does not restore local secrets/config by itself.

Important local-only file:

    /srv/marcbot/config/marcbot.toml

This file contains local configuration such as the Telegram bot token and allowed chat ID. Do not commit it to GitHub.

---

## 2. Current runtime layout

MarcBot project root:

    /srv/marcbot

Important paths:

    /srv/marcbot/app
    /srv/marcbot/config
    /srv/marcbot/state
    /srv/marcbot/workspace
    /srv/marcbot/logs
    /srv/marcbot/backups
    /srv/marcbot/tmp

Main Telegram service:

    marcbot-telegram.service

Daily app backup timer:

    marcbot-backup.timer

Daily backup service:

    marcbot-backup.service

---

## 3. Pre-restore safety checklist

Before restoring MarcBot files on a running VM:

    sudo systemctl stop marcbot-telegram.service
    sudo systemctl stop marcbot-backup.timer

Check service state:

    sudo systemctl is-active marcbot-telegram.service || true
    sudo systemctl is-active marcbot-backup.timer || true

Expected:

    inactive
    inactive

If practical, preserve the current damaged state before overwriting it:

    sudo tar -czf /root/marcbot-pre-restore-snapshot-$(date +%Y%m%d-%H%M%S).tar.gz /srv/marcbot

---

## 4. Restore from Proxmox VM backup

Use this when restoring the whole server.

High-level process:

    1. Shut down or isolate the damaged VM.
    2. Restore the known-good Proxmox VM backup.
    3. Boot the restored VM.
    4. Confirm network identity and IP address.
    5. Confirm MarcBot service and timer state.
    6. Confirm Telegram responds.

After VM restore, run:

    hostname
    ip -br addr
    systemctl status marcbot-telegram.service --no-pager
    systemctl status marcbot-backup.timer --no-pager

Then test from Telegram:

    /version
    /health
    /backup_status
    /git
    /ls

Expected:

    MarcBot: 0.2.0

Expected health:

    Overall: healthy

---

## 5. Restore from MarcBot app-level backup tarball

Use this when the VM is healthy and only `/srv/marcbot` needs recovery.

### 5.1 Find the latest app-level backup

    sudo -u marc bash -lc '
    cat /srv/marcbot/backups/latest-backup.txt
    '

Expected fields include:

    name=
    path=
    sha256_path=
    created_iso=
    created_epoch=
    size_bytes=
    retention_days=

Extract the latest path:

    sudo -u marc bash -lc '
    awk -F= "/^path=/{print \$2}" /srv/marcbot/backups/latest-backup.txt
    '

### 5.2 Verify checksum

    sudo -u marc bash -lc '
    cd /srv/marcbot/backups
    sha_file="$(basename "$(awk -F= "/^sha256_path=/{print \$2}" latest-backup.txt)")"
    sha256sum -c "$sha_file"
    '

Expected:

    OK

### 5.3 Inspect archive contents

    sudo -u marc bash -lc '
    latest="$(awk -F= "/^path=/{print \$2}" /srv/marcbot/backups/latest-backup.txt)"
    tar -tzf "$latest" | head -80
    '

Expected contents should include:

    srv/marcbot/app/
    srv/marcbot/config/
    srv/marcbot/state/
    srv/marcbot/workspace/
    srv/marcbot/logs/

Expected contents should not include:

    srv/marcbot/app/.venv
    srv/marcbot/backups
    srv/marcbot/tmp

### 5.4 Stop MarcBot services

    sudo systemctl stop marcbot-telegram.service
    sudo systemctl stop marcbot-backup.timer

### 5.5 Restore archive

This command extracts the backup back into `/srv/marcbot` paths because the archive stores paths relative to `/`.

    sudo bash -lc '
    latest="$(awk -F= "/^path=/{print \$2}" /srv/marcbot/backups/latest-backup.txt)"
    tar -xzf "$latest" -C /
    '

### 5.6 Recreate virtual environment if needed

The app-level backup intentionally excludes `.venv`.

If `.venv` is missing or broken:

    sudo -u marc bash -lc '
    cd /srv/marcbot/app
    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -r requirements-dev.txt
    '

### 5.7 Restore file ownership and permissions

    sudo chown -R marc:marc /srv/marcbot
    sudo chmod 700 /srv/marcbot/config
    sudo chmod 600 /srv/marcbot/config/marcbot.toml
    sudo chmod +x /srv/marcbot/app/scripts/check.sh
    sudo chmod +x /srv/marcbot/app/scripts/backup_marcbot.sh

### 5.8 Validate restored app

    sudo -u marc bash -lc '
    cd /srv/marcbot/app
    ./scripts/check.sh
    '

Expected:

    All MarcBot checks passed.

### 5.9 Restart services

    sudo systemctl daemon-reload
    sudo systemctl start marcbot-telegram.service
    sudo systemctl start marcbot-backup.timer

Check:

    sudo systemctl status marcbot-telegram.service --no-pager
    sudo systemctl status marcbot-backup.timer --no-pager

Telegram validation:

    /version
    /health
    /backup_status
    /git
    /ls

---

## 6. Restore from GitHub repository

Use this when source files need to be restored from GitHub.

Repository:

    git@github.com:Tin55FoilDev/marcbot.git

### 6.1 Stop service

    sudo systemctl stop marcbot-telegram.service

### 6.2 Preserve current app directory

    sudo bash -lc '
    timestamp="$(date +%Y%m%d-%H%M%S)"
    mv /srv/marcbot/app "/srv/marcbot/app.broken-${timestamp}"
    '

### 6.3 Clone fresh source

    sudo -u marc bash -lc '
    cd /srv/marcbot
    git clone git@github.com:Tin55FoilDev/marcbot.git app
    '

### 6.4 Recreate virtual environment

    sudo -u marc bash -lc '
    cd /srv/marcbot/app
    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -r requirements-dev.txt
    '

### 6.5 Confirm local config still exists

    sudo -u marc bash -lc '
    test -f /srv/marcbot/config/marcbot.toml
    ls -l /srv/marcbot/config/marcbot.toml
    '

Expected:

    -rw------- ... /srv/marcbot/config/marcbot.toml

If local config is missing, restore it from a Proxmox backup or app-level backup. Do not recreate it by pasting secrets into chat.

### 6.6 Validate source

    sudo -u marc bash -lc '
    cd /srv/marcbot/app
    ./scripts/check.sh
    '

### 6.7 Restart service

    sudo systemctl start marcbot-telegram.service
    sudo systemctl status marcbot-telegram.service --no-pager

Telegram validation:

    /version
    /health
    /git
    /ls

---

## 7. Systemd restore notes

Repo copies of unit files are stored under:

    /srv/marcbot/app/systemd/

Installed unit files are stored under:

    /etc/systemd/system/

Expected installed units:

    /etc/systemd/system/marcbot-telegram.service
    /etc/systemd/system/marcbot-backup.service
    /etc/systemd/system/marcbot-backup.timer

If unit files need to be reinstalled from the repo:

    sudo cp /srv/marcbot/app/systemd/marcbot-telegram.service /etc/systemd/system/marcbot-telegram.service
    sudo cp /srv/marcbot/app/systemd/marcbot-backup.service /etc/systemd/system/marcbot-backup.service
    sudo cp /srv/marcbot/app/systemd/marcbot-backup.timer /etc/systemd/system/marcbot-backup.timer

    sudo systemctl daemon-reload
    sudo systemctl enable marcbot-telegram.service
    sudo systemctl enable marcbot-backup.timer

Then start:

    sudo systemctl start marcbot-telegram.service
    sudo systemctl start marcbot-backup.timer

---

## 8. Post-restore validation checklist

Run on server:

    sudo -u marc bash -lc '
    cd /srv/marcbot/app
    ./scripts/check.sh
    '

Check services:

    sudo systemctl status marcbot-telegram.service --no-pager
    sudo systemctl status marcbot-backup.timer --no-pager
    sudo systemctl list-timers --all | grep -E "marcbot-backup|NEXT"

Check logs:

    sudo -u marc tail -n 120 /srv/marcbot/logs/marcbot.log
    sudo journalctl -u marcbot-telegram.service -n 80 --no-pager

Test Telegram:

    /version
    /health
    /service
    /git
    /backup_status
    /ls
    /docs
    /doc restore

Expected:

    MarcBot: 0.2.0
    Overall: healthy
    Status: clean

---

## 9. Backup verification after restore

Run a fresh app-level backup after a successful restore:

    sudo -u marc bash -lc '
    cd /srv/marcbot
    /srv/marcbot/app/scripts/backup_marcbot.sh
    '

Verify:

    sudo -u marc bash -lc '
    cd /srv/marcbot/backups
    sha_file="$(basename "$(awk -F= "/^sha256_path=/{print \$2}" latest-backup.txt)")"
    sha256sum -c "$sha_file"
    cat latest-backup.txt
    '

Telegram:

    /backup_status

---

## 10. Success criteria

Restore is considered successful when all are true:

    - MarcBot Telegram service is active
    - backup timer is active
    - /version responds with expected version
    - /health reports healthy
    - /git reports expected branch/status
    - /backup_status reports healthy or understandable stale-backup warning
    - /ls works
    - /doc restore works
    - scripts/check.sh passes
    - no traceback appears in app or service logs

---

## 11. Do not do these during restore

Avoid:

    - committing local secrets to GitHub
    - pasting Telegram bot tokens into chat
    - restoring unverified tarballs
    - extracting archives without checking contents first
    - enabling arbitrary shell execution from Telegram
    - deleting the damaged state before preserving a snapshot, unless disk pressure forces it
