# Spec: harness-level UUID validation for ID-bearing tool inputs

## Goal

Stop prefix-shaped IDs (8-char hex from branch names / file paths) from reaching the Koala API. Today the agent passes shortnames like `5ca0d89d` to `get_paper` because that's how it refers to papers in its own todos, branch names, and prior thinking. The behavioral fix (docs + tightened tool descriptions) shipped 2026-04-25 but the partial soak (job 9362701) still showed 2 prefix 422s in 14 min — confirming docs alone don't override the prefix's pattern-match strength in the agent's working memory. This spec adds structural enforcement: the harness intercepts prefix IDs before they leave the box and returns a corrective error string the LLM sees in the tool result.

## Context

- `agent_definition/harness/tools.py::dispatch(tool_name, tool_input, client) -> str` is the harness-side router. Today it does one thing: `if tool_name == "run_code"` use the local runner, else delegate to `client.call_tool(...)`. It returns the string the LLM sees in `tool_result.content`.
- `agent_definition/harness/koala.py::KoalaClient.call_tool(name, arguments) -> str` does the MCP HTTP call.
- Every tool schema in `tools.py:PLATFORM_TOOLS` declares its inputs. The ID-bearing fields across all platform tools are exactly:
  - `paper_id` — used by `get_paper`, `get_comments`, `post_comment`, `post_verdict`
  - `parent_id` — used by `post_comment` (optional)
  - `actor_id` — used by `get_actor_profile`
  - `flagged_agent_id` — used by `post_verdict` (optional)
  - `notification_ids` — used by `mark_notifications_read` (list of strings)

  No other current tool schema field name ends in `_id` or `_ids`. (Note: the original memory listed `comment_id` and `notification_id` — neither exists as an actual schema field. Citations use `[[comment:<uuid>]]` inside `content_markdown`, which is a string regex match, not a structured field.)
- All Koala IDs are full UUIDs matching `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`. The 8-char prefix shape `^[0-9a-f]{8}$` is reserved for human-facing identifiers (branch names, reasoning-file paths) per `agent_definition/GLOBAL_RULES.md` "ID Conventions".
- Evidence the docs-only fix isn't enough: in job 9362701's first 14 min the agent ran `git show ... agent-reasoning/qwerty81/41c60725` then immediately called `get_paper(paper_id="41c60725")` — the full UUID was right there in the same shell output (`41c60725-bb92-47f2-acf8-07f0b99647fb.md`) but the agent took the prefix.

## Requirements

1. **Pre-API validation in `dispatch`** (not `KoalaClient.call_tool`). When a tool's input contains any field whose name ends in `_id` or `_ids`, validate the value(s) against the full-UUID regex `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$` BEFORE delegating to `client.call_tool`. Rationale for choosing `dispatch`: (i) it's the LLM-facing return path (string in, string out), (ii) error-string returns fit naturally, (iii) `KoalaClient` is the network layer and should stay focused on HTTP; mixing schema validation in is a concern-leak.
2. **List-valued fields are validated element-wise.** `notification_ids: ["uuid-1", "prefix-2", "uuid-3"]` returns an error naming the offending element(s).
3. **Generic suffix match, not an explicit whitelist.** Validate any field whose name ends in `_id` or `_ids`. The current tool set has zero false-positive field names; new tools that add `_id`-suffixed fields will get validation for free, which is the desired default (Koala IDs are always UUIDs). If a future tool adds a non-UUID `_id` field, that tool's spec is on the hook to opt out — but that case doesn't exist today.
4. **Validation skips:**
   - Field is absent (the JSON schema's `required` list is the API's job).
   - Field value is `None` or empty string (let the API return its own error — different failure mode).
   - Tool is `run_code` (no Koala IDs flow through it).
5. **Error format (returned, not raised).** A single field violation returns:
   ```
   ERROR: paper_id 'a1b44436' is the 8-char branch-prefix shape, not the full UUID. Koala IDs are always full UUIDs (e.g. 'a1b44436-1234-4abc-9def-0123456789ab'). The 8-char prefix is for branch names / reasoning-file paths only — never in tool calls. To recover the full UUID for this paper, call get_papers (or look up the full UUID in the file path inside your agent-reasoning branch).
   ```
   Multiple violations in one call (e.g. `notification_ids` list with two prefix entries) are reported in one error string, one per line. The field name in the prefix is the actual schema field that failed (`paper_id`, `parent_id`, `actor_id`, `flagged_agent_id`, `notification_ids`).
6. **Validation rejects only the **prefix shape** specifically — not arbitrary malformed values.** Anything that's not the 8-char hex prefix shape but also not a full UUID (e.g. random text, integer, partial UUID like `a1b44436-1234`) is passed through to the API, which will return its own 422. Rationale: the structural enforcement is targeted at the *known* failure mode (prefix → 422). Catching every malformed input is API-shaped concern; doing it here would expand scope without payoff.

## Constraints

- Do not modify `KoalaClient.call_tool` (network layer stays clean).
- Do not modify `tools.py:PLATFORM_TOOLS` schemas (this is enforcement, not schema change).
- Do not modify `agent_definition/GLOBAL_RULES.md` (the "ID Conventions" section already documents the rule).
- Do not call the network in tests — `dispatch` validation must happen before `client.call_tool`, so a `MagicMock` client suffices.
- Do not raise exceptions on validation failure. The dispatch return type is `str`; an LLM-facing error string is the right shape.
- Keep the implementation in `tools.py` — do not add a new file. The validator can be one private function (`_validate_ids` or similar).

## Test Plan

New file: `tests/test_harness_id_validation.py`. Use `MagicMock` for `KoalaClient` (no network). Tests:

1. **Prefix paper_id is rejected, network not called.**
   ```python
   client = MagicMock()
   result = dispatch("get_paper", {"paper_id": "a1b44436"}, client)
   assert "ERROR" in result and "a1b44436" in result and "branch-prefix" in result
   client.call_tool.assert_not_called()
   ```
2. **Full-UUID paper_id passes through.** `dispatch("get_paper", {"paper_id": FULL_UUID}, client)` returns whatever `call_tool` returned; `call_tool` is called once with the same args.
3. **Each ID-bearing field individually rejects a prefix:** parameterize over `("get_paper", "paper_id")`, `("post_comment", "parent_id")`, `("get_actor_profile", "actor_id")`, `("post_verdict", "flagged_agent_id")`.
4. **`mark_notifications_read.notification_ids` list — one bad element returns error naming that element; pure-UUID list passes through.**
5. **`mark_notifications_read.notification_ids` empty list passes through** (no validation to run).
6. **Absent optional ID** (e.g. `post_comment` without `parent_id`) passes through.
7. **`None` and empty string ID values pass through** (let API return its own error).
8. **`run_code` tool with `script` containing the substring `paper_id="a1b44436"` is NOT validated** — `_id` fields are validated by *field name*, not by content scanning.
9. **Multiple violations in one call** (e.g. `notification_ids: ["prefix1", "prefix2"]`) produce one error string with one line per violation; both prefixes appear in the message.
10. **Non-prefix malformed input is passed through** (e.g. `paper_id: "not-a-uuid"`, `paper_id: ""` covered above, `paper_id: "a1b44436-1234"` partial). The validator only blocks the specific prefix shape `^[0-9a-f]{8}$`.

No mocking of `KoalaClient.call_tool` return value beyond `MagicMock()` defaults. No live HTTP.

## Acceptance Criteria

- [ ] `pytest tests/` passes; new file `tests/test_harness_id_validation.py` is included; no skipped/xfail tests added.
- [ ] `git grep -nE 'def _validate_ids|def _is_uuid|def _is_prefix' agent_definition/harness/tools.py` shows the validator was added in `tools.py` (not a new file, not in `koala.py`).
- [ ] `git grep -n 'def call_tool' agent_definition/harness/koala.py` shows `KoalaClient.call_tool` was NOT modified beyond what's already in HEAD.
- [ ] Smoke test: in a Python REPL, `from agent_definition.harness.tools import dispatch; from unittest.mock import MagicMock; print(dispatch("get_paper", {"paper_id": "a1b44436"}, MagicMock()))` prints an `ERROR:` string containing the prefix and the corrective sentence; the mock's `call_tool` was not called.
- [ ] Existing tests stay green: `tests/test_harness_koala.py`, `tests/test_validate_agent_log.py`, `tests/test_backends.py`.
- [ ] **Next 2h soak — readiness gate:** `validate_agent_log.py agent_configs/qwerty81/agent.log` exits 0. Zero prefix-paper_id 422s reach the API.
- [ ] **Next 2h soak — observability gate (proves the contingency is actually load-bearing, not dead code):** if `agent.log` contains any `tool_use` whose `*_id` or `*_ids` input has a value matching `^[0-9a-f]{8}$`, every such `tool_use` must be followed by a matching `tool_result` with `is_error: true` and content starting with `ERROR:` containing `branch-prefix`. Vacuously satisfied if the agent never emitted a prefix-shape `*_id` during the soak (in which case the docs-only fix turned out to suffice and this contingency is over-engineered — useful information). Concretely: after the soak, run a one-off Python check (similar shape to `validate_agent_log.py`) that pairs prefix-shape tool_uses with their tool_results and asserts the harness-rejection error.

## Out of scope (parked for later)

- **Auto-expand prefix → full UUID via cached `get_papers` lookup.** Would silently rewrite prefix paper_ids to full UUIDs on the way through `dispatch`, eliminating the violation entirely instead of just catching it. ~30 lines plus a per-prefix cache. Parked because: (i) the basic contingency proves the pattern first, (ii) auto-expand only helps `paper_id` — `parent_id`/`actor_id`/`flagged_agent_id` would still need catch-and-correct, (iii) YAGNI if the basic version's recovery cost is acceptable. Revisit only if the post-soak agent.log shows an excessive number of harness-rejected calls causing visible recovery overhead.

## Naming (locked)

- Validator function: `_validate_ids` in `agent_definition/harness/tools.py`.
- Test file: `tests/test_harness_id_validation.py` (matches existing `test_harness_koala.py` convention).
