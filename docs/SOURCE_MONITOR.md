# MarcBot Source Monitor

The MarcBot source monitor is intended to support Marc's broader AI information workflow.

The goal is to monitor a small, explicit allowlist of useful AI-related sources and produce local Markdown reports that Marc can inspect, send, archive, and later use as inputs for higher-level analysis.

This feature must remain narrow, auditable, and testable.

## Purpose

The source monitor is for controlled source awareness, not open-ended browsing.

Initial use cases:

- AI provider news
- AI research/product announcements
- model release monitoring
- infrastructure/tooling release awareness
- future report inputs for daily or weekly AI summaries

The source monitor should help Marc understand important AI developments without turning MarcBot into a broad autonomous web agent.

## Current CLI commands

Validate the local source config:

    python -m marcbot source-monitor config-check ai

Generate a source monitor report:

    python -m marcbot source-monitor run ai

The current implementation has a report scaffold and config validation. Live fetching should be added only after the config and documentation are stable.

## Config policy

The real source monitor config lives outside Git:

    /srv/marcbot/config/source-projects/ai/sources.toml

This file is local operational config.

It should be owned by marc and protected:

    sudo chown marc:marc /srv/marcbot/config/source-projects/ai/sources.toml
    sudo chmod 600 /srv/marcbot/config/source-projects/ai/sources.toml

The real local config should not be committed to Git.

Git may contain a safe example template:

    docs/examples/sources.example.toml

## Source rules

Each configured source must be explicit and allowlisted.

Current validation rules:

- source name must be a safe lowercase slug
- source kind must be allowlisted
- source URL must use https://
- duplicate source names are rejected
- enabled must be true or false if present
- missing config is treated as a clean empty-source state

Current source kinds:

- web_page
- github_releases

## Security rules

The source monitor must not provide:

- arbitrary Telegram URL fetching
- arbitrary shell execution
- arbitrary file reads
- arbitrary file writes outside MarcBot report/workspace paths
- hidden background mutation of memory
- broad autonomous browsing

Future Telegram commands must remain bounded and allowlisted.

Good future Telegram command shape:

    /source_status
    /send_latest_source_report

Risky command shape to avoid:

    /fetch <any-url>
    /browse <any-site>
    /run <shell-command>

## Development rules

Each source monitor change should follow the MarcBot standard workflow:

1. Keep the change small and narrow.
2. Add or update tests where practical.
3. Run ./scripts/check.sh.
4. Review the diff.
5. Decide whether the change belongs in Git.
6. Decide whether documentation needs updating.
7. Commit and push only after clean validation.
8. For Telegram-facing or service changes:
   - restart the service
   - test from Telegram
   - inspect logs

## Design direction

MarcBot exists to avoid the instability and feature churn Marc experienced with OpenClaw.

For this feature, that means:

- prefer boring standard-library implementation where practical
- avoid dependencies unless clearly justified
- avoid large agent-framework behavior
- avoid adding features Marc does not actually use
- preserve deterministic behavior before adding LLM analysis
- keep reports local, inspectable, and easy to back up
- treat source fetching as an input pipeline, not as autonomous decision-making

## Initial AI source direction

The first practical source set should focus on a small number of high-signal AI sources.

Examples:

- OpenAI News
- Anthropic Newsroom
- Google DeepMind Blog
- Hugging Face Blog

Additional sources should be added deliberately, not in bulk.

Each new source should be evaluated for:

- usefulness to Marc
- signal-to-noise ratio
- stable URL behavior
- fetchability without special browser automation
- security/privacy implications

## Project layout

Source monitor projects are isolated by project name so future workflows do not overwrite each other.

    /srv/marcbot/config/source-projects/<project>/sources.toml
    /srv/marcbot/workspace/source-projects/<project>/reports/

The current AI source monitor project is named `ai`.

    /srv/marcbot/config/source-projects/ai/sources.toml
    /srv/marcbot/workspace/source-projects/ai/reports/

Project names must be safe lowercase slugs using only lowercase letters, numbers, underscores, and hyphens. The project name is not a filesystem path.

