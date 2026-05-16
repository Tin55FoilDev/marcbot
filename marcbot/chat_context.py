"""Local Markdown chat context loading for MarcBot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from marcbot.errors import MarcBotError

CHAT_CONTEXT_FILENAMES = (
    "system.md",
    "agent.md",
    "user.md",
    "project.md",
)

DEFAULT_CHAT_CONTEXT_DIR = Path("/srv/marcbot/config/chat")
DEFAULT_MAX_FILE_CHARS = 8000
DEFAULT_MAX_TOTAL_CHARS = 20000


@dataclass(frozen=True)
class ChatContextFile:
    """One loaded local chat context file."""

    name: str
    path: Path
    content: str

    @property
    def char_count(self) -> int:
        """Return loaded character count."""

        return len(self.content)


@dataclass(frozen=True)
class ChatContextBundle:
    """Loaded local chat context files plus safe metadata."""

    context_dir: Path
    files: tuple[ChatContextFile, ...]

    @property
    def total_chars(self) -> int:
        """Return total loaded context characters."""

        return sum(item.char_count for item in self.files)

    @property
    def loaded_names(self) -> tuple[str, ...]:
        """Return loaded context filenames in prompt order."""

        return tuple(item.name for item in self.files)

    def format_status(self) -> str:
        """Return safe status text without exposing context contents."""

        lines = [
            "MarcBot chat context",
            f"Directory: {self.context_dir}",
            f"Loaded files: {len(self.files)}",
            f"Total chars: {self.total_chars}",
        ]

        loaded_by_name = {item.name: item for item in self.files}
        for name in CHAT_CONTEXT_FILENAMES:
            item = loaded_by_name.get(name)
            if item is None:
                lines.append(f"- {name}: missing")
            else:
                lines.append(f"- {name}: loaded ({item.char_count} chars)")

        return "\n".join(lines)

    def assemble_text(self) -> str:
        """Assemble loaded context content in prompt order."""

        sections = []
        for item in self.files:
            sections.append(f"## Local chat context: {item.name}\n\n{item.content}")
        return "\n\n".join(sections).strip()


def load_chat_context(
    *,
    context_dir: Path = DEFAULT_CHAT_CONTEXT_DIR,
    max_file_chars: int = DEFAULT_MAX_FILE_CHARS,
    max_total_chars: int = DEFAULT_MAX_TOTAL_CHARS,
) -> ChatContextBundle:
    """Load approved local chat context files with strict size limits."""

    if max_file_chars < 1:
        raise ValueError("max_file_chars must be at least 1")
    if max_total_chars < 1:
        raise ValueError("max_total_chars must be at least 1")

    loaded: list[ChatContextFile] = []
    total_chars = 0

    for name in CHAT_CONTEXT_FILENAMES:
        path = context_dir / name
        if not path.exists():
            continue
        if not path.is_file():
            raise MarcBotError(
                "MBOT-CHATCTX-001",
                f"Chat context path is not a file: {path}",
            )

        content = path.read_text(encoding="utf-8").strip()
        char_count = len(content)
        if char_count > max_file_chars:
            raise MarcBotError(
                "MBOT-CHATCTX-002",
                (
                    f"Chat context file is too large: {name} "
                    f"({char_count} > {max_file_chars} chars)"
                ),
            )

        if total_chars + char_count > max_total_chars:
            raise MarcBotError(
                "MBOT-CHATCTX-003",
                (
                    "Combined chat context is too large: "
                    f"{total_chars + char_count} > {max_total_chars} chars"
                ),
            )

        loaded.append(ChatContextFile(name=name, path=path, content=content))
        total_chars += char_count

    return ChatContextBundle(context_dir=context_dir, files=tuple(loaded))
