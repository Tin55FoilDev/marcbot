# MarcBot Configuration

MarcBot local configuration lives outside Git at:

/srv/marcbot/config/marcbot.toml

This file may eventually contain secrets such as Telegram bot tokens and API keys.

Do not commit real config files or secrets to Git.

## Initial Example

```toml
[app]
name = "MarcBot"
environment = "development"

[telegram]
enabled = false
bot_token = ""
allowed_chat_ids = []
