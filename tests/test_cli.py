"""Tests for MarcBot CLI behavior."""

import logging

import pytest

from marcbot import __version__
from marcbot.cli import main
from marcbot.errors import MarcBotError


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


def test_llm_ask_task_missing_task_config_returns_error(capsys, monkeypatch, tmp_path) -> None:
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


def test_llm_summarize_file_missing_file_returns_error(capsys, monkeypatch, tmp_path) -> None:
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


def test_llm_summarize_file_save_existing_output_returns_error(
    capsys, monkeypatch, tmp_path
) -> None:
    import marcbot.cli as cli

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    report = workspace / "report.md"
    report.write_text("report content", encoding="utf-8")
    output = workspace / "summary.md"
    output.write_text("existing", encoding="utf-8")

    def load_test_summary_input(path):
        from marcbot.llm_file_summary import load_workspace_summary_input

        return load_workspace_summary_input(path, workspace_dir=workspace)

    def resolve_test_summary_output(path):
        from marcbot.llm_file_summary import resolve_workspace_summary_output_path

        return resolve_workspace_summary_output_path(path, workspace_dir=workspace)

    monkeypatch.setattr(cli, "load_workspace_summary_input", load_test_summary_input)
    monkeypatch.setattr(
        cli,
        "resolve_workspace_summary_output_path",
        resolve_test_summary_output,
    )

    result = main(
        [
            "llm",
            "summarize-file-save",
            "report_summary",
            "report.md",
            "summary.md",
        ]
    )
    captured = capsys.readouterr()

    assert result == 1
    assert "ERROR [MBOT-LLM-061]" in captured.err


def test_summary_completion_retries_empty_response(monkeypatch) -> None:
    import marcbot.cli as cli
    from marcbot.llm_client import LlmCompletionResult

    calls = {"count": 0}

    def flaky_completion(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise MarcBotError("MBOT-LLM-035", "empty response")
        return LlmCompletionResult(
            profile_name=kwargs["profile_name"],
            provider_name=kwargs["provider"].name,
            model=kwargs["model"],
            response_text="Recovered summary",
            finish_reason="stop",
        )

    monkeypatch.setattr(cli, "run_openai_compatible_completion", flaky_completion)

    class Provider:
        name = "test-provider"

    result = cli._run_summary_completion_with_retry(
        provider=Provider(),
        profile_name="local_fast",
        model="test-model",
        prompt="Summarize this.",
        temperature=0.2,
        max_tokens=100,
    )

    assert calls["count"] == 2
    assert result.response_text == "Recovered summary"


def test_summary_completion_reraises_empty_after_retry(monkeypatch) -> None:
    import marcbot.cli as cli

    calls = {"count": 0}

    def empty_completion(**kwargs):
        calls["count"] += 1
        raise MarcBotError("MBOT-LLM-035", "empty response")

    monkeypatch.setattr(cli, "run_openai_compatible_completion", empty_completion)

    class Provider:
        name = "test-provider"

    with pytest.raises(MarcBotError) as excinfo:
        cli._run_summary_completion_with_retry(
            provider=Provider(),
            profile_name="local_fast",
            model="test-model",
            prompt="Summarize this.",
            temperature=0.2,
            max_tokens=100,
        )

    assert calls["count"] == 2
    assert excinfo.value.code == "MBOT-LLM-035"


def test_summary_completion_does_not_retry_non_empty_error(monkeypatch) -> None:
    import marcbot.cli as cli

    calls = {"count": 0}

    def auth_failure(**kwargs):
        calls["count"] += 1
        raise MarcBotError("MBOT-LLM-027", "auth failed")

    monkeypatch.setattr(cli, "run_openai_compatible_completion", auth_failure)

    class Provider:
        name = "test-provider"

    with pytest.raises(MarcBotError) as excinfo:
        cli._run_summary_completion_with_retry(
            provider=Provider(),
            profile_name="local_fast",
            model="test-model",
            prompt="Summarize this.",
            temperature=0.2,
            max_tokens=100,
        )

    assert calls["count"] == 1
    assert excinfo.value.code == "MBOT-LLM-027"


def test_support_snapshot_prints_redacted_restart_packet(capsys) -> None:
    result = main(["support", "snapshot"])
    captured = capsys.readouterr()

    assert result == 0
    assert "# MarcBot Support Snapshot" in captured.out
    assert "MarcBot version:" in captured.out
    assert "## Git" in captured.out
    assert "## Important docs" in captured.out
    assert "docs/SESSION_START.md:" in captured.out
    assert "## Security note" in captured.out
    assert "environment variables" in captured.out


def test_build_source_monitor_summary_input_compacts_large_report(tmp_path) -> None:
    from pathlib import Path

    from marcbot.cli import SOURCE_MONITOR_SUMMARY_INPUT_LIMIT, _build_source_monitor_summary_input

    report_path = tmp_path / "source-monitor-large.md"
    fetch_lines = []
    for index in range(30):
        fetch_lines.extend(
            [
                f"- source-{index}",
                "  - kind: web_page",
                "  - url: https://example.com",
                "  - fetched: true",
                "  - status: 200",
                "  - bytes_read: 262144",
                f"  - title: Example {index}",
                "  - latest_item_title: n/a",
                "  - change: unchanged",
                "  - error: none",
            ]
        )

    report_path.write_text(
        "\n".join(
            [
                "# MarcBot Source Monitor - ai - 2026-05-03",
                "",
                "## Status",
                "",
                "Source monitor installed.",
                "",
                "## Summary",
                "",
                "Total sources checked: 30",
                "New: 0",
                "Changed: 0",
                "Unchanged: 30",
                "Errored: 0",
                "",
                "## Observations",
                "",
                "No new, changed, or errored sources were detected.",
                "",
                "## Fetch results",
                *fetch_lines,
            ]
        ),
        encoding="utf-8",
    )

    compact = _build_source_monitor_summary_input(
        report_path,
        Path("source-projects/ai/reports/source-monitor-large.md"),
    )

    assert compact.requested_path == "source-projects/ai/reports/source-monitor-large.md"
    assert compact.resolved_path == report_path
    assert len(compact.text) <= SOURCE_MONITOR_SUMMARY_INPUT_LIMIT
    assert "## Summary" in compact.text
    assert "## Observations" in compact.text
    assert "## Fetch results" in compact.text
    assert "compacted source-monitor report input" in compact.text


def test_source_monitor_run_summary_writes_report_and_summary(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    import marcbot.cli as cli
    from marcbot.llm_client import LlmCompletionResult
    from marcbot.llm_config import LlmConfig, LlmProfileConfig, LlmProviderConfig
    from marcbot.llm_file_summary import (
        load_workspace_summary_input,
        resolve_workspace_summary_output_path,
        write_workspace_summary_output,
    )
    from marcbot.llm_tasks import LlmTaskConfig, LlmTaskProfile
    from marcbot.source_monitor import SourceMonitorResult

    workspace = tmp_path / "workspace"
    report_dir = workspace / "source-projects" / "ai" / "reports"
    report_dir.mkdir(parents=True)
    report_path = report_dir / "source-monitor-2026-05-02-120000.md"
    report_path.write_text("Source monitor report body", encoding="utf-8")

    monkeypatch.setattr(cli, "WORKSPACE_DIR", workspace)
    monkeypatch.setattr(
        cli,
        "load_workspace_summary_input",
        lambda requested_path: load_workspace_summary_input(
            requested_path,
            workspace_dir=workspace,
        ),
    )
    monkeypatch.setattr(
        cli,
        "resolve_workspace_summary_output_path",
        lambda requested_path: resolve_workspace_summary_output_path(
            requested_path,
            workspace_dir=workspace,
        ),
    )
    monkeypatch.setattr(
        cli,
        "write_workspace_summary_output",
        lambda requested_path, content: write_workspace_summary_output(
            requested_path,
            content,
            workspace_dir=workspace,
        ),
    )
    monkeypatch.setattr(
        cli,
        "write_source_monitor_report",
        lambda project_name: SourceMonitorResult(
            path=report_path,
            message=f"Source monitor report written: {report_path}",
        ),
    )
    monkeypatch.setattr(
        cli,
        "load_llm_task_config",
        lambda: LlmTaskConfig(
            tasks={
                "source_monitor_analysis": LlmTaskProfile(
                    name="source_monitor_analysis",
                    profile="local_fast",
                    description="Analyze source monitor output",
                )
            },
        ),
    )
    monkeypatch.setattr(
        cli,
        "load_llm_config",
        lambda: LlmConfig(
            path=tmp_path / "llm-providers.toml",
            providers={
                "lmstudio": LlmProviderConfig(
                    name="lmstudio",
                    enabled=True,
                    provider_type="openai_compatible",
                    base_url="http://localhost:1234/v1",
                    api_key_env="MARCBOT_TEST_KEY",
                    timeout_seconds=10.0,
                )
            },
            profiles={
                "local_fast": LlmProfileConfig(
                    name="local_fast",
                    provider="lmstudio",
                    model="test-model",
                    temperature=0.2,
                    max_tokens=100,
                    intended_use="test",
                )
            },
        ),
    )
    monkeypatch.setattr(
        cli,
        "_run_summary_completion_with_retry",
        lambda **kwargs: LlmCompletionResult(
            profile_name=kwargs["profile_name"],
            provider_name=kwargs["provider"].name,
            model=kwargs["model"],
            response_text="Saved source monitor summary",
            finish_reason="stop",
        ),
    )

    result = main(["source-monitor", "run-summary", "ai"])
    captured = capsys.readouterr()

    summary_path = (
        workspace
        / "source-projects"
        / "ai"
        / "summaries"
        / "source-monitor-2026-05-02-120000.summary.md"
    )

    assert result == 0
    assert "Source monitor report written:" in captured.out
    assert "Source monitor summary written:" in captured.out
    assert summary_path.read_text(encoding="utf-8") == "Saved source monitor summary\n"


def test_source_monitor_status_cli_uses_read_only_formatter(
    capsys,
    monkeypatch,
) -> None:
    import marcbot.cli as cli

    def fake_status(project_name: str) -> str:
        assert project_name == "ai"
        return "read-only source monitor status"

    def fail_if_report_generation_runs(*args, **kwargs):
        raise AssertionError("status command must not generate reports")

    def fail_if_llm_config_loads(*args, **kwargs):
        raise AssertionError("status command must not load LLM config")

    monkeypatch.setattr(cli, "format_source_monitor_cli_status", fake_status)
    monkeypatch.setattr(cli, "write_source_monitor_report", fail_if_report_generation_runs)
    monkeypatch.setattr(cli, "load_llm_config", fail_if_llm_config_loads)

    result = cli.main(["source-monitor", "status", "ai"])

    captured = capsys.readouterr()
    assert result == 0
    assert "read-only source monitor status" in captured.out


def test_llm_status_cli_is_read_only(capsys, monkeypatch) -> None:
    from pathlib import Path
    from types import SimpleNamespace

    import marcbot.cli as cli

    llm_config = SimpleNamespace(
        path=Path("/tmp/llm-providers.toml"),
        profiles={"local_fast": object()},
    )
    task_config = SimpleNamespace(
        path=Path("/tmp/llm-tasks.toml"),
        tasks={
            "source_monitor_analysis": SimpleNamespace(profile="local_fast"),
            "report_summary": SimpleNamespace(profile="local_fast"),
        },
    )

    def fail_if_models_are_listed(*args, **kwargs):
        raise AssertionError("llm status must not list provider models")

    def fail_if_health_check_runs(*args, **kwargs):
        raise AssertionError("llm status must not run health checks")

    def fail_if_completion_runs(*args, **kwargs):
        raise AssertionError("llm status must not run completions")

    monkeypatch.setattr(cli, "load_llm_config", lambda: llm_config)
    monkeypatch.setattr(cli, "load_llm_task_config", lambda: task_config)
    monkeypatch.setattr(cli, "list_openai_compatible_models", fail_if_models_are_listed)
    monkeypatch.setattr(
        cli,
        "run_openai_compatible_health_check",
        fail_if_health_check_runs,
    )
    monkeypatch.setattr(
        cli,
        "run_openai_compatible_completion",
        fail_if_completion_runs,
    )

    result = cli.main(["llm", "status"])

    captured = capsys.readouterr()
    assert result == 0
    assert "MarcBot LLM status" in captured.out
    assert "Provider config: valid (/tmp/llm-providers.toml)" in captured.out
    assert "Task config: valid (/tmp/llm-tasks.toml)" in captured.out
    assert "Profiles: 1 configured" in captured.out
    assert "Tasks: 2 configured" in captured.out
    assert "Task routes: valid" in captured.out


def test_llm_status_reports_missing_task_profiles(capsys, monkeypatch) -> None:
    from pathlib import Path
    from types import SimpleNamespace

    import marcbot.cli as cli

    llm_config = SimpleNamespace(
        path=Path("/tmp/llm-providers.toml"),
        profiles={"local_fast": object()},
    )
    task_config = SimpleNamespace(
        path=Path("/tmp/llm-tasks.toml"),
        tasks={
            "source_monitor_analysis": SimpleNamespace(profile="missing_profile"),
        },
    )

    monkeypatch.setattr(cli, "load_llm_config", lambda: llm_config)
    monkeypatch.setattr(cli, "load_llm_task_config", lambda: task_config)

    result = cli.main(["llm", "status"])

    captured = capsys.readouterr()
    assert result == 0
    assert "Task routes: invalid; missing profiles: missing_profile" in captured.out
