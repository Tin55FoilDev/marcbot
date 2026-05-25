"""Tests for approved MarcBot workflow registry."""
from __future__ import annotations

import pytest

from marcbot.workflow_registry import (
    format_workflow_detail,
    format_workflow_list,
    get_workflow_definition,
    list_workflow_definitions,
)


def test_workflow_registry_lists_initial_source_monitor_workflows() -> None:
    workflows = list_workflow_definitions()
    workflow_ids = [workflow.workflow_id for workflow in workflows]

    assert workflow_ids == ["source-monitor-ai-report", "source-monitor-ai-summary"]


def test_format_workflow_list_discloses_boundaries() -> None:
    output = format_workflow_list()

    assert "MarcBot approved workflows" in output
    assert "- source-monitor-ai-report" in output
    assert "- source-monitor-ai-summary" in output
    assert "Provider contact: no" in output
    assert "Provider contact: yes" in output
    assert "Writes artifacts: yes" in output
    assert "Writes memory: no" in output
    assert "Telegram executable: no" in output
    assert "Registry provider contact: no" in output


def test_format_workflow_detail_discloses_execution_boundaries() -> None:
    output = format_workflow_detail("source-monitor-ai-summary")

    assert "MarcBot approved workflow" in output
    assert "ID: source-monitor-ai-summary" in output
    assert "Provider contact when run: yes" in output
    assert "Writes artifacts when run: yes" in output
    assert "Writes memory when run: no" in output
    assert "Telegram executable: no" in output
    assert "Memory profile: source-monitor" in output
    assert "CLI workflow run v2 executes this workflow with explicit provider contact." in output
    assert "Registry provider contact: no" in output


def test_get_workflow_definition_rejects_unknown_workflow() -> None:
    with pytest.raises(ValueError, match="unknown workflow: missing-workflow"):
        get_workflow_definition("missing-workflow")
