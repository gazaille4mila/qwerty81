#!/usr/bin/env python3
"""
Run a single sampled agent on the Coalescence platform.

Usage:
    python run_agent.py \
        --role agent_definition/roles/novelty.md \
        --interests agent_definition/research_interests/nlp.md \
        --persona agent_definition/personas/optimistic.md \
        --scaffolding agent_definition/harness/scaffolding.md \
        [--gpu] [--max-turns 20] [--model claude-haiku-4-5-20251001]

Environment variables:
    ANTHROPIC_API_KEY       Claude API key
    COALESCENCE_API_KEY     Coalescence bearer token (cs_...)
"""
import argparse
import os
import sys
from pathlib import Path

from agent_definition.prompt_builder import build_prompt
from agent_definition.harness import Agent


def load(path: str) -> str:
    p = Path(path)
    if not p.exists():
        sys.exit(f"File not found: {path}")
    return p.read_text(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Run a Coalescence reviewing agent.")
    parser.add_argument("--role", required=True, help="Path to role prompt .md")
    parser.add_argument("--interests", required=True, help="Path to research interests prompt .md")
    parser.add_argument("--persona", required=True, help="Path to persona prompt .md")
    parser.add_argument("--scaffolding", required=True, help="Path to scaffolding prompt .md")
    parser.add_argument("--gpu", action="store_true", help="Enable run_code tool (GPU experiments)")
    parser.add_argument("--max-turns", type=int, default=20)
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    args = parser.parse_args()

    system_prompt = build_prompt(
        role_prompt=load(args.role),
        research_interests_prompt=load(args.interests),
        persona_prompt=load(args.persona),
        scaffolding_prompt=load(args.scaffolding),
    )

    agent = Agent(
        system_prompt=system_prompt,
        coalescence_api_key=os.environ.get("COALESCENCE_API_KEY"),
        model=args.model,
        max_turns=args.max_turns,
        has_gpu=args.gpu,
    )
    agent.run()


if __name__ == "__main__":
    main()
