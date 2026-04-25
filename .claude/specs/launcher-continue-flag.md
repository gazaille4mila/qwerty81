# Spec: switch claude-code launcher from `--resume` to `--continue`

## Goal
Stop losing conversation context on every cluster-job restart. Switch the claude-code backend's resume mechanism from `claude --resume "$SESSION_ID"` (always fails after a `_timeout` SIGTERM) to `claude --continue` (works after SIGTERM, preserves context). This is a prerequisite for letting the agent run long-term on the cluster.

## Context

- `cli/reva/backends.py` declares the claude-code backend. Today it sets:
  ```
  resume_command_template = 'claude --resume "$SESSION_ID" ... --mcp-config {...}'
  session_id_extractor    = <python snippet that parses session_id from agent.log>
  ```
- `cli/reva/tmux.py:_make_run_block` generates a Bash loop. When `resume_command_template` is non-None, the loop:
  1. reads `last_session_id` (created by piping the previous run's stdout through `session_id_extractor`),
  2. runs `_timeout SESSION_TIMEOUT claude --resume "$SESSION_ID" ...`,
  3. on non-zero rc, falls back to `_timeout SESSION_TIMEOUT claude -p "$(cat initial_prompt.txt)" ...`.
- `_timeout` sends SIGTERM at `SESSION_TIMEOUT` seconds (default 600, deliberately kept low to cycle idle backends).
- **Empirical finding (spike, 2026-04-25):** `claude --resume "$SESSION_ID"` *always* fails after a SIGTERM-killed session — it requires the prior session to have ended via a "deferred tool" handoff. Result: every restart produces a `"No deferred tool marker found in the resumed session"` line in `agent.log`, falls through to the `-p initial_prompt.txt` path, and the agent loses all conversation context.
- Same spike confirmed: `claude --continue` *does* work after SIGTERM. Same session_id, prior cache hit, agent saw partial pre-SIGTERM output. The `-c, --continue` flag is documented as "Continue the most recent conversation in the current directory".
- The 2h soak (SLURM job 9360098) hit this 5 times in a single run — 6 distinct sessions, ~10 min of useful context per restart, then total reset.

User-confirmed scope:
- **Only the claude-code backend matters.** Codex / native backends are not in use; do not waste tokens preserving them. Leaving their templates broken is acceptable.
- `SESSION_TIMEOUT=600` stays — its purpose is idle-session cycling.

## Requirements

1. In `cli/reva/backends.py`, the claude-code backend's `resume_command_template` is changed to invoke `claude --continue` (no `"$SESSION_ID"` argument). All other args (`--dangerously-skip-permissions`, `--output-format stream-json`, `--verbose`, `--mcp-config <…>`) stay exactly as today.
2. The claude-code backend's `session_id_extractor` is dropped (set to `None` or removed entirely — `--continue` does not need it).
3. `cli/reva/tmux.py:_make_run_block` must produce a working launch script when `resume_command_template` is set but `session_id_extractor` is `None`. Concretely: the `last_session_id` file logic is bypassed for the claude path. Two acceptable implementations:
   - (a) Conditional in the template: only emit the parsing block when `session_id_extractor` is set; or
   - (b) Always parse but treat the `last_session_id` file as advisory (and have the resume command not depend on it).
   Implementer's choice; (a) is simpler.
4. The launch loop body for the claude backend always runs the resume command first; the `-p initial_prompt.txt` fallback is now reachable only on the very first iteration (when no prior conversation exists in the cwd). This is a behavior change — and is the desired one.
5. `--mcp-config` must continue to be passed on every invocation, including `--continue` runs (MCP server config is a runtime flag, not stored in the session).

## Constraints

- Do not modify other backends (codex, native). They may stop working as a side effect; that is acceptable per user direction.
- Do not modify `cli/reva/cluster.py` SLURM wrapping.
- Do not change the `--mcp-config` JSON structure or environment-variable substitution.
- Do not raise or lower `SESSION_TIMEOUT` defaults.
- Do not touch `agent_definition/` (this spec is launcher-only).

## Test Plan

Files to update / create:

- `tests/test_backends.py` — update assertions about the claude backend:
  - `resume_command_template` contains `--continue`
  - `resume_command_template` does **not** contain `--resume` or `$SESSION_ID`
  - `session_id_extractor` is `None`
- `tests/test_tmux.py` — update the rendering tests:
  - rendered launch script for the claude backend contains `claude --continue`
  - rendered launch script does **not** contain `claude --resume`
  - rendered launch script does **not** contain a `last_session_id` write (or, if it does, that file is unused on the claude path)
- `tests/test_launch_script.py` — add one new test: render a full launch script with the claude backend and assert the loop body has the structure described in Requirement #4 (resume command runs first, fallback only on rc != 0 with an empty/missing prior conversation).

No mocks needed — these are pure-string template tests.

## Acceptance Criteria

- [ ] `pytest tests/` passes with no skipped or xfail'd tests added by this change.
- [ ] `grep -n -- '--resume' cli/reva/backends.py` returns no line tied to the claude backend.
- [ ] `grep -n -- '--continue' cli/reva/backends.py` shows the claude backend's resume command.
- [ ] In a freshly rendered launch script (via existing renderer with `backend="claude"`), `grep "claude --continue"` returns at least one match and `grep "claude --resume"` returns zero matches.
- [ ] **Local smoke test — HARD GATE before any SLURM submission.** Run by user, not the implementing agent. Start a `reva` job in a scratch dir with `SESSION_TIMEOUT=120` so restarts are forced quickly. After ≥3 restarts, the resulting `agent.log` must show:
  - 0 lines containing the substring `No deferred tool marker`
  - The same `session_id` field across all `system/init` records (one continuous session)
  - Each post-restart `assistant` record has non-zero `cache_read_input_tokens` (proving context preserved)
  Do not submit a SLURM soak until all three checks pass locally.
- [ ] **Next 2h soak** (next SLURM run after the smoke test passes): post-mortem script reports a single `session_id` across the entire run, and 0 `BAD-JSON` parse failures in `agent.log`. This soak is the readiness gate for long-term cluster running.
