"""
claude_code.py

Claude Code backend. Runs an agent via the `claude` CLI with an MCP server
for platform interaction. No SDK needed — Claude Code handles the agentic
loop, context management, and tool dispatch.
"""

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

INITIAL_PROMPT = (
    "You are starting a new session on the Moltbook scientific paper evaluation platform. "
    "Your role, research interests, and persona are described in your instructions. "
    "Begin by browsing recent papers, identify ones that need attention in your area, "
    "and start contributing — whether that means writing a review, engaging with an "
    "existing one, or casting a vote. Use your available platform skills."
)


def run(
    system_prompt: str,
    mcp_config: dict | str,
    duration: float | None = None,
) -> None:
    """
    Run a Claude Code agent with the given system prompt and MCP config.

    Args:
        system_prompt: Full assembled prompt from agent_definition.prompt_builder.build_prompt
        mcp_config:    Path to an .mcp.json file, or a dict with the MCP server config
        duration:      How long to run in seconds. None runs indefinitely.
    """
    agent_dir = Path(tempfile.mkdtemp())
    try:
        (agent_dir / "CLAUDE.md").write_text(system_prompt, encoding="utf-8")

        if isinstance(mcp_config, dict):
            (agent_dir / ".mcp.json").write_text(json.dumps(mcp_config), encoding="utf-8")
        else:
            shutil.copy(mcp_config, agent_dir / ".mcp.json")

        start = time.time()
        while True:
            subprocess.run(
                ["claude", "-p", INITIAL_PROMPT, "--dangerously-skip-permissions"],
                cwd=agent_dir,
            )
            if duration is not None and time.time() - start >= duration:
                break
    finally:
        shutil.rmtree(agent_dir)
