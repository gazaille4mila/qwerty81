#!/usr/bin/env bash
#
# check.sh — One-shot status check for verdict timing.
#
# Usage:
#   bash .claude/skills/verdict-phase-monitor/check.sh [API_KEY]
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ $# -gt 0 ]]; then
    API_KEY="$1"
else
    API_KEY=$(cat "$SCRIPT_DIR/../../../agent_configs/qwerty81/.api_key" 2>/dev/null || echo "")
    if [[ -z "$API_KEY" ]]; then
        echo "ERROR: No API key found. Provide one as argument or check path to .api_key" >&2
        exit 1
    fi
fi

BASE="https://koala.science/api/v1"
HEADERS="Authorization: Bearer $API_KEY"

# Identity
me=$(curl -s "$BASE/users/me" -H "$HEADERS")
MY_ID=$(echo "$me" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")
if [[ -z "$MY_ID" ]]; then
    echo "ERROR: Could not authenticate. Check your API key." >&2
    exit 1
fi

# Authoritative verdict count
profile=$(curl -s "$BASE/users/$MY_ID" -H "$HEADERS")
SUBMITTED_VERDICTS=$(echo "$profile" | python3 -c "import json,sys; d=json.load(sys.stdin); print(((d.get('stats') or {}).get('verdicts')) or 0)" 2>/dev/null || echo "0")

# Commented papers
comments=$(curl -s "$BASE/users/$MY_ID/comments?limit=1000" -H "$HEADERS")
paper_ids=$(echo "$comments" | python3 -c '
import json,sys
try:
    data=json.load(sys.stdin)
    ids=sorted({c.get("paper_id") for c in data if c.get("paper_id")})
    print("\n".join(ids))
except:
    pass
' 2>/dev/null || echo "")

if [[ -z "$paper_ids" ]]; then
    echo "No commented papers found."
    echo "Verdicts already submitted: $SUBMITTED_VERDICTS"
    exit 0
fi

temp_file=$(mktemp)
trap 'rm -f "$temp_file"' EXIT

while read -r paper_id; do
    [[ -z "$paper_id" ]] && continue
    paper=$(curl -s "$BASE/papers/$paper_id" -H "$HEADERS")
    row=$(echo "$paper" | python3 -c '
import json,sys,datetime
try:
    d=json.load(sys.stdin)
    s=d.get("status","unknown")
    c=d.get("created_at","")
    title=(d.get("title") or "").replace("|", "/")
    if not c:
        raise SystemExit

    # Normalize API timestamp to aware UTC.
    ts=c.strip()
    if ts.endswith("Z"):
        dt=datetime.datetime.fromisoformat(ts.replace("Z","+00:00"))
    else:
        dt=datetime.datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt=dt.replace(tzinfo=datetime.timezone.utc)

    verdict_dt_utc=dt + datetime.timedelta(hours=48)
    verdict_epoch=int(verdict_dt_utc.timestamp())
    try:
        from zoneinfo import ZoneInfo
        mtl=ZoneInfo("America/Toronto")
        verdict_fmt=verdict_dt_utc.astimezone(mtl).strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        # Fallback for environments without tz data.
        mtl=datetime.timezone(datetime.timedelta(hours=-4))
        verdict_fmt=verdict_dt_utc.astimezone(mtl).strftime("%Y-%m-%d %H:%M:%S EDT")
    print(f"{s}|{verdict_epoch}|{verdict_fmt}|{title}")
except:
    pass
' 2>/dev/null || echo "")

    [[ -n "$row" ]] && echo "$paper_id|$row" >> "$temp_file"
done <<< "$paper_ids"

if [[ ! -s "$temp_file" ]]; then
    echo "No valid paper data found."
    echo "Verdicts already submitted: $SUBMITTED_VERDICTS"
    exit 0
fi

in_review=$(grep -c '|in_review|' "$temp_file" || true)
deliberating=$(grep -c '|deliberating|' "$temp_file" || true)
reviewed=$(grep -c '|reviewed|' "$temp_file" || true)
total=$(wc -l < "$temp_file")

echo "Summary: $total papers total | $in_review in review | $deliberating in verdict phase | $reviewed closed"
echo "Verdicts already submitted: $SUBMITTED_VERDICTS"

already_verdicted=0
if [[ "$deliberating" -gt 0 ]]; then
    deliberating_paper_ids=$(grep '|deliberating|' "$temp_file" | cut -d'|' -f1 || true)

    while read -r paper_id; do
        [[ -z "$paper_id" ]] && continue

        verdicts=$(curl -s "$BASE/verdicts/paper/$paper_id" -H "$HEADERS")
        has_mine=$(echo "$verdicts" | python3 -c '
import json,sys
author_id=sys.argv[1]
try:
    data=json.load(sys.stdin)
    mine=any(isinstance(v, dict) and v.get("author_id") == author_id for v in data)
    print("1" if mine else "0")
except Exception:
    print("0")
' "$MY_ID" 2>/dev/null || echo "0")

        if [[ "$has_mine" == "1" ]]; then
            already_verdicted=$((already_verdicted + 1))
        fi
    done <<< "$deliberating_paper_ids"
fi

need_verdict=$((deliberating - already_verdicted))
echo "In verdict phase (commented papers): $deliberating | already verdicted: $already_verdicted | not yet verdicted: $need_verdict"

# Exact transition timestamps for papers still in review
if [[ "$in_review" -gt 0 ]]; then
    echo ""
    echo "Exact transition times to verdict phase (Montreal):"
    grep '|in_review|' "$temp_file" \
        | cut -d'|' -f4 \
        | sort \
        | uniq -c \
        | while read -r count ts; do
            echo "  $ts - $count paper(s)"
          done

fi
