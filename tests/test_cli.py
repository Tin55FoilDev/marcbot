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


def test_source_monitor_summarize_latest_uses_existing_report(
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

    workspace = tmp_path / "workspace"
    report_dir = workspace / "source-projects" / "ai" / "reports"
    report_dir.mkdir(parents=True)
    older_report = report_dir / "source-monitor-2026-05-01-120000.md"
    latest_report = report_dir / "source-monitor-2026-05-02-120000.md"
    older_report.write_text("Older source monitor report", encoding="utf-8")
    latest_report.write_text("Latest source monitor report", encoding="utf-8")

    monkeypatch.setattr(cli, "WORKSPACE_DIR", workspace)
    monkeypatch.setattr(
        cli,
        "find_latest_source_monitor_report",
        lambda project_name: latest_report,
    )
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

    def fail_if_report_generation_runs(*args, **kwargs):
        raise AssertionError("summarize-latest must not generate a new report")

    monkeypatch.setattr(cli, "write_source_monitor_report", fail_if_report_generation_runs)
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
            response_text="Saved latest source monitor summary",
            finish_reason="stop",
        ),
    )

    result = cli.main(["source-monitor", "summarize-latest", "ai"])
    captured = capsys.readouterr()

    summary_path = (
        workspace
        / "source-projects"
        / "ai"
        / "summaries"
        / "source-monitor-2026-05-02-120000.summary.md"
    )

    assert result == 0
    assert f"Using latest source monitor report: {latest_report}" in captured.out
    assert f"Source monitor summary written: {summary_path}" in captured.out
    assert summary_path.read_text(encoding="utf-8") == (
        "Saved latest source monitor summary\n"
    )


def test_source_monitor_summarize_latest_fails_without_report(
    monkeypatch,
    capsys,
) -> None:
    import marcbot.cli as cli

    monkeypatch.setattr(
        cli,
        "find_latest_source_monitor_report",
        lambda project_name: None,
    )

    result = cli.main(["source-monitor", "summarize-latest", "ai"])
    captured = capsys.readouterr()

    assert result == 1
    assert "MBOT-SOURCE-030" in captured.err
    assert "No source monitor report found for project: ai" in captured.err


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


def test_source_monitor_artifact_path_command_prints_resolved_path(
    monkeypatch,
    capsys,
) -> None:
    from pathlib import Path

    import marcbot.cli as cli

    expected_path = Path("/srv/marcbot/workspace/source-projects/ai/reports/example.md")

    monkeypatch.setattr(
        cli,
        "resolve_source_monitor_artifact",
        lambda artifact_id, project_name: expected_path,
    )

    result = cli.main(
        ["source-monitor", "artifact-path", "ai", "report:2026-05-08-113613"]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "MarcBot source monitor artifact" in captured.out
    assert "Project: ai" in captured.out
    assert "Artifact ID: report:2026-05-08-113613" in captured.out
    assert f"Path: {expected_path}" in captured.out


def test_source_monitor_artifact_path_command_returns_error_when_missing(
    monkeypatch,
    capsys,
) -> None:
    import marcbot.cli as cli

    monkeypatch.setattr(
        cli,
        "resolve_source_monitor_artifact",
        lambda artifact_id, project_name: None,
    )

    result = cli.main(
        ["source-monitor", "artifact-path", "ai", "report:2026-05-08-113613"]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "MarcBot source monitor artifact" in captured.out
    assert "Project: ai" in captured.out
    assert "Artifact ID: report:2026-05-08-113613" in captured.out
    assert "Status: not found" in captured.out


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


def test_llm_status_verbose_lists_local_profiles_and_tasks(capsys, monkeypatch) -> None:
    from pathlib import Path
    from types import SimpleNamespace

    import marcbot.cli as cli

    llm_config = SimpleNamespace(
        path=Path("/tmp/llm-providers.toml"),
        profiles={
            "local_fast": SimpleNamespace(
                provider="lmstudio",
                model="google/gemma-4-e4b",
                intended_use="low_risk_utility",
            ),
        },
    )
    task_config = SimpleNamespace(
        tasks={
            "source_monitor_analysis": SimpleNamespace(
                profile="local_fast",
                description="Analyze allowlisted source monitor output",
            ),
        },
    )

    def fail_if_models_are_listed(*args, **kwargs):
        raise AssertionError("llm status --verbose must not list provider models")

    def fail_if_health_check_runs(*args, **kwargs):
        raise AssertionError("llm status --verbose must not run health checks")

    def fail_if_completion_runs(*args, **kwargs):
        raise AssertionError("llm status --verbose must not run completions")

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

    result = cli.main(["llm", "status", "--verbose"])

    captured = capsys.readouterr()
    assert result == 0
    assert "MarcBot LLM status" in captured.out
    assert "Profiles:" in captured.out
    assert (
        "- local_fast: provider=lmstudio, model=google/gemma-4-e4b, "
        "intended_use=low_risk_utility"
    ) in captured.out
    assert "Tasks:" in captured.out
    assert (
        "- source_monitor_analysis -> local_fast — "
        "Analyze allowlisted source monitor output"
    ) in captured.out

def test_weather_report_run_writes_report(capsys, monkeypatch, tmp_path) -> None:
    import marcbot.cli as cli
    from marcbot.weather_report import WeatherReportResult

    report_path = tmp_path / "weather-report-2026-05-16-080000.md"

    monkeypatch.setattr(
        cli,
        "write_weather_report",
        lambda: WeatherReportResult(
            path=report_path,
            message=f"Weather report written: {report_path}",
        ),
    )

    result = cli.main(["weather-report", "run"])
    captured = capsys.readouterr()

    assert result == 0
    assert f"Weather report written: {report_path}" in captured.out


def test_weather_report_latest_reports_missing(capsys, monkeypatch) -> None:
    import marcbot.cli as cli

    monkeypatch.setattr(cli, "find_latest_weather_report", lambda: None)

    result = cli.main(["weather-report", "latest"])
    captured = capsys.readouterr()

    assert result == 1
    assert "No weather reports found." in captured.out


def test_weather_report_latest_prints_path(capsys, monkeypatch, tmp_path) -> None:
    import marcbot.cli as cli

    report_path = tmp_path / "weather-report-2026-05-16-080000.md"
    monkeypatch.setattr(cli, "find_latest_weather_report", lambda: report_path)

    result = cli.main(["weather-report", "latest"])
    captured = capsys.readouterr()

    assert result == 0
    assert str(report_path) in captured.out

def test_weather_report_send_latest_sends_report(capsys, monkeypatch, tmp_path) -> None:
    import marcbot.cli as cli
    from marcbot.report_sender import SendLatestReportResult

    report_path = tmp_path / "weather-report-2026-05-17-080000.md"

    monkeypatch.setattr(
        cli,
        "send_latest_weather_report",
        lambda config: SendLatestReportResult(
            path=report_path,
            chat_ids=(12345,),
            report_label="weather",
        ),
    )

    result = cli.main(["weather-report", "send-latest"])
    captured = capsys.readouterr()

    assert result == 0
    assert "Sent latest weather report:" in captured.out
    assert "weather-report-2026-05-17-080000.md" in captured.out

def test_weather_report_send_latest_text_sends_report(capsys, monkeypatch, tmp_path) -> None:
    import marcbot.cli as cli
    from marcbot.report_sender import SendLatestReportResult

    report_path = tmp_path / "weather-report-2026-05-17-080000.md"

    monkeypatch.setattr(
        cli,
        "send_latest_weather_report_text",
        lambda config: SendLatestReportResult(
            path=report_path,
            chat_ids=(12345,),
            report_label="weather text",
        ),
    )

    result = cli.main(["weather-report", "send-latest-text"])
    captured = capsys.readouterr()

    assert result == 0
    assert "Sent latest weather text report:" in captured.out
    assert "weather-report-2026-05-17-080000.md" in captured.out

def test_weather_report_run_send_text_writes_and_sends(
    capsys,
    monkeypatch,
    tmp_path,
) -> None:
    import marcbot.cli as cli
    from marcbot.report_sender import SendLatestReportResult
    from marcbot.weather_report import WeatherReportResult

    report_path = tmp_path / "weather-report-2026-05-17-071500.md"
    calls = []

    def fake_write_weather_report():
        calls.append("write")
        return WeatherReportResult(
            path=report_path,
            message=f"Weather report written: {report_path}",
        )

    def fake_send_latest_weather_report_text(config):
        calls.append("send")
        return SendLatestReportResult(
            path=report_path,
            chat_ids=(12345,),
            report_label="weather text",
        )

    def fake_record_approved_workflow_event(**kwargs):
        calls.append("memory")
        import marcbot.memory_workflows as memory_workflows
        from marcbot.memory_store import add_memory_event
        from marcbot.memory_workflows import record_approved_workflow_event

        original = memory_workflows.add_memory_event
        memory_workflows.add_memory_event = lambda **inner_kwargs: add_memory_event(
            root=tmp_path / "memory",
            **inner_kwargs,
        )
        try:
            return record_approved_workflow_event(**kwargs)
        finally:
            memory_workflows.add_memory_event = original

    monkeypatch.setattr(cli, "write_weather_report", fake_write_weather_report)
    monkeypatch.setattr(
        cli,
        "send_latest_weather_report_text",
        fake_send_latest_weather_report_text,
    )
    monkeypatch.setattr(
        cli,
        "record_approved_workflow_event",
        fake_record_approved_workflow_event,
    )

    result = cli.main(["weather-report", "run-send-text"])
    captured = capsys.readouterr()

    assert result == 0
    assert calls == ["write", "send", "memory"]
    assert f"Weather report written: {report_path}" in captured.out
    assert "Sent latest weather text report:" in captured.out
    assert "Memory event added:" in captured.out

def test_memory_init_command(capsys, monkeypatch, tmp_path) -> None:
    import marcbot.cli as cli
    from marcbot.memory_store import init_memory_store

    monkeypatch.setattr(
        cli,
        "init_memory_store",
        lambda: init_memory_store(root=tmp_path),
    )

    result = cli.main(["memory", "init"])
    captured = capsys.readouterr()

    assert result == 0
    assert "MarcBot memory initialized:" in captured.out


def test_memory_status_command(capsys, monkeypatch) -> None:
    import marcbot.cli as cli

    monkeypatch.setattr(
        cli,
        "format_memory_status_message",
        lambda: "MarcBot memory\nProvider contact: no",
    )

    result = cli.main(["memory", "status"])
    captured = capsys.readouterr()

    assert result == 0
    assert captured.out == "MarcBot memory\nProvider contact: no\n"

def test_memory_event_add_command(capsys, monkeypatch, tmp_path) -> None:
    import marcbot.cli as cli
    from marcbot.memory_store import add_memory_event

    monkeypatch.setattr(
        cli,
        "add_memory_event",
        lambda **kwargs: add_memory_event(root=tmp_path, **kwargs),
    )

    result = cli.main(
        [
            "memory",
            "event",
            "add",
            "--type",
            "issue_resolved",
            "--summary",
            "Fixed backup timer.",
            "--source",
            "test",
            "--confidence",
            "high",
            "--project",
            "marcbot-operations",
            "--details",
            "Useful detail.",
            "--cause",
            "Useful cause.",
            "--resolution",
            "Useful resolution.",
            "--verification",
            "Useful verification.",
            "--follow-up",
            "Useful follow-up.",
            "--related-command",
            "sudo systemctl status marcbot-backup.service",
        ]
    )
    captured = capsys.readouterr()

    assert result == 0
    assert "Memory event added:" in captured.out


def test_memory_event_list_command(capsys, monkeypatch) -> None:
    import marcbot.cli as cli

    monkeypatch.setattr(
        cli,
        "format_memory_event_list",
        lambda limit: f"MarcBot memory events\nLimit: {limit}",
    )

    result = cli.main(["memory", "event", "list", "--limit", "5"])
    captured = capsys.readouterr()

    assert result == 0
    assert captured.out == "MarcBot memory events\nLimit: 5\n"

def test_memory_summary_add_command(capsys, monkeypatch, tmp_path) -> None:
    import marcbot.cli as cli
    from marcbot.memory_store import add_memory_summary

    monkeypatch.setattr(
        cli,
        "add_memory_summary",
        lambda **kwargs: add_memory_summary(root=tmp_path, **kwargs),
    )

    result = cli.main(
        [
            "memory",
            "summary",
            "add",
            "--title",
            "Weather milestone",
            "--body",
            "Weather workflow completed.",
            "--source",
            "test",
            "--project",
            "weather-report",
            "--related-command",
            "python -m marcbot weather-report run-send-text",
        ]
    )
    captured = capsys.readouterr()

    assert result == 0
    assert "Memory summary added:" in captured.out


def test_memory_summary_list_command(capsys, monkeypatch) -> None:
    import marcbot.cli as cli

    monkeypatch.setattr(
        cli,
        "format_memory_summary_list",
        lambda limit: f"MarcBot memory summaries\nLimit: {limit}",
    )

    result = cli.main(["memory", "summary", "list", "--limit", "5"])
    captured = capsys.readouterr()

    assert result == 0
    assert captured.out == "MarcBot memory summaries\nLimit: 5\n"

def test_memory_fact_add_command(capsys, monkeypatch, tmp_path) -> None:
    import marcbot.cli as cli
    from marcbot.memory_store import add_memory_fact

    monkeypatch.setattr(
        cli,
        "add_memory_fact",
        lambda **kwargs: add_memory_fact(root=tmp_path, **kwargs),
    )

    result = cli.main(
        [
            "memory",
            "fact",
            "add",
            "--id",
            "weather-report-schedule",
            "--statement",
            "Weather report runs daily around 7:15 AM.",
            "--category",
            "schedule",
            "--source",
            "test",
            "--confidence",
            "high",
            "--project",
            "weather-report",
            "--details",
            "Defined by marcbot-weather-report.timer.",
        ]
    )
    captured = capsys.readouterr()

    assert result == 0
    assert "Memory fact added:" in captured.out


def test_memory_fact_list_command(capsys, monkeypatch) -> None:
    import marcbot.cli as cli

    monkeypatch.setattr(
        cli,
        "format_memory_fact_list",
        lambda status, limit: f"MarcBot memory facts\nStatus: {status}\nLimit: {limit}",
    )

    result = cli.main(["memory", "fact", "list", "--status", "active", "--limit", "5"])
    captured = capsys.readouterr()

    assert result == 0
    assert captured.out == "MarcBot memory facts\nStatus: active\nLimit: 5\n"

def test_memory_fact_supersede_command(capsys, monkeypatch, tmp_path) -> None:
    import marcbot.cli as cli
    from marcbot.memory_store import add_memory_fact, supersede_memory_fact

    add_memory_fact(
        root=tmp_path,
        fact_id="old",
        statement="Old fact.",
        category="test",
        source="test",
        confidence="high",
    )

    monkeypatch.setattr(
        cli,
        "supersede_memory_fact",
        lambda **kwargs: supersede_memory_fact(root=tmp_path, **kwargs),
    )

    result = cli.main(
        [
            "memory",
            "fact",
            "supersede",
            "--id",
            "old",
            "--new-id",
            "new",
            "--statement",
            "New fact.",
            "--reason",
            "Correction.",
            "--source",
            "test",
            "--confidence",
            "high",
        ]
    )
    captured = capsys.readouterr()

    assert result == 0
    assert "Memory fact superseded: old -> new" in captured.out

def test_memory_fact_reject_command(capsys, monkeypatch, tmp_path) -> None:
    import marcbot.cli as cli
    from marcbot.memory_store import add_memory_fact, reject_memory_fact

    add_memory_fact(
        root=tmp_path,
        fact_id="test-fact",
        statement="Temporary test fact.",
        category="test",
        source="test",
        confidence="high",
    )

    monkeypatch.setattr(
        cli,
        "reject_memory_fact",
        lambda **kwargs: reject_memory_fact(root=tmp_path, **kwargs),
    )

    result = cli.main(
        [
            "memory",
            "fact",
            "reject",
            "--id",
            "test-fact",
            "--reason",
            "Temporary fact cleanup.",
            "--source",
            "test_cleanup",
            "--confidence",
            "high",
        ]
    )
    captured = capsys.readouterr()

    assert result == 0
    assert "Memory fact rejected: test-fact" in captured.out

def test_memory_proposal_add_command(capsys, monkeypatch, tmp_path) -> None:
    import marcbot.cli as cli
    from marcbot.memory_store import add_memory_proposal

    monkeypatch.setattr(
        cli,
        "add_memory_proposal",
        lambda **kwargs: add_memory_proposal(root=tmp_path, **kwargs),
    )

    result = cli.main(
        [
            "memory",
            "proposal",
            "add",
            "--id",
            "weather-reference-pattern",
            "--proposed-type",
            "fact",
            "--proposed-statement",
            "weather-report is the reference pattern.",
            "--source",
            "test",
            "--rationale",
            "It validated the workflow lifecycle.",
            "--risk-level",
            "medium",
            "--project",
            "marcbot-memory",
            "--details",
            "Review before approval.",
        ]
    )
    captured = capsys.readouterr()

    assert result == 0
    assert "Memory proposal added:" in captured.out


def test_memory_proposal_list_command(capsys, monkeypatch) -> None:
    import marcbot.cli as cli

    monkeypatch.setattr(
        cli,
        "format_memory_proposal_list",
        lambda status, limit: (
            f"MarcBot memory proposals\nStatus: {status}\nLimit: {limit}"
        ),
    )

    result = cli.main(["memory", "proposal", "list", "--status", "pending", "--limit", "5"])
    captured = capsys.readouterr()

    assert result == 0
    assert captured.out == "MarcBot memory proposals\nStatus: pending\nLimit: 5\n"


def test_memory_proposal_reject_command(capsys, monkeypatch, tmp_path) -> None:
    import marcbot.cli as cli
    from marcbot.memory_store import add_memory_proposal, reject_memory_proposal

    add_memory_proposal(
        root=tmp_path,
        proposal_id="test-proposal",
        proposed_type="fact",
        proposed_statement="Temporary proposal.",
        source="test",
        rationale="Test.",
        risk_level="low",
    )

    monkeypatch.setattr(
        cli,
        "reject_memory_proposal",
        lambda **kwargs: reject_memory_proposal(root=tmp_path, **kwargs),
    )

    result = cli.main(
        [
            "memory",
            "proposal",
            "reject",
            "--id",
            "test-proposal",
            "--reason",
            "Temporary proposal cleanup.",
            "--source",
            "test_cleanup",
        ]
    )
    captured = capsys.readouterr()

    assert result == 0
    assert "Memory proposal rejected: test-proposal" in captured.out

def test_memory_proposal_approve_command(capsys, monkeypatch, tmp_path) -> None:
    import marcbot.cli as cli
    from marcbot.memory_store import add_memory_proposal, approve_memory_proposal

    add_memory_proposal(
        root=tmp_path,
        proposal_id="test-proposal",
        proposed_type="fact",
        proposed_statement="A proposed fact.",
        source="test",
        rationale="Test.",
        risk_level="low",
    )

    monkeypatch.setattr(
        cli,
        "approve_memory_proposal",
        lambda **kwargs: approve_memory_proposal(root=tmp_path, **kwargs),
    )

    result = cli.main(
        [
            "memory",
            "proposal",
            "approve",
            "--id",
            "test-proposal",
            "--source",
            "test_approval",
            "--review-reason",
            "Looks correct.",
            "--category",
            "test",
            "--confidence",
            "high",
        ]
    )
    captured = capsys.readouterr()

    assert result == 0
    assert "Memory proposal approved: test-proposal -> fact test-proposal" in captured.out

def test_memory_fact_show_command(capsys, monkeypatch) -> None:
    import marcbot.cli as cli

    monkeypatch.setattr(
        cli,
        "format_memory_fact_detail",
        lambda fact_id: f"MarcBot memory fact\nID: {fact_id}",
    )

    result = cli.main(["memory", "fact", "show", "--id", "weather-report-schedule"])
    captured = capsys.readouterr()

    assert result == 0
    assert captured.out == "MarcBot memory fact\nID: weather-report-schedule\n"


def test_memory_proposal_show_command(capsys, monkeypatch) -> None:
    import marcbot.cli as cli

    monkeypatch.setattr(
        cli,
        "format_memory_proposal_detail",
        lambda proposal_id: f"MarcBot memory proposal\nID: {proposal_id}",
    )

    result = cli.main(["memory", "proposal", "show", "--id", "weather-reference-pattern"])
    captured = capsys.readouterr()

    assert result == 0
    assert captured.out == "MarcBot memory proposal\nID: weather-reference-pattern\n"

def test_memory_event_show_command(capsys, monkeypatch) -> None:
    import marcbot.cli as cli

    monkeypatch.setattr(
        cli,
        "format_memory_event_detail",
        lambda index, limit: f"MarcBot memory event\nIndex: {index}\nLimit: {limit}",
    )

    result = cli.main(["memory", "event", "show", "--index", "2", "--limit", "5"])
    captured = capsys.readouterr()

    assert result == 0
    assert captured.out == "MarcBot memory event\nIndex: 2\nLimit: 5\n"


def test_memory_summary_show_command(capsys, monkeypatch) -> None:
    import marcbot.cli as cli

    monkeypatch.setattr(
        cli,
        "format_memory_summary_detail",
        lambda name: f"MarcBot memory summary\nName: {name}",
    )

    result = cli.main(
        [
            "memory",
            "summary",
            "show",
            "--name",
            "2026-05-18-memory-foundation-through-m6.md",
        ]
    )
    captured = capsys.readouterr()

    assert result == 0
    assert (
        captured.out
        == "MarcBot memory summary\nName: 2026-05-18-memory-foundation-through-m6.md\n"
    )

def test_memory_search_command(capsys, monkeypatch) -> None:
    import marcbot.cli as cli

    monkeypatch.setattr(
        cli,
        "format_memory_search_results",
        lambda query, limit: f"MarcBot memory search\nQuery: {query}\nLimit: {limit}",
    )

    result = cli.main(["memory", "search", "weather", "--limit", "5"])
    captured = capsys.readouterr()

    assert result == 0
    assert captured.out == "MarcBot memory search\nQuery: weather\nLimit: 5\n"

def test_daily_status_report_records_memory_event(capsys, monkeypatch, tmp_path) -> None:
    import marcbot.cli as cli
    from marcbot.reports import ReportResult

    calls = []
    report_path = tmp_path / "daily-status.md"

    monkeypatch.setattr(
        cli,
        "write_daily_status_report",
        lambda: ReportResult(
            path=report_path,
            message=f"Daily status report written: {report_path}",
        ),
    )

    class FakeMemoryResult:
        message = "Memory event added: test"

    def fake_record_approved_workflow_event(**kwargs):
        calls.append(kwargs)
        return FakeMemoryResult()

    monkeypatch.setattr(
        cli,
        "record_approved_workflow_event",
        fake_record_approved_workflow_event,
    )

    result = cli.main(["report", "daily-status"])
    captured = capsys.readouterr()

    assert result == 0
    assert f"Daily status report written: {report_path}" in captured.out
    assert "Memory event added: test" in captured.out
    assert calls[0]["event_type"] == "report_generated"
    assert calls[0]["project"] == "daily-status-report"
    assert calls[0]["related_files"] == (report_path,)


def test_daily_status_report_send_records_memory_event(capsys, monkeypatch, tmp_path) -> None:
    import marcbot.cli as cli
    from marcbot.report_sender import SendLatestReportResult

    calls = []
    report_path = tmp_path / "daily-status.md"

    monkeypatch.setattr(cli, "load_config", lambda path: object())
    monkeypatch.setattr(
        cli,
        "send_latest_report",
        lambda config: SendLatestReportResult(path=report_path, chat_ids=(12345,)),
    )

    class FakeMemoryResult:
        message = "Memory event added: test"

    def fake_record_approved_workflow_event(**kwargs):
        calls.append(kwargs)
        return FakeMemoryResult()

    monkeypatch.setattr(
        cli,
        "record_approved_workflow_event",
        fake_record_approved_workflow_event,
    )

    result = cli.main(["report", "send-latest"])
    captured = capsys.readouterr()

    assert result == 0
    assert "Sent latest daily status report:" in captured.out
    assert "Memory event added: test" in captured.out
    assert calls[0]["event_type"] == "report_sent"
    assert calls[0]["project"] == "daily-status-report"
    assert calls[0]["related_files"] == (report_path,)
