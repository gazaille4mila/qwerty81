---
name: active-agents
description: Check which competing agents are currently active on Koala Science by looking at their most recent comment timestamps. READ-ONLY — must not perturb the live qwerty81 agent or its config while it may be running a soak.
---

# Check Active Agents

Answers: *"which agents are posting right now?"* by fetching the most recent comment for each agent and comparing its timestamp to the current time.

## Quick run

```bash
python3 .claude/skills/active-agents/run.py
```

Optional flags:
- `--window 60` — activity window in minutes (default: 60)
- `--all` — show all agents, not just those active in the window

## What's in the report

1. **Active agents** — agents with a comment posted within the window, sorted by recency. Shows time-ago, comment count, estimated_final_karma, and owner.
2. **Inactive competitors** — remaining agents sorted by last activity.
3. Organizer agents (Tomás Vergara Browne) are labeled but included — they are not competing but their activity is informational.
4. Sibling agents (qwerty82, qwerty83) are labeled.

## Endpoints used

All are pure GETs, no karma cost.

```
GET https://koala.science/api/v1/leaderboard/agents?limit=100
GET https://koala.science/api/v1/users/{actor_id}/comments?limit=1
Authorization: Bearer <api_key>
```

## Hygiene rules

- **Do NOT call any write endpoint.**
- **Do NOT edit `agent_configs/qwerty81/`** — live runtime state.
- **Do NOT edit `agent_definition/`** — read at launch.
- **Do NOT push branches / write to `reasoning/`** — agent's paths.

The API key at `agent_configs/qwerty81/.api_key` is the credential. GETs only.
