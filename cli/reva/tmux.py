"""tmux session management for reva agents."""

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SESSION_PREFIX = "reva_"


def _tmux_bin() -> str:
    path = shutil.which("tmux")
    if path is None:
        raise RuntimeError("tmux is not installed. Install it with: apt install tmux")
    return path


def _run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_tmux_bin()] + args,
        capture_output=True,
        text=True,
        check=check,
    )


def session_name(agent_name: str) -> str:
    return f"{SESSION_PREFIX}{agent_name}"


def has_session(agent_name: str) -> bool:
    result = _run(["has-session", "-t", session_name(agent_name)], check=False)
    return result.returncode == 0


def build_launch_script(
    backend_command: str,
    duration_hours: float | None = None,
) -> str:
    """Build a bash script that runs the backend in a restart loop.

    If duration_hours is set, the loop exits after that many hours.
    """
    if duration_hours is not None:
        timeout_secs = int(duration_hours * 3600)
        return f"""\
#!/usr/bin/env bash
TIMEOUT={timeout_secs}
START=$(date +%s)

while true; do
    ELAPSED=$(( $(date +%s) - START ))
    [ $ELAPSED -ge $TIMEOUT ] && echo "[reva] duration reached, stopping." && break
    REMAINING=$((TIMEOUT - ELAPSED))

    timeout "${{REMAINING}}s" {backend_command}
    EXIT_CODE=$?
    echo "[reva] agent exited ($EXIT_CODE), restarting in 5s..."
    sleep 5
done
"""
    else:
        return f"""\
#!/usr/bin/env bash
while true; do
    {backend_command}
    EXIT_CODE=$?
    echo "[reva] agent exited ($EXIT_CODE), restarting in 5s..."
    sleep 5
done
"""


def create_session(
    agent_name: str,
    working_dir: str,
    launch_script: str,
) -> None:
    """Create a detached tmux session running the launch script.

    Writes the script to a file in the agent directory so tmux can execute it
    reliably, and forwards the current environment into the session.
    """
    name = session_name(agent_name)
    if has_session(agent_name):
        raise RuntimeError(f"tmux session {name!r} already exists. Kill it first.")

    # write env vars to a file (not the command line, to avoid leaking in ps)
    env_keys = [k for k in os.environ if k.startswith(("GEMINI_", "ANTHROPIC_", "OPENAI_", "GOOGLE_"))]
    env_path = Path(working_dir) / ".reva_env.sh"
    env_lines = [f"export {k}={os.environ[k]!r}" for k in env_keys]
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    env_path.chmod(0o600)

    # write launch script with env sourcing
    script_path = Path(working_dir) / ".reva_launch.sh"
    full_script = f"source {env_path}\n{launch_script}"
    script_path.write_text(full_script, encoding="utf-8")
    script_path.chmod(0o755)

    # create session then send-keys (not bash -c) so the shell is interactive
    # and properly attached to the PTY — some backends (gemini-cli) get
    # suspended (SIGTTIN) if they aren't the foreground process group leader.
    _run([
        "new-session", "-d",
        "-s", name,
        "-c", working_dir,
    ])
    _run(["send-keys", "-t", name, f"bash {script_path}", "Enter"])


def kill_session(agent_name: str) -> bool:
    """Kill a tmux session. Returns True if it existed."""
    if not has_session(agent_name):
        return False
    _run(["kill-session", "-t", session_name(agent_name)])
    return True


@dataclass
class SessionInfo:
    agent_name: str
    session: str
    created: datetime | None


def list_sessions() -> list[SessionInfo]:
    """List all reva.* tmux sessions."""
    result = _run(["ls", "-F", "#{session_name}\t#{session_created}"], check=False)
    if result.returncode != 0:
        return []

    sessions = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        name, created_ts = parts
        if not name.startswith(SESSION_PREFIX):
            continue

        agent_name = name[len(SESSION_PREFIX):]
        try:
            created = datetime.fromtimestamp(int(created_ts), tz=timezone.utc)
        except (ValueError, OSError):
            created = None

        sessions.append(SessionInfo(
            agent_name=agent_name,
            session=name,
            created=created,
        ))

    return sessions


def kill_all_sessions() -> int:
    """Kill all reva.* sessions. Returns count killed."""
    sessions = list_sessions()
    for s in sessions:
        _run(["kill-session", "-t", s.session], check=False)
    return len(sessions)
