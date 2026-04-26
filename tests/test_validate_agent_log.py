"""Unit tests for the agent.log paper_id-prefix validator.

The validator scans an agent.log (JSONL Claude session transcript) and reports
any 422 errors from `mcp__koala__get_paper` / `mcp__koala__get_comments` calls
where the supplied `paper_id` is an 8-char hex prefix instead of a full UUID.
This catches the regression from SLURM job 9360098 (2026-04-25) where the agent
passed branch-name prefixes to MCP tools.
"""
import importlib.util
import json
import sys
from pathlib import Path


def _load_validator():
    path = Path(__file__).parent / "validate_agent_log.py"
    spec = importlib.util.spec_from_file_location("validate_agent_log", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_agent_log"] = module
    spec.loader.exec_module(module)
    return module


_validator = _load_validator()
scan_log = _validator.scan_log
Violation = _validator.Violation
_VALIDATOR_PATH = Path(__file__).parent / "validate_agent_log.py"


FULL_UUID = "a1b44436-1234-4abc-9def-0123456789ab"
PREFIX = "a1b44436"


def _tool_use(tool_id: str, name: str, paper_id: str) -> dict:
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": name,
                    "input": {"paper_id": paper_id},
                }
            ]
        },
    }


def _tool_result(tool_id: str, *, is_error: bool, content: str) -> dict:
    return {
        "type": "user",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": content,
                    "is_error": is_error,
                }
            ]
        },
    }


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")


def test_clean_log_full_uuid_no_violations(tmp_path: Path) -> None:
    log = tmp_path / "agent.log"
    _write_jsonl(
        log,
        [
            _tool_use("t1", "mcp__koala__get_paper", FULL_UUID),
            _tool_result("t1", is_error=False, content="paper details..."),
        ],
    )
    assert scan_log(log) == []


def test_prefix_paper_id_with_422_is_flagged(tmp_path: Path) -> None:
    log = tmp_path / "agent.log"
    err = (
        f"Error calling tool 'get_paper': Client error '422 Unprocessable Entity' "
        f"for url 'http://backend:8000/api/v1/papers/{PREFIX}'"
    )
    _write_jsonl(
        log,
        [
            _tool_use("t1", "mcp__koala__get_paper", PREFIX),
            _tool_result("t1", is_error=True, content=err),
        ],
    )
    violations = scan_log(log)
    assert len(violations) == 1
    v = violations[0]
    assert isinstance(v, Violation)
    assert v.tool_name == "mcp__koala__get_paper"
    assert v.paper_id == PREFIX


def test_prefix_paper_id_on_get_comments_is_flagged(tmp_path: Path) -> None:
    log = tmp_path / "agent.log"
    err = "Client error '422 Unprocessable Entity'"
    _write_jsonl(
        log,
        [
            _tool_use("t1", "mcp__koala__get_comments", PREFIX),
            _tool_result("t1", is_error=True, content=err),
        ],
    )
    assert len(scan_log(log)) == 1


def test_prefix_paper_id_without_422_is_not_flagged(tmp_path: Path) -> None:
    """An 8-char paper_id that did not produce a 422 error is not the bug we're
    catching — the validator should only flag prefix calls that actually failed
    at the API."""
    log = tmp_path / "agent.log"
    _write_jsonl(
        log,
        [
            _tool_use("t1", "mcp__koala__get_paper", PREFIX),
            _tool_result("t1", is_error=False, content="(somehow succeeded)"),
        ],
    )
    assert scan_log(log) == []


def test_full_uuid_with_422_is_not_flagged(tmp_path: Path) -> None:
    """A 422 against a full UUID is a different kind of failure; out of scope."""
    log = tmp_path / "agent.log"
    err = "Client error '422 Unprocessable Entity'"
    _write_jsonl(
        log,
        [
            _tool_use("t1", "mcp__koala__get_paper", FULL_UUID),
            _tool_result("t1", is_error=True, content=err),
        ],
    )
    assert scan_log(log) == []


def test_other_tools_with_prefix_are_not_flagged(tmp_path: Path) -> None:
    """Validator scope is narrow: only get_paper / get_comments."""
    log = tmp_path / "agent.log"
    err = "Client error '422 Unprocessable Entity'"
    _write_jsonl(
        log,
        [
            _tool_use("t1", "mcp__koala__post_comment", PREFIX),
            _tool_result("t1", is_error=True, content=err),
        ],
    )
    assert scan_log(log) == []


def test_multiple_violations_all_reported(tmp_path: Path) -> None:
    log = tmp_path / "agent.log"
    err = "Client error '422 Unprocessable Entity'"
    records = []
    for i, (tool, pid) in enumerate(
        [
            ("mcp__koala__get_paper", "a1b44436"),
            ("mcp__koala__get_comments", "7920483a"),
            ("mcp__koala__get_paper", FULL_UUID),
            ("mcp__koala__get_paper", "ed85ad2f"),
        ]
    ):
        tid = f"t{i}"
        records.append(_tool_use(tid, tool, pid))
        records.append(_tool_result(tid, is_error=True, content=err))
    _write_jsonl(log, records)
    violations = scan_log(log)
    assert {v.paper_id for v in violations} == {"a1b44436", "7920483a", "ed85ad2f"}


def test_non_8_char_short_paper_id_not_flagged(tmp_path: Path) -> None:
    """The regex is anchored to exactly 8 hex chars (the branch-prefix shape)."""
    log = tmp_path / "agent.log"
    err = "Client error '422 Unprocessable Entity'"
    _write_jsonl(
        log,
        [
            _tool_use("t1", "mcp__koala__get_paper", "a1b4"),
            _tool_result("t1", is_error=True, content=err),
        ],
    )
    assert scan_log(log) == []


def test_malformed_jsonl_lines_are_skipped(tmp_path: Path) -> None:
    log = tmp_path / "agent.log"
    err = "Client error '422 Unprocessable Entity'"
    lines = [
        "not json at all",
        json.dumps(_tool_use("t1", "mcp__koala__get_paper", PREFIX)),
        "{partial...",
        json.dumps(_tool_result("t1", is_error=True, content=err)),
        "",
    ]
    log.write_text("\n".join(lines))
    assert len(scan_log(log)) == 1


def test_cli_exit_code_zero_on_clean_log(tmp_path: Path) -> None:
    import subprocess
    import sys

    log = tmp_path / "agent.log"
    _write_jsonl(
        log,
        [
            _tool_use("t1", "mcp__koala__get_paper", FULL_UUID),
            _tool_result("t1", is_error=False, content="ok"),
        ],
    )
    result = subprocess.run(
        [sys.executable, str(_VALIDATOR_PATH), str(log)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_cli_exit_code_nonzero_on_violation(tmp_path: Path) -> None:
    import subprocess
    import sys

    log = tmp_path / "agent.log"
    err = "Client error '422 Unprocessable Entity'"
    _write_jsonl(
        log,
        [
            _tool_use("t1", "mcp__koala__get_paper", PREFIX),
            _tool_result("t1", is_error=True, content=err),
        ],
    )
    result = subprocess.run(
        [sys.executable, str(_VALIDATOR_PATH), str(log)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert PREFIX in (result.stdout + result.stderr)
