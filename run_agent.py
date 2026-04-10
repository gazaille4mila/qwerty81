#!/usr/bin/env python3
"""
Run a single agent on the Moltbook platform.

Usage:
    python run_agent.py \
        --role agent_definition/roles/novelty.md \
        --interests agent_definition/research_interests/nlp.md \
        --persona agent_definition/personas/optimistic.md \
        --scaffolding agent_definition/harness/scaffolding.md \
        --mcp-config .mcp.json \
        [--duration 3600] [--backend claude_code]

Environment variables:
    COALESCENCE_API_KEY     Coalescence bearer token (cs_...)
"""

import argparse
import sys
from pathlib import Path

from agent_definition.prompt_builder import build_prompt


def load(path: str) -> str:
    p = Path(path)
    if not p.exists():
        sys.exit(f"File not found: {path}")
    return p.read_text(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True)
    parser.add_argument("--interests", required=True)
    parser.add_argument("--persona", required=True)
    parser.add_argument("--scaffolding", required=True)
    parser.add_argument("--mcp-config", required=True, help="Path to .mcp.json")
    parser.add_argument("--duration", type=float, default=None,
                        help="How long to run in seconds (omit to run indefinitely)")
    parser.add_argument("--backend", default="claude_code", choices=["claude_code"],
                        help="Agent backend to use")
    args = parser.parse_args()

    system_prompt = build_prompt(
        role_prompt=load(args.role),
        research_interests_prompt=load(args.interests),
        persona_prompt=load(args.persona),
        scaffolding_prompt=load(args.scaffolding),
    )

    if args.backend == "claude_code":
        from launcher.backends.claude_code import run
        run(system_prompt, mcp_config=args.mcp_config, duration=args.duration)


if __name__ == "__main__":
    main()
