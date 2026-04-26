"""Tests for reva.backends — backend registry and command templates."""
import pytest

from reva.backends import BACKEND_CHOICES, Backend, get_backend


EXPECTED_BACKENDS = {"claude-code", "gemini-cli", "codex", "aider", "opencode"}


def test_all_expected_backends_registered():
    assert set(BACKEND_CHOICES) == EXPECTED_BACKENDS


@pytest.mark.parametrize("name", sorted(EXPECTED_BACKENDS))
def test_get_backend_returns_backend_for_known_name(name):
    backend = get_backend(name)
    assert isinstance(backend, Backend)
    assert backend.name == name


def test_get_backend_raises_for_unknown_name():
    with pytest.raises(ValueError, match="Unknown backend"):
        get_backend("not-a-real-backend")


@pytest.mark.parametrize("name", sorted(EXPECTED_BACKENDS))
def test_backend_has_required_fields(name):
    b = get_backend(name)
    assert b.name == name
    assert b.prompt_filename, f"{name} missing prompt_filename"
    assert b.command_template, f"{name} missing command_template"


@pytest.mark.parametrize("name", sorted(EXPECTED_BACKENDS))
def test_command_template_tees_to_agent_log(name):
    """Every backend must pipe its output through `tee -a agent.log` so the
    log viewer and resume logic have something to read."""
    b = get_backend(name)
    assert "tee -a agent.log" in b.command_template


@pytest.mark.parametrize("name", sorted(EXPECTED_BACKENDS))
def test_command_template_includes_stderr_merge(name):
    b = get_backend(name)
    assert "2>&1" in b.command_template, f"{name} command_template missing 2>&1"


def test_codex_uses_exec_subcommand():
    """Regression: codex must invoke `codex exec` (non-interactive) rather
    than the bare `codex` which drops into the interactive TUI and hangs.
    See commit 4e50698."""
    b = get_backend("codex")
    assert "codex exec" in b.command_template
    assert b.resume_command_template and "codex exec resume" in b.resume_command_template


def test_codex_resume_command_passes_prompt():
    """Regression: `codex exec resume --last` without a prompt falls back to
    interactive behavior. The resume path must re-send the initial prompt."""
    b = get_backend("codex")
    assert b.resume_command_template is not None
    assert 'initial_prompt.txt' in b.resume_command_template


def test_codex_skip_git_repo_check():
    """Codex refuses to run outside a git repo by default. Agent directories
    are usually not git repos, so --skip-git-repo-check must be present."""
    b = get_backend("codex")
    assert "--skip-git-repo-check" in b.command_template
    assert b.resume_command_template and "--skip-git-repo-check" in b.resume_command_template


def test_claude_code_uses_stream_json_output():
    """Claude-code's resume flow parses session IDs out of the stream-json
    log. Removing --output-format stream-json would break that parser."""
    b = get_backend("claude-code")
    assert "--output-format stream-json" in b.command_template


def test_claude_code_resume_uses_continue_with_prompt():
    """The claude-code resume path uses `claude --continue -p "$(cat initial_prompt.txt)"`.
    `--resume "$SESSION_ID"` was abandoned: it errors with "No deferred tool marker"
    after a SIGTERM-killed session. Bare `--continue` (no -p) was also insufficient:
    once the prior session ended cleanly, claude requires a prompt to continue.
    The combined `--continue -p ...` works in both cases and preserves history."""
    b = get_backend("claude-code")
    assert b.resume_command_template is not None
    assert "--continue" in b.resume_command_template
    assert '-p "$(cat initial_prompt.txt)"' in b.resume_command_template
    assert "--resume" not in b.resume_command_template
    assert "$SESSION_ID" not in b.resume_command_template


def test_claude_code_templates_have_model_placeholder():
    """Per-agent model selection: both the initial and resume templates must
    expose a `{model}` placeholder so cli.py can substitute either an empty
    string (use claude's default) or `--model <name>` (per agent's config.json
    `model` field). Without the placeholder, all agents share whatever model
    claude was last configured with — which makes qwerty81 (Opus) and
    qwerty82 (Sonnet) impossible to run side by side."""
    b = get_backend("claude-code")
    assert "{model}" in b.command_template, (
        "claude-code command_template must have a {model} placeholder so "
        "cli.py can pass --model per agent."
    )
    assert b.resume_command_template is not None
    assert "{model}" in b.resume_command_template, (
        "claude-code resume_command_template must have a {model} placeholder "
        "so resumes preserve the agent's chosen model."
    )


def test_claude_code_resume_preserves_mcp_config():
    """Regression: --mcp-config is a runtime flag, not persisted in session
    state. If the resume template omits it, the resumed agent loses access to
    paperlantern MCP tools — and any tool_use blocks from the prior transcript
    reference tools that no longer exist."""
    b = get_backend("claude-code")
    assert b.resume_command_template is not None
    assert "--mcp-config" in b.resume_command_template
    assert "paperlantern" in b.resume_command_template


@pytest.mark.parametrize(
    "template_attr", ["command_template", "resume_command_template"]
)
def test_claude_code_mcp_config_includes_koala(template_attr):
    """Regression: without the koala MCP server, the agent has no platform
    tools (get_my_profile, get_notifications, post_comment, post_verdict, ...)
    and falls back to curl against the REST API. Both the initial and resume
    paths must register the koala server, since --mcp-config is a runtime flag
    that is not persisted across resumes."""
    b = get_backend("claude-code")
    template = getattr(b, template_attr)
    assert template is not None, f"claude-code missing {template_attr}"
    assert "koala.science/mcp" in template, (
        f"{template_attr} does not register the koala MCP server URL"
    )
    assert "COALESCENCE_API_KEY" in template, (
        f"{template_attr} does not pass the koala bearer token "
        "(COALESCENCE_API_KEY is auto-exported from .api_key by the launch script)"
    )


def test_opencode_resume_command_passes_prompt():
    """Regression: `opencode run --session` without a message has no task to
    perform in headless mode — same failure mode as codex resume without a
    prompt. The resume path must re-send the initial prompt."""
    b = get_backend("opencode")
    assert b.resume_command_template is not None
    assert 'initial_prompt.txt' in b.resume_command_template


def test_opencode_has_session_id_extractor():
    """opencode doesn't emit session IDs in a claude-style JSON log, so it
    ships a custom shell extractor. Missing extractor → broken resume."""
    b = get_backend("opencode")
    assert b.session_id_extractor is not None
    assert "opencode session list" in b.session_id_extractor


def test_command_template_uses_cat_for_prompt():
    """$(cat initial_prompt.txt) must be used instead of inlining the prompt
    so that multiline prompts and shell metacharacters survive."""
    for name in ("claude-code", "gemini-cli", "codex", "aider", "opencode"):
        b = get_backend(name)
        assert 'initial_prompt.txt' in b.command_template, (
            f"{name} command_template should read from initial_prompt.txt"
        )


def test_gemini_cli_uses_skip_trust():
    """Regression: gemini-cli 0.39+ refuses to run in 'untrusted' directories
    in headless mode, exiting immediately with 'not running in a trusted
    directory'. Every reva agent dir triggers this. --skip-trust is required."""
    b = get_backend("gemini-cli")
    assert "--skip-trust" in b.command_template, (
        "gemini-cli backend must pass --skip-trust or headless runs crash-loop "
        "on every recent version of the CLI"
    )
