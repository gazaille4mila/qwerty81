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
    COALESCENCE_API_KEY     Coalescence bearer token (cs_...) — or pass via --coalescence-api-key
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
    parser.add_argument("--review-methodology", default="",
                        help="Path to review methodology .md file")
    parser.add_argument("--review-format", default="",
                        help="Path to review format .md file")
    parser.add_argument("--coalescence-api-key", default=None,
                        help="Coalescence bearer token (falls back to COALESCENCE_API_KEY env var)")
    parser.add_argument("--paper-lantern-api-key", default=None,
                        help="Paper Lantern API key (falls back to PAPER_LANTERN_API_KEY env var). "
                             "Optional — if omitted, the paperlantern MCP server is not attached.")
    parser.add_argument("--duration", type=float, default=None,
                        help="How long to run in minutes (omit to run indefinitely)")
    parser.add_argument("--backend", default="claude_code", choices=["claude_code"],
                        help="Agent backend to use")
    args = parser.parse_args()

    review_methodology = load(args.review_methodology) if args.review_methodology else ""
    review_format = load(args.review_format) if args.review_format else ""

    system_prompt = build_prompt(
        role_prompt=load(args.role),
        research_interests_prompt=load(args.interests),
        persona_prompt=load(args.persona),
        scaffolding_prompt=load(args.scaffolding),
        review_methodology_prompt=review_methodology,
        review_format_prompt=review_format,
    )

    import os
    api_key = args.coalescence_api_key or os.environ["COALESCENCE_API_KEY"]
    pl_api_key = args.paper_lantern_api_key or os.environ.get("PAPER_LANTERN_API_KEY")

    if args.backend == "claude_code":
        from launcher.backends.claude_code import run
        run(
            system_prompt,
            coalescence_api_key=api_key,
            paper_lantern_api_key=pl_api_key,
            duration=args.duration,
        )


if __name__ == "__main__":
    main()
