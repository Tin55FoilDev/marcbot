# 🤖 MarcBot Project Plan

## 1. Purpose

MarcBot is a personal-only automation and assistant platform intended to replace the reliable subset of OpenClaw used by Marc.

The goal is not to clone OpenClaw. The goal is to build a smaller, more stable, testable, understandable system that supports Marc’s real workflows:

- Telegram-based control and notifications
- Scheduled reports and automation
- Safe named actions
- Local file and project management
- Optional LLM-assisted work
- Coding/project help, including small web-app games
- Long-term memory and project continuity
- Clear logs and diagnostics
- Controlled updates

MarcBot favors reliability, security, and maintainability over feature count.

---

## 2. Operating Assumptions

MarcBot is designed for a single trusted user: Marc.

The system will run on a dedicated Ubuntu Server VM:

- Hostname: marcbot01
- OS target: Ubuntu 26.04 LTS
- Runtime user: marc
- Project root: /srv/marcbot
- Git repo: /srv/marcbot/app
- Remote repo: GitHub private repository

MarcBot is expected to run long-term with minimal churn. Updates should generally be limited to:

- Security fixes
- Major reliability fixes
- Major memory leak or performance fixes
- Carefully selected feature additions
- Python/package updates only when justified

The platform should avoid unnecessary framework dependencies and should prefer ordinary Linux primitives where practical.

---

## 3. Design Priorities

Priorities, in order:

1. Reliability
2. Security
3. Clear diagnostics
4. Testability
5. Maintainability
6. Controlled feature growth
7. Convenience

MarcBot should be boring where possible.

MarcBot should not become a large opaque agent framework.

---

## 4. Core Design Principles

### 4.1 Explicit Commands First

MarcBot should initially expose explicit named commands rather than arbitrary shell execution.

Examples:

- /status
- /ping
- /help
- /run-health-check
- /run-backup-report
- /projects
- /new-game
- /tail-log

Arbitrary shell execution from Telegram is out of scope until a clear security policy exists.

### 4.2 Deterministic Plumbing Before AI

The first working system should prove:

- Telegram communication
- systemd service management
- logging
- cron or timer-triggered notifications
- file layout
- test harness

LLM calls should be added only after the non-LLM foundation is stable.

### 4.3 Clear Operator-Facing Errors

MarcBot should avoid dumping raw Python tracebacks to Telegram or normal CLI output.

Operator-facing errors should be concise and identifiable.

Example:

ERROR [MBOT-CONFIG-001]: Missing config file: /srv/marcbot/config/marcbot.yaml

Detailed exceptions and tracebacks may be written to logs for debugging.

### 4.4 Testable Units

Where practical, features should be written as testable Python functions with pytest coverage.

At minimum, tests should cover:

- path handling
- config validation
- command routing
- error formatting
- safe action registration
- basic CLI behavior

### 4.5 Small Dependency Surface

Dependencies should be added deliberately.

Before adding a dependency, ask:

- Is it necessary?
- Is it actively maintained?
- Does it introduce security risk?
- Can the same result be achieved simply with the standard library?
- Is it stable on the project’s Python version?

### 4.6 Ordinary Linux Primitives

Prefer:

- systemd for services
- cron or systemd timers for scheduled jobs
- files for logs and reports
- Git for source control
- Python virtual environments for dependency isolation
- simple Markdown for documentation and memory

---

## 5. Directory Layout

Target layout:

/srv/marcbot/
├── app/          # Git repository and Python application
├── state/        # Runtime state, not committed
├── workspace/    # Bot-created projects, reports, and files
├── logs/         # Runtime logs, not committed
├── config/       # Local config and secrets, not committed
├── backups/      # Optional backups
└── tmp/          # Runtime temporary files

Application repo layout:

/srv/marcbot/app/
├── marcbot/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── errors.py
│   ├── logging_setup.py
│   └── paths.py
├── scripts/
├── systemd/
├── tests/
├── docs/
│   ├── DESIGN.md
│   └── PROJECT_PLAN.md
├── README.md
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt

---

## 6. Error Code Families

MarcBot should use stable error code families.

Initial families:

- MBOT-CONFIG-xxx
- MBOT-CLI-xxx
- MBOT-TELEGRAM-xxx
- MBOT-LLM-xxx
- MBOT-FILES-xxx
- MBOT-SYSTEMD-xxx
- MBOT-CRON-xxx
- MBOT-SECURITY-xxx
- MBOT-UNKNOWN-xxx

Operator-facing messages should include the code.

Logs should include enough context to diagnose the problem.

---

## 7. Initial Development Phases

### Phase 1 — Python Foundation

Goal: create a testable Python application baseline.

Deliverables:

- Python virtual environment
- minimal package structure
- CLI entry point
- version command
- doctor command
- logging conventions
- error-handling conventions
- pytest test harness
- Git commit and push

Success checks:

- python -m marcbot --version
- python -m marcbot doctor
- pytest -q
- git status clean

### Phase 2 — Telegram Foreground Bot

Goal: prove Telegram communication manually before systemd.

Deliverables:

- Telegram bot dependency
- local config file template
- secure token loading
- /ping command
- /help command
- foreground run mode
- clear error if token/config is missing
- tests for command handlers where practical

Success checks:

- bot starts manually
- /ping returns a response
- missing config produces clear MBOT-CONFIG error
- logs are readable

### Phase 3 — systemd Service

Goal: run MarcBot as a managed service.

Deliverables:

- systemd unit file
- environment handling
- restart policy
- logging path
- startup validation
- service status instructions

Success checks:

- service starts
- service survives reboot
- logs are visible
- /ping works after reboot

### Phase 4 — Scheduled Notifications

Goal: prove cron or timer-triggered outbound messages.

Deliverables:

- send-test-message script
- cron or systemd timer example
- log output
- failure handling

Success checks:

- scheduled test message arrives
- failure is logged clearly

### Phase 5 — Safe Named Actions

Goal: add controlled commands for useful workflows.

Initial actions:

- health check summary
- backup report
- project listing
- log tail
- report delivery

Success checks:

- each action has a named function
- no arbitrary shell execution from Telegram
- each action logs start, success, and failure
- errors return clean MBOT-* messages

### Phase 6 — LLM Routing

Goal: add explicit model calls after the base system is stable.

Potential providers:

- OpenAI / GPT models
- LM Studio OpenAI-compatible endpoint
- Anthropic
- Gemini

Design rule:

No hidden fallback magic at first. The requested model/provider should be explicit.

Success checks:

- local LM Studio test works
- OpenAI test works
- provider failure returns clear error
- no provider failure crashes the bot

### Phase 7 — Coding Project Helpers

Goal: support small web-app/game projects.

Initial commands may include:

- /projects
- /new-game NAME
- /describe-project NAME
- /project-status NAME

Generated project layout example:

workspace/games/turtle-race/
├── README.md
├── TODO.md
├── CHANGELOG.md
└── src/

Success checks:

- project scaffold is created safely
- invalid names are rejected
- existing projects are not overwritten without explicit handling

### Phase 8 — Memory and Continuity

Goal: add simple durable memory.

Start with Markdown files and simple search.

Potential layout:

workspace/memory/
├── daily/
├── projects/
├── user/
└── index/

Do not start with vector memory.

Success checks:

- memory files are readable
- project notes are updateable
- search is simple and explainable

### Phase 9 — Update Mechanism

Goal: provide a controlled CLI update process.

Possible future command:

marcbot-admin update

Update process should eventually:

- check Git status
- pull from GitHub
- install/update dependencies if required
- run tests
- restart service only if tests pass
- provide rollback guidance

This is not part of the initial implementation.

---


## 8. Initial Non-Goals

### Source monitor direction

MarcBot may include a narrow allowlisted source monitor for Marc's broader AI information workflow.

The source monitor should use explicit local configuration, validate sources before use, and produce local Markdown reports. It should not become open-ended browsing, arbitrary URL fetching from Telegram, or an autonomous web agent.

Real operational source config belongs outside Git under /srv/marcbot/config/source-projects/<project>/sources.toml. The current AI project uses /srv/marcbot/config/source-projects/ai/sources.toml. Git may contain only safe examples such as docs/examples/sources.example.toml.

The source monitor should follow the same project standards as every other feature: small changes, tests where practical, ./scripts/check.sh, diff review, documentation updates, and commit/push only after clean validation.


MarcBot will not initially support:

- arbitrary shell execution from Telegram
- autonomous multi-agent behavior
- browser automation
- vector memory
- self-modifying skills
- public multi-user access
- complex approval workflows
- automatic background software updates

These may be reconsidered only after the core system is stable.

---

## 9. Security Posture

MarcBot is personal-only, but it should still be built carefully.

Initial security rules:

- run as non-root user marc
- keep secrets out of Git
- store local config under /srv/marcbot/config
- avoid logging secrets
- use explicit named actions
- validate user-supplied names and paths
- keep workspace writes inside /srv/marcbot/workspace
- avoid arbitrary command execution
- prefer least privilege
- document any elevated operation before adding it

---

## 10. Documentation Policy

Important behavior should be documented as it is added.

Primary docs:

- docs/PROJECT_PLAN.md
- docs/DESIGN.md
- README.md

Future docs may include:

- docs/INSTALL.md
- docs/OPERATIONS.md
- docs/SECURITY.md
- docs/TELEGRAM.md
- docs/LLM_ROUTING.md
- docs/UPDATES.md

The documentation should be useful enough that the system can be rebuilt or debugged later without relying on memory.

---

## 11. Current Status

Day 1 completed:

- Ubuntu VM created
- /srv/marcbot directory layout created
- Git repo initialized
- GitHub remote configured
- Initial project skeleton committed and pushed

Day 2 target:

- create project plan
- create Python foundation
- add tests
- verify local CLI behavior
- commit and push

