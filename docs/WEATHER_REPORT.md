# MarcBot weather report project

This document defines the initial MarcBot weather-report project.

The weather report is a small approved workflow intended to exercise MarcBot's
project lifecycle with a low-risk daily job.

## Goal

Fetch an approved National Weather Service forecast page for Westfield, MA,
extract the Detailed Forecast text, format the next three calendar days, save a
Markdown report artifact, and send the report to Telegram at 8:00 AM daily.

## Initial source

The initial source is Marc's current National Weather Service forecast page for
Westfield, MA.

The source URL should be stored in local runtime config:

    /srv/marcbot/config/weather-report.toml

The URL should not be accepted from Telegram.

Initial URL:

    https://forecast.weather.gov/MapClick.php?CityName=Westfield&state=MA&site=BOX&textField1=42.1389&textField2=-72.756&e=0

## Why this source is acceptable for the first version

The page is human-readable HTML, but it includes a predictable Detailed Forecast
section with period names such as `Today`, `Tonight`, `Monday`, and
`Monday Night`, followed by forecast text.

The first implementation may parse this Detailed Forecast section directly.

If the page structure proves brittle, the project should switch to a more
structured National Weather Service endpoint such as XML, text-only, or API
output.

## Non-goals for the first version

The first version should not:

- accept arbitrary URLs
- scrape arbitrary weather sites
- fetch weather for arbitrary Telegram-supplied locations
- require LLM provider contact
- expose secrets
- run browser automation
- parse radar images or maps
- provide emergency weather alerting
- replace official weather warnings

## Output

Reports should be written under:

    /srv/marcbot/workspace/weather/reports/

Suggested filename pattern:

    weather-report-YYYY-MM-DD-HHMMSS.md

The report should include:

- report title
- generation timestamp
- location/source label
- forecast source URL
- next three calendar days
- day and night period text when available
- two short summary sentences

## Telegram delivery

The scheduled 8:00 AM job should send the generated report to Marc through
Telegram.

The Telegram delivery path should use MarcBot's existing Telegram configuration
and authorization model where possible.

The report should be bounded and text-only for the first version.

## Scheduling

The intended schedule is daily at 8:00 AM America/New_York.

The preferred deployment mechanism is a systemd service and timer, following the
same project pattern as other MarcBot scheduled jobs.

Potential unit names:

    marcbot-weather-report.service
    marcbot-weather-report.timer

## CLI-first workflow

The project should be CLI-testable before scheduling.

Potential commands:

    python -m marcbot weather-report run
    python -m marcbot weather-report latest
    python -m marcbot weather-report send-latest

The exact command names may be adjusted during implementation.

## Summary behavior

The first version should use a deterministic summary, not an LLM summary.

This keeps the first scheduled Telegram job independent of local model
availability.

A future version may add an optional LLM-polished summary after the deterministic
workflow is stable.

## Safety boundaries

The weather report workflow must:

- fetch only the configured approved URL
- write only under the approved weather report artifact directory
- avoid arbitrary host file access
- avoid arbitrary Telegram file access
- avoid arbitrary Telegram URL fetching
- avoid provider contact in the first version
- log metadata without secrets
- fail with clear non-traceback messages where possible

## Testing requirements

The implementation should include tests for:

- config loading
- allowed URL handling
- Detailed Forecast parsing from sample HTML
- three-day grouping
- deterministic summary generation
- Markdown report rendering
- artifact writing under the approved directory
- safe failure when the Detailed Forecast section is missing

Scheduled service/timer deployment should be validated manually after CLI tests
pass.

## Manual Telegram delivery

After a report has been generated, the latest weather report can be sent to
Telegram with:

    python -m marcbot weather-report send-latest

This command uses MarcBot's existing Telegram configuration and sends the newest
weather report artifact to the configured allowed chat IDs.

It does not fetch a new forecast by itself.

## Telegram text delivery

For daily delivery, the preferred command is:

    python -m marcbot weather-report send-latest-text

This sends the latest generated weather report as a cleaned-up Telegram text
message instead of a file attachment.

The older document delivery command remains available for debugging or artifact
retrieval:

    python -m marcbot weather-report send-latest

## Combined run and Telegram text delivery

For scheduled daily delivery, the preferred command is:

    python -m marcbot weather-report run-send-text

This command:

1. fetches the configured weather forecast
2. writes a new Markdown report artifact
3. sends the newest weather report as cleaned Telegram text

This is the command intended for the daily 7:15 AM America/New_York systemd
service.

## Daily schedule

The intended daily delivery time is:

    7:15 AM America/New_York

This is early enough for the report to be waiting in Telegram before the normal
morning routine.

## Systemd service and timer

The weather report daily job uses:

    marcbot-weather-report.service
    marcbot-weather-report.timer

The service runs:

    /srv/marcbot/app/.venv/bin/python -m marcbot weather-report run-send-text

The timer runs daily at:

    7:15 AM America/New_York

The timer includes:

    Persistent=true
    RandomizedDelaySec=2m

Install deployed units:

    sudo cp /srv/marcbot/app/systemd/marcbot-weather-report.service /etc/systemd/system/marcbot-weather-report.service
    sudo cp /srv/marcbot/app/systemd/marcbot-weather-report.timer /etc/systemd/system/marcbot-weather-report.timer
    sudo chmod 644 /etc/systemd/system/marcbot-weather-report.service
    sudo chmod 644 /etc/systemd/system/marcbot-weather-report.timer
    sudo systemd-analyze verify /etc/systemd/system/marcbot-weather-report.service /etc/systemd/system/marcbot-weather-report.timer
    sudo systemctl daemon-reload
    sudo systemctl enable --now marcbot-weather-report.timer

Manual service run:

    sudo systemctl start marcbot-weather-report.service
    sudo systemctl status marcbot-weather-report.service --no-pager
    sudo journalctl -u marcbot-weather-report.service -n 80 --no-pager

Timer status:

    sudo systemctl status marcbot-weather-report.timer --no-pager
    sudo systemctl list-timers --all | grep -E 'weather-report|NEXT'
