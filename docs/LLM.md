# MarcBot LLM Provider and Profile Operations

MarcBot has a CLI-only LLM provider/profile foundation for controlled local model
testing and future task routing.

The current implementation is intentionally narrow:

- No Telegram arbitrary prompt interface.
- No automatic task routing to LLMs.
- No secrets in Git.
- No provider token in chat.
- No unrestricted model access from Telegram.
- CLI-only provider/profile inspection and health checks.

## Current config files

### `/srv/marcbot/config/llm-providers.toml`

This local-only TOML file defines providers and profiles.

Note: `192.0.2.10` is a documentation/test example address. Real local LLM
hostnames or IP addresses belong in `/srv/marcbot/config/llm-providers.toml`,
outside Git.

It is outside the Git repository and should not be committed.

Current provider pattern:

~~toml
[providers.lmstudio]
enabled = true
type = "openai_compatible"
base_url = "http://192.0.2.10:1234/v1"
api_key_env = "MARCBOT_LMSTUDIO_API_KEY"
timeout_seconds = 30
~~

Current profile pattern:

~~toml
[profiles.local_fast]
provider = "lmstudio"
model = "google/gemma-4-e4b"
temperature = 0.2
max_tokens = 500
intended_use = "low_risk_utility"
~~

Profiles are named MarcBot usage slots. Code and future tasks should target profiles,
not hardcoded model IDs.

### `/srv/marcbot/config/llm.env`

This local-only env file stores provider secrets.

Expected permissions:

~~text
-rw------- 1 marc marc ... /srv/marcbot/config/llm.env
~~

Current content pattern:

~~bash
MARCBOT_LMSTUDIO_API_KEY=...
~~

Rules:

- Keep this file outside Git.
- Keep mode `600`.
- Keep owner/group `marc:marc`.
- Do not paste the token into Telegram.
- Do not add this token to system-wide shell profiles unless there is a clear need.

## Current CLI commands

Run commands as the MarcBot runtime user:

~~bash
sudo -u marc env \
  HOME=/home/marc \
  GIT_PAGER=cat \
  PATH="/srv/marcbot/app/.venv/bin:/usr/local/bin:/usr/bin:/bin" \
  bash -lc '
set -e
cd /srv/marcbot/app

set -a
. /srv/marcbot/config/llm.env
set +a

python -m marcbot llm profiles
python -m marcbot llm profile local_fast
python -m marcbot llm models lmstudio
python -m marcbot llm health local_fast
python -m marcbot llm ask local_fast "Say OK in one sentence."
'
~~

### `python -m marcbot llm profiles`

Lists configured profiles from `/srv/marcbot/config/llm-providers.toml`.

This does not call the provider.

### `python -m marcbot llm profile local_fast`

Shows one configured profile and its provider details.

This command does not call the provider, load provider secrets, or send a prompt. It is intended for operator visibility before assigning profiles to future tasks.

Expected output shape:

    MarcBot LLM profile
    Name: local_fast
    Provider: lmstudio
    Provider type: openai_compatible
    Model: google/gemma-4-e4b
    Temperature: 0.2
    Max tokens: 500
    Intended use: low_risk_utility
    Provider enabled: yes
    Base URL: http://192.0.2.10:1234/v1
    API key env: MARCBOT_LMSTUDIO_API_KEY


### `python -m marcbot llm models lmstudio`

Calls the LM Studio OpenAI-compatible endpoint:

~~text
GET /v1/models
~~

This verifies that MarcBot can authenticate to LM Studio and list currently visible
models.

### `python -m marcbot llm health local_fast`

Runs an explicit health check for one named profile. This command contacts only the requested profile; it does not test every configured profile.

Calls the LM Studio OpenAI-compatible endpoint:

~~text
POST /v1/chat/completions
~~

The health prompt is intentionally tiny:

~~text
Reply exactly: marcbot-ok
~~

Expected output:

~~text
MarcBot LLM health check
Profile: local_fast
Provider: lmstudio
Model: google/gemma-4-e4b
Result: OK
Response: marcbot-ok
~~

### `python -m marcbot llm ask local_fast "Say OK in one sentence."`

Runs a bounded one-shot prompt through a configured profile.

This is CLI-only. It is intended for operator testing of profile-based completion before any task routing or Telegram-facing prompt workflows are added.

Safety boundaries:

- requires an explicit configured profile
- uses the profile's configured provider, model, temperature, and max_tokens
- rejects prompts longer than 4000 characters
- does not allow arbitrary provider URL override from the command line
- does not allow arbitrary model override from the command line
- does not provide tool access
- does not provide file access
- does not create conversation memory
- does not expose prompt access through Telegram

Expected output shape:

    MarcBot LLM completion
    Profile: local_fast
    Provider: lmstudio
    Model: google/gemma-4-e4b
    Finish reason: stop

    OK.


## Current LM Studio models observed

The current LM Studio `/v1/models` response showed:

~~text
google/gemma-4-e4b
openai/gpt-oss-20b
qwen3.6-35b-a3b
text-embedding-nomic-embed-text-v1.5
~~

Keep this section current when models are added, removed, renamed, or behavior changes.

## Current model behavior notes

### `google/gemma-4-e4b`

Current role:

~~text
local_fast
~~

Observed behavior:

- Works for deterministic MarcBot health checks.
- Returns final `message.content` correctly for `marcbot-ok`.
- Good current default for low-risk utility checks and early local LLM plumbing.

### `openai/gpt-oss-20b`

Observed behavior:

- Returns final `message.content` correctly for `marcbot-ok`.
- May also include a reasoning field.
- Useful candidate for comparison testing.

### `qwen3.6-35b-a3b`

Current role:

~~text
local_careful
~~

Observed behavior:

- For the tiny deterministic health check, it returned empty `message.content`.
- It filled `message.reasoning_content`.
- It hit `finish_reason = length` with the small health-check token budget.
- Do not use this as the basic MarcBot health-check model until reasoning/final-content
  behavior is better controlled.

This does not mean the model is unusable. It means MarcBot should treat it as
experimental for controlled testing rather than simple deterministic jobs.

### `text-embedding-nomic-embed-text-v1.5`

Observed role:

- Embedding model.
- Not a chat-completion model.
- Do not assign it to chat profiles.

## Task-to-profile mapping

MarcBot supports a separate local task mapping file:

    /srv/marcbot/config/llm-tasks.toml

This file maps stable MarcBot task names to configured LLM profiles. It lets future workflows request a purpose such as `report_summary` instead of hard-coding a provider or model.

Example:

    [tasks.report_summary]
    profile = "local_fast"
    description = "Summarize MarcBot reports with a local model"

Current inspection commands:

    python -m marcbot llm tasks
    python -m marcbot llm task report_summary

Current task-routed prompt command:

    python -m marcbot llm ask-task report_summary "Summarize this in one sentence: MarcBot is online."

The `ask-task` command resolves the task to its configured profile, then uses that profile's provider, model, temperature, max_tokens, and prompt guardrails.

Current workspace file summary commands:

    python -m marcbot llm summarize-file report_summary reports/example.md
    python -m marcbot llm summarize-file-save report_summary reports/example.md summaries/example.summary.md

The `summarize-file` command reads a UTF-8 text file from `/srv/marcbot/workspace`, builds a fixed summary prompt, and routes it through the configured LLM task.

The `summarize-file-save` command uses the same input boundary and writes the generated summary to a new workspace-relative output file. It refuses to overwrite existing files.

Safety boundaries:

- task mappings only point to already-configured LLM profiles
- task mappings do not define provider URLs
- task mappings do not define API keys
- task mappings do not expose prompts through Telegram
- task-routed prompts stay CLI-only
- task-routed prompts use the same 4000-character prompt guardrail as profile-based `llm ask`
- workspace file summaries only accept workspace-relative paths
- workspace file summaries reject absolute paths and parent traversal
- workspace file summaries reject files over 3000 characters before provider calls
- `summarize-file` prints output only
- `summarize-file-save` writes only to new workspace-relative files
- `summarize-file-save` refuses to overwrite existing files
- summary commands retry once when the provider returns empty response content
- saved summaries are written only after a successful non-empty provider response


## Source monitor summary workflow

The source monitor can generate a report and save an LLM summary in one CLI-only workflow:

    python -m marcbot source-monitor run-summary ai

Behavior:

- writes the source monitor report first
- summarizes the generated report through the configured `source_monitor_analysis` LLM task by default
- saves the summary under the same source project in the workspace `summaries/` directory
- uses the same workspace path, overwrite, empty-response retry, and non-empty-response safeguards as saved file summaries
- remains CLI-only and does not expose arbitrary Telegram prompt access


## Current profile guidance

Recommended current profile meanings:

~~text
local_fast
  Provider: lmstudio
  Model: google/gemma-4-e4b
  Use: low-risk utility checks, health checks, simple local tasks

local_careful
  Provider: lmstudio
  Model: qwen3.6-35b-a3b
  Use: experimental/local analysis only until final-content behavior is stable

local_experimental
  Provider: lmstudio
  Model: currently google/gemma-4-e4b
  Use: model comparison and controlled tests
~~

Future online/frontier profiles should follow the same pattern:

~~text
frontier_chat
frontier_analysis
~~

Those should be added only after there is a safe provider/auth design.

## Frontier model research boundary

MarcBot should eventually support frontier models if a stable, supportable path is found.

Marc currently does not plan to use per-call OpenAI API billing for MarcBot. The desired future path is subscription/OAuth-style access similar in purpose to the way OpenClaw currently uses `openai-codex/gpt-5.5`.

This is a research track, not current implementation.

Before implementation, MarcBot should document:

- what client or protocol would be used
- whether the path is stable enough for MarcBot
- whether the path is supported or likely to break
- where credentials are stored
- what files contain tokens or session material
- how credentials are protected
- how logout or revocation works
- how logs avoid credential leakage
- whether the path is consistent with the relevant service terms
- how MarcBot avoids becoming dependent on OpenClaw as a backend worker

Research rules:

- do not store frontier credentials in Git
- do not paste credentials into chat
- do not expose credentials through Telegram
- do not expose credentials through logs
- do not expose credentials through reports
- do not expose credentials through memory
- do not build Telegram-facing frontier chat until the provider boundary is understood
- start with CLI-only experiments
- document findings before implementation

OpenClaw may be studied as a reference point because it currently provides functionality Marc values. MarcBot should not simply call OpenClaw as a backend worker.

Reasons:

- MarcBot exists partly to avoid OpenClaw runtime churn
- depending on OpenClaw would import some of the same instability
- provider access should be understood and controlled directly where possible
- MarcBot should remain inspectable and independently testable

Fallback direction:

- keep using local models for bounded MarcBot workflows
- continue using OpenClaw separately where it remains useful
- defer direct frontier MarcBot integration until there is a safe path

## Safety boundary

The LLM foundation currently supports CLI-only inspection and health checks.

Allowed today:

- List configured LLM profiles.
- List models from an allowlisted configured provider.
- Run a tiny deterministic health check for a configured profile.

Not allowed today:

- Arbitrary Telegram prompt relay.
- Arbitrary URL/model/provider configuration from Telegram.
- User-provided shell commands.
- Secrets in Telegram.
- Secrets in Git.
- Background autonomous LLM task routing without explicit design.

## Troubleshooting

### HTTP 401 or 403

Meaning:

~~text
LM Studio rejected the request token.
~~

Check:

~~bash
set -a
. /srv/marcbot/config/llm.env
set +a
python -m marcbot llm models lmstudio
~~

Also confirm that `api_key_env` in `llm-providers.toml` matches the env var name in
`llm.env`.

### Empty health response content

Meaning:

~~text
The model returned no final message.content.
~~

Known case:

~~text
qwen3.6-35b-a3b may return reasoning_content with empty content.
~~

Use `local_fast` with `google/gemma-4-e4b` for the current health check.

### Model appears in LM Studio but not MarcBot

Check:

- LM Studio server is running.
- LM Studio API is listening on `192.0.2.10:1234`.
- VLAN/firewall rules allow MarcBot to reach `192.0.2.10:1234`.
- `/srv/marcbot/config/llm-providers.toml` has the correct base URL.
- `/srv/marcbot/config/llm.env` has the correct token.

## Development rules

- Keep tests offline and mocked.
- Use standard-library HTTP unless a dependency is clearly justified.
- Add one capability at a time.
- Validate with `./scripts/check.sh`.
- Review diffs before commit.
- Document model behavior changes as they are observed.

## Telegram status command

### `/llm_status`

`/llm_status` is a Telegram-facing read-only LLM status command.

It is read-only and bounded:

- Lists configured profiles.
- Does not contact providers.
- Does not run health checks.
- Does not load provider secrets.
- Does not accept arbitrary prompts.
- Does not expose secrets.
- Does not allow arbitrary provider/model selection.

Expected output includes:

~~text
🤖 MarcBot LLM status

Profiles: 3
- local_fast: google/gemma-4-e4b via lmstudio

Provider contact: not performed
Health checks: CLI-only via python -m marcbot llm health <profile>
~~

## Read-only LLM status

Use the combined status command to inspect local LLM provider and task-route configuration without contacting a model server.

Command:

    python -m marcbot llm status

This command loads the local provider and task config, reports the number of configured profiles and tasks, and verifies that every task route references an existing profile. It does not list remote models, run health checks, or send prompts.
 The optional `--verbose` flag adds local profile names, provider/model assignments, intended-use labels, and task routes. It still does not contact providers.

Command:

    python -m marcbot llm status --verbose
\n
## Chat-enabled profiles

LLM profiles may optionally include:

    chat_enabled = true

The default is false.

This field means the profile is approved for future Telegram chat mode. It does
not by itself expose chat commands, contact a provider, or start a chat session.

Example:

    [profiles.local_fast]
    provider = "lmstudio"
    model = "google/gemma-4-e4b"
    temperature = 0.2
    max_tokens = 500
    intended_use = "low_risk_utility"
    chat_enabled = false

A profile can be valid for CLI-only LLM commands and task routes while still not
being approved for Telegram chat.

## Telegram provider secret environment

CLI provider-contacting commands can load `/srv/marcbot/config/llm.env` from the
operator shell. Telegram provider-contacting features run inside
`marcbot-telegram.service`, so the service must load the same local environment
file explicitly.

The systemd unit should include:

    EnvironmentFile=/srv/marcbot/config/llm.env

This is required for provider-contacting Telegram chat to access variables such
as `MARCBOT_LMSTUDIO_API_KEY`. The env file remains local runtime configuration
and must not be committed.

## Chat profile token guidance

Profiles used for Telegram chat may need higher `max_tokens` than profiles used
for short utility checks or compact summaries.

When local chat context files are active, a chat prompt includes configured
context plus volatile conversation history. A low output-token setting can cause
local models to return truncated responses.

For local chat testing, `local_fast` worked better with:

    max_tokens = 1000

This value is a practical starting point, not a hard rule. Tune it per model,
hardware, and chat style.

Keep the profile explicitly chat-approved:

    chat_enabled = true

and keep provider secrets in `/srv/marcbot/config/llm.env`, not in Git.

## Memory context and provider contact

Memory context retrieval is local and separate from LLM/provider contact.
Selected future LLM workflows may retrieve bounded memory context before
building a prompt, but that retrieval must not contact a provider.

Provider contact remains controlled by explicit LLM commands, configured
task routes, and selected profiles. A memory context package may be included
in a prompt only after deterministic MarcBot code has assembled and bounded
the context.

This keeps local memory retrieval auditable and safe while allowing future
model-assisted workflows to benefit from project history and durable facts.

### Opt-in memory context for file summarization

`llm summarize-file` and `llm summarize-file-save` may include bounded
local memory context when explicitly requested with memory flags:

```bash
python -m marcbot llm summarize-file report_summary path.md --memory-query "weather report" --memory-project weather-report
python -m marcbot llm summarize-file-save report_summary path.md output.md --memory-query "weather report" --memory-project weather-report
```

Memory context retrieval remains local and provider-contact-free. Provider
contact still occurs only because the operator explicitly runs an `llm`
command routed through the configured task/profile.

### LLM environment loading note

Provider-contact CLI commands require the relevant provider secrets to be
present in the process environment. For LM Studio, this means
`MARCBOT_LMSTUDIO_API_KEY` must be loaded before commands such as:

```bash
python -m marcbot llm health local_fast
python -m marcbot llm summarize-file report_summary path.md
```

Operationally, Marc can source the local LLM environment file before manual
provider-contact tests:

```bash
set -a
. /srv/marcbot/config/llm.env
set +a
```

If direct LM Studio `curl` tests pass with Authorization but MarcBot LLM
commands return HTTP 401, verify that the shell running MarcBot has loaded
`/srv/marcbot/config/llm.env`. A future hardening step may make provider
secret loading more explicit or automatic for CLI provider-contact commands.
