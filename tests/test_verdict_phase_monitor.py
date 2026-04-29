import os
import subprocess
from pathlib import Path


def _write_fake_curl(bin_dir: Path) -> None:
    curl_path = bin_dir / "curl"
    curl_path.write_text(
        """#!/usr/bin/env python3
import json
import sys

url = ""
for arg in sys.argv[1:]:
    if arg.startswith("http://") or arg.startswith("https://"):
        url = arg

if url.endswith("/users/me"):
    print(json.dumps({"id": "agent-1"}))
elif url.endswith("/users/agent-1"):
    print(json.dumps({"stats": {"verdicts": 2}}))
elif "/users/agent-1/comments" in url:
    print(json.dumps([
        {"paper_id": "paper-a"},
        {"paper_id": "paper-b"},
        {"paper_id": "paper-c"},
    ]))
elif url.endswith("/papers/paper-a"):
    print(json.dumps({
        "id": "paper-a",
        "status": "in_review",
        "created_at": "2026-04-29T00:00:01Z",
        "title": "Paper A Title"
    }))
elif url.endswith("/papers/paper-b"):
    print(json.dumps({
        "id": "paper-b",
        "status": "deliberating",
        "created_at": "2026-04-28T00:00:01Z",
        "title": "Paper B Title"
    }))
elif url.endswith("/papers/paper-c"):
    print(json.dumps({
        "id": "paper-c",
        "status": "deliberating",
        "created_at": "2026-04-28T04:00:01Z",
        "title": "Paper C Title"
    }))
elif url.endswith("/verdicts/paper/paper-b"):
    print(json.dumps([
        {"author_id": "agent-1", "paper_id": "paper-b"}
    ]))
elif url.endswith("/verdicts/paper/paper-c"):
    print(json.dumps([
        {"author_id": "other-agent", "paper_id": "paper-c"}
    ]))
else:
    print("{}")
""",
        encoding="utf-8",
    )
    curl_path.chmod(0o755)


def test_verdict_phase_monitor_splits_deliberating_subset(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / ".claude/skills/verdict-phase-monitor/check.sh"

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_curl(bin_dir)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"

    result = subprocess.run(
        ["bash", str(script), "dummy-api-key"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Summary: 3 papers total | 1 in review | 2 in verdict phase | 0 closed" in result.stdout
    assert "In verdict phase (commented papers): 2 | already verdicted: 1 | not yet verdicted: 1" in result.stdout
    assert "Exact transition times to verdict phase (Montreal):" in result.stdout
    assert "2026-04-30 20:00:01 EDT - 1 paper(s)" in result.stdout
    assert "Papers about to enter verdict phase:" not in result.stdout
    assert "Paper A Title" not in result.stdout
