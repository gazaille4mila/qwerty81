"""Tests for harness-level UUID validation in dispatch (tools.py)."""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

FULL_UUID = "a1b44436-1234-4abc-9def-0123456789ab"
PREFIX = "a1b44436"


def _load_tools_module():
    sys.modules.setdefault("httpx", MagicMock())
    harness_dir = Path(__file__).parent.parent / "agent_definition" / "harness"
    koala_path = harness_dir / "koala.py"
    koala_spec = importlib.util.spec_from_file_location("agent_definition.harness.koala", koala_path)
    koala_module = importlib.util.module_from_spec(koala_spec)
    sys.modules["agent_definition.harness.koala"] = koala_module
    koala_spec.loader.exec_module(koala_module)

    tools_path = harness_dir / "tools.py"
    tools_spec = importlib.util.spec_from_file_location("agent_definition.harness.tools", tools_path)
    tools_module = importlib.util.module_from_spec(tools_spec)
    tools_spec.loader.exec_module(tools_module)
    return tools_module


_tools = _load_tools_module()
dispatch = _tools.dispatch


def make_client():
    client = MagicMock()
    client.call_tool.return_value = "ok"
    return client


def test_prefix_paper_id_rejected_network_not_called():
    client = make_client()
    result = dispatch("get_paper", {"paper_id": PREFIX}, client)
    assert "ERROR" in result
    assert PREFIX in result
    assert "branch-prefix" in result
    client.call_tool.assert_not_called()


def test_full_uuid_paper_id_passes_through():
    client = make_client()
    result = dispatch("get_paper", {"paper_id": FULL_UUID}, client)
    assert result == "ok"
    client.call_tool.assert_called_once_with("get_paper", {"paper_id": FULL_UUID})


@pytest.mark.parametrize("tool_name,field_name", [
    ("get_paper", "paper_id"),
    ("post_comment", "parent_id"),
    ("get_actor_profile", "actor_id"),
    ("post_verdict", "flagged_agent_id"),
])
def test_prefix_shape_rejected_for_each_id_field(tool_name, field_name):
    client = make_client()
    result = dispatch(tool_name, {field_name: PREFIX}, client)
    assert "ERROR" in result
    assert PREFIX in result
    assert field_name in result
    client.call_tool.assert_not_called()


def test_notification_ids_one_bad_element_returns_error():
    client = make_client()
    good_uuid = "b2c55547-2345-5bcd-aef0-1234567890bc"
    result = dispatch("mark_notifications_read", {"notification_ids": [good_uuid, PREFIX]}, client)
    assert "ERROR" in result
    assert PREFIX in result
    client.call_tool.assert_not_called()


def test_notification_ids_pure_uuid_list_passes_through():
    client = make_client()
    uuid1 = "b2c55547-2345-5bcd-aef0-1234567890bc"
    uuid2 = "c3d66658-3456-6cde-bf01-234567890abc"
    result = dispatch("mark_notifications_read", {"notification_ids": [uuid1, uuid2]}, client)
    assert result == "ok"
    client.call_tool.assert_called_once()


def test_notification_ids_empty_list_passes_through():
    client = make_client()
    result = dispatch("mark_notifications_read", {"notification_ids": []}, client)
    assert result == "ok"
    client.call_tool.assert_called_once()


def test_absent_optional_id_passes_through():
    client = make_client()
    result = dispatch("post_comment", {
        "paper_id": FULL_UUID,
        "content_markdown": "hello",
        "github_file_url": "https://github.com/foo/bar",
    }, client)
    assert result == "ok"
    client.call_tool.assert_called_once()


def test_none_id_value_passes_through():
    client = make_client()
    result = dispatch("post_comment", {
        "paper_id": None,
        "content_markdown": "hello",
        "github_file_url": "https://github.com/foo/bar",
    }, client)
    assert result == "ok"
    client.call_tool.assert_called_once()


def test_empty_string_id_value_passes_through():
    client = make_client()
    result = dispatch("get_paper", {"paper_id": ""}, client)
    assert result == "ok"
    client.call_tool.assert_called_once()


def test_run_code_not_validated_by_field_content():
    client = make_client()
    script = f'print("paper_id=\\"{PREFIX}\\"")'
    result = dispatch("run_code", {"script": script}, client)
    assert "ERROR" not in result or "branch-prefix" not in result


def test_multiple_violations_produce_one_error_with_both_prefixes():
    client = make_client()
    prefix1 = "a1b44436"
    prefix2 = "b2c55547"
    result = dispatch("mark_notifications_read", {"notification_ids": [prefix1, prefix2]}, client)
    assert "ERROR" in result
    assert prefix1 in result
    assert prefix2 in result
    client.call_tool.assert_not_called()


def test_non_prefix_malformed_input_passes_through():
    client = make_client()
    for bad_value in ["not-a-uuid", "a1b44436-1234"]:
        client = make_client()
        result = dispatch("get_paper", {"paper_id": bad_value}, client)
        assert result == "ok", f"Expected passthrough for {bad_value!r}, got {result!r}"
        client.call_tool.assert_called_once()
