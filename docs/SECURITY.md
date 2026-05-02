# MarcBot Security Notes

MarcBot is a personal-only Telegram automation bot. This document records the current security model, assumptions, and guardrails.

## Security goals

MarcBot should be:

- Personal-only
- Predictable
- Easy to audit
- Safe to operate over Telegram
- Resistant to accidental secret exposure
- Easy to restore from backup
- Narrow in command scope
- Explicit about risky actions

MarcBot should not become a general-purpose remote shell.

## Current trust model

Current trusted operator:

- Marc

Current runtime user:

- `marc`

Current admin/operator user:

- `adminuser`

Current host:

- `marcbot01`

Current application root:

- `/srv/marcbot/app`

Current runtime root:

- `/srv/marcbot`

## Telegram access model

MarcBot uses Telegram for operator interaction.

Access is restricted by configured Telegram chat IDs:

- Config file: `/srv/marcbot/config/marcbot.toml`
- Config key: `telegram.allowed_chat_ids`

Important rule:

- If `allowed_chat_ids` is empty, no Telegram chats are authorized.

Unauthorized chats receive only:

    Unauthorized chat.

Unauthorized access attempts are logged with the attempted chat ID.

## Telegram token handling

The Telegram bot token is stored outside Git:

    /srv/marcbot/config/marcbot.toml

The real config file must not be committed.

Expected permissions:

    marc:marc 600 /srv/marcbot/config/marcbot.toml

Verification command:

    sudo stat -c "%U:%G %a %n" /srv/marcbot/config/marcbot.toml

Expected result:

    marc:marc 600 /srv/marcbot/config/marcbot.toml

If the token is accidentally exposed:

1. Stop the service.
2. Clear affected logs.
3. Strengthen redaction if needed.
4. Rotate the token in BotFather if exposure may have left the local environment.
5. Update `/srv/marcbot/config/marcbot.toml`.
6. Restart the service.
7. Test `/version`, `/health`, and `/logs`.

## Git safety

The repository should contain code, tests, and documentation.

The repository should not contain:

- Telegram bot tokens
- Real allowed chat IDs if avoidable
- API keys
- Passwords
- SSH private keys
- Personal credentials
- Generated logs
- Runtime state
- Backups
- Temporary files

Before each commit:

    sudo -u marc bash -lc '
    cd /srv/marcbot/app
    git status --short
    '

Review all changed files before committing.

## Runtime filesystem layout

MarcBot uses this runtime layout:

    /srv/marcbot/app       application repository
    /srv/marcbot/config    local config outside Git
    /srv/marcbot/logs      application logs
    /srv/marcbot/state     runtime state
    /srv/marcbot/workspace working files/reports
    /srv/marcbot/backups   backup-related files
    /srv/marcbot/tmp       temporary files

The application service runs as `marc`.

## Systemd service hardening

The current service uses systemd hardening controls, including:

- `NoNewPrivileges=true`
- `PrivateTmp=true`
- `ProtectSystem=full`
- `ProtectHome=true`
- `ReadWritePaths=/srv/marcbot`

Primary unit file:

    /etc/systemd/system/marcbot-telegram.service

Repository copy:

    /srv/marcbot/app/systemd/marcbot-telegram.service

After editing the service file:

    sudo cp /srv/marcbot/app/systemd/marcbot-telegram.service /etc/systemd/system/marcbot-telegram.service
    sudo systemctl daemon-reload
    sudo systemctl restart marcbot-telegram.service
    sudo systemctl status marcbot-telegram.service --no-pager

## Logging safety

MarcBot writes rotating application logs to:

    /srv/marcbot/logs/marcbot.log

The `/logs` Telegram command:

- Reads only `/srv/marcbot/logs/marcbot.log`
- Returns only the last fixed number of lines
- Does not accept arbitrary paths
- Redacts obvious Telegram-token-shaped strings
- Redacts the configured Telegram bot token if it appears
- Truncates long output before sending to Telegram

Log inspection from shell should be done as `marc`:

    sudo -u marc tail -n 80 /srv/marcbot/logs/marcbot.log

## Source monitor safety

The source monitor must remain allowlist-based.

Rules:

- Real source config lives outside Git under /srv/marcbot/config/source-projects/<project>/sources.toml.
- Git may contain safe examples only.
- URLs must be explicit and validated before use.
- Only HTTPS sources are allowed.
- Telegram must not accept arbitrary fetch URLs.
- Source monitor output must be bounded.
- Fetch failures must produce clean operator-facing errors or report entries.
- The feature must not become arbitrary browsing or shell execution.

Stop development if the source monitor can be used to read arbitrary local files, fetch arbitrary Telegram-supplied URLs, expose secrets, or write outside MarcBot workspace/report paths.


Telegram source-monitor report access is read-only:

- `/report_status source <project>` reads the newest local report summary for a validated project name.
- It must not fetch sources.
- It must not accept arbitrary URLs.
- It must not accept arbitrary local file paths.
- It must not call an LLM.
- It must keep Telegram output bounded.
- It should use the generic report-status pattern rather than one-off source-monitor commands.

Scheduled source-monitor runs are performed by systemd, not by Telegram:

    marcbot-source-monitor-ai.service
    marcbot-source-monitor-ai.timer



## Command safety rules

Current Telegram commands are intentionally narrow:

    /ping
    /version
    /status
    /health
    /logs
    /help

Current commands do not provide:

- Arbitrary shell execution
- Arbitrary file reads
- Arbitrary file writes
- Package updates
- System upgrades
- Remote code execution
- Open-ended model/tool routing

Future commands should follow these rules:

1. Prefer read-only commands first.
2. Use explicit allowlists.
3. Avoid arbitrary user-supplied file paths.
4. Avoid arbitrary shell command input.
5. Keep Telegram output bounded.
6. Log actions without logging secrets.
7. Add tests where practical.
8. Require confirmation for risky actions.
9. Keep dangerous operations out of Telegram unless there is a clear safety design.

## Safe command design

Good command pattern:

- Fixed command name
- Fixed data source
- Short bounded output
- Clear authorization check
- Clear log entry
- Tests for expected behavior

Example:

    /health

Risky command pattern:

- Accepts arbitrary shell text
- Accepts arbitrary file paths
- Can delete or overwrite files
- Can install packages
- Can expose secrets
- Has no confirmation step
- Has no tests

Example of what not to add:

    /run rm -rf ...
    /cat /any/path
    /exec arbitrary command text

## Confirmation policy for future actions

Risky actions should require confirmation.

Examples of actions that should require confirmation:

- Restarting a service
- Running an update
- Triggering a backup restore
- Deleting files
- Sending emails externally
- Running expensive model/report jobs
- Writing persistent memory entries from ambiguous input

A future confirmation flow should include:

- Action summary
- Short expiration window
- Clear confirm/cancel commands
- Logging of request and result
- No secret values in logs

## Error handling

Expected errors should use clean operator-facing messages.

Preferred pattern:

    ERROR [MBOT-CATEGORY-001]: Human-readable message

Do not normally expose Python tracebacks to Telegram.

Tracebacks may appear in local logs during development, but user-facing Telegram responses should stay clean and concise.

## Dependency safety

Current dependency surface is intentionally small.

Runtime dependency:

- `python-telegram-bot`

Development dependencies:

- `pytest`
- `ruff`

Guidelines:

- Avoid adding dependencies unless they clearly reduce risk or complexity.
- Pin dependencies in requirements files.
- Prefer boring, maintained libraries.
- Run tests after dependency changes.
- Commit dependency changes separately when possible.

## Model/backend safety

Model integrations are not part of the current baseline.

Future model integrations should:

- Be optional
- Have timeouts
- Fail cleanly
- Avoid logging sensitive prompts
- Avoid breaking non-model Telegram commands
- Keep endpoints and API keys outside Git
- Use a small provider abstraction

Local model backends may include LM Studio, vLLM, llama.cpp, or similar, but those should be added only after the foundation remains stable.

## Memory safety

Memory features are not part of the current baseline.

Future memory features should:

- Prefer Markdown files first
- Avoid storing secrets
- Avoid storing sensitive personal data unless explicitly requested
- Keep files inspectable by Marc
- Keep writes explicit and logged
- Avoid hidden background memory mutation until the design is clear

## Backup and restore security

VM or server backups should be treated as sensitive because they may contain:

- Telegram bot token
- Local config
- Logs
- Runtime state
- Future reports or memory files

Backup storage should be protected appropriately.

After restoring from backup:

1. Validate config permissions.
2. Validate service status.
3. Run `./scripts/check.sh`.
4. Test `/version`, `/health`, and `/logs`.
5. Confirm logs do not contain exposed secrets.

## Incident checklist

If something looks wrong:

1. Stop the service if needed:

       sudo systemctl stop marcbot-telegram.service

2. Inspect recent journal logs:

       sudo journalctl -u marcbot-telegram.service -n 120 --no-pager

3. Inspect application logs:

       sudo -u marc tail -n 120 /srv/marcbot/logs/marcbot.log

4. Check Git status:

       sudo -u marc bash -lc '
       cd /srv/marcbot/app
       git status --short
       '

5. Re-run validation:

       sudo -u marc bash -lc '
       cd /srv/marcbot/app
       ./scripts/check.sh
       '

6. Restart only after the issue is understood or rolled back:

       sudo systemctl restart marcbot-telegram.service

## Stop conditions

Pause development if:

- A secret appears in Telegram output.
- A secret appears in committed files.
- A command can read arbitrary files.
- A command can run arbitrary shell input.
- Tests fail for unclear reasons.
- The service becomes unreliable.
- The deploy/restore process becomes unclear.
- The command surface becomes too broad to audit.

## Current security standard

For each new feature:

1. Confirm it fits the personal-only model.
2. Prefer read-only behavior first.
3. Avoid arbitrary shell and arbitrary path input.
4. Add authorization checks.
5. Add tests where practical.
6. Run `./scripts/check.sh`.
7. Restart service.
8. Test from Telegram.
9. Inspect logs.
10. Commit and push only after clean validation.
