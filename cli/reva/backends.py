"""Backend definitions: command templates and system-prompt filenames per backend."""

from dataclasses import dataclass

from reva.env import koala_base_url

# MCP server config inlined into the claude-code command template.
#
# Two servers are registered:
#   - paperlantern: research-helper MCP, public key is fine to inline.
#   - koala: the platform itself (profile, notifications, papers, comments,
#     verdicts). Bearer-token authenticated; the token comes from
#     $COALESCENCE_API_KEY, which the launch script auto-exports from the
#     agent's `.api_key` file (see tmux.py:_LOAD_AGENT_ENV_FUNC).
#
# The JSON is wrapped in single quotes at the shell level so its internal
# double quotes pass through unchanged. To get bash to expand
# $COALESCENCE_API_KEY *inside* a single-quoted string, we close the single
# quote, re-open as a double-quoted segment containing the variable, and
# resume single-quoting — the standard '"$VAR"' dance.
#
# Braces are doubled ({{ / }}) so reva's str.format() call in cli.py — which
# substitutes {prompt} for other backends — does not interpret them as format
# fields; doubling collapses back to single braces at format time.
_CLAUDE_MCP_CONFIG = (
    "'{{"
    '"mcpServers":{{'
    '"paperlantern":{{'
    '"type":"http",'
    '"url":"https://mcp.paperlantern.ai/chat/mcp?key=pl_cd1099cd5b35f6c193f9"'
    "}},"
    '"koala":{{'
    '"type":"http",'
    '"url":"https://koala.science/mcp",'
    '"headers":{{'
    '"Authorization":"Bearer \'"$COALESCENCE_API_KEY"\'"'
    "}}"
    "}}"
    "}}"
    "}}'"
)


def _codex_koala_mcp_config() -> str:
    base = koala_base_url()
    return (
        f'-c \'mcp_servers.koala.url="{base}/mcp"\''
        ' -c \'mcp_servers.koala.bearer_token_env_var="COALESCENCE_API_KEY"\''
    )


@dataclass(frozen=True)
class Backend:
    name: str
    prompt_filename: str  # backend-specific system prompt file (e.g. CLAUDE.md)
    command_template: str  # shell command; {prompt} is replaced with initial prompt
    resume_command_template: str | None = None  # command to resume last session
    # Shell command run after each invocation whose stdout is written to
    # last_session_id. Only used when resume_command_template contains
    # $SESSION_ID. When None and $SESSION_ID is present, the session ID is
    # parsed from the stream-json agent.log (claude-code default).
    session_id_extractor: str | None = None


def _build_backends() -> dict[str, Backend]:
    codex_mcp = _codex_koala_mcp_config()
    return {
        "claude-code": Backend(
            name="claude-code",
            prompt_filename="CLAUDE.md",
            command_template=(
                'claude -p "$(cat initial_prompt.txt)"'
                " --dangerously-skip-permissions"
                " --output-format stream-json --verbose"
                f" --mcp-config {_CLAUDE_MCP_CONFIG}"
                " 2>&1 | tee -a agent.log"
            ),
            # `--continue` resumes the most recent conversation in the cwd, which
            # works after a SIGTERM (`--resume "$SESSION_ID"` does not — it requires
            # a deferred-tool marker the SIGTERM-killed session lacks). `-p` is
            # required: bare `--continue` errors with "Provide a prompt to continue
            # the conversation" once the prior session ended cleanly. We re-feed
            # initial_prompt.txt as that prompt so the agent has a fresh task hook
            # but keeps the prior conversation history.
            # --mcp-config must be re-passed on resume: it is a runtime flag, not
            # persisted in the session state, so omitting it drops both
            # paperlantern and koala (i.e. all platform tools).
            resume_command_template=(
                'claude --continue -p "$(cat initial_prompt.txt)"'
                " --dangerously-skip-permissions"
                " --output-format stream-json --verbose"
                f" --mcp-config {_CLAUDE_MCP_CONFIG}"
                " 2>&1 | tee -a agent.log"
            ),
        ),
        "gemini-cli": Backend(
            name="gemini-cli",
            prompt_filename="GEMINI.md",
            # Use $(cat) to safely handle multiline prompts; no resume since
            # headless sessions don't persist a resumable state.
            # --skip-trust: recent gemini-cli (0.39+) refuses to run in
            # "untrusted" directories in headless mode, which includes every
            # reva agent dir. Without the flag the backend exits immediately
            # with "not running in a trusted directory" and the restart loop
            # spins.
            command_template='gemini --yolo --skip-trust -p "$(cat initial_prompt.txt)" 2>&1 | tee -a agent.log',
        ),
        "codex": Backend(
            name="codex",
            prompt_filename="AGENTS.md",
            command_template=(
                "codex exec"
                f" {codex_mcp}"
                " --skip-git-repo-check"
                ' --dangerously-bypass-approvals-and-sandbox "$(cat initial_prompt.txt)"'
                " 2>&1 | tee -a agent.log"
            ),
            # --last resumes the most recent session in the current working directory.
            # Re-send the initial work loop prompt so non-interactive resume has a task
            # to perform instead of falling back to interactive behavior.
            resume_command_template=(
                "codex exec resume"
                f" {codex_mcp}"
                " --last --skip-git-repo-check"
                ' --dangerously-bypass-approvals-and-sandbox "$(cat initial_prompt.txt)"'
                " 2>&1 | tee -a agent.log"
            ),
        ),
        "aider": Backend(
            name="aider",
            prompt_filename="AIDER.md",
            # aider auto-persists chat history in .aider.chat.history.md; no
            # explicit resume needed — context is available on every restart.
            command_template='aider --yes --message "$(cat initial_prompt.txt)" 2>&1 | tee -a agent.log',
        ),
        "opencode": Backend(
            name="opencode",
            prompt_filename="OPENCODE.md",
            command_template='opencode run --dangerously-skip-permissions "$(cat initial_prompt.txt)" 2>&1 | tee -a agent.log',
            # Re-send the initial work loop prompt so non-interactive resume has
            # a task to perform instead of falling back to interactive behavior
            # (same reasoning as the codex resume above).
            resume_command_template=(
                'opencode run --session "$SESSION_ID" --dangerously-skip-permissions'
                ' "$(cat initial_prompt.txt)" 2>&1 | tee -a agent.log'
            ),
            session_id_extractor=(
                'opencode session list --format json -n 1 2>/dev/null'
                ' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0][\'id\'] if d else \'\')"'
            ),
        ),
    }


BACKEND_CHOICES = ["claude-code", "gemini-cli", "codex", "aider", "opencode"]


def get_backend(name: str) -> Backend:
    backends = _build_backends()
    if name not in backends:
        raise ValueError(f"Unknown backend: {name!r}. Choose from: {BACKEND_CHOICES}")
    return backends[name]
