"""Tests for reva.cli — command tree structure and --help output.

We use click's CliRunner to invoke commands in-process, which lets us
verify help output and argument parsing without touching tmux, the
network, or any backend binary.
"""
from click.testing import CliRunner

from reva.cli import main


def _invoke(*args, input=None):
    runner = CliRunner()
    return runner.invoke(main, list(args), input=input, catch_exceptions=False)


# ── top-level ──────────────────────────────────────────────────────────

def test_main_help_exits_zero():
    result = _invoke("--help")
    assert result.exit_code == 0
    assert "reva — reviewer agent CLI" in result.output


def test_main_help_lists_all_expected_commands():
    result = _invoke("--help")
    assert result.exit_code == 0
    # Commands that should be visible in `reva --help` output
    for cmd in (
        "init",
        "create",
        "launch",
        "kill",
        "status",
        "persona",
        "interests",
        "list",
        "batch",
        "log",
        "view",
        "debug",
    ):
        assert cmd in result.output, f"{cmd!r} missing from `reva --help`"


# ── per-command --help ────────────────────────────────────────────────

def test_init_help():
    result = _invoke("init", "--help")
    assert result.exit_code == 0
    assert "Initialize a reva project" in result.output


def test_create_help_lists_required_options():
    result = _invoke("create", "--help")
    assert result.exit_code == 0
    # Required flags must appear in the help text
    for flag in ("--name", "--backend", "--role", "--persona", "--interest"):
        assert flag in result.output


def test_create_help_lists_all_backends():
    result = _invoke("create", "--help")
    assert result.exit_code == 0
    for backend in ("claude-code", "gemini-cli", "codex", "aider", "opencode"):
        assert backend in result.output


def test_launch_help_lists_required_options():
    result = _invoke("launch", "--help")
    assert result.exit_code == 0
    assert "--name" in result.output
    assert "--duration" in result.output
    assert "--session-timeout" in result.output


def test_kill_help():
    result = _invoke("kill", "--help")
    assert result.exit_code == 0


def test_status_help():
    result = _invoke("status", "--help")
    assert result.exit_code == 0


def test_log_help():
    result = _invoke("log", "--help")
    assert result.exit_code == 0


def test_persona_help_has_subcommands():
    result = _invoke("persona", "--help")
    assert result.exit_code == 0
    assert "list" in result.output
    assert "show" in result.output


def test_interests_help_has_subcommands():
    result = _invoke("interests", "--help")
    assert result.exit_code == 0
    assert "list-topics" in result.output
    assert "generate" in result.output
    assert "validate" in result.output


def test_batch_help_has_subcommands():
    result = _invoke("batch", "--help")
    assert result.exit_code == 0
    assert "create" in result.output
    assert "launch" in result.output
    assert "kill" in result.output


def test_batch_create_help_lists_required_options():
    result = _invoke("batch", "create", "--help")
    assert result.exit_code == 0
    # Batch create takes counts/axes
    assert "--n" in result.output or "-n" in result.output or "count" in result.output.lower()


# ── unknown command / flag error handling ────────────────────────────

def test_unknown_command_exits_nonzero():
    result = _invoke("definitely-not-a-command")
    assert result.exit_code != 0


def test_create_missing_required_args_errors_out():
    result = _invoke("create")
    assert result.exit_code != 0
    # Click's error message should mention a missing required option
    assert "missing" in result.output.lower() or "required" in result.output.lower()
