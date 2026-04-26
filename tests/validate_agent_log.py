"""Scan an agent.log for paper_id-prefix-vs-UUID regressions.

Background: in SLURM job 9360098 (2026-04-25) the agent passed 8-char hex
prefixes (the shape used for branch names like `agent-reasoning/<name>/<prefix>`)
to `mcp__koala__get_paper` / `mcp__koala__get_comments`. The Koala API expects
the full UUID and returned 422 for every such call, wasting ~9 tool turns and
muddying the karma signal.

This script parses an agent.log (Claude Code session JSONL) and exits non-zero
if any 422 response was produced by a prefix-shaped paper_id on those two
tools. Run after a soak to confirm the GLOBAL_RULES.md / tools.py fix landed.

Usage:
    python tests/validate_agent_log.py <path/to/agent.log>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


PREFIX_RE = re.compile(r"^[0-9a-f]{8}$")
TARGET_TOOLS = {"mcp__koala__get_paper", "mcp__koala__get_comments"}


@dataclass(frozen=True)
class Violation:
    line: int
    tool_name: str
    paper_id: str
    error_snippet: str


def _iter_content_blocks(line: str):
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return
    msg = obj.get("message")
    if not isinstance(msg, dict):
        return
    content = msg.get("content")
    if not isinstance(content, list):
        return
    for block in content:
        if isinstance(block, dict):
            yield block


def scan_log(path: Path) -> list[Violation]:
    pending: dict[str, tuple[str, str, int]] = {}
    violations: list[Violation] = []
    with open(path) as f:
        for ln, raw in enumerate(f, 1):
            for block in _iter_content_blocks(raw):
                btype = block.get("type")
                if btype == "tool_use":
                    name = block.get("name", "")
                    if name not in TARGET_TOOLS:
                        continue
                    inp = block.get("input") or {}
                    pid = inp.get("paper_id")
                    if isinstance(pid, str) and PREFIX_RE.match(pid):
                        tid = block.get("id")
                        if isinstance(tid, str):
                            pending[tid] = (name, pid, ln)
                elif btype == "tool_result":
                    tid = block.get("tool_use_id")
                    if not isinstance(tid, str) or tid not in pending:
                        continue
                    if not block.get("is_error"):
                        pending.pop(tid, None)
                        continue
                    content = block.get("content")
                    text = content if isinstance(content, str) else json.dumps(content)
                    if "422" in text:
                        name, pid, use_ln = pending.pop(tid)
                        snippet = text[:200]
                        violations.append(
                            Violation(
                                line=ln,
                                tool_name=name,
                                paper_id=pid,
                                error_snippet=snippet,
                            )
                        )
                    else:
                        pending.pop(tid, None)
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("log", type=Path, help="Path to agent.log")
    args = parser.parse_args(argv)

    violations = scan_log(args.log)
    if not violations:
        print(f"OK: no prefix-paper_id 422s in {args.log}")
        return 0

    print(f"FAIL: {len(violations)} prefix-paper_id 422 error(s) in {args.log}")
    for v in violations:
        print(f"  line {v.line}: {v.tool_name} paper_id={v.paper_id!r}")
        print(f"    {v.error_snippet}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
