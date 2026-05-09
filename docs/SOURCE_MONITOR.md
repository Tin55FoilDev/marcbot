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

## Source kinds

MarcBot currently supports these source kinds:

- `web_page` — bounded HTTPS fetch with basic HTML title extraction.
- `rss_feed` — bounded HTTPS fetch with deterministic RSS/Atom metadata extraction.
- `github_releases` — reserved source kind for GitHub release tracking.

### `rss_feed` sources

`rss_feed` is intended for RSS or Atom feeds such as release feeds, changelogs, and news feeds.

RSS/Atom parsing is deterministic and uses only bounded response bytes. MarcBot stores and reports metadata only:

- feed title
- latest item title
- latest item link
- latest item published/updated date

MarcBot does not fetch linked articles, summarize article bodies, call an LLM, or store feed bodies in state.

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

## Current report contents

The source monitor report currently includes bounded fetch metadata for each configured source:

    source name
    source kind
    URL
    fetched true/false
    HTTP status or n/a
    bounded bytes read
    basic HTML page title when available
    clean error text when applicable

The report does not yet parse articles, summarize content, classify importance, or send Telegram notifications.

## Deterministic state and change detection

Each source monitor project stores a small metadata state file under its project workspace.

    /srv/marcbot/workspace/source-projects/<project>/state/source-monitor-state.json

For the AI project:

    /srv/marcbot/workspace/source-projects/ai/state/source-monitor-state.json

This state file is used to classify each source result as:

    new
    changed
    unchanged

Change detection compares deterministic metadata from the current run against the previous run:

    HTTP status
    basic HTML page title
    clean error text

The state file does not store fetched page bodies or article content.

## Summary counts

Each report includes a compact summary section near the top, followed by deterministic observations that call out new, changed, and errored sources.

    Total sources checked
    New
    Changed
    Unchanged
    Errored

Errored counts include fetch failures such as timeouts, URL errors, HTTP errors, or OS errors. Disabled sources are reported in the per-source details but are not counted as errored.

## Telegram RSS highlights

`/report_status source <project>` includes a compact `RSS latest items` section when the newest local report contains `rss_feed` metadata.

The Telegram status view remains read-only:

- it reads only the newest local report;
- it does not perform network fetches;
- it does not fetch linked articles;
- it does not call an LLM;
- it remains bounded by the source-status character cap.

## Telegram report access

Source monitor report visibility is exposed through the generic report-status command:

    /report_status source ai

The command reads the newest local AI source monitor report and returns the compact summary section plus deterministic observations. Observations name new, changed, and errored sources without parsing article bodies or using an LLM.

The command does not fetch sources, parse articles, summarize content, classify importance, or call an LLM.

## Recommended AI source allowlist

The live AI source config is stored outside Git at `/srv/marcbot/config/source-projects/ai/sources.toml`.

Current recommended sources:

- `openai-news` — `https://openai.com/news/rss.xml`
- `anthropic-news` — `https://www.anthropic.com/news`
- `google-deepmind-news` — `https://deepmind.google/blog/`
- `huggingface-blog` — `https://huggingface.co/blog`
- `mistral-news` — `https://mistral.ai/news/`
- `meta-ai-blog` — `https://ai.meta.com/blog/`
- `lmstudio-changelog` — `https://lmstudio.ai/changelog`
- `langchain-blog` — `https://www.langchain.com/blog`

These sources cover frontier/small model announcements, local model tooling, and AI agent framework news. RSS URLs may be configured as `kind = "web_page"` until MarcBot has a dedicated `rss_feed` source kind.

## Source notes

- `openai-news` should use `https://openai.com/news/rss.xml` rather than the HTML news page. The HTML page may reject simple bounded fetches with HTTP 403, while the RSS feed is more suitable for deterministic monitoring.

## Scheduled local report generation

The AI source monitor can be run by systemd using:

    marcbot-source-monitor-ai.service
    marcbot-source-monitor-ai.timer

The service runs:

    python -m marcbot source-monitor run ai

The scheduled job writes local reports only. It does not send Telegram messages, call an LLM, or perform Telegram-triggered network fetches.

The latest report summary is available through:

    /report_status source ai

Timer health is visible through:

    /timer_status

## Deployment note

The source monitor systemd unit templates are tracked in Git:

    /srv/marcbot/app/systemd/marcbot-source-monitor-ai.service
    /srv/marcbot/app/systemd/marcbot-source-monitor-ai.timer

The live installed unit files are:

    /etc/systemd/system/marcbot-source-monitor-ai.service
    /etc/systemd/system/marcbot-source-monitor-ai.timer

Keep the tracked templates synchronized with the installed units. See `docs/DEPLOY.md` and `docs/RESTORE.md` for install and recovery commands.


## Source monitor status

`python -m marcbot source-monitor status ai` shows the latest saved source-monitor artifacts.

The status output includes:

- configuration validity
- config path
- reports directory
- summaries directory
- recent report filenames
- recent summary filenames
- latest report path
- latest report modified time and age
- generated timestamp from the report
- compact report state
- latest summary path
- latest summary modified time and age
- summary freshness relative to the latest report
