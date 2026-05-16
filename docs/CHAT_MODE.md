# MarcBot chat mode

This document defines the first implementation target for MarcBot chat mode.

Chat mode is a future controlled Telegram conversation with a selected approved
LLM profile. It is provider-contacting by design, but it must remain bounded,
explicit, inspectable, and separate from command execution.

## Goal

Initial chat mode should let Marc have a bounded Telegram conversation with an
approved model profile.

The first version should support discussion, explanation, planning, drafting,
comparison, and lightweight analysis.

The first version should not execute actions.

## Non-goals for the first version

Initial chat mode should not:

- run shell commands
- run MarcBot CLI commands
- modify files
- read arbitrary files
- send arbitrary files
- browse arbitrary URLs
- fetch arbitrary web pages
- trigger workflows
- generate source-monitor reports
- summarize source-monitor reports
- send report artifacts
- update durable memory
- inspect secrets
- expose provider credentials
- accept arbitrary provider names
- accept arbitrary model IDs
- accept arbitrary tool requests

Chat may suggest a command or workflow that Marc can run separately, but chat
should not execute it automatically.

## Proposed first commands

Initial Telegram chat mode should use explicit session commands:

    /chat_start <profile>
    /chat_stop
    /chat_status
    /chat_clear

These commands are intentionally smaller than the long-term command set.

The following commands remain future design items:

    /chat_profile
    /chat_context

## Command behavior

### /chat_start <profile>

Starts a chat session for the authorized Telegram chat.

Required behavior:

- require an authorized Telegram chat ID
- require exactly one profile argument
- accept only configured and approved chat profiles
- reject unknown profiles
- reject profiles not approved for chat
- clearly state that chat contacts a model provider
- clearly state the active profile
- initialize volatile per-chat session state
- avoid sending provider secrets to Telegram
- avoid logging provider secrets or prompt text

Initial implementation may use a simple allowlist of chat-capable profiles.

A future implementation may add a dedicated config field such as:

    chat_enabled = true

or a profile intended-use category such as:

    intended_use = "chat"

### /chat_stop

Stops the active chat session for the authorized Telegram chat.

Required behavior:

- require an authorized Telegram chat ID
- clear volatile chat session state
- return a concise confirmation
- do not contact the model provider

### /chat_status

Reports chat state for the authorized Telegram chat.

Required behavior:

- require an authorized Telegram chat ID
- show whether chat is active
- show the selected profile when active
- show basic limits such as history size or prompt limit when available
- do not contact the model provider
- do not load provider secrets unless required to read local config safely

### /chat_clear

Clears volatile chat history while keeping the selected profile active.

Required behavior:

- require an authorized Telegram chat ID
- clear only chat session history
- do not clear durable memory
- do not delete artifacts
- do not contact the model provider
- return a concise confirmation

## Handling normal Telegram text

When chat mode is active, normal Telegram text messages from the authorized chat
may be treated as chat input.

Required behavior:

- ignore normal text from unauthorized chats
- keep slash commands routed to command handlers
- reject empty messages
- enforce a maximum input length
- enforce a maximum assembled prompt length
- send only bounded conversation context to the selected profile
- return bounded model output to Telegram
- handle provider errors with clean user-facing messages
- avoid tracebacks in Telegram
- avoid logging full prompt text
- avoid logging full response text
- log only metadata such as chat ID, profile, success/failure, and size counts

When chat mode is inactive, normal Telegram text should continue to be ignored
or handled by the existing fallback behavior.

## Session state

Initial chat session state should be volatile process memory.

The first version should not persist chat history to disk or durable memory.

Per authorized Telegram chat, state may include:

- active or inactive
- selected profile
- recent message history
- created timestamp
- updated timestamp

Because initial state is volatile, restarting the Telegram service may clear
active chat sessions. That is acceptable for the first implementation.

## History limits

Initial chat history should be small and bounded.

Suggested starting limits:

- maximum user message length: 4000 characters
- maximum stored exchanges: 6
- maximum assembled prompt characters: 12000
- maximum Telegram response characters: bounded below Telegram limits

These values can be adjusted after testing.

## Prompt boundary

The chat system prompt should define MarcBot's role and restrictions.

It should say that chat may:

- explain
- discuss
- plan
- draft
- compare
- summarize text provided directly in chat

It should say that chat must not claim it executed actions.

It should say that chat cannot read files, inspect the server, run commands,
fetch URLs, update memory, or access secrets unless a future approved workflow
explicitly provides that capability.

## Provider/profile boundary

Chat mode must use configured LLM profiles.

It must not accept:

- arbitrary provider URLs
- arbitrary provider names
- arbitrary model IDs
- arbitrary API keys
- arbitrary system prompts from Telegram
- arbitrary tool configuration from Telegram

The first version should support only profiles explicitly approved for chat.

Local profiles may be used for early testing. Frontier profiles should wait
until the frontier-provider path is documented and stable.

## Logging boundary

Chat logs should support debugging without exposing sensitive content.

Logs may include:

- command name
- authorized chat ID
- selected profile
- active or inactive state
- input size
- output size
- provider success or failure
- error codes or safe error summaries

Logs must not include:

- provider credentials
- full user prompts
- full model responses
- secret values
- arbitrary file contents
- large generated text

## Failure behavior

Chat mode should fail safely.

Examples:

- unknown profile: return a clean unknown-profile message
- profile not approved for chat: return a clean not-approved message
- provider unavailable: return a clean provider-unavailable message
- input too long: return a clean size-limit message
- no active session: do not accidentally contact a provider
- internal error: return a clean generic failure and log details locally

## Testing requirements

Initial chat mode should include tests for:

- command registration
- unauthorized `/chat_start`
- unknown profile rejection
- non-chat profile rejection
- successful `/chat_start`
- `/chat_status` active and inactive states
- `/chat_clear`
- `/chat_stop`
- normal text ignored when chat inactive
- normal text handled when chat active
- slash commands still handled as commands
- provider errors return clean Telegram messages
- prompt and response text are not logged directly
- no provider contact from `/chat_status`, `/chat_clear`, or `/chat_stop`

## Implementation sequence

A safe implementation sequence is:

1. Add chat design documentation.
2. Add config/design for chat-approved profiles.
3. Add in-memory chat session state helpers.
4. Add Telegram command handlers for status-only chat lifecycle commands.
5. Add tests for lifecycle commands without provider contact.
6. Add bounded provider-contacting text handling.
7. Add tests for model call success and failure.
8. Update command docs and help text.
9. Restart Telegram service.
10. Validate from Telegram.
11. Inspect logs.
12. Commit and push.

## Open decisions

Before implementation, decide:

1. How profiles are approved for chat.
2. Whether chat approval uses `intended_use`, a new config field, or a separate chat config.
3. Whether only one authorized chat can have an active session.
4. Exact input and history limits.
5. Whether the first version should use local profiles only.
6. Whether `/chat_start` should display an explicit provider-contact warning every time.

## Chat profile approval

Chat-capable profiles should be approved explicitly.

The initial config field for this is:

    chat_enabled = true

Profiles without this field, or with `chat_enabled = false`, must not be usable
with `/chat_start`.

This keeps chat exposure separate from general LLM profile existence. A profile
may be valid for CLI health checks, report summaries, or experiments without
being approved for Telegram chat.

## Session helper implementation

Initial chat session state should be implemented as a small in-memory helper
module before Telegram handlers are added.

The helper should support:

- start session
- stop session
- inspect active session
- clear history
- append bounded history messages
- report provider-contact-free status text

This helper must not load LLM config, load provider secrets, contact providers,
read files, write files, or persist memory. Telegram handlers should be layered
on top only after the helper is tested.

## Initial Telegram lifecycle commands

The first Telegram-facing chat implementation should add only lifecycle
commands:

    /chat_start <profile>
    /chat_status
    /chat_clear
    /chat_stop

This milestone should not handle normal Telegram text as chat input and should
not send prompts to a model provider. `/chat_start` may load local LLM
configuration to validate that the requested profile exists and has
`chat_enabled = true`.

## Active normal-text chat handling

After lifecycle commands are stable, normal Telegram text may be handled as chat
input only when chat mode is active.

Required behavior:

- ignore normal text when chat mode is inactive
- keep slash commands routed to command handlers
- enforce a bounded input length
- assemble a bounded prompt from volatile in-memory history
- call only the selected chat-approved profile
- append user and assistant messages to volatile history only after success
- return clean provider errors without tracebacks
- log metadata only, not full prompts or full responses

This does not add file access, URL access, workflow execution, memory writes, or
tool use.

## Telegram service environment for provider-contacting chat

Provider-contacting Telegram chat requires the Telegram system service to load
MarcBot's LLM secret environment file:

    /srv/marcbot/config/llm.env

The deployed service unit should include:

    EnvironmentFile=/srv/marcbot/config/llm.env

This file is local runtime configuration and must not be committed to Git. It
should be readable by the `marc` runtime user and should define provider secret
variables such as:

    MARCBOT_LMSTUDIO_API_KEY

Without this environment file, `/chat_start` may succeed, but normal chat text
can fail with provider authentication errors such as HTTP 401.

After changing the deployed systemd unit, run:

    sudo systemctl daemon-reload
    sudo systemctl restart marcbot-telegram.service

## Local chat context files

MarcBot chat should support local Markdown context files so chat can feel more
personal and useful without expanding runtime authority.

These files are local runtime configuration and should live outside Git:

    /srv/marcbot/config/chat/system.md
    /srv/marcbot/config/chat/agent.md
    /srv/marcbot/config/chat/user.md
    /srv/marcbot/config/chat/project.md

Git may include examples under a non-secret examples path, but the real local
files should not be committed.

### Purpose of each file

`system.md`

Defines local hard behavior boundaries for MarcBot chat. This file may reinforce
rules such as:

- do not claim to execute commands
- do not claim to read files
- do not claim to browse URLs
- do not claim to update memory
- do not expose secrets
- suggest approved commands or workflows instead of pretending to perform them

`agent.md`

Defines MarcBot's conversational identity and voice. This file may include:

- bot name
- role
- response style
- humor level
- excitement or enthusiasm level
- slang preference
- concision versus detail preference
- how technical or casual the bot should sound

Example content:

    Name: MarcBot
    Role: Marc's personal technical assistant
    Tone: clear, direct, technically precise, friendly
    Humor: light and occasional
    Excitement: moderate; encouraging but not gushy
    Slang: minimal
    Default style: practical and step-by-step for systems work

`user.md`

Defines durable Marc-specific preferences that make chat more useful. This file
may include preferences such as:

- use numbered steps for development work
- work one step at a time
- run tests before commit
- review diffs before commit
- avoid Python triple-quoted strings in command blocks
- prefer security, stability, and explicit behavior over broad automation

`project.md`

Defines current project context. For MarcBot, this may include:

- current baseline
- active milestone
- important repo paths
- operational constraints
- design direction
- known deferred items

This file should be editable as project focus changes.

### Authority and precedence

Local chat context files should shape conversation, not grant new permissions.

Prompt assembly should follow this precedence:

1. built-in MarcBot chat safety rules
2. `/srv/marcbot/config/chat/system.md`
3. `/srv/marcbot/config/chat/agent.md`
4. `/srv/marcbot/config/chat/user.md`
5. `/srv/marcbot/config/chat/project.md`
6. volatile chat history
7. current user message

Lower-precedence files must not override higher-precedence safety boundaries.

For example, `agent.md` may say to use light humor, but it must not be able to
override the built-in rule that chat cannot run shell commands or inspect
secrets.

### Size limits

Each local context file should have a small maximum size.

Suggested starting limits:

- maximum file size per context file: 8000 characters
- maximum combined local context: 20000 characters

If a file is too large, MarcBot should fail safely with a clean message or skip
that file with a clear status message. It should not silently send unexpectedly
large local context to a model provider.

### Secret handling

Local chat context files must not contain secrets.

They must not contain:

- Telegram bot tokens
- API keys
- OAuth tokens
- passwords
- private keys
- recovery codes
- full secret config files
- credential material copied from `.env` files

The files may contain non-secret preferences, project notes, and operational
guidance.

### Logging boundary

MarcBot should not log full chat context file contents.

Logs may include:

- which context files were found
- which context files were loaded
- file size counts
- combined prompt size
- success or failure

Logs must not include full context text, full user prompts, full model
responses, or secret values.

### Status visibility

A future `/chat_status` enhancement may show context-file status without showing
file contents.

Example:

    Chat context:
    - system.md: loaded
    - agent.md: loaded
    - user.md: loaded
    - project.md: missing

This would help Marc understand what context is active without exposing private
content through Telegram.

### Implementation sequence

A safe implementation sequence is:

1. Document the local chat context file model.
2. Add example files under a Git-tracked examples directory.
3. Add a helper that loads allowed local context files with size limits.
4. Add tests for missing files, loaded files, oversized files, and prompt order.
5. Add prompt assembly using built-in safety rules plus local context files.
6. Keep normal chat behavior unchanged except for richer prompt context.
7. Add `/chat_status` context-file visibility later.

## Chat context loader helper

MarcBot should load local chat context files through a dedicated helper before
the files are wired into live prompt assembly.

The helper should:

- load only approved filenames
- preserve prompt order
- ignore unrelated files
- handle missing files cleanly
- enforce per-file and combined size limits
- return safe status metadata without exposing file contents
- assemble context text only for provider prompt construction
- avoid logging full context contents

Initial approved filenames are:

    system.md
    agent.md
    user.md
    project.md

## Live prompt assembly with local context

When wired into live chat, local context should be inserted into the provider
prompt before volatile conversation history and the current user message.

Live chat must continue to:

- avoid logging full context contents
- report context loading failures cleanly
- avoid provider contact when context loading fails
- keep all file access limited to approved local chat context filenames
- keep context content out of Telegram status messages unless explicitly sent as
  part of a model prompt

## Chat profile output-token tuning

Chat-enabled profiles may need more output room than short utility or report
summary profiles.

When local chat context files are loaded, the prompt contains:

- built-in chat safety rules
- local `system.md`
- local `agent.md`
- local `user.md`
- optional local `project.md`
- volatile chat history
- the current user message

If a profile has too small a `max_tokens` value, local models may return
truncated replies or stop with `finish_reason=length`.

For the current local `local_fast` chat profile, runtime testing showed that:

    max_tokens = 1000

is more appropriate than a smaller utility-style limit when local chat context
files are active.

This is local runtime configuration in:

    /srv/marcbot/config/llm-providers.toml

It should not be committed to Git unless represented as a non-secret example.
