#!/usr/bin/env python3
"""Check which competing agents are currently active on Koala Science.

Fetches the leaderboard, then for each agent fetches their most recent
comment to determine last-active time. Reports active agents within a
configurable time window.

Read-only. GETs only, no karma cost.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
KEY_PATH = REPO_ROOT / "agent_configs/qwerty81/.api_key"
BASE = "https://koala.science/api/v1"

ORGANIZER_OWNER = "Tomás Vergara Browne"
SIBLINGS = {"qwerty82", "qwerty83"}


def fetch(url: str, headers: dict) -> object:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def time_ago(dt: datetime) -> str:
    delta = datetime.now(timezone.utc) - dt
    mins = int(delta.total_seconds() / 60)
    if mins < 1:
        return "<1m ago"
    if mins < 60:
        return f"{mins}m ago"
    hours = mins // 60
    remaining = mins % 60
    if hours < 24:
        return f"{hours}h{remaining}m ago"
    days = hours // 24
    return f"{days}d{hours % 24}h ago"


def main() -> None:
    parser = argparse.ArgumentParser(description="Check active Koala Science agents")
    parser.add_argument("--window", type=int, default=60, help="Activity window in minutes (default: 60)")
    parser.add_argument("--all", action="store_true", help="Show all agents, not just active ones")
    args = parser.parse_args()

    key = KEY_PATH.read_text().strip()
    headers = {"Authorization": f"Bearer {key}"}

    now = datetime.now(timezone.utc)

    print(f"[1/2] Fetching leaderboard...")
    lb = fetch(f"{BASE}/leaderboard/agents?limit=100", headers)
    agents_with_comments = [a for a in lb if a["comment_count"] > 0]
    print(f"  {len(lb)} agents total, {len(agents_with_comments)} with comments")

    print(f"[2/2] Fetching last comment for {len(agents_with_comments)} agents...")
    results = []
    for a in agents_with_comments:
        try:
            comments = fetch(f"{BASE}/users/{a['id']}/comments?limit=1", headers)
            if comments:
                last_ts = comments[0].get("created_at", "")
                last_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                mins_ago = (now - last_dt).total_seconds() / 60
            else:
                last_dt = None
                mins_ago = float("inf")
        except (urllib.error.HTTPError, Exception) as e:
            print(f"  ERR {a['name']}: {e}", file=sys.stderr)
            last_dt = None
            mins_ago = float("inf")

        is_organizer = a.get("owner_name") == ORGANIZER_OWNER
        is_sibling = a["name"] in SIBLINGS

        results.append({
            "name": a["name"],
            "efk": a.get("estimated_final_karma", 0),
            "karma": a.get("karma", 0),
            "comments": a["comment_count"],
            "papers": a.get("papers_reviewing", 0),
            "owner": a.get("owner_name", "?"),
            "last_dt": last_dt,
            "mins_ago": mins_ago,
            "is_organizer": is_organizer,
            "is_sibling": is_sibling,
        })
        time.sleep(0.03)

    results.sort(key=lambda r: r["mins_ago"])

    active = [r for r in results if r["mins_ago"] <= args.window]
    inactive = [r for r in results if r["mins_ago"] > args.window]

    print()
    print("=" * 100)
    print(f"ACTIVE in the last {args.window} min: {len(active)} agents")
    print("=" * 100)
    if active:
        print(f"  {'Agent':<30s}  {'Last active':>12s}  {'EFK':>8s}  {'Karma':>7s}  {'Cmts':>5s}  {'Papers':>6s}  Owner")
        print(f"  {'-'*30}  {'-'*12}  {'-'*8}  {'-'*7}  {'-'*5}  {'-'*6}  {'-'*25}")
        for r in active:
            tag = ""
            if r["is_organizer"]:
                tag = " [ORG]"
            elif r["is_sibling"]:
                tag = " [SIB]"
            ago = time_ago(r["last_dt"]) if r["last_dt"] else "?"
            print(f"  {r['name'] + tag:<30s}  {ago:>12s}  {r['efk']:8.1f}  {r['karma']:7.2f}  {r['comments']:5d}  {r['papers']:6d}  {r['owner']}")
    else:
        print("  (none)")

    if args.all or not active:
        print()
        print(f"INACTIVE (>{args.window} min since last comment): {len(inactive)} agents")
        print(f"  {'Agent':<30s}  {'Last active':>12s}  {'EFK':>8s}  {'Cmts':>5s}  Owner")
        print(f"  {'-'*30}  {'-'*12}  {'-'*8}  {'-'*5}  {'-'*25}")
        for r in inactive:
            tag = ""
            if r["is_organizer"]:
                tag = " [ORG]"
            elif r["is_sibling"]:
                tag = " [SIB]"
            ago = time_ago(r["last_dt"]) if r["last_dt"] else "never"
            print(f"  {r['name'] + tag:<30s}  {ago:>12s}  {r['efk']:8.1f}  {r['comments']:5d}  {r['owner']}")

    no_comments = [a for a in lb if a["comment_count"] == 0]
    if no_comments:
        print(f"\n  + {len(no_comments)} agents with 0 comments (never active)")


if __name__ == "__main__":
    main()
