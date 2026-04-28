#!/usr/bin/env python3
"""Live monitor for qwerty81 agent logs. Prints key events as they happen.

Usage:
    python3 scripts/watch_agent.py                    # auto-detect latest log
    python3 scripts/watch_agent.py agent_configs/qwerty81/agent.log
"""
import json
import sys
import time
from pathlib import Path

AGENT_DIR = Path(__file__).parent.parent / "agent_configs" / "qwerty81"

TOOL_LABELS = {
    "mcp__koala__get_papers": "GET_PAPERS",
    "mcp__koala__search_papers": "SEARCH_PAPERS",
    "mcp__koala__get_paper": "GET_PAPER",
    "mcp__koala__get_comments": "GET_COMMENTS",
    "mcp__koala__post_comment": "POST_COMMENT",
    "mcp__koala__post_verdict": "POST_VERDICT",
    "mcp__koala__get_notifications": "GET_NOTIFS",
    "mcp__koala__get_unread_count": "UNREAD_COUNT",
    "mcp__koala__mark_notifications_read": "MARK_READ",
    "mcp__koala__get_verdicts": "GET_VERDICTS",
    "mcp__koala__get_my_profile": "MY_PROFILE",
    "ScheduleWakeup": "WAKEUP",
    "WebSearch": "WEB_SEARCH",
}

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
DIM = "\033[2m"
RESET = "\033[0m"

comments_posted = 0
papers_seen = set()
errors = 0


def fmt_tool_use(name: str, inp: dict) -> str:
    global papers_seen
    label = TOOL_LABELS.get(name, name)
    color = RESET

    if label == "POST_COMMENT":
        color = GREEN
        pid = inp.get("paper_id", "?")
        return f"{color}>>> {label} paper={pid[:8]}{RESET}"
    if label == "POST_VERDICT":
        color = GREEN
        pid = inp.get("paper_id", "?")
        score = inp.get("score", "?")
        return f"{color}>>> {label} paper={pid[:8]} score={score}{RESET}"
    if label == "GET_PAPERS":
        limit = inp.get("limit", 20)
        domain = inp.get("domain", "")
        extra = f" domain={domain}" if domain else ""
        return f"{CYAN}{label} limit={limit}{extra}{RESET}"
    if label == "SEARCH_PAPERS":
        q = inp.get("query", "")[:40]
        return f"{CYAN}{label} q=\"{q}\"{RESET}"
    if label == "GET_COMMENTS":
        pid = inp.get("paper_id", "?")
        papers_seen.add(pid)
        return f"{DIM}{label} paper={pid[:8]}{RESET}"
    if label == "WAKEUP":
        return f"{YELLOW}⏰ {label}{RESET}"
    if label == "WEB_SEARCH":
        q = inp.get("query", "")[:50]
        return f"{DIM}{label} \"{q}\"{RESET}"

    return f"{DIM}{label}{RESET}"


def fmt_tool_result(content: str) -> str | None:
    global errors
    lower = content[:200].lower()
    if "error" in lower or "isError" in lower or "validation error" in lower:
        errors += 1
        snippet = content[:120].replace("\n", " ")
        return f"{RED}ERROR: {snippet}{RESET}"
    return None


def process_line(raw: str):
    global comments_posted
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        return

    msg_type = d.get("type", "")
    ts = d.get("timestamp", "")
    if not ts:
        ts_prefix = ""
    else:
        ts_prefix = ts[11:19] + " "

    if msg_type == "system" and d.get("subtype") == "init":
        sid = d.get("session_id", "?")[:8]
        print(f"{ts_prefix}{CYAN}=== SESSION INIT {sid} ==={RESET}")
        return

    content = d.get("message", {}).get("content", [])
    if not isinstance(content, list):
        return

    for block in content:
        if not isinstance(block, dict):
            continue

        if block.get("type") == "tool_use":
            name = block.get("name", "")
            inp = block.get("input", {})
            line = fmt_tool_use(name, inp)
            if line:
                print(f"{ts_prefix}{line}")
            if name == "mcp__koala__post_comment":
                comments_posted += 1

        if block.get("type") == "tool_result":
            text = ""
            rc = block.get("content", "")
            if isinstance(rc, str):
                text = rc
            elif isinstance(rc, list):
                text = " ".join(
                    b.get("text", "") for b in rc if isinstance(b, dict)
                )
            err = fmt_tool_result(text)
            if err:
                print(f"{ts_prefix}{err}")


def status_line():
    return (
        f"{DIM}[comments={comments_posted} "
        f"papers_touched={len(papers_seen)} "
        f"errors={errors}]{RESET}"
    )


def find_log() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    agent_log = AGENT_DIR / "agent.log"
    if agent_log.exists():
        return agent_log
    errs = sorted(AGENT_DIR.glob("cluster.*.err"), key=lambda p: p.stat().st_mtime)
    if errs:
        return errs[-1]
    print("No log file found. Pass path as argument.", file=sys.stderr)
    sys.exit(1)


def main():
    log_path = find_log()
    print(f"{CYAN}Watching: {log_path}{RESET}")
    print(f"{DIM}Ctrl+C to stop{RESET}\n")

    with open(log_path) as f:
        f.seek(0, 2)
        last_status = time.time()
        while True:
            line = f.readline()
            if line:
                process_line(line.strip())
                now = time.time()
                if now - last_status > 30:
                    print(status_line())
                    last_status = now
            else:
                time.sleep(1)


if __name__ == "__main__":
    main()
