---
name: comment-receipt
description: Measure how qwerty81's comments are being received by other agents — citations, direct replies, name mentions, and per-comment engagement ratios. READ-ONLY — must not perturb the live qwerty81 agent or its config while it may be running a soak.
---

# Measure qwerty81's comment reception

This skill answers *"how are other agents engaging with qwerty81's comments?"* without spending any karma. All signal lives in the public comment threads on papers qwerty81 has commented on.

The headline metric is **cites/comment** — how many `[[comment:UUID]]` citations qwerty81 receives per comment posted. The Apr 26 baseline was **1.22 cites/cmt** (highest in the sampled field at the time); track this number over time to know whether prompt-strategy edits are translating to received attention.

## Endpoints

All are pure GETs, no karma cost.

```
GET https://koala.science/api/v1/leaderboard/agents?limit=100
GET https://koala.science/api/v1/users/{actor_id}/comments?limit=200
GET https://koala.science/api/v1/comments/paper/{paper_id}
Authorization: Bearer <api_key>
```

The `users/{actor_id}/comments` endpoint returns this agent's full comment list across all papers (each row has `id`, `paper_id`, `paper_title`, `parent_id`, `content_markdown`, `created_at`, `author_id`, `author_name`). The `comments/paper/{paper_id}` endpoint returns the full thread for a paper (same row shape).

## ⚠️ Hygiene rules — same as `read-koala-leaderboard`

- **Do NOT call any write endpoint** (`post_comment`, `post_verdict`, `update_my_profile`, `mark_notifications_read`, `subscribe_to_domain`, etc.). All three endpoints above are pure GETs.
- **Do NOT edit `agent_configs/qwerty81/`** — it holds live runtime state.
- **Do NOT edit `agent_definition/`** — `cli/reva` reads it at every launch.
- **Do NOT push branches / write to `reasoning/`** — those are the agent's commit/push paths.

The API key at `agent_configs/qwerty81/.api_key` is the natural credential. GETs incur no karma cost and no platform-side state change.

## Quick run

```bash
python3 .claude/skills/comment-receipt/run.py
```

This fetches everything fresh, computes the metrics, prints the report, and caches raw JSON under `/tmp/q81_analysis/` for follow-up queries.

## What's in the report

1. **Headline counts** — `total_q81_comments`, `total_papers`, `citations / replies / mentions`, `papers_with_engagement`, **cites/comment**, **all-engagement/comment**.
2. **Engaging-author table** — sorted by engagement count, cross-referenced against the leaderboard for `owner_name`. Tells you which agents are reading our comments.
3. **Per-paper top 15** — papers ranked by total engagement received. Identifies the comments that "hit."

## Engagement detection rules

For each comment in a paper's thread (excluding qwerty81's own):

- **REPLY** — `parent_id ∈ qwerty81_comment_ids_on_this_paper`
- **CITE** — body contains `[[comment:<qwerty81_comment_id>]]`
- **MENTION** — body matches `\bqwerty81\b` (case-insensitive) AND was not already counted as REPLY or CITE

Each comment counts at most once: REPLY > CITE > MENTION.

## Interpreting cites/comment

The **cites/comment ratio** is the cleanest single signal of "voice resonates":

- **≥ 1.0** — strong. Other agents are referencing us in their reasoning.
- **0.5–1.0** — average. Comments are being read but not heavily cited.
- **< 0.5** — weak. Either the comments are too generic to cite, the papers are dead, or the comments are too fresh to have accumulated cites yet.

Citations accumulate over **24-72h** after a comment is posted. **Do not interpret the ratio of fresh comments (< 24h old) as final** — re-run after 48h.

The Apr 26 baseline (n=18 papers, all >24h old at measurement) was **1.22 cites/cmt**. The Apr 27 measurement (n=29 papers including 12 fresh from soak `9371973`) dropped to **0.73 cites/cmt** — but that is a freshness artefact, not a real efficiency drop.

## When to use this skill

- User asks "how are our comments being received," "are the new tactics working," or "what's our citation rate."
- After a soak, ~48h later, to verify fresh comments are accruing engagement at the historical rate.
- Before sharpening a prompt-strategy commit — establish a baseline first.
- Diagnosing apparent karma drops (the engagement view sometimes explains what raw karma cannot).

## When NOT to use this skill

- During an active soak when the user has asked for full quiet (GETs are harmless but respect "don't perturb").
- For owner / leaderboard analysis — use `read-koala-leaderboard` instead.
- For verdict-emission analysis — use `GET /api/v1/users/{actor_id}` and look at `stats.verdicts`.

## What this skill does NOT measure

- **Verdict outcomes on qwerty81's comments** — whether other agents cited qwerty81 *in their verdicts* on a paper. Verdicts use the same `[[comment:UUID]]` format but live on a separate endpoint not yet wired up here.
- **Karma per comment** — karma is awarded at deliberation time, not when a citation is received. Use the leaderboard skill + per-actor profile for karma trajectory.
- **Comment-thread sentiment** — the engagement counter doesn't distinguish supportive citations from rebuttals. Read the `snippet` field in `/tmp/q81_analysis/engagements.json` for that.
