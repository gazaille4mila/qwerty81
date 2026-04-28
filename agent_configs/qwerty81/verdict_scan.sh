#!/usr/bin/env bash
set -euo pipefail

API_KEY=$(cat "$(dirname "$0")/.api_key")
BASE="https://koala.science/api/v1"
MY_ID="69f37a13-0440-4509-a27c-3b92114a7591"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

curl -s "$BASE/papers/?status=deliberating&limit=500" \
  -H "Authorization: Bearer $API_KEY" > /tmp/delib_papers.json

curl -s "$BASE/users/$MY_ID/comments?limit=1000" \
  -H "Authorization: Bearer $API_KEY" > /tmp/my_comments.json

# Pass API_KEY to python via env
export API_KEY

python3 << 'PYEOF'
import json, subprocess, os

MY_ID = "69f37a13-0440-4509-a27c-3b92114a7591"
API_KEY = os.environ["API_KEY"]

delib = json.load(open("/tmp/delib_papers.json"))
comments = json.load(open("/tmp/my_comments.json"))

delib_ids = {p["id"] for p in delib}
my_paper_ids = {c["paper_id"] for c in comments}
eligible = sorted(delib_ids & my_paper_ids)

print(f"Deliberating: {len(delib)}  My comments: {len(comments)}  Eligible: {len(eligible)}")

# Check which I already verdicted
need_verdict = []
for pid in eligible:
    r = subprocess.run(
        ["curl", "-s", f"https://koala.science/api/v1/verdicts/paper/{pid}",
         "-H", f"Authorization: Bearer {API_KEY}"],
        capture_output=True, text=True
    )
    verdicts = json.loads(r.stdout)
    mine = [v for v in verdicts if v.get("author_id") == MY_ID]
    if not mine:
        need_verdict.append(pid)

print(f"Already verdicted: {len(eligible) - len(need_verdict)}  Need verdict: {len(need_verdict)}")
print()
for pid in need_verdict:
    print(pid)
PYEOF
