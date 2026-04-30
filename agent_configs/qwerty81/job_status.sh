#!/usr/bin/env bash
set -euo pipefail

JOB_ID="${1:-}"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ -z "$JOB_ID" ]]; then
  echo "Usage: $(basename "$0") <job_id>"
  exit 1
fi

OUT_FILE="$ROOT_DIR/cluster.${JOB_ID}.out"
ERR_FILE="$ROOT_DIR/cluster.${JOB_ID}.err"

echo "Job status snapshot"
echo "==================="

if command -v squeue >/dev/null 2>&1; then
  squeue -j "$JOB_ID" -o "%.18i %.9P %.20j %.8u %.2t %.10M %.10L %.6D %R" || true
fi

if command -v sacct >/dev/null 2>&1; then
  echo
  sacct -j "$JOB_ID" --parsable2 --noheader --format=JobIDRaw,State,Submit,Start,End,Elapsed || true
fi

if [[ ! -f "$OUT_FILE" ]]; then
  echo
  echo "No cluster output file yet: $OUT_FILE"
  exit 0
fi

echo
python3 - "$OUT_FILE" <<'PY'
import json
import sys
from collections import deque

out_file = sys.argv[1]

attempts = []
successes = []
failures = []
pending_ids = set()

last_text = None
last_text_ts = None
last_tool = None
last_tool_ts = None
last_task = None
last_task_ts = None

recent_events = deque(maxlen=12)

with open(out_file, "r", encoding="utf-8", errors="ignore") as f:
    for idx, raw in enumerate(f, start=1):
        line = raw.strip()
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue

        ts = row.get("timestamp") or f"line#{idx}"
        typ = row.get("type")

        if typ == "assistant":
            msg = row.get("message") or {}
            content = msg.get("content") or []
            if isinstance(content, list):
                for c in content:
                    if not isinstance(c, dict):
                        continue
                    ctype = c.get("type")
                    if ctype == "text":
                        txt = (c.get("text") or "").strip().replace("\n", " ")
                        if txt:
                            last_text = txt
                            last_text_ts = ts
                    elif ctype == "tool_use":
                        tname = c.get("name")
                        tid = c.get("id")
                        if tname:
                            last_tool = tname
                            last_tool_ts = ts
                            recent_events.append((ts, f"tool_use {tname}"))
                        if tname == "mcp__koala__post_verdict" and tid:
                            attempts.append((tid, ts))
                            pending_ids.add(tid)

        elif typ == "user":
            msg = row.get("message") or {}
            content = msg.get("content") or []
            if isinstance(content, list):
                for c in content:
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") != "tool_result":
                        continue
                    tid = c.get("tool_use_id")
                    if not tid or tid not in pending_ids:
                        continue

                    is_error = bool(c.get("is_error", False))
                    payload = c.get("content", "")
                    payload_str = payload if isinstance(payload, str) else json.dumps(payload)

                    if is_error:
                        failures.append((tid, ts, payload_str[:160]))
                    else:
                        successes.append((tid, ts, payload_str[:160]))
                    pending_ids.discard(tid)

        elif typ == "system":
            subtype = row.get("subtype")
            if subtype in {"task_started", "task_notification"}:
                summary = row.get("summary") or row.get("description") or subtype
                status = row.get("status")
                if status:
                    summary = f"{summary} ({status})"
                last_task = summary
                last_task_ts = ts
                recent_events.append((ts, f"system {subtype}: {summary}"))

print("Agent activity")
print("--------------")
if last_text:
    print(f"Last assistant message: {last_text_ts} | {last_text[:240]}")
else:
    print("Last assistant message: none yet")

if last_tool:
    print(f"Last tool call: {last_tool_ts} | {last_tool}")
else:
    print("Last tool call: none yet")

if last_task:
    print(f"Last task event: {last_task_ts} | {last_task}")

print()
print("Verdict posting")
print("---------------")
print(f"Attempts: {len(attempts)}")
print(f"Successful posts: {len(successes)}")
print(f"Failed posts: {len(failures)}")
print(f"Awaiting tool result: {len(pending_ids)}")

if successes:
    print("Recent successful post timestamps:")
    for _, ts, _ in successes[-5:]:
        print(f"  {ts}")

if failures:
    print("Recent failures:")
    for _, ts, msg in failures[-3:]:
        print(f"  {ts} | {msg}")

if recent_events:
    print()
    print("Recent stream events")
    print("--------------------")
    for ts, ev in list(recent_events)[-8:]:
        print(f"  {ts} | {ev}")
PY

if [[ -f "$ERR_FILE" ]]; then
  echo
  echo "Stderr tail"
  echo "-----------"
  tail -n 12 "$ERR_FILE" || true
fi
