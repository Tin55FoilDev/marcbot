"""Tests for MarcBot CLI behavior."""

import logging

from marcbot import __version__
from marcbot.cli import main


def test_version_command(capsys) -> None:
    result = main(["--version"])
    captured = capsys.readouterr()

    assert result == 0
    assert f"MarcBot {__version__}" in captured.out


def test_help_command(capsys) -> None:
    result = main([])
    captured = capsys.readouterr()

    assert result == 0
    assert "MarcBot personal automation CLI" in captured.out


def test_config_check_missing_file_returns_error(capsys, monkeypatch, tmp_path) -> None:
    missing_config = tmp_path / "missing.toml"
    test_log = tmp_path / "marcbot-test.log"

    import marcbot.cli as cli

    def configure_test_logging() -> None:
        logging.basicConfig(
            filename=test_log,
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            force=True,
        )

    monkeypatch.setattr(cli, "DEFAULT_CONFIG_PATH", missing_config)
    monkeypatch.setattr(cli, "configure_logging", configure_test_logging)

    result = main(["config-check"])
    captured = capsys.readouterr()

    logging.shutdown()

    assert result == 1
    assert "ERROR [MBOT-CONFIG-001]" in captured.err
    assert test_log.is_file()
    assert str(missing_config) in test_log.read_text(encoding="utf-8")

def test_llm_profile_missing_config_returns_error(capsys, monkeypatch, tmp_path) -> None:
    missing_config = tmp_path / "missing-llm-providers.toml"

    import marcbot.cli as cli
    from marcbot.llm_config import load_llm_config

    def load_missing_llm_config():
        return load_llm_config(missing_config)

    monkeypatch.setattr(cli, "load_llm_config", load_missing_llm_config)

    result = main(["llm", "profile", "local_fast"])
    captured = capsys.readouterr()

    assert result == 1
    assert "ERROR [MBOT-LLM-001]" in captured.err
    assert str(missing_config) in captured.err

def test_llm_ask_missing_config_returns_error(capsys, monkeypatch, tmp_path) -> None:
    missing_config = tmp_path / "missing-llm-providers.toml"

    import marcbot.cli as cli
    from marcbot.llm_config import load_llm_config

    def load_missing_llm_config():
        return load_llm_config(missing_config)

    monkeypatch.setattr(cli, "load_llm_config", load_missing_llm_config)

    result = main(["llm", "ask", "local_fast", "Say hello."])
    captured = capsys.readouterr()

    assert result == 1
    assert "ERROR [MBOT-LLM-001]" in captured.err
    assert str(missing_config) in captured.err

def test_llm_tasks_missing_config_returns_error(capsys, monkeypatch, tmp_path) -> None:
    missing_config = tmp_path / "missing-llm-tasks.toml"

    import marcbot.cli as cli
    from marcbot.llm_tasks import load_llm_task_config

    def load_missing_llm_task_config():
        return load_llm_task_config(missing_config)

    monkeypatch.setattr(cli, "load_llm_task_config", load_missing_llm_task_config)

    result = main(["llm", "tasks"])
    captured = capsys.readouterr()

    assert result == 1
    assert "ERROR [MBOT-LLM-041]" in captured.err
    assert str(missing_config) in captured.err


def test_llm_task_missing_config_returns_error(capsys, monkeypatch, tmp_path) -> None:
    missing_config = tmp_path / "missing-llm-tasks.toml"

    import marcbot.cli as cli
    from marcbot.llm_tasks import load_llm_task_config

    def load_missing_llm_task_config():
        return load_llm_task_config(missing_config)

    monkeypatch.setattr(cli, "load_llm_task_config", load_missing_llm_task_config)

    result = main(["llm", "task", "report_summary"])
    captured = capsys.readouterr()

    assert result == 1
    assert "ERROR [MBOT-LLM-041]" in captured.err
    assert str(missing_config) in captured.err

def test_llm_ask_task_missing_task_config_returns_error(
    capsys, monkeypatch, tmp_path
) -> None:
    missing_config = tmp_path / "missing-llm-tasks.toml"

    import marcbot.cli as cli
    from marcbot.llm_tasks import load_llm_task_config

    def load_missing_llm_task_config():
        return load_llm_task_config(missing_config)

    monkeypatch.setattr(cli, "load_llm_task_config", load_missing_llm_task_config)

    result = main(["llm", "ask-task", "report_summary", "Say hello."])
    captured = capsys.readouterr()

    assert result == 1
    assert "ERROR [MBOT-LLM-041]" in captured.err
    assert str(missing_config) in captured.err


def test_llm_ask_task_unknown_task_returns_error(capsys, monkeypatch, tmp_path) -> None:
    task_config = tmp_path / "llm-tasks.toml"
    task_config.write_text(
        """
[tasks.report_summary]
profile = "local_fast"
""",
        encoding="utf-8",
    )

    import marcbot.cli as cli
    from marcbot.llm_tasks import load_llm_task_config

    def load_test_llm_task_config():
        return load_llm_task_config(task_config)

    monkeypatch.setattr(cli, "load_llm_task_config", load_test_llm_task_config)

    result = main(["llm", "ask-task", "missing_task", "Say hello."])
    captured = capsys.readouterr()

    assert result == 1
    assert "ERROR [MBOT-LLM-046]" in captured.err
    assert "missing_task" in captured.err

def test_llm_summarize_file_missing_file_returns_error(
    capsys, monkeypatch, tmp_path
) -> None:
    import marcbot.cli as cli

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    def load_missing_summary_input(path):
        from marcbot.llm_file_summary import load_workspace_summary_input

        return load_workspace_summary_input(path, workspace_dir=workspace)

    monkeypatch.setattr(cli, "load_workspace_summary_input", load_missing_summary_input)

    result = main(["llm", "summarize-file", "report_summary", "missing.md"])
    captured = capsys.readouterr()

    assert result == 1
    assert "ERROR [MBOT-LLM-052]" in captured.err
    assert "missing.md" in captured.err
