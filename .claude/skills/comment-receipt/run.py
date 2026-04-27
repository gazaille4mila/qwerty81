#!/usr/bin/env python3
"""Measure how qwerty81's comments are being received by other agents.

Read-only. Pulls leaderboard, qwerty81's comment list, and the full thread
for each paper qwerty81 has commented on. Reports citations / replies /
mentions and the cites-per-comment ratio.

Caches raw JSON under /tmp/q81_analysis/ for follow-up queries.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
KEY_PATH = REPO_ROOT / "agent_configs/qwerty81/.api_key"
CACHE_DIR = Path("/tmp/q81_analysis")
BASE = "https://koala.science/api/v1"

Q81_ACTOR = os.environ.get("Q81_ACTOR", "69f37a13-0440-4509-a27c-3b92114a7591")
Q81_NAME = os.environ.get("Q81_NAME", "qwerty81")


def fetch(url: str, headers: dict) -> object:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = KEY_PATH.read_text().strip()
    headers = {"Authorization": f"Bearer {key}"}

    print("[1/4] Fetching leaderboard...")
    lb = fetch(f"{BASE}/leaderboard/agents?limit=100", headers)
    (CACHE_DIR / "lb.json").write_text(json.dumps(lb))
    lb_by_id = {r["id"]: r for r in lb}
    print(f"  {len(lb)} agents")

    print(f"[2/4] Fetching {Q81_NAME}'s comments...")
    q81 = fetch(f"{BASE}/users/{Q81_ACTOR}/comments?limit=200", headers)
    (CACHE_DIR / "q81_comments.json").write_text(json.dumps(q81))
    print(f"  {len(q81)} comments")

    q81_by_paper: dict[str, list[dict]] = defaultdict(list)
    for c in q81:
        q81_by_paper[c["paper_id"]].append(c)
    print(f"  across {len(q81_by_paper)} papers")

    print(f"[3/4] Fetching {len(q81_by_paper)} paper threads...")
    all_threads: dict[str, list[dict]] = {}
    for pid in q81_by_paper:
        try:
            all_threads[pid] = fetch(f"{BASE}/comments/paper/{pid}", headers)
        except urllib.error.HTTPError as e:
            print(f"  ERR {pid[:8]}: {e}")
            continue
        time.sleep(0.05)
    (CACHE_DIR / "all_threads.json").write_text(json.dumps(all_threads))
    print(f"  {sum(len(t) for t in all_threads.values())} comments fetched")

    print("[4/4] Computing engagement metrics...")
    print()

    papers_summary: list[dict] = []
    all_engagements: list[dict] = []
    total_replies = total_citations = total_mentions = 0

    for pid, qcs in q81_by_paper.items():
        thread = all_threads.get(pid, [])
        paper_title = qcs[0].get("paper_title", "?")
        pid_q81_ids = {c["id"] for c in qcs}

        replies: list[dict] = []
        citations: list[tuple[dict, str]] = []
        mentions: list[dict] = []

        for c in thread:
            if c["author_id"] == Q81_ACTOR:
                continue
            body = c.get("content_markdown") or ""
            if c.get("parent_id") in pid_q81_ids:
                replies.append(c)
                continue
            cited = False
            for qid in pid_q81_ids:
                if f"[[comment:{qid}]]" in body:
                    citations.append((c, qid))
                    cited = True
                    break
            if cited:
                continue
            if re.search(rf"\b{re.escape(Q81_NAME)}\b", body, re.IGNORECASE):
                mentions.append(c)

        total_replies += len(replies)
        total_citations += len(citations)
        total_mentions += len(mentions)

        for r in replies:
            all_engagements.append({
                "pid": pid[:8], "title": paper_title[:60], "type": "REPLY",
                "author": r["author_name"], "author_id": r["author_id"],
                "snippet": (r.get("content_markdown") or "")[:250].replace("\n", " "),
            })
        for c, qid in citations:
            all_engagements.append({
                "pid": pid[:8], "title": paper_title[:60], "type": "CITE",
                "author": c["author_name"], "author_id": c["author_id"],
                "snippet": (c.get("content_markdown") or "")[:250].replace("\n", " "),
            })
        for m in mentions:
            all_engagements.append({
                "pid": pid[:8], "title": paper_title[:60], "type": "MENTION",
                "author": m["author_name"], "author_id": m["author_id"],
                "snippet": (m.get("content_markdown") or "")[:250].replace("\n", " "),
            })

        papers_summary.append({
            "pid": pid[:8], "title": paper_title[:55],
            "q81_cmts": len(qcs), "thread_total": len(thread),
            "replies": len(replies), "citations": len(citations),
            "mentions": len(mentions),
        })

    papers_summary.sort(key=lambda p: -(p["replies"] + p["citations"] + p["mentions"]))

    print("=" * 100)
    print(f"HEADLINE: {Q81_NAME} has {len(q81)} comments across {len(q81_by_paper)} papers")
    total_eng = total_citations + total_replies + total_mentions
    print(f"  {total_citations} citations + {total_replies} replies + {total_mentions} mentions = {total_eng} engagements")
    papers_with_eng = sum(1 for p in papers_summary if (p["replies"] + p["citations"] + p["mentions"]) > 0)
    print(f"  {papers_with_eng}/{len(papers_summary)} papers have ≥1 engagement")
    print(f"  cites/comment:          {total_citations / len(q81):.2f}")
    print(f"  all-engagement/comment: {total_eng / len(q81):.2f}")

    auth_counter: Counter[tuple[str, str]] = Counter()
    for e in all_engagements:
        auth_counter[(e["author"], e["author_id"])] += 1
    print()
    print("=== Engaging authors ===")
    print(f"  {'author':<28} {'count':>5}  {'owner':<28}")
    for (name, aid), n in auth_counter.most_common():
        owner = (lb_by_id.get(aid, {}).get("owner_name") or "?")[:26]
        print(f"  {name[:26]:<28} {n:>5}  {owner:<28}")

    print()
    print("=== Per-paper top 15 by engagement ===")
    print(f"  {'pid':<10} {'q81':>4} {'thr':>4} {'rep':>3} {'cit':>3} {'men':>3}  title")
    for p in papers_summary[:15]:
        print(f"  {p['pid']} {p['q81_cmts']:>4} {p['thread_total']:>4} "
              f"{p['replies']:>3} {p['citations']:>3} {p['mentions']:>3}  {p['title']}")

    out = {
        "engagements": all_engagements,
        "papers": papers_summary,
        "totals": {
            "q81_comments": len(q81),
            "papers": len(q81_by_paper),
            "replies": total_replies,
            "citations": total_citations,
            "mentions": total_mentions,
            "papers_with_eng": papers_with_eng,
            "cites_per_comment": total_citations / len(q81) if q81 else 0,
        },
    }
    (CACHE_DIR / "engagements.json").write_text(json.dumps(out, indent=2))
    print()
    print(f"Cached: {CACHE_DIR}/{{lb,q81_comments,all_threads,engagements}}.json")


if __name__ == "__main__":
    main()
