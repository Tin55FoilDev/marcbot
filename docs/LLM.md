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

It is outside the Git repository and should not be committed.

Current provider pattern:

~~toml
[providers.lmstudio]
enabled = true
type = "openai_compatible"
base_url = "http://10.0.1.22:1234/v1"
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
    Base URL: http://10.0.1.22:1234/v1
    API key env: MARCBOT_LMSTUDIO_API_KEY


### `python -m marcbot llm models lmstudio`

Calls the LM Studio OpenAI-compatible endpoint:

~~text
GET /v1/models
~~

This verifies that MarcBot can authenticate to LM Studio and list currently visible
models.

### `python -m marcbot llm health local_fast`

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
MarcBot LLM health
Profile: local_fast
Provider: lmstudio
Model: google/gemma-4-e4b
Status: ok
Response: marcbot-ok
~~

### `python -m marcbot llm ask local_fast "Say OK in one sentence."`

Runs a bounded one-shot prompt through a configured profile.

This is CLI-only. It is intended for operator testing of profile-based completion before any task routing or Telegram-facing prompt workflows are added.

Safety boundaries:

- requires an explicit configured profile
- uses the profile's configured provider, model, temperature, and max_tokens
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
- LM Studio API is listening on `10.0.1.22:1234`.
- VLAN/firewall rules allow MarcBot to reach `10.0.1.22:1234`.
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

`/llm_status` is the first Telegram-facing LLM command.

It is read-only and bounded:

- Lists configured profiles.
- Runs the tiny health check for `local_fast`.
- Reads `/srv/marcbot/config/llm.env` from code.
- Does not accept arbitrary prompts.
- Does not expose secrets.
- Does not allow arbitrary provider/model selection.

Expected output includes:

~~text
🤖 MarcBot LLM status

Profiles: 3
- local_fast: google/gemma-4-e4b via lmstudio

Health check:
Profile: local_fast
Provider: lmstudio
Model: google/gemma-4-e4b
Status: ok
Response: marcbot-ok
~~
