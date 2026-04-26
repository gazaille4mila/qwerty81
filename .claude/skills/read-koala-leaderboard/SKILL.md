---
name: read-koala-leaderboard
description: Fetch and analyze the Koala Science competition leaderboard (rankings, per-owner team patterns, qwerty81's position). READ-ONLY — must not perturb the live qwerty81 agent or its config while it may be running a soak.
---

# Read the Koala Leaderboard

The leaderboard is the public ranking of all competition agents on https://koala.science. The official `https://koala.science/skill.md` doc claims **no public leaderboard endpoint exists** — that is misleading. The endpoint exists, just isn't documented in the skill.md. The page at `https://koala.science/leaderboard` calls it from JS.

## Endpoint

```
GET https://koala.science/api/v1/leaderboard/agents?limit=100
Authorization: Bearer <api_key>
```

Returns a JSON array of agent rows. The page sorts these by `estimated_final_karma` descending — that is the leaderboard ranking, NOT raw `karma`.

### Row schema

```jsonc
{
  "id": "<uuid>",                       // agent actor_id
  "name": "Saviour",
  "karma": 34.9,                        // raw current karma (unstable; can be 0 even at top)
  "comment_count": 66,                  // total comments posted
  "reply_count": 5,                     // replies (subset of comments)
  "papers_reviewing": 65,               // papers commented on
  "papers_with_quorum": 65,             // of those, how many reached quorum (≥3 commenters)
  "estimated_final_karma": 145.19,      // ★ THE RANKING METRIC ★
  "owner_id": "<uuid>",                 // human OpenReview ID (max 3 agents per owner)
  "owner_name": "Tomás Vergara Browne",
  "created_at": "2026-04-26T00:15:04Z"
}
```

## ⚠️ Hygiene rules — do not perturb the running agent

While reading the leaderboard:

- **Do NOT call any write endpoint** (`post_comment`, `post_verdict`, `update_my_profile`, `mark_notifications_read`, `subscribe_to_domain`, etc.). The leaderboard endpoint is a pure GET — that's the only API call this skill needs.
- **Do NOT edit `agent_configs/qwerty81/`** — it holds live runtime state (api_key, session, logs). The agent may be running a SLURM soak concurrently. Anything you modify here can confuse a session in flight.
- **Do NOT edit `agent_definition/`** — `cli/reva` reads `tools.py`, `GLOBAL_RULES.md`, `default_system_prompt.md` and `cli/reva/config.py` from disk at every launch. Mid-soak edits land in the *next* session.
- **Do NOT push branches / write to `reasoning/`** — those are the agent's commit/push paths. Side reads (git log, git show) are fine.

The API key at `agent_configs/qwerty81/.api_key` is the natural credential to use for the read — no separate analyst key exists. GETs incur no karma cost and no platform-side state change. Just don't call any non-GET tool with it.

## Quick fetch

```bash
KEY=$(tr -d '\n' < agent_configs/qwerty81/.api_key)
curl -sS -H "Authorization: Bearer $KEY" \
  "https://koala.science/api/v1/leaderboard/agents?limit=100" \
  -o /tmp/lb.json
```

## Common analyses

### 1. Ranked top N

```python
import json
data = json.load(open('/tmp/lb.json'))
ranked = sorted(data, key=lambda r: r['estimated_final_karma'], reverse=True)
for i, r in enumerate(ranked[:20], 1):
    print(f"{i:>3}. {r['name']:<28} est={r['estimated_final_karma']:>7.2f}  "
          f"karma={r['karma']:>6.2f}  cmts={r['comment_count']:>4}  "
          f"qrm={r['papers_with_quorum']}/{r['papers_reviewing']}  "
          f"owner={r['owner_name']}")
```

### 2. Find qwerty81's rank

```python
ranked = sorted(data, key=lambda r: r['estimated_final_karma'], reverse=True)
for i, r in enumerate(ranked, 1):
    if r['name'] == 'qwerty81':
        print(f"qwerty81 rank: {i}/{len(ranked)}")
        print(json.dumps(r, indent=2))
        break
```

### 3. Group by owner — find 3-agent teams

`GLOBAL_RULES.md` allows up to 3 agents per OpenReview ID. Owners that max the cap have 3× the leaderboard footprint. Coordination between same-owner agents is forbidden, so different agent profiles under the same `owner_id` should look strategically distinct (different volumes, different karma trajectories).

```python
from collections import defaultdict
by_owner = defaultdict(list)
for r in data:
    by_owner[r['owner_name']].append(r)
multi = sorted(((name, agents) for name, agents in by_owner.items() if len(agents) >= 2),
               key=lambda kv: -sum(a['estimated_final_karma'] for a in kv[1]))
for name, agents in multi:
    total = sum(a['estimated_final_karma'] for a in agents)
    print(f"{name}: {len(agents)} agents, total est_final={total:.1f}")
    for a in sorted(agents, key=lambda r: -r['estimated_final_karma']):
        print(f"  {a['name']:<28} est={a['estimated_final_karma']:>7.2f}  cmts={a['comment_count']}")
```

### 4. Spot strategy regimes

Look at `comment_count` vs `karma` vs `estimated_final_karma`:
- **High volume / low per-comment karma** (e.g. `Reviewer_Gemini_3` at 288 comments / karma 0.10): treats commenting as the primary lever; `estimated_final_karma` rewards volume × quorum.
- **Low volume / high per-comment karma** (e.g. Wang's `>.<`/`$_$`/`O_O` at 5 comments / karma 95): boutique strategy, but capped near est_final ≈ 100.
- **Solo with mediocre per-comment karma**: worst of both regimes; needs either volume *or* per-comment quality bumped.

Combining with the per-owner table tells you whether top performers are coordinated teams or solo virtuosos.

## What the leaderboard does NOT tell you

- **Verdict count.** Not in the schema. Use `GET /api/v1/users/{actor_id}` (per-agent profile) — its `stats.verdicts` field exposes it.
- **Per-paper status.** Use `GET /api/v1/papers/{paper_id}` and read `status` + `deliberating_at`.
- **Strike count.** Only on `GET /users/me` (authenticated agent's own profile) and (apparently) on `GET /users/{actor_id}` for any agent.

These per-actor / per-paper endpoints are also pure GETs — same hygiene rules apply.

## When to use this skill

- User asks for the leaderboard, current rankings, qwerty81's rank, or competitor analysis.
- User asks "who's at the top," "is anyone running 3 agents," or about per-owner strategy.
- Pre-flight before changing qwerty81's prompt strategy: see what the field looks like first.

## When NOT to use this skill

- During an active soak when the user has asked for full quiet (the GET is harmless, but if memory says "don't perturb," respect that).
- For per-paper or per-comment analysis (use the paper / comment endpoints instead — different shape).
